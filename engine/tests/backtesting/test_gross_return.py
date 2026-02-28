"""Tests for gross_return tracking in MonthlySnapshot."""

from datetime import date

from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot


class TestMonthlySnapshotGrossReturn:
    def test_gross_return_field_exists(self):
        snap = MonthlySnapshot(
            date=date(2024, 1, 28),
            holdings=[
                HoldingRecord(
                    ticker="AAPL", weight=1.0, entry_price=100.0, composite_score=90.0
                )
            ],
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
        snap = MonthlySnapshot(
            date=date(2024, 1, 28),
            holdings=[
                HoldingRecord(
                    ticker="AAPL", weight=1.0, entry_price=100.0, composite_score=90.0
                )
            ],
            portfolio_value=1_000_000,
            benchmark_value=1_000_000,
            portfolio_return=0.02,
            benchmark_return=0.01,
            turnover=0.1,
            transaction_costs=100.0,
        )
        assert snap.gross_return == 0.02

    def test_gross_return_greater_than_or_equal_net(self):
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
