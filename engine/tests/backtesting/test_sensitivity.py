"""Tests for cost sensitivity analysis."""

from datetime import date

import pytest
from margin_engine.backtesting.metrics import run_sensitivity_analysis, PerformanceCalculator
from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot


def _snap(month, pv, bv, pr, br, tc, gr):
    return MonthlySnapshot(
        date=date(2024, month, 28),
        holdings=[HoldingRecord(ticker="AAPL", weight=1.0, entry_price=100.0, composite_score=90.0)],
        portfolio_value=pv, benchmark_value=bv,
        portfolio_return=pr, benchmark_return=br,
        turnover=0.1, transaction_costs=tc, gross_return=gr,
    )


class TestRunSensitivityAnalysis:
    @pytest.fixture()
    def snapshots(self):
        # Self-consistent data: portfolio_return = gross_return - tc / start_pv
        # start_pv(month1) = 1_000_000
        # month1: gross_pv = 1_030_000, net_pv = 1_029_800, net_ret = 0.0298
        # month2: gross_pv = 1_060_694, net_pv = 1_060_394, net_ret ~ 0.029709
        # month3: gross_pv = 1_049_790.06, net_pv = 1_049_690.06, net_ret ~ -0.010094
        return [
            _snap(1, 1_029_800, 1_020_000, 0.0298, 0.02, 200.0, 0.03),
            _snap(2, 1_060_394, 1_040_000, 0.029709, 0.02, 300.0, 0.03),
            _snap(3, 1_049_690, 1_040_000, -0.010094, 0.00, 100.0, -0.01),
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
        assert result[1]["cost_drag_bps"] > result[0]["cost_drag_bps"]

    def test_base_row_matches_actual_metrics(self, snapshots):
        calc = PerformanceCalculator()
        actual = calc.calculate(snapshots)
        result = run_sensitivity_analysis(snapshots)
        assert result[0]["cagr"] == pytest.approx(actual.cagr, rel=1e-4)

    def test_custom_multipliers(self, snapshots):
        result = run_sensitivity_analysis(snapshots, multipliers=[1.0, 1.5, 2.0, 5.0])
        assert len(result) == 4
        assert result[3]["multiplier"] == 5.0

    def test_empty_snapshots(self):
        result = run_sensitivity_analysis([])
        assert len(result) == 3
        assert all(r["cagr"] == 0.0 for r in result)
