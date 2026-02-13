"""Tests for FCF distress check filter."""

from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.models.scoring import FilterVerdict
from margin_engine.scoring.filters.fcf_distress import fcf_distress_check


class TestFCFDistress:
    def test_apple_passes(self):
        """Apple FY2024 with strong positive FCF should PASS."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = fcf_distress_check(APPLE_PERIOD_2024)
        assert result.passed is True
        assert result.name == "fcf_distress"

    def test_negative_fcf_fails(self):
        """Company with negative FCF should FAIL."""
        income = IncomeStatement(
            revenue=Decimal("500"),
            ebit=Decimal("50"),
            net_income=Decimal("20"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("1000"),
            total_equity=Decimal("500"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("30"),
            capital_expenditures=Decimal("-50"),  # FCF = 30 - 50 = -20
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = fcf_distress_check(period)
        assert result.passed is False
        assert result.verdict == FilterVerdict.FAIL

    def test_zero_fcf_passes(self):
        """Zero FCF should PASS (not negative)."""
        income = IncomeStatement(
            revenue=Decimal("500"),
            ebit=Decimal("50"),
            net_income=Decimal("20"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("1000"),
            total_equity=Decimal("500"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("50"),
            capital_expenditures=Decimal("-50"),  # FCF = 0
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = fcf_distress_check(period)
        assert result.passed is True

    def test_threshold_is_zero(self):
        """Threshold should be 0."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = fcf_distress_check(APPLE_PERIOD_2024)
        assert result.threshold == 0.0
