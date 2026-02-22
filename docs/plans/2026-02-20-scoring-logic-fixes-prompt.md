# Scoring Logic Fixes — Implementation Prompt

> **For Claude:** Use TDD for every change. Write the failing test first, verify it fails, implement the fix, verify it passes, run the full engine suite, commit. Use `uv run pytest engine/tests/ -v` to run tests.

**Goal:** Fix 14 identified issues in the scoring pipeline that systematically limit candidate quality and portfolio construction.

**Architecture:** All changes are in `engine/src/margin_engine/scoring/`. Each fix is independent — commit after each one.

**Test command:** `uv run pytest engine/tests/ -v`

---

## Fix 1: MEDIUM conviction gets starter positions (not 0%)

**Problem:** MEDIUM conviction = 0% across all opportunity types. A stock passing 3+ gates gets identified as qualifying but receives no allocation. In a concentrated 10-position portfolio, this forces holding cash when decent ideas exist.

**File:** `engine/src/margin_engine/scoring/v3_position_sizing.py`

**Current code:**
```python
_SIZING: dict[str, dict[ConvictionLevel, float]] = {
    "compounder": {
        ConvictionLevel.EXCEPTIONAL: 15.0,
        ConvictionLevel.HIGH: 8.0,
        ConvictionLevel.MEDIUM: 0.0,  # <-- problem
        ConvictionLevel.NONE: 0.0,
    },
    # ... same pattern for all types
}
```

**Fix:** Add starter positions for MEDIUM conviction:

| Opportunity Type | MEDIUM (new) |
|---|---|
| compounder | 4.0% |
| mispricing | 3.0% |
| efficient_growth | 3.0% |
| both | 5.0% |
| compounder_growth | 5.0% |
| all_three | 5.0% |

Update the module docstring — remove "Medium = 0% (not actionable)".

**Tests:** `engine/tests/scoring/test_v3_position_sizing.py`
- Test that MEDIUM conviction returns the correct new values for each opportunity type
- Test that NONE conviction still returns 0.0 for all types
- Test that existing EXCEPTIONAL and HIGH values are unchanged

---

## Fix 2: Tiered IV gate based on quality floor score

**Problem:** Track B Gate 1 requires `price < 0.60 * ensemble_iv` (40% margin of safety). Quality businesses rarely trade at 40%+ discounts. This gate eliminates most quality mispricings.

**File:** `engine/src/margin_engine/scoring/v3_cascade.py` (line 213)

**Current code:**
```python
if ensemble.converged and inputs.current_price < 0.60 * ensemble.ensemble_iv:
    gates_passed += 1
```

**Fix:** Tier the discount threshold based on quality. Compute `quality_floor` BEFORE Gate 1 (currently computed in Gate 4). Use quality to set the IV discount threshold:

```python
# Compute quality floor early (move from Gate 4 position)
roic = _current_roic(inputs.period)
improving = _is_roic_improving(inputs.history)
quality_floor = compute_quality_floor_factor(roic, improving)

# Gate 1: Tiered IV discount
if quality_floor >= 1.0:
    iv_discount = 0.75  # 25% margin for quality businesses (ROIC >= 8%)
elif quality_floor > 0:
    iv_discount = 0.65  # 35% margin for improving businesses
else:
    iv_discount = 0.60  # 40% margin for low-quality (original)

if ensemble.converged and inputs.current_price < iv_discount * ensemble.ensemble_iv:
    gates_passed += 1
```

Gate 4 still uses the same `quality_floor` value — just don't recompute it.

**Tests:** `engine/tests/scoring/test_v3_cascade.py` (Track B tests)
- High-quality business (ROIC=12%) at 70% of IV passes Gate 1 (would have failed before)
- Improving business (ROIC=5%, improving) at 62% of IV passes Gate 1
- Low-quality business (ROIC=3%, not improving) at 62% of IV still fails Gate 1
- Low-quality business at 55% of IV still passes Gate 1
- Existing tests still pass with adjusted expectations

---

## Fix 3: Relax ensemble convergence for asset-light businesses

**Problem:** Requiring 3+ of 4 methods to converge within 30% systematically fails for asset-light businesses because asset floor valuations are near-zero, creating automatic divergence. This perpetuates value bias.

**File:** `engine/src/margin_engine/scoring/quantitative/ensemble_valuation.py`

**Current code:**
```python
def compute_ensemble_valuation(
    ...
    min_converging: int = 3,
) -> EnsembleResult:
```

**Fix:** Add a `sector` parameter. For asset-light sectors (Technology, Communication Services, Healthcare), allow convergence on 2 of 4 methods, BUT only if those 2 are DCF and peer comparison (the methods that work for asset-light businesses). For all other sectors, keep `min_converging=3`.

```python
from margin_engine.models.financial import GICSSector

_ASSET_LIGHT_SECTORS = frozenset({
    GICSSector.TECHNOLOGY,
    GICSSector.COMMUNICATION_SERVICES,
    GICSSector.HEALTHCARE,
})

def compute_ensemble_valuation(
    dcf_iv: float,
    owner_earnings_iv: float,
    asset_floor_iv: float,
    peer_comparison_iv: float,
    convergence_pct: float = 0.30,
    min_converging: int = 3,
    sector: GICSSector | None = None,
) -> EnsembleResult:
```

After the main convergence loop fails, add an asset-light fallback:
```python
# Asset-light fallback: 2 of 4 if sector is asset-light
if not converged and sector in _ASSET_LIGHT_SECTORS:
    core_methods = {"dcf": dcf_iv, "peer_comparison": peer_comparison_iv}
    core_valid = {k: v for k, v in core_methods.items() if v > 0}
    if len(core_valid) == 2:
        vals = list(core_valid.values())
        median_iv = statistics.median(vals)
        if median_iv > 0:
            within = [v for v in vals if abs(v - median_iv) / median_iv <= convergence_pct]
            if len(within) >= 2:
                return EnsembleResult(
                    converged=True,
                    converging_count=2,
                    ensemble_iv=median_iv,
                    methods=methods,
                )
```

Update `run_track_b_cascade` in `v3_cascade.py` to pass `sector=inputs.profile.sector`.

**Tests:** `engine/tests/scoring/quantitative/test_ensemble_valuation.py`
- Tech company: DCF=100, peer=110, owner_earnings=90, asset_floor=5 — converges on DCF+peer (2 of 4) with sector=TECHNOLOGY
- Same inputs without sector parameter — does NOT converge (only 2 of 4, below min_converging=3)
- Non-tech company with same inputs — does NOT converge
- Existing convergence tests unchanged (3 of 4 still works as before)

---

## Fix 4: Increase Track C position sizing

**Problem:** `efficient_growth` at HIGH conviction is only 7% — the smallest HIGH allocation. This systematically underweights the growth opportunity set that Track C was built to capture.

**File:** `engine/src/margin_engine/scoring/v3_position_sizing.py`

**Fix:** Change `efficient_growth` sizing to match `compounder`:

```python
"efficient_growth": {
    ConvictionLevel.EXCEPTIONAL: 15.0,  # was 12.0
    ConvictionLevel.HIGH: 8.0,          # was 7.0
    ConvictionLevel.MEDIUM: 3.0,        # was 0.0 (from Fix 1)
    ConvictionLevel.NONE: 0.0,
},
```

**Tests:** Update existing position sizing tests for the new values.

---

## Fix 5: Use median absolute deviation for compounding power stability

**Problem:** The compounding power formula multiplies by `(1 - ROIC_CV)` where CV = coefficient of variation. Companies that make acquisitions in bursts (Constellation Software, Danaher) show high ROIC variance, penalizing them even though incremental returns are excellent.

**File:** `engine/src/margin_engine/scoring/v3_intermediates.py` (function `compute_compounding_power`, lines 49-93)

**Current code:**
```python
stdev_roic = statistics.pstdev(roics)
cv = min(abs(stdev_roic / mean_roic), 1.0)
return inc_roic * reinvestment_rate * (1.0 - cv)
```

**Fix:** Replace CV with normalized MAD (median absolute deviation), which is more robust to outliers from lumpy acquisitions:

```python
median_roic = statistics.median(roics)
mad = statistics.median([abs(r - median_roic) for r in roics])
# Normalize MAD to 0-1 scale (MAD of 50% of median = maximum penalty)
normalized_mad = min(mad / max(abs(median_roic), 0.001), 1.0)
stability = 1.0 - normalized_mad
return inc_roic * reinvestment_rate * max(stability, 0.0)
```

**Tests:** `engine/tests/scoring/test_v3_intermediates.py`
- Steady ROIC history [0.15, 0.16, 0.15, 0.14, 0.15] — stability near 1.0 (both CV and MAD should agree)
- Lumpy ROIC history [0.10, 0.25, 0.12, 0.22, 0.14] — MAD gives higher stability than CV (test the difference)
- Single outlier [0.15, 0.15, 0.15, 0.15, 0.40] — MAD much more forgiving than CV
- All identical ROICs [0.12, 0.12, 0.12] — stability = 1.0

---

## Fix 6: Weight moat signatures by durability

**Problem:** All 4 moat signatures contribute equally (1 point each), but switching costs and pricing power are empirically more durable than scale economics and capital efficiency.

**File:** `engine/src/margin_engine/scoring/quantitative/moat_durability.py`

**Current code:**
```python
signatures: list[str] = []
if _detect_scale_economics(history):
    signatures.append("scale_economics")
if _detect_pricing_power(history):
    signatures.append("pricing_power")
if _detect_switching_costs(history):
    signatures.append("switching_costs")
if _detect_capital_efficiency(history):
    signatures.append("capital_efficiency")

return FactorScore(
    name="moat_durability",
    raw_value=float(len(signatures)),
    ...
)
```

**Fix:** Assign weights to each signature:

```python
_SIGNATURE_WEIGHTS: dict[str, float] = {
    "switching_costs": 1.5,
    "pricing_power": 1.25,
    "scale_economics": 1.0,
    "capital_efficiency": 0.75,
}
# Max possible score: 1.5 + 1.25 + 1.0 + 0.75 = 4.5
# Normalize to 0-4 scale for backward compatibility

weighted_score = sum(_SIGNATURE_WEIGHTS[s] for s in signatures)
# Normalize: 4.5 max -> 4.0 max
normalized = weighted_score * (4.0 / 4.5)
```

Use `normalized` as `raw_value` instead of `len(signatures)`.

**Important:** The conviction thresholds in `v3_thresholds.py` reference `moat_durability` as integer comparisons (`>= 2`, `>= 3`). Since the new scale is 0-4.0 (float), the thresholds still work — a company with switching_costs + pricing_power scores `(1.5 + 1.25) * 4/4.5 = 2.44` which passes `>= 2`. A company with only scale + capital_efficiency scores `(1.0 + 0.75) * 4/4.5 = 1.56` which fails `>= 2`. This is the desired behavior.

**Tests:** `engine/tests/scoring/quantitative/test_moat_durability.py`
- All 4 signatures detected: raw_value = 4.0 (max)
- switching_costs + pricing_power only: raw_value ≈ 2.44
- scale_economics + capital_efficiency only: raw_value ≈ 1.56
- switching_costs only: raw_value ≈ 1.33
- No signatures: raw_value = 0.0
- Verify backward compatibility: thresholds that passed before still pass

---

## Fix 7: Corroborated catalyst strength

**Problem:** `catalyst_strength = max(insider, institutional, sue)` — a single strong signal passes the gate. A stock with 90th percentile SUE but declining institutional ownership and no insider buying still scores 90.

**File:** `engine/src/margin_engine/scoring/v3_intermediates.py` (function `compute_catalyst_strength`, lines 157-166)

**Current code:**
```python
def compute_catalyst_strength(
    insider_percentile: float,
    institutional_percentile: float,
    sue_percentile: float,
) -> float:
    return max(insider_percentile, institutional_percentile, sue_percentile)
```

**Fix:** Weighted blend that rewards corroboration:

```python
def compute_catalyst_strength(
    insider_percentile: float,
    institutional_percentile: float,
    sue_percentile: float,
) -> float:
    """Catalyst strength = weighted blend favoring corroboration.

    50% weight on strongest signal, 30% on second, 20% on third.
    This rewards multiple confirming catalysts over a single outlier.
    """
    sorted_signals = sorted(
        [insider_percentile, institutional_percentile, sue_percentile],
        reverse=True,
    )
    return 0.50 * sorted_signals[0] + 0.30 * sorted_signals[1] + 0.20 * sorted_signals[2]
```

**Impact on thresholds:** The catalyst gate threshold is 60. Under the old formula, a single signal at 61 with others at 0 would pass (max=61). Under the new formula: `0.50*61 + 0.30*0 + 0.20*0 = 30.5` — fails. This is the intended behavior. A stock needs corroboration to pass.

**Threshold adjustment:** The gate threshold in `v3_cascade.py` (line 244) should be lowered from 60 to 40 to compensate for the blending, since the new formula produces lower values by design:
```python
catalyst_threshold = 40.0  # was 60.0
```

And in `v3_thresholds.py`, adjust the Track B catalyst thresholds:
```python
_B_EXCEPTIONAL_CATALYST = 55.0  # was 80.0
_B_HIGH_CATALYST = 40.0         # was 60.0
```

These recalibrated thresholds maintain the same selectivity: a stock with all three signals at 70th percentile scores `0.50*70 + 0.30*70 + 0.20*70 = 70` (passes both). A stock with one signal at 80 and others at 20 scores `0.50*80 + 0.30*20 + 0.20*20 = 50` (passes HIGH but not EXCEPTIONAL).

**Tests:** `engine/tests/scoring/test_v3_intermediates.py`
- All three at 70: result = 70.0
- One at 90, others at 0: result = 45.0 (was 90.0)
- One at 80, one at 50, one at 20: result = 0.50*80 + 0.30*50 + 0.20*20 = 59.0
- All at 0: result = 0.0

Also update `engine/tests/scoring/test_v3_cascade.py` and `engine/tests/scoring/test_v3_thresholds.py` for the new thresholds.

---

## Fix 8: Add margin expansion solver to reverse DCF

**Problem:** The reverse DCF only solves for revenue growth, holding margins constant. Compounders like Chipotle, Copart, and O'Reilly create value through margin expansion. The current solver shows a small growth gap for these companies because the market is pricing margin expansion, not revenue acceleration.

**File:** `engine/src/margin_engine/scoring/quantitative/reverse_dcf.py`

**Fix:** Add a parallel margin expansion check. If either the growth gap OR the implied margin is below sustainable margin, the gate can pass.

Add a new function:

```python
def solve_implied_margin(
    current_price: float,
    current_revenue: float,
    current_fcf_margin: float,
    wacc: float,
    terminal_growth: float,
    revenue_growth: float,
    shares_outstanding: int,
    projection_years: int = _PROJECTION_YEARS,
) -> float | None:
    """Solve for the FCF margin implied by the current market price.

    Holds revenue growth constant and solves for the margin that would
    produce the current price.

    Returns None if inputs are invalid.
    """
    if current_revenue <= 0 or current_price <= 0 or shares_outstanding <= 0:
        return None

    target = current_price * shares_outstanding

    lo, hi = -0.10, 0.60  # margin range

    for _ in range(_SOLVER_MAX_ITER):
        mid = (lo + hi) / 2.0
        # FCF = revenue * margin at each year
        pv_sum = 0.0
        for t in range(1, projection_years + 1):
            projected_rev = current_revenue * (1 + revenue_growth) ** t
            projected_fcf = projected_rev * mid
            pv_sum += projected_fcf / (1 + wacc) ** t

        final_rev = current_revenue * (1 + revenue_growth) ** projection_years
        final_fcf = final_rev * mid
        if wacc > terminal_growth:
            terminal = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
            pv_sum += terminal / (1 + wacc) ** projection_years

        if abs(pv_sum - target) / max(target, 1.0) < _SOLVER_TOLERANCE:
            return mid
        if pv_sum < target:
            lo = mid
        else:
            hi = mid

    return (lo + hi) / 2.0
```

Add a combined function:

```python
def reverse_dcf_combined_gap(
    current_price: float,
    current_fcf: float,
    current_revenue: float,
    current_fcf_margin: float,
    sustainable_fcf_margin: float,
    wacc: float,
    terminal_growth: float,
    shares_outstanding: int,
    sustainable_growth_rate: float,
    revenue_growth_for_margin_solve: float,
    projection_years: int = _PROJECTION_YEARS,
) -> FactorScore:
    """Compute combined growth gap and margin gap.

    Returns the MORE FAVORABLE of the two gaps as raw_value.
    If the market is pricing in less growth than sustainable OR less
    margin expansion than achievable, the opportunity exists.
    """
    # Growth gap (existing logic)
    growth_gap_result = reverse_dcf_growth_gap(
        current_price, current_fcf, wacc, terminal_growth,
        shares_outstanding, sustainable_growth_rate, projection_years,
    )
    growth_gap = growth_gap_result.raw_value

    # Margin gap
    implied_margin = solve_implied_margin(
        current_price, current_revenue, current_fcf_margin,
        wacc, terminal_growth, revenue_growth_for_margin_solve,
        shares_outstanding, projection_years,
    )
    margin_gap = (sustainable_fcf_margin - implied_margin) if implied_margin is not None else 0.0

    # Use the more favorable gap
    best_gap = max(growth_gap, margin_gap)

    return FactorScore(
        name="reverse_dcf_combined_gap",
        raw_value=best_gap,
        percentile_rank=0.0,
        detail=(
            f"growth_gap={growth_gap:.4f}, margin_gap={margin_gap:.4f}, "
            f"best_gap={best_gap:.4f}"
        ),
    )
```

**DO NOT** change `reverse_dcf_growth_gap` — it stays as-is for backward compatibility. The combined function is a new alternative that Track A can optionally use. Wire it into `run_track_a_cascade` only if the additional inputs (`current_revenue`, `current_fcf_margin`, `sustainable_fcf_margin`, `revenue_growth_for_margin_solve`) are available via `TrackAInputs`.

Add optional fields to `TrackAInputs`:
```python
current_revenue: float | None = None
current_fcf_margin: float | None = None
sustainable_fcf_margin: float | None = None
revenue_growth_for_margin_solve: float | None = None
```

In `run_track_a_cascade`, Gate 4 logic:
```python
# If margin inputs available, use combined gap; otherwise use growth-only gap
if all(v is not None for v in [inputs.current_revenue, inputs.current_fcf_margin,
                                 inputs.sustainable_fcf_margin, inputs.revenue_growth_for_margin_solve]):
    combined = reverse_dcf_combined_gap(...)
    growth_gap = combined.raw_value
else:
    growth_gap = growth_gap_result.raw_value
```

**Tests:** `engine/tests/scoring/quantitative/test_reverse_dcf.py`
- `solve_implied_margin`: Price implies 15% margin, sustainable is 25% → positive margin gap
- `solve_implied_margin`: Invalid inputs return None
- `reverse_dcf_combined_gap`: Growth gap negative but margin gap positive → returns margin gap
- `reverse_dcf_combined_gap`: Both gaps positive → returns the larger one
- `reverse_dcf_combined_gap`: Both gaps negative → returns the less negative one
- Existing `reverse_dcf_growth_gap` tests unchanged

---

## Fix 9: Break tie in style classifier using valuation signal

**Problem:** When signals split 2-2 between VALUE and GROWTH (no BLEND votes), the classifier returns BLEND. This dilutes the style signal for companies like Amazon that are clearly either expensive-growth or cheap-value, not a compromise.

**File:** `engine/src/margin_engine/scoring/style_classifier.py`

**Current code:**
```python
if len(winners) > 1:
    return InvestmentStyle.BLEND
```

**Fix:** When the tie is specifically VALUE vs GROWTH (2-2 split, no BLEND votes), break the tie using the valuation signal:

```python
if len(winners) > 1:
    # VALUE vs GROWTH tie: break using valuation signal (most investable)
    if (
        InvestmentStyle.VALUE in winners
        and InvestmentStyle.GROWTH in winners
        and InvestmentStyle.BLEND not in winners
        and ev_fcf_sector_percentile is not None
    ):
        if ev_fcf_sector_percentile <= _VALUATION_LOW:
            return InvestmentStyle.VALUE
        elif ev_fcf_sector_percentile >= _VALUATION_HIGH:
            return InvestmentStyle.GROWTH
    return InvestmentStyle.BLEND
```

This only changes behavior for the specific 2-2 VALUE/GROWTH split. All other ties still return BLEND.

**Tests:** `engine/tests/scoring/test_style_classifier.py`
- VALUE/GROWTH 2-2 split with low valuation percentile (20) → VALUE
- VALUE/GROWTH 2-2 split with high valuation percentile (80) → GROWTH
- VALUE/GROWTH 2-2 split with mid valuation percentile (50) → BLEND (no valuation signal)
- VALUE/GROWTH 2-2 split with valuation=None → BLEND (can't break tie)
- VALUE/BLEND tie → BLEND (unchanged behavior)
- BLEND/GROWTH tie → BLEND (unchanged behavior)
- 3-way tie → BLEND (unchanged behavior)

---

## Fix 10: Variable momentum weight by style

**Problem:** Momentum is fixed at 25% regardless of style or stage. Academic evidence shows momentum is strongest for growth stocks (trend persistence) and weakest for deep value (mean reversion).

**File:** `engine/src/margin_engine/scoring/v4_weights.py`

**Current state:** All 15 entries have `momentum=0.25`.

**Fix:** Vary momentum by style while keeping rows summing to 1.0. Redistribute from value weight:

| Style | Momentum (new) | Change |
|---|---|---|
| VALUE rows | 0.20 | -0.05 (add to value weight) |
| BLEND rows | 0.25 | unchanged |
| GROWTH rows | 0.30 | +0.05 (take from value weight) |

New matrix:

```python
_WEIGHT_MATRIX = {
    # Value: momentum 0.20 (was 0.25), value gets +0.05
    (InvestmentStyle.VALUE, GrowthStage.MATURE): (0.25, 0.40, 0.20, 0.15),
    (InvestmentStyle.VALUE, GrowthStage.STEADY_GROWTH): (0.25, 0.35, 0.20, 0.20),
    (InvestmentStyle.VALUE, GrowthStage.CYCLICAL): (0.25, 0.35, 0.20, 0.20),
    (InvestmentStyle.VALUE, GrowthStage.HIGH_GROWTH): (0.25, 0.30, 0.20, 0.25),
    (InvestmentStyle.VALUE, GrowthStage.TURNAROUND): (0.30, 0.30, 0.20, 0.20),
    # Blend: momentum 0.25 (unchanged)
    (InvestmentStyle.BLEND, GrowthStage.MATURE): (0.30, 0.25, 0.25, 0.20),
    (InvestmentStyle.BLEND, GrowthStage.STEADY_GROWTH): (0.30, 0.20, 0.25, 0.25),
    (InvestmentStyle.BLEND, GrowthStage.CYCLICAL): (0.30, 0.20, 0.25, 0.25),
    (InvestmentStyle.BLEND, GrowthStage.HIGH_GROWTH): (0.25, 0.15, 0.25, 0.35),
    (InvestmentStyle.BLEND, GrowthStage.TURNAROUND): (0.30, 0.25, 0.25, 0.20),
    # Growth: momentum 0.30 (was 0.25), value gets -0.05
    (InvestmentStyle.GROWTH, GrowthStage.MATURE): (0.25, 0.15, 0.30, 0.30),
    (InvestmentStyle.GROWTH, GrowthStage.STEADY_GROWTH): (0.25, 0.10, 0.30, 0.35),
    (InvestmentStyle.GROWTH, GrowthStage.CYCLICAL): (0.25, 0.10, 0.30, 0.35),
    (InvestmentStyle.GROWTH, GrowthStage.HIGH_GROWTH): (0.20, 0.05, 0.30, 0.45),
    (InvestmentStyle.GROWTH, GrowthStage.TURNAROUND): (0.30, 0.20, 0.30, 0.20),
}
```

Update module docstring: remove "Momentum constant at 0.25", add "Momentum varies: VALUE=0.20, BLEND=0.25, GROWTH=0.30".

**Constraint check:** No cell exceeds 0.45 ✓, quality >= 0.20 ✓, all sum to 1.0 ✓.

**Tests:** `engine/tests/scoring/test_v4_weights.py`
- All rows sum to 1.0
- No cell exceeds 0.45
- Quality >= 0.20 for all rows
- VALUE rows have momentum=0.20
- BLEND rows have momentum=0.25
- GROWTH rows have momentum=0.30
- Fallback still returns (0.30, 0.20, 0.25, 0.25)

---

## Fix 11: Make asset floor liquidation multiples regime-aware (minor)

**Problem:** Hardcoded sector liquidation multiples don't adjust for economic environment.

**File:** `engine/src/margin_engine/scoring/quantitative/asset_floor.py`

**Fix:** Add an optional `regime_multiplier` parameter (default 1.0):

```python
def asset_floor_valuation(
    net_cash: Decimal,
    tangible_book: Decimal,
    sector: GICSSector,
    shares_outstanding: int,
    regime_multiplier: float = 1.0,
) -> float:
    multiple = _SECTOR_LIQUIDATION_MULTIPLES.get(sector, _DEFAULT_MULTIPLE)
    multiple *= regime_multiplier  # <-- new
    total_floor = float(net_cash) + float(tangible_book) * multiple
    ...
```

Callers can pass `regime_multiplier=0.7` in CHEAP regime (distressed recoveries lower) or `1.2` in NORMAL (orderly liquidation recovers more). Default behavior is unchanged.

**Tests:** `engine/tests/scoring/quantitative/test_asset_floor.py`
- Default (no multiplier): unchanged behavior
- regime_multiplier=0.7: floor is 30% lower
- regime_multiplier=1.2: floor is 20% higher

---

## Fix 12: Floor operating leverage at meaningful minimum (minor)

**Problem:** When revenue is flat and opex grows, operating leverage = 0.0. Companies managing costs during flat revenue get no credit.

**File:** `engine/src/margin_engine/scoring/quantitative/operating_leverage.py`

**Fix:** When revenue growth is near-zero but opex growth is negative (cost cutting), return a positive score:

```python
# In the compute logic, before the main ratio:
if revenue_growth_rate <= 0.01 and opex_growth_rate < 0:
    # Cost discipline during flat/declining revenue — reward it
    raw_value = min(abs(opex_growth_rate) * 5.0, 2.0)  # cap at 2.0
```

This gives credit for cost management without rewarding stagnation.

**Tests:** `engine/tests/scoring/quantitative/test_operating_leverage.py`
- Flat revenue (1%), opex declining (-5%): raw_value = min(0.25, 2.0) = 0.25
- Flat revenue (1%), opex declining (-20%): raw_value = min(1.0, 2.0) = 1.0
- Growing revenue (10%), growing opex (5%): unchanged (10/5 = 2.0)
- Growing revenue, zero opex growth: unchanged (cap at 10.0)

---

## Fix 13: Use 3-year median effective tax rate for ROIC (minor)

**Problem:** ROIC calculations use `effective_tax_rate` which is volatile due to NOLs, one-time items, and jurisdiction changes.

**File:** `engine/src/margin_engine/scoring/v3_intermediates.py`

**Fix:** Add a helper that computes median tax rate from history, and use it in `compute_compounding_power`:

```python
def _median_tax_rate(history: FinancialHistory) -> float:
    """Return median effective tax rate across all periods."""
    rates = [p.current_income.effective_tax_rate for p in history.periods]
    if not rates:
        return 0.21  # US statutory fallback
    return statistics.median(rates)
```

In `compute_compounding_power`, replace per-period `tax_rate` with the median when computing NOPAT for the stability (CV/MAD) calculation. Keep earliest/latest NOPAT using their own rates for the incremental ROIC calculation (point-in-time accuracy matters there).

**Tests:** `engine/tests/scoring/test_v3_intermediates.py`
- History with volatile tax rates [0.05, 0.30, 0.21, 0.18, 0.22] — stability uses median 0.21
- History with consistent tax rates — no meaningful change
- Empty history returns 0.21 fallback

---

## Fix 14: Document TAM headroom as externally sourced (minor)

**Problem:** Track C's `tam_headroom` is an input parameter, not computed. TAM estimates are unreliable and can dominate conviction assessment.

**File:** `engine/src/margin_engine/scoring/v3_track_c_cascade.py`

**Fix:** Cap the impact of TAM headroom in the growth durability calculation:

```python
# Current:
growth_durability = min(tam_headroom / 3, 2.0) * (1 - max(-deceleration, 0) / 20)

# Fix: Cap TAM contribution at 1.5x (was 2.0x) and add a confidence discount
tam_factor = min(tam_headroom / 3, 1.5)  # reduced cap
growth_durability = tam_factor * (1 - max(-deceleration, 0) / 20)
```

Also in `v3_track_c_thresholds.py`, for EXCEPTIONAL conviction, change `tam_headroom > 5` to `tam_headroom > 5 and tam_headroom < 50` to reject implausible TAM estimates:

```python
if (
    gates_passed >= 4
    and rule_of_40 >= 50
    and incremental_roic > 2 * wacc
    and tam_headroom > 5
    and tam_headroom < 50  # reject implausible TAM
):
    return ConvictionLevel.EXCEPTIONAL
```

**Tests:**
- TAM=100 → capped contribution, NOT exceptional (implausible)
- TAM=8 → exceptional eligible (reasonable)
- TAM=2 → doesn't pass gate 4 (too small)
- Existing Track C cascade tests updated for new cap

---

## Execution Order

Fixes are independent. Suggested order (easiest/highest-impact first):

1. **Fix 1** — MEDIUM sizing (5 min, low risk)
2. **Fix 4** — Track C sizing (5 min, low risk)
3. **Fix 7** — Catalyst corroboration (15 min, medium risk — threshold recalibration)
4. **Fix 9** — Style classifier tie-breaking (10 min, low risk)
5. **Fix 10** — Variable momentum weight (10 min, low risk)
6. **Fix 2** — Tiered IV gate (15 min, medium risk)
7. **Fix 6** — Weighted moat signatures (15 min, medium risk)
8. **Fix 5** — MAD for compounding stability (15 min, medium risk)
9. **Fix 3** — Ensemble convergence for asset-light (20 min, medium risk)
10. **Fix 8** — Margin expansion solver (30 min, higher risk — new solver)
11. **Fix 11** — Regime-aware asset floor (5 min, low risk)
12. **Fix 12** — Operating leverage floor (5 min, low risk)
13. **Fix 13** — Median tax rate (10 min, low risk)
14. **Fix 14** — TAM headroom cap (5 min, low risk)

After all fixes, run the full engine test suite: `uv run pytest engine/tests/ -v`

Commit after each fix with message format: `fix(engine): <description of fix>`
