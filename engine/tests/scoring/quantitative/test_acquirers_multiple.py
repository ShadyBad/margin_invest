"""Tests for Acquirer's Multiple (EV/EBIT) value factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.acquirers_multiple import acquirers_multiple


class TestAcquirersMultiple:
    def test_apple_golden_value(self):
        """Apple FY2024: EV/EBIT = 3,743,260,000,000 / 122,571,000,000 ~ 30.5395."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = acquirers_multiple(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.raw_value == pytest.approx(30.5395, rel=1e-3)

    def test_name(self):
        """Factor name should be 'acquirers_multiple'."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = acquirers_multiple(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.name == "acquirers_multiple"

    def test_percentile_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = acquirers_multiple(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.percentile_rank == 0.0

    def test_negative_ebit(self):
        """When EBIT < 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            ebit=Decimal("-5000"),
            current_liabilities=Decimal("1000"),
            long_term_debt=Decimal("2000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = acquirers_multiple(period, Decimal("100000"))
        assert result.raw_value == 0.0
        assert "non-positive" in result.detail.lower() or "ebit" in result.detail.lower()

    def test_zero_ebit(self):
        """When EBIT = 0 exactly, raw_value should be 0.0."""
        period = _make_period(
            ebit=Decimal("0"),
            current_liabilities=Decimal("1000"),
            long_term_debt=Decimal("2000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = acquirers_multiple(period, Decimal("100000"))
        assert result.raw_value == 0.0

    def test_zero_market_cap(self):
        """When market_cap <= 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            ebit=Decimal("10000"),
            current_liabilities=Decimal("1000"),
            long_term_debt=Decimal("3000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = acquirers_multiple(period, Decimal("0"))
        assert result.raw_value == 0.0
        assert "market cap" in result.detail.lower()

    def test_negative_market_cap(self):
        """When market_cap < 0, raw_value should be 0.0."""
        period = _make_period(
            ebit=Decimal("10000"),
            current_liabilities=Decimal("1000"),
            long_term_debt=Decimal("3000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = acquirers_multiple(period, Decimal("-100"))
        assert result.raw_value == 0.0

    def test_detail_contains_key_values(self):
        """Detail string should contain EV, EBIT, and the ratio."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = acquirers_multiple(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert "3743260000000" in result.detail
        assert "122571000000" in result.detail
        assert "30.53" in result.detail

    def test_simple_synthetic_computation(self):
        """Verify computation with simple synthetic values.

        market_cap=100, total_debt=30 (LTD=20 + CL=10), cash=10 -> EV=120
        EBIT=15
        EV/EBIT = 120/15 = 8.0
        """
        period = _make_period(
            ebit=Decimal("15"),
            current_liabilities=Decimal("10"),
            long_term_debt=Decimal("20"),
            cash_and_equivalents=Decimal("10"),
        )
        result = acquirers_multiple(period, Decimal("100"))
        assert result.raw_value == pytest.approx(8.0, rel=1e-3)

    def test_none_cash_treated_as_zero(self):
        """When cash_and_equivalents is None, treat as 0."""
        period = _make_period(
            ebit=Decimal("10"),
            current_liabilities=Decimal("5"),
            long_term_debt=Decimal("15"),
            cash_and_equivalents=None,
        )
        # EV = 100 + 20 - 0 = 120, EV/EBIT = 120/10 = 12.0
        result = acquirers_multiple(period, Decimal("100"))
        assert result.raw_value == pytest.approx(12.0, rel=1e-3)


def _make_period(
    ebit: Decimal,
    current_liabilities: Decimal = Decimal("0"),
    long_term_debt: Decimal | None = None,
    cash_and_equivalents: Decimal | None = None,
) -> FinancialPeriod:
    """Helper to build a minimal FinancialPeriod for testing Acquirer's Multiple."""
    income = IncomeStatement(revenue=Decimal("0"), ebit=ebit)
    balance = BalanceSheet(
        total_assets=Decimal("100000"),
        current_liabilities=current_liabilities,
        long_term_debt=long_term_debt,
        cash_and_equivalents=cash_and_equivalents,
    )
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("0"),
        capital_expenditures=Decimal("0"),
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )
