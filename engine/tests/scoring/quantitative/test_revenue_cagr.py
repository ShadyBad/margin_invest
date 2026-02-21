"""Tests for Revenue CAGR factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr


class TestRevenueCagr:
    def test_steady_growth(self):
        """Revenue doubles in 3 years: CAGR = 2^(1/3) - 1 ~ 0.2599 (26%)."""
        history = _make_history(
            revenues=[Decimal("100"), Decimal("126"), Decimal("159"), Decimal("200")]
        )
        result = revenue_cagr(history, years=3)
        assert result.raw_value == pytest.approx(0.2599, rel=1e-2)
        assert result.name == "revenue_cagr"
        assert result.percentile_rank == 0.0

    def test_flat_revenue(self):
        """Flat revenue -> CAGR = 0.0."""
        history = _make_history(
            revenues=[Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100")]
        )
        result = revenue_cagr(history, years=3)
        assert result.raw_value == pytest.approx(0.0, abs=1e-6)

    def test_declining_revenue(self):
        """Declining revenue -> negative CAGR."""
        history = _make_history(
            revenues=[Decimal("200"), Decimal("180"), Decimal("160"), Decimal("100")]
        )
        result = revenue_cagr(history, years=3)
        assert result.raw_value < 0.0

    def test_insufficient_periods(self):
        """Only 1 period -> 0.0 sentinel."""
        history = _make_history(revenues=[Decimal("100")])
        result = revenue_cagr(history, years=3)
        assert result.raw_value == 0.0
        assert "need at least 2" in result.detail.lower()

    def test_zero_starting_revenue(self):
        """Zero starting revenue -> 0.0 sentinel."""
        history = _make_history(
            revenues=[Decimal("0"), Decimal("50"), Decimal("100"), Decimal("150")]
        )
        result = revenue_cagr(history, years=3)
        assert result.raw_value == 0.0
        assert "zero" in result.detail.lower() or "negative" in result.detail.lower()


def _make_history(revenues: list[Decimal]) -> FinancialHistory:
    """Build a FinancialHistory with given revenue values per period."""
    periods = []
    for i, rev in enumerate(revenues):
        period = FinancialPeriod(
            period_end=f"{2020 + i}-12-31",
            filing_date=f"{2021 + i}-02-15",
            current_income=IncomeStatement(revenue=rev),
            current_balance=BalanceSheet(total_assets=Decimal("100000")),
            current_cash_flow=CashFlowStatement(),
        )
        periods.append(period)
    return FinancialHistory(ticker="TEST", periods=periods)
