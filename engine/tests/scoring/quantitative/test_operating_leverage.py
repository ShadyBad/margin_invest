"""Tests for Operating Leverage factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.operating_leverage import operating_leverage


class TestOperatingLeverage:
    def test_positive_leverage(self):
        """Revenue +20%, OpEx +10% -> leverage = 2.0."""
        history = _make_history(
            revenues=[Decimal("100"), Decimal("120")],
            sga_expenses=[Decimal("50"), Decimal("55")],
        )
        result = operating_leverage(history)
        assert result.raw_value == pytest.approx(2.0, rel=1e-3)
        assert result.name == "operating_leverage"
        assert result.percentile_rank == 0.0

    def test_no_leverage(self):
        """Both revenue and OpEx +20% -> leverage = 1.0."""
        history = _make_history(
            revenues=[Decimal("100"), Decimal("120")],
            sga_expenses=[Decimal("50"), Decimal("60")],
        )
        result = operating_leverage(history)
        assert result.raw_value == pytest.approx(1.0, rel=1e-3)

    def test_negative_leverage(self):
        """Revenue +10%, OpEx +20% -> leverage = 0.5."""
        history = _make_history(
            revenues=[Decimal("100"), Decimal("110")],
            sga_expenses=[Decimal("50"), Decimal("60")],
        )
        result = operating_leverage(history)
        assert result.raw_value == pytest.approx(0.5, rel=1e-3)

    def test_insufficient_periods(self):
        """Only 1 period -> 0.0 sentinel."""
        history = _make_history(
            revenues=[Decimal("100")],
            sga_expenses=[Decimal("50")],
        )
        result = operating_leverage(history)
        assert result.raw_value == 0.0
        assert "need at least 2" in result.detail.lower()

    def test_zero_opex_growth_capped(self):
        """OpEx flat (growth = 0), revenue growing -> capped at 10.0."""
        history = _make_history(
            revenues=[Decimal("100"), Decimal("120")],
            sga_expenses=[Decimal("50"), Decimal("50")],
        )
        result = operating_leverage(history)
        assert result.raw_value == pytest.approx(10.0, rel=1e-3)

    def test_cost_cutting_flat_revenue(self):
        """Flat revenue (1% growth), declining opex (-5%) -> positive floor score."""
        # rev_growth = (101-100)/100 = 0.01
        # opex_growth = (47.5-50)/50 = -0.05
        # raw_value = min(abs(-0.05) * 5.0, 2.0) = min(0.25, 2.0) = 0.25
        history = _make_history(
            revenues=[Decimal("100"), Decimal("101")],
            sga_expenses=[Decimal("50"), Decimal("47.5")],
        )
        result = operating_leverage(history)
        assert result.raw_value == pytest.approx(0.25, rel=1e-3)
        assert result.name == "operating_leverage"

    def test_cost_cutting_large_opex_decline_capped(self):
        """Flat revenue (1%), large opex decline (-40%) -> capped at 2.0."""
        # rev_growth = (101-100)/100 = 0.01
        # opex_growth = (30-50)/50 = -0.40
        # raw_value = min(abs(-0.40) * 5.0, 2.0) = min(2.0, 2.0) = 2.0
        history = _make_history(
            revenues=[Decimal("100"), Decimal("101")],
            sga_expenses=[Decimal("50"), Decimal("30")],
        )
        result = operating_leverage(history)
        assert result.raw_value == pytest.approx(2.0, rel=1e-3)

    def test_growing_revenue_growing_opex_unchanged(self):
        """Growing revenue (10%), growing opex (5%) -> normal leverage, no floor."""
        # rev_growth = 0.10, opex_growth = 0.05 -> leverage = 2.0
        history = _make_history(
            revenues=[Decimal("100"), Decimal("110")],
            sga_expenses=[Decimal("50"), Decimal("52.5")],
        )
        result = operating_leverage(history)
        assert result.raw_value == pytest.approx(2.0, rel=1e-3)


def _make_history(
    revenues: list[Decimal],
    sga_expenses: list[Decimal],
) -> FinancialHistory:
    """Build a FinancialHistory with given revenue and SGA values per period."""
    periods = []
    for i, (rev, sga) in enumerate(zip(revenues, sga_expenses)):
        period = FinancialPeriod(
            period_end=f"{2020 + i}-12-31",
            filing_date=f"{2021 + i}-02-15",
            current_income=IncomeStatement(revenue=rev, sga_expense=sga),
            current_balance=BalanceSheet(total_assets=Decimal("100000")),
            current_cash_flow=CashFlowStatement(),
        )
        periods.append(period)
    return FinancialHistory(ticker="TEST", periods=periods)
