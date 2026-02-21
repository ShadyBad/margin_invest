# Historical Application Chart v2 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update the Historical Application chart to use precedence-fill selection (Exceptional first, backfill with High up to 5 holdings) with MoS > 20% threshold, and add holding count + MoS to the chart tooltip.

**Architecture:** Extend existing `CONVICTION_MOS` selection mode in the engine simulator with `max_holdings` and `min_conviction_score_high` config fields. Two-tier selection: Exceptional (≥ 79) first, then High (≥ 72) backfill up to `max_holdings`. Update API schema to expose new fields. Enhance web chart tooltip with holding metadata.

**Tech Stack:** Python (engine), Pydantic models, pytest. FastAPI (api). Next.js 15, React, Vitest (web).

**Design doc:** `docs/plans/2026-02-20-historical-application-v2-design.md`

---

## Task 1: Add `max_holdings` and `min_conviction_score_high` to BacktestConfig

**Files:**
- Modify: `engine/src/margin_engine/backtesting/models.py:29-49` (BacktestConfig)
- Modify: `engine/tests/backtesting/test_simulator.py` (add model tests)

**Step 1: Write the failing tests**

Add to `engine/tests/backtesting/test_simulator.py`, after the existing `TestScoredStockModel` class (line ~1136):

```python
class TestBacktestConfigV2Fields:
    """Tests for v2 config fields: max_holdings, min_conviction_score_high, updated MoS default."""

    def test_max_holdings_default(self):
        config = BacktestConfig(start_date=date(2020, 1, 1), end_date=date(2020, 12, 31))
        assert config.max_holdings == 5

    def test_min_conviction_score_high_default(self):
        config = BacktestConfig(start_date=date(2020, 1, 1), end_date=date(2020, 12, 31))
        assert config.min_conviction_score_high == 72.0

    def test_min_margin_of_safety_default_changed(self):
        config = BacktestConfig(start_date=date(2020, 1, 1), end_date=date(2020, 12, 31))
        assert config.min_margin_of_safety == 0.20

    def test_custom_max_holdings(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1), end_date=date(2020, 12, 31), max_holdings=10
        )
        assert config.max_holdings == 10

    def test_custom_min_conviction_score_high(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1), end_date=date(2020, 12, 31),
            min_conviction_score_high=75.0,
        )
        assert config.min_conviction_score_high == 75.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestBacktestConfigV2Fields -v`
Expected: FAIL — `BacktestConfig` does not have `max_holdings` or `min_conviction_score_high` fields.

**Step 3: Add fields to BacktestConfig**

In `engine/src/margin_engine/backtesting/models.py`, add these fields to `BacktestConfig` after the `min_margin_of_safety` field (line 49):

```python
    min_margin_of_safety: float = Field(
        default=0.20, description="Minimum margin of safety for CONVICTION_MOS mode"
    )
    max_holdings: int = Field(
        default=5, description="Maximum number of holdings for CONVICTION_MOS mode"
    )
    min_conviction_score_high: float = Field(
        default=72.0,
        description="Minimum composite_raw_score for High-conviction tier 2 backfill",
    )
```

Note: Also change `min_margin_of_safety` default from `0.30` to `0.20`.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestBacktestConfigV2Fields -v`
Expected: PASS (5 tests)

**Step 5: Verify existing tests still pass**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py -v`
Expected: Some existing tests that hard-coded MoS=0.30 behavior may need updating. Specifically, `TestConvictionMosSelection.test_fails_mos_threshold` uses MoS=0.25 and expects rejection — with new default of 0.20, this test should still pass (0.25 > 0.20). Check `test_mos_exactly_threshold_rejected` — it tests MoS=0.30 rejection, but the default is now 0.20. The test creates a simulator with default `min_mos=0.30` via `_make_simulator()`, so it explicitly sets 0.30. Verify all pass.

**Step 6: Commit**

```bash
git add engine/src/margin_engine/backtesting/models.py engine/tests/backtesting/test_simulator.py
git commit -m "feat(engine): add max_holdings and min_conviction_score_high to BacktestConfig"
```

---

## Task 2: Rewrite `_select_by_conviction_mos()` with Precedence-Fill Logic

**Files:**
- Modify: `engine/src/margin_engine/backtesting/simulator.py:249-279` (`_select_by_conviction_mos`)
- Modify: `engine/tests/backtesting/test_simulator.py` (add precedence-fill tests)

**Step 1: Write the failing tests**

Add a new test class after `TestConvictionMosSelection` in `engine/tests/backtesting/test_simulator.py`:

```python
class TestPrecedenceFillSelection:
    """Tests for v2 precedence-fill selection: Exceptional first, backfill with High."""

    def _make_simulator(
        self,
        min_score: float = 79.0,
        min_score_high: float = 72.0,
        min_mos: float = 0.20,
        max_holdings: int = 5,
    ):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            min_conviction_score=min_score,
            min_conviction_score_high=min_score_high,
            min_margin_of_safety=min_mos,
            max_holdings=max_holdings,
        )
        return WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )

    def test_exceptional_fills_first(self):
        """3 Exceptional + 4 High eligible → selects 3 Exceptional + top 2 High."""
        sim = self._make_simulator()
        scores = [
            # 3 Exceptional (score >= 79)
            ScoredStock(ticker="E1", composite_score=85.0, price=100.0, margin_of_safety=0.35),
            ScoredStock(ticker="E2", composite_score=82.0, price=100.0, margin_of_safety=0.30),
            ScoredStock(ticker="E3", composite_score=79.5, price=100.0, margin_of_safety=0.25),
            # 4 High (72 <= score < 79)
            ScoredStock(ticker="H1", composite_score=78.0, price=100.0, margin_of_safety=0.40),
            ScoredStock(ticker="H2", composite_score=76.0, price=100.0, margin_of_safety=0.35),
            ScoredStock(ticker="H3", composite_score=74.0, price=100.0, margin_of_safety=0.30),
            ScoredStock(ticker="H4", composite_score=72.5, price=100.0, margin_of_safety=0.25),
        ]
        holdings = sim._select_holdings(scores, [])
        tickers = [h.ticker for h in holdings]
        assert len(holdings) == 5
        # All 3 Exceptional first
        assert "E1" in tickers
        assert "E2" in tickers
        assert "E3" in tickers
        # Top 2 High to fill to 5
        assert "H1" in tickers
        assert "H2" in tickers
        # H3 and H4 excluded (cap at 5)
        assert "H3" not in tickers
        assert "H4" not in tickers

    def test_max_holdings_cap_exceptional_only(self):
        """7 Exceptional eligible → selects top 5 by score."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker=f"E{i}", composite_score=90.0 - i, price=100.0, margin_of_safety=0.30)
            for i in range(7)
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 5
        tickers = [h.ticker for h in holdings]
        assert tickers == ["E0", "E1", "E2", "E3", "E4"]

    def test_high_backfill_when_no_exceptional(self):
        """0 Exceptional + 6 High → selects top 5 High."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker=f"H{i}", composite_score=78.0 - i, price=100.0, margin_of_safety=0.30)
            for i in range(6)
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 5
        tickers = [h.ticker for h in holdings]
        assert tickers == ["H0", "H1", "H2", "H3", "H4"]

    def test_mos_20_threshold_excludes_exact(self):
        """Candidate with MoS = 0.20 exactly is excluded (strictly greater)."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.20),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0

    def test_mos_21_threshold_includes(self):
        """Candidate with MoS = 0.21 is included."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.21),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 1

    def test_hold_through_zero_eligible_both_tiers(self):
        """0 Exceptional + 0 High eligible → returns prev_holdings."""
        sim = self._make_simulator()
        prev = [
            HoldingRecord(ticker="OLD", weight=1.0, entry_price=100.0, composite_score=82.0),
        ]
        scores = [
            ScoredStock(ticker="LOW", composite_score=60.0, price=100.0, margin_of_safety=0.10),
        ]
        holdings = sim._select_holdings(scores, prev)
        assert holdings == prev

    def test_fewer_than_max_available(self):
        """2 Exceptional + 1 High → 3 holdings, weight = 1/3."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="E1", composite_score=85.0, price=100.0, margin_of_safety=0.30),
            ScoredStock(ticker="E2", composite_score=80.0, price=100.0, margin_of_safety=0.25),
            ScoredStock(ticker="H1", composite_score=75.0, price=100.0, margin_of_safety=0.35),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 3
        for h in holdings:
            assert h.weight == pytest.approx(1.0 / 3.0)

    def test_deterministic_sort_within_tier(self):
        """Equal scores sorted by (-mos, ticker) within each tier."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="ZZZ", composite_score=80.0, price=100.0, margin_of_safety=0.30),
            ScoredStock(ticker="AAA", composite_score=80.0, price=100.0, margin_of_safety=0.30),
            ScoredStock(ticker="MMM", composite_score=80.0, price=100.0, margin_of_safety=0.40),
        ]
        holdings1 = sim._select_holdings(scores, [])
        holdings2 = sim._select_holdings(scores, [])
        tickers1 = [h.ticker for h in holdings1]
        tickers2 = [h.ticker for h in holdings2]
        assert tickers1 == tickers2
        # MMM has highest MoS (0.40), then AAA and ZZZ tied on MoS, alphabetical
        assert tickers1 == ["MMM", "AAA", "ZZZ"]

    def test_high_below_threshold_excluded(self):
        """Score 71.9 (below High threshold of 72) is excluded."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="LOW", composite_score=71.9, price=100.0, margin_of_safety=0.40),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestPrecedenceFillSelection -v`
Expected: FAIL — current `_select_by_conviction_mos` only checks `min_conviction_score` (79), not the two-tier logic.

**Step 3: Rewrite `_select_by_conviction_mos()` in simulator.py**

Replace the method at `engine/src/margin_engine/backtesting/simulator.py:249-279`:

```python
    def _select_by_conviction_mos(
        self, scores: list[ScoredStock], prev_holdings: list[HoldingRecord]
    ) -> list[HoldingRecord]:
        """Select stocks using two-tier precedence fill.

        Tier 1: Exceptional conviction (score >= min_conviction_score) with MoS above threshold.
        Tier 2: High conviction (score >= min_conviction_score_high) with MoS above threshold.

        Takes all tier 1 first (up to max_holdings), then fills remaining slots
        with tier 2 candidates. If zero eligible across both tiers, returns
        prev_holdings unchanged (hold-through).
        """
        def is_mos_eligible(s: ScoredStock) -> bool:
            return (
                s.margin_of_safety is not None
                and s.margin_of_safety > self._config.min_margin_of_safety
            )

        eligible_exceptional = [
            s for s in scores
            if s.composite_score >= self._config.min_conviction_score and is_mos_eligible(s)
        ]
        eligible_high = [
            s for s in scores
            if self._config.min_conviction_score_high <= s.composite_score < self._config.min_conviction_score
            and is_mos_eligible(s)
        ]

        sort_key = lambda s: (-s.composite_score, -(s.margin_of_safety or 0), s.ticker)
        eligible_exceptional.sort(key=sort_key)
        eligible_high.sort(key=sort_key)

        max_h = self._config.max_holdings
        selected_stocks = eligible_exceptional[:max_h]
        if len(selected_stocks) < max_h:
            remaining = max_h - len(selected_stocks)
            selected_stocks += eligible_high[:remaining]

        if not selected_stocks:
            return prev_holdings

        weight = 1.0 / len(selected_stocks)
        return [
            HoldingRecord(
                ticker=stock.ticker,
                weight=weight,
                entry_price=stock.price,
                composite_score=stock.composite_score,
            )
            for stock in selected_stocks
        ]
```

**Step 4: Run new tests to verify they pass**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestPrecedenceFillSelection -v`
Expected: PASS (10 tests)

**Step 5: Run ALL engine tests to check for regressions**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py -v`
Expected: All pass. The existing `TestConvictionMosSelection` tests use `_make_simulator(min_score=79.0, min_mos=0.30)` which explicitly sets thresholds, so they'll still work — they just won't exercise the High tier. The key behavioral change: the old method returned ALL eligible without a cap. If any existing test expects more than `max_holdings=5` results, it will need updating. Check `test_equal_weight_multiple` — it expects 4 holdings, which is < 5, so it will pass.

**Step 6: Commit**

```bash
git add engine/src/margin_engine/backtesting/simulator.py engine/tests/backtesting/test_simulator.py
git commit -m "feat(engine): add precedence-fill selection (Exceptional then High, cap at max_holdings)"
```

---

## Task 3: Update API Schema with New Config Fields

**Files:**
- Modify: `api/src/margin_api/schemas/backtest.py:10-22` (BacktestConfigRequest)
- Modify: `api/tests/` (if API tests exist for schema validation)

**Step 1: Write the failing test**

Check if there are existing API tests for the backtest schema. If so, add a test. If not, we can verify via import.

Create or add to the appropriate test file:

```python
def test_backtest_config_request_v2_fields():
    from margin_api.schemas.backtest import BacktestConfigRequest
    req = BacktestConfigRequest()
    assert req.max_holdings == 5
    assert req.min_conviction_score_high == 72.0
    assert req.min_margin_of_safety == 0.20
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/ -k "test_backtest_config_request_v2" -v`
Expected: FAIL — `BacktestConfigRequest` does not have `max_holdings`.

**Step 3: Add fields to BacktestConfigRequest**

In `api/src/margin_api/schemas/backtest.py`, add after `min_margin_of_safety` (line 22):

```python
    min_margin_of_safety: float = Field(default=0.20, ge=-1.0, le=1.0)
    max_holdings: int = Field(default=5, ge=1, le=50)
    min_conviction_score_high: float = Field(default=72.0, ge=0, le=100)
```

Note: Also change `min_margin_of_safety` default from `0.30` to `0.20`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/ -k "test_backtest_config_request_v2" -v`
Expected: PASS

**Step 5: Run all API tests to check for regressions**

Run: `uv run pytest api/tests/ -v`
Expected: All pass. Existing tests that construct `BacktestConfigRequest()` with defaults will now get `min_margin_of_safety=0.20` instead of `0.30`. If any existing test asserts `min_margin_of_safety == 0.30`, update it to `0.20`.

**Step 6: Commit**

```bash
git add api/src/margin_api/schemas/backtest.py api/tests/
git commit -m "feat(api): add max_holdings and min_conviction_score_high to BacktestConfigRequest"
```

---

## Task 4: Add Holding Count and MoS to Chart Tooltip

**Files:**
- Modify: `web/src/components/backtesting/performance-chart.tsx`
- Modify: `web/src/components/backtesting/__tests__/performance-chart.test.tsx`

**Step 1: Write the failing tests**

Add to `web/src/components/backtesting/__tests__/performance-chart.test.tsx`:

```typescript
  it("shows holding count in tooltip when holdingCounts provided", () => {
    const holdingCounts = [3, 5, 4, 5, 5]
    render(
      <PerformanceChart
        snapshots={mockSnapshots}
        holdingCounts={holdingCounts}
        maxHoldings={5}
      />,
    )
    const hitAreas = screen.getAllByTestId(/^chart-hit-area-/)
    fireEvent.mouseEnter(hitAreas[0])
    const tooltip = screen.getByTestId("chart-tooltip")
    expect(tooltip.textContent).toContain("3 of 5")
  })

  it("shows MoS threshold in tooltip when mosThreshold provided", () => {
    render(
      <PerformanceChart
        snapshots={mockSnapshots}
        mosThreshold={0.20}
      />,
    )
    const hitAreas = screen.getAllByTestId(/^chart-hit-area-/)
    fireEvent.mouseEnter(hitAreas[0])
    const tooltip = screen.getByTestId("chart-tooltip")
    expect(tooltip.textContent).toContain("> 20%")
  })

  it("does not show holding count when holdingCounts not provided", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    const hitAreas = screen.getAllByTestId(/^chart-hit-area-/)
    fireEvent.mouseEnter(hitAreas[0])
    const tooltip = screen.getByTestId("chart-tooltip")
    expect(tooltip.textContent).not.toContain("of")
  })
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/backtesting/__tests__/performance-chart.test.tsx`
Expected: FAIL — `PerformanceChart` does not accept `holdingCounts`, `maxHoldings`, or `mosThreshold` props.

**Step 3: Add new props to PerformanceChart**

In `web/src/components/backtesting/performance-chart.tsx`:

Update the interface (around line 13):

```typescript
interface PerformanceChartProps {
  snapshots: SnapshotData[]
  portfolioLabel?: string
  benchmarkLabel?: string
  holdingCounts?: number[]
  maxHoldings?: number
  mosThreshold?: number
  className?: string
}
```

Update the function signature (around line 63):

```typescript
export function PerformanceChart({
  snapshots,
  portfolioLabel = "Portfolio",
  benchmarkLabel = "Benchmark",
  holdingCounts,
  maxHoldings,
  mosThreshold,
  className,
}: PerformanceChartProps) {
```

Add to the tooltip section (inside the `hoveredIndex !== null` block, after the Excess line around line 265):

```tsx
          {holdingCounts && maxHoldings && hoveredIndex !== null && (
            <div className="text-text-secondary">
              Holdings: {holdingCounts[hoveredIndex]} of {maxHoldings}
            </div>
          )}
          {mosThreshold !== undefined && (
            <div className="text-text-secondary">
              MoS: &gt; {(mosThreshold * 100).toFixed(0)}%
            </div>
          )}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/backtesting/__tests__/performance-chart.test.tsx`
Expected: PASS (all existing + 3 new)

**Step 5: Commit**

```bash
git add web/src/components/backtesting/performance-chart.tsx web/src/components/backtesting/__tests__/performance-chart.test.tsx
git commit -m "feat(web): add holding count and MoS threshold to chart tooltip"
```

---

## Task 5: Update Backtesting Page Labels

**Files:**
- Modify: `web/src/app/backtesting/page.tsx:124-128`

**Step 1: Update the PerformanceChart props in the backtesting page**

In `web/src/app/backtesting/page.tsx`, replace the PerformanceChart usage (lines 124-128):

```tsx
              <PerformanceChart
                snapshots={result.snapshots ?? []}
                portfolioLabel="Up to 5, Exceptional then High, MoS > 20%, Equal-Weight, Monthly"
                benchmarkLabel="S&P 500 (SPY Total Return)"
                mosThreshold={0.20}
                maxHoldings={5}
              />
```

Note: `holdingCounts` would need to come from the API response (snapshot-level data). For now, we pass `mosThreshold` and `maxHoldings` as static values since the API doesn't yet return per-snapshot holding counts. When the API returns real snapshots, we can wire `holdingCounts={result.snapshots?.map(s => s.holdings?.length ?? 0)}`.

**Step 2: Run web tests to verify no regressions**

Run: `cd web && npx vitest run`
Expected: All pass.

**Step 3: Commit**

```bash
git add web/src/app/backtesting/page.tsx
git commit -m "feat(web): update chart labels for v2 precedence-fill portfolio"
```

---

## Task 6: Update Existing Tests for New MoS Default

**Files:**
- Modify: `engine/tests/backtesting/test_simulator.py` (fix any tests broken by MoS default change)
- Modify: `api/tests/` (fix any API tests broken by MoS default change)

**Step 1: Run full test suite to find broken tests**

Run: `uv run pytest -v`
Expected: Check for any tests that assumed `min_margin_of_safety=0.30` as a default. The `TestConvictionMosSelection._make_simulator()` explicitly passes `min_mos=0.30`, so those tests will still work. But check for any test that constructs `BacktestConfig()` without specifying `min_margin_of_safety` and relies on the 0.30 default.

**Step 2: Fix any broken tests**

If `_make_simulator()` in `TestConvictionMosSelection` uses `min_mos=0.30`, keep it — those tests are testing the explicit 0.30 behavior. The default just changed from 0.30 to 0.20.

If any API tests break, update the expected default from 0.30 to 0.20.

**Step 3: Run full test suite**

Run: `uv run pytest -v`
Expected: All pass.

Run: `cd web && npx vitest run`
Expected: All pass.

**Step 4: Commit (only if changes were needed)**

```bash
git add -u
git commit -m "test: update assertions for new MoS default (0.30 → 0.20)"
```

---

## Task 7: Integration Test — Full Simulation with Precedence Fill

**Files:**
- Modify: `engine/tests/backtesting/test_simulator.py`

**Step 1: Write the integration test**

Add to `engine/tests/backtesting/test_simulator.py`, after `TestConvictionMosSimulation`:

```python
class TestPrecedenceFillSimulation:
    """Integration tests for full simulation with precedence-fill selection."""

    def test_mixed_tiers_across_months(self):
        """Multi-month simulation where tier composition changes each month."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)
        mar2 = date(2020, 3, 2)

        universe_data = {
            # Jan: 2 Exceptional + 3 High eligible → 5 holdings
            jan1: [
                ScoredStock(ticker="E1", composite_score=85.0, price=100.0, margin_of_safety=0.35),
                ScoredStock(ticker="E2", composite_score=80.0, price=100.0, margin_of_safety=0.30),
                ScoredStock(ticker="H1", composite_score=78.0, price=100.0, margin_of_safety=0.40),
                ScoredStock(ticker="H2", composite_score=75.0, price=100.0, margin_of_safety=0.25),
                ScoredStock(ticker="H3", composite_score=73.0, price=100.0, margin_of_safety=0.22),
                ScoredStock(ticker="LOW", composite_score=60.0, price=100.0, margin_of_safety=0.50),
            ],
            # Feb: 0 Exceptional + 2 High eligible → 2 holdings
            feb3: [
                ScoredStock(ticker="E1", composite_score=85.0, price=110.0, margin_of_safety=0.15),
                ScoredStock(ticker="E2", composite_score=80.0, price=105.0, margin_of_safety=0.10),
                ScoredStock(ticker="H1", composite_score=78.0, price=105.0, margin_of_safety=0.30),
                ScoredStock(ticker="H2", composite_score=75.0, price=102.0, margin_of_safety=0.25),
            ],
            # Mar: 0 eligible anywhere → hold-through
            mar2: [
                ScoredStock(ticker="E1", composite_score=85.0, price=108.0, margin_of_safety=0.10),
                ScoredStock(ticker="H1", composite_score=78.0, price=103.0, margin_of_safety=0.15),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            min_conviction_score=79.0,
            min_conviction_score_high=72.0,
            min_margin_of_safety=0.20,
            max_holdings=5,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider(universe_data),
            benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 105.0, mar2: 103.0}),
        )
        result = sim.run()

        assert len(result.snapshots) == 3

        # Jan: E1, E2 (Exceptional) + H1, H2, H3 (High backfill) = 5
        snap1 = result.snapshots[0]
        tickers1 = {h.ticker for h in snap1.holdings}
        assert len(snap1.holdings) == 5
        assert tickers1 == {"E1", "E2", "H1", "H2", "H3"}

        # Feb: H1 (mos=0.30 > 0.20) and H2 (mos=0.25 > 0.20) only
        snap2 = result.snapshots[1]
        tickers2 = {h.ticker for h in snap2.holdings}
        assert len(snap2.holdings) == 2
        assert tickers2 == {"H1", "H2"}

        # Mar: 0 eligible → hold-through from Feb
        snap3 = result.snapshots[2]
        tickers3 = {h.ticker for h in snap3.holdings}
        assert tickers3 == {"H1", "H2"}
        assert snap3.turnover == pytest.approx(0.0)

    def test_determinism_precedence_fill(self):
        """Same inputs produce identical outputs with precedence fill."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)

        universe_data = {
            jan1: [
                ScoredStock(ticker="E1", composite_score=85.0, price=100.0, margin_of_safety=0.35),
                ScoredStock(ticker="H1", composite_score=75.0, price=100.0, margin_of_safety=0.30),
            ],
            feb3: [
                ScoredStock(ticker="E1", composite_score=85.0, price=110.0, margin_of_safety=0.33),
                ScoredStock(ticker="H1", composite_score=75.0, price=105.0, margin_of_safety=0.28),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 2, 28),
            selection_mode=SelectionMode.CONVICTION_MOS,
            min_conviction_score=79.0,
            min_conviction_score_high=72.0,
            min_margin_of_safety=0.20,
            max_holdings=5,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
        )

        def run_once():
            sim = WalkForwardSimulator(
                config=config,
                universe_provider=FakeUniverseProvider(universe_data),
                benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 105.0}),
            )
            return [s.portfolio_value for s in sim.run().snapshots]

        assert run_once() == run_once()
```

**Step 2: Run the integration tests**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestPrecedenceFillSimulation -v`
Expected: PASS (2 tests)

**Step 3: Run full test suite one final time**

Run: `uv run pytest -v`
Expected: All pass.

**Step 4: Commit**

```bash
git add engine/tests/backtesting/test_simulator.py
git commit -m "test(engine): add integration tests for precedence-fill simulation"
```
