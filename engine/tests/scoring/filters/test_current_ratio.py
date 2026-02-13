"""Tests for Current Ratio filter."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.filters.current_ratio import current_ratio_check


class TestCurrentRatio:
    def test_apple_passes_technology(self):
        """Apple FY2024 CR ~0.87 should PASS for Technology (threshold > 0.8)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = current_ratio_check(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True
        assert result.value == pytest.approx(0.8673, abs=0.001)

    def test_low_ratio_fails(self):
        """Company with CR = 0.5 should FAIL for default threshold."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            net_income=Decimal("50"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            current_assets=Decimal("200"),
            current_liabilities=Decimal("400"),  # CR = 0.5
            total_liabilities=Decimal("800"),
            total_equity=Decimal("1200"),
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
        result = current_ratio_check(period)
        assert result.passed is False
        assert result.value == pytest.approx(0.5)

    def test_utilities_lower_threshold(self):
        """Utilities with CR = 0.7 should PASS (threshold > 0.6)."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            net_income=Decimal("50"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("5000"),
            current_assets=Decimal("350"),
            current_liabilities=Decimal("500"),  # CR = 0.7
            total_liabilities=Decimal("3000"),
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
        result = current_ratio_check(period, sector=GICSSector.UTILITIES)
        assert result.passed is True

    def test_zero_liabilities_passes(self):
        """Zero current liabilities -> infinite ratio -> PASS."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            net_income=Decimal("50"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            current_assets=Decimal("500"),
            current_liabilities=Decimal("0"),
            total_liabilities=Decimal("200"),
            total_equity=Decimal("1800"),
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
        result = current_ratio_check(period)
        assert result.passed is True

    def test_filter_name(self):
        """Filter should have correct name."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = current_ratio_check(APPLE_PERIOD_2024)
        assert result.name == "current_ratio"
