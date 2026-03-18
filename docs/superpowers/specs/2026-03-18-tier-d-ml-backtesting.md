# Tier D: Engine v2 — ML & Backtesting

Technical design doc for 5 items enhancing the ML pipeline and backtesting framework.

---

## D1: ML Multi-Horizon Training

**Effort: Large**

### Problem

The ML pipeline trains a single model for a single forward-return horizon (252 trading
days / 1 year). Different investment horizons capture different return drivers — a 63-day
model captures mean-reversion and catalyst-driven returns, while a 504-day model captures
secular compounding. Blending multiple horizons produces a more robust signal.

### Current State

**Horizon hardcoded** in two places:
- `ml/forward_returns.py:48` — `horizon_days: int = 252`
- `ml/historical_forward_returns.py:31` — `horizon_days: int = 252`

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
    horizon_weights: dict[int, float] = {
        63: 0.15,   # Short-term: mean-reversion, catalyst
        126: 0.25,  # Medium: momentum continuation
        252: 0.35,  # Standard: annual compounding
        504: 0.25,  # Long-term: secular growth
    }
```

**Step 2: Multi-horizon forward returns**

Extend `forward_returns.py`:
```python
def compute_forward_returns(
    prices: pd.DataFrame,
    horizons: list[int] = [252],  # Backward compatible default
) -> dict[int, pd.Series]:
    """Compute forward returns for multiple horizons.
    Returns {horizon_days: pd.Series of returns}."""
```

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

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/ml/forward_returns.py` | Multi-horizon returns |
| `engine/src/margin_engine/ml/historical_forward_returns.py` | Multi-horizon returns |
| `engine/src/margin_engine/ml/signal_model.py` | Train per horizon per cluster |
| `engine/src/margin_engine/ml/blend.py` | Multi-horizon blending |
| `engine/src/margin_engine/ml/seed_validation.py` | Per-horizon IC validation |
| `api/src/margin_api/db/models.py` | Add horizon_days column to ml_model_runs |
| `api/alembic/versions/xxx_add_horizon_days.py` | Migration |

### Config/Data Dependencies

- Extended PIT price history for 504-day forward returns (need 2 extra years of data)
- Training time: ~4x current (4 horizons × same work per horizon per seed)
- Storage: ~4x current model count

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
def blend_with_vae(composite, gbm, vae, gbm_weight=0.60, vae_weight=0.0):
    remaining = 1.0 - gbm_weight - vae_weight  # Currently 0.40 for composite
    return remaining * composite + gbm_weight * gbm + vae_weight * vae
```

### Design

**Staged rollout:**

1. **Validate at 0.40**: Change `ml_weight=0.40`, run full 20-seed backtest cycle.
   Gate: median IC > 0.15, Sharpe > 0.70, max drawdown < 35%.

2. **Stage 0.40 for 1 cycle**: Deploy with `ml_weight=0.40` in staged scoring pipeline.
   Monitor live IC vs backtested IC. Gate: live IC within 80% of backtested median.

3. **Validate at 0.50**: If 0.40 passes, backtest 0.50. Same gates.

4. **Deploy 0.50**: Update default, monitor for 1 more cycle.

**For blend_with_vae (v4):**
- Adjust `gbm_weight` from 0.60 to 0.50
- Composite weight drops from 0.40 to 0.50 (wait, that's wrong)
- Actually: composite = 1.0 - gbm_weight - vae_weight
- At 50/50 with VAE disabled: composite = 0.50, gbm = 0.50, vae = 0.0

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/ml/blend.py` | Change ml_weight default 0.30 → 0.50 |

### Test Strategy

- Update existing blend tests to expect 50/50 behavior
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

- Confidence gate: confidence < 0.60 → no override
- Confidence = 1.0 - clamped_variance

### Design

**Add 2-level tier with higher confidence gate:**

```python
class OverrideConfig(BaseModel):
    # 1-level override (existing)
    top_1_percentile: float = 0.85        # Top 15%
    bottom_1_percentile: float = 0.15     # Bottom 15%
    min_confidence_1: float = 0.60

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
    idx = _LEVELS.index(tier)
    return _LEVELS[min(idx + levels, len(_LEVELS) - 1)]

def demote(tier: CompositeTier, levels: int) -> CompositeTier:
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
- Test 1-level still works: top 15% + confidence 0.65 → promotes 1 level
- Test confidence gate: bottom 5% + confidence 0.70 → only 1-level demotion
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
- `blend_with_vae(composite, gbm, vae, gbm_weight=0.60, vae_weight=0.0)`
- Composite gets remaining weight: `1.0 - 0.60 - 0.0 = 0.40`

### Design

**Phase 1: Shadow Mode (2 training cycles)**

- Set `FactorVAEConfig.enable = True`
- Keep `vae_weight = 0.0` (VAE trains but doesn't affect scores)
- Monitor per cycle:
  - `rank_ic`: Must be > 0.05 consistently (lower bar than GBM's 0.15)
  - `reconstruction_loss`: Should decrease over training epochs
  - `kl_divergence`: Should stabilize (not collapse to prior)
  - `mean_variance`: Calibration check (predicted uncertainty ≈ actual error variance)

**Phase 2: Low-Weight Enablement (2 quarters)**

If shadow mode passes:
- Set `vae_weight = 0.10`, `gbm_weight = 0.60`, composite = 0.30
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
| `engine/src/margin_engine/ml/factor_vae.py` | Change `enable` default to True |
| `engine/src/margin_engine/ml/blend.py` | Change `vae_weight` when gate passes |

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
- `SelectionStrategy`: TOP_PERCENTILE, CONVICTION_MOS, OPTIMIZED

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

Modify `simulator.py` to track cohort returns:
- Each rebalance creates a new cohort
- Track each cohort's return over the specified holding period
- Aggregate across cohorts for overall metrics

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

**Enhancement 4: Regime-Conditional Validation**

Separate pass thresholds for bull, bear, and sideways markets:
```python
class RegimePassThresholds(BaseModel):
    bull: PassThreshold     # Less strict (rising tide lifts all boats)
    bear: PassThreshold     # Most strict (alpha generation matters most)
    sideways: PassThreshold # Standard
```

Classify regimes by: S&P 500 drawdown >20% = bear, >10% = sideways, <10% = bull.

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

### Files to Modify

| File | Change |
|------|--------|
| `engine/src/margin_engine/backtesting/models.py` | New config fields, TailMetrics, RegimePassThresholds |
| `engine/src/margin_engine/backtesting/simulator.py` | Multi-holding-period cohort tracking |
| `engine/src/margin_engine/backtesting/metrics.py` | Tail metrics, regime-conditional validation |
| `api/src/margin_api/cli.py` | Update backtest CLI to support new options |

### Config/Data Dependencies

- PIT price data back to 2005-2008 (requires price-backfill extension)
- Benchmark index data (S&P 500, Russell 1000) — need historical daily returns
- Current PIT data starts at 2009 — GFC start (2007) requires additional backfill

### Test Strategy

- Unit test: tail metrics with known return distribution
- Unit test: regime classification from drawdown
- Unit test: multi-holding-period cohort return calculation
- Integration test: full backtest with GFC period, verify regime-conditional thresholds
- Backward compat: default config produces identical results to current
