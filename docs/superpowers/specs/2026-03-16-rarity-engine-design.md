# Rarity Engine: Once-in-a-Generation Opportunity Detection

**Date:** 2026-03-16
**Status:** Design approved
**Author:** Brandon + Claude

## Overview

The Rarity Engine is an orthogonal diagnostic layer built on top of the existing v4 scoring pipeline. It answers: "How unusual is this specific combination of factor scores, relative to the cross-sectional distribution of all scored securities?"

This is NOT a replacement for the scoring system. It enriches scores with rarity metadata.

**Key decisions made during design:**
- Standalone regime classification (not reusing existing 4-axis `RegimeState`)
- 4 universal pillars only (quality, value, momentum, growth) for cross-stock comparison
- Historical rarity accumulates from first run (no backfill from PIT data)
- Smart money uses extended `FactorScore.metadata` (not direct 13F queries)
- Parallel sidecar pipeline integration (not inline chain link)

---

## 1. Definition Layer

### "Once-in-a-Generation" (Computable)

A stock qualifies as "once-in-a-generation" when its joint factor profile occurs in fewer than 1% of all stock-quarters observed historically.

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Joint rarity percentile | >= 97th | Only 3% of universe achieves this combination |
| Pillar consistency floor | All available pillars >= 60th pctl | No weak link allowed |
| Min pillars >= 80th pctl | >= 3 of 4 (or >= 2 of 3 for Track B) | Must excel broadly |
| Historical frequency | < 2% of quarters | This pattern genuinely rare over time |
| Composite raw score | >= 76 (EXCEPTIONAL tier) | Must clear existing quality bar |

```python
is_generational = (
    joint_rarity_pctl >= 97
    and min_pillar >= 60
    and pillars_above_80 >= (3 if n_pillars == 4 else 2)
    and hist_freq < 0.02
    and composite_raw >= 76
)
```

Base rate: ~0.5-1.5% of universe at any time = 15-50 stocks before further filtering.

**Track B adaptation:** Mispricing-track stocks (`winning_track="mispricing"`) have a different pillar structure. In `composite_mispricing.py`, Track B produces:
- `quality` = quality_floor (populated, meaningful)
- `value` = value (populated, meaningful)
- `momentum` = empty `FactorBreakdown(weight=0.0, sub_scores=[])` — `average_percentile` returns 0.0 (NOT a real signal)
- `growth` = `None`
- `catalyst` = populated (meaningful, but not a universal pillar)

**Pillar extraction for rarity:** For Track B stocks, the 3 meaningful pillars are `quality`, `value`, and `catalyst`. The dummy `momentum` (percentile 0.0) is excluded — including it would severely distort convergence and joint rarity. Gates adjust: `min_pillar` operates on 3 pillars, `pillars_above_80` threshold drops to 2 of 3.

### "High-Conviction" (Computable)

Conviction measures confidence in the signal, not just signal strength.

| Dimension | Metric | Weight |
|-----------|--------|--------|
| Cross-factor agreement | Pillar consistency score (min/max ratio) | 0.25 |
| Temporal persistence | Signal strengthening over 2+ quarters | 0.20 |
| Smart money alignment | Insider buy + institutional accumulation | 0.20 |
| Valuation depth | Margin of safety >= 25% | 0.20 |
| Catalyst proximity | Near-term catalyst identified | 0.15 |

```python
conviction_score = (
    0.25 * consistency
    + 0.20 * persistence
    + 0.20 * smart_money
    + 0.20 * valuation_depth
    + 0.15 * catalyst_proximity
)
```

Each dimension scaled 0-100. Final `conviction_score >= 70` = "high conviction."

---

## 2. Signal Architecture

### 2A. Cross-Factor Convergence Signal

**Problem:** Averaging percentiles hides disagreement. Q=95, V=45, M=90, G=50 averages 70 but is a split decision.

**File:** `engine/src/margin_engine/rarity/convergence.py`

```python
def compute_convergence(pillar_percentiles: list[float]) -> float:
    """Score 0-100 measuring how aligned pillars are at HIGH levels.

    Algorithm:
    1. Compute min/max ratio: min(pillars) / max(pillars)
       - Perfect convergence (all equal): ratio = 1.0
       - Divergent: ratio -> 0
    2. Penalize if floor is below 60th percentile (convergence on mediocrity doesn't count)
    3. Scale to 0-100
    """
    floor = min(pillar_percentiles)
    ceiling = max(pillar_percentiles)
    ratio = floor / ceiling if ceiling > 0 else 0
    # Ramp: 0 at 60th pctl, 1.0 at 100th pctl. Below 60 = zero convergence credit.
    floor_penalty = max(0, (floor - 60) / 40)
    convergence = ratio * floor_penalty * 100
    return round(convergence, 2)
```

Operates on meaningful pillars only: 4 for Track A (quality, value, momentum, growth), 3 for Track B (quality, value, catalyst). See Track B adaptation in Section 1.

### 2B. Joint Rarity Signal (Core)

**Problem:** Individual high percentiles are not rare. Simultaneously high percentiles across multiple independent dimensions IS rare.

**File:** `engine/src/margin_engine/rarity/joint_rarity.py`

```python
def compute_joint_rarity(
    factor_matrix: np.ndarray,  # (N_stocks, F_factors) percentile ranks
    target_idx: int,
) -> float:
    """Empirical joint CDF -- no parametric assumptions.

    Count what fraction of universe has ALL factor percentiles
    simultaneously >= target's percentiles.

    Returns rarity_percentile (0-100): higher = rarer.
    """
    target = factor_matrix[target_idx]
    dominated = (factor_matrix >= target).all(axis=1)
    frac_dominating = dominated.sum() / len(factor_matrix)
    return round((1 - frac_dominating) * 100, 2)
```

**Complexity:** O(N * F) per stock, O(N^2 * F) for full universe. N=3000, F=4: ~36M comparisons, <1 second with numpy broadcasting.

**Factor selection:** Use only the 4 pillar `average_percentile` values for a uniform comparison surface. This avoids the cross-track alignment problem where different winning tracks have structurally different individual factors (e.g., `gross_profitability` vs `dcf_margin_of_safety` cannot share a matrix column).

**Pillar-to-column mapping:**
- **Track A (compounder):** quality, value, momentum, growth → columns 0-3
- **Track B (mispricing):** quality, value, catalyst, `NaN` → columns 0-2, column 3 masked

For Track B stocks, the growth column is `NaN`. The joint rarity comparison for Track B stocks uses masked comparison: only columns 0-2 participate in the "all factors >= target" test. This means Track B stocks are compared on 3 dimensions (slightly easier to dominate), which is a known trade-off — accepted because Track B is ~15% of the universe and the convergence/gate cascade provides additional filtering.

### 2C. Historical Rarity Signal

**Problem:** Is today's factor profile unusual vs history, or does this happen every quarter?

**File:** `engine/src/margin_engine/rarity/historical_rarity.py`

**Data accumulation strategy:** No backfill. The `rarity_distribution_snapshots` table starts accumulating from the first rarity run. Historical frequency returns 50 (neutral) until >= 4 quarters of data exist. The 15% weight in the composite formula limits impact during the ramp-up period.

```python
def compute_historical_frequency(
    current_signature: str,      # e.g., "Q90+V85+M80+G75" (bucketed to nearest 5)
    historical_snapshots: list[RarityDistributionSnapshot],
    lookback_quarters: int = 40,
) -> float:
    """What fraction of historical stock-quarters match this signature pattern?

    Bucket each pillar percentile to nearest 5 (reduce granularity).
    Count matches across all historical snapshots.
    Apply exponential decay (half-life = 20 quarters).
    Returns 0-100 rarity score (100 = never seen before).
    """
```

### 2D. Regime Alignment Signal

**Problem:** A "rare value opportunity" in a crisis regime is different from one in a euphoria regime.

**File:** `engine/src/margin_engine/rarity/regime.py`

Standalone regime classification (independent of the existing `RegimeState` in `engine/src/margin_engine/regime/`). This is a deliberate design choice — the rarity regime is simpler (4 classes vs 4 axes) and purpose-built for historical comparison.

**Data sources** (extend `api/src/margin_api/data/fred_client.py`):
- Yield curve slope: `DGS10` minus `DGS2` (FRED) — 10Y-2Y Treasury spread in percentage points
- Credit spread: `BAA10Y` (FRED) — Moody's Baa Corporate Bond Yield Relative to 10-Year Treasury, already a spread in percentage points. No subtraction needed.
- VIX level: from yfinance (`^VIX`) — separate from FRED, same 24h cache pattern

**Note:** VIX is fetched via yfinance, not FRED. The `fred_client.py` file is being repurposed as a general macro data fetcher. Consider renaming to `macro_data_client.py` during implementation.

**Regime classification** — evaluated in precedence order (first match wins):

| Regime | Conditions (exact thresholds) | Favored Opportunity Types |
|--------|------|--------------------------|
| CRISIS | VIX > 35 AND Baa-10Y spread > 2.5pp | Deep Value, Turnaround |
| CONTRACTION | Yield curve slope < 0 (inverted) OR VIX > 25 | Value, Mispricing |
| LATE_CYCLE | Yield curve slope between -0.2 and 0.5 AND 15 <= VIX <= 25 | Quality, Capital Allocation |
| EXPANSION | (default — none of the above) | Growth, Momentum |

Boundary conditions: VIX thresholds use strict inequalities (`>`, not `>=`). Yield curve slope is in percentage points (e.g., 0.5 = 50bp). The Baa-10Y spread threshold of 2.5pp (~250bp) corresponds to historical stress levels; during 2008-2009 it reached 6pp+, during COVID it briefly hit 3.5pp.

**Regime-conditional rarity:** Historical analogs only compare against the same regime classification. Activates once >= 2 quarters of data per regime accumulate.

### 2E. Temporal Quality Momentum

**Problem:** Is the company getting fundamentally better or just mean-reverting?

**File:** `engine/src/margin_engine/rarity/quality_momentum.py`

Compares current pillar percentiles vs trailing 4-quarter average from stored `V4Score.detail` JSONB. Returns 50 (neutral) if < 2 prior quarters exist.

```python
def compute_quality_momentum(
    current_pillars: dict[str, float],
    historical_pillars: list[dict[str, float]],  # last 4 quarters
) -> float:
    """Rate of change in fundamental quality. 0-100 scale.

    Positive = improving, 50 = stable, < 50 = deteriorating.
    Requires 2+ quarters of consecutive improvement to score > 70.
    """
```

### 2F. Smart Money Convergence

**Problem:** Existing factors output a single percentile. Need intermediate signals for richer convergence detection.

**File:** `engine/src/margin_engine/rarity/smart_money.py`

**Model change:** Add `metadata: dict[str, Any] | None = None` to `FactorScore` in `engine/src/margin_engine/models/scoring.py`. Backward-compatible — existing code that doesn't populate it gets `None`.

**Factor extensions:**
- `institutional_accumulation.py` populates `metadata` with: `n_quality_institutions_adding`, `n_consecutive_quarters_accumulated`, `manager_tier_breakdown`
- `insider_cluster.py` populates `metadata` with: `cluster_buy_detected`, `n_distinct_insiders`, `total_buy_value`

```python
def compute_smart_money_convergence(
    accumulation_percentile: float,
    insider_cluster_percentile: float,
    accumulation_metadata: dict | None,
    insider_metadata: dict | None,
) -> float:
    """0-100 score. Rare events get extreme scores:

    - Institutional accumulation alone: max 60
    - + insider buying: max 80
    - + 3+ quality institutions: max 90
    - + 2+ consecutive quarters: max 100
    """
```

**Metadata propagation path:** `institutional_accumulation()` and `insider_cluster_score()` populate `metadata` on their returned `FactorScore` → these flow into `FactorBreakdown.sub_scores` → into `CompositeScore` → `CompositeScore.model_dump(mode="json")` → `V4Score.detail` JSONB. The rarity engine reads metadata by traversing: `detail["quality"]["sub_scores"][i]["metadata"]` (or equivalent pillar path). The rarity engine must handle `metadata=None` for all historical V4Score rows (pre-metadata) and for any factor function that doesn't populate it. All metadata reads use `.get()` with defaults.

---

## 3. Rarity Scoring Formula

### Composite Rarity Score

```python
rarity_score = (
    0.35 * joint_rarity_percentile +
    0.25 * convergence_score +
    0.15 * historical_rarity_score +
    0.10 * quality_momentum +
    0.10 * smart_money_convergence +
    0.05 * regime_alignment
)
```

**Early-run behavior:** Historical rarity returns 50 (neutral) until >= 4 quarters accumulate. This effectively makes the formula a 5-signal system initially, with ~7.5 points of "dead weight" from the neutral historical signal. This is conservative in the right direction — rarity scores are slightly dampened until the historical baseline strengthens.

### Anti-Dilution

The key insight: `joint_rarity_percentile` (0.35) measures the *combination*, not individual factors. A stock with Q=80, V=80, M=80, G=80 is rarer than Q=99, V=50, M=80, G=60. The `convergence_score` (0.25) further penalizes split decisions. Together (60% of weight), "broadly excellent" is rewarded over "narrowly exceptional."

### Gate Cascade

Gates run in order — fail any = excluded:

| Gate | Criterion | Track B Adjustment |
|------|-----------|-------------------|
| 1 | `COMPOSITE_TIER` = EXCEPTIONAL or HIGH | Same |
| 2 | `MIN_PILLAR` >= 60th percentile | Min of 3 available pillars |
| 3 | `CONVERGENCE_SCORE` >= 50 | Computed over 3 pillars |
| 4 | `RARITY_SCORE` >= 80 | Same |
| 5 | Hard cap: top 30 by rarity_score | Same |
| 6 | Sector cap: max 40% per sector | Drop lowest-rarity from over-concentrated sectors |

**Note:** Gates 1-6 produce the **rarity-scored universe** (~30 stocks). The `is_generational` flag is a stricter subset within this list, requiring `composite_raw >= 76` (EXCEPTIONAL only) plus all 5 criteria from Section 1. Gate 1 intentionally allows HIGH-tier stocks (>= 71) through so they receive rarity scores — only the `is_generational` boolean requires EXCEPTIONAL.

Expected survival rates:
- Gate 1: ~3,500 -> ~500
- Gate 2: ~500 -> ~200
- Gate 3: ~200 -> ~80
- Gate 4: ~80 -> ~25-40
- Gate 5: ~25-40 -> 30 max
- Gate 6: Sector rebalancing within the 30

---

## 4. System Design

### Pipeline Integration: Parallel Sidecar

```
full_score_v4 ──→ stage_scores ──→ [approval] ──→ publish_scores
      │                              (UNCHANGED)
      └──→ compute_rarity (parallel, independent)
               ├─ Read V4Score rows + detail JSONB
               ├─ Build factor matrix (N×F numpy array)
               ├─ Compute joint rarity, convergence, quality momentum
               ├─ Fetch regime data (VIX, yield curve, credit spreads)
               ├─ Read FactorScore.metadata for smart money signals
               ├─ Write rarity_scores table
               └─ Write rarity_distribution_snapshots
```

`full_score_v4` enqueues both `stage_scores` and `compute_rarity` as independent ARQ jobs. The existing `stage_scores` chain is **completely untouched**. If `compute_rarity` fails, no other job is affected.

**Change to `full_score_v4`:** Add one `redis.enqueue_job("compute_rarity", ...)` call alongside the existing `stage_scores` enqueue. ~3 lines of new code in the worker.

### New Database Tables

**`rarity_scores`** — per-ticker per-scoring-run rarity metrics:

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| asset_id | FK -> assets.id | indexed |
| scored_at | DateTime(tz=True) | indexed |
| rarity_score | Float | 0-100 composite rarity |
| joint_rarity_pctl | Float | empirical joint CDF |
| convergence_score | Float | pillar consistency |
| historical_frequency | Float | how often this pattern occurs |
| quality_momentum | Float | fundamental trajectory |
| smart_money_score | Float | institutional + insider |
| regime_alignment | Float | macro fit |
| combination_signature | String(30) | e.g., "Q92+V85+M78+G88" |
| regime | String(20) | current regime label |
| conviction_score | Float | 0-100 high-conviction composite (Section 1) |
| is_generational | Boolean | passes all generational gates |
| detail | JSONVariant | full breakdown incl. per-dimension scores |
| universe_size | Integer | |

Indexes: `(asset_id, scored_at)`, `scored_at`

**`rarity_distribution_snapshots`** — distribution summaries per run:

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| scored_at | DateTime(tz=True) | indexed |
| scope | String(30) | "universe" or sector name |
| factor_name | String(50) | |
| n_obs | Integer | |
| percentiles | JSONVariant | {p5, p10, p25, p50, p75, p90, p95} |
| mean | Float | |
| std | Float | |

Named `rarity_distribution_snapshots` (not `factor_distribution_snapshots`) to avoid confusion with the existing `sector_distribution_snapshots` table.

### Engine Model Change

In `engine/src/margin_engine/models/scoring.py`, add to `FactorScore`:

```python
metadata: dict[str, Any] | None = None
```

Backward-compatible. Existing `model_dump()` serialization includes it as `null`.

### New Engine Modules

All in `engine/src/margin_engine/rarity/`:

| File | Purpose | Complexity |
|------|---------|-----------|
| `__init__.py` | Module init, exports | S |
| `models.py` | Pydantic models: RarityResult, RarityConfig | S |
| `joint_rarity.py` | Empirical joint CDF computation | M |
| `convergence.py` | Cross-factor convergence scoring | S |
| `historical_rarity.py` | Historical frequency analysis | M |
| `quality_momentum.py` | Temporal quality trajectory | S |
| `smart_money.py` | Smart money convergence scoring | S |
| `regime.py` | Regime classification + alignment | M |
| `combination_signature.py` | Human-readable factor fingerprint | S |
| `rarity_engine.py` | Orchestrator: runs all dimensions, produces RarityResult | M |

### API Changes

**New file:** `api/src/margin_api/routes/rarity.py`
- `GET /api/v1/rarity/{ticker}` — full rarity breakdown for a ticker
- `GET /api/v1/rarity/picks` — top N generational picks (the 10-30 list)

**Modified:** `api/src/margin_api/schemas/scores.py`
- Add to `ScoreResponse`: `rarity_score: float | None`, `is_generational: bool | None`, `combination_signature: str | None`

**Modified:** `api/src/margin_api/app.py`
- Register rarity router

### Worker Integration

**New function:** `compute_rarity` in `api/src/margin_api/workers.py`
- Registered as ARQ function
- 300s timeout
- Creates `JobRun` record (job_type="compute_rarity")
- Reads all V4Score rows for the current `scored_at`
- Builds factor matrix from `detail` JSONB
- Runs rarity orchestrator
- Writes `rarity_scores` and `rarity_distribution_snapshots` rows
- Fails gracefully — logs error, marks job failed, no downstream impact

**Modified:** `full_score_v4` in `api/src/margin_api/workers.py`
- Add `redis.enqueue_job("compute_rarity", pipeline_id, job_id, scored_at_iso, ...)` alongside the existing `stage_scores` enqueue

### Macro Data Client

**Renamed:** `api/src/margin_api/data/fred_client.py` → `api/src/margin_api/data/macro_data_client.py` (existing `fetch_shiller_cape()` moves too; update imports in `cli.py`).

New async functions (same 24h cache pattern):
- `fetch_yield_curve_slope()` — `DGS10` minus `DGS2` (FRED), returns spread in percentage points
- `fetch_credit_spread()` — `BAA10Y` (FRED), Baa-Treasury spread, already a spread value
- `fetch_vix()` — from yfinance (`^VIX`), current VIX level

---

## 5. Validation Layer

### Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Conditional Rank IC | > 0.05 | Among same-tier stocks, rarity predicts returns |
| Hit rate (12-month) | > 55% | More than half beat benchmark |
| Median excess return (12m) | > 5% | Meaningful alpha, not noise |
| Max drawdown | < 40% | Concentrated portfolio risk bound |
| Rarity signal stability | IC CV < 0.60 | Signal not regime-dependent |
| False positive rate | < 30% | < 30% of "rare" picks underperform benchmark |

### Anti-Overfitting Protocol

1. **Conditional testing:** Test rarity's value WITHIN each conviction tier, not across tiers
2. **Minimum 30 quarterly rebalances** in walk-forward before trusting signal
3. **Parameter stability:** Sweep rarity weights +/-20% — if Rank IC sign flips, signal is fragile
4. **Regime partitioning:** Must show positive IC in at least 3 of 4 regime types
5. **Report confidence intervals:** With N=25 picks, SE ~ return_std / sqrt(25). If CI spans zero, report "inconclusive"

### Critical Decision Gate

**Before building frontend (Phase 4):** Run the conditional Rank IC test. If rarity's conditional IC is not significantly positive (> 2 standard errors from zero), pivot rarity to a pure transparency feature — "here's how unusual your portfolio is" rather than "rare stocks outperform."

Transparency has value independent of predictive power.

---

## 6. Failure Modes

| Failure | Detection | Mitigation |
|---------|-----------|------------|
| Rarity job never runs | No `rarity_scores` rows for latest `scored_at` | Alert; dashboard shows "rarity pending" or omits badges |
| Stale distributions | Distribution snapshot age > 7 days | Alert; fall back to last valid snapshot |
| Data gaps | `data_coverage < 0.6` on scored ticker | Exclude from rarity computation; set `rarity_score = null` |
| Regime misclassification | Regime flips > 2x per quarter | Use 20-day rolling regime, require 5+ days stability |
| False positives | "Rare" stock with any pillar < 40th pctl | Gate 2 (min_pillar >= 60) eliminates |
| Overfitting | Conditional IC sign-flips across regimes | Parameter stability sweep; report "inconclusive" |
| Computation timeout | `compute_rarity` exceeds 300s | Hard timeout; pipeline unaffected (sidecar) |
| Factor crowding | Top 30 rarity picks cluster in 1-2 sectors | Gate 6: sector concentration cap at 40% |
| Survivorship bias | Historical analogs only match surviving stocks | Use `pit_universe_memberships` with delisted tickers |

---

## 7. Hard Critique

### What this design gets right:
- Rarity is orthogonal to scoring (doesn't corrupt existing pipeline)
- Parallel sidecar means zero risk to production scoring
- Empirical joint CDF avoids parametric assumptions
- Convergence scoring penalizes "one great factor, rest mediocre"
- Regime conditioning prevents cross-regime confusion
- Graceful degradation at every level

### Where this design is likely to fail:
- **Complexity theater risk:** Rarity score may correlate with `composite_raw_score`. The conditional Rank IC test (Phase 3) is the critical gate.
- **Small sample statistics:** With 10-30 picks, performance claims are statistically weak. Must report confidence intervals honestly.
- **The "rare = good" assumption:** Rarity measures unusualness, not quality. Gate 1 (EXCEPTIONAL/HIGH) and Gate 2 (min_pillar >= 60) guard against rare-but-terrible, but edge cases will slip through.
- **Historical frequency is backward-looking:** A factor combination that was "rare" historically may become common. Exponential decay (half-life 20 quarters) mitigates but doesn't eliminate.
- **FactorScore.metadata coupling:** Extending scoring models to serve rarity creates a dependency. If metadata format changes, rarity breaks. Mitigation: rarity reads metadata defensively with `.get()` and defaults.

---

## 8. Frontend Components

Contingent on Phase 3 decision gate (signal vs transparency).

New in `web/src/components/rarity/`:

| Component | Purpose |
|-----------|---------|
| `rarity-badge.tsx` | Inline badge: "Top 2% Rare" with color coding |
| `rarity-radar.tsx` | Radar chart: 6-axis rarity dimension visualization |
| `generational-picks.tsx` | Dedicated page/section: the 10-30 generational list |
| `combination-signature.tsx` | Visual "Q92+V85+M78+G88" fingerprint display |
| `rarity-detail-panel.tsx` | Full breakdown panel for asset detail page |

---

## 9. Implementation Phases

### Phase 1: Foundation (L — ~3-4 days)
Core rarity computation + pipeline integration.

**Deliverables:**
- `FactorScore.metadata` field addition (`engine/src/margin_engine/models/scoring.py`)
- Pydantic models: `RarityResult`, `RarityConfig` -> `engine/src/margin_engine/rarity/models.py`
- Joint rarity -> `engine/src/margin_engine/rarity/joint_rarity.py`
- Convergence -> `engine/src/margin_engine/rarity/convergence.py`
- Combination signature -> `engine/src/margin_engine/rarity/combination_signature.py`
- Rarity orchestrator -> `engine/src/margin_engine/rarity/rarity_engine.py`
- ORM models: `RarityScore`, `RarityDistributionSnapshot` -> `api/src/margin_api/db/models.py`
- Alembic migration
- `compute_rarity` ARQ worker (parallel sidecar)
- Add `compute_rarity` enqueue to `full_score_v4` (~3 lines)
- Golden-value tests -> `engine/tests/rarity/`

### Phase 2: Additional Signals + API (M — ~2-3 days)
**Deliverables:**
- Quality momentum -> `engine/src/margin_engine/rarity/quality_momentum.py`
- Smart money convergence -> `engine/src/margin_engine/rarity/smart_money.py`
- Extend `institutional_accumulation.py` and `insider_cluster.py` to populate `FactorScore.metadata`
- Regime alignment -> `engine/src/margin_engine/rarity/regime.py`
- Historical rarity -> `engine/src/margin_engine/rarity/historical_rarity.py`
- FRED client extensions -> `api/src/margin_api/data/fred_client.py`
- API routes -> `api/src/margin_api/routes/rarity.py`
- API schemas -> `api/src/margin_api/schemas/rarity.py`
- `ScoreResponse` enrichment -> `api/src/margin_api/schemas/scores.py`
- Route tests -> `api/tests/test_rarity_routes.py`

### Phase 3: Backtesting Validation (L — ~3-4 days)
**Critical: must complete before Phase 4.**

**Deliverables:**
- Rarity as backtesting dimension in walk-forward engine
- Conditional Rank IC test (within same conviction tier)
- Parameter stability sweep (weights +/-20%)
- Regime-partitioned IC report
- **Decision:** rarity is a signal feature OR transparency-only feature

### Phase 4: Frontend (M — ~2-3 days)
Depends on Phase 3 decision.

**Deliverables:**
- RarityBadge, RarityRadar, GenerationalPicks, CombinationSignature, RarityDetailPanel
- Integration with dashboard and asset detail page
- Frontend tests

### Phase 5: Monitoring + Refinement (S — ~1-2 days)
**Deliverables:**
- Rarity distribution stability monitoring
- Sector concentration alerting
- Admin dashboard for rarity config
- GovernanceEvent logging for rarity regime shifts

---

## 10. Verification

- **Unit tests:** `uv run pytest engine/tests/rarity/ -v` — golden-value tests for all 6 signals
- **Integration tests:** `uv run pytest api/tests/test_rarity_routes.py -v` — API endpoints
- **Pipeline test:** Run `compute_rarity` worker against test DB; verify `rarity_scores` rows written
- **Sidecar test:** Verify `full_score_v4` enqueues both `stage_scores` and `compute_rarity`
- **Backtest validation:** Conditional Rank IC report across available quarterly rebalances
- **Frontend tests:** `cd web && npx vitest run src/components/rarity/`
- **Performance:** `compute_rarity` completes in < 30 seconds for 3,000 stock universe (historical rarity snapshots batch-loaded into memory before per-stock loop; FRED/VIX fetches cached with 24h TTL so no network I/O in steady state)
