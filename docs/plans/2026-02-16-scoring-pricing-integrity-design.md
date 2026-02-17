# Scoring & Pricing Integrity Fix

**Date:** 2026-02-16
**Status:** Approved

## Problem

Two critical defects in the candidate ranking and pricing system:

1. **Scoring integrity:** Top picks display a composite score of 100.0 because `rerank_composites()` converts weighted averages to percentile ranks via `(rank / n) * 100`. The #1 stock always gets exactly 100.0 regardless of actual quality. A mediocre stock in a weak universe still reads "100."

2. **Target price extremes:** Assets show prices like $0.01 or $1,483,565.45 due to: no bounds on `shares_outstanding` beyond `<= 0`, no per-method output validation, and no final output sanity checks.

## Root Cause Analysis

### Scoring

In `normalizer.py:rerank_composites()`, the formula `(rank / n) * 100` maps the highest-ranked stock to exactly 100.0 by definition. The system already computes and stores two values:
- `composite_raw_score` — the weighted average of sector-neutral factor percentiles (set at `composite.py:105`)
- `composite_percentile` — overwritten by `rerank_composites()` to be the universe-level percentile rank

Both fields exist on `CompositeScore`. The raw score is the meaningful quality measure; the percentile is the relative rank. The API currently surfaces only the percentile as "the score."

### Target Prices

In `price_targets.py:compute_price_targets()`:
- **Line 102:** Only checks `shares <= 0`. A value of 10 or 1 trillion passes through.
- **Lines 254, 283, 312, 337:** Division by `shares` with no bounds produces extreme per-share prices.
- **No cross-method consistency check:** A single garbage method (e.g., shareholder yield implying $1.5M/share) skews the weighted consensus.
- **No final output validation:** The consensus result is returned regardless of magnitude.

## Design

### Fix 1: Scoring — Surface Raw Score as Primary Metric

**Model layer** (`engine/src/margin_engine/models/scoring.py`):
- No changes. `CompositeScore` already has both `composite_raw_score` (0-100 weighted average) and `composite_percentile` (0-100 universe rank).
- `conviction_level` and `signal` properties continue to use `composite_percentile` for threshold logic. This is correct — conviction is about relative position in the universe.

**Engine layer** (`engine/src/margin_engine/scoring/`):
- No changes to `composite.py` or `normalizer.py`. The engine already computes both values correctly. `rerank_composites()` updates `composite_percentile` but leaves `composite_raw_score` as the original weighted average.

**API schema layer** (`api/src/margin_api/schemas/scores.py`):
- Expose `composite_raw_score` as `score` in responses — the primary displayed metric.
- Expose `composite_percentile` as `universe_percentile` — the relative rank.
- Frontend displays `score` as the primary number. Users see true quality, not an artificial 100.

### Fix 2: Target Prices — Four-Layer Validation Pipeline

All changes in `engine/src/margin_engine/scoring/quantitative/price_targets.py`.

**PriceTargets model change:**
- Add `invalid_reason: str | None = None` field.
- When set, all price fields (`intrinsic_value`, `buy_price`, `sell_price`, `price_upside`) remain None.
- Add validator: if `invalid_reason` is set, price fields must be None.
- Add validator: `intrinsic_value`, `buy_price`, `sell_price` must be > 0 when present.

**Layer 1 — Input validation** (top of `compute_price_targets()`):
- Fixed bounds: `shares_outstanding` must be 100,000–50,000,000,000. Outside → return `PriceTargets(actual_price=actual_price, invalid_reason="shares_outstanding_out_of_bounds")`.
- Market-cap cross-validation: if `actual_price` available, compute `actual_price * shares`. If < $1M or > $10T → return with `invalid_reason="implied_market_cap_unreasonable"`.

**Layer 2 — Per-method output bounds** (inside each `_*_per_share()` helper):
- Thread `actual_price` into each helper as optional parameter.
- After computing per-share price: if result < $0.01 → return None.
- If `actual_price` available and result > 100x `actual_price` → return None.

**Layer 3 — Cross-method consistency** (after collecting valid methods):
- If 2+ methods valid, compute median. Exclude any method < 0.1x or > 10x the median.
- If no methods survive → return with `invalid_reason="methods_inconsistent"`.

**Layer 4 — Final output validation** (after consensus computation):
- If `actual_price` available: intrinsic value must be between 1% and 50x of actual price. Outside → null all prices + `invalid_reason="intrinsic_value_extreme"`.
- If `actual_price` unavailable: intrinsic value must be $0.10–$1,000,000. Outside → null + flag.

**Logging:**
- `logging.warning` on every validation trigger with ticker, layer name, offending value, and violated bound.

## Testing

### Scoring Tests

- `rerank_composites()` with 5 stocks: `composite_raw_score` values differ from `composite_percentile` values.
- Top stock's `composite_raw_score` is not 100.0 unless all factors genuinely average to 100.
- API schema test: response includes both `score` and `universe_percentile`.

### Target Price Tests

- **Layer 1:** shares=50 → `invalid_reason="shares_outstanding_out_of_bounds"`. shares=100B → same.
- **Layer 1:** actual_price=$100, shares=1000 (market cap $100K) → `invalid_reason="implied_market_cap_unreasonable"`.
- **Layer 2:** Method returning $0.005/share → excluded (returns None).
- **Layer 2:** Method returning 200x actual_price → excluded.
- **Layer 3:** Methods [$50, $55, $5000] → $5000 excluded as > 10x median.
- **Layer 4:** Consensus = $0.005 with actual_price=$100 → `invalid_reason="intrinsic_value_extreme"`.
- **Happy path:** Valid inputs, `invalid_reason` is None, prices within bounds.
- **Determinism:** Same inputs → identical outputs across 10 runs.
- **PriceTargets validator:** `invalid_reason` set with non-None price field → validation error.

## Before/After Examples

| Scenario | Before | After |
|----------|--------|-------|
| Top pick (AAPL, #1 of 500) | `score: 100.0` | `score: 87.4`, `universe_percentile: 100.0` |
| 2nd pick (MSFT, #2 of 500) | `score: 99.8` | `score: 85.1`, `universe_percentile: 99.8` |
| Mid-pack (#250 of 500) | `score: 50.0` | `score: 52.3`, `universe_percentile: 50.0` |
| Corrupt shares (shares=10) | `intrinsic_value: 1,483,565.45` | `intrinsic_value: null`, `invalid_reason: "shares_outstanding_out_of_bounds"` |
| Inflated shares (shares=1T) | `intrinsic_value: 0.01` | `intrinsic_value: null`, `invalid_reason: "shares_outstanding_out_of_bounds"` |
| Method outlier (3 agree ~$150, 1 says $15K) | `intrinsic_value: ~$3,900` | `intrinsic_value: ~$155` (outlier excluded) |

## Drift Prevention

- `FactorScore.percentile_rank` validator (0-100) already exists.
- New `PriceTargets` validators enforce consistency between `invalid_reason` and price fields.
- Structured logging on every validation trigger provides audit trail.
- All scoring is deterministic: same inputs → same outputs. No randomness, no AI calls.

## Files Changed

| File | Change |
|------|--------|
| `engine/src/margin_engine/scoring/quantitative/price_targets.py` | Add 4-layer validation, `invalid_reason` field, per-method bounds, logging |
| `api/src/margin_api/schemas/scores.py` | Expose `score` (raw) and `universe_percentile` (rank) |
| `engine/tests/scoring/quantitative/test_price_targets.py` | Validation layer tests, happy path, determinism |
| `engine/tests/scoring/test_normalizer.py` | Raw score vs percentile divergence test |
| `api/tests/test_schemas.py` | Schema field mapping tests |

## Constraints

- No UI masking of errors.
- No hardcoded overrides.
- No temporary fixes.
- All fixes at the calculation layer.
- Results consistent across re-runs.
- Mathematically sound and defensible.
