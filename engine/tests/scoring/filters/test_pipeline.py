"""Tests for the elimination filter pipeline."""

from decimal import Decimal

from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.filters.pipeline import run_elimination_filters


class TestFilterPipeline:
    def test_apple_runs_all_filters(self):
        """Pipeline runs all 6 filters for Apple."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE)
        assert len(result.results) == 6

    def test_apple_overall_result(self):
        """Apple should pass all 6 filters."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE)
        assert result.passed is True
        assert len(result.failed_filters) == 0

    def test_all_filter_names_present(self):
        """All 6 filter names should be in the results."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE)
        names = {r.name for r in result.results}
        assert names == {
            "liquidity",
            "beneish_m_score",
            "altman_z_score",
            "fcf_distress",
            "interest_coverage",
            "current_ratio",
        }

    def test_excluded_sector_fails(self):
        """Financial sector company should fail (liquidity filter)."""
        income = IncomeStatement(
            revenue=Decimal("50000"),
            ebit=Decimal("10000"),
            net_income=Decimal("8000"),
            shares_outstanding=1000,
        )
        balance = BalanceSheet(
            total_assets=Decimal("500000"),
            current_assets=Decimal("200000"),
            current_liabilities=Decimal("100000"),
            total_liabilities=Decimal("300000"),
            total_equity=Decimal("200000"),
            retained_earnings=Decimal("50000"),
            shares_outstanding=1000,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("12000"),
            capital_expenditures=Decimal("-2000"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        profile = AssetProfile(
            ticker="JPM",
            name="JPMorgan",
            sector=GICSSector.FINANCIALS,
            market_cap=Decimal("500000000000"),
            avg_daily_volume=Decimal("50000000"),
            years_of_history=30,
        )
        result = run_elimination_filters(period, profile)
        assert result.passed is False
        assert any(r.name == "liquidity" and not r.passed for r in result.results)

    def test_no_short_circuit(self):
        """All filters should run even if one fails (no short-circuit)."""
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
        profile = AssetProfile(
            ticker="BAD",
            name="Bad Corp",
            sector=GICSSector.INDUSTRIALS,
            market_cap=Decimal("500000000"),
            avg_daily_volume=Decimal("5000000"),
            years_of_history=10,
        )
        result = run_elimination_filters(period, profile)
        # Should have all 6 results even though multiple fail
        assert len(result.results) == 6
        assert result.passed is False
        assert len(result.failed_filters) >= 1

    def test_pipeline_result_properties(self):
        """PipelineResult.passed and failed_filters work correctly."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE)
        # All passed
        assert result.passed is True
        assert result.failed_filters == []
