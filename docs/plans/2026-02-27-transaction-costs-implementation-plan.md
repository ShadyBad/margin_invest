# Transaction Costs in Backtesting — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add realistic transaction cost modeling with gross-vs-net transparency, sensitivity analysis, capacity analysis, and academic benchmark validation to the backtesting engine.

**Architecture:** Promote the existing non-linear cost model as the default, add `gross_return` tracking to MonthlySnapshot, build post-hoc sensitivity/capacity analysis from snapshot data, and surface everything through API schemas and three new frontend components.

**Tech Stack:** Python/Pydantic (engine + API), Recharts (frontend charts), Vitest + pytest (testing)

---

## Dependency Graph

```
T1 (cost model defaults + academic benchmarks)
T2 (gross_return on MonthlySnapshot)  ── depends on T1
T3 (gross metrics in PerformanceCalculator) ── depends on T2
T4 (sensitivity analysis) ── depends on T3
T5 (capacity analysis module) ── depends on T3
T6 (API schema + service wiring) ── depends on T4, T5
T7 (frontend: MetricsSummary gross annotations) ── depends on T6
T8 (frontend: CostSensitivity component) ── depends on T6
T9 (frontend: CapacityChart component) ── depends on T6
T10 (frontend: CostDisclosure component) ── depends on T6
T11 (backtest page integration) ── depends on T7, T8, T9, T10
```

**Parallel groups:** T1; then T2; then T3; then T4+T5 in parallel; then T6; then T7+T8+T9+T10 in parallel; then T11.

---

### Task 1: Add Cost Assumptions Constant and Academic Benchmarks

**Files:**
- Modify: `engine/src/margin_engine/backtesting/cost_model.py`
- Test: `engine/tests/backtesting/test_cost_model.py`

**Step 1: Write the failing tests**

Add to `engine/tests/backtesting/test_cost_model.py`:

```python
from margin_engine.backtesting.cost_model import (
    COST_ASSUMPTIONS,
    ACADEMIC_BENCHMARKS,
    validate_cost_assumptions,
)


class TestCostAssumptions:
    def test_assumptions_has_required_keys(self):
        assert "base_commission_bps" in COST_ASSUMPTIONS
        assert "market_impact_coefficient" in COST_ASSUMPTIONS
        assert "spread_formula" in COST_ASSUMPTIONS

    def test_assumptions_values_are_positive(self):
        assert COST_ASSUMPTIONS["base_commission_bps"] > 0
        assert COST_ASSUMPTIONS["market_impact_coefficient"] > 0


class TestAcademicBenchmarks:
    def test_benchmarks_non_empty(self):
        assert len(ACADEMIC_BENCHMARKS) >= 2

    def test_benchmark_structure(self):
        for b in ACADEMIC_BENCHMARKS:
            assert "source" in b
            assert "cost_range_bps" in b
            assert len(b["cost_range_bps"]) == 2
            assert b["cost_range_bps"][0] <= b["cost_range_bps"][1]


class TestValidateCostAssumptions:
    def test_within_range(self):
        result = validate_cost_assumptions(model_cost_bps=15.0, market_cap_billions=50.0)
        assert result["status"] == "within_range"

    def test_below_benchmark_optimistic(self):
        result = validate_cost_assumptions(model_cost_bps=3.0, market_cap_billions=50.0)
        assert result["status"] == "below_benchmark"

    def test_above_benchmark_conservative(self):
        result = validate_cost_assumptions(model_cost_bps=100.0, market_cap_billions=50.0)
        assert result["status"] == "above_benchmark"

    def test_small_cap_uses_small_cap_range(self):
        result = validate_cost_assumptions(model_cost_bps=40.0, market_cap_billions=0.5)
        assert result["status"] == "within_range"

    def test_result_contains_source(self):
        result = validate_cost_assumptions(model_cost_bps=15.0, market_cap_billions=50.0)
        assert "source" in result
        assert "Frazzini" in result["source"]
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/backtesting/test_cost_model.py::TestCostAssumptions -v`
Expected: FAIL — `COST_ASSUMPTIONS` not importable.

**Step 3: Implement**

Add to `engine/src/margin_engine/backtesting/cost_model.py` after the existing imports:

```python
# ---------------------------------------------------------------------------
# Documented cost assumptions
# ---------------------------------------------------------------------------

COST_ASSUMPTIONS: dict[str, object] = {
    "base_commission_bps": 5.0,
    "market_impact_coefficient": 0.1,
    "spread_formula": "3.0 + 50.0 / sqrt(market_cap_billions)",
    "spread_description": "Market-cap dependent half-spread. Mega-cap ~4 bps, mid-cap ~10 bps, small-cap ~18 bps.",
    "impact_formula": "coefficient * sqrt(trade_value / ADV) * 10_000",
    "impact_description": "Square-root market impact model. Conservative coefficient of 0.1.",
    "not_modeled": [
        "Short-selling costs / borrow fees",
        "Taxes (capital gains, wash sale rules)",
        "Management fees / fund expenses",
        "Opportunity cost of delayed execution",
        "Time-of-day effects",
    ],
}

ACADEMIC_BENCHMARKS: list[dict[str, object]] = [
    {
        "source": "Frazzini, Israel & Moskowitz (2015)",
        "paper": "Trading Costs of Asset Pricing Anomalies",
        "asset_class": "US Equities",
        "market_cap_range": "large_cap",
        "cost_range_bps": (10.0, 20.0),
    },
    {
        "source": "Frazzini, Israel & Moskowitz (2015)",
        "paper": "Trading Costs of Asset Pricing Anomalies",
        "asset_class": "US Equities",
        "market_cap_range": "small_cap",
        "cost_range_bps": (30.0, 60.0),
    },
    {
        "source": "Novy-Marx & Velikov (2016)",
        "paper": "A Taxonomy of Anomalies and Their Trading Costs",
        "asset_class": "US Equities",
        "market_cap_range": "all_cap",
        "cost_range_bps": (10.0, 50.0),
    },
]


def validate_cost_assumptions(
    model_cost_bps: float,
    market_cap_billions: float,
) -> dict[str, object]:
    """Compare model cost against academic benchmark range for given market cap.

    Returns dict with status ("within_range", "below_benchmark", "above_benchmark"),
    the benchmark_range_bps, and source citation.
    """
    # Pick the right benchmark by market cap tier
    if market_cap_billions >= 10.0:
        tier = "large_cap"
    elif market_cap_billions >= 2.0:
        tier = "all_cap"
    else:
        tier = "small_cap"

    benchmark = next(
        (b for b in ACADEMIC_BENCHMARKS if b["market_cap_range"] == tier),
        ACADEMIC_BENCHMARKS[0],
    )
    low, high = benchmark["cost_range_bps"]

    if model_cost_bps < low:
        status = "below_benchmark"
    elif model_cost_bps > high:
        status = "above_benchmark"
    else:
        status = "within_range"

    return {
        "model_cost_bps": model_cost_bps,
        "benchmark_range_bps": (low, high),
        "status": status,
        "source": benchmark["source"],
    }
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/backtesting/test_cost_model.py -v`
Expected: All pass (old + new).

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/cost_model.py engine/tests/backtesting/test_cost_model.py
git commit -m "feat(engine): add COST_ASSUMPTIONS, ACADEMIC_BENCHMARKS, and validate_cost_assumptions"
```

---

### Task 2: Add gross_return to MonthlySnapshot and Wire in Both Orchestrators

**Files:**
- Modify: `engine/src/margin_engine/backtesting/models.py:87-98`
- Modify: `engine/src/margin_engine/backtesting/simulator.py:166-221`
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py:228-308`
- Test: `engine/tests/backtesting/test_simulator.py` (update existing snapshot helper)
- Test: `engine/tests/backtesting/test_metrics.py` (update `_make_snapshot` helper)

**Step 1: Write the failing test**

In a new file `engine/tests/backtesting/test_gross_return.py`:

```python
"""Tests for gross_return tracking in MonthlySnapshot."""

from datetime import date

from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot


class TestMonthlySnapshotGrossReturn:
    def test_gross_return_field_exists(self):
        snap = MonthlySnapshot(
            date=date(2024, 1, 28),
            holdings=[HoldingRecord(ticker="AAPL", weight=1.0, entry_price=100.0, composite_score=90.0)],
            portfolio_value=1_000_000,
            benchmark_value=1_000_000,
            portfolio_return=0.02,
            benchmark_return=0.01,
            turnover=0.1,
            transaction_costs=100.0,
            gross_return=0.025,
        )
        assert snap.gross_return == 0.025

    def test_gross_return_defaults_to_portfolio_return(self):
        """When gross_return not provided, it defaults to portfolio_return (backwards compat)."""
        snap = MonthlySnapshot(
            date=date(2024, 1, 28),
            holdings=[HoldingRecord(ticker="AAPL", weight=1.0, entry_price=100.0, composite_score=90.0)],
            portfolio_value=1_000_000,
            benchmark_value=1_000_000,
            portfolio_return=0.02,
            benchmark_return=0.01,
            turnover=0.1,
            transaction_costs=100.0,
        )
        assert snap.gross_return == 0.02

    def test_gross_return_greater_than_or_equal_net(self):
        """Gross return should always be >= net return (costs reduce returns)."""
        snap = MonthlySnapshot(
            date=date(2024, 1, 28),
            holdings=[],
            portfolio_value=1_000_000,
            benchmark_value=1_000_000,
            portfolio_return=0.02,
            benchmark_return=0.01,
            turnover=0.1,
            transaction_costs=100.0,
            gross_return=0.025,
        )
        assert snap.gross_return >= snap.portfolio_return
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_gross_return.py -v`
Expected: FAIL — `gross_return` is not a field on MonthlySnapshot.

**Step 3: Add gross_return to MonthlySnapshot**

In `engine/src/margin_engine/backtesting/models.py`, modify `MonthlySnapshot` class (line 87-98):

Add after `transaction_costs` field:
```python
    gross_return: float = Field(
        default=None,
        description="Month-over-month return BEFORE transaction costs",
    )
```

Add a model_validator to default `gross_return` to `portfolio_return` when not provided:
```python
    @model_validator(mode="after")
    def _default_gross_return(self) -> MonthlySnapshot:
        if self.gross_return is None:
            self.gross_return = self.portfolio_return
        return self
```

**Step 4: Wire gross_return in WalkForwardSimulator**

In `engine/src/margin_engine/backtesting/simulator.py`, around lines 188-221:

After computing `portfolio_return` (which is net), compute `gross_return` from the pre-cost portfolio value:

```python
            # Compute gross return (before transaction cost deduction)
            if i == 0:
                gross_return = 0.0
            else:
                prev_portfolio_value = snapshots[i - 1].portfolio_value
                if prev_portfolio_value > 0:
                    gross_return = (portfolio_value - prev_portfolio_value) / prev_portfolio_value
                else:
                    gross_return = 0.0
```

Note: `portfolio_value` at this point is PRE-cost (the deduction happens at line 177 `portfolio_value_after_costs = portfolio_value - transaction_costs`). The `portfolio_return` is computed at lines 195-197 from `portfolio_value_after_costs`, so `gross_return` should be computed from `portfolio_value` (pre-cost) before the deduction.

Add `gross_return=gross_return` to the MonthlySnapshot constructor at line 212.

**Step 5: Wire gross_return in ReplayOrchestrator**

In `engine/src/margin_engine/backtesting/replay_orchestrator.py`, around lines 228-308:

After line 236 (`portfolio_value *= 1.0 + total_return`), capture the pre-cost value. Then after cost deduction at line 241, compute gross_return:

```python
            # Capture pre-cost portfolio value for gross return
            pre_cost_value = portfolio_value

            # Transaction costs (existing line 240-241)
            cost = portfolio_value * (turnover * self._config.transaction_cost_bps / 10_000)
            portfolio_value -= cost

            # ...existing benchmark/return code...

            # Gross return
            if not snapshots:
                gross_return = 0.0
            else:
                prev_pv = snapshots[-1].portfolio_value
                gross_return = (pre_cost_value - prev_pv) / prev_pv if prev_pv > 0 else 0.0
```

Add `gross_return=gross_return` to MonthlySnapshot constructor at line 299.

**Step 6: Update existing test helpers**

In `engine/tests/backtesting/test_metrics.py`, update `_make_snapshot` to accept optional `gross_return` parameter (with default `None` so existing tests keep working).

In any other test files that construct `MonthlySnapshot` directly, the default `None` → `portfolio_return` validator handles backwards compatibility.

**Step 7: Run all backtesting tests**

Run: `uv run pytest engine/tests/backtesting/ -v`
Expected: All pass.

**Step 8: Commit**

```bash
git add engine/src/margin_engine/backtesting/models.py engine/src/margin_engine/backtesting/simulator.py engine/src/margin_engine/backtesting/replay_orchestrator.py engine/tests/backtesting/test_gross_return.py engine/tests/backtesting/test_metrics.py
git commit -m "feat(engine): add gross_return to MonthlySnapshot, wire in both orchestrators"
```

---

### Task 3: Add Gross Metrics to PerformanceCalculator

**Files:**
- Modify: `engine/src/margin_engine/backtesting/models.py:105-118` (PerformanceMetrics)
- Modify: `engine/src/margin_engine/backtesting/metrics.py:33-98` (PerformanceCalculator.calculate)
- Test: `engine/tests/backtesting/test_metrics.py`

**Step 1: Write the failing test**

Add to `engine/tests/backtesting/test_metrics.py`:

```python
class TestGrossMetrics:
    """Verify gross metrics are computed from gross_return field."""

    def test_gross_cagr_computed(self):
        snapshots = [
            _make_snapshot(1, 1_030_000, 1_020_000, 0.028, 0.02, gross_return=0.03),
            _make_snapshot(2, 1_060_900, 1_040_400, 0.028, 0.02, gross_return=0.03),
            _make_snapshot(3, 1_048_191, 1_040_400, -0.012, 0.00, gross_return=-0.01),
        ]
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert hasattr(m, "gross_cagr")
        assert m.gross_cagr > m.cagr  # Gross CAGR > net CAGR

    def test_gross_sharpe_computed(self):
        snapshots = [
            _make_snapshot(1, 1_030_000, 1_020_000, 0.028, 0.02, gross_return=0.03),
            _make_snapshot(2, 1_060_900, 1_040_400, 0.028, 0.02, gross_return=0.03),
            _make_snapshot(3, 1_048_191, 1_040_400, -0.012, 0.00, gross_return=-0.01),
        ]
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert hasattr(m, "gross_sharpe")
        assert m.gross_sharpe >= m.sharpe_ratio

    def test_cost_drag_bps(self):
        """cost_drag_bps = (gross_cagr - net_cagr) * 10_000."""
        snapshots = [
            _make_snapshot(1, 1_030_000, 1_020_000, 0.028, 0.02, gross_return=0.03),
            _make_snapshot(2, 1_060_900, 1_040_400, 0.028, 0.02, gross_return=0.03),
            _make_snapshot(3, 1_048_191, 1_040_400, -0.012, 0.00, gross_return=-0.01),
        ]
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        expected_drag = (m.gross_cagr - m.cagr) * 10_000
        assert abs(m.cost_drag_bps - expected_drag) < 0.01
        assert m.cost_drag_bps >= 0

    def test_gross_max_drawdown(self):
        snapshots = [
            _make_snapshot(1, 1_030_000, 1_020_000, 0.028, 0.02, gross_return=0.03),
            _make_snapshot(2, 1_060_900, 1_040_400, 0.028, 0.02, gross_return=0.03),
            _make_snapshot(3, 1_048_191, 1_040_400, -0.012, 0.00, gross_return=-0.01),
        ]
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert hasattr(m, "gross_max_drawdown")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_metrics.py::TestGrossMetrics -v`
Expected: FAIL.

**Step 3: Add fields to PerformanceMetrics**

In `engine/src/margin_engine/backtesting/models.py`, add to `PerformanceMetrics` (after `avg_turnover`):

```python
    gross_cagr: float = 0.0
    gross_sharpe: float = 0.0
    gross_max_drawdown: float = 0.0
    cost_drag_bps: float = 0.0
```

Default to 0.0 so all existing code that constructs PerformanceMetrics without these fields still works.

**Step 4: Compute gross metrics in PerformanceCalculator.calculate()**

In `engine/src/margin_engine/backtesting/metrics.py`, in the `calculate` method, after the existing metric calculations (around line 84), add:

```python
        # Gross metrics (from pre-cost returns)
        gross_returns = [s.gross_return for s in snapshots]
        gross_total_ratio = math.prod(1.0 + r for r in gross_returns)
        gross_cagr = self._cagr(gross_total_ratio, years)
        gross_sharpe = self._sharpe(gross_returns, risk_free_monthly)

        # Gross portfolio values (reconstruct from gross returns)
        gross_values = []
        gv = portfolio_values[0] if portfolio_values else 0.0
        gross_values.append(gv)
        for gr in gross_returns[1:]:
            gv = gv * (1.0 + gr)
            gross_values.append(gv)
        gross_max_dd = self._max_drawdown(gross_values) if len(gross_values) >= 2 else 0.0

        cost_drag = (gross_cagr - portfolio_cagr) * 10_000
```

Then add these to the return statement:
```python
            gross_cagr=gross_cagr,
            gross_sharpe=gross_sharpe,
            gross_max_drawdown=gross_max_dd,
            cost_drag_bps=max(cost_drag, 0.0),
```

Update `_make_snapshot` helper in `test_metrics.py` to accept `gross_return`:

```python
def _make_snapshot(
    month: int,
    portfolio_value: float,
    benchmark_value: float,
    portfolio_return: float,
    benchmark_return: float,
    turnover: float = 0.1,
    transaction_costs: float = 100.0,
    gross_return: float | None = None,
) -> MonthlySnapshot:
    return MonthlySnapshot(
        date=date(2024, month, 28),
        holdings=[HoldingRecord(ticker="AAPL", weight=1.0, entry_price=100.0, composite_score=90.0)],
        portfolio_value=portfolio_value,
        benchmark_value=benchmark_value,
        portfolio_return=portfolio_return,
        benchmark_return=benchmark_return,
        turnover=turnover,
        transaction_costs=transaction_costs,
        gross_return=gross_return,
    )
```

**Step 5: Run all tests**

Run: `uv run pytest engine/tests/backtesting/test_metrics.py -v`
Expected: All pass (old golden values unchanged since we only added new fields with defaults).

**Step 6: Commit**

```bash
git add engine/src/margin_engine/backtesting/models.py engine/src/margin_engine/backtesting/metrics.py engine/tests/backtesting/test_metrics.py
git commit -m "feat(engine): add gross_cagr, gross_sharpe, gross_max_drawdown, cost_drag_bps to PerformanceMetrics"
```

---

### Task 4: Sensitivity Analysis

**Files:**
- Modify: `engine/src/margin_engine/backtesting/metrics.py`
- Test: `engine/tests/backtesting/test_sensitivity.py` (new)

**Step 1: Write the failing test**

Create `engine/tests/backtesting/test_sensitivity.py`:

```python
"""Tests for cost sensitivity analysis."""

from datetime import date

import pytest
from margin_engine.backtesting.metrics import run_sensitivity_analysis
from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot


def _snap(month: int, pv: float, bv: float, pr: float, br: float, tc: float, gr: float) -> MonthlySnapshot:
    return MonthlySnapshot(
        date=date(2024, month, 28),
        holdings=[HoldingRecord(ticker="AAPL", weight=1.0, entry_price=100.0, composite_score=90.0)],
        portfolio_value=pv, benchmark_value=bv,
        portfolio_return=pr, benchmark_return=br,
        turnover=0.1, transaction_costs=tc, gross_return=gr,
    )


class TestRunSensitivityAnalysis:
    @pytest.fixture()
    def snapshots(self) -> list[MonthlySnapshot]:
        return [
            _snap(1, 1_030_000, 1_020_000, 0.028, 0.02, 200.0, 0.03),
            _snap(2, 1_060_000, 1_040_000, 0.027, 0.02, 300.0, 0.03),
            _snap(3, 1_050_000, 1_040_000, -0.011, 0.00, 100.0, -0.01),
        ]

    def test_returns_three_rows_by_default(self, snapshots):
        result = run_sensitivity_analysis(snapshots)
        assert len(result) == 3

    def test_multipliers_are_1_2_3(self, snapshots):
        result = run_sensitivity_analysis(snapshots)
        assert [r["multiplier"] for r in result] == [1.0, 2.0, 3.0]

    def test_higher_multiplier_lower_cagr(self, snapshots):
        result = run_sensitivity_analysis(snapshots)
        assert result[0]["cagr"] > result[1]["cagr"] > result[2]["cagr"]

    def test_higher_multiplier_lower_sharpe(self, snapshots):
        result = run_sensitivity_analysis(snapshots)
        assert result[0]["sharpe"] >= result[1]["sharpe"] >= result[2]["sharpe"]

    def test_cost_drag_scales_with_multiplier(self, snapshots):
        result = run_sensitivity_analysis(snapshots)
        drag_1x = result[0]["cost_drag_bps"]
        drag_2x = result[1]["cost_drag_bps"]
        # 2x costs should roughly double the drag
        assert drag_2x > drag_1x

    def test_base_row_matches_actual_metrics(self, snapshots):
        """1x multiplier should match the original net metrics."""
        from margin_engine.backtesting.metrics import PerformanceCalculator
        calc = PerformanceCalculator()
        actual = calc.calculate(snapshots)
        result = run_sensitivity_analysis(snapshots)
        assert result[0]["cagr"] == pytest.approx(actual.cagr, rel=1e-4)

    def test_custom_multipliers(self, snapshots):
        result = run_sensitivity_analysis(snapshots, multipliers=[1.0, 1.5, 2.0, 5.0])
        assert len(result) == 4
        assert result[3]["multiplier"] == 5.0
```

**Step 2: Run to verify failure**

Run: `uv run pytest engine/tests/backtesting/test_sensitivity.py -v`
Expected: FAIL — `run_sensitivity_analysis` not importable.

**Step 3: Implement**

Add to `engine/src/margin_engine/backtesting/metrics.py`:

```python
def run_sensitivity_analysis(
    snapshots: list[MonthlySnapshot],
    multipliers: list[float] | None = None,
    risk_free_rate: float = 0.04,
) -> list[dict[str, float]]:
    """Recompute performance metrics at different cost multiplier levels.

    Takes the gross_return and transaction_costs from each snapshot, scales
    costs by each multiplier, and recomputes net returns + metrics.

    Args:
        snapshots: Original snapshots with gross_return and transaction_costs populated.
        multipliers: Cost multiplier levels (default [1.0, 2.0, 3.0]).
        risk_free_rate: Annual risk-free rate for Sharpe calculation.

    Returns:
        List of dicts, one per multiplier, with keys:
        multiplier, cagr, sharpe, max_drawdown, cost_drag_bps.
    """
    if multipliers is None:
        multipliers = [1.0, 2.0, 3.0]

    calc = PerformanceCalculator(risk_free_rate=risk_free_rate)
    gross_returns = [s.gross_return for s in snapshots]
    costs_dollars = [s.transaction_costs for s in snapshots]

    # Compute gross CAGR once for cost_drag calculation
    if not snapshots:
        return [{"multiplier": m, "cagr": 0.0, "sharpe": 0.0, "max_drawdown": 0.0, "cost_drag_bps": 0.0} for m in multipliers]

    num_months = len(snapshots)
    years = num_months / 12.0
    gross_total_ratio = math.prod(1.0 + r for r in gross_returns)
    gross_cagr = calc._cagr(gross_total_ratio, years)

    results = []
    for mult in multipliers:
        # Reconstruct net returns at this cost level
        adjusted_returns = []
        pv = snapshots[0].portfolio_value / (1.0 + snapshots[0].portfolio_return) if snapshots[0].portfolio_return != -1.0 else snapshots[0].portfolio_value
        values = [pv]

        for i, snap in enumerate(snapshots):
            # Gross portfolio value
            gross_pv = pv * (1.0 + gross_returns[i])
            # Adjusted cost
            adjusted_cost = costs_dollars[i] * mult
            # Net portfolio value
            net_pv = gross_pv - adjusted_cost
            # Net return
            net_return = (net_pv - pv) / pv if pv > 0 else 0.0
            adjusted_returns.append(net_return)
            pv = net_pv
            values.append(pv)

        # Compute metrics from adjusted returns
        total_ratio = math.prod(1.0 + r for r in adjusted_returns)
        cagr = calc._cagr(total_ratio, years)
        sharpe = calc._sharpe(adjusted_returns, risk_free_rate / 12.0)
        max_dd = calc._max_drawdown(values[1:])  # skip initial value
        cost_drag = (gross_cagr - cagr) * 10_000

        results.append({
            "multiplier": mult,
            "cagr": cagr,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "cost_drag_bps": max(cost_drag, 0.0),
        })

    return results
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/backtesting/test_sensitivity.py -v`
Expected: All pass.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/metrics.py engine/tests/backtesting/test_sensitivity.py
git commit -m "feat(engine): add run_sensitivity_analysis for cost stress testing"
```

---

### Task 5: Capacity Analysis Module

**Files:**
- Create: `engine/src/margin_engine/backtesting/capacity.py`
- Test: `engine/tests/backtesting/test_capacity.py` (new)

**Step 1: Write the failing test**

Create `engine/tests/backtesting/test_capacity.py`:

```python
"""Tests for capacity analysis."""

from datetime import date

import pytest
from margin_engine.backtesting.capacity import run_capacity_analysis
from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot


def _snap(month: int, pv: float, bv: float, pr: float, br: float, tc: float, gr: float, turnover: float = 0.2) -> MonthlySnapshot:
    return MonthlySnapshot(
        date=date(2024, month, 28),
        holdings=[
            HoldingRecord(ticker="AAPL", weight=0.5, entry_price=150.0, composite_score=85.0),
            HoldingRecord(ticker="MSFT", weight=0.5, entry_price=300.0, composite_score=80.0),
        ],
        portfolio_value=pv, benchmark_value=bv,
        portfolio_return=pr, benchmark_return=br,
        turnover=turnover, transaction_costs=tc, gross_return=gr,
    )


class TestRunCapacityAnalysis:
    @pytest.fixture()
    def snapshots(self) -> list[MonthlySnapshot]:
        return [
            _snap(1, 1_030_000, 1_020_000, 0.028, 0.02, 200.0, 0.03),
            _snap(2, 1_060_000, 1_040_000, 0.027, 0.02, 300.0, 0.03),
            _snap(3, 1_090_000, 1_060_000, 0.027, 0.02, 250.0, 0.03),
            _snap(4, 1_080_000, 1_060_000, -0.010, 0.00, 100.0, -0.01),
        ]

    def test_returns_rows_for_each_aum(self, snapshots):
        result = run_capacity_analysis(snapshots)
        assert len(result["rows"]) == 7  # default 7 AUM levels

    def test_aum_levels_ascending(self, snapshots):
        result = run_capacity_analysis(snapshots)
        aums = [r["aum"] for r in result["rows"]]
        assert aums == sorted(aums)

    def test_sharpe_decreases_with_aum(self, snapshots):
        result = run_capacity_analysis(snapshots)
        sharpes = [r["sharpe"] for r in result["rows"]]
        # Sharpe should generally decrease (or stay flat) as AUM increases
        assert sharpes[0] >= sharpes[-1]

    def test_impact_increases_with_aum(self, snapshots):
        result = run_capacity_analysis(snapshots)
        impacts = [r["avg_impact_bps"] for r in result["rows"]]
        assert impacts[-1] > impacts[0]

    def test_breakeven_aum_returned(self, snapshots):
        result = run_capacity_analysis(snapshots)
        assert "breakeven_aum" in result
        # breakeven_aum is None or a positive number
        if result["breakeven_aum"] is not None:
            assert result["breakeven_aum"] > 0

    def test_custom_aum_levels(self, snapshots):
        result = run_capacity_analysis(snapshots, aum_levels=[1e6, 1e9])
        assert len(result["rows"]) == 2

    def test_small_aum_matches_base_metrics(self, snapshots):
        """At small AUM ($1M), impact costs are negligible."""
        result = run_capacity_analysis(snapshots, aum_levels=[1e6])
        from margin_engine.backtesting.metrics import PerformanceCalculator
        calc = PerformanceCalculator()
        actual = calc.calculate(snapshots)
        # At $1M AUM, added impact should be tiny, so metrics should be very close
        assert result["rows"][0]["sharpe"] == pytest.approx(actual.sharpe_ratio, abs=0.5)
```

**Step 2: Run to verify failure**

Run: `uv run pytest engine/tests/backtesting/test_capacity.py -v`
Expected: FAIL — module not found.

**Step 3: Implement**

Create `engine/src/margin_engine/backtesting/capacity.py`:

```python
"""Capacity analysis for backtesting.

Estimates how strategy performance degrades as AUM increases,
due to growing market impact costs. Uses the square-root impact
model from cost_model.py.
"""

from __future__ import annotations

import math

from margin_engine.backtesting.cost_model import compute_market_impact_bps
from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import MonthlySnapshot

# Default AUM levels: $1M to $1B
DEFAULT_AUM_LEVELS = [1e6, 10e6, 50e6, 100e6, 250e6, 500e6, 1e9]

# Conservative ADV proxy: 0.5% of market cap as daily turnover
_ADV_PROXY_FRACTION = 0.005
_DEFAULT_MARKET_CAP = 10e9  # $10B default for ADV proxy

# Sharpe threshold for "strategy breaks"
_BREAKEVEN_SHARPE = 0.5


def run_capacity_analysis(
    snapshots: list[MonthlySnapshot],
    aum_levels: list[float] | None = None,
    market_impact_coefficient: float = 0.1,
    risk_free_rate: float = 0.04,
) -> dict:
    """Estimate performance at various AUM levels.

    For each AUM level, scales trade sizes proportionally and computes
    the additional market impact cost, then re-derives net returns and
    metrics.

    Args:
        snapshots: Monthly snapshots with gross_return, turnover, holdings.
        aum_levels: AUM levels to evaluate (default $1M to $1B).
        market_impact_coefficient: Impact model coefficient.
        risk_free_rate: Annual risk-free rate.

    Returns:
        Dict with "rows" (list of per-AUM dicts) and "breakeven_aum" (float or None).
    """
    if aum_levels is None:
        aum_levels = DEFAULT_AUM_LEVELS

    if not snapshots:
        return {
            "rows": [{"aum": a, "cagr": 0.0, "sharpe": 0.0, "avg_impact_bps": 0.0} for a in aum_levels],
            "breakeven_aum": None,
        }

    calc = PerformanceCalculator(risk_free_rate=risk_free_rate)
    gross_returns = [s.gross_return for s in snapshots]
    turnovers = [s.turnover for s in snapshots]
    num_holdings_list = [max(len(s.holdings), 1) for s in snapshots]
    base_costs = [s.transaction_costs for s in snapshots]
    num_months = len(snapshots)
    years = num_months / 12.0

    # ADV proxy: use default market cap * daily turnover fraction
    adv = _DEFAULT_MARKET_CAP * _ADV_PROXY_FRACTION  # $50M

    rows = []
    breakeven_aum = None

    for aum in aum_levels:
        # Compute additional impact costs at this AUM level
        impact_bps_list = []
        adjusted_returns = []
        pv = aum  # start at this AUM

        for i in range(num_months):
            gross_pv = pv * (1.0 + gross_returns[i])

            # Trade value per position at this AUM
            trade_fraction = turnovers[i] / num_holdings_list[i] if num_holdings_list[i] > 0 else turnovers[i]
            trade_value = pv * trade_fraction

            # Market impact at this AUM scale
            impact_bps = compute_market_impact_bps(trade_value, adv, market_impact_coefficient)
            impact_bps_list.append(impact_bps)

            # Total cost = base non-impact costs (scaled from original) + impact at new AUM
            # Scale base costs proportionally to AUM
            original_pv = snapshots[i].portfolio_value
            scale_factor = pv / original_pv if original_pv > 0 else 1.0
            base_cost = base_costs[i] * scale_factor

            # Additional impact cost
            impact_cost = pv * turnovers[i] * impact_bps / 10_000

            total_cost = base_cost + impact_cost
            net_pv = gross_pv - total_cost
            net_return = (net_pv - pv) / pv if pv > 0 else 0.0
            adjusted_returns.append(net_return)
            pv = net_pv

        # Compute metrics
        total_ratio = math.prod(1.0 + r for r in adjusted_returns)
        cagr = calc._cagr(total_ratio, years)
        sharpe = calc._sharpe(adjusted_returns, risk_free_rate / 12.0)
        avg_impact = sum(impact_bps_list) / len(impact_bps_list) if impact_bps_list else 0.0

        rows.append({
            "aum": aum,
            "cagr": cagr,
            "sharpe": sharpe,
            "avg_impact_bps": avg_impact,
        })

        # Track breakeven
        if breakeven_aum is None and sharpe < _BREAKEVEN_SHARPE:
            breakeven_aum = aum

    return {
        "rows": rows,
        "breakeven_aum": breakeven_aum,
    }
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/backtesting/test_capacity.py -v`
Expected: All pass.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/capacity.py engine/tests/backtesting/test_capacity.py
git commit -m "feat(engine): add capacity analysis module for AUM scaling"
```

---

### Task 6: API Schema and Service Wiring

**Files:**
- Modify: `api/src/margin_api/schemas/backtest.py`
- Modify: `api/src/margin_api/services/backtest.py`
- Modify: `web/src/lib/api/types.ts`
- Test: `api/tests/test_backtest_service.py` (or whatever existing service tests exist)

**Step 1: Write the failing test**

Find the existing API backtest service tests and add:

```python
class TestFullBacktestResponseHasCostFields:
    def test_sensitivity_field_present(self):
        result = get_default_replay_result()
        response = build_full_response(result)
        assert hasattr(response, "sensitivity")

    def test_capacity_field_present(self):
        result = get_default_replay_result()
        response = build_full_response(result)
        assert hasattr(response, "capacity")

    def test_metrics_has_gross_fields(self):
        result = get_default_replay_result()
        response = build_full_response(result)
        assert hasattr(response.metrics, "gross_cagr")
        assert hasattr(response.metrics, "cost_drag_bps")
```

**Step 2: Run to verify failure**

Run: `uv run pytest api/tests/ -k "CostFields" -v`
Expected: FAIL.

**Step 3: Update API schemas**

In `api/src/margin_api/schemas/backtest.py`:

Add new response schemas:

```python
class CostSensitivityRow(BaseModel):
    multiplier: float
    cagr: float
    sharpe: float
    max_drawdown: float
    cost_drag_bps: float

class SensitivityResponse(BaseModel):
    rows: list[CostSensitivityRow]

class CapacityRow(BaseModel):
    aum: float
    cagr: float
    sharpe: float
    avg_impact_bps: float

class CapacityResponse(BaseModel):
    rows: list[CapacityRow]
    breakeven_aum: float | None

class CostValidationResponse(BaseModel):
    model_cost_bps: float
    benchmark_range_bps: list[float]
    status: str
    source: str
```

Add to `MetricsResponse`:
```python
    gross_cagr: float = 0.0
    gross_sharpe: float = 0.0
    gross_max_drawdown: float = 0.0
    cost_drag_bps: float = 0.0
```

Add to `FullBacktestResponse`:
```python
    sensitivity: SensitivityResponse | None = None
    capacity: CapacityResponse | None = None
    cost_validation: CostValidationResponse | None = None
```

**Step 4: Update API service**

In `api/src/margin_api/services/backtest.py`:

Update `_build_metrics_response` to pass through gross fields:
```python
        gross_cagr=m.gross_cagr,
        gross_sharpe=m.gross_sharpe,
        gross_max_drawdown=m.gross_max_drawdown,
        cost_drag_bps=m.cost_drag_bps,
```

Update `build_full_response` to compute sensitivity and capacity:
```python
from margin_engine.backtesting.metrics import run_sensitivity_analysis
from margin_engine.backtesting.capacity import run_capacity_analysis
from margin_engine.backtesting.cost_model import validate_cost_assumptions

# Inside build_full_response, after existing code:
    # Sensitivity analysis
    sensitivity_data = run_sensitivity_analysis(result.snapshots)
    sensitivity = SensitivityResponse(
        rows=[CostSensitivityRow(**row) for row in sensitivity_data]
    )

    # Capacity analysis
    capacity_data = run_capacity_analysis(result.snapshots)
    capacity = CapacityResponse(
        rows=[CapacityRow(**row) for row in capacity_data["rows"]],
        breakeven_aum=capacity_data["breakeven_aum"],
    )

    # Cost validation (average cost across snapshots)
    avg_cost_bps = ...  # compute from snapshots
    validation = validate_cost_assumptions(avg_cost_bps, market_cap_billions=10.0)
    cost_validation = CostValidationResponse(
        model_cost_bps=validation["model_cost_bps"],
        benchmark_range_bps=list(validation["benchmark_range_bps"]),
        status=validation["status"],
        source=validation["source"],
    )
```

**Step 5: Update TypeScript types**

In `web/src/lib/api/types.ts`, add to `BacktestMetrics`:
```typescript
  gross_cagr?: number
  gross_sharpe?: number
  gross_max_drawdown?: number
  cost_drag_bps?: number
```

Add new interfaces:
```typescript
export interface CostSensitivityRow {
  multiplier: number
  cagr: number
  sharpe: number
  max_drawdown: number
  cost_drag_bps: number
}

export interface SensitivityResponse {
  rows: CostSensitivityRow[]
}

export interface CapacityRow {
  aum: number
  cagr: number
  sharpe: number
  avg_impact_bps: number
}

export interface CapacityResponse {
  rows: CapacityRow[]
  breakeven_aum: number | null
}

export interface CostValidationResponse {
  model_cost_bps: number
  benchmark_range_bps: number[]
  status: string
  source: string
}
```

Add to `FullBacktestResponse`:
```typescript
  sensitivity?: SensitivityResponse
  capacity?: CapacityResponse
  cost_validation?: CostValidationResponse
```

**Step 6: Run tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass.

**Step 7: Commit**

```bash
git add api/src/margin_api/schemas/backtest.py api/src/margin_api/services/backtest.py web/src/lib/api/types.ts
git commit -m "feat(api): wire sensitivity, capacity, and gross metrics into backtest response"
```

---

### Task 7: MetricsSummary Gross Annotations and Cost Drag Card

**Files:**
- Modify: `web/src/components/backtesting/metrics-summary.tsx`
- Test: `web/src/__tests__/components/backtesting/metrics-summary.test.tsx` (update existing)

**Step 1: Write the failing test**

```typescript
import { render, screen } from "@testing-library/react"
import { MetricsSummary } from "@/components/backtesting/metrics-summary"

describe("MetricsSummary gross annotations", () => {
  const metrics = {
    cagr: 0.104, excess_cagr: 0.031, sharpe_ratio: 0.85, sortino_ratio: 1.18,
    max_drawdown: 0.28, win_rate: 0.57, information_ratio: 0.62,
    total_return: 5.42, benchmark_total_return: 3.87, num_months: 240, avg_turnover: 0.18,
    gross_cagr: 0.115, gross_sharpe: 0.92, gross_max_drawdown: 0.26, cost_drag_bps: 110,
  }

  it("renders cost drag card", () => {
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.getByTestId("metric-cost-drag")).toBeInTheDocument()
    expect(screen.getByTestId("metric-cost-drag")).toHaveTextContent("110")
  })

  it("renders gross CAGR annotation", () => {
    render(<MetricsSummary metrics={metrics} />)
    expect(screen.getByTestId("metric-cagr")).toHaveTextContent("gross:")
  })
})
```

**Step 2: Run to verify failure**

Run: `cd web && npx vitest run src/__tests__/components/backtesting/metrics-summary.test.tsx`

**Step 3: Implement**

Update `MetricCard` to optionally show a gross annotation:

```tsx
interface MetricCardProps {
  label: string
  value: string
  colorClass: string
  testId: string
  grossValue?: string
}

function MetricCard({ label, value, colorClass, testId, grossValue }: MetricCardProps) {
  return (
    <div className="bg-bg-elevated border border-border-primary rounded-sm p-4" data-testid={testId}>
      <p className="text-xs text-text-secondary mb-1">{label}</p>
      <p className={`text-xl font-semibold ${colorClass}`}>{value}</p>
      {grossValue && (
        <p className="text-xs text-text-tertiary mt-0.5">(gross: {grossValue})</p>
      )}
    </div>
  )
}
```

In `MetricsSummary`, add gross annotations to CAGR, Sharpe, and Max Drawdown cards:

```tsx
      <MetricCard
        label="CAGR"
        value={formatPercent(metrics.cagr)}
        colorClass={valueColor(metrics.cagr)}
        testId="metric-cagr"
        grossValue={metrics.gross_cagr ? formatPercent(metrics.gross_cagr) : undefined}
      />
```

Add a cost drag card at the end:

```tsx
      {metrics.cost_drag_bps != null && metrics.cost_drag_bps > 0 && (
        <MetricCard
          label="Cost Drag"
          value={`${Math.round(metrics.cost_drag_bps)} bps/yr`}
          colorClass="text-warning"
          testId="metric-cost-drag"
        />
      )}
```

**Step 4: Run tests**

Run: `cd web && npx vitest run`
Expected: All pass.

**Step 5: Commit**

```bash
git add web/src/components/backtesting/metrics-summary.tsx web/src/__tests__/components/backtesting/metrics-summary.test.tsx
git commit -m "feat(web): add gross annotations and cost drag card to MetricsSummary"
```

---

### Task 8: CostSensitivity Component (Table + Chart)

**Files:**
- Create: `web/src/components/backtesting/cost-sensitivity.tsx`
- Test: `web/src/__tests__/components/backtesting/cost-sensitivity.test.tsx`

**Step 1: Write the failing test**

```typescript
import { render, screen } from "@testing-library/react"
import { CostSensitivity } from "@/components/backtesting/cost-sensitivity"

const rows = [
  { multiplier: 1.0, cagr: 0.104, sharpe: 0.85, max_drawdown: 0.28, cost_drag_bps: 47 },
  { multiplier: 2.0, cagr: 0.089, sharpe: 0.72, max_drawdown: 0.29, cost_drag_bps: 94 },
  { multiplier: 3.0, cagr: 0.074, sharpe: 0.59, max_drawdown: 0.30, cost_drag_bps: 141 },
]

describe("CostSensitivity", () => {
  it("renders the component", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByTestId("cost-sensitivity")).toBeInTheDocument()
  })

  it("renders all multiplier columns", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("Base (1x)")).toBeInTheDocument()
    expect(screen.getByText("Conservative (2x)")).toBeInTheDocument()
    expect(screen.getByText("Stress (3x)")).toBeInTheDocument()
  })

  it("renders CAGR row", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByText("CAGR")).toBeInTheDocument()
  })

  it("renders chart container", () => {
    render(<CostSensitivity rows={rows} />)
    expect(screen.getByTestId("sensitivity-chart")).toBeInTheDocument()
  })
})
```

**Step 2: Run to verify failure**

**Step 3: Implement**

Create `web/src/components/backtesting/cost-sensitivity.tsx`:

Build a component with:
- A Recharts `LineChart` showing CAGR and Sharpe across multipliers (testId: `sensitivity-chart`)
- A table below with rows: CAGR, Sharpe, Max DD, Cost Drag; columns: Base (1x), Conservative (2x), Stress (3x)
- Use existing design tokens (`terminal-card`, `text-text-secondary`, etc.)

**Step 4: Export from barrel file**

Update `web/src/components/backtesting/index.ts` to export `CostSensitivity`.

**Step 5: Run tests**

**Step 6: Commit**

```bash
git add web/src/components/backtesting/cost-sensitivity.tsx web/src/__tests__/components/backtesting/cost-sensitivity.test.tsx web/src/components/backtesting/index.ts
git commit -m "feat(web): add CostSensitivity component with chart and table"
```

---

### Task 9: CapacityChart Component

**Files:**
- Create: `web/src/components/backtesting/capacity-chart.tsx`
- Test: `web/src/__tests__/components/backtesting/capacity-chart.test.tsx`

**Step 1: Write the failing test**

```typescript
import { render, screen } from "@testing-library/react"
import { CapacityChart } from "@/components/backtesting/capacity-chart"

const data = {
  rows: [
    { aum: 1e6, cagr: 0.104, sharpe: 0.85, avg_impact_bps: 2 },
    { aum: 1e7, cagr: 0.100, sharpe: 0.80, avg_impact_bps: 8 },
    { aum: 1e8, cagr: 0.080, sharpe: 0.60, avg_impact_bps: 25 },
    { aum: 1e9, cagr: 0.040, sharpe: 0.30, avg_impact_bps: 80 },
  ],
  breakeven_aum: 500e6,
}

describe("CapacityChart", () => {
  it("renders the chart", () => {
    render(<CapacityChart rows={data.rows} breakevenAum={data.breakeven_aum} />)
    expect(screen.getByTestId("capacity-chart")).toBeInTheDocument()
  })

  it("shows breakeven annotation", () => {
    render(<CapacityChart rows={data.rows} breakevenAum={data.breakeven_aum} />)
    expect(screen.getByTestId("breakeven-callout")).toBeInTheDocument()
  })

  it("shows no breakeven when null", () => {
    render(<CapacityChart rows={data.rows} breakevenAum={null} />)
    expect(screen.queryByTestId("breakeven-callout")).not.toBeInTheDocument()
  })
})
```

**Step 2: Run to verify failure**

**Step 3: Implement**

Create `web/src/components/backtesting/capacity-chart.tsx`:

Build a component with:
- Recharts `LineChart` with log-scale x-axis (AUM), y-axis (Sharpe ratio)
- A `ReferenceLine` at Sharpe = 0.5 (dashed, labeled "Strategy breaks")
- A callout below the chart if `breakevenAum` is not null: "Strategy degrades below Sharpe 0.5 at $XXM AUM"
- Format AUM labels as "$1M", "$10M", "$100M", "$1B"

**Step 4: Export from barrel file**

**Step 5: Run tests**

**Step 6: Commit**

```bash
git add web/src/components/backtesting/capacity-chart.tsx web/src/__tests__/components/backtesting/capacity-chart.test.tsx web/src/components/backtesting/index.ts
git commit -m "feat(web): add CapacityChart component with breakeven annotation"
```

---

### Task 10: CostDisclosure Component

**Files:**
- Create: `web/src/components/backtesting/cost-disclosure.tsx`
- Test: `web/src/__tests__/components/backtesting/cost-disclosure.test.tsx`

**Step 1: Write the failing test**

```typescript
import { render, screen, fireEvent } from "@testing-library/react"
import { CostDisclosure } from "@/components/backtesting/cost-disclosure"

describe("CostDisclosure", () => {
  it("renders collapsed by default", () => {
    render(<CostDisclosure />)
    expect(screen.getByTestId("cost-disclosure")).toBeInTheDocument()
    expect(screen.queryByTestId("cost-disclosure-content")).not.toBeVisible()
  })

  it("expands on click", () => {
    render(<CostDisclosure />)
    fireEvent.click(screen.getByTestId("cost-disclosure-toggle"))
    expect(screen.getByTestId("cost-disclosure-content")).toBeVisible()
  })

  it("shows commission assumption", () => {
    render(<CostDisclosure />)
    fireEvent.click(screen.getByTestId("cost-disclosure-toggle"))
    expect(screen.getByText(/5 bps/)).toBeInTheDocument()
  })

  it("shows what is not modeled", () => {
    render(<CostDisclosure />)
    fireEvent.click(screen.getByTestId("cost-disclosure-toggle"))
    expect(screen.getByText(/not modeled/i)).toBeInTheDocument()
  })

  it("shows academic validation when provided", () => {
    render(
      <CostDisclosure
        costValidation={{ model_cost_bps: 12, benchmark_range_bps: [10, 20], status: "within_range", source: "Frazzini, Israel & Moskowitz (2015)" }}
      />
    )
    fireEvent.click(screen.getByTestId("cost-disclosure-toggle"))
    expect(screen.getByText(/Frazzini/)).toBeInTheDocument()
    expect(screen.getByText(/within/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run to verify failure**

**Step 3: Implement**

Create `web/src/components/backtesting/cost-disclosure.tsx`:

Collapsible panel (`<details>/<summary>` or state-controlled) with:
- Title: "Cost Model Assumptions"
- Commission: "5 bps round-trip (conservative; many brokers now offer zero-commission trades)"
- Spread: "Market-cap dependent: 3 + 50/sqrt(cap in $B). Mega-cap ~4 bps, mid-cap ~10 bps, small-cap ~18 bps"
- Market impact: "Square-root model: 0.1 × sqrt(trade_value / ADV) × 10,000"
- Not modeled: bullet list
- Academic validation: conditional section showing the citation and status

**Step 4: Export from barrel file**

**Step 5: Run tests**

**Step 6: Commit**

```bash
git add web/src/components/backtesting/cost-disclosure.tsx web/src/__tests__/components/backtesting/cost-disclosure.test.tsx web/src/components/backtesting/index.ts
git commit -m "feat(web): add CostDisclosure collapsible panel component"
```

---

### Task 11: Integrate All Components into Backtest Page

**Files:**
- Modify: `web/src/app/backtesting/page.tsx`
- Test: `web/src/__tests__/app/backtesting/page.test.tsx` (update existing)

**Step 1: Write the failing test**

Add to existing page tests:

```typescript
it("renders cost sensitivity section when data available", () => {
  // Mock replayData with sensitivity field
  render(<BacktestingPage />)
  // After load...
  expect(screen.getByTestId("cost-sensitivity")).toBeInTheDocument()
})

it("renders capacity chart when data available", () => {
  render(<BacktestingPage />)
  expect(screen.getByTestId("capacity-chart")).toBeInTheDocument()
})

it("renders cost disclosure", () => {
  render(<BacktestingPage />)
  expect(screen.getByTestId("cost-disclosure")).toBeInTheDocument()
})
```

**Step 2: Run to verify failure**

**Step 3: Implement**

In `web/src/app/backtesting/page.tsx`:

1. Import new components:
```typescript
import { CostSensitivity, CapacityChart, CostDisclosure } from "@/components/backtesting"
```

2. After the "Latest Performance Metrics" section (around line 353), add three new sections:

```tsx
            {/* Cost Sensitivity */}
            {replayData?.sensitivity && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Cost Sensitivity Analysis
                </h2>
                <CostSensitivity rows={replayData.sensitivity.rows} />
              </section>
            )}

            {/* Capacity Analysis */}
            {replayData?.capacity && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4">
                  Strategy Capacity
                </h2>
                <CapacityChart
                  rows={replayData.capacity.rows}
                  breakevenAum={replayData.capacity.breakeven_aum}
                />
              </section>
            )}

            {/* Cost Disclosure (before honesty footer) */}
            <CostDisclosure costValidation={replayData?.cost_validation ?? undefined} />
```

3. Update the honesty disclosure text to reference the non-linear model:
```tsx
            <p className="text-xs text-text-tertiary">
              {replayData?.honesty_disclosure ??
                "Backtest results include non-linear transaction cost estimates (commission + spread + market impact). See Cost Model Assumptions for details."}
            </p>
```

**Step 4: Run all web tests**

Run: `cd web && npx vitest run`
Expected: All pass.

**Step 5: Run all engine + API tests**

Run: `uv run pytest -v`
Expected: All pass.

**Step 6: Commit**

```bash
git add web/src/app/backtesting/page.tsx web/src/__tests__/app/backtesting/page.test.tsx
git commit -m "feat(web): integrate cost sensitivity, capacity chart, and cost disclosure into backtest page"
```

---

## Verification Checklist

After all tasks are complete, verify:

1. `uv run pytest engine/tests/backtesting/ -v` — all pass, including new test files
2. `uv run pytest api/tests/ -v` — all pass
3. `cd web && npx vitest run` — all pass
4. Manual: `FullBacktestResponse` JSON includes `sensitivity`, `capacity`, `cost_validation`, and `metrics.gross_cagr` / `metrics.cost_drag_bps`
5. Manual: Backtest page renders sensitivity table + chart, capacity curve, and cost disclosure panel
