"""Tests for the ValidationGate — threshold checks and methodology comparison.

All metrics are hand-chosen so expected outcomes are deterministic and obvious.
"""

from __future__ import annotations

from datetime import date

from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    HoldingRecord,
    MonthlySnapshot,
    PassThreshold,
    PerformanceMetrics,
)
from margin_engine.backtesting.validation import ValidationGate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_metrics(
    *,
    excess_cagr: float = 0.05,
    sharpe_ratio: float = 0.9,
    sortino_ratio: float = 1.3,
    max_drawdown: float = 0.20,
    win_rate: float = 0.62,
    information_ratio: float = 0.7,
    cagr: float = 0.15,
    total_return: float = 2.0,
    benchmark_total_return: float = 1.5,
    num_months: int = 120,
    avg_turnover: float = 0.15,
) -> PerformanceMetrics:
    """Create PerformanceMetrics with sensible defaults that pass all thresholds."""
    return PerformanceMetrics(
        cagr=cagr,
        excess_cagr=excess_cagr,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        information_ratio=information_ratio,
        total_return=total_return,
        benchmark_total_return=benchmark_total_return,
        num_months=num_months,
        avg_turnover=avg_turnover,
    )


def _make_backtest_result(metrics: PerformanceMetrics) -> BacktestResult:
    """Create a minimal BacktestResult wrapping the given metrics."""
    return BacktestResult(
        config=BacktestConfig(start_date=date(2020, 1, 1), end_date=date(2024, 12, 31)),
        snapshots=[
            MonthlySnapshot(
                date=date(2024, 1, 28),
                holdings=[
                    HoldingRecord(
                        ticker="AAPL", weight=1.0, entry_price=100.0, composite_score=90.0
                    ),
                ],
                portfolio_value=1_000_000,
                benchmark_value=1_000_000,
                portfolio_return=0.01,
                benchmark_return=0.01,
                turnover=0.1,
                transaction_costs=100.0,
            ),
        ],
        metrics=metrics,
        duration_seconds=1.5,
    )


# ---------------------------------------------------------------------------
# Test 1: validate() delegates to calculator
# ---------------------------------------------------------------------------


class TestValidateDelegation:
    """validate() should delegate to PerformanceCalculator.validate()."""

    def test_validate_returns_validation_result(self):
        metrics = _make_metrics()
        gate = ValidationGate()
        result = gate.validate(metrics)
        assert result.metrics is metrics
        assert result.thresholds == PassThreshold()

    def test_validate_uses_stored_thresholds(self):
        """Gate passes its own thresholds to the calculator."""
        custom = PassThreshold(min_excess_cagr=0.10)
        gate = ValidationGate(thresholds=custom)
        metrics = _make_metrics(excess_cagr=0.05)  # below 0.10
        result = gate.validate(metrics)
        assert result.excess_cagr_pass is False
        assert result.thresholds is custom


# ---------------------------------------------------------------------------
# Test 2: validate_result() attaches validation to BacktestResult
# ---------------------------------------------------------------------------


class TestValidateResult:
    """validate_result() should return a new BacktestResult with validation attached."""

    def test_attaches_validation(self):
        metrics = _make_metrics()
        bt_result = _make_backtest_result(metrics)
        assert bt_result.validation is None

        gate = ValidationGate()
        validated = gate.validate_result(bt_result)

        assert validated.validation is not None
        assert validated.validation.overall_pass is True
        assert validated.metrics is metrics

    def test_does_not_mutate_original(self):
        metrics = _make_metrics()
        bt_result = _make_backtest_result(metrics)
        gate = ValidationGate()
        validated = gate.validate_result(bt_result)

        # Original unchanged
        assert bt_result.validation is None
        # Validated has it
        assert validated.validation is not None


# ---------------------------------------------------------------------------
# Test 3: All thresholds pass
# ---------------------------------------------------------------------------


class TestAllThresholdsPass:
    def test_all_pass(self):
        metrics = _make_metrics(
            excess_cagr=0.05,  # >= 0.03
            sharpe_ratio=0.9,  # >= 0.7
            sortino_ratio=1.3,  # >= 1.0
            max_drawdown=0.20,  # <= 0.35
            win_rate=0.62,  # >= 0.55
            information_ratio=0.7,  # >= 0.5
        )
        gate = ValidationGate()
        result = gate.validate(metrics)
        assert result.overall_pass is True
        assert result.passed_count == 6
        assert result.excess_cagr_pass is True
        assert result.sharpe_pass is True
        assert result.sortino_pass is True
        assert result.drawdown_pass is True
        assert result.win_rate_pass is True
        assert result.information_ratio_pass is True


# ---------------------------------------------------------------------------
# Test 4: All thresholds fail
# ---------------------------------------------------------------------------


class TestAllThresholdsFail:
    def test_all_fail(self):
        metrics = _make_metrics(
            excess_cagr=0.01,  # < 0.03
            sharpe_ratio=0.4,  # < 0.7
            sortino_ratio=0.6,  # < 1.0
            max_drawdown=0.45,  # > 0.35
            win_rate=0.45,  # < 0.55
            information_ratio=0.3,  # < 0.5
        )
        gate = ValidationGate()
        result = gate.validate(metrics)
        assert result.overall_pass is False
        assert result.passed_count == 0
        assert result.excess_cagr_pass is False
        assert result.sharpe_pass is False
        assert result.sortino_pass is False
        assert result.drawdown_pass is False
        assert result.win_rate_pass is False
        assert result.information_ratio_pass is False


# ---------------------------------------------------------------------------
# Test 5: Mixed pass/fail
# ---------------------------------------------------------------------------


class TestMixedPassFail:
    def test_three_pass_three_fail(self):
        metrics = _make_metrics(
            excess_cagr=0.04,  # >= 0.03 PASS
            sharpe_ratio=0.5,  # < 0.7 FAIL
            sortino_ratio=1.2,  # >= 1.0 PASS
            max_drawdown=0.40,  # > 0.35 FAIL
            win_rate=0.60,  # >= 0.55 PASS
            information_ratio=0.3,  # < 0.5 FAIL
        )
        gate = ValidationGate()
        result = gate.validate(metrics)
        assert result.overall_pass is False
        assert result.passed_count == 3
        assert result.excess_cagr_pass is True
        assert result.sortino_pass is True
        assert result.win_rate_pass is True
        assert result.sharpe_pass is False
        assert result.drawdown_pass is False
        assert result.information_ratio_pass is False


# ---------------------------------------------------------------------------
# Test 6: Boundary values
# ---------------------------------------------------------------------------


class TestBoundaryValues:
    def test_exactly_at_thresholds_pass(self):
        """Exactly at threshold values should pass (>= for mins, <= for max_drawdown)."""
        metrics = _make_metrics(
            excess_cagr=0.03,  # == min_excess_cagr
            sharpe_ratio=0.7,  # == min_sharpe
            sortino_ratio=1.0,  # == min_sortino
            max_drawdown=0.35,  # == max_drawdown
            win_rate=0.55,  # == min_win_rate
            information_ratio=0.5,  # == min_information_ratio
        )
        gate = ValidationGate()
        result = gate.validate(metrics)
        assert result.overall_pass is True
        assert result.passed_count == 6

    def test_just_below_thresholds_fail(self):
        """Just below each threshold should fail."""
        metrics = _make_metrics(
            excess_cagr=0.0299,
            sharpe_ratio=0.699,
            sortino_ratio=0.999,
            max_drawdown=0.3501,
            win_rate=0.549,
            information_ratio=0.499,
        )
        gate = ValidationGate()
        result = gate.validate(metrics)
        assert result.overall_pass is False
        assert result.passed_count == 0


# ---------------------------------------------------------------------------
# Test 7: compare_methodologies — new wins all 5
# ---------------------------------------------------------------------------


class TestCompareNewWinsAll:
    def test_new_wins_all_five(self):
        old = _make_metrics(
            excess_cagr=0.03,
            sharpe_ratio=0.7,
            sortino_ratio=1.0,
            max_drawdown=0.30,
            win_rate=0.55,
        )
        new = _make_metrics(
            excess_cagr=0.06,
            sharpe_ratio=1.0,
            sortino_ratio=1.5,
            max_drawdown=0.15,
            win_rate=0.65,
        )
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old, new)

        assert comparison.new_is_better is True
        assert len(comparison.new_wins) == 5
        assert len(comparison.old_wins) == 0
        assert len(comparison.ties) == 0
        assert set(comparison.metrics_compared) == {
            "excess_cagr",
            "sharpe_ratio",
            "sortino_ratio",
            "max_drawdown",
            "win_rate",
        }


# ---------------------------------------------------------------------------
# Test 8: compare_methodologies — new wins 3 of 5 (minimum)
# ---------------------------------------------------------------------------


class TestCompareNewWinsThree:
    def test_new_wins_exactly_three(self):
        """Minimum to pass: new wins 3, old wins 2."""
        old = _make_metrics(
            excess_cagr=0.03,
            sharpe_ratio=0.7,
            sortino_ratio=1.0,
            max_drawdown=0.20,
            win_rate=0.60,
        )
        new = _make_metrics(
            excess_cagr=0.05,
            sharpe_ratio=0.9,
            sortino_ratio=1.2,
            max_drawdown=0.25,
            win_rate=0.55,  # old wins drawdown and win_rate
        )
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old, new)

        assert comparison.new_is_better is True
        assert len(comparison.new_wins) == 3
        assert len(comparison.old_wins) == 2
        assert "excess_cagr" in comparison.new_wins
        assert "sharpe_ratio" in comparison.new_wins
        assert "sortino_ratio" in comparison.new_wins
        assert "max_drawdown" in comparison.old_wins  # 0.25 > 0.20 => old is better
        assert "win_rate" in comparison.old_wins  # 0.55 < 0.60 => old is better


# ---------------------------------------------------------------------------
# Test 9: compare_methodologies — new wins 2 of 5 (not enough)
# ---------------------------------------------------------------------------


class TestCompareNewWinsTwo:
    def test_new_wins_only_two(self):
        """Below minimum: new wins 2, old wins 3 => new_is_better = False."""
        old = _make_metrics(
            excess_cagr=0.03,
            sharpe_ratio=0.8,
            sortino_ratio=1.2,
            max_drawdown=0.20,
            win_rate=0.60,
        )
        new = _make_metrics(
            excess_cagr=0.05,
            sharpe_ratio=0.7,
            sortino_ratio=1.0,
            max_drawdown=0.25,
            win_rate=0.65,  # new wins: excess_cagr, win_rate
        )
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old, new)

        assert comparison.new_is_better is False
        assert len(comparison.new_wins) == 2
        assert len(comparison.old_wins) == 3
        assert "excess_cagr" in comparison.new_wins
        assert "win_rate" in comparison.new_wins


# ---------------------------------------------------------------------------
# Test 10: compare_methodologies — old wins all 5
# ---------------------------------------------------------------------------


class TestCompareOldWinsAll:
    def test_old_wins_all_five(self):
        old = _make_metrics(
            excess_cagr=0.06,
            sharpe_ratio=1.0,
            sortino_ratio=1.5,
            max_drawdown=0.15,
            win_rate=0.65,
        )
        new = _make_metrics(
            excess_cagr=0.03,
            sharpe_ratio=0.7,
            sortino_ratio=1.0,
            max_drawdown=0.30,
            win_rate=0.55,
        )
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old, new)

        assert comparison.new_is_better is False
        assert len(comparison.new_wins) == 0
        assert len(comparison.old_wins) == 5
        assert len(comparison.ties) == 0


# ---------------------------------------------------------------------------
# Test 11: compare_methodologies — ties counted
# ---------------------------------------------------------------------------


class TestCompareTies:
    def test_ties_do_not_count_as_wins(self):
        """Ties don't count as wins for either side.

        If all 5 are tied, new_wins = 0 => new_is_better = False.
        """
        metrics = _make_metrics(
            excess_cagr=0.04,
            sharpe_ratio=0.8,
            sortino_ratio=1.1,
            max_drawdown=0.25,
            win_rate=0.58,
        )
        gate = ValidationGate()
        comparison = gate.compare_methodologies(metrics, metrics)

        assert comparison.new_is_better is False
        assert len(comparison.new_wins) == 0
        assert len(comparison.old_wins) == 0
        assert len(comparison.ties) == 5

    def test_two_wins_three_ties_not_enough(self):
        """2 wins + 3 ties => new_is_better = False (need >= 3 wins)."""
        old = _make_metrics(
            excess_cagr=0.04,
            sharpe_ratio=0.8,
            sortino_ratio=1.1,
            max_drawdown=0.25,
            win_rate=0.58,
        )
        new = _make_metrics(
            excess_cagr=0.05,
            sharpe_ratio=0.8,
            sortino_ratio=1.1,
            max_drawdown=0.25,
            win_rate=0.60,
        )
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old, new)

        assert comparison.new_is_better is False
        assert len(comparison.new_wins) == 2
        assert len(comparison.ties) == 3
        assert len(comparison.old_wins) == 0

    def test_three_wins_two_ties_enough(self):
        """3 wins + 2 ties => new_is_better = True."""
        old = _make_metrics(
            excess_cagr=0.04,
            sharpe_ratio=0.8,
            sortino_ratio=1.1,
            max_drawdown=0.25,
            win_rate=0.58,
        )
        new = _make_metrics(
            excess_cagr=0.05,
            sharpe_ratio=0.9,
            sortino_ratio=1.1,
            max_drawdown=0.25,
            win_rate=0.60,
        )
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old, new)

        assert comparison.new_is_better is True
        assert len(comparison.new_wins) == 3
        assert len(comparison.ties) == 2
        assert len(comparison.old_wins) == 0


# ---------------------------------------------------------------------------
# Test 12: compare_methodologies — max_drawdown comparison inverted
# ---------------------------------------------------------------------------


class TestCompareMaxDrawdownInverted:
    def test_lower_drawdown_is_new_win(self):
        """Lower max_drawdown means better => new wins on drawdown."""
        old = _make_metrics(max_drawdown=0.30)
        new = _make_metrics(max_drawdown=0.15)
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old, new)
        assert "max_drawdown" in comparison.new_wins

    def test_higher_drawdown_is_old_win(self):
        """Higher max_drawdown means worse => old wins on drawdown."""
        old = _make_metrics(max_drawdown=0.15)
        new = _make_metrics(max_drawdown=0.30)
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old, new)
        assert "max_drawdown" in comparison.old_wins

    def test_equal_drawdown_is_tie(self):
        old = _make_metrics(max_drawdown=0.25)
        new = _make_metrics(max_drawdown=0.25)
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old, new)
        assert "max_drawdown" in comparison.ties


# ---------------------------------------------------------------------------
# Test 13: Custom thresholds
# ---------------------------------------------------------------------------


class TestCustomThresholds:
    def test_stricter_thresholds_cause_failure(self):
        """Metrics that pass default thresholds fail stricter custom ones."""
        metrics = _make_metrics(
            excess_cagr=0.05,
            sharpe_ratio=0.9,
            sortino_ratio=1.3,
            max_drawdown=0.20,
            win_rate=0.62,
            information_ratio=0.7,
        )
        strict = PassThreshold(
            min_excess_cagr=0.06,  # 0.05 < 0.06 FAIL
            min_sharpe=1.0,  # 0.9 < 1.0 FAIL
            min_sortino=1.5,  # 1.3 < 1.5 FAIL
            max_drawdown=0.15,  # 0.20 > 0.15 FAIL
            min_win_rate=0.65,  # 0.62 < 0.65 FAIL
            min_information_ratio=0.8,  # 0.7 < 0.8 FAIL
        )
        gate = ValidationGate(thresholds=strict)
        result = gate.validate(metrics)
        assert result.overall_pass is False
        assert result.passed_count == 0

    def test_looser_thresholds_cause_pass(self):
        """Metrics that fail default thresholds pass looser custom ones."""
        metrics = _make_metrics(
            excess_cagr=0.01,
            sharpe_ratio=0.4,
            sortino_ratio=0.6,
            max_drawdown=0.45,
            win_rate=0.45,
            information_ratio=0.3,
        )
        loose = PassThreshold(
            min_excess_cagr=0.005,
            min_sharpe=0.3,
            min_sortino=0.5,
            max_drawdown=0.50,
            min_win_rate=0.40,
            min_information_ratio=0.2,
        )
        gate = ValidationGate(thresholds=loose)
        result = gate.validate(metrics)
        assert result.overall_pass is True
        assert result.passed_count == 6

    def test_gate_stores_custom_thresholds(self):
        """Custom thresholds appear in the ValidationResult."""
        custom = PassThreshold(min_excess_cagr=0.10)
        gate = ValidationGate(thresholds=custom)
        metrics = _make_metrics()
        result = gate.validate(metrics)
        assert result.thresholds.min_excess_cagr == 0.10

    def test_gate_with_custom_calculator(self):
        """Gate can be constructed with a custom PerformanceCalculator."""
        calc = PerformanceCalculator(risk_free_rate=0.02)
        gate = ValidationGate(calculator=calc)
        # Verify the gate uses the injected calculator
        assert gate._calculator is calc
