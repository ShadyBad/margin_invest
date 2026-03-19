# Tier D: Engine v2 — ML & Backtesting

Technical design doc for 5 items enhancing the ML pipeline and backtesting framework.

## Cross-Cutting Concern: Unified BlendConfig

D1 (multi-horizon blending), D2 (weight increase), and D4 (VAE enablement) all modify
`blend.py` weights. To avoid rewriting the blend function three times, introduce a
unified config up front:

```python
class BlendConfig(BaseModel):
    """Single source of truth for all blend weights."""
    composite_weight: float = 0.70       # D2 changes this to 0.50
    gbm_weight: float = 0.30            # D2 changes this to 0.50
    vae_weight: float = 0.0             # D4 enables this (0.10 → 0.15)
    vae_shadow_mode: bool = True        # D4: train VAE but don't blend
    horizon_weights: dict[int, float] = {252: 1.0}  # D1 expands this

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> Self:
        total = self.composite_weight + self.gbm_weight + self.vae_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        hw_total = sum(self.horizon_weights.values())
        if abs(hw_total - 1.0) > 1e-6:
            raise ValueError(f"Horizon weights must sum to 1.0, got {hw_total}")
        return self
```

**Implementation order:** Build `BlendConfig` first (as part of D2, the smallest item),
then D1 and D4 extend it rather than introducing their own weight management.

---

## D1: ML Multi-Horizon Training

**Effort: Large**

### Problem

The ML pipeline trains a single model for a single forward-return horizon (252 trading
days / 1 year). Different investment horizons capture different return drivers — a 63-day
model captures mean-reversion and catalyst-driven returns, while a 504-day model captures
secular compounding. Blending multiple horizons produces a more robust signal.

### Current State

**Horizon already parameterized** (default 252) in two places:
- `ml/forward_returns.py:48` — `horizon_days: int = 252` (function parameter, not hardcoded constant)
- `ml/historical_forward_returns.py:31` — `horizon_days: int = 252` (same)

Both functions already accept `horizon_days` as a parameter — the missing piece is a
config object to drive multi-horizon training and an outer loop in `signal_model.py`.

**Training pipeline:**
- `ml/signal_model.py`: Trains one LGBMRegressor per cluster (5 clusters default)
- Walk-forward time-series CV with adaptive n_splits
- LightGBM: 100 estimators, depth 5, learning rate 0.05
- Models serialized via pickle with SHA-256 checksums

**Multi-seed validation** (`ml/seed_validation.py`):
- 20 seeds per cycle
- Gate: median IC > 0.15, CV < 0.50, worst seed > 0.05

### Design

**Step 1: Make horizon configurable**

```python
# ml/config.py (or v3_scoring_config.py)
class MLTrainingConfig(BaseModel):
    horizons: list[int] = [63, 126, 252, 504]  # 3M, 6M, 1Y, 2Y
    # horizon_weights live in BlendConfig (cross-cutting section above),
    # NOT here. MLTrainingConfig controls WHICH horizons to train;
    # BlendConfig.horizon_weights controls HOW to blend predictions at inference.
```

Update `BlendConfig.horizon_weights` default when D1 ships:
```python
horizon_weights: dict[int, float] = {
    63: 0.15,   # Short-term: mean-reversion, catalyst
    126: 0.25,  # Medium: momentum continuation
    252: 0.35,  # Standard: annual compounding
    504: 0.25,  # Long-term: secular growth
}
```

**Step 2: Multi-horizon forward returns**

Add a multi-horizon wrapper that preserves the existing function interface:
```python
# Existing function signature (unchanged):
# compute_forward_returns(scored_tickers, price_data, horizon_days=252, delisted_tickers=None) -> dict[str, float]

def compute_multi_horizon_returns(
    scored_tickers: list[dict],
    price_data: dict[str, list[dict]],
    horizons: list[int] = [252],
    delisted_tickers: set[str] | None = None,
) -> dict[int, dict[str, float]]:
    """Compute forward returns for multiple horizons.
    Returns {horizon_days: {ticker: return}}."""
    return {
        h: compute_forward_returns(scored_tickers, price_data, horizon_days=h, delisted_tickers=delisted_tickers)
        for h in horizons
    }
```

Same approach for `historical_forward_returns.py`.

**Step 3: Train per horizon**

Modify `signal_model.py` training loop:
```python
for horizon in config.horizons:
    for cluster_id in range(n_clusters):
        model = train_cluster_model(
            features=features[cluster_id],
            targets=forward_returns[horizon][cluster_id],
        )
        models[(horizon, cluster_id)] = model
```

**Step 4: Blend multi-horizon predictions**

Extend `blend.py`:
```python
def blend_multi_horizon(
    horizon_predictions: dict[int, float],
    horizon_weights: dict[int, float],
) -> float:
    """Weighted average of predictions across horizons."""
    return sum(
        horizon_weights[h] * horizon_predictions[h]
        for h in horizon_predictions
    )
```

**Step 5: Storage**

Add `horizon_days` column to `ml_model_runs` table:
```sql
ALTER TABLE ml_model_runs ADD COLUMN horizon_days INT DEFAULT 252;
```

Each seed now produces `len(horizons) * n_clusters` models instead of `n_clusters`.

**Step 6: Multi-horizon seed validation**

Each horizon must independently pass the IC gate. A seed fails if any horizon's IC
is below threshold. This prevents a strong 252-day model from masking a terrible
63-day model.

**New `seed_metrics` schema** — currently each seed produces `{"rank_ic": float}`.
Multi-horizon changes this to:
```python
# Per-seed metrics dict
{
    "rank_ic": float,                          # Overall blended IC (backward compat)
    "per_horizon_ic": dict[int, float],        # {63: 0.12, 126: 0.18, 252: 0.22, 504: 0.14}
}
```

**Updated `validate_seed_distribution()`:**
```python
def validate_seed_distribution(
    seed_metrics: list[dict],
    thresholds: SeedValidationThresholds,
) -> SeedValidationResult:
    # Existing gate: overall rank_ic
    rank_ics = [m["rank_ic"] for m in seed_metrics]
    # ... existing checks ...

    # New gate: per-horizon IC (if multi-horizon)
    if "per_horizon_ic" in seed_metrics[0]:
        for horizon in seed_metrics[0]["per_horizon_ic"]:
            horizon_ics = [m["per_horizon_ic"][horizon] for m in seed_metrics]
            if np.median(horizon_ics) < thresholds.min_median_rank_ic:
                return SeedValidationResult(passed=False, reason=f"Horizon {horizon} IC below gate")
```

**DB storage**: Add `per_horizon_rank_ic: Mapped[dict | None]` (JSONB) to `MlModelRun`
to persist per-horizon IC values for audit.

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/ml/forward_returns.py` | Add multi-horizon wrapper that calls existing function per horizon |
| `engine/src/margin_engine/ml/historical_forward_returns.py` | Same multi-horizon wrapper |
| `engine/src/margin_engine/ml/signal_model.py` | Outer horizon loop around cluster training |
| `engine/src/margin_engine/ml/blend.py` | `blend_multi_horizon()` function, uses `BlendConfig.horizon_weights` |
| `engine/src/margin_engine/ml/seed_validation.py` | Accept per-horizon IC dict, validate each independently |
| `api/src/margin_api/db/models.py` | Add `horizon_days` column + `per_horizon_rank_ic` JSONB to `ml_model_runs` |
| `api/src/margin_api/workers.py` | Expand price window dynamically: `timedelta(days=int(max_horizon * 1.5))` |
| `api/alembic/versions/xxx_add_horizon_days.py` | Migration |

### Config/Data Dependencies

- Extended PIT price history for 504-day forward returns (need 2 extra years of data)
- Training time: ~4x current (4 horizons × same work per horizon per seed)
- Storage: ~4x current model count
- **ARQ timeout**: 20 seeds × 4 horizons may exceed 7200s timeout. Consider per-horizon
  parallelization or increasing `train_ml_models` timeout to 14400s

### Test Strategy

- Unit test: multi-horizon forward returns computation
- Unit test: multi-horizon blending with known weights
- Unit test: seed validation fails if any single horizon below IC gate
- Integration test: full training cycle with 2 horizons on test data
- Backward compat: single horizon [252] produces identical results to current

---

## D2: ML Weight Increase (50/50 Blend)

**Effort: Small**

### Problem

The rules/ML blend is 70/30 (`ml_weight=0.30` in `blend.py:9`). As the ML model matures
and demonstrates consistent IC above threshold, increasing to 50/50 captures more of the
ML signal's alpha while keeping rules-based guardrails.

### Current State

```python
# blend.py
def blend_alpha(composite_alpha: float, ml_alpha: float, ml_weight: float = 0.30) -> float:
    return (1.0 - ml_weight) * composite_alpha + ml_weight * ml_alpha
```

```python
# blend_with_vae (for v4+)
def blend_with_vae(composite, gbm, vae, gbm_weight=0.30, vae_weight=0.0):
    remaining = 1.0 - gbm_weight - vae_weight  # Currently 0.70 for composite
    return remaining * composite + gbm_weight * gbm + vae_weight * vae
```

**Current effective blend:** 70% composite / 30% GBM / 0% VAE (both `blend_alpha`
and `blend_with_vae` use 0.30 ML weight — they are consistent).

### Design

**Staged rollout:**

1. **Validate at 0.40**: Change `ml_weight=0.40`, run full 20-seed backtest cycle.
   Gate: median IC > 0.15, Sharpe > 0.70, max drawdown < 35%.

2. **Stage 0.40 for 1 cycle**: Deploy with `ml_weight=0.40` in staged scoring pipeline.
   Monitor live IC vs backtested IC. Gate: live IC within 80% of backtested median.

3. **Validate at 0.50**: If 0.40 passes, backtest 0.50. Same gates.

4. **Deploy 0.50**: Update default, monitor for 1 more cycle.

**For blend_with_vae (v4):**
- Adjust `gbm_weight` from 0.30 to 0.50
- Composite = 1.0 - gbm_weight - vae_weight
- At 50/50 with VAE disabled: composite = 0.50, gbm = 0.50, vae = 0.0

### Implementation Approach

Do NOT change `blend_alpha` / `blend_with_vae` function defaults — this would silently
break callers that rely on the default. Instead:
1. Introduce `BlendConfig` (see cross-cutting section) with `gbm_weight=0.30` initially
2. Refactor `blend_alpha` and `blend_with_vae` to accept `BlendConfig` instead of raw floats
3. All callers pass `BlendConfig` explicitly — no more implicit defaults
4. Staged rollout: change `BlendConfig.gbm_weight` from 0.30 → 0.40 → 0.50 via config,
   not by modifying function signatures

For staged persistence between deployment cycles, wire `BlendConfig` defaults to
`governance_configs` table so weight changes don't require code deploys.

**Note:** `ensemble_override.py` calls `blend_with_vae(gbm_weight=0.60, vae_weight=0.40)`
internally for ML signal blending. This is a SEPARATE blend (GBM vs VAE within the ML
signal) and should NOT use `BlendConfig` — it has its own internal weights.

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/ml/blend.py` | Accept `BlendConfig`, keep old signatures as deprecated wrappers |
| `api/src/margin_api/workers.py` | Pass `BlendConfig` to blend calls in v3/v4 scoring |

### Test Strategy

- Update existing blend tests to use `BlendConfig(gbm_weight=0.50)`
- Test backward compat: `BlendConfig()` with defaults produces identical results to current
- Backtest: compare Sharpe/IC at 0.30, 0.40, 0.50 blend ratios
- Regression: golden-value tests may shift — update expected values

---

## D3: ML 2-Level Override

**Effort: Small**

### Problem

`ensemble_override.py` caps conviction promotion/demotion at 1 level. A stock in the
bottom 5% of ML alpha with very high confidence (>0.80) should be able to demote 2
levels (EXCEPTIONAL → MEDIUM), not just 1 (EXCEPTIONAL → HIGH).

### Current State

**`ml/ensemble_override.py`:**
```python
# Percentile thresholds
TOP_PERCENTILE = 0.85    # Top 15% → promote
BOTTOM_PERCENTILE = 0.15  # Bottom 15% → demote

# Override logic (simplified)
if alpha_percentile >= TOP_PERCENTILE:
    conviction = promote_one_level(conviction)      # MEDIUM → HIGH
elif alpha_percentile <= BOTTOM_PERCENTILE:
    conviction = demote_one_level(conviction)        # HIGH → MEDIUM
```

- Early-exit gate: confidence < 0.60 → no override considered
- Override trigger gate: confidence ≥ 0.75 required for actual promote/demote
- Confidence = 1.0 - clamped_variance

### Design

**Add 2-level tier with higher confidence gate:**

```python
class OverrideConfig(BaseModel):
    # 1-level override (existing — actual code uses 0.75, not 0.60)
    top_1_percentile: float = 0.85        # Top 15%
    bottom_1_percentile: float = 0.15     # Bottom 15%
    min_confidence_1: float = 0.75        # Matches current code (0.60 is only the early-exit)

    # 2-level override (new)
    top_2_percentile: float = 0.95        # Top 5%
    bottom_2_percentile: float = 0.05     # Bottom 5%
    min_confidence_2: float = 0.80        # Much higher confidence required

    max_override_levels: int = 2          # Feature flag: set to 1 to disable
```

**Updated logic:**
```python
def apply_ml_override(conviction, alpha_percentile, confidence, config):
    if config.max_override_levels >= 2 and confidence >= config.min_confidence_2:
        if alpha_percentile >= config.top_2_percentile:
            return promote(conviction, levels=2)
        if alpha_percentile <= config.bottom_2_percentile:
            return demote(conviction, levels=2)

    if confidence >= config.min_confidence_1:
        if alpha_percentile >= config.top_1_percentile:
            return promote(conviction, levels=1)
        if alpha_percentile <= config.bottom_1_percentile:
            return demote(conviction, levels=1)

    return conviction
```

**Conviction level traversal:**
```python
_LEVELS = [CompositeTier.NONE, CompositeTier.MEDIUM, CompositeTier.HIGH, CompositeTier.EXCEPTIONAL]

def promote(tier: CompositeTier, levels: int) -> CompositeTier:
    if tier not in _LEVELS:
        return tier  # Unknown tier — no override (CompositeTier only has NONE/MEDIUM/HIGH/EXCEPTIONAL)
    idx = _LEVELS.index(tier)
    return _LEVELS[min(idx + levels, len(_LEVELS) - 1)]

def demote(tier: CompositeTier, levels: int) -> CompositeTier:
    if tier not in _LEVELS:
        return tier
    idx = _LEVELS.index(tier)
    return _LEVELS[max(idx - levels, 0)]
```

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/ml/ensemble_override.py` | Add 2-level logic, config |

### Test Strategy

- Test 2-level promotion: top 5% + confidence 0.85 → MEDIUM → EXCEPTIONAL
- Test 2-level demotion: bottom 5% + confidence 0.85 → EXCEPTIONAL → MEDIUM
- Test 1-level still works: top 15% + confidence 0.80 → promotes 1 level
- Test confidence gate: bottom 5% + confidence 0.70 → no override (below 0.75 gate)
- Test confidence between gates: confidence 0.76 + top 5% → 1-level only (above 0.75 but below 0.80)
- Test max_override_levels=1 → 2-level disabled (backward compat)
- Test boundaries: NONE can't demote further, EXCEPTIONAL can't promote further

---

## D4: VAE Enablement

**Effort: Medium**

### Problem

The Factor VAE model (`factor_vae.py`) is fully implemented but disabled. Its weight
in the blend is 0.0. The VAE captures latent factor interactions that the GBM model
misses — enabling it should improve ensemble diversity and prediction robustness.

### Current State

**`ml/factor_vae.py`:**
- `FactorVAEConfig.enable = False`
- Architecture: Encoder (features + returns → latent), Predictor (features → latent),
  Decoder (latent → predicted return)
- Training: MSE reconstruction + KL divergence loss
- Metrics: rank_ic, reconstruction_loss, kl_divergence, mean_variance

**`ml/blend.py`:**
- `vae_weight = 0.0` (no-op)
- `blend_with_vae(composite, gbm, vae, gbm_weight=0.30, vae_weight=0.0)`
- Composite gets remaining weight: `1.0 - 0.30 - 0.0 = 0.70`

**No shadow mode concept exists:** `enable` is currently binary — when True, VAE trains
AND blends. Shadow mode (train + log metrics without affecting scores) requires new
infrastructure to decouple training from blending.

### Design

**Phase 1: Shadow Mode (2 training cycles)**

Shadow mode does not currently exist and must be built. The implementation:
- Set `FactorVAEConfig.enable = True` — controls whether VAE **trains**
- `BlendConfig.vae_shadow_mode: bool = True` — controls whether VAE output **affects scores**
- **Single source of truth:** `FactorVAEConfig` owns training; `BlendConfig` owns blending.
  No `shadow_mode` field on `FactorVAEConfig` — avoid dual-config ambiguity.
- When `vae_shadow_mode=True`: VAE trains, metrics are logged to `ml_model_runs`, but
  the caller passes `vae_weight=0.0` to `blend_with_vae` regardless of `BlendConfig.vae_weight`
- Keep `vae_weight = 0.0` (VAE trains but doesn't affect scores)
- Monitor per cycle:
  - `rank_ic`: Must be > 0.05 consistently (lower bar than GBM's 0.15)
  - `reconstruction_loss`: Should decrease over training epochs
  - `kl_divergence`: Should stabilize (not collapse to prior)
  - `mean_variance`: Calibration check (predicted uncertainty ≈ actual error variance)

**Phase 2: Low-Weight Enablement (2 quarters)**

If shadow mode passes:
- Set `shadow_mode = False`, `vae_weight = 0.10`, `gbm_weight = 0.30`, composite = 0.60
- Gate: ensemble IC with VAE > ensemble IC without VAE by at least 0.01
- Monitor live vs backtested IC divergence

**Phase 3: Weight Increase (optional)**

If Phase 2 passes:
- Consider `vae_weight = 0.15` or `0.20`
- Each increase requires a full backtest validation cycle

**Enablement gate criteria:**

| Metric | Shadow Mode Gate | Low-Weight Gate |
|--------|-----------------|-----------------|
| VAE rank_ic | > 0.05 (2 consecutive cycles) | > 0.08 |
| Ensemble IC improvement | N/A | > 0.01 vs GBM-only |
| KL divergence | Stable (not collapsing) | Stable |
| Reconstruction loss | Decreasing | < 0.5 |

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/ml/factor_vae.py` | Change `enable` default to True (no shadow_mode here — that's in BlendConfig) |
| `engine/src/margin_engine/ml/blend.py` | Respect `BlendConfig.vae_shadow_mode`; change `vae_weight` when gate passes |
| `engine/src/margin_engine/ml/signal_model.py` | Log VAE metrics to model run even when shadow_mode=True |

### Test Strategy

- Unit test: VAE trains and produces non-zero predictions
- Unit test: blend_with_vae produces weighted average when vae_weight > 0
- Integration test: full training cycle with VAE enabled, verify metrics logged
- Regression test: vae_weight=0.0 → identical results to current (no change)

---

## D5: Backtest Framework Upgrades

**Effort: Large**

### Problem

The backtest framework starts at 2015 (misses GFC 2008-2009), only supports
monthly/quarterly rebalance, and lacks tail performance metrics. These gaps limit
the ability to validate the scoring system across market regimes and holding periods.

### Current State

**`backtesting/models.py`:**
- `BacktestConfig.start_date = date(2015, 1, 1)`
- `RebalanceFrequency`: MONTHLY, QUARTERLY
- `SelectionMode`: TOP_PERCENTILE, CONVICTION_MOS, OPTIMIZED

**`backtesting/simulator.py`** (WalkForwardSimulator):
- Walk-forward monthly/quarterly rebalance
- Equal-weight or DRO-optimized allocation
- Turnover tracking, cost drag computation

**`backtesting/metrics.py`** (PerformanceCalculator):
- CAGR, Sharpe, Sortino, Max Drawdown, Win Rate, Information Ratio
- Gross metrics (before costs), cost drag in bps
- Pass thresholds: Excess CAGR > 3%, Sharpe > 0.7, Sortino > 1.0,
  Max DD < 35%, Win Rate > 55%, IR > 0.5

**PIT data:** 2009-present (from EDGAR backfill). Price data: 2009-present.

### Design

**Enhancement 1: Extend to 2005 (include GFC)**

- Requires PIT data backfill to 2005 (EDGAR XBRL available from ~2008, pre-XBRL
  financials from other sources like Compustat)
- Alternative: Use EDGAR XBRL from 2008 + price data from 2005 (limited pre-2008
  fundamental data, use what's available)
- Extend `BacktestConfig.start_date` default to `date(2008, 1, 1)` initially
- Long-term: explore Compustat/FactSet API for pre-2008 fundamentals

**Enhancement 2: Multi-Holding-Period Support**

Add holding period independent of rebalance frequency:
```python
class BacktestConfig(BaseModel):
    holding_periods: list[int] = [63, 126, 252]  # 3M, 6M, 1Y in trading days
    # Each holding period produces separate return series
```

Modify `simulator.py` to track cohort returns via a new data model:

```python
class CohortRecord(BaseModel):
    """A group of stocks selected at one rebalance point, tracked over a holding period."""
    entry_date: date
    exit_date: date
    holding_period_days: int          # 63, 126, or 252
    tickers: list[str]
    weights: dict[str, float]         # ticker → allocation weight
    cohort_return: float              # Realized return over holding period
    benchmark_return: float           # Benchmark return over same period

class HoldingPeriodResult(BaseModel):
    """Aggregated results for a single holding period across all cohorts."""
    holding_period_days: int
    cohorts: list[CohortRecord]
    metrics: PerformanceMetrics       # Computed from cohort returns
```

**Aggregation rule:** Overlapping cohorts are independent — each produces its own
return series. `PerformanceMetrics` is computed per holding period by treating each
cohort's return as one observation. `BacktestResult` gains a new field:
`per_holding_period: dict[int, HoldingPeriodResult]`. The existing `MonthlySnapshot`-
based portfolio NAV is unaffected — it continues to track the default rebalance-
frequency return series.

**Enhancement 3: Tail Performance Metrics**

Add to `metrics.py`:
```python
class TailMetrics(BaseModel):
    capture_rate_5x: float   # % of picks that returned >= 5x
    capture_rate_10x: float  # % of picks that returned >= 10x
    max_single_return: float
    avg_top_decile_return: float
    skewness: float          # Return distribution skewness (positive = fat right tail)
```

**Enhancement 4: Regime-Conditional Pass Thresholds**

Regime classification already exists in `backtesting/regime_classifier.py`:
- `MarketRegimeHistorical` enum: BULL, BEAR, SIDEWAYS, CRISIS
- `classify_regime()` uses drawdown + VIX + NBER recession logic
- `segment_by_regime()` groups returns by regime

What's missing is regime-conditional **pass thresholds** — currently validation
applies the same gates regardless of market regime. Add:
```python
class RegimePassThresholds(BaseModel):
    bull: PassThreshold     # Less strict (rising tide lifts all boats)
    bear: PassThreshold     # Most strict (alpha generation matters most)
    sideways: PassThreshold # Standard
```

Wire `segment_by_regime()` output into `validation.py` so each regime's returns
are validated against its own thresholds.

**Enhancement 5: Multiple Benchmarks**

Add benchmark options beyond S&P 500:
```python
class BenchmarkStrategy(StrEnum):
    SP500 = "sp500"
    SP500_EQUAL_WEIGHT = "sp500_ew"
    RUSSELL_1000 = "russell_1000"
    RUSSELL_1000_VALUE = "russell_1000_value"
```

Compute excess returns and IC vs each benchmark.

**Benchmark data sourcing:** Use ETF proxies via yfinance:
- SPY (S&P 500), RSP (S&P 500 Equal Weight), IWB (Russell 1000), IWD (Russell 1000 Value)
- ETF proxies introduce tracking error (~10-30 bps/yr) — acceptable for backtesting
- Note this in `BenchmarkStrategy` docstring so users understand the limitation

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/backtesting/models.py` | New config fields, TailMetrics, RegimePassThresholds, CohortRecord, HoldingPeriodResult |
| `engine/src/margin_engine/backtesting/simulator.py` | Multi-holding-period cohort tracking |
| `engine/src/margin_engine/backtesting/metrics.py` | Tail metrics computation |
| `engine/src/margin_engine/backtesting/validation.py` | Regime-conditional pass thresholds |
| `api/src/margin_api/cli.py` | Update backtest CLI to support new options |

### Config/Data Dependencies

- PIT price data back to 2005-2008 (requires price-backfill extension)
- Benchmark ETF data (SPY, RSP, IWB, IWD) — historical daily prices via yfinance
- Current PIT data starts at 2009 — GFC start (2007) requires additional backfill

### Test Strategy

- Unit test: tail metrics with known return distribution
- Unit test: regime-conditional thresholds apply correct gates per regime (classifier already tested)
- Unit test: multi-holding-period cohort return calculation
- Integration test: full backtest with GFC period, verify regime-conditional thresholds
- Backward compat: default config produces identical results to current
