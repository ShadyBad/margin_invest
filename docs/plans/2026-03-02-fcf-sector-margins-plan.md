# FCF Sector-Specific Margins + UI Clarity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the global -5% FCF margin floor with sector-specific thresholds and show the full multi-year rule inline in the UI.

**Architecture:** Add `sector_margin_overrides` dict to `FcfDistressConfig`, look up sector-specific floor in `fcf_distress_check_v2`, thread `computed_metrics` through the API layer to the web `FilterResultResponse`, and update the filter card display.

**Tech Stack:** Python (engine + API), TypeScript/React (web), Pydantic, Vitest

---

### Task 1: Add sector_margin_overrides to FcfDistressConfig

**Files:**
- Modify: `engine/src/margin_engine/config/filter_config.py:95-106`
- Test: `engine/tests/scoring/filters/test_fcf_distress.py`

**Step 1: Write failing test**

Add to `engine/tests/scoring/filters/test_fcf_distress.py`:

```python
class TestFcfDistressConfigSectorOverrides:
    """Tests for sector-specific FCF margin overrides in config."""

    def test_default_min_fcf_margin_is_zero(self):
        """Default min_fcf_margin should be 0.0 (not -0.05)."""
        config = FcfDistressConfig()
        assert config.min_fcf_margin == 0.0

    def test_get_min_fcf_margin_returns_sector_override(self):
        """get_min_fcf_margin returns the sector-specific floor when available."""
        config = FcfDistressConfig()
        assert config.get_min_fcf_margin("information technology") == 0.10

    def test_get_min_fcf_margin_returns_default_for_unknown(self):
        """get_min_fcf_margin falls back to min_fcf_margin for unknown sectors."""
        config = FcfDistressConfig()
        assert config.get_min_fcf_margin("unknown sector") == 0.0

    def test_get_min_fcf_margin_returns_default_for_none(self):
        """get_min_fcf_margin falls back to min_fcf_margin when sector is None."""
        config = FcfDistressConfig()
        assert config.get_min_fcf_margin(None) == 0.0

    def test_sector_margin_overrides_all_sectors(self):
        """All 9 scoreable GICS sectors should have explicit overrides."""
        config = FcfDistressConfig()
        expected_sectors = {
            "information technology", "communication services",
            "health care", "consumer staples", "consumer discretionary",
            "industrials", "materials", "energy", "utilities",
        }
        assert set(config.sector_margin_overrides.keys()) == expected_sectors

    def test_custom_override_via_config(self):
        """Custom sector_margin_overrides should work."""
        config = FcfDistressConfig(sector_margin_overrides={"energy": 0.05})
        assert config.get_min_fcf_margin("energy") == 0.05
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/filters/test_fcf_distress.py::TestFcfDistressConfigSectorOverrides -v`
Expected: FAIL — `min_fcf_margin` is -0.05, `get_min_fcf_margin` doesn't exist, `sector_margin_overrides` doesn't exist.

**Step 3: Implement config changes**

In `engine/src/margin_engine/config/filter_config.py`, replace the `FcfDistressConfig` class (lines 95-106):

```python
class FcfDistressConfig(BaseModel):
    """Free Cash Flow distress filter configuration."""

    positive_years_required: int = 3
    lookback_years: int = 5
    min_fcf_margin: float = 0.0
    allow_positive_trend_rescue: bool = True

    # Style-aware overrides for Growth stocks
    growth_positive_years_required: int = 2
    growth_ocf_rescue_min_gross_margin: float = 0.40

    # Sector-specific FCF margin floors (lowercased GICSSector value → minimum)
    sector_margin_overrides: dict[str, float] = Field(
        default_factory=lambda: {
            "information technology": 0.10,
            "communication services": 0.08,
            "health care": 0.05,
            "consumer staples": 0.05,
            "consumer discretionary": 0.03,
            "industrials": 0.03,
            "materials": 0.02,
            "energy": 0.0,
            "utilities": 0.0,
        }
    )

    def get_min_fcf_margin(self, sector: str | None) -> float:
        """Look up the FCF margin floor for a sector.

        Returns the sector-specific override if available, otherwise
        falls back to ``min_fcf_margin``.
        """
        if sector is None:
            return self.min_fcf_margin
        return self.sector_margin_overrides.get(sector.lower(), self.min_fcf_margin)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/scoring/filters/test_fcf_distress.py::TestFcfDistressConfigSectorOverrides -v`
Expected: PASS

**Step 5: Fix any existing tests broken by min_fcf_margin default change**

The default changed from -0.05 to 0.0. Scan existing tests for assertions on the old value:
- `test_fcf_margin_floor` (line 301): tests `median_fcf_margin < -0.05` — this test's data has median_fcf_margin = -0.4, well below both -0.05 and 0.0. Still passes.
- `test_fcf_margin_floor_borderline_pass` (line 316): tests median exactly at -0.05. With new default of 0.0, this will now FAIL because -0.05 < 0.0. **Fix this test** by passing `sector=None` and noting the threshold changed, OR adjust the test data so median is exactly 0.0.

Update `test_fcf_margin_floor_borderline_pass` to use explicit config with old threshold since it's testing the margin floor mechanism, not the default value:

```python
def test_fcf_margin_floor_borderline_pass(self):
    """Median FCF margin at exactly the floor should PASS (>=, not >)."""
    # Explicitly set floor to -0.05 to test the >= boundary
    config = FcfDistressConfig(min_fcf_margin=-0.05, sector_margin_overrides={})
    history = _make_history([-100, -50, -50, 20, 100])
    result = fcf_distress_check_v2(history, config=config)
    assert result.passed is True
```

Run: `uv run pytest engine/tests/scoring/filters/test_fcf_distress.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/config/filter_config.py engine/tests/scoring/filters/test_fcf_distress.py
git commit -m "feat(engine): add sector-specific FCF margin overrides to FcfDistressConfig"
```

---

### Task 2: Use sector-specific floor in fcf_distress_check_v2

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/fcf_distress.py:81-242`
- Test: `engine/tests/scoring/filters/test_fcf_distress.py`

**Step 1: Write failing tests**

Add to `engine/tests/scoring/filters/test_fcf_distress.py`:

```python
import pytest

class TestFCFDistressSectorMarginFloors:
    """Tests for sector-specific FCF margin floors in v2."""

    @pytest.mark.parametrize(
        "sector,floor",
        [
            (GICSSector.TECHNOLOGY, 0.10),
            (GICSSector.COMMUNICATION_SERVICES, 0.08),
            (GICSSector.HEALTHCARE, 0.05),
            (GICSSector.CONSUMER_STAPLES, 0.05),
            (GICSSector.CONSUMER_DISCRETIONARY, 0.03),
            (GICSSector.INDUSTRIALS, 0.03),
            (GICSSector.MATERIALS, 0.02),
            (GICSSector.ENERGY, 0.0),
            (GICSSector.UTILITIES, 0.0),
        ],
    )
    def test_sector_floor_applied(self, sector, floor):
        """Each sector should use its specific FCF margin floor."""
        # Build history with median FCF margin = floor - 0.01 (just below threshold)
        margin_below = floor - 0.01
        fcf_values = [margin_below * 1000] * 5  # All same → median = margin_below
        history = _make_history(fcf_values)
        result = fcf_distress_check_v2(history, sector=sector)
        assert result.passed is False, f"{sector.value} should fail with margin {margin_below:.2%} < {floor:.0%}"

    def test_tech_stock_passes_with_adequate_margin(self):
        """Tech stock with 15% FCF margin should pass the 10% floor."""
        # FCF margin = 150/1000 = 15% per year, all positive
        history = _make_history([150, 160, 140, 170, 155])
        result = fcf_distress_check_v2(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True

    def test_tech_stock_fails_with_8pct_margin(self):
        """Tech stock with 8% FCF margin should fail the 10% floor."""
        # FCF margin = 80/1000 = 8% per year, all positive but below 10%
        history = _make_history([80, 80, 80, 80, 80])
        result = fcf_distress_check_v2(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False

    def test_energy_stock_passes_with_tiny_margin(self):
        """Energy stock with 0.5% FCF margin should pass the 0% floor."""
        history = _make_history([5, 5, 5, 5, 5])
        result = fcf_distress_check_v2(history, sector=GICSSector.ENERGY)
        assert result.passed is True

    def test_no_sector_uses_default_floor(self):
        """When sector is None, use the default min_fcf_margin (0.0)."""
        # Margin = -1% — below 0 but above old -5%
        history = _make_history([-10, -10, -10, -10, -10], revenues=[1000]*5)
        result = fcf_distress_check_v2(history, sector=None)
        assert result.passed is False

    def test_computed_metrics_includes_sector_info(self):
        """computed_metrics should include sector_fcf_margin_floor and sector_name."""
        history = _make_history([150, 160, 140, 170, 155])
        result = fcf_distress_check_v2(history, sector=GICSSector.TECHNOLOGY)
        assert result.computed_metrics is not None
        assert result.computed_metrics["sector_fcf_margin_floor"] == 0.10
        assert result.computed_metrics["sector_name"] == "Information Technology"

    def test_computed_metrics_no_sector(self):
        """When sector is None, sector_name should be empty string and floor is default."""
        history = _make_history([150, 160, 140, 170, 155])
        result = fcf_distress_check_v2(history, sector=None)
        assert result.computed_metrics is not None
        assert result.computed_metrics["sector_fcf_margin_floor"] == 0.0
        assert result.computed_metrics["sector_name"] == ""
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/filters/test_fcf_distress.py::TestFCFDistressSectorMarginFloors -v`
Expected: FAIL — sector floors not yet implemented in `fcf_distress_check_v2`, `sector_fcf_margin_floor` and `sector_name` not in `computed_metrics`.

**Step 3: Implement sector-aware margin floor in fcf_distress_check_v2**

In `engine/src/margin_engine/scoring/filters/fcf_distress.py`, modify `fcf_distress_check_v2`:

1. After `config = FcfDistressConfig()` (line 112), add sector floor lookup:
```python
    sector_value = sector.value if sector is not None else None
    margin_floor = config.get_min_fcf_margin(sector_value)
    sector_name = sector.value if sector is not None else ""
```

2. Replace the margin floor check (line 159) — change `config.min_fcf_margin` to `margin_floor`:
```python
    margin_floor_passed = median_fcf_margin >= margin_floor
    if not margin_floor_passed:
        detail = (
            f"FAIL: median FCF margin {median_fcf_margin:.1%} < "
            f"floor {margin_floor:.1%}"
            f"{' (' + sector_name + ')' if sector_name else ''}. "
            f"positive_years={positive_years}/{total_years}, "
            f"required={required}"
        )
        return FilterResult(
            name=_FILTER_NAME,
            passed=False,
            value=median_fcf_margin,
            threshold=margin_floor,
            detail=detail,
            computed_metrics={
                "positive_years": float(positive_years),
                "total_years": float(total_years),
                "positive_years_required": float(required),
                "median_fcf_margin": median_fcf_margin,
                "consecutive_improving_years": float(consecutive_improving),
                "sector_fcf_margin_floor": margin_floor,
                "sector_name": sector_name,
            },
        )
```

3. Add `sector_fcf_margin_floor` and `sector_name` to the PASS computed_metrics dict at the end (around line 235):
```python
        computed_metrics={
            "positive_years": float(positive_years),
            "total_years": float(total_years),
            "positive_years_required": float(required),
            "median_fcf_margin": median_fcf_margin,
            "consecutive_improving_years": float(consecutive_improving),
            "sector_fcf_margin_floor": margin_floor,
            "sector_name": sector_name,
        },
```

Note: `computed_metrics` stores `sector_name` as a string (not a float). The dict type is `dict[str, float] | None` on `FilterResult`. You'll need to widen this to `dict[str, float | str] | None` in `engine/src/margin_engine/models/scoring.py:67`. Change:
```python
computed_metrics: dict[str, float] | None = None
```
to:
```python
computed_metrics: dict[str, float | str] | None = None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/filters/test_fcf_distress.py -v`
Expected: ALL PASS (new sector tests + existing tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/filters/fcf_distress.py engine/src/margin_engine/models/scoring.py engine/tests/scoring/filters/test_fcf_distress.py
git commit -m "feat(engine): apply sector-specific FCF margin floors in fcf_distress_check_v2"
```

---

### Task 3: Thread computed_metrics through API layer

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py:13-23` (FilterResultResponse)
- Modify: `api/src/margin_api/schemas/scores.py:183-192` (from_engine conversion)
- Modify: `web/src/lib/api/types.ts:1-9` (FilterResultResponse TS type)
- Test: `api/tests/test_schemas.py`

**Step 1: Write failing test**

Add to `api/tests/test_schemas.py` in the `TestFilterResultResponse` class:

```python
def test_filter_result_response_with_computed_metrics(self) -> None:
    """FilterResultResponse should include computed_metrics when present."""
    result = FilterResultResponse(
        name="fcf_distress",
        passed=True,
        value=4.0,
        threshold=3.0,
        detail="PASS: 4/5 positive FCF years",
        verdict="pass",
        computed_metrics={
            "positive_years": 4.0,
            "total_years": 5.0,
            "positive_years_required": 3.0,
            "median_fcf_margin": 0.15,
            "consecutive_improving_years": 2.0,
            "sector_fcf_margin_floor": 0.10,
            "sector_name": "Information Technology",
        },
    )
    data = result.model_dump()
    assert data["computed_metrics"]["sector_fcf_margin_floor"] == 0.10
    assert data["computed_metrics"]["sector_name"] == "Information Technology"

def test_filter_result_response_computed_metrics_optional(self) -> None:
    """computed_metrics should default to None when not provided."""
    result = FilterResultResponse(
        name="altman_z_score",
        passed=True,
        value=5.0,
        threshold=1.1,
        detail="Healthy",
        verdict="pass",
    )
    assert result.computed_metrics is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_schemas.py::TestFilterResultResponse::test_filter_result_response_with_computed_metrics -v`
Expected: FAIL — `computed_metrics` not a field on `FilterResultResponse`.

**Step 3: Implement API changes**

In `api/src/margin_api/schemas/scores.py`:

1. Add `computed_metrics` to `FilterResultResponse` (after line 22):
```python
class FilterResultResponse(BaseModel):
    """API representation of a single filter result."""

    name: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    detail: str = ""
    verdict: str  # "pass", "fail", or "inconclusive"
    missing_fields: list[str] | None = None
    sector_pass_rate: float | None = None
    computed_metrics: dict[str, float | str] | None = None
```

2. Update `from_engine` (around line 184) to pass `computed_metrics`:
```python
            filters_passed=[
                FilterResultResponse(
                    name=f.name,
                    passed=f.passed,
                    value=f.value,
                    threshold=f.threshold,
                    detail=f.detail,
                    verdict=f.verdict.value,
                    missing_fields=f.missing_fields,
                    computed_metrics=f.computed_metrics,
                )
                for f in score.filters_passed
            ],
```

3. Update the web TypeScript type in `web/src/lib/api/types.ts`:
```typescript
export interface FilterResultResponse {
  name: string
  passed: boolean
  value: number | null
  threshold: number | null
  detail: string
  verdict: string
  missing_fields?: string[] | null
  computed_metrics?: Record<string, number | string> | null
}
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_schemas.py::TestFilterResultResponse -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py web/src/lib/api/types.ts api/tests/test_schemas.py
git commit -m "feat(api): thread computed_metrics through FilterResultResponse"
```

---

### Task 4: Update filter card UI to show expanded inline format

**Files:**
- Modify: `web/src/components/asset-detail/filter-card.tsx`
- Test: `web/src/components/asset-detail/__tests__/filter-card.test.tsx`

**Step 1: Write failing tests**

Add to `web/src/components/asset-detail/__tests__/filter-card.test.tsx`:

```typescript
describe("FilterCard FCF display", () => {
  const fcfFilterWithMetrics: FilterResultResponse = {
    name: "fcf_distress",
    passed: true,
    value: 4.0,
    threshold: 3.0,
    detail: "PASS: 4/5 positive FCF years (required 3). median_fcf_margin=18.3%, improving_streak=2",
    verdict: "passed",
    computed_metrics: {
      positive_years: 4,
      total_years: 5,
      positive_years_required: 3,
      median_fcf_margin: 0.183,
      consecutive_improving_years: 2,
      sector_fcf_margin_floor: 0.10,
      sector_name: "Information Technology",
    },
  }

  it("shows multi-year positive count and FCF margin in value", () => {
    render(<FilterCard filter={fcfFilterWithMetrics} expanded={false} />)
    expect(screen.getByText(/4\/5 years positive/)).toBeInTheDocument()
    expect(screen.getByText(/18\.3%/)).toBeInTheDocument()
  })

  it("shows sector-specific threshold inline", () => {
    render(<FilterCard filter={fcfFilterWithMetrics} expanded={false} />)
    expect(screen.getByText(/≥ 3\/5 years/)).toBeInTheDocument()
    expect(screen.getByText(/margin ≥ 10%/)).toBeInTheDocument()
    expect(screen.getByText(/Technology/)).toBeInTheDocument()
  })

  it("falls back to legacy display when computed_metrics is missing", () => {
    const legacyFilter: FilterResultResponse = {
      name: "fcf_distress",
      passed: true,
      value: 4200000000,
      threshold: 0,
      detail: "FCF=4,200,000,000 (PASS, threshold=0.0)",
      verdict: "passed",
    }
    render(<FilterCard filter={legacyFilter} expanded={false} />)
    expect(screen.getByText("$4.2B")).toBeInTheDocument()
    expect(screen.getByText("Positive")).toBeInTheDocument()
  })

  it("shows cyclical note for cyclical sectors", () => {
    const cyclicalFilter: FilterResultResponse = {
      ...fcfFilterWithMetrics,
      passed: true,
      threshold: 2.0,
      computed_metrics: {
        ...fcfFilterWithMetrics.computed_metrics!,
        positive_years_required: 2,
        sector_fcf_margin_floor: 0.0,
        sector_name: "Energy",
      },
    }
    render(<FilterCard filter={cyclicalFilter} expanded={false} />)
    expect(screen.getByText(/≥ 2\/5 years/)).toBeInTheDocument()
    expect(screen.getByText(/Energy/)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/filter-card.test.tsx`
Expected: FAIL — filter card still shows `$4.2B` / `Positive` for FCF.

**Step 3: Implement UI changes**

In `web/src/components/asset-detail/filter-card.tsx`, update `formatValue` and `formatThreshold`:

```typescript
function formatValue(value: number | null, name: string, metrics?: Record<string, number | string> | null): string {
  if (value == null) return "N/A"
  if (name === "fcf_distress" && metrics && "positive_years" in metrics) {
    const posYears = metrics.positive_years as number
    const totalYears = metrics.total_years as number
    const margin = metrics.median_fcf_margin as number
    return `${posYears}/${totalYears} years positive · FCF margin ${(margin * 100).toFixed(1)}%`
  }
  if (name === "liquidity") {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
    if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`
    return `$${value.toLocaleString()}`
  }
  if (name === "interest_coverage") return `${value.toFixed(1)}x`
  if (name === "fcf_distress") {
    if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
    if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(0)}M`
    return `$${value.toLocaleString()}`
  }
  return value.toFixed(2)
}

function formatThreshold(threshold: number | null, name: string, metrics?: Record<string, number | string> | null): string {
  if (threshold == null) return "N/A"
  if (name === "fcf_distress" && metrics && "positive_years_required" in metrics) {
    const required = metrics.positive_years_required as number
    const totalYears = metrics.total_years as number
    const floor = metrics.sector_fcf_margin_floor as number
    const sector = metrics.sector_name as string
    const sectorLabel = sector ? ` (${sector})` : ""
    return `≥ ${required}/${totalYears} years · margin ≥ ${Math.round(floor * 100)}%${sectorLabel}`
  }
  if (name === "liquidity") return `$${(threshold / 1e6).toFixed(0)}M`
  if (name === "interest_coverage") return `${threshold.toFixed(1)}x`
  if (name === "fcf_distress") return "Positive"
  return threshold.toFixed(2)
}
```

Update the JSX calls in the component to pass `filter.computed_metrics`:

```typescript
<span className="text-text-primary">{formatValue(filter.value, filter.name, filter.computed_metrics)}</span>
```

```typescript
<span className="text-text-primary">{formatThreshold(filter.threshold, filter.name, filter.computed_metrics)}</span>
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/filter-card.test.tsx`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/filter-card.tsx web/src/components/asset-detail/__tests__/filter-card.test.tsx
git commit -m "feat(web): show expanded FCF filter info with sector-specific thresholds"
```

---

### Task 5: Run full test suites and verify nothing broke

**Files:** None (verification only)

**Step 1: Run engine tests**

Run: `uv run pytest engine/tests/ -v`
Expected: ALL PASS (~2621 tests)

**Step 2: Run API tests**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
Expected: ALL PASS (~1587 tests)

**Step 3: Run web tests**

Run: `cd web && npx vitest run`
Expected: ALL PASS (~1285 tests)

**Step 4: Commit any remaining fixes if needed**

If any tests broke, fix them and commit:
```bash
git commit -m "fix: adjust tests for sector-specific FCF margin defaults"
```
