"""Tests for EV/FCF (Enterprise Value / Free Cash Flow) value factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.ev_fcf import ev_fcf


class TestEvFcf:
    def test_apple_golden_value(self):
        """Apple FY2024: EV/FCF = 3,587,747,000,000 / 108,295,000,000 ~ 33.1294."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = ev_fcf(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.raw_value == pytest.approx(33.1294, rel=1e-3)

    def test_name(self):
        """Factor name should be 'ev_fcf'."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = ev_fcf(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.name == "ev_fcf"

    def test_percentile_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = ev_fcf(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.percentile_rank == 0.0

    def test_negative_fcf(self):
        """When FCF <= 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            operating_cash_flow=Decimal("5000"),
            capital_expenditures=Decimal("-8000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("2000"),
            cash_and_equivalents=Decimal("500"),
        )
        market_cap = Decimal("100000")
        result = ev_fcf(period, market_cap)
        assert result.raw_value == 0.0
        assert "negative" in result.detail.lower() or "zero" in result.detail.lower()

    def test_zero_fcf(self):
        """When FCF = 0 exactly, raw_value should be 0.0."""
        period = _make_period(
            operating_cash_flow=Decimal("5000"),
            capital_expenditures=Decimal("-5000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("2000"),
            cash_and_equivalents=Decimal("500"),
        )
        market_cap = Decimal("100000")
        result = ev_fcf(period, market_cap)
        assert result.raw_value == 0.0

    def test_zero_market_cap(self):
        """When market_cap <= 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            operating_cash_flow=Decimal("10000"),
            capital_expenditures=Decimal("-2000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("3000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = ev_fcf(period, Decimal("0"))
        assert result.raw_value == 0.0
        assert "market cap" in result.detail.lower()

    def test_negative_market_cap(self):
        """When market_cap < 0, raw_value should be 0.0."""
        period = _make_period(
            operating_cash_flow=Decimal("10000"),
            capital_expenditures=Decimal("-2000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("3000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = ev_fcf(period, Decimal("-100"))
        assert result.raw_value == 0.0

    def test_detail_contains_key_values(self):
        """Detail string should contain EV, FCF, and the ratio."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = ev_fcf(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert "3587747000000" in result.detail
        assert "108295000000" in result.detail
        assert "33.12" in result.detail

    def test_simple_synthetic_computation(self):
        """Verify computation with simple synthetic values.

        market_cap=100, total_debt=30 (LTD=20 + STD=10), cash=10 -> EV=120
        CFO=20, CapEx=-5 -> FCF=15
        EV/FCF = 120/15 = 8.0
        """
        period = _make_period(
            operating_cash_flow=Decimal("20"),
            capital_expenditures=Decimal("-5"),
            short_term_debt=Decimal("10"),
            long_term_debt=Decimal("20"),
            cash_and_equivalents=Decimal("10"),
        )
        result = ev_fcf(period, Decimal("100"))
        assert result.raw_value == pytest.approx(8.0, rel=1e-3)


def _make_period(
    operating_cash_flow: Decimal,
    capital_expenditures: Decimal,
    short_term_debt: Decimal = Decimal("0"),
    long_term_debt: Decimal | None = None,
    cash_and_equivalents: Decimal | None = None,
) -> FinancialPeriod:
    """Helper to build a minimal FinancialPeriod for testing EV/FCF."""
    income = IncomeStatement(revenue=Decimal("0"))
    balance = BalanceSheet(
        total_assets=Decimal("100000"),
        short_term_debt=short_term_debt,
        long_term_debt=long_term_debt,
        cash_and_equivalents=cash_and_equivalents,
    )
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )
