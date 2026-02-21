"""Tests for EV/Gross Profit factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.ev_gross_profit import ev_gross_profit


class TestEvGrossProfit:
    def test_normal_ratio(self):
        """Normal case: EV/GP with positive gross profit.

        market_cap=100, total_debt=30 (LTD=20 + STD=10), cash=10 -> EV=120
        gross_profit=40
        EV/GP = 120 / 40 = 3.0
        """
        period = _make_period(
            revenue=Decimal("100"),
            gross_profit=Decimal("40"),
            short_term_debt=Decimal("10"),
            long_term_debt=Decimal("20"),
            cash_and_equivalents=Decimal("10"),
        )
        result = ev_gross_profit(period, Decimal("100"))
        assert result.raw_value == pytest.approx(3.0, rel=1e-3)
        assert result.name == "ev_gross_profit"
        assert result.percentile_rank == 0.0

    def test_zero_gross_profit(self):
        """Zero gross profit -> 0.0 sentinel."""
        period = _make_period(
            revenue=Decimal("100"),
            gross_profit=Decimal("0"),
        )
        result = ev_gross_profit(period, Decimal("100"))
        assert result.raw_value == 0.0
        assert "non-positive" in result.detail.lower()

    def test_negative_gross_profit(self):
        """Negative gross profit -> 0.0 sentinel."""
        period = _make_period(
            revenue=Decimal("100"),
            gross_profit=Decimal("-20"),
        )
        result = ev_gross_profit(period, Decimal("100"))
        assert result.raw_value == 0.0
        assert "non-positive" in result.detail.lower()


def _make_period(
    revenue: Decimal = Decimal("0"),
    gross_profit: Decimal = Decimal("0"),
    short_term_debt: Decimal = Decimal("0"),
    long_term_debt: Decimal | None = None,
    cash_and_equivalents: Decimal | None = None,
) -> FinancialPeriod:
    """Helper to build a minimal FinancialPeriod for testing EV/GP."""
    income = IncomeStatement(revenue=revenue, gross_profit=gross_profit)
    balance = BalanceSheet(
        total_assets=Decimal("100000"),
        short_term_debt=short_term_debt,
        long_term_debt=long_term_debt,
        cash_and_equivalents=cash_and_equivalents,
    )
    cf = CashFlowStatement()
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )
