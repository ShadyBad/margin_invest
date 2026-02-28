"""Tests for capacity analysis."""

from datetime import date

import pytest
from margin_engine.backtesting.capacity import run_capacity_analysis
from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot


def _snap(month, pv, bv, pr, br, tc, gr, turnover=0.2):
    return MonthlySnapshot(
        date=date(2024, month, 28),
        holdings=[
            HoldingRecord(ticker="AAPL", weight=0.5, entry_price=150.0, composite_score=85.0),
            HoldingRecord(ticker="MSFT", weight=0.5, entry_price=300.0, composite_score=80.0),
        ],
        portfolio_value=pv,
        benchmark_value=bv,
        portfolio_return=pr,
        benchmark_return=br,
        turnover=turnover,
        transaction_costs=tc,
        gross_return=gr,
    )


class TestRunCapacityAnalysis:
    @pytest.fixture()
    def snapshots(self):
        return [
            _snap(1, 1_030_000, 1_020_000, 0.028, 0.02, 200.0, 0.03),
            _snap(2, 1_060_000, 1_040_000, 0.027, 0.02, 300.0, 0.03),
            _snap(3, 1_090_000, 1_060_000, 0.027, 0.02, 250.0, 0.03),
            _snap(4, 1_080_000, 1_060_000, -0.010, 0.00, 100.0, -0.01),
        ]

    def test_returns_rows_for_each_aum(self, snapshots):
        result = run_capacity_analysis(snapshots)
        assert len(result["rows"]) == 7

    def test_aum_levels_ascending(self, snapshots):
        result = run_capacity_analysis(snapshots)
        aums = [r["aum"] for r in result["rows"]]
        assert aums == sorted(aums)

    def test_sharpe_decreases_with_aum(self, snapshots):
        result = run_capacity_analysis(snapshots)
        sharpes = [r["sharpe"] for r in result["rows"]]
        assert sharpes[0] >= sharpes[-1]

    def test_impact_increases_with_aum(self, snapshots):
        result = run_capacity_analysis(snapshots)
        impacts = [r["avg_impact_bps"] for r in result["rows"]]
        assert impacts[-1] > impacts[0]

    def test_breakeven_aum_returned(self, snapshots):
        result = run_capacity_analysis(snapshots)
        assert "breakeven_aum" in result
        if result["breakeven_aum"] is not None:
            assert result["breakeven_aum"] > 0

    def test_custom_aum_levels(self, snapshots):
        result = run_capacity_analysis(snapshots, aum_levels=[1e6, 1e9])
        assert len(result["rows"]) == 2

    def test_empty_snapshots(self):
        result = run_capacity_analysis([])
        assert len(result["rows"]) == 7
        assert all(r["cagr"] == 0.0 for r in result["rows"])
        assert result["breakeven_aum"] is None
