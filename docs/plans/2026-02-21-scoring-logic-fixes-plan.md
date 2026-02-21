# Scoring Logic Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 14 identified issues in the scoring pipeline that systematically limit candidate quality and portfolio construction.

**Architecture:** All changes are in `engine/src/margin_engine/scoring/`. Each fix is independent — TDD for every change, one commit per fix. Detailed code specs in `docs/plans/2026-02-20-scoring-logic-fixes-prompt.md`.

**Tech Stack:** Python 3.13, pytest, Pydantic, Decimal math

**Branch:** `feat/scoring-logic-fixes` (create from main)

**Test command:** `uv run pytest engine/tests/ -v`

**Test conventions:** Class-based tests, no pytest fixtures, local `_helper()` builders, `Decimal` for financial data, `pytest.approx()` for floats, docstrings explain "why".

---

### Task 1: MEDIUM conviction gets starter positions

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_position_sizing.py`
- Modify: `engine/tests/scoring/test_v3_position_sizing.py`

**Step 1: Write failing tests**

Add to the existing `TestV3PositionSizing` class in `test_v3_position_sizing.py`:

```python
def test_medium_compounder(self):
    """MEDIUM conviction compounders get 4% starter position."""
    assert compute_v3_position_size("compounder", ConvictionLevel.MEDIUM) == 4.0

def test_medium_mispricing(self):
    """MEDIUM conviction mispricings get 3% starter position."""
    assert compute_v3_position_size("mispricing", ConvictionLevel.MEDIUM) == 3.0

def test_medium_efficient_growth(self):
    """MEDIUM conviction efficient_growth gets 3% starter position."""
    assert compute_v3_position_size("efficient_growth", ConvictionLevel.MEDIUM) == 3.0

def test_medium_both(self):
    """MEDIUM conviction both gets 5% starter position."""
    assert compute_v3_position_size("both", ConvictionLevel.MEDIUM) == 5.0

def test_medium_compounder_growth(self):
    """MEDIUM conviction compounder_growth gets 5% starter position."""
    assert compute_v3_position_size("compounder_growth", ConvictionLevel.MEDIUM) == 5.0

def test_medium_all_three(self):
    """MEDIUM conviction all_three gets 5% starter position."""
    assert compute_v3_position_size("all_three", ConvictionLevel.MEDIUM) == 5.0

def test_none_still_zero_all_types(self):
    """NONE conviction returns 0.0 for every opportunity type."""
    for track in ("compounder", "mispricing", "efficient_growth", "both", "compounder_growth", "all_three"):
        assert compute_v3_position_size(track, ConvictionLevel.NONE) == 0.0

def test_exceptional_and_high_unchanged(self):
    """Verify EXCEPTIONAL and HIGH values were not modified."""
    assert compute_v3_position_size("compounder", ConvictionLevel.EXCEPTIONAL) == 15.0
    assert compute_v3_position_size("compounder", ConvictionLevel.HIGH) == 8.0
    assert compute_v3_position_size("mispricing", ConvictionLevel.EXCEPTIONAL) == 12.0
    assert compute_v3_position_size("mispricing", ConvictionLevel.HIGH) == 6.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_position_sizing.py -v -k "medium"`
Expected: FAIL — current MEDIUM values are 0.0

**Step 3: Implement the fix**

In `v3_position_sizing.py`, update `_SIZING` dict — change MEDIUM from 0.0 to the new values:
- compounder: 4.0, mispricing: 3.0, efficient_growth: 3.0, both: 5.0, compounder_growth: 5.0, all_three: 5.0

Update the module docstring — remove "Medium = 0% (not actionable)".

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_v3_position_sizing.py -v`
Expected: ALL PASS

**Step 5: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS (check for any tests that asserted MEDIUM == 0.0)

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_position_sizing.py engine/tests/scoring/test_v3_position_sizing.py
git commit -m "fix(engine): MEDIUM conviction gets starter positions (not 0%)"
```

---

### Task 2: Increase Track C position sizing

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_position_sizing.py`
- Modify: `engine/tests/scoring/test_v3_position_sizing.py`

**Step 1: Write failing tests**

Add to `TestV3PositionSizing`:

```python
def test_efficient_growth_exceptional_matches_compounder(self):
    """Track C EXCEPTIONAL should match compounder at 15%."""
    assert compute_v3_position_size("efficient_growth", ConvictionLevel.EXCEPTIONAL) == 15.0

def test_efficient_growth_high_matches_compounder(self):
    """Track C HIGH should match compounder at 8%."""
    assert compute_v3_position_size("efficient_growth", ConvictionLevel.HIGH) == 8.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_position_sizing.py -v -k "efficient_growth"`
Expected: FAIL — current values are EXCEPTIONAL=12.0, HIGH=7.0

**Step 3: Implement the fix**

In `v3_position_sizing.py`, update `efficient_growth` entry:
- EXCEPTIONAL: 12.0 -> 15.0
- HIGH: 7.0 -> 8.0
- MEDIUM: already 3.0 from Task 1

**Step 4: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS (fix any tests that asserted old values)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_position_sizing.py engine/tests/scoring/test_v3_position_sizing.py
git commit -m "fix(engine): increase Track C position sizing to match compounder"
```

---

### Task 3: Corroborated catalyst strength

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_intermediates.py`
- Modify: `engine/src/margin_engine/scoring/v3_cascade.py`
- Modify: `engine/src/margin_engine/scoring/v3_thresholds.py`
- Modify: `engine/tests/scoring/test_v3_intermediates.py`
- Modify: `engine/tests/scoring/test_v3_cascade.py`
- Modify: `engine/tests/scoring/test_v3_thresholds.py`

**Step 1: Write failing tests for the formula change**

Add to the catalyst test class in `test_v3_intermediates.py`:

```python
def test_catalyst_all_three_at_70(self):
    """Uniform signals: 0.50*70 + 0.30*70 + 0.20*70 = 70.0."""
    result = compute_catalyst_strength(70.0, 70.0, 70.0)
    assert result == pytest.approx(70.0)

def test_catalyst_single_strong_signal(self):
    """Single signal at 90 with others at 0: 0.50*90 = 45.0 (was 90.0)."""
    result = compute_catalyst_strength(0.0, 0.0, 90.0)
    assert result == pytest.approx(45.0)

def test_catalyst_mixed_signals(self):
    """80, 50, 20: 0.50*80 + 0.30*50 + 0.20*20 = 59.0."""
    result = compute_catalyst_strength(80.0, 50.0, 20.0)
    assert result == pytest.approx(59.0)

def test_catalyst_all_zero(self):
    """All zero signals: result = 0.0."""
    result = compute_catalyst_strength(0.0, 0.0, 0.0)
    assert result == pytest.approx(0.0)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py -v -k "catalyst"`
Expected: FAIL — current formula uses max(), not weighted blend

**Step 3: Implement the formula change**

In `v3_intermediates.py`, replace `compute_catalyst_strength` body:

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

**Step 4: Run catalyst tests**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py -v -k "catalyst"`
Expected: PASS

**Step 5: Update threshold constants**

In `v3_thresholds.py`:
- `_B_EXCEPTIONAL_CATALYST`: 80.0 -> 55.0
- `_B_HIGH_CATALYST`: 60.0 -> 40.0

In `v3_cascade.py`:
- `catalyst_threshold`: 60.0 -> 40.0

**Step 6: Fix any existing tests that assert old threshold/formula values**

Check and update tests in:
- `test_v3_cascade.py` (Track B catalyst gate tests)
- `test_v3_thresholds.py` (threshold comparison tests)

**Step 7: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_intermediates.py engine/src/margin_engine/scoring/v3_cascade.py engine/src/margin_engine/scoring/v3_thresholds.py engine/tests/scoring/test_v3_intermediates.py engine/tests/scoring/test_v3_cascade.py engine/tests/scoring/test_v3_thresholds.py
git commit -m "fix(engine): corroborated catalyst strength with weighted blend"
```

---

### Task 4: Style classifier tie-breaking with valuation signal

**Files:**
- Modify: `engine/src/margin_engine/scoring/style_classifier.py`
- Modify: `engine/tests/scoring/test_style_classifier.py`

**Step 1: Write failing tests**

Add to the test class in `test_style_classifier.py`. These tests need inputs that produce a 2-2 VALUE/GROWTH split. Read the current `classify_investment_style` signature to construct appropriate inputs. The key parameters are the 4 signal votes + `ev_fcf_sector_percentile`.

```python
def test_value_growth_tie_low_valuation_breaks_to_value(self):
    """VALUE/GROWTH 2-2 split with cheap valuation → VALUE."""
    # Construct inputs that produce VALUE=2, GROWTH=2, BLEND=0
    # Then ev_fcf_sector_percentile=20 (below _VALUATION_LOW=33.33) → VALUE
    ...
    assert style == InvestmentStyle.VALUE

def test_value_growth_tie_high_valuation_breaks_to_growth(self):
    """VALUE/GROWTH 2-2 split with expensive valuation → GROWTH."""
    # ev_fcf_sector_percentile=80 (above _VALUATION_HIGH=66.67) → GROWTH
    ...
    assert style == InvestmentStyle.GROWTH

def test_value_growth_tie_mid_valuation_stays_blend(self):
    """VALUE/GROWTH 2-2 split with mid valuation → BLEND (no signal)."""
    # ev_fcf_sector_percentile=50 → BLEND
    ...
    assert style == InvestmentStyle.BLEND

def test_value_growth_tie_no_valuation_stays_blend(self):
    """VALUE/GROWTH 2-2 split with valuation=None → BLEND."""
    ...
    assert style == InvestmentStyle.BLEND
```

Read the style_classifier.py to understand exactly how votes are tallied (which parameters produce which votes) and construct accurate test inputs.

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_style_classifier.py -v -k "tie"`
Expected: FAIL — all ties currently return BLEND

**Step 3: Implement the fix**

In `style_classifier.py`, replace the `if len(winners) > 1: return InvestmentStyle.BLEND` block:

```python
if len(winners) > 1:
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

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/test_style_classifier.py -v`
Expected: ALL PASS

**Step 5: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/style_classifier.py engine/tests/scoring/test_style_classifier.py
git commit -m "fix(engine): break VALUE/GROWTH tie using valuation signal"
```

---

### Task 5: Variable momentum weight by style

**Files:**
- Modify: `engine/src/margin_engine/scoring/v4_weights.py`
- Modify: `engine/tests/scoring/test_v4_weights.py`

**Step 1: Write failing tests**

Add to the test class in `test_v4_weights.py`:

```python
def test_value_rows_momentum_020(self):
    """All VALUE rows should have momentum=0.20."""
    for stage in GrowthStage:
        q, v, m, g = weights_for_style_stage(InvestmentStyle.VALUE, stage)
        assert m == pytest.approx(0.20), f"VALUE/{stage} momentum should be 0.20, got {m}"

def test_blend_rows_momentum_025(self):
    """All BLEND rows should have momentum=0.25."""
    for stage in GrowthStage:
        q, v, m, g = weights_for_style_stage(InvestmentStyle.BLEND, stage)
        assert m == pytest.approx(0.25), f"BLEND/{stage} momentum should be 0.25, got {m}"

def test_growth_rows_momentum_030(self):
    """All GROWTH rows should have momentum=0.30."""
    for stage in GrowthStage:
        q, v, m, g = weights_for_style_stage(InvestmentStyle.GROWTH, stage)
        assert m == pytest.approx(0.30), f"GROWTH/{stage} momentum should be 0.30, got {m}"

def test_all_rows_sum_to_one(self):
    """Every style/stage combination sums to 1.0."""
    for style in InvestmentStyle:
        for stage in GrowthStage:
            q, v, m, g = weights_for_style_stage(style, stage)
            assert q + v + m + g == pytest.approx(1.0), f"{style}/{stage} sums to {q+v+m+g}"

def test_no_cell_exceeds_045(self):
    """No single weight exceeds 0.45."""
    for style in InvestmentStyle:
        for stage in GrowthStage:
            q, v, m, g = weights_for_style_stage(style, stage)
            for w, name in [(q, "quality"), (v, "value"), (m, "momentum"), (g, "growth")]:
                assert w <= 0.45, f"{style}/{stage} {name}={w} exceeds 0.45"

def test_quality_at_least_020(self):
    """Quality weight >= 0.20 for all rows."""
    for style in InvestmentStyle:
        for stage in GrowthStage:
            q, _, _, _ = weights_for_style_stage(style, stage)
            assert q >= 0.20, f"{style}/{stage} quality={q} below 0.20"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v4_weights.py -v`
Expected: FAIL — VALUE rows currently have momentum=0.25, GROWTH rows have momentum=0.25

**Step 3: Implement the fix**

Replace `_WEIGHT_MATRIX` in `v4_weights.py` with the new matrix from the spec (see `2026-02-20-scoring-logic-fixes-prompt.md` Fix 10 for exact values). Update the module docstring.

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/test_v4_weights.py -v`
Expected: ALL PASS

**Step 5: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/scoring/v4_weights.py engine/tests/scoring/test_v4_weights.py
git commit -m "fix(engine): variable momentum weight by style (VALUE=0.20, GROWTH=0.30)"
```

---

### Task 6: Tiered IV gate based on quality floor

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_cascade.py`
- Modify: `engine/tests/scoring/test_v3_cascade.py`

**Step 1: Write failing tests**

Add Track B tests in `test_v3_cascade.py`. Build test inputs using the existing `_period()` and `_profile()` helpers. Key scenarios:

```python
def test_high_quality_at_70pct_iv_passes_gate1(self):
    """ROIC=12% business at 70% of IV passes Gate 1 (25% margin requirement)."""
    # Build TrackBInputs with ROIC=12% (quality_floor >= 1.0)
    # Set current_price = 0.70 * ensemble_iv
    # Assert gates_passed >= 1

def test_improving_at_62pct_iv_passes_gate1(self):
    """ROIC=5%, improving business at 62% of IV passes Gate 1 (35% margin)."""
    # quality_floor > 0 → iv_discount = 0.65
    # 0.62 < 0.65 → passes

def test_low_quality_at_62pct_iv_fails_gate1(self):
    """ROIC=3%, not improving at 62% of IV fails Gate 1 (40% margin still)."""
    # quality_floor = 0 → iv_discount = 0.60
    # 0.62 > 0.60 → fails

def test_low_quality_at_55pct_iv_passes_gate1(self):
    """ROIC=3%, not improving at 55% of IV passes Gate 1."""
    # 0.55 < 0.60 → passes
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_cascade.py -v -k "quality"`
Expected: FAIL

**Step 3: Implement the fix**

In `v3_cascade.py` `run_track_b_cascade`:
1. Move `quality_floor` computation before Gate 1 (currently in Gate 4)
2. Add tiered IV discount logic based on quality_floor value
3. Gate 4 reuses the same quality_floor (no recomputation)

See spec Fix 2 for exact code.

**Step 4: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS (fix any Track B tests asserting old gate behavior)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_cascade.py engine/tests/scoring/test_v3_cascade.py
git commit -m "fix(engine): tiered IV gate based on quality floor score"
```

---

### Task 7: Weighted moat signatures by durability

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/moat_durability.py`
- Modify: `engine/tests/scoring/quantitative/test_moat_durability.py`

**Step 1: Write failing tests**

Add to test class in `test_moat_durability.py`. These tests need to construct `FinancialHistory` objects that trigger specific signature detections. Read the existing tests to understand how they construct histories that trigger each signature.

```python
def test_all_four_signatures_weighted_max(self):
    """All 4 signatures → raw_value = 4.0 (normalized from 4.5)."""
    # Build history that triggers all 4 signatures
    result = moat_durability_score(history)
    assert result.raw_value == pytest.approx(4.0, rel=0.01)

def test_switching_costs_plus_pricing_power(self):
    """switching_costs + pricing_power → (1.5+1.25)*4/4.5 ≈ 2.44."""
    result = moat_durability_score(history)
    assert result.raw_value == pytest.approx(2.44, rel=0.01)

def test_scale_plus_capital_efficiency(self):
    """scale_economics + capital_efficiency → (1.0+0.75)*4/4.5 ≈ 1.56."""
    result = moat_durability_score(history)
    assert result.raw_value == pytest.approx(1.56, rel=0.01)

def test_switching_costs_only(self):
    """switching_costs only → 1.5*4/4.5 ≈ 1.33."""
    result = moat_durability_score(history)
    assert result.raw_value == pytest.approx(1.33, rel=0.01)

def test_no_signatures_zero(self):
    """No signatures → raw_value = 0.0."""
    result = moat_durability_score(history)
    assert result.raw_value == pytest.approx(0.0)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_moat_durability.py -v`
Expected: FAIL — current uses unweighted count

**Step 3: Implement the fix**

In `moat_durability.py`:
1. Add `_SIGNATURE_WEIGHTS` dict
2. Replace `float(len(signatures))` with normalized weighted sum

See spec Fix 6 for exact code.

**Step 4: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS (check threshold tests in v3_thresholds.py still pass with new float values)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/moat_durability.py engine/tests/scoring/quantitative/test_moat_durability.py
git commit -m "fix(engine): weight moat signatures by durability"
```

---

### Task 8: MAD for compounding power stability

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_intermediates.py`
- Modify: `engine/tests/scoring/test_v3_intermediates.py`

**Step 1: Write failing tests**

Add to test class in `test_v3_intermediates.py`. Build `FinancialHistory` with specific ROIC patterns:

```python
def test_steady_roic_stability_near_one(self):
    """Steady ROICs [0.15, 0.16, 0.15, 0.14, 0.15] → stability near 1.0."""
    # Build history with these ROICs
    result = compute_compounding_power(history)
    # MAD of these values is very small → stability ≈ 1.0
    assert result > 0  # positive compounding power

def test_lumpy_roic_mad_more_forgiving_than_cv(self):
    """Lumpy ROICs [0.10, 0.25, 0.12, 0.22, 0.14] → MAD higher stability than CV."""
    # Build history, verify positive result
    result = compute_compounding_power(history)
    assert result > 0

def test_single_outlier_mad_forgiving(self):
    """Single outlier [0.15, 0.15, 0.15, 0.15, 0.40] → MAD much more forgiving."""
    # Build history, verify positive result
    result = compute_compounding_power(history)
    assert result > 0

def test_identical_roics_stability_one(self):
    """Identical ROICs [0.12, 0.12, 0.12] → stability = 1.0, no penalty."""
    result = compute_compounding_power(history)
    assert result > 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py -v -k "roic or lumpy or outlier or identical"`
Expected: Some may already pass with current CV — the key test is lumpy/outlier producing higher values with MAD

**Step 3: Implement the fix**

In `v3_intermediates.py` `compute_compounding_power`:
Replace CV calculation with MAD:

```python
median_roic = statistics.median(roics)
mad = statistics.median([abs(r - median_roic) for r in roics])
normalized_mad = min(mad / max(abs(median_roic), 0.001), 1.0)
stability = 1.0 - normalized_mad
return inc_roic * reinvestment_rate * max(stability, 0.0)
```

**Step 4: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS (update any golden value tests that depend on exact compounding_power values)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/v3_intermediates.py engine/tests/scoring/test_v3_intermediates.py
git commit -m "fix(engine): use MAD instead of CV for compounding power stability"
```

---

### Task 9: Relax ensemble convergence for asset-light

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/ensemble_valuation.py`
- Modify: `engine/src/margin_engine/scoring/v3_cascade.py`
- Modify: `engine/tests/scoring/quantitative/test_ensemble_valuation.py`

**Step 1: Write failing tests**

Add to test class in `test_ensemble_valuation.py`:

```python
def test_asset_light_dcf_peer_convergence(self):
    """Tech company: DCF=100, peer=110, asset_floor=5 → converges on DCF+peer."""
    from margin_engine.models.financial import GICSSector
    result = compute_ensemble_valuation(
        dcf_iv=100.0, owner_earnings_iv=90.0,
        asset_floor_iv=5.0, peer_comparison_iv=110.0,
        sector=GICSSector.TECHNOLOGY,
    )
    assert result.converged is True
    assert result.converging_count == 2

def test_same_inputs_no_sector_does_not_converge(self):
    """Same inputs without sector → does NOT converge (only 2 of 4)."""
    result = compute_ensemble_valuation(
        dcf_iv=100.0, owner_earnings_iv=90.0,
        asset_floor_iv=5.0, peer_comparison_iv=110.0,
    )
    assert result.converged is False

def test_non_tech_same_inputs_does_not_converge(self):
    """Non-tech company with same inputs → does NOT converge."""
    from margin_engine.models.financial import GICSSector
    result = compute_ensemble_valuation(
        dcf_iv=100.0, owner_earnings_iv=90.0,
        asset_floor_iv=5.0, peer_comparison_iv=110.0,
        sector=GICSSector.FINANCIALS,
    )
    assert result.converged is False
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_ensemble_valuation.py -v -k "asset_light or non_tech"`
Expected: FAIL — sector parameter doesn't exist yet

**Step 3: Implement the fix**

In `ensemble_valuation.py`:
1. Add `_ASSET_LIGHT_SECTORS` frozenset
2. Add `sector: GICSSector | None = None` parameter
3. Add asset-light fallback after main convergence check

In `v3_cascade.py`:
4. Pass `sector=inputs.profile.sector` to `compute_ensemble_valuation` in `run_track_b_cascade`

See spec Fix 3 for exact code.

**Step 4: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/ensemble_valuation.py engine/src/margin_engine/scoring/v3_cascade.py engine/tests/scoring/quantitative/test_ensemble_valuation.py
git commit -m "fix(engine): relax ensemble convergence for asset-light sectors"
```

---

### Task 10: Margin expansion solver for reverse DCF

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/reverse_dcf.py`
- Modify: `engine/src/margin_engine/scoring/v3_cascade.py`
- Modify: `engine/tests/scoring/quantitative/test_reverse_dcf.py`

**Step 1: Write failing tests**

Add to test class in `test_reverse_dcf.py`:

```python
def test_solve_implied_margin_positive_gap(self):
    """Price implies ~15% margin, sustainable is 25% → positive gap."""
    implied = solve_implied_margin(
        current_price=100.0, current_revenue=500.0,
        current_fcf_margin=0.10, wacc=0.10,
        terminal_growth=0.025, revenue_growth=0.05,
        shares_outstanding=1,
    )
    assert implied is not None
    assert implied < 0.25  # Market implies less than sustainable

def test_solve_implied_margin_invalid_inputs(self):
    """Invalid inputs return None."""
    assert solve_implied_margin(0.0, 500.0, 0.1, 0.1, 0.025, 0.05, 1) is None
    assert solve_implied_margin(100.0, 0.0, 0.1, 0.1, 0.025, 0.05, 1) is None
    assert solve_implied_margin(100.0, 500.0, 0.1, 0.1, 0.025, 0.05, 0) is None

def test_combined_gap_margin_better_than_growth(self):
    """Growth gap negative but margin gap positive → returns margin gap."""
    result = reverse_dcf_combined_gap(
        current_price=..., current_fcf=..., current_revenue=...,
        current_fcf_margin=..., sustainable_fcf_margin=...,
        wacc=..., terminal_growth=..., shares_outstanding=...,
        sustainable_growth_rate=..., revenue_growth_for_margin_solve=...,
    )
    assert result.raw_value > 0  # Margin gap wins

def test_combined_gap_both_positive_returns_larger(self):
    """Both gaps positive → returns the larger one."""
    # Construct inputs where both are positive but margin gap is larger
    ...

def test_combined_gap_both_negative_returns_less_negative(self):
    """Both gaps negative → returns the less negative one."""
    ...
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_reverse_dcf.py -v -k "implied_margin or combined"`
Expected: FAIL — functions don't exist yet

**Step 3: Implement solve_implied_margin and reverse_dcf_combined_gap**

In `reverse_dcf.py`, add both new functions. See spec Fix 8 for exact code.

**Step 4: Run reverse DCF tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_reverse_dcf.py -v`
Expected: ALL PASS (existing tests unchanged)

**Step 5: Add optional fields to TrackAInputs and wire into cascade**

In `v3_cascade.py`:
1. Add optional fields to `TrackAInputs`: `current_revenue`, `current_fcf_margin`, `sustainable_fcf_margin`, `revenue_growth_for_margin_solve`
2. Update Gate 4 logic to use combined gap when fields are available

**Step 6: Run full engine suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/reverse_dcf.py engine/src/margin_engine/scoring/v3_cascade.py engine/tests/scoring/quantitative/test_reverse_dcf.py
git commit -m "fix(engine): add margin expansion solver to reverse DCF"
```

---

### Task 11: Regime-aware asset floor

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/asset_floor.py`
- Modify: `engine/tests/scoring/quantitative/test_asset_floor.py`

**Step 1: Write failing tests**

```python
def test_regime_multiplier_07_lowers_floor(self):
    """Distressed regime (0.7) reduces floor by 30%."""
    base = asset_floor_valuation(net_cash=..., tangible_book=..., sector=..., shares_outstanding=...)
    stressed = asset_floor_valuation(net_cash=..., tangible_book=..., sector=..., shares_outstanding=..., regime_multiplier=0.7)
    assert stressed < base

def test_regime_multiplier_12_raises_floor(self):
    """Normal regime (1.2) increases floor by 20%."""
    base = asset_floor_valuation(...)
    normal = asset_floor_valuation(..., regime_multiplier=1.2)
    assert normal > base

def test_default_regime_unchanged(self):
    """Default (no multiplier) matches existing behavior."""
    # Compare with and without parameter — should be identical
```

**Step 2: Run tests, verify failure, implement, verify pass**

Add `regime_multiplier: float = 1.0` parameter, multiply sector multiple by it.

**Step 3: Run full suite and commit**

```bash
git commit -m "fix(engine): regime-aware asset floor liquidation multiples"
```

---

### Task 12: Operating leverage cost-cutting floor

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/operating_leverage.py`
- Modify: `engine/tests/scoring/quantitative/test_operating_leverage.py`

**Step 1: Write failing tests**

```python
def test_flat_revenue_declining_opex_positive(self):
    """Flat revenue (1%), opex declining (-5%) → positive raw_value."""
    # Build history: rev_growth ~1%, opex_growth ~-5%
    result = operating_leverage(history)
    assert result.raw_value == pytest.approx(0.25, rel=0.1)

def test_flat_revenue_large_opex_decline_capped(self):
    """Flat revenue, opex -20% → raw_value capped at 2.0."""
    result = operating_leverage(history)
    assert result.raw_value <= 2.0
    assert result.raw_value > 0
```

**Step 2: Implement**

Add early return before main ratio: `if revenue_growth_rate <= 0.01 and opex_growth_rate < 0: raw_value = min(abs(opex_growth_rate) * 5.0, 2.0)`

**Step 3: Run full suite and commit**

```bash
git commit -m "fix(engine): floor operating leverage for cost discipline"
```

---

### Task 13: Median tax rate for ROIC stability

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_intermediates.py`
- Modify: `engine/tests/scoring/test_v3_intermediates.py`

**Step 1: Write failing tests**

```python
def test_median_tax_rate_volatile_rates(self):
    """Volatile tax rates [0.05, 0.30, 0.21, 0.18, 0.22] → median 0.21."""
    from margin_engine.scoring.v3_intermediates import _median_tax_rate
    # Build history with these tax rates
    result = _median_tax_rate(history)
    assert result == pytest.approx(0.21)

def test_median_tax_rate_empty_history(self):
    """Empty history → 0.21 fallback."""
    from margin_engine.scoring.v3_intermediates import _median_tax_rate
    result = _median_tax_rate(empty_history)
    assert result == pytest.approx(0.21)
```

**Step 2: Implement**

Add `_median_tax_rate()` helper. Use it in `compute_compounding_power` for the stability (MAD) calculation only — keep point-in-time rates for incremental ROIC.

**Step 3: Run full suite and commit**

```bash
git commit -m "fix(engine): use median tax rate for ROIC stability calculation"
```

---

### Task 14: TAM headroom cap

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_track_c_cascade.py`
- Modify: `engine/src/margin_engine/scoring/v3_track_c_thresholds.py`
- Modify: `engine/tests/scoring/` (Track C tests)

**Step 1: Write failing tests**

```python
def test_tam_100_not_exceptional(self):
    """TAM=100 is implausible → NOT exceptional even if all other gates pass."""
    # Build inputs with tam_headroom=100, all other gates passing
    result = compute_track_c_conviction(...)
    assert result != ConvictionLevel.EXCEPTIONAL

def test_tam_8_exceptional_eligible(self):
    """TAM=8 is reasonable → exceptional eligible."""
    result = compute_track_c_conviction(...)
    # Could be EXCEPTIONAL if all other conditions met

def test_growth_durability_cap_at_15(self):
    """TAM factor capped at 1.5 (was 2.0)."""
    # tam_headroom=10: min(10/3, 1.5) = 1.5 (was 2.0)
    # Verify the growth_durability value reflects the lower cap
```

**Step 2: Implement**

In `v3_track_c_cascade.py`: Change `min(tam_headroom / 3.0, 2.0)` to `min(tam_headroom / 3.0, 1.5)`.

In `v3_track_c_thresholds.py`: Add `and tam_headroom < 50` to EXCEPTIONAL conviction check.

**Step 3: Run full suite and commit**

```bash
git commit -m "fix(engine): cap TAM headroom impact and reject implausible estimates"
```

---

### Task 15: Final verification

**Step 1: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL 784+ tests PASS

**Step 2: Run with coverage**

Run: `uv run pytest --cov=margin_engine engine/ -v`
Expected: engine/ coverage >= 95%

**Step 3: Verify all 14 commits exist**

Run: `git log --oneline -15`
Expected: 14 `fix(engine):` commits on the feature branch
