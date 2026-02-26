"""Tests for shadow portfolio tracker."""

from datetime import date

import pytest
from margin_engine.backtesting.shadow_portfolio import (
    ShadowPortfolio,
    ShadowPosition,
)


class TestShadowPortfolio:
    def test_record_snapshot(self):
        portfolio = ShadowPortfolio(start_date=date(2026, 2, 24))
        positions = [
            ShadowPosition(ticker="AAPL", weight=0.5, price=175.0, composite_score=82.0),
            ShadowPosition(ticker="MSFT", weight=0.5, price=410.0, composite_score=78.0),
        ]
        portfolio.record_snapshot(date(2026, 2, 24), positions, portfolio_value=1_000_000.0)
        assert len(portfolio.snapshots) == 1
        assert portfolio.snapshots[0].num_positions == 2

    def test_cannot_backfill(self):
        portfolio = ShadowPortfolio(start_date=date(2026, 2, 24))
        positions = [ShadowPosition(ticker="AAPL", weight=1.0, price=175.0, composite_score=82.0)]
        portfolio.record_snapshot(date(2026, 2, 25), positions, portfolio_value=1_000_000.0)

        with pytest.raises(ValueError, match="Cannot backfill"):
            portfolio.record_snapshot(date(2026, 2, 24), positions, portfolio_value=999_000.0)

    def test_performance_calculation(self):
        portfolio = ShadowPortfolio(start_date=date(2026, 2, 24))
        positions = [ShadowPosition(ticker="AAPL", weight=1.0, price=175.0, composite_score=82.0)]
        portfolio.record_snapshot(date(2026, 2, 24), positions, portfolio_value=1_000_000.0)
        portfolio.record_snapshot(date(2026, 2, 25), positions, portfolio_value=1_010_000.0)
        portfolio.record_snapshot(date(2026, 2, 26), positions, portfolio_value=1_005_000.0)

        assert portfolio.total_return == pytest.approx(0.005, abs=1e-6)
        assert portfolio.max_drawdown == pytest.approx(0.00495, abs=1e-4)
        assert portfolio.num_days == 3

    def test_empty_portfolio_zero_return(self):
        portfolio = ShadowPortfolio(start_date=date(2026, 2, 24))
        assert portfolio.total_return == 0.0
        assert portfolio.max_drawdown == 0.0
        assert portfolio.num_days == 0
