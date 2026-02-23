# ML + V4 Scoring Integration Design

**Date:** 2026-02-22
**Status:** Approved

## Overview

Wire LightGBM cluster models, FactorVAE, Track C (Efficient Growth), style classifier, and V4 orchestrator into the production scoring pipeline. ML predictions can override rules-based conviction by one level when model confidence is high (rank IC > 0.15, VAE variance low).

## Architecture

### Approach: Integrated Pipeline (ML embedded in scoring)

ML predictions are computed upfront and fed into the V4 pipeline as additional inputs. The V4 orchestrator uses rules-based gates plus ML confidence to determine final conviction.

```
WEEKLY (Saturday 2AM UTC):
  Load historical V4Scores + price data
  -> Compute 12-month forward returns
  -> Build feature matrix from factor scores
  -> Cluster stocks (KMeans, n=5)
  -> Train per-cluster LightGBM models (walk-forward CV)
  -> Train FactorVAE (latent_dim=8, hidden_dim=64, epochs=100)
  -> Save artifacts + record MlModelRun
  -> Compute held-out rank IC -> store model_qualifies flag

DAILY (scoring run):
  1. Build TickerV4Data (financials, prices, real percentiles)
  2. Classify investment style (VALUE/BLEND/GROWTH) per ticker
  3. Run Track A cascade (Compounder)
  4. Run Track B cascade (Mispricing)
  5. Run Track C cascade (Efficient Growth)
  6. Load latest qualified ML models
  7. Build feature matrix for current universe
  8. LightGBM predict -> per-ticker alpha signal
  9. FactorVAE predict -> per-ticker alpha + uncertainty
  10. V4 Orchestrator: select winning track, assign rules-based conviction
  11. ML Ensemble Override: promote/demote by one level if confident
  12. Apply timing overlay (with real momentum percentiles)
  13. Enforce portfolio concentration cap (50 positions)
  -> Persist V4Score
```

## Forward Returns Pipeline

Fixes the critical bug where `train_ml_models` uses `forward_returns = np.zeros()`.

New module: `engine/src/margin_engine/ml/forward_returns.py`

```python
def compute_forward_returns(
    scores: list[V4ScoreRecord],           # historical scored tickers with scored_at dates
    price_data: dict[str, list[PriceBar]], # ticker -> price history
    horizon_days: int = 252,               # 12 months (~252 trading days)
) -> dict[str, float]:                     # ticker -> forward return
```

**Logic:**
1. For each scored ticker, find the closing price on `scored_at` date.
2. Find the closing price `horizon_days` trading days later.
3. `return = (future_price / score_date_price) - 1`
4. Tickers without sufficient future price data are excluded.
5. Delisted tickers get -100% return (survivorship bias handling).

**Training data window:** Only scores from 13+ months ago are used for training (so 12-month forward returns are fully realized). Most recent 12 months are excluded until returns materialize.

## ML Training Pipeline

The `train_ml_models` worker is reworked to:
- Read from `v4_scores` table (not deprecated `scores` table)
- Use real 12-month forward returns
- Train both LightGBM and FactorVAE
- Record model qualification status

**Training flow:**

1. Load V4Scores older than 13 months (realized returns available)
2. Load price_history for those tickers
3. `compute_forward_returns()` -> real 12-month returns
4. `build_feature_matrix()` from V4Score JSONB detail
5. `cluster_stocks(features, tickers, n_clusters=5)`
6. Train LightGBM:
   - `train_cluster_models(features, forward_returns, cluster_indices)`
   - Walk-forward CV within each cluster
   - Compute held-out rank IC per cluster
7. Train FactorVAE:
   - `train_factor_vae(features, forward_returns, config)`
   - Config: `enable=True, latent_dim=8, hidden_dim=64, epochs=100`
   - Record rank_ic, reconstruction_loss, kl_divergence
8. Save artifacts:
   - LightGBM: one `.pkl` per cluster
   - VAE: one `.pt` state dict
   - Metadata: cluster assignments, feature names, rank IC scores
9. Record MlModelRun with `model_qualifies = (overall_rank_ic > 0.15)`

**Model qualification gate:** If the latest trained models have rank IC <= 0.15, the scoring pipeline runs purely rules-based. ML override is disabled. This prevents bad models from corrupting production scores.

**Schedule:** Saturday 2AM UTC. Retrains weekly on growing historical dataset.

## Track C: Efficient Growth Cascade

New cascade in `engine/src/margin_engine/scoring/v3_track_c_cascade.py`.

**Eligibility:** Only tickers classified as GROWTH by the style classifier. VALUE/BLEND tickers get Track C result = NONE.

### Four-Gate System

| Gate | Metric | Pass Threshold |
|------|--------|----------------|
| 1. Growth Efficiency | Revenue CAGR 3yr > 15% AND gross margin > 40% | Both must pass |
| 2. Unit Economics | gross_profit_growth > revenue_growth (expanding margins) | Positive spread |
| 3. Capital Efficiency | ROIC > WACC despite reinvestment rate > 50% of FCF | ROIC-WACC > 0 |
| 4. Growth Durability | Revenue growth CV < 0.30 over 3yr AND R&D/Revenue > 5% | Both must pass |

### Conviction Thresholds

| Conviction | Conditions |
|------------|------------|
| EXCEPTIONAL | 4 gates, revenue CAGR > 25%, gross margin expanding, ROIC-WACC > 5% |
| HIGH | 3+ gates, revenue CAGR > 15%, ROIC-WACC > 2% |
| MEDIUM | 3+ gates |
| NONE | < 3 gates |

### Score (multiplicative)

```
score = growth_efficiency x unit_economics x capital_efficiency x durability
```

### Inputs (TrackCInputs)

- Financial history (3yr minimum for CAGR)
- Current period (margins, ROIC, reinvestment rate)
- WACC
- R&D/Revenue ratio
- Regime adjustments

## Style Classifier Integration

The existing `style_classifier.py` majority-vote system (EV/FCF percentile, revenue CAGR, earnings acceleration, reinvestment intensity) is called at the start of each scoring run.

The style tag (VALUE/BLEND/GROWTH) is used for:
- V4 weight adjustments via `v4_weights.py` (already built)
- Track C routing (only GROWTH tickers enter Track C)
- Attached to V4Score for downstream analysis

## V4 Orchestrator

Replaces V3 orchestrator. Uses existing `v4_orchestrator.py` scaffold with three tracks.

### Track Selection Rules

| Condition | Result | Position |
|-----------|--------|----------|
| All three tracks HIGH+ | `all_three`, EXCEPTIONAL | 20% |
| A + B both HIGH+ | `both`, EXCEPTIONAL | 20% |
| A + C both HIGH+ | `compounder_growth`, EXCEPTIONAL | 15% |
| B + C both HIGH+ | `mispricing_growth`, HIGH | 10% |
| Single track strongest | Use that track's conviction | Track-dependent |
| None qualify | `neither`, NONE | 0% |

## ML Ensemble Override

Runs after the V4 orchestrator assigns rules-based conviction. Can promote or demote by exactly one level.

```python
def apply_ml_override(
    rules_conviction: ConvictionLevel,
    ml_alpha: float,            # LightGBM prediction
    vae_mean: float,            # VAE prediction
    vae_variance: float,        # VAE uncertainty
    model_qualifies: bool,      # rank IC > 0.15 from training
    universe_ml_alphas: list,   # all ML alphas for percentile ranking
) -> tuple[ConvictionLevel, str]:  # (final_conviction, override_type)
```

**Logic:**

1. If not `model_qualifies` -> return `rules_conviction` unchanged.
2. Compute `ml_signal = blend_with_vae(composite=0, gbm=ml_alpha, vae_mean, vae_var, gbm_weight=0.60, vae_weight=0.40)`.
3. Compute `confidence = 1.0 - clamp(vae_variance, 0, 1)`.
4. If `confidence < 0.60` -> return `rules_conviction` unchanged (too uncertain).
5. `ml_percentile = rank(ml_signal)` across universe (0-100).
6. Override rules:
   - **PROMOTE** (ml_percentile >= 85 AND confidence >= 0.75): move up one level.
   - **DEMOTE** (ml_percentile <= 15 AND confidence >= 0.75): move down one level.
   - Otherwise: no change.
7. Record `ml_override = "promoted" | "demoted" | "none"`.

### Safety Rails

- Maximum one-level change (cannot jump NONE -> HIGH)
- Requires high confidence (>= 0.75) to override
- Model must pass qualification gate (IC > 0.15) or override is fully disabled
- Override is logged in V4Score JSONB for audit trail
- Deterministic: VAE inference uses z_mu (mean, no sampling)

## Worker Pipeline Changes

### New `full_score_v4()` Worker

```
1. Load all Assets + FinancialData from DB
2. Compute universe-wide percentiles:
   - SUE percentiles (existing)
   - Momentum percentiles (NEW: rank 12-1mo return across universe)
   - Insider cluster percentiles
   - Institutional accumulation percentiles
3. Classify style per ticker via style_classifier
4. Build TickerV4Data per ticker (with real percentiles)
5. Load latest qualified ML models:
   - Query MlModelRun WHERE model_qualifies=True ORDER BY created_at DESC
   - Load LightGBM .pkl + VAE .pt from artifact_path
   - If none exist -> ml_models = None
6. Build feature matrix for current universe
7. If ml_models exist:
   - LightGBM predict per cluster -> ml_alphas[ticker]
   - VAE predict -> vae_means[ticker], vae_variances[ticker]
   - Else: all None
8. Call score_universe_v4(ticker_data, shiller_cape, ml_predictions)
9. Persist V4Score rows to DB
10. Chain -> backtest_validate (optional)
```

### Timing Overlay Fix

Replace hardcoded `momentum_percentile=50.0` with real computation:

```python
# Compute 12-1 month momentum (skip last month) per ticker
returns_12_1 = {}
for ticker, prices in price_data.items():
    r12 = (prices[-21] / prices[-252]) - 1
    returns_12_1[ticker] = r12

momentum_percentiles = compute_percentile_ranks(returns_12_1)
# Feed into TickerV4Data.momentum_percentile
```

### Cron Schedule

```python
functions = [
    full_ingest,
    full_score_v4,      # replaces full_score + full_score_v3
    backtest_validate,
    train_ml_models,
    live_price_poll,
    retry_quarantined,
]
cron_jobs = [
    cron(full_ingest, hour=1),
    cron(live_price_poll, minute={0, 5, 10, ...}),
    cron(retry_quarantined, hour=3),
    cron(train_ml_models, weekday=5, hour=2),
]
```

`full_score_v4` chains from `full_ingest` completion. Old `full_score` (v2) and `full_score_v3` are removed from the function list.

## Database Changes

### New `v4_scores` Table

```
v4_scores:
  id: int PK
  asset_id: int FK -> assets
  opportunity_type: str        # compounder|mispricing|both|compounder_growth|
                               #  mispricing_growth|all_three|neither
  conviction: str              # final (after ML override)
  rules_conviction: str        # before ML override
  track_a: JSONB               # serialized V3TrackResult
  track_b: JSONB               # serialized V3TrackResult
  track_c: JSONB               # serialized V3TrackResult (NEW)
  style: str                   # value|blend|growth
  timing_signal: str
  max_position_pct: float
  regime: str
  composite_score: float
  ml_alpha: float | None
  ml_confidence: float | None
  ml_override: str             # promoted|demoted|none
  scored_at: datetime(tz)
```

### `ml_model_runs` — New Columns

```
+ model_qualifies: bool
+ overall_rank_ic: float
+ vae_rank_ic: float | None
+ vae_artifact_path: str | None
```

### Migration

One Alembic migration creates `v4_scores` table and adds columns to `ml_model_runs`. Existing `v3_scores` table is kept as-is for historical data.

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Forward returns | `compute_forward_returns()` with known prices | Golden-value test with hand-calculated returns |
| Track C cascade | Each gate individually + full cascade | Parametrized pass/fail per gate (same pattern as A/B) |
| Style classifier | Known financial profiles -> expected style | Golden-value tests for VALUE/BLEND/GROWTH |
| ML override | Mock ML predictions + confidence levels | Parametrized: (conviction, ml_pct, confidence) -> result |
| V4 orchestrator | All track combinations | Exhaustive matrix of (A, B, C) conviction combos |
| Integration | Full `score_universe_v4()` | End-to-end with golden dataset (~20 real companies) |
| ML training | `train_ml_models` with historical data | Verify IC > 0 on held-out data |
| Worker | `full_score_v4` with test DB | Verify V4Score rows persist correctly |

**Coverage targets:** engine >= 95%, api >= 90%.

**Determinism:** All ML components use `seed=42`. Same inputs = same outputs. VAE inference uses `z_mu` (mean, no sampling).

## Key Design Decisions

1. **Ensemble override, not blend:** ML can promote/demote conviction by one level rather than blending scores. Preserves the interpretability of the gate cascade while allowing ML to correct edge cases.
2. **VAE variance as confidence gate:** Low VAE variance = high confidence = ML override allowed. High variance = uncertain = rules-only. This naturally limits ML influence to cases where the model is sure.
3. **Model qualification gate (IC > 0.15):** Prevents poorly-trained models from affecting production scores. First few weeks of operation will run rules-only until sufficient training data accumulates.
4. **12-month forward returns:** Matches the investment horizon. Longer than 6mo for cleaner signal, accepts fewer training samples as tradeoff.
5. **Track C only for GROWTH-style tickers:** Prevents the growth cascade from misapplying to mature/value companies where growth metrics are irrelevant.
6. **Keep v3_scores table:** No migration of historical data. V4 scores go to new table. Dashboard/API routes updated to read from v4_scores.
