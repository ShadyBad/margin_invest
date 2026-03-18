"""Tests for Beneish M-Score earnings manipulation filter."""

from decimal import Decimal

import pytest
from margin_engine.config.filter_config import BeneishConfig
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import FilterVerdict
from margin_engine.scoring.filters.beneish import beneish_m_score, beneish_m_score_v2


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


# ---------------------------------------------------------------------------
# Helper to build multi-period FinancialHistory for v2 tests
# ---------------------------------------------------------------------------


def _make_period(
    period_end: str,
    revenue_current: int,
    revenue_prior: int | None,
    receivables_current: int,
    receivables_prior: int | None,
    total_assets_current: int,
    total_assets_prior: int | None,
    net_income: int,
    operating_cf: int,
    gross_profit_current: int | None = None,
    gross_profit_prior: int | None = None,
    *,
    has_prior: bool = True,
) -> FinancialPeriod:
    """Build a FinancialPeriod with configurable current/prior data."""
    ci = IncomeStatement(
        revenue=Decimal(str(revenue_current)),
        cost_of_revenue=Decimal(
            str(revenue_current - (gross_profit_current or revenue_current // 2))
        ),
        gross_profit=Decimal(str(gross_profit_current or revenue_current // 2)),
        sga_expense=Decimal("100"),
        depreciation=Decimal("50"),
        ebit=Decimal(str(net_income + 50)),
        net_income=Decimal(str(net_income)),
        shares_outstanding=100,
    )
    cb = BalanceSheet(
        total_assets=Decimal(str(total_assets_current)),
        current_assets=Decimal(str(total_assets_current // 3)),
        receivables=Decimal(str(receivables_current)),
        total_liabilities=Decimal(str(total_assets_current // 2)),
        current_liabilities=Decimal(str(total_assets_current // 6)),
        long_term_debt=Decimal(str(total_assets_current // 5)),
        total_equity=Decimal(str(total_assets_current // 2)),
        pp_and_e=Decimal(str(total_assets_current // 4)),
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=Decimal(str(operating_cf)),
        capital_expenditures=Decimal("-30"),
    )

    pi = None
    pb = None
    if has_prior and revenue_prior is not None and total_assets_prior is not None:
        pi = IncomeStatement(
            revenue=Decimal(str(revenue_prior)),
            cost_of_revenue=Decimal(
                str(revenue_prior - (gross_profit_prior or revenue_prior // 2))
            ),
            gross_profit=Decimal(str(gross_profit_prior or revenue_prior // 2)),
            sga_expense=Decimal("100"),
            depreciation=Decimal("50"),
            ebit=Decimal(str(net_income - 10)),
            net_income=Decimal(str(net_income - 20)),
            shares_outstanding=100,
        )
        pb = BalanceSheet(
            total_assets=Decimal(str(total_assets_prior)),
            current_assets=Decimal(str(total_assets_prior // 3)),
            receivables=Decimal(str(receivables_prior or receivables_current)),
            total_liabilities=Decimal(str(total_assets_prior // 2)),
            current_liabilities=Decimal(str(total_assets_prior // 6)),
            long_term_debt=Decimal(str(total_assets_prior // 5)),
            total_equity=Decimal(str(total_assets_prior // 2)),
            pp_and_e=Decimal(str(total_assets_prior // 4)),
            shares_outstanding=100,
        )

    return FinancialPeriod(
        period_end=period_end,
        filing_date=period_end,
        current_income=ci,
        prior_income=pi,
        current_balance=cb,
        prior_balance=pb,
        current_cash_flow=cf,
    )


class TestBeneishMScoreV2:
    """Tests for multi-period Beneish M-Score (v2) with INCONCLUSIVE support."""

    def test_beneish_multi_period_computation(self):
        """Computes M-Score for each period that has prior data."""
        # Build 3 periods, each with prior data -> 3 computable M-Scores
        periods = [
            _make_period(
                "2022-09-30",
                1000,
                900,
                100,
                90,
                2000,
                1800,
                net_income=150,
                operating_cf=180,
            ),
            _make_period(
                "2023-09-30",
                1100,
                1000,
                110,
                100,
                2200,
                2000,
                net_income=160,
                operating_cf=190,
            ),
            _make_period(
                "2024-09-30",
                1200,
                1100,
                120,
                110,
                2400,
                2200,
                net_income=170,
                operating_cf=200,
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = beneish_m_score_v2(history)

        # Should produce a result
        assert result.name == "beneish_m_score"
        # Should have computed_metrics with historical_m_scores
        assert result.computed_metrics is not None
        assert "current_m_score" in result.computed_metrics
        assert "historical_m_scores_count" in result.computed_metrics
        # 3 periods each with prior data -> 3 M-Scores
        assert result.computed_metrics["historical_m_scores_count"] == 3.0
        # current_m_score should equal the most recent period's M-Score
        assert result.computed_metrics["current_m_score"] == result.value

    def test_beneish_inconclusive_no_prior(self):
        """Single period with no prior -> INCONCLUSIVE."""
        period = _make_period(
            "2024-09-30",
            1000,
            None,
            100,
            None,
            2000,
            None,
            net_income=150,
            operating_cf=180,
            has_prior=False,
        )
        history = FinancialHistory(ticker="TEST", periods=[period])
        result = beneish_m_score_v2(history)

        assert result.insufficient_data is True
        assert result.verdict == FilterVerdict.INCONCLUSIVE
        assert "insufficient" in result.detail.lower()

    def test_beneish_trend_detection(self):
        """M-Scores getting worse (closer to -1.78) -> deteriorating trend."""
        # Period 1: healthy company, low M-Score (well below -1.78)
        # Period 2: slightly worse M-Score (closer to -1.78)
        # Period 3: even worse M-Score (closer still to -1.78)
        # Achieve this by increasing receivables ratio and accruals over time
        periods = [
            _make_period(
                "2022-09-30",
                1000,
                900,
                80,
                72,
                2000,
                1800,
                net_income=150,
                operating_cf=200,
                gross_profit_current=500,
                gross_profit_prior=450,
            ),
            _make_period(
                "2023-09-30",
                1100,
                1000,
                150,
                80,
                2200,
                2000,
                net_income=180,
                operating_cf=160,  # accruals getting worse
                gross_profit_current=500,
                gross_profit_prior=500,
            ),
            _make_period(
                "2024-09-30",
                1200,
                1100,
                280,
                150,
                2400,
                2200,
                net_income=250,
                operating_cf=100,  # accruals much worse
                gross_profit_current=480,
                gross_profit_prior=500,
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = beneish_m_score_v2(history)

        assert result.computed_metrics is not None
        # Should detect deteriorating trend (M-Scores getting closer to -1.78)
        assert "trend" in result.computed_metrics
        assert result.computed_metrics["trend"] == 1.0  # 1.0 = deteriorating

    def test_beneish_backward_compat_single_period(self):
        """Still works with single FinancialPeriod input (delegates to v1)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result_v2 = beneish_m_score_v2(APPLE_PERIOD_2024)
        result_v1 = beneish_m_score(APPLE_PERIOD_2024)

        assert result_v2.passed == result_v1.passed
        assert result_v2.value == result_v1.value
        assert result_v2.verdict == result_v1.verdict

    def test_beneish_latest_fails(self):
        """Most recent M-Score above threshold -> FAIL."""
        # Build periods where the latest period has manipulator-like data
        periods = [
            # Period 1: normal company
            _make_period(
                "2022-09-30",
                1000,
                900,
                100,
                90,
                2000,
                1800,
                net_income=150,
                operating_cf=180,
                gross_profit_current=500,
                gross_profit_prior=450,
            ),
            # Period 2: heavy manipulation signals
            _make_period(
                "2023-09-30",
                1200,
                1000,
                480,
                100,
                2000,
                1800,
                net_income=400,
                operating_cf=50,  # huge accruals
                gross_profit_current=300,
                gross_profit_prior=500,
            ),
        ]
        history = FinancialHistory(ticker="MANIP", periods=periods)
        result = beneish_m_score_v2(history)

        assert result.passed is False
        assert result.verdict == FilterVerdict.FAIL
        assert result.value is not None
        assert result.value > -1.78

    def test_beneish_v2_with_history_all_periods_no_prior(self):
        """Multiple periods but none have prior data -> INCONCLUSIVE."""
        periods = [
            _make_period(
                "2022-09-30",
                1000,
                None,
                100,
                None,
                2000,
                None,
                net_income=150,
                operating_cf=180,
                has_prior=False,
            ),
            _make_period(
                "2023-09-30",
                1100,
                None,
                110,
                None,
                2200,
                None,
                net_income=160,
                operating_cf=190,
                has_prior=False,
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = beneish_m_score_v2(history)

        assert result.insufficient_data is True
        assert result.verdict == FilterVerdict.INCONCLUSIVE

    def test_beneish_v2_config_threshold(self):
        """Config threshold should be respected in v2."""
        periods = [
            _make_period(
                "2022-09-30",
                1000,
                900,
                100,
                90,
                2000,
                1800,
                net_income=150,
                operating_cf=180,
            ),
            _make_period(
                "2023-09-30",
                1100,
                1000,
                110,
                100,
                2200,
                2000,
                net_income=160,
                operating_cf=190,
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)

        # Default threshold
        result_default = beneish_m_score_v2(history)
        assert result_default.threshold == -1.78

        # Very strict threshold: should cause FAIL for most companies
        strict_config = BeneishConfig(threshold=-10.0)
        result_strict = beneish_m_score_v2(history, config=strict_config)
        assert result_strict.threshold == -10.0
        assert result_strict.passed is False  # Virtually no company would pass -10.0

    def test_beneish_v2_stable_trend(self):
        """M-Scores not deteriorating -> stable trend."""
        # All periods have similar healthy data -> stable M-Scores
        periods = [
            _make_period(
                "2022-09-30",
                1000,
                900,
                100,
                90,
                2000,
                1800,
                net_income=150,
                operating_cf=180,
                gross_profit_current=500,
                gross_profit_prior=450,
            ),
            _make_period(
                "2023-09-30",
                1100,
                1000,
                110,
                100,
                2200,
                2000,
                net_income=165,
                operating_cf=198,
                gross_profit_current=550,
                gross_profit_prior=500,
            ),
            _make_period(
                "2024-09-30",
                1200,
                1100,
                120,
                110,
                2400,
                2200,
                net_income=180,
                operating_cf=216,
                gross_profit_current=600,
                gross_profit_prior=550,
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = beneish_m_score_v2(history)

        assert result.computed_metrics is not None
        # Stable company -> trend should be 0.0 (stable)
        assert result.computed_metrics["trend"] == 0.0


class TestBeneishSectorExemption:
    """Tests for sector exemption in Beneish M-Score filter."""

    def test_financials_exempt_v1(self):
        """Financials sector should be exempt from Beneish M-Score (v1)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        config = BeneishConfig()
        result = beneish_m_score(
            APPLE_PERIOD_2024,
            config=config,
            sector=GICSSector.FINANCIALS,
        )
        assert result.passed is True
        assert "exempt" in result.detail.lower()

    def test_real_estate_exempt_v1(self):
        """Real Estate sector should be exempt from Beneish M-Score (v1)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        config = BeneishConfig()
        result = beneish_m_score(
            APPLE_PERIOD_2024,
            config=config,
            sector=GICSSector.REAL_ESTATE,
        )
        assert result.passed is True
        assert "exempt" in result.detail.lower()

    def test_financials_exempt_v2(self):
        """Financials sector should be exempt from Beneish M-Score (v2)."""
        periods = [
            _make_period(
                "2023-09-30",
                1200,
                1000,
                480,
                100,
                2000,
                1800,
                net_income=400,
                operating_cf=50,
                gross_profit_current=300,
                gross_profit_prior=500,
            ),
        ]
        history = FinancialHistory(ticker="BANK", periods=periods)
        result = beneish_m_score_v2(
            history,
            config=BeneishConfig(),
            sector=GICSSector.FINANCIALS,
        )
        assert result.passed is True
        assert "exempt" in result.detail.lower()

    def test_real_estate_exempt_v2(self):
        """Real Estate sector should be exempt from Beneish M-Score (v2)."""
        periods = [
            _make_period(
                "2023-09-30",
                1200,
                1000,
                480,
                100,
                2000,
                1800,
                net_income=400,
                operating_cf=50,
                gross_profit_current=300,
                gross_profit_prior=500,
            ),
        ]
        history = FinancialHistory(ticker="REIT", periods=periods)
        result = beneish_m_score_v2(
            history,
            config=BeneishConfig(),
            sector=GICSSector.REAL_ESTATE,
        )
        assert result.passed is True
        assert "exempt" in result.detail.lower()

    def test_technology_not_exempt(self):
        """Technology sector should NOT be exempt from Beneish M-Score."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        config = BeneishConfig()
        result = beneish_m_score(
            APPLE_PERIOD_2024,
            config=config,
            sector=GICSSector.TECHNOLOGY,
        )
        # Should compute normally, not be exempt
        assert "exempt" not in result.detail.lower()

    def test_default_config_exempt_sectors(self):
        """Default BeneishConfig should exempt Financials and Real Estate."""
        config = BeneishConfig()
        assert "Financials" in config.exempt_sectors
        assert "Real Estate" in config.exempt_sectors

    def test_custom_exempt_sectors(self):
        """Custom exempt_sectors should override defaults."""
        config = BeneishConfig(exempt_sectors=["Utilities"])
        assert "Financials" not in config.exempt_sectors
        assert "Utilities" in config.exempt_sectors
