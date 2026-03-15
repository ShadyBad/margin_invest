# Growth Factors + PIT-Bootstrapped ML Design

**Date:** 2026-03-15
**Status:** Approved
**Approach:** A — Growth Factors + PIT-Bootstrapped ML

## Problem Statement

Three interconnected gaps in the scoring engine:

1. **Growth factors exist but carry zero weight**: 4 growth scoring modules (`incremental_roic`, `revenue_cagr`, `rule_of_40`, `runway_score`) exist in `engine/src/margin_engine/scoring/quantitative/` and are wired into `scoring.py`, but `compute_composite_score()` assigns them `weight=0.0` — they are informational only and don't affect the final score.
2. **ML IC=0.0**: V4 scoring has only existed since 2026-02-24 (~3 weeks). Forward returns require 252 trading days of future data. Zero tickers have enough data, so all forward returns default to 0.0 and IC is mathematically 0.0.
3. **V2 scoring is dead weight**: `full_score` (v2) runs in the pipeline chain but produces scores superseded by v3/v4. It wastes compute on every scoring cycle.

## Solution Overview

Sequential four-phase approach:

1. Give growth factors real weight in composite scoring (requires `ScoringConfig` and `compute_composite_score()` changes)
2. Build a historical scorer using PIT data to generate ~150K training samples
3. Fix forward returns computation and retrain ML with real data
4. Remove v2 scoring path once v4+ML is validated

## Phase 1: Growth Factor Weight Activation

### Current State

The 4 growth modules already exist and are registered in the factor registry (38 total factors: 13 quality + 10 value + 9 momentum + 4 growth + 2 catalyst). They use `FinancialHistory` / `FinancialPeriod` models, not raw dicts:

- `incremental_roic(history: FinancialHistory) -> FactorScore`
- `revenue_cagr(history: FinancialHistory, years: int = 3) -> FactorScore`
- `rule_of_40(revenue_growth_rate: float, fcf_margin: float) -> FactorScore`
- `runway_score(revenue: float, ...) -> FactorScore`

They are already called in `scoring.py` and passed to `compute_composite_score()`, but `composite.py` line 80 sets `weight=0.0` and the composite percentile calculation (lines 85-88) only uses quality, value, and momentum.

### Required Changes

#### `ScoringConfig` (engine/src/margin_engine/models/scoring.py)

Add `growth_weight` field. Current weights: `quality_weight=0.35, value_weight=0.30, momentum_weight=0.35` (sum=1.0). No `catalyst_weight` exists.

New defaults:
- `quality_weight=0.25`
- `value_weight=0.20`
- `momentum_weight=0.25`
- `growth_weight=0.15`
- Remaining 0.15 reserved for future catalyst activation (catalyst stays at weight=0.0 for now; weights sum to 0.85 from named pillars, normalized to 1.0 in composite calculation)

Update `weights_for_stage()` to return 4-tuple `(q, v, m, g)` instead of 3-tuple.

#### `compute_composite_score()` (engine/src/margin_engine/scoring/composite.py)

- Use `config.growth_weight` instead of hardcoded `0.0`
- Include growth in composite percentile: `q*wq + v*wv + m*wm + g*wg`
- Normalize weights to sum to 1.0 (handles the case where catalyst is added later)
- Include growth scores in `all_scores` for data coverage calculation

#### Growth factor golden-value tests

Each module needs a golden-value test (hand-calculated expected output). These may partially exist in unstaged test files — verify and complete.

## Phase 2: Historical Scorer

### Purpose

Generate synthetic V4 scores for every quarter from 2009-Q1 to 2025-Q4, creating ~67 quarters x ~3,000 tickers of training data for ML.

### New Module: `engine/src/margin_engine/scoring/historical_scorer.py`

**Core function:** `score_universe_at_date(pit_snapshots, pit_prices, date) -> list[CompositeScore]`

- Takes a point-in-time slice of financial data and prices as-of a specific date
- Runs the identical scoring pipeline as `full_score_v4`: elimination filters → raw factor scores → sector-neutral percentile ranking → composite score
- Returns fully populated `CompositeScore` objects
- Uses `pit_universe_memberships` to only score tickers listed on each date (survivorship bias prevention)

### Data Flow

```
pit_financial_snapshots (quarterly, 213K rows)
         |
For each rebalance date (quarter-end, 67 dates):
  1. Query snapshots with filing_date <= rebalance_date (PIT-correct)
  2. Query pit_daily_prices for trailing 252 days (momentum factors)
  3. Query pit_universe_memberships for active tickers
  4. Run compute_composite_score() with all 38 factors
  5. Bulk-insert into historical_scores
         |
historical_scores table (~180K rows, of which ~150K will have valid forward returns)
```

### New Table: `historical_scores`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| ticker | VARCHAR(20) | Asset ticker |
| score_date | DATE | Quarter-end date |
| composite_score | FLOAT | 0-100 |
| composite_tier | VARCHAR(20) | strong/stable/emerging/weak/failed |
| sub_scores | JSONB | Full factor breakdown (all 38 factors) |
| created_at | TIMESTAMP(tz) | When computed |

**Unique constraint:** `(ticker, score_date)` — prevents duplicate scoring.

**Alembic migration required:** Create with idempotent `inspector.has_table()` check per project conventions.

### New Worker: `backfill_historical_scores`

- Iterates quarter-end dates from 2009-Q1 to 2025-Q4
- Idempotent: skips quarters that already have scores
- Expected runtime: ~30-60 minutes (67 quarters x ~3,000 tickers, pure computation)
- Registered in `workers.py` with 2h timeout

## Phase 3: ML Training Fix

### Forward Returns Fix

**Modified module:** `engine/src/margin_engine/ml/forward_returns.py`

New function: `compute_historical_forward_returns(pit_prices: dict[str, list], score_date, horizon_days=252) -> dict[str, float]`

- Takes PIT price data as a parameter (engine stays pure Python — no DB access)
- The worker passes PIT prices from the database; the engine function is a pure computation
- For each ticker: `(price_at_score_date+252 / price_at_score_date) - 1.0`
- Tickers without sufficient future price data are **excluded entirely** (not returned in the dict)

**Critical bug fix** in training data assembly (current code defaults missing tickers to 0.0):
```python
# BEFORE (broken): missing tickers get 0.0, polluting signal
forward_returns = np.array([fwd_returns.get(t, 0.0) for t in tickers])

# AFTER (fixed): only include tickers with actual forward returns
valid_mask = np.array([t in fwd_returns for t in tickers])
tickers = [t for t in tickers if t in fwd_returns]
features = features[valid_mask]
forward_returns = np.array([fwd_returns[t] for t in tickers])
# Must also re-index composites list for cluster_stocks() downstream
composites = [c for c, m in zip(composites, valid_mask) if m]
```

### Training Data Assembly

Modified `train_ml_models` worker:

1. Load `historical_scores` for quarters 2009-Q1 through 2024-Q4 (stop 1 year before present — need forward returns)
2. For each quarter: extract 38-feature matrix from `sub_scores`, compute forward returns from PIT prices (passed as parameter)
3. Concatenate: ~60 quarters x ~2,500 valid tickers (those with 252 days of future prices) = **~150K training samples**
4. Cluster via VAE → train per-cluster LightGBM → validate IC
5. Expected IC: 0.05-0.15 range (typical for cross-sectional equity factors)

### Multi-Seed Validation Gate Adjustment

The existing gate requires `median IC > 0.15`, but bootstrapped models will realistically produce IC in the 0.05-0.15 range. Two options:

- **Lower the gate** for bootstrapped training: `median IC > 0.05, CV < 0.50, worst seed > 0.02`
- **Keep the gate** and iterate on feature engineering until 0.15 is achievable

Recommendation: **lower the gate** initially with a config flag `MARGIN_ML_BOOTSTRAP_MODE=true`. Once live data accumulates and model quality improves, revert to the stricter gate. The Phase 4 safety gate (IC > 0.05) is the minimum bar for removing v2.

### Ongoing Training Transition

Post-bootstrap, training transitions to blended data:
- Config: `MARGIN_ML_LIVE_WEIGHT` (default 0.0, gradually increase)
- Late 2027+: 70% PIT-bootstrapped + 30% live-scored, shifting to 100% live
- Prevents discontinuity when switching data sources

## Phase 4: V2 Scoring Deprecation

### Removed

- `full_score()` function from `scoring.py`
- `full_score` from `workers.py` registered functions list and any cron schedule references
- Any CLI commands invoking v2 scoring
- Tests referencing `full_score` (delete or redirect to v3)
- Helper functions only used by v2

### Changed

Worker chain:
- **Before:** `ingest_sweep_complete` → `full_score` → `full_score_v3` → `full_score_v4` → `stage_scores`
- **After:** `ingest_sweep_complete` → `full_score_v3` → `full_score_v4` → `stage_scores`

Update `ingest_sweep_complete` to enqueue `full_score_v3` directly.

### Preserved

- All historical v2 data in the database (no data deletion)
- `scores` table schema unchanged
- `full_score_v3` and `full_score_v4` unchanged

### Safety Gate

V2 removal only proceeds after ALL conditions are met:
1. Growth factors have real weight and passing tests
2. `historical_scores` table populated (~180K rows)
3. ML training produces IC > 0.05 (non-zero, meaningful signal)
4. At least one full live scoring cycle completes with v3→v4 chain (no v2)

If any gate fails, v2 stays as fallback.

## Testing Strategy

### Growth Factor Tests (engine)
- Golden-value tests: hand-calculated inputs → expected `FactorScore` output (one per module, using `FinancialHistory` / `FinancialPeriod` models)
- Edge cases: insufficient periods → zero-value score, negative values, zero revenue, single-period history
- Integration: full `compute_composite_score()` with growth weight > 0, verify it contributes to composite percentile
- Weight normalization: verify weights sum to 1.0 after normalization

### Historical Scorer Tests (engine)
- Unit: `score_universe_at_date()` with synthetic PIT data → verify output matches live scoring logic
- Survivorship: delisted ticker appears in early quarters, disappears in later ones
- Determinism: identical inputs produce identical scores

### ML Training Tests (engine)
- Forward returns: tickers without future prices excluded (not defaulted to 0.0)
- Downstream index consistency: after filtering, `features`, `tickers`, and `composites` arrays remain aligned
- Training with data: mock historical scores with known feature/return pairs, verify IC > 0
- Regression: all 92 existing ML tests continue passing

### V2 Deprecation Tests (api)
- Chain: `ingest_sweep_complete` enqueues `full_score_v3` (not `full_score`)
- Negative: `full_score` function no longer exists in module
- End-to-end: full scoring pipeline completes without v2

### Infrastructure
No new test infrastructure needed. Engine tests use pure Python with `FinancialHistory` models. API tests use aiosqlite. Historical scorer tests use synthetic PIT data. One Alembic migration for the `historical_scores` table.

## Execution Order

Strict sequential phases — each depends on the prior:

1. **Growth Factor Activation** (modify `ScoringConfig`, `compute_composite_score()`, add golden-value tests)
2. **Historical Scorer** (depends on growth factors having real weight)
3. **ML Training Fix** (depends on historical scores existing)
4. **V2 Deprecation** (depends on ML validation passing)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Weight change shifts all existing scores | Expected — v4 scores are recomputed on every cycle. No cached scores are served stale |
| Growth factor distributions skewed for some sectors | Sector-neutral percentile ranking handles this inherently |
| Historical scorer produces different results than live scorer | Shared code path — `score_universe_at_date()` calls the same `compute_composite_score()` |
| PIT data quality issues (missing fields, bad values) | Existing sanitization in PIT pipeline + zero-value returns for insufficient data |
| ML IC below bootstrap gate (0.05) | Iterate on feature engineering; v2 stays as fallback until gate passes |
| V2 removal breaks downstream consumers | Safety gate requires full live cycle success before removal |
| Forward returns filtering breaks downstream array alignment | Explicit test for index consistency after mask application |
