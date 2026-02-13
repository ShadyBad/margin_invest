"""Tests for Beneish M-Score earnings manipulation filter."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.models.scoring import FilterVerdict
from margin_engine.scoring.filters.beneish import beneish_m_score


class TestBeneishMScore:
    def test_apple_passes(self):
        """Apple FY2024 should PASS (M-Score well below -1.78)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = beneish_m_score(APPLE_PERIOD_2024)
        assert result.passed is True
        assert result.verdict == FilterVerdict.PASS
        assert result.value is not None
        assert result.value == pytest.approx(-2.79, abs=0.1)  # Golden value

    def test_manipulator_fails(self):
        """Synthetic data with high manipulation indicators should FAIL."""
        # Create synthetic data that would trigger a FAIL:
        # High DSRI (inflated receivables), high TATA (accruals >> cash)
        current_income = IncomeStatement(
            revenue=Decimal("1000"),
            cost_of_revenue=Decimal("600"),
            gross_profit=Decimal("400"),
            sga_expense=Decimal("100"),
            depreciation=Decimal("50"),
            ebit=Decimal("250"),
            net_income=Decimal("300"),  # Suspiciously high vs cash flow
            shares_outstanding=100,
        )
        prior_income = IncomeStatement(
            revenue=Decimal("800"),
            cost_of_revenue=Decimal("400"),
            gross_profit=Decimal("400"),
            sga_expense=Decimal("100"),
            depreciation=Decimal("50"),
            ebit=Decimal("250"),
            net_income=Decimal("200"),
            shares_outstanding=100,
        )
        current_balance = BalanceSheet(
            total_assets=Decimal("2000"),
            current_assets=Decimal("800"),
            receivables=Decimal("400"),  # 40% of revenue (high)
            total_liabilities=Decimal("1200"),
            current_liabilities=Decimal("600"),
            long_term_debt=Decimal("400"),
            total_equity=Decimal("800"),
            pp_and_e=Decimal("500"),
            shares_outstanding=100,
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("1500"),
            current_assets=Decimal("600"),
            receivables=Decimal("160"),  # 20% of revenue (normal)
            total_liabilities=Decimal("900"),
            current_liabilities=Decimal("400"),
            long_term_debt=Decimal("300"),
            total_equity=Decimal("600"),
            pp_and_e=Decimal("500"),
            shares_outstanding=100,
        )
        current_cf = CashFlowStatement(
            operating_cash_flow=Decimal("50"),  # Way below net_income = high accruals
            capital_expenditures=Decimal("-30"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=current_income,
            prior_income=prior_income,
            current_balance=current_balance,
            prior_balance=prior_balance,
            current_cash_flow=current_cf,
        )
        result = beneish_m_score(period)
        assert result.passed is False
        assert result.verdict == FilterVerdict.FAIL
        assert result.value is not None
        assert result.value > -1.78

    def test_missing_prior_data_passes(self):
        """Without prior period data, filter passes with explanation."""
        current_income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("200"),
            net_income=Decimal("150"),
            shares_outstanding=100,
        )
        current_balance = BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
            shares_outstanding=100,
        )
        current_cf = CashFlowStatement(
            operating_cash_flow=Decimal("180"),
            capital_expenditures=Decimal("-30"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=current_income,
            current_balance=current_balance,
            current_cash_flow=current_cf,
        )
        result = beneish_m_score(period)
        assert result.passed is True
        assert "insufficient" in result.detail.lower() or "historical" in result.detail.lower()

    def test_filter_name(self):
        """Filter result should have correct name."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = beneish_m_score(APPLE_PERIOD_2024)
        assert result.name == "beneish_m_score"

    def test_threshold_value(self):
        """Filter should report threshold of -1.78."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = beneish_m_score(APPLE_PERIOD_2024)
        assert result.threshold == -1.78
