# Growth Factors + PIT-Bootstrapped ML Design

**Date:** 2026-03-15
**Status:** Approved
**Approach:** A — Growth Factors + PIT-Bootstrapped ML

## Problem Statement

Three interconnected gaps in the scoring engine:

1. **Missing growth factors**: 4 growth scoring modules (`incremental_roic`, `revenue_cagr`, `rule_of_40`, `runway_score`) are referenced but not implemented. The growth pillar has zero weight.
2. **ML IC=0.0**: V4 scoring has only existed since 2026-02-24 (~3 weeks). Forward returns require 252 trading days of future data. Zero tickers have enough data, so all forward returns default to 0.0 and IC is mathematically 0.0.
3. **V2 scoring is dead weight**: `full_score` (v2) runs in the pipeline chain but produces scores superseded by v3/v4. It wastes compute on every scoring cycle.

## Solution Overview

Sequential four-phase approach:

1. Create 4 growth factor modules with golden-value tests
2. Build a historical scorer using PIT data to generate ~150K training samples
3. Fix forward returns computation and retrain ML with real data
4. Remove v2 scoring path once v4+ML is validated

## Phase 1: Growth Factor Modules

### New Modules

Four new files in `engine/src/margin_engine/scoring/quantitative/`:

#### `incremental_roic.py`
- **Formula**: `delta_NOPAT / delta_invested_capital` over trailing 4 quarters
- **Inputs**: PIT snapshot fields — `net_income`, `total_assets`, `total_debt`, `cash_and_equivalents`
- **Signal**: High incremental ROIC (>15%) indicates efficient capital deployment and compounding ability
- **Edge cases**: Returns `None` if fewer than 2 quarters of data available

#### `revenue_cagr.py`
- **Formula**: Compound annual growth rate over 3-year and 1-year windows
- **Inputs**: PIT snapshots spanning 12 quarters (3Y) and 4 quarters (1Y)
- **Output**: `cagr_3y`, `cagr_1y`, blended score (70% 3Y / 30% 1Y for stability)
- **Edge cases**: Returns `None` if fewer than 4 quarters available; handles zero/negative base revenue

#### `rule_of_40.py`
- **Formula**: `revenue_growth_rate + profit_margin` vs. 40 threshold
- **Inputs**: Trailing 4Q revenue vs. prior 4Q; operating income / revenue for margin
- **Output**: Distance from 40 threshold, percentile-ranked within sector
- **Edge cases**: Zero revenue → `None`; applicable to all sectors (not SaaS-only)

#### `runway_score.py`
- **Formula**: Profitable companies → `free_cash_flow / market_cap` (FCF yield proxy). Unprofitable → `cash / quarterly_burn_rate` (quarters of runway)
- **Inputs**: `free_cash_flow`, `market_cap`, `cash_and_equivalents`, operating expenses
- **Output**: Continuous percentile within profitable/unprofitable bucket
- **Edge cases**: Zero burn rate → max runway score; missing FCF → derive from operating cash flow - capex

### Module Pattern

Each module follows the existing scoring module pattern:
- Pure function: `compute_<factor>(financials: dict, history: list[dict]) -> FactorScore`
- Returns `FactorScore(raw_value=float, percentile=None, details=dict)`
- Percentile ranking happens at the composite level (sector-neutral)
- No external dependencies (pure computation)

### Wiring

- Added to `GROWTH_FACTORS` list in `api/src/margin_api/services/scoring.py` → `compute_raw_factor_scores()`
- `compute_composite_score()` receives `growth_scores` with real weight: **0.15**
- Weight redistribution: quality 0.30→0.25, value 0.25→0.20, momentum 0.20 (unchanged), growth 0.00→0.15, catalyst 0.05 (unchanged)
- Feature registry updated: 4 new features in the `growth` pillar (46→50 total factors)

## Phase 2: Historical Scorer

### Purpose

Generate synthetic V4 scores for every quarter from 2009-Q1 to 2025-Q4, creating ~60 quarters x ~3,000 tickers of training data for ML.

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
  4. Run compute_composite_score() with all 50 factors
  5. Bulk-insert into historical_scores
         |
historical_scores table (~180K rows)
```

### New Table: `historical_scores`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| ticker | VARCHAR(20) | Asset ticker |
| score_date | DATE | Quarter-end date |
| composite_score | FLOAT | 0-100 |
| composite_tier | VARCHAR(20) | strong/stable/emerging/weak/failed |
| sub_scores | JSONB | Full factor breakdown (all 50 factors) |
| created_at | TIMESTAMP(tz) | When computed |

**Unique constraint:** `(ticker, score_date)` — prevents duplicate scoring.

### New Worker: `backfill_historical_scores`

- Iterates quarter-end dates from 2009-Q1 to 2025-Q4
- Idempotent: skips quarters that already have scores
- Expected runtime: ~30-60 minutes (67 quarters x ~3,000 tickers, pure computation)
- Registered in `workers.py` with 2h timeout

## Phase 3: ML Training Fix

### Forward Returns Fix

**Modified module:** `engine/src/margin_engine/ml/forward_returns.py`

New function: `compute_historical_forward_returns(score_date, horizon_days=252) -> dict[str, float]`
- Uses `pit_daily_prices` instead of live `price_history` JSONB
- For each ticker: `(price_at_score_date+252 / price_at_score_date) - 1.0`
- Tickers without sufficient future price data are **excluded entirely**

**Critical bug fix** in training data assembly (current code defaults missing tickers to 0.0):
```python
# BEFORE (broken): missing tickers get 0.0, polluting signal
forward_returns = np.array([fwd_returns.get(t, 0.0) for t in tickers])

# AFTER (fixed): only include tickers with actual forward returns
mask = [t in fwd_returns for t in tickers]
features = features[mask]
forward_returns = np.array([fwd_returns[t] for t in tickers if t in fwd_returns])
```

### Training Data Assembly

Modified `train_ml_models` worker:

1. Load `historical_scores` for quarters 2009-Q1 through 2024-Q4 (stop 1 year before present)
2. For each quarter: extract 50-feature matrix from `sub_scores`, compute forward returns from PIT prices
3. Concatenate: ~60 quarters x ~2,500 valid tickers = **~150K training samples**
4. Cluster via VAE → train per-cluster LightGBM → validate IC
5. Expected IC: 0.05-0.15 range

### Multi-Seed Validation

Existing pipeline unchanged:
- 20 seeds per cycle
- Distributional gate: median IC>0.15, CV<0.50, worst seed>0.05
- Staged approval flow: `stage → approve → promote`

### Ongoing Training Transition

Post-bootstrap, training transitions to blended data:
- Config: `MARGIN_ML_LIVE_WEIGHT` (default 0.0, gradually increase)
- Late 2027+: 70% PIT-bootstrapped + 30% live-scored, shifting to 100% live
- Prevents discontinuity when switching data sources

## Phase 4: V2 Scoring Deprecation

### Removed

- `full_score()` function from `scoring.py`
- `full_score` from `workers.py` registered functions
- Any CLI commands invoking v2 scoring
- Tests referencing `full_score` (delete or redirect to v3)
- Helper functions only used by v2

### Changed

Worker chain:
- **Before:** `ingest_sweep_complete` → `full_score` → `full_score_v3` → `full_score_v4` → `stage_scores`
- **After:** `ingest_sweep_complete` → `full_score_v3` → `full_score_v4` → `stage_scores`

### Preserved

- All historical v2 data in the database (no data deletion)
- `scores` table schema unchanged
- `full_score_v3` and `full_score_v4` unchanged

### Safety Gate

V2 removal only proceeds after ALL conditions are met:
1. All 4 growth factors implemented and passing tests
2. `historical_scores` table populated (~180K rows)
3. ML training produces IC > 0.05 (non-zero, meaningful signal)
4. At least one full live scoring cycle completes with v3→v4 chain (no v2)

If any gate fails, v2 stays as fallback.

## Testing Strategy

### Growth Factor Tests (engine)
- Golden-value tests: hand-calculated inputs → expected `FactorScore` output (one per module)
- Edge cases: missing fields → `None`, negative values, zero revenue, single-quarter history
- Integration: full `compute_composite_score()` with growth factors, verify weight contribution

### Historical Scorer Tests (engine)
- Unit: `score_universe_at_date()` with synthetic PIT data → verify matches live scoring logic
- Survivorship: delisted ticker appears in early quarters, disappears in later ones
- Determinism: identical inputs produce identical scores

### ML Training Tests (engine)
- Forward returns: tickers without future prices excluded (not defaulted to 0.0)
- Training with data: mock historical scores with known feature/return pairs, verify IC > 0
- Regression: all 92 existing ML tests continue passing

### V2 Deprecation Tests (api)
- Chain: `ingest_sweep_complete` enqueues `full_score_v3` (not `full_score`)
- Negative: `full_score` function no longer exists in module
- End-to-end: full scoring pipeline completes without v2

### Infrastructure
No new test infrastructure needed. Engine tests use pure Python. API tests use aiosqlite. Historical scorer tests use synthetic PIT data dicts.

## Execution Order

Strict sequential phases — each depends on the prior:

1. **Growth Factors** (no dependencies)
2. **Historical Scorer** (depends on growth factors being wired in)
3. **ML Training Fix** (depends on historical scores existing)
4. **V2 Deprecation** (depends on ML validation passing)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Growth factor formulas produce unexpected distributions | Golden-value tests + manual inspection of percentile distributions on PIT data |
| Historical scorer produces different results than live scorer | Shared code path — `score_universe_at_date()` calls the same `compute_composite_score()` |
| PIT data quality issues (missing fields, bad values) | Existing sanitization in PIT pipeline + `None` returns for insufficient data |
| ML IC still low after bootstrap | IC > 0.05 gate before removing v2; iterate on feature engineering if needed |
| V2 removal breaks downstream consumers | Safety gate requires full live cycle success before removal |
