"""Tests for Altman Z'' Score financial distress filter."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import FilterVerdict
from margin_engine.scoring.filters.altman import altman_z_score


class TestAltmanZScore:
    def test_apple_passes(self):
        """Apple FY2024 should PASS with Z'' ≈ 1.86."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024
        result = altman_z_score(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True
        assert result.value is not None
        assert result.value == pytest.approx(1.86, abs=0.05)

    def test_distressed_company_fails(self):
        """Synthetic distressed company should FAIL (Z'' < 1.1)."""
        income = IncomeStatement(
            revenue=Decimal("500"),
            ebit=Decimal("-50"),  # Negative EBIT
            net_income=Decimal("-80"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("200"),
            current_liabilities=Decimal("400"),  # Negative working capital
            total_liabilities=Decimal("900"),
            total_equity=Decimal("100"),
            retained_earnings=Decimal("-200"),  # Accumulated losses
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("-30"),
            capital_expenditures=Decimal("-10"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = altman_z_score(period)
        assert result.passed is False
        assert result.verdict == FilterVerdict.FAIL
        assert result.value < 1.1

    def test_utilities_exempt(self):
        """Utilities sector should be exempt (auto-PASS)."""
        income = IncomeStatement(
            revenue=Decimal("500"),
            ebit=Decimal("-50"),
            net_income=Decimal("-80"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("200"),
            current_liabilities=Decimal("400"),
            total_liabilities=Decimal("900"),
            total_equity=Decimal("100"),
            retained_earnings=Decimal("-200"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("-30"),
            capital_expenditures=Decimal("-10"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = altman_z_score(period, sector=GICSSector.UTILITIES)
        assert result.passed is True
        assert "utilities" in result.detail.lower() or "not applicable" in result.detail.lower()

    def test_filter_name_and_threshold(self):
        """Filter result should have correct name and threshold."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024
        result = altman_z_score(APPLE_PERIOD_2024)
        assert result.name == "altman_z_score"
        assert result.threshold == 1.1

    def test_healthy_company_passes(self):
        """Synthetic healthy company should PASS."""
        income = IncomeStatement(
            revenue=Decimal("2000"),
            ebit=Decimal("500"),
            net_income=Decimal("400"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("3000"),
            current_assets=Decimal("1500"),
            current_liabilities=Decimal("600"),
            total_liabilities=Decimal("1200"),
            total_equity=Decimal("1800"),
            retained_earnings=Decimal("800"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("450"),
            capital_expenditures=Decimal("-100"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = altman_z_score(period)
        assert result.passed is True
        assert result.value > 1.1
