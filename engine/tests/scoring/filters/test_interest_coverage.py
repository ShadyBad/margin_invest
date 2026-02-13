"""Tests for Interest Coverage Ratio filter."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.filters.interest_coverage import interest_coverage_check


class TestInterestCoverage:
    def test_apple_passes(self):
        """Apple FY2024 with ICR ~34x should PASS for Technology."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = interest_coverage_check(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True
        assert result.value == pytest.approx(34.21, abs=0.1)

    def test_low_coverage_fails_tech(self):
        """Company with ICR = 2.0 should FAIL for Technology (threshold > 3.0)."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            interest_expense=Decimal("50"),
            net_income=Decimal("30"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("80"),
            capital_expenditures=Decimal("-20"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = interest_coverage_check(period, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False
        assert result.value == pytest.approx(2.0)

    def test_same_coverage_passes_default(self):
        """ICR = 2.0 should PASS for non-tech default threshold (> 1.5)."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            interest_expense=Decimal("50"),
            net_income=Decimal("30"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("80"),
            capital_expenditures=Decimal("-20"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = interest_coverage_check(period, sector=GICSSector.CONSUMER_STAPLES)
        assert result.passed is True

    def test_no_interest_expense_passes(self):
        """No interest expense means no debt service -> PASS."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            net_income=Decimal("80"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("80"),
            capital_expenditures=Decimal("-20"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = interest_coverage_check(period)
        assert result.passed is True

    def test_utilities_lower_threshold(self):
        """Utilities have a lower threshold of 1.2."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("130"),
            interest_expense=Decimal("100"),
            net_income=Decimal("20"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("5000"),
            total_equity=Decimal("2000"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("150"),
            capital_expenditures=Decimal("-50"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        # ICR = 130/100 = 1.3, passes utilities threshold of 1.2
        result = interest_coverage_check(period, sector=GICSSector.UTILITIES)
        assert result.passed is True
        assert result.value == pytest.approx(1.3)

    def test_filter_name(self):
        """Filter should have correct name."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = interest_coverage_check(APPLE_PERIOD_2024)
        assert result.name == "interest_coverage"
