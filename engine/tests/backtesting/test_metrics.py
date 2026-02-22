"""Golden-value tests for PerformanceCalculator.

Every expected value is hand-calculated so the tests are fully deterministic.
"""

from __future__ import annotations

from datetime import date

import pytest
from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import (
    HoldingRecord,
    MonthlySnapshot,
    PassThreshold,
    PerformanceMetrics,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot(
    month: int,
    portfolio_value: float,
    benchmark_value: float,
    portfolio_return: float,
    benchmark_return: float,
    turnover: float = 0.1,
    transaction_costs: float = 100.0,
) -> MonthlySnapshot:
    """Create a MonthlySnapshot with minimal boilerplate."""
    return MonthlySnapshot(
        date=date(2024, month, 28),
        holdings=[
            HoldingRecord(ticker="AAPL", weight=1.0, entry_price=100.0, composite_score=90.0),
        ],
        portfolio_value=portfolio_value,
        benchmark_value=benchmark_value,
        portfolio_return=portfolio_return,
        benchmark_return=benchmark_return,
        turnover=turnover,
        transaction_costs=transaction_costs,
    )


# ---------------------------------------------------------------------------
# CAGR
# ---------------------------------------------------------------------------


class TestCAGR:
    """Static _cagr helper — pure compound growth formula."""

    def test_24_month_50pct_growth(self):
        """1M -> 1.5M in 24 months => CAGR ~ 22.47%."""
        result = PerformanceCalculator._cagr(1.5, 2.0)
        assert result == pytest.approx(0.22474487139, rel=1e-6)

    def test_60_month_100pct_growth(self):
        """1M -> 2M in 60 months => CAGR ~ 14.87%."""
        result = PerformanceCalculator._cagr(2.0, 5.0)
        assert result == pytest.approx(0.14869835500, rel=1e-6)

    def test_zero_years_returns_zero(self):
        result = PerformanceCalculator._cagr(1.5, 0.0)
        assert result == 0.0

    def test_negative_years_returns_zero(self):
        result = PerformanceCalculator._cagr(1.5, -1.0)
        assert result == 0.0

    def test_zero_return_ratio_returns_zero(self):
        result = PerformanceCalculator._cagr(0.0, 2.0)
        assert result == 0.0

    def test_negative_return_ratio_returns_zero(self):
        result = PerformanceCalculator._cagr(-0.5, 2.0)
        assert result == 0.0

    def test_no_growth(self):
        """Ratio = 1.0 means no growth => CAGR = 0."""
        result = PerformanceCalculator._cagr(1.0, 3.0)
        assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Sharpe Ratio
# ---------------------------------------------------------------------------


class TestSharpe:
    """Static _sharpe helper — annualized Sharpe ratio."""

    def test_known_returns(self):
        """Hand-calculated Sharpe for known monthly returns.

        returns = [0.02, 0.03, -0.01, 0.04, 0.01, 0.02]
        risk_free_monthly = 0.04 / 12 = 0.003333...
        excess = [0.01667, 0.02667, -0.01333, 0.03667, 0.00667, 0.01667]
        mean(excess) = 0.015
        std(excess, ddof=1) = 0.01722401...
        sharpe = (0.015 / 0.01722401) * sqrt(12) = 3.01681...
        """
        returns = [0.02, 0.03, -0.01, 0.04, 0.01, 0.02]
        rfm = 0.04 / 12.0
        result = PerformanceCalculator._sharpe(returns, rfm)
        assert result == pytest.approx(3.01680685, rel=1e-5)

    def test_single_month_returns_zero(self):
        result = PerformanceCalculator._sharpe([0.05], 0.003333)
        assert result == 0.0

    def test_empty_returns_zero(self):
        result = PerformanceCalculator._sharpe([], 0.003333)
        assert result == 0.0

    def test_zero_std_returns_zero(self):
        """All identical returns => std = 0 => Sharpe = 0."""
        result = PerformanceCalculator._sharpe([0.01, 0.01, 0.01], 0.003333)
        assert result == 0.0

    def test_negative_excess_mean(self):
        """When risk-free dominates, Sharpe should be negative."""
        returns = [-0.02, -0.03, -0.01]
        rfm = 0.04 / 12.0
        result = PerformanceCalculator._sharpe(returns, rfm)
        assert result < 0.0


# ---------------------------------------------------------------------------
# Sortino Ratio
# ---------------------------------------------------------------------------


class TestSortino:
    """Static _sortino helper — downside-deviation-only Sharpe variant."""

    def test_known_returns(self):
        """Hand-calculated Sortino for known monthly returns.

        Same excess as Sharpe test, but only negative excess used for deviation.
        excess = [0.01667, 0.02667, -0.01333, 0.03667, 0.00667, 0.01667]
        downside_sq = [0, 0, 0.01333^2, 0, 0, 0] = [0, 0, 0.00017778, 0, 0, 0]
        downside_dev = sqrt(0.00017778 / 6) = sqrt(0.00002963) = 0.00544331
        sortino = (0.015 / 0.00544331) * sqrt(12) = 9.54594...
        """
        returns = [0.02, 0.03, -0.01, 0.04, 0.01, 0.02]
        rfm = 0.04 / 12.0
        result = PerformanceCalculator._sortino(returns, rfm)
        assert result == pytest.approx(9.54594155, rel=1e-5)

    def test_no_downside_returns_zero(self):
        """All excess returns positive => downside_dev = 0 => Sortino = 0."""
        returns = [0.10, 0.10, 0.10]
        rfm = 0.001
        result = PerformanceCalculator._sortino(returns, rfm)
        assert result == 0.0

    def test_single_month_returns_zero(self):
        result = PerformanceCalculator._sortino([0.05], 0.003333)
        assert result == 0.0

    def test_empty_returns_zero(self):
        result = PerformanceCalculator._sortino([], 0.003333)
        assert result == 0.0

    def test_all_negative_excess(self):
        """All excess returns are negative — Sortino should be negative."""
        returns = [-0.05, -0.04, -0.06]
        rfm = 0.04 / 12.0
        result = PerformanceCalculator._sortino(returns, rfm)
        assert result < 0.0


# ---------------------------------------------------------------------------
# Max Drawdown
# ---------------------------------------------------------------------------


class TestMaxDrawdown:
    """Static _max_drawdown helper."""

    def test_known_values(self):
        """Values [100, 110, 90, 95, 80, 100].

        Peak hits 110 at index 1. Lowest point is 80 at index 4.
        max_drawdown = (110 - 80) / 110 = 30/110 = 0.27272727...
        """
        values = [100, 110, 90, 95, 80, 100]
        result = PerformanceCalculator._max_drawdown(values)
        assert result == pytest.approx(0.27272727, rel=1e-6)

    def test_monotonically_increasing(self):
        """No drawdown in a series that only goes up."""
        values = [100, 110, 120, 130, 140]
        result = PerformanceCalculator._max_drawdown(values)
        assert result == pytest.approx(0.0)

    def test_monotonically_decreasing(self):
        """Entire series is a drawdown from the first value.

        peak=100, lowest=60 => max_drawdown = (100-60)/100 = 0.4
        """
        values = [100, 90, 80, 70, 60]
        result = PerformanceCalculator._max_drawdown(values)
        assert result == pytest.approx(0.4)

    def test_single_value_returns_zero(self):
        result = PerformanceCalculator._max_drawdown([100])
        assert result == 0.0

    def test_empty_returns_zero(self):
        result = PerformanceCalculator._max_drawdown([])
        assert result == 0.0

    def test_recovery_then_new_drawdown(self):
        """Two drawdown episodes; verify the larger one is captured.

        [100, 90, 100, 80] => first dd: (100-90)/100=0.10,
        recovery to 100, then (100-80)/100=0.20. max_dd = 0.20
        """
        values = [100, 90, 100, 80]
        result = PerformanceCalculator._max_drawdown(values)
        assert result == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# Win Rate (tested via calculate — no static helper)
# ---------------------------------------------------------------------------


class TestWinRate:
    """Win rate: fraction of months portfolio beats benchmark."""

    def test_known_win_rate(self):
        """Portfolio [0.05, -0.02, 0.03, 0.01] vs benchmark [0.02, 0.01, 0.04, -0.01].

        Excess: [+0.03, -0.03, -0.01, +0.02] => 2 wins / 4 = 0.5
        """
        snapshots = [
            _make_snapshot(1, 1_050_000, 1_020_000, 0.05, 0.02),
            _make_snapshot(2, 1_029_000, 1_030_200, -0.02, 0.01),
            _make_snapshot(3, 1_059_870, 1_071_408, 0.03, 0.04),
            _make_snapshot(4, 1_070_469, 1_060_694, 0.01, -0.01),
        ]
        calc = PerformanceCalculator()
        metrics = calc.calculate(snapshots)
        assert metrics.win_rate == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Information Ratio
# ---------------------------------------------------------------------------


class TestInformationRatio:
    """Static _information_ratio helper — annualized active-return / tracking error."""

    def test_known_active_returns(self):
        """Portfolio [0.05, -0.02, 0.03, 0.01] vs benchmark [0.02, 0.01, 0.04, -0.01].

        active = [0.03, -0.03, -0.01, 0.02]
        mean_active = 0.0025
        var(active, ddof=1) = sum((x-0.0025)^2)/3
          = ((0.0275)^2 + (-0.0325)^2 + (-0.0125)^2 + (0.0175)^2) / 3
          = (0.00075625 + 0.00105625 + 0.00015625 + 0.00030625) / 3
          = 0.002275 / 3 = 0.000758333...
        tracking_error = sqrt(0.000758333) * sqrt(12) = 0.027538... * 3.46410... = 0.095394
        ir = (0.0025 * 12) / 0.095394 = 0.03 / 0.095394 = 0.31449
        """
        pr = [0.05, -0.02, 0.03, 0.01]
        br = [0.02, 0.01, 0.04, -0.01]
        result = PerformanceCalculator._information_ratio(pr, br)
        assert result == pytest.approx(0.31448545, rel=1e-5)

    def test_single_month_returns_zero(self):
        result = PerformanceCalculator._information_ratio([0.05], [0.02])
        assert result == 0.0

    def test_empty_returns_zero(self):
        result = PerformanceCalculator._information_ratio([], [])
        assert result == 0.0

    def test_identical_returns_zero(self):
        """If portfolio perfectly tracks benchmark, tracking error = 0 => IR = 0."""
        pr = [0.01, 0.02, 0.03]
        br = [0.01, 0.02, 0.03]
        result = PerformanceCalculator._information_ratio(pr, br)
        assert result == 0.0


# ---------------------------------------------------------------------------
# Full calculate() Method
# ---------------------------------------------------------------------------


class TestCalculateFull:
    """End-to-end test of calculate() with 6 months of synthetic data."""

    @pytest.fixture()
    def snapshots(self) -> list[MonthlySnapshot]:
        """6 months of synthetic data.

        portfolio_returns = [0.03, 0.02, -0.01, 0.04, 0.01, 0.03]
        benchmark_returns = [0.02, 0.01, 0.00, 0.03, 0.02, 0.02]
        turnovers = [1.0, 0.15, 0.10, 0.20, 0.12, 0.18]
        """
        portfolio_returns = [0.03, 0.02, -0.01, 0.04, 0.01, 0.03]
        benchmark_returns = [0.02, 0.01, 0.00, 0.03, 0.02, 0.02]
        turnovers = [1.0, 0.15, 0.10, 0.20, 0.12, 0.18]

        # Build cumulative values from returns
        pv = 1_000_000.0
        bv = 1_000_000.0
        result = []
        for i, (pr, br, to) in enumerate(zip(portfolio_returns, benchmark_returns, turnovers)):
            pv *= 1.0 + pr
            bv *= 1.0 + br
            result.append(
                _make_snapshot(
                    month=i + 1,
                    portfolio_value=pv,
                    benchmark_value=bv,
                    portfolio_return=pr,
                    benchmark_return=br,
                    turnover=to,
                    transaction_costs=pv * to * 0.0015,
                )
            )
        return result

    def test_num_months(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.num_months == 6

    def test_total_return(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        # prod(1+r) - 1 for portfolio
        assert m.total_return == pytest.approx(0.12529018, rel=1e-5)

    def test_benchmark_total_return(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.benchmark_total_return == pytest.approx(0.10397468, rel=1e-5)

    def test_cagr(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.cagr == pytest.approx(0.26627799, rel=1e-5)

    def test_excess_cagr(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.excess_cagr == pytest.approx(0.04751789, rel=1e-4)

    def test_sharpe(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.sharpe_ratio == pytest.approx(3.22748612, rel=1e-4)

    def test_sortino(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.sortino_ratio == pytest.approx(10.60660172, rel=1e-4)

    def test_max_drawdown(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        # Only drawdown is the -1% month: peak at 1050600, drops to 1040094
        # dd = (1050600 - 1040094) / 1050600 = 10506/1050600 = 0.01
        assert m.max_drawdown == pytest.approx(0.01, rel=1e-4)

    def test_win_rate(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        # Portfolio beats benchmark in months: 0.03>0.02, 0.02>0.01, -0.01<0.00, 0.04>0.03
        # 0.01<0.02, 0.03>0.02 => 4 wins out of 6
        assert m.win_rate == pytest.approx(4.0 / 6.0, rel=1e-6)

    def test_information_ratio(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.information_ratio == pytest.approx(1.11803399, rel=1e-4)

    def test_avg_turnover(self, snapshots: list[MonthlySnapshot]):
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.avg_turnover == pytest.approx(0.29166667, rel=1e-5)


# ---------------------------------------------------------------------------
# validate() Method
# ---------------------------------------------------------------------------


class TestValidate:
    """Test validation of metrics against pass thresholds."""

    @pytest.fixture()
    def calculator(self) -> PerformanceCalculator:
        return PerformanceCalculator()

    @pytest.fixture()
    def strong_metrics(self) -> PerformanceMetrics:
        """Metrics that pass all default thresholds."""
        return PerformanceMetrics(
            cagr=0.15,
            excess_cagr=0.05,  # >= 0.03
            sharpe_ratio=0.9,  # >= 0.7
            sortino_ratio=1.3,  # >= 1.0
            max_drawdown=0.20,  # <= 0.35
            win_rate=0.62,  # >= 0.55
            information_ratio=0.7,  # >= 0.5
            total_return=2.0,
            benchmark_total_return=1.5,
            num_months=120,
            avg_turnover=0.15,
        )

    @pytest.fixture()
    def weak_metrics(self) -> PerformanceMetrics:
        """Metrics that fail all default thresholds."""
        return PerformanceMetrics(
            cagr=0.05,
            excess_cagr=0.01,  # < 0.03
            sharpe_ratio=0.4,  # < 0.7
            sortino_ratio=0.6,  # < 1.0
            max_drawdown=0.45,  # > 0.35
            win_rate=0.45,  # < 0.55
            information_ratio=0.3,  # < 0.5
            total_return=0.5,
            benchmark_total_return=0.4,
            num_months=120,
            avg_turnover=0.25,
        )

    def test_all_pass(self, calculator: PerformanceCalculator, strong_metrics: PerformanceMetrics):
        result = calculator.validate(strong_metrics)
        assert result.overall_pass is True
        assert result.passed_count == 6
        assert result.excess_cagr_pass is True
        assert result.sharpe_pass is True
        assert result.sortino_pass is True
        assert result.drawdown_pass is True
        assert result.win_rate_pass is True
        assert result.information_ratio_pass is True

    def test_all_fail(self, calculator: PerformanceCalculator, weak_metrics: PerformanceMetrics):
        result = calculator.validate(weak_metrics)
        assert result.overall_pass is False
        assert result.passed_count == 0
        assert result.excess_cagr_pass is False
        assert result.sharpe_pass is False
        assert result.sortino_pass is False
        assert result.drawdown_pass is False
        assert result.win_rate_pass is False
        assert result.information_ratio_pass is False

    def test_mixed_pass_fail(self, calculator: PerformanceCalculator):
        """3 out of 6 pass."""
        metrics = PerformanceMetrics(
            cagr=0.10,
            excess_cagr=0.04,  # >= 0.03 PASS
            sharpe_ratio=0.5,  # < 0.7 FAIL
            sortino_ratio=1.2,  # >= 1.0 PASS
            max_drawdown=0.40,  # > 0.35 FAIL
            win_rate=0.60,  # >= 0.55 PASS
            information_ratio=0.3,  # < 0.5 FAIL
            total_return=1.0,
            benchmark_total_return=0.7,
            num_months=60,
            avg_turnover=0.20,
        )
        result = calculator.validate(metrics)
        assert result.overall_pass is False
        assert result.passed_count == 3
        assert result.excess_cagr_pass is True
        assert result.sharpe_pass is False
        assert result.sortino_pass is True
        assert result.drawdown_pass is False
        assert result.win_rate_pass is True
        assert result.information_ratio_pass is False

    def test_boundary_values_pass(self, calculator: PerformanceCalculator):
        """Exactly at threshold values should pass (>= for mins, <= for max_drawdown)."""
        metrics = PerformanceMetrics(
            cagr=0.10,
            excess_cagr=0.03,  # == min_excess_cagr
            sharpe_ratio=0.7,  # == min_sharpe
            sortino_ratio=1.0,  # == min_sortino
            max_drawdown=0.35,  # == max_drawdown
            win_rate=0.55,  # == min_win_rate
            information_ratio=0.5,  # == min_information_ratio
            total_return=1.0,
            benchmark_total_return=0.7,
            num_months=60,
            avg_turnover=0.15,
        )
        result = calculator.validate(metrics)
        assert result.overall_pass is True
        assert result.passed_count == 6

    def test_custom_thresholds(self, calculator: PerformanceCalculator):
        """Use stricter thresholds that the strong metrics now fail."""
        metrics = PerformanceMetrics(
            cagr=0.15,
            excess_cagr=0.05,
            sharpe_ratio=0.9,
            sortino_ratio=1.3,
            max_drawdown=0.20,
            win_rate=0.62,
            information_ratio=0.7,
            total_return=2.0,
            benchmark_total_return=1.5,
            num_months=120,
            avg_turnover=0.15,
        )
        strict = PassThreshold(
            min_excess_cagr=0.06,  # 0.05 < 0.06 FAIL
            min_sharpe=1.0,  # 0.9 < 1.0 FAIL
            min_sortino=1.5,  # 1.3 < 1.5 FAIL
            max_drawdown=0.15,  # 0.20 > 0.15 FAIL
            min_win_rate=0.65,  # 0.62 < 0.65 FAIL
            min_information_ratio=0.8,  # 0.7 < 0.8 FAIL
        )
        result = calculator.validate(metrics, thresholds=strict)
        assert result.overall_pass is False
        assert result.passed_count == 0

    def test_default_thresholds_used_when_none(
        self, calculator: PerformanceCalculator, strong_metrics: PerformanceMetrics
    ):
        result = calculator.validate(strong_metrics, thresholds=None)
        assert result.thresholds == PassThreshold()

    def test_validation_stores_metrics_and_thresholds(
        self, calculator: PerformanceCalculator, strong_metrics: PerformanceMetrics
    ):
        thresholds = PassThreshold(min_excess_cagr=0.01)
        result = calculator.validate(strong_metrics, thresholds=thresholds)
        assert result.metrics is strong_metrics
        assert result.thresholds is thresholds


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: empty data, single month, custom risk-free rate."""

    def test_empty_snapshots(self):
        calc = PerformanceCalculator()
        m = calc.calculate([])
        assert m.num_months == 0
        assert m.cagr == 0.0
        assert m.excess_cagr == 0.0
        assert m.sharpe_ratio == 0.0
        assert m.sortino_ratio == 0.0
        assert m.max_drawdown == 0.0
        assert m.win_rate == 0.0
        assert m.information_ratio == 0.0
        assert m.total_return == 0.0
        assert m.benchmark_total_return == 0.0
        assert m.avg_turnover == 0.0

    def test_single_snapshot(self):
        """One month of data => ratios that need >= 2 months return 0.0."""
        snap = _make_snapshot(1, 1_020_000, 1_010_000, 0.02, 0.01)
        calc = PerformanceCalculator()
        m = calc.calculate([snap])
        assert m.num_months == 1
        # CAGR still computes (1 month = 1/12 year)
        assert m.cagr > 0.0
        # But Sharpe/Sortino/IR need >= 2 months
        assert m.sharpe_ratio == 0.0
        assert m.sortino_ratio == 0.0
        assert m.information_ratio == 0.0
        # Max drawdown with single value is 0
        assert m.max_drawdown == 0.0

    def test_zero_variance_returns(self):
        """All identical returns => Sharpe = 0.0 (zero std dev)."""
        snapshots = [
            _make_snapshot(i, 1_000_000 * 1.01**i, 1_000_000 * 1.01**i, 0.01, 0.01)
            for i in range(1, 7)
        ]
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.sharpe_ratio == 0.0
        assert m.information_ratio == 0.0

    def test_custom_risk_free_rate(self):
        """Different risk-free rate changes Sharpe/Sortino calculations."""
        snapshots = [
            _make_snapshot(1, 1_030_000, 1_020_000, 0.03, 0.02),
            _make_snapshot(2, 1_050_600, 1_030_200, 0.02, 0.01),
            _make_snapshot(3, 1_040_094, 1_030_200, -0.01, 0.00),
        ]
        calc_low = PerformanceCalculator(risk_free_rate=0.02)
        calc_high = PerformanceCalculator(risk_free_rate=0.08)
        m_low = calc_low.calculate(snapshots)
        m_high = calc_high.calculate(snapshots)
        # Higher risk-free rate penalizes excess returns more => lower Sharpe
        assert m_low.sharpe_ratio > m_high.sharpe_ratio

    def test_all_positive_excess_sortino_equals_zero_when_no_downside(self):
        """When all excess returns are positive, downside deviation = 0 => Sortino = 0."""
        # Very high returns so all excess returns are positive
        snapshots = [
            _make_snapshot(1, 1_100_000, 1_000_000, 0.10, 0.00),
            _make_snapshot(2, 1_210_000, 1_000_000, 0.10, 0.00),
            _make_snapshot(3, 1_331_000, 1_000_000, 0.10, 0.00),
        ]
        calc = PerformanceCalculator()
        m = calc.calculate(snapshots)
        assert m.sortino_ratio == 0.0

    def test_risk_free_rate_stored(self):
        calc = PerformanceCalculator(risk_free_rate=0.05)
        assert calc._risk_free_rate == 0.05

    def test_default_risk_free_rate(self):
        calc = PerformanceCalculator()
        assert calc._risk_free_rate == 0.04
