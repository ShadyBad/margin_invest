"""Integration tests: full elimination filter pipeline against golden fixture."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.filters.pipeline import run_elimination_filters


class TestAppleIntegration:
    """Verify Apple FY2024 passes the full elimination pipeline."""

    @pytest.fixture
    def apple_result(self):
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        return run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE)

    def test_apple_passes_overall(self, apple_result):
        """Apple should pass the complete elimination pipeline."""
        assert apple_result.passed is True, (
            f"Apple failed filters: {[r.name for r in apple_result.failed_filters]}"
        )

    def test_apple_all_seven_filters_run(self, apple_result):
        assert len(apple_result.results) == 7

    def test_apple_liquidity_pass(self, apple_result):
        liquidity = next(r for r in apple_result.results if r.name == "liquidity")
        assert liquidity.passed is True

    def test_apple_beneish_pass(self, apple_result):
        beneish = next(r for r in apple_result.results if r.name == "beneish_m_score")
        assert beneish.passed is True
        assert beneish.value is not None
        assert beneish.value < -1.78  # Well below threshold

    def test_apple_altman_pass(self, apple_result):
        altman = next(r for r in apple_result.results if r.name == "altman_z_score")
        assert altman.passed is True
        assert altman.value is not None
        assert altman.value > 1.1  # Above distress threshold

    def test_apple_fcf_pass(self, apple_result):
        fcf = next(r for r in apple_result.results if r.name == "fcf_distress")
        assert fcf.passed is True
        # Apple has massive positive FCF

    def test_apple_interest_coverage_pass(self, apple_result):
        ic = next(r for r in apple_result.results if r.name == "interest_coverage")
        assert ic.passed is True
        assert ic.value is not None
        assert ic.value > 3.0  # Technology threshold

    def test_apple_current_ratio_pass(self, apple_result):
        cr = next(r for r in apple_result.results if r.name == "current_ratio")
        assert cr.passed is True
        assert cr.value is not None
        assert cr.value == pytest.approx(0.8673, abs=0.001)


class TestDistressedCompanyIntegration:
    """Verify a synthetic distressed company fails the pipeline."""

    @pytest.fixture
    def distressed_result(self):
        """Create a company that should fail multiple filters."""
        current_income = IncomeStatement(
            revenue=Decimal("500"),
            cost_of_revenue=Decimal("400"),
            gross_profit=Decimal("100"),
            sga_expense=Decimal("80"),
            depreciation=Decimal("20"),
            ebit=Decimal("-20"),  # Negative EBIT
            interest_expense=Decimal("50"),  # High interest
            net_income=Decimal("-100"),
            shares_outstanding=100,
        )
        prior_income = IncomeStatement(
            revenue=Decimal("600"),
            cost_of_revenue=Decimal("350"),
            gross_profit=Decimal("250"),
            sga_expense=Decimal("60"),
            depreciation=Decimal("20"),
            ebit=Decimal("150"),
            interest_expense=Decimal("30"),
            net_income=Decimal("90"),
            shares_outstanding=100,
        )
        current_balance = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("150"),
            receivables=Decimal("100"),
            current_liabilities=Decimal("400"),
            total_liabilities=Decimal("900"),
            long_term_debt=Decimal("400"),
            total_equity=Decimal("100"),
            retained_earnings=Decimal("-300"),
            pp_and_e=Decimal("400"),
            shares_outstanding=100,
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("1200"),
            current_assets=Decimal("300"),
            receivables=Decimal("120"),
            current_liabilities=Decimal("350"),
            total_liabilities=Decimal("800"),
            long_term_debt=Decimal("350"),
            total_equity=Decimal("400"),
            retained_earnings=Decimal("100"),
            pp_and_e=Decimal("450"),
            shares_outstanding=100,
        )
        current_cf = CashFlowStatement(
            operating_cash_flow=Decimal("-40"),
            capital_expenditures=Decimal("-10"),
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
        profile = AssetProfile(
            ticker="FAIL",
            name="Failing Corp",
            sector=GICSSector.INDUSTRIALS,
            market_cap=Decimal("500000000"),  # $500M -- passes liquidity
            avg_daily_volume=Decimal("5000000"),
            years_of_history=10,
        )
        return run_elimination_filters(period, profile)

    def test_distressed_fails_overall(self, distressed_result):
        """Distressed company should fail the pipeline."""
        assert distressed_result.passed is False

    def test_distressed_multiple_failures(self, distressed_result):
        """Should fail multiple filters (FCF, interest coverage, current ratio, possibly altman)."""
        assert len(distressed_result.failed_filters) >= 3

    def test_all_filters_still_run(self, distressed_result):
        """All 7 filters should run even with failures."""
        assert len(distressed_result.results) == 7
