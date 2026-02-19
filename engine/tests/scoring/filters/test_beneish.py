"""Tests for Beneish M-Score earnings manipulation filter."""

from decimal import Decimal

import pytest
from margin_engine.config.filter_config import BeneishConfig
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


class TestBeneishWithConfig:
    """Tests for config-driven Beneish thresholds."""

    def test_config_parameter_accepted(self):
        """Config parameter should be accepted without error."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        config = BeneishConfig()
        result = beneish_m_score(APPLE_PERIOD_2024, config=config)
        assert result.passed is True

    def test_config_threshold_overrides_hardcoded(self):
        """Config threshold should override the hardcoded -1.78.

        Apple M-Score is approx -2.79. With a stricter threshold of -3.0,
        Apple should FAIL because -2.79 > -3.0.
        """
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        strict_config = BeneishConfig(threshold=-3.0)
        result = beneish_m_score(APPLE_PERIOD_2024, config=strict_config)
        assert result.passed is False
        assert result.threshold == -3.0

    def test_without_config_backward_compatible(self):
        """Without config, behavior matches original hardcoded thresholds."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = beneish_m_score(APPLE_PERIOD_2024)
        assert result.passed is True
        assert result.threshold == -1.78

    def test_insufficient_data_sets_fields(self):
        """When prior data is missing, insufficient_data and missing_fields should be set."""
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
        assert result.insufficient_data is True
        assert result.missing_fields is not None
        assert "prior_income" in result.missing_fields
        assert "prior_balance" in result.missing_fields

    def test_insufficient_data_only_prior_balance_missing(self):
        """When only prior_balance is missing, missing_fields should contain just that."""
        current_income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("200"),
            net_income=Decimal("150"),
            shares_outstanding=100,
        )
        prior_income = IncomeStatement(
            revenue=Decimal("800"),
            ebit=Decimal("180"),
            net_income=Decimal("120"),
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
            prior_income=prior_income,
            current_balance=current_balance,
            current_cash_flow=current_cf,
        )
        result = beneish_m_score(period)
        assert result.insufficient_data is True
        assert result.missing_fields == ["prior_balance"]
