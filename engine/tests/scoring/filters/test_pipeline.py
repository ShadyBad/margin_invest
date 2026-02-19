"""Tests for the elimination filter pipeline."""

from decimal import Decimal

from margin_engine.config.filter_config import BeneishConfig, FilterConfig
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
    PriceBar,
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


class TestFilterPipelineWithConfig:
    """Tests for config-driven pipeline."""

    def test_config_parameter_accepted(self):
        """Pipeline accepts config parameter without error."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        config = FilterConfig()
        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE, config=config)
        assert len(result.results) == 6
        assert result.passed is True

    def test_config_flows_to_beneish(self):
        """Config beneish threshold should flow through the pipeline.

        Apple M-Score is approx -2.79. With threshold -3.0, it should FAIL.
        """
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        config = FilterConfig(beneish=BeneishConfig(threshold=-3.0))
        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE, config=config)
        beneish_result = next(r for r in result.results if r.name == "beneish_m_score")
        assert beneish_result.passed is False
        assert beneish_result.threshold == -3.0

    def test_without_config_backward_compatible(self):
        """Without config, pipeline behavior is identical to original."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE)
        assert result.passed is True
        assert len(result.results) == 6
        # All filter names present
        names = {r.name for r in result.results}
        assert names == {
            "liquidity",
            "beneish_m_score",
            "altman_z_score",
            "fcf_distress",
            "interest_coverage",
            "current_ratio",
        }

    def test_default_config_produces_same_results_as_no_config(self):
        """FilterConfig() defaults should produce the same results as no config."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result_no_config = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE)
        result_with_config = run_elimination_filters(
            APPLE_PERIOD_2024, APPLE_PROFILE, config=FilterConfig()
        )
        # Both should pass
        assert result_no_config.passed == result_with_config.passed
        # Same number of results
        assert len(result_no_config.results) == len(result_with_config.results)


# ---------------------------------------------------------------------------
# Helper factories for v2 pipeline tests
# ---------------------------------------------------------------------------

def _make_period(
    period_end: str,
    revenue: Decimal = Decimal("100000000000"),
    ebit: Decimal = Decimal("30000000000"),
    net_income: Decimal = Decimal("20000000000"),
    interest_expense: Decimal = Decimal("1000000000"),
    total_assets: Decimal = Decimal("300000000000"),
    current_assets: Decimal = Decimal("150000000000"),
    current_liabilities: Decimal = Decimal("100000000000"),
    total_liabilities: Decimal = Decimal("200000000000"),
    total_equity: Decimal = Decimal("100000000000"),
    retained_earnings: Decimal = Decimal("50000000000"),
    operating_cash_flow: Decimal = Decimal("35000000000"),
    capital_expenditures: Decimal = Decimal("-5000000000"),
    prior_income: IncomeStatement | None = None,
    prior_balance: BalanceSheet | None = None,
) -> FinancialPeriod:
    """Build a FinancialPeriod with sensible defaults for pipeline testing."""
    income = IncomeStatement(
        revenue=revenue,
        ebit=ebit,
        net_income=net_income,
        interest_expense=interest_expense,
        shares_outstanding=1000000000,
    )
    balance = BalanceSheet(
        total_assets=total_assets,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        retained_earnings=retained_earnings,
        shares_outstanding=1000000000,
    )
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date=period_end,
        current_income=income,
        prior_income=prior_income,
        current_balance=balance,
        prior_balance=prior_balance,
        current_cash_flow=cf,
    )


def _make_healthy_profile() -> AssetProfile:
    """Build a healthy large-cap tech profile that passes liquidity checks."""
    return AssetProfile(
        ticker="TEST",
        name="Test Corp",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("500000000000"),
        avg_daily_volume=Decimal("50000000"),
        years_of_history=20,
    )


def _make_price_bars(n: int = 100) -> list[PriceBar]:
    """Generate n daily price bars with sufficient volume for liquidity checks."""
    bars = []
    for i in range(n):
        day = f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}"
        bars.append(
            PriceBar(
                date=day,
                open=Decimal("150.00"),
                high=Decimal("155.00"),
                low=Decimal("148.00"),
                close=Decimal("152.00"),
                volume=50_000_000,  # 50M shares * ~$152 = ~$7.6B daily volume
            )
        )
    return bars


class TestFilterPipelineV2:
    """Tests for v2 multi-period pipeline path."""

    def test_pipeline_accepts_financial_history(self):
        """Pipeline should use multi-year checks when history is provided."""
        profile = _make_healthy_profile()

        # Build 3 periods with prior data so Beneish can compute M-Score
        prior_income = IncomeStatement(
            revenue=Decimal("90000000000"),
            ebit=Decimal("27000000000"),
            net_income=Decimal("18000000000"),
            interest_expense=Decimal("1000000000"),
            shares_outstanding=1000000000,
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("280000000000"),
            current_assets=Decimal("140000000000"),
            current_liabilities=Decimal("95000000000"),
            total_liabilities=Decimal("190000000000"),
            total_equity=Decimal("90000000000"),
            retained_earnings=Decimal("40000000000"),
            shares_outstanding=1000000000,
        )

        p1 = _make_period("2022-12-31", prior_income=prior_income, prior_balance=prior_balance)
        p2 = _make_period("2023-12-31", prior_income=p1.current_income, prior_balance=p1.current_balance)
        p3 = _make_period("2024-12-31", prior_income=p2.current_income, prior_balance=p2.current_balance)

        history = FinancialHistory(ticker="TEST", periods=[p1, p2, p3])

        result = run_elimination_filters(p3, profile, history=history)

        # Should still run all 6 filters
        assert len(result.results) == 6
        names = {r.name for r in result.results}
        assert names == {
            "liquidity",
            "beneish_m_score",
            "altman_z_score",
            "fcf_distress",
            "interest_coverage",
            "current_ratio",
        }

        # Beneish v2 should populate computed_metrics when using multi-period
        beneish_result = next(r for r in result.results if r.name == "beneish_m_score")
        assert beneish_result.computed_metrics is not None
        assert "current_m_score" in beneish_result.computed_metrics
        assert "historical_m_scores_count" in beneish_result.computed_metrics

        # FCF v2 should populate computed_metrics
        fcf_result = next(r for r in result.results if r.name == "fcf_distress")
        assert fcf_result.computed_metrics is not None
        assert "positive_years" in fcf_result.computed_metrics

        # Interest coverage v2 should populate computed_metrics
        ic_result = next(r for r in result.results if r.name == "interest_coverage")
        assert ic_result.computed_metrics is not None
        assert "median_icr" in ic_result.computed_metrics

        # Current ratio v2 should populate computed_metrics
        cr_result = next(r for r in result.results if r.name == "current_ratio")
        assert cr_result.computed_metrics is not None
        assert "median_cr" in cr_result.computed_metrics

    def test_pipeline_accepts_price_bars(self):
        """Pipeline should use v2 liquidity when price bars are provided."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        price_bars = _make_price_bars(100)

        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE, price_bars=price_bars)

        # Should still run all 6 filters
        assert len(result.results) == 6

        # Liquidity v2 should populate computed_metrics (vs v1 which does not)
        liq_result = next(r for r in result.results if r.name == "liquidity")
        assert liq_result.computed_metrics is not None
        assert "market_cap" in liq_result.computed_metrics

        # Other filters should use v1 (no history provided)
        beneish_result = next(r for r in result.results if r.name == "beneish_m_score")
        # v1 beneish does NOT set computed_metrics
        assert beneish_result.computed_metrics is None

    def test_pipeline_backward_compat_no_history(self):
        """Without history/price_bars, pipeline uses v1 filters (existing tests)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE)

        assert result.passed is True
        assert len(result.results) == 6
        names = {r.name for r in result.results}
        assert names == {
            "liquidity",
            "beneish_m_score",
            "altman_z_score",
            "fcf_distress",
            "interest_coverage",
            "current_ratio",
        }

        # v1 liquidity check does NOT produce computed_metrics
        liq_result = next(r for r in result.results if r.name == "liquidity")
        assert liq_result.computed_metrics is None

        # v1 beneish does NOT produce computed_metrics
        beneish_result = next(r for r in result.results if r.name == "beneish_m_score")
        assert beneish_result.computed_metrics is None

    def test_pipeline_with_both_history_and_price_bars(self):
        """Pipeline uses v2 for all applicable filters when both are provided."""
        profile = _make_healthy_profile()

        prior_income = IncomeStatement(
            revenue=Decimal("90000000000"),
            ebit=Decimal("27000000000"),
            net_income=Decimal("18000000000"),
            interest_expense=Decimal("1000000000"),
            shares_outstanding=1000000000,
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("280000000000"),
            current_assets=Decimal("140000000000"),
            current_liabilities=Decimal("95000000000"),
            total_liabilities=Decimal("190000000000"),
            total_equity=Decimal("90000000000"),
            retained_earnings=Decimal("40000000000"),
            shares_outstanding=1000000000,
        )

        p1 = _make_period("2022-12-31", prior_income=prior_income, prior_balance=prior_balance)
        p2 = _make_period("2023-12-31", prior_income=p1.current_income, prior_balance=p1.current_balance)
        p3 = _make_period("2024-12-31", prior_income=p2.current_income, prior_balance=p2.current_balance)

        history = FinancialHistory(ticker="TEST", periods=[p1, p2, p3])
        price_bars = _make_price_bars(100)

        result = run_elimination_filters(
            p3, profile, history=history, price_bars=price_bars
        )

        assert len(result.results) == 6

        # Liquidity should use v2 (has computed_metrics)
        liq_result = next(r for r in result.results if r.name == "liquidity")
        assert liq_result.computed_metrics is not None

        # Beneish should use v2 (has computed_metrics)
        beneish_result = next(r for r in result.results if r.name == "beneish_m_score")
        assert beneish_result.computed_metrics is not None

        # FCF should use v2 (has computed_metrics)
        fcf_result = next(r for r in result.results if r.name == "fcf_distress")
        assert fcf_result.computed_metrics is not None

        # Interest coverage should use v2 (has computed_metrics)
        ic_result = next(r for r in result.results if r.name == "interest_coverage")
        assert ic_result.computed_metrics is not None

        # Current ratio should use v2 (has computed_metrics)
        cr_result = next(r for r in result.results if r.name == "current_ratio")
        assert cr_result.computed_metrics is not None

    def test_pipeline_v2_still_runs_all_six_filters(self):
        """Even with v2, all 6 filter names are present and no extra filters appear."""
        profile = _make_healthy_profile()
        p1 = _make_period("2023-12-31")
        p2 = _make_period("2024-12-31")
        history = FinancialHistory(ticker="TEST", periods=[p1, p2])

        result = run_elimination_filters(p2, profile, history=history)

        assert len(result.results) == 6
        names = [r.name for r in result.results]
        assert names == [
            "liquidity",
            "beneish_m_score",
            "altman_z_score",
            "fcf_distress",
            "interest_coverage",
            "current_ratio",
        ]

    def test_pipeline_v2_config_flows_through(self):
        """Config parameter flows through to v2 filters."""
        profile = _make_healthy_profile()

        prior_income = IncomeStatement(
            revenue=Decimal("90000000000"),
            ebit=Decimal("27000000000"),
            net_income=Decimal("18000000000"),
            interest_expense=Decimal("1000000000"),
            shares_outstanding=1000000000,
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("280000000000"),
            current_assets=Decimal("140000000000"),
            current_liabilities=Decimal("95000000000"),
            total_liabilities=Decimal("190000000000"),
            total_equity=Decimal("90000000000"),
            retained_earnings=Decimal("40000000000"),
            shares_outstanding=1000000000,
        )

        p1 = _make_period("2022-12-31", prior_income=prior_income, prior_balance=prior_balance)
        p2 = _make_period("2023-12-31", prior_income=p1.current_income, prior_balance=p1.current_balance)

        history = FinancialHistory(ticker="TEST", periods=[p1, p2])

        # Use a very strict beneish threshold to force failure
        config = FilterConfig(beneish=BeneishConfig(threshold=-10.0))

        result = run_elimination_filters(p2, profile, config=config, history=history)

        beneish_result = next(r for r in result.results if r.name == "beneish_m_score")
        assert beneish_result.threshold == -10.0
        # M-Score should be well above -10.0, so it should FAIL
        assert beneish_result.passed is False
