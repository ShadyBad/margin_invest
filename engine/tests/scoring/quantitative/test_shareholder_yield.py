"""Tests for Shareholder Yield (Mebane Faber) value factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.shareholder_yield import shareholder_yield


class TestShareholderYield:
    def test_apple_golden_value(self):
        """Apple FY2024: (15234B + 94949B) / 3500B ≈ 0.0315."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = shareholder_yield(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.raw_value == pytest.approx(0.0315, rel=1e-3)

    def test_name(self):
        """Factor name should be 'shareholder_yield'."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = shareholder_yield(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.name == "shareholder_yield"

    def test_percentile_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = shareholder_yield(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.percentile_rank == 0.0

    def test_zero_market_cap(self):
        """When market_cap=0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            dividends_paid=Decimal("-5000"),
            share_repurchases=Decimal("-3000"),
            share_issuance=Decimal("0"),
        )
        result = shareholder_yield(period, Decimal("0"))
        assert result.raw_value == 0.0
        assert "market_cap" in result.detail.lower()

    def test_negative_market_cap(self):
        """When market_cap<0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            dividends_paid=Decimal("-5000"),
            share_repurchases=Decimal("-3000"),
            share_issuance=Decimal("0"),
        )
        result = shareholder_yield(period, Decimal("-100"))
        assert result.raw_value == 0.0
        assert "market_cap" in result.detail.lower()

    def test_no_dividends(self):
        """When dividends_paid is None, treat as 0 — only buybacks contribute."""
        period = _make_period(
            dividends_paid=None,
            share_repurchases=Decimal("-10000"),
            share_issuance=Decimal("0"),
        )
        result = shareholder_yield(period, Decimal("100000"))
        # Net buybacks = 10000, dividends = 0 -> yield = 10000 / 100000 = 0.10
        assert result.raw_value == pytest.approx(0.10, abs=0.001)

    def test_net_issuance_negative_yield(self):
        """When net buybacks are negative (net issuance), yield can be negative."""
        period = _make_period(
            dividends_paid=Decimal("-1000"),
            share_repurchases=Decimal("0"),
            share_issuance=Decimal("5000"),
        )
        result = shareholder_yield(period, Decimal("100000"))
        # Dividends = 1000, net_buybacks = 0 - 5000 = -5000
        # Total return = 1000 + (-5000) = -4000
        # Yield = -4000 / 100000 = -0.04
        assert result.raw_value == pytest.approx(-0.04, abs=0.001)

    def test_detail_contains_breakdown(self):
        """Detail string should contain a human-readable breakdown."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = shareholder_yield(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert "15234000000" in result.detail
        assert "94949000000" in result.detail

    def test_basic_computation(self):
        """Simple synthetic case: (2000 + 3000) / 100000 = 0.05."""
        period = _make_period(
            dividends_paid=Decimal("-2000"),
            share_repurchases=Decimal("-3000"),
            share_issuance=Decimal("0"),
        )
        result = shareholder_yield(period, Decimal("100000"))
        assert result.raw_value == pytest.approx(0.05, abs=0.001)


def _make_period(
    dividends_paid: Decimal | None,
    share_repurchases: Decimal | None,
    share_issuance: Decimal | None,
) -> FinancialPeriod:
    """Helper to build a minimal FinancialPeriod for testing."""
    income = IncomeStatement(revenue=Decimal("0"))
    balance = BalanceSheet(total_assets=Decimal("1"))
    cf = CashFlowStatement(
        dividends_paid=dividends_paid,
        share_repurchases=share_repurchases,
        share_issuance=share_issuance,
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )
