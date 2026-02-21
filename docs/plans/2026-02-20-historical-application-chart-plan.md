# Historical Application Chart Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update the Historical Application chart so the benchmark is SPY total return and the portfolio is built from Exceptional candidates (score >= 79) with MoS > 30%, equal-weighted, monthly rebalance.

**Architecture:** Extend the existing `WalkForwardSimulator` with a new `CONVICTION_MOS` selection mode. Add `margin_of_safety` to `ScoredStock`. Update the chart component with configurable legend labels and tooltips.

**Tech Stack:** Python/Pydantic (engine models + simulator), FastAPI (API schemas), React/TypeScript (chart component)

**Design doc:** `docs/plans/2026-02-20-historical-application-chart-design.md`

---

### Task 1: Add SelectionMode enum and extend BacktestConfig

**Files:**
- Modify: `engine/src/margin_engine/backtesting/models.py:10-46`
- Test: `engine/tests/backtesting/test_models.py`

**Step 1: Write the failing tests**

Add to `engine/tests/backtesting/test_models.py`:

```python
from margin_engine.backtesting.models import (
    BacktestConfig,
    SelectionMode,
)


class TestSelectionMode:
    def test_enum_values(self):
        assert SelectionMode.TOP_PERCENTILE == "top_percentile"
        assert SelectionMode.CONVICTION_MOS == "conviction_mos"

    def test_default_selection_mode_is_top_percentile(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        assert config.selection_mode == SelectionMode.TOP_PERCENTILE

    def test_conviction_mos_config(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            min_conviction_score=79.0,
            min_margin_of_safety=0.30,
        )
        assert config.selection_mode == SelectionMode.CONVICTION_MOS
        assert config.min_conviction_score == 79.0
        assert config.min_margin_of_safety == 0.30

    def test_conviction_mos_defaults(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
        )
        assert config.min_conviction_score == 79.0
        assert config.min_margin_of_safety == 0.30
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/backtesting/test_models.py::TestSelectionMode -v`
Expected: FAIL with `ImportError: cannot import name 'SelectionMode'`

**Step 3: Write minimal implementation**

In `engine/src/margin_engine/backtesting/models.py`, add `SelectionMode` enum after `RebalanceFrequency` (after line 19):

```python
class SelectionMode(StrEnum):
    """Portfolio stock selection strategy."""

    TOP_PERCENTILE = "top_percentile"
    CONVICTION_MOS = "conviction_mos"
```

Add fields to `BacktestConfig` (after line 35, before the validator):

```python
    selection_mode: SelectionMode = SelectionMode.TOP_PERCENTILE
    min_conviction_score: float = Field(
        default=79.0, description="Minimum composite_raw_score for CONVICTION_MOS mode"
    )
    min_margin_of_safety: float = Field(
        default=0.30, description="Minimum margin of safety for CONVICTION_MOS mode"
    )
```

Update the import in models.py `__all__` or wherever `SelectionMode` needs to be exported.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/backtesting/test_models.py::TestSelectionMode -v`
Expected: PASS (4 tests)

**Step 5: Run all existing model tests to confirm no regressions**

Run: `uv run pytest engine/tests/backtesting/test_models.py -v`
Expected: All existing tests PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/backtesting/models.py engine/tests/backtesting/test_models.py
git commit -m "feat(engine): add SelectionMode enum and conviction_mos config fields"
```

---

### Task 2: Extend ScoredStock with margin_of_safety

**Files:**
- Modify: `engine/src/margin_engine/backtesting/simulator.py:33-38`
- Test: `engine/tests/backtesting/test_simulator.py`

**Step 1: Write the failing tests**

Add to `engine/tests/backtesting/test_simulator.py`:

```python
class TestScoredStockModel:
    def test_scored_stock_without_mos(self):
        """ScoredStock should work without margin_of_safety (backward compat)."""
        stock = ScoredStock(ticker="AAPL", composite_score=85.0, price=150.0)
        assert stock.margin_of_safety is None

    def test_scored_stock_with_mos(self):
        """ScoredStock should accept margin_of_safety."""
        stock = ScoredStock(
            ticker="AAPL", composite_score=85.0, price=150.0, margin_of_safety=0.35
        )
        assert stock.margin_of_safety == 0.35

    def test_scored_stock_with_negative_mos(self):
        """Negative MoS means overvalued — should be accepted."""
        stock = ScoredStock(
            ticker="TSLA", composite_score=60.0, price=300.0, margin_of_safety=-0.20
        )
        assert stock.margin_of_safety == -0.20
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestScoredStockModel -v`
Expected: FAIL — `margin_of_safety` is not a field on `ScoredStock`

**Step 3: Write minimal implementation**

In `engine/src/margin_engine/backtesting/simulator.py`, modify `ScoredStock` (lines 33-38):

```python
class ScoredStock(BaseModel):
    """A stock with its composite score at a point in time."""

    ticker: str
    composite_score: float
    price: float
    margin_of_safety: float | None = None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestScoredStockModel -v`
Expected: PASS (3 tests)

**Step 5: Run all existing simulator tests to confirm no regressions**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py -v`
Expected: All existing tests PASS (ScoredStock field is optional, so no breakage)

**Step 6: Commit**

```bash
git add engine/src/margin_engine/backtesting/simulator.py engine/tests/backtesting/test_simulator.py
git commit -m "feat(engine): add margin_of_safety field to ScoredStock"
```

---

### Task 3: Add conviction_mos selection method

**Files:**
- Modify: `engine/src/margin_engine/backtesting/simulator.py:215-240`
- Test: `engine/tests/backtesting/test_simulator.py`

**Step 1: Write the failing tests**

Add to `engine/tests/backtesting/test_simulator.py`:

```python
from margin_engine.backtesting.models import SelectionMode


class TestConvictionMosSelection:
    """Tests for _select_by_conviction_mos stock selection."""

    def _make_simulator(self, min_score: float = 79.0, min_mos: float = 0.30):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            min_conviction_score=min_score,
            min_margin_of_safety=min_mos,
        )
        return WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )

    def test_passes_both_thresholds(self):
        """Stock with score >= 79 AND MoS > 0.30 is selected."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="AAPL", composite_score=82.0, price=150.0, margin_of_safety=0.35),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 1
        assert holdings[0].ticker == "AAPL"

    def test_fails_mos_threshold(self):
        """Stock with good score but MoS <= 0.30 is rejected."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="MSFT", composite_score=82.0, price=300.0, margin_of_safety=0.25),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0

    def test_fails_conviction_threshold(self):
        """Stock with good MoS but score < 79 is rejected."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="GOOG", composite_score=75.0, price=140.0, margin_of_safety=0.40),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0

    def test_mos_none_rejected(self):
        """Stock with MoS = None (DCF failed) is rejected."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="AMZN", composite_score=80.0, price=180.0, margin_of_safety=None),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0

    def test_mos_exactly_threshold_rejected(self):
        """MoS must be strictly > 0.30, not equal."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="META", composite_score=79.0, price=500.0, margin_of_safety=0.30),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 0

    def test_mos_barely_above_threshold(self):
        """MoS = 0.3001 should pass."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="META", composite_score=79.0, price=500.0, margin_of_safety=0.3001),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 1

    def test_zero_eligible_returns_prev_holdings(self):
        """When no stocks pass, return prev_holdings unchanged."""
        sim = self._make_simulator()
        prev = [
            HoldingRecord(ticker="AAPL", weight=0.5, entry_price=150.0, composite_score=82.0),
            HoldingRecord(ticker="MSFT", weight=0.5, entry_price=300.0, composite_score=80.0),
        ]
        scores = [
            ScoredStock(ticker="GOOG", composite_score=70.0, price=140.0, margin_of_safety=0.10),
        ]
        holdings = sim._select_holdings(scores, prev)
        assert holdings == prev

    def test_equal_weight_multiple(self):
        """4 eligible stocks should each get weight 0.25."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.40),
            ScoredStock(ticker="B", composite_score=82.0, price=100.0, margin_of_safety=0.35),
            ScoredStock(ticker="C", composite_score=80.0, price=100.0, margin_of_safety=0.32),
            ScoredStock(ticker="D", composite_score=79.5, price=100.0, margin_of_safety=0.31),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 4
        for h in holdings:
            assert h.weight == pytest.approx(0.25)
        assert sum(h.weight for h in holdings) == pytest.approx(1.0)

    def test_single_eligible_full_weight(self):
        """1 eligible stock gets weight 1.0."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="AAPL", composite_score=85.0, price=150.0, margin_of_safety=0.40),
            ScoredStock(ticker="MSFT", composite_score=70.0, price=300.0, margin_of_safety=0.50),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 1
        assert holdings[0].weight == pytest.approx(1.0)

    def test_deterministic_sort_order(self):
        """Holdings sorted by (-score, -mos, ticker) for determinism."""
        sim = self._make_simulator()
        scores = [
            ScoredStock(ticker="ZZZ", composite_score=80.0, price=100.0, margin_of_safety=0.35),
            ScoredStock(ticker="AAA", composite_score=80.0, price=100.0, margin_of_safety=0.35),
            ScoredStock(ticker="MMM", composite_score=85.0, price=100.0, margin_of_safety=0.40),
        ]
        holdings1 = sim._select_holdings(scores, [])
        holdings2 = sim._select_holdings(scores, [])
        tickers1 = [h.ticker for h in holdings1]
        tickers2 = [h.ticker for h in holdings2]
        assert tickers1 == tickers2
        # MMM first (higher score), then AAA before ZZZ (alphabetical tiebreak)
        assert tickers1 == ["MMM", "AAA", "ZZZ"]

    def test_top_percentile_mode_unchanged(self):
        """TOP_PERCENTILE mode still uses the old selection logic."""
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            selection_mode=SelectionMode.TOP_PERCENTILE,
            top_percentile=0.50,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider({}),
            benchmark_provider=FakeBenchmarkProvider({}),
        )
        scores = [
            ScoredStock(ticker="A", composite_score=90.0, price=100.0),
            ScoredStock(ticker="B", composite_score=80.0, price=100.0),
            ScoredStock(ticker="C", composite_score=70.0, price=100.0),
            ScoredStock(ticker="D", composite_score=60.0, price=100.0),
        ]
        holdings = sim._select_holdings(scores, [])
        assert len(holdings) == 2
        assert holdings[0].ticker == "A"
        assert holdings[1].ticker == "B"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestConvictionMosSelection -v`
Expected: FAIL — `_select_holdings` doesn't accept `prev_holdings` argument

**Step 3: Write minimal implementation**

In `engine/src/margin_engine/backtesting/simulator.py`:

First, add the import at the top (update the import block around line 21-28):

```python
from margin_engine.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    HoldingRecord,
    MonthlySnapshot,
    PerformanceMetrics,
    RebalanceFrequency,
    SelectionMode,
)
```

Replace the `_select_holdings` method (lines 215-240) with:

```python
    def _select_holdings(
        self, scores: list[ScoredStock], prev_holdings: list[HoldingRecord]
    ) -> list[HoldingRecord]:
        """Select portfolio holdings based on configured selection mode."""
        if self._config.selection_mode == SelectionMode.CONVICTION_MOS:
            return self._select_by_conviction_mos(scores, prev_holdings)
        return self._select_by_top_percentile(scores)

    def _select_by_top_percentile(self, scores: list[ScoredStock]) -> list[HoldingRecord]:
        """Select top N% by composite score, equal weight.

        Sorts by composite_score descending, takes top ceil(len * top_percentile)
        stocks, and assigns equal weight (1/N) to each.
        """
        if not scores:
            return []

        sorted_scores = sorted(scores, key=lambda s: (-s.composite_score, s.ticker))
        n_select = max(1, math.ceil(len(sorted_scores) * self._config.top_percentile))
        selected = sorted_scores[:n_select]
        weight = 1.0 / len(selected)

        return [
            HoldingRecord(
                ticker=stock.ticker,
                weight=weight,
                entry_price=stock.price,
                composite_score=stock.composite_score,
            )
            for stock in selected
        ]

    def _select_by_conviction_mos(
        self, scores: list[ScoredStock], prev_holdings: list[HoldingRecord]
    ) -> list[HoldingRecord]:
        """Select stocks with Exceptional conviction AND MoS above threshold.

        If no stocks pass the filter, returns prev_holdings unchanged (hold-through).
        """
        eligible = [
            s for s in scores
            if s.composite_score >= self._config.min_conviction_score
            and s.margin_of_safety is not None
            and s.margin_of_safety > self._config.min_margin_of_safety
        ]

        if not eligible:
            return prev_holdings

        eligible.sort(
            key=lambda s: (-s.composite_score, -(s.margin_of_safety or 0), s.ticker)
        )
        weight = 1.0 / len(eligible)

        return [
            HoldingRecord(
                ticker=stock.ticker,
                weight=weight,
                entry_price=stock.price,
                composite_score=stock.composite_score,
            )
            for stock in eligible
        ]
```

Update the call site in `run()` at line 101 to pass `prev_holdings`:

```python
            # 2. Select holdings based on configured mode
            new_holdings = self._select_holdings(scores, prev_holdings)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestConvictionMosSelection -v`
Expected: PASS (12 tests)

**Step 5: Run ALL existing simulator tests**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py -v`
Expected: All tests PASS. The existing tests that call `_select_holdings` directly use one argument — these need updating too.

**IMPORTANT:** The existing `TestStockSelection` tests call `sim._select_holdings(scores)` without `prev_holdings`. Update those calls to `sim._select_holdings(scores, [])` to match the new signature. There are 7 calls in `TestStockSelection` to update. The `run()` method handles this internally so integration tests are unaffected.

**Step 6: Commit**

```bash
git add engine/src/margin_engine/backtesting/simulator.py engine/tests/backtesting/test_simulator.py
git commit -m "feat(engine): add conviction_mos selection mode with hold-through"
```

---

### Task 4: Full simulation integration test with CONVICTION_MOS

**Files:**
- Test: `engine/tests/backtesting/test_simulator.py`

**Step 1: Write integration tests**

Add to `engine/tests/backtesting/test_simulator.py`:

```python
class TestConvictionMosSimulation:
    """Integration tests for full simulation with CONVICTION_MOS mode."""

    def test_basic_conviction_mos_simulation(self):
        """Run a full simulation with CONVICTION_MOS selection."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)
        mar2 = date(2020, 3, 2)

        universe_data = {
            jan1: [
                ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.40),
                ScoredStock(ticker="B", composite_score=80.0, price=50.0, margin_of_safety=0.35),
                ScoredStock(ticker="C", composite_score=70.0, price=80.0, margin_of_safety=0.50),
            ],
            feb3: [
                ScoredStock(ticker="A", composite_score=85.0, price=110.0, margin_of_safety=0.38),
                ScoredStock(ticker="B", composite_score=80.0, price=55.0, margin_of_safety=0.33),
                ScoredStock(ticker="C", composite_score=70.0, price=85.0, margin_of_safety=0.48),
            ],
            mar2: [
                ScoredStock(ticker="A", composite_score=85.0, price=105.0, margin_of_safety=0.36),
                ScoredStock(ticker="B", composite_score=80.0, price=52.0, margin_of_safety=0.31),
                ScoredStock(ticker="C", composite_score=70.0, price=90.0, margin_of_safety=0.45),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            min_conviction_score=79.0,
            min_margin_of_safety=0.30,
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
        # Jan: A (score=85, mos=0.40) and B (score=80, mos=0.35) selected
        # C rejected (score=70, below 79)
        snap1 = result.snapshots[0]
        assert len(snap1.holdings) == 2
        tickers = {h.ticker for h in snap1.holdings}
        assert tickers == {"A", "B"}

    def test_hold_through_zero_eligible_period(self):
        """Portfolio holds when no candidates pass filter."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)
        mar2 = date(2020, 3, 2)

        universe_data = {
            jan1: [
                ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.40),
            ],
            feb3: [
                # All fail: A's MoS dropped below threshold
                ScoredStock(ticker="A", composite_score=85.0, price=110.0, margin_of_safety=0.20),
            ],
            mar2: [
                # A recovers
                ScoredStock(ticker="A", composite_score=85.0, price=115.0, margin_of_safety=0.35),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider(universe_data),
            benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 105.0, mar2: 103.0}),
        )
        result = sim.run()

        # Month 1: A selected
        assert len(result.snapshots[0].holdings) == 1
        assert result.snapshots[0].holdings[0].ticker == "A"

        # Month 2: zero eligible -> hold prior (A from month 1)
        assert len(result.snapshots[1].holdings) == 1
        assert result.snapshots[1].holdings[0].ticker == "A"
        assert result.snapshots[1].turnover == pytest.approx(0.0)
        assert result.snapshots[1].transaction_costs == pytest.approx(0.0)

        # Month 3: A qualifies again
        assert len(result.snapshots[2].holdings) == 1
        assert result.snapshots[2].holdings[0].ticker == "A"

    def test_point_in_time_correctness(self):
        """Scores from each date are used, not current values."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)

        universe_data = {
            jan1: [
                ScoredStock(ticker="X", composite_score=82.0, price=100.0, margin_of_safety=0.35),
            ],
            feb3: [
                # X drops below Exceptional
                ScoredStock(ticker="X", composite_score=70.0, price=110.0, margin_of_safety=0.35),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 2, 28),
            selection_mode=SelectionMode.CONVICTION_MOS,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
        )
        sim = WalkForwardSimulator(
            config=config,
            universe_provider=FakeUniverseProvider(universe_data),
            benchmark_provider=FakeBenchmarkProvider({jan1: 100.0, feb3: 105.0}),
        )
        result = sim.run()

        # Jan: X selected (score=82 >= 79)
        assert len(result.snapshots[0].holdings) == 1
        # Feb: X rejected (score=70 < 79), hold prior
        assert len(result.snapshots[1].holdings) == 1
        assert result.snapshots[1].turnover == pytest.approx(0.0)

    def test_determinism_conviction_mos(self):
        """Same inputs produce identical outputs."""
        jan1 = date(2020, 1, 1)
        feb3 = date(2020, 2, 3)

        universe_data = {
            jan1: [
                ScoredStock(ticker="A", composite_score=85.0, price=100.0, margin_of_safety=0.40),
                ScoredStock(ticker="B", composite_score=80.0, price=50.0, margin_of_safety=0.35),
            ],
            feb3: [
                ScoredStock(ticker="A", composite_score=85.0, price=110.0, margin_of_safety=0.38),
                ScoredStock(ticker="B", composite_score=80.0, price=55.0, margin_of_safety=0.33),
            ],
        }

        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 2, 28),
            selection_mode=SelectionMode.CONVICTION_MOS,
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

**Step 2: Run tests**

Run: `uv run pytest engine/tests/backtesting/test_simulator.py::TestConvictionMosSimulation -v`
Expected: PASS (4 tests) — these build on Task 3's implementation

**Step 3: Run full backtesting test suite**

Run: `uv run pytest engine/tests/backtesting/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add engine/tests/backtesting/test_simulator.py
git commit -m "test(engine): add conviction_mos simulation integration tests"
```

---

### Task 5: Extend API BacktestConfigRequest schema

**Files:**
- Modify: `api/src/margin_api/schemas/backtest.py:10-19`
- Test: `api/tests/` (existing backtest tests)

**Step 1: Write the failing test**

Add a test in the appropriate API test file (or create `api/tests/test_backtest_schemas.py`):

```python
from margin_api.schemas.backtest import BacktestConfigRequest


def test_config_request_accepts_conviction_mos():
    config = BacktestConfigRequest(
        selection_mode="conviction_mos",
        min_conviction_score=79.0,
        min_margin_of_safety=0.30,
    )
    assert config.selection_mode == "conviction_mos"
    assert config.min_conviction_score == 79.0
    assert config.min_margin_of_safety == 0.30


def test_config_request_defaults_to_top_percentile():
    config = BacktestConfigRequest()
    assert config.selection_mode == "top_percentile"


def test_config_request_backward_compatible():
    """Existing requests without new fields still work."""
    config = BacktestConfigRequest(
        start_date="2020-01-01",
        top_percentile=0.05,
        benchmark_ticker="SPY",
    )
    assert config.selection_mode == "top_percentile"
    assert config.min_conviction_score == 79.0
    assert config.min_margin_of_safety == 0.30
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_backtest_schemas.py -v`
Expected: FAIL — `selection_mode` not a field

**Step 3: Write minimal implementation**

In `api/src/margin_api/schemas/backtest.py`, add to `BacktestConfigRequest` (after line 19):

```python
    selection_mode: str = "top_percentile"
    min_conviction_score: float = Field(default=79.0, ge=0, le=100)
    min_margin_of_safety: float = Field(default=0.30, ge=-1.0, le=1.0)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_backtest_schemas.py -v`
Expected: PASS

**Step 5: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/schemas/backtest.py api/tests/test_backtest_schemas.py
git commit -m "feat(api): add conviction_mos fields to BacktestConfigRequest"
```

---

### Task 6: Add legend label props to PerformanceChart

**Files:**
- Modify: `web/src/components/backtesting/performance-chart.tsx:1-12, 57, 204-217`
- Test: `web/src/components/backtesting/__tests__/performance-chart.test.tsx`

**Step 1: Write the failing tests**

Add to `web/src/components/backtesting/__tests__/performance-chart.test.tsx`:

```typescript
  it("shows custom legend labels when provided", () => {
    render(
      <PerformanceChart
        snapshots={mockSnapshots}
        portfolioLabel="Exceptional Portfolio (MoS > 30%, Equal-Weight, Monthly)"
        benchmarkLabel="S&P 500 (SPY Total Return)"
      />,
    )
    expect(
      screen.getByText(
        "Exceptional Portfolio (MoS > 30%, Equal-Weight, Monthly)",
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText("S&P 500 (SPY Total Return)"),
    ).toBeInTheDocument()
  })

  it("shows default legend labels when props omitted", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    expect(screen.getByText("Portfolio")).toBeInTheDocument()
    expect(screen.getByText("Benchmark")).toBeInTheDocument()
  })
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/backtesting/__tests__/performance-chart.test.tsx`
Expected: FAIL — custom label text not found

**Step 3: Write minimal implementation**

In `web/src/components/backtesting/performance-chart.tsx`:

Update the interface (lines 9-12):

```typescript
interface PerformanceChartProps {
  snapshots: SnapshotData[]
  portfolioLabel?: string
  benchmarkLabel?: string
  className?: string
}
```

Update the component signature (line 57):

```typescript
export function PerformanceChart({
  snapshots,
  portfolioLabel = "Portfolio",
  benchmarkLabel = "Benchmark",
  className,
}: PerformanceChartProps) {
```

Update the legend (lines 209-216) — replace the hardcoded text:

```typescript
          <span className="text-sm text-text-primary">{portfolioLabel}</span>
```

and:

```typescript
          <span className="text-sm text-text-primary">{benchmarkLabel}</span>
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/backtesting/__tests__/performance-chart.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/backtesting/performance-chart.tsx web/src/components/backtesting/__tests__/performance-chart.test.tsx
git commit -m "feat(web): add portfolioLabel and benchmarkLabel props to PerformanceChart"
```

---

### Task 7: Add tooltips to PerformanceChart

**Files:**
- Modify: `web/src/components/backtesting/performance-chart.tsx`
- Test: `web/src/components/backtesting/__tests__/performance-chart.test.tsx`

**Step 1: Write the failing tests**

Add to `web/src/components/backtesting/__tests__/performance-chart.test.tsx`:

```typescript
import { fireEvent } from "@testing-library/react"

  it("shows tooltip on hover with cumulative returns", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    // Hover over the first hit area
    const hitAreas = screen.getAllByTestId(/^chart-hit-area-/)
    expect(hitAreas.length).toBe(mockSnapshots.length)

    fireEvent.mouseEnter(hitAreas[1])
    const tooltip = screen.getByTestId("chart-tooltip")
    expect(tooltip).toBeInTheDocument()
    // Should show the date
    expect(tooltip.textContent).toContain("2024-02")
  })

  it("hides tooltip on mouse leave", () => {
    render(<PerformanceChart snapshots={mockSnapshots} />)
    const hitAreas = screen.getAllByTestId(/^chart-hit-area-/)

    fireEvent.mouseEnter(hitAreas[0])
    expect(screen.getByTestId("chart-tooltip")).toBeInTheDocument()

    fireEvent.mouseLeave(hitAreas[0])
    expect(screen.queryByTestId("chart-tooltip")).not.toBeInTheDocument()
  })

  it("does not render tooltips for empty snapshots", () => {
    render(<PerformanceChart snapshots={[]} />)
    expect(screen.queryAllByTestId(/^chart-hit-area-/)).toHaveLength(0)
  })
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/backtesting/__tests__/performance-chart.test.tsx`
Expected: FAIL — no `chart-hit-area-*` test IDs

**Step 3: Write minimal implementation**

The component needs to become a client component with `useState`. Add to the top of `performance-chart.tsx`:

```typescript
"use client"

import { useState } from "react"
```

Add state inside the component function (after the early return for empty snapshots):

```typescript
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
```

Inside the SVG, after the portfolio polyline and before the closing `</svg>`, add invisible hit areas:

```typescript
        {/* Tooltip hit areas */}
        {snapshots.map((_, i) => {
          const hitWidth = PLOT_WIDTH / Math.max(snapshots.length - 1, 1)
          const x = scaleX(i) - hitWidth / 2
          return (
            <rect
              key={`hit-${i}`}
              data-testid={`chart-hit-area-${i}`}
              x={Math.max(PADDING.left, x)}
              y={PADDING.top}
              width={hitWidth}
              height={PLOT_HEIGHT}
              fill="transparent"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            />
          )
        })}
```

After the closing `</svg>` tag and before the legend `<div>`, add the tooltip:

```typescript
      {/* Tooltip */}
      {hoveredIndex !== null && (
        <div
          data-testid="chart-tooltip"
          className="absolute bg-bg-elevated border border-border-primary rounded-sm px-3 py-2 shadow-lg pointer-events-none text-xs"
          style={{
            left: scaleX(hoveredIndex) > CHART_WIDTH / 2
              ? `${((scaleX(hoveredIndex) - 140) / CHART_WIDTH) * 100}%`
              : `${(scaleX(hoveredIndex) / CHART_WIDTH) * 100}%`,
            top: `${((scaleY(portfolioCumulative[hoveredIndex]) - 10) / CHART_HEIGHT) * 100}%`,
          }}
        >
          <div className="font-semibold text-text-primary mb-1">
            {formatDateLabel(dates[hoveredIndex])}
          </div>
          <div className="text-text-secondary">
            {portfolioLabel}: {formatPercent(portfolioCumulative[hoveredIndex])}
          </div>
          <div className="text-text-secondary">
            {benchmarkLabel}: {formatPercent(benchmarkCumulative[hoveredIndex])}
          </div>
          <div
            className={
              portfolioCumulative[hoveredIndex] - benchmarkCumulative[hoveredIndex] >= 0
                ? "text-bullish"
                : "text-bearish"
            }
          >
            Excess: {formatPercent(portfolioCumulative[hoveredIndex] - benchmarkCumulative[hoveredIndex])}
          </div>
        </div>
      )}
```

Wrap the outer `<div>` with `relative` positioning so the tooltip positions correctly:

```typescript
    <div className={`relative ${className ?? ""}`}>
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/backtesting/__tests__/performance-chart.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/backtesting/performance-chart.tsx web/src/components/backtesting/__tests__/performance-chart.test.tsx
git commit -m "feat(web): add interactive tooltips to PerformanceChart"
```

---

### Task 8: Wire PerformanceChart into backtesting page

**Files:**
- Modify: `web/src/app/backtesting/page.tsx:111-127`
- Test: `web/src/app/backtesting/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Add to `web/src/app/backtesting/__tests__/page.test.tsx` (check existing test setup for mock patterns):

```typescript
  it("renders performance chart when result has snapshots", async () => {
    // Mock API to return a result with snapshots
    // (adapt to existing mock setup in the file)
    // ...
    expect(screen.getByTestId("performance-chart")).toBeInTheDocument()
  })
```

Note: The exact test depends on the existing mock setup in this file. Check the file first and follow its mocking patterns for `getBacktestResults` and `getBacktestResult`.

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/app/backtesting/__tests__/page.test.tsx`
Expected: FAIL — no performance-chart testid rendered

**Step 3: Write minimal implementation**

In `web/src/app/backtesting/page.tsx`:

Add the import at the top:

```typescript
import { MetricsSummary, ValidationBadges, PerformanceChart } from "@/components/backtesting"
```

Note: Check that the `@/components/backtesting/index.ts` barrel export includes `PerformanceChart`. If not, add the export there or import directly from the file.

Add the chart section in the result display area (after `<MetricsSummary>` section, around line 118):

```typescript
            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Historical Performance
              </h2>
              <PerformanceChart
                snapshots={result.snapshots ?? []}
                portfolioLabel="Exceptional Portfolio (MoS > 30%, Equal-Weight, Monthly)"
                benchmarkLabel="S&P 500 (SPY Total Return)"
              />
            </section>
```

Note: The current `BacktestResultResponse` doesn't include snapshots in the API response (only `num_snapshots`). You may need to:
1. Add `snapshots` to the `BacktestResultResponse` schema in `api/src/margin_api/schemas/backtest.py`
2. Add `snapshots` to the `BacktestResult` TypeScript type in `web/src/lib/api/types.ts`
3. Return actual snapshot data from the API endpoint

If snapshots aren't available yet (API returns synthetic data), render the chart with an empty array and rely on the empty state. This can be wired up fully when the API is connected to the real `WalkForwardSimulator`.

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/app/backtesting/__tests__/page.test.tsx`
Expected: PASS

**Step 5: Run all web tests**

Run: `cd web && npx vitest run`
Expected: All PASS

**Step 6: Commit**

```bash
git add web/src/app/backtesting/page.tsx web/src/app/backtesting/__tests__/page.test.tsx web/src/components/backtesting/index.ts
git commit -m "feat(web): wire PerformanceChart into backtesting page with labels"
```

---

### Task 9: Final verification

**Step 1: Run complete engine test suite**

Run: `uv run pytest engine/tests/ -v`
Expected: All 784+ tests PASS

**Step 2: Run complete API test suite**

Run: `uv run pytest api/tests/ -v`
Expected: All 294+ tests PASS

**Step 3: Run complete web test suite**

Run: `cd web && npx vitest run`
Expected: All tests PASS

**Step 4: Commit any fixups**

If any tests fail, fix and commit with appropriate message.
