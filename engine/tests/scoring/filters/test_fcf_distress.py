"""Tests for FCF distress check filter."""

from decimal import Decimal

from margin_engine.config.filter_config import FcfDistressConfig
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import FilterVerdict
from margin_engine.scoring.filters.fcf_distress import (
    fcf_distress_check,
    fcf_distress_check_v2,
)


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


class TestFcfDistressConfigSectorOverrides:
    """Tests for sector-specific FCF margin overrides in config."""

    def test_default_min_fcf_margin_is_zero(self):
        """Default min_fcf_margin should be 0.0 (not -0.05)."""
        config = FcfDistressConfig()
        assert config.min_fcf_margin == 0.0

    def test_get_min_fcf_margin_returns_sector_override(self):
        """get_min_fcf_margin returns the sector-specific floor when available."""
        config = FcfDistressConfig()
        assert config.get_min_fcf_margin("information technology") == 0.10

    def test_get_min_fcf_margin_returns_default_for_unknown(self):
        """get_min_fcf_margin falls back to min_fcf_margin for unknown sectors."""
        config = FcfDistressConfig()
        assert config.get_min_fcf_margin("unknown sector") == 0.0

    def test_get_min_fcf_margin_returns_default_for_none(self):
        """get_min_fcf_margin falls back to min_fcf_margin when sector is None."""
        config = FcfDistressConfig()
        assert config.get_min_fcf_margin(None) == 0.0

    def test_sector_margin_overrides_all_sectors(self):
        """All 9 scoreable GICS sectors should have explicit overrides."""
        config = FcfDistressConfig()
        expected_sectors = {
            "information technology",
            "communication services",
            "health care",
            "consumer staples",
            "consumer discretionary",
            "industrials",
            "materials",
            "energy",
            "utilities",
        }
        assert set(config.sector_margin_overrides.keys()) == expected_sectors

    def test_get_min_fcf_margin_case_insensitive(self):
        """Sector lookup should be case-insensitive."""
        config = FcfDistressConfig()
        assert config.get_min_fcf_margin("Information Technology") == 0.10
        assert config.get_min_fcf_margin("INFORMATION TECHNOLOGY") == 0.10

    def test_custom_override_via_config(self):
        """Custom sector_margin_overrides should work."""
        config = FcfDistressConfig(sector_margin_overrides={"energy": 0.05})
        assert config.get_min_fcf_margin("energy") == 0.05


class TestFCFDistressWithConfig:
    """Tests for config-driven FCF distress thresholds."""

    def test_config_parameter_accepted(self):
        """Config parameter should be accepted without error."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        config = FcfDistressConfig()
        result = fcf_distress_check(APPLE_PERIOD_2024, config=config)
        assert result.passed is True

    def test_without_config_backward_compatible(self):
        """Without config, behavior matches original hardcoded thresholds."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = fcf_distress_check(APPLE_PERIOD_2024)
        assert result.passed is True
        assert result.threshold == 0.0

    def test_config_does_not_change_single_period_behavior(self):
        """Config multi-year fields are accepted but don't change single-period check."""
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
            capital_expenditures=Decimal("-50"),  # FCF = -20
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        # Even with generous config settings, single-period negative FCF still fails
        config = FcfDistressConfig(
            positive_years_required=1,
            lookback_years=1,
            min_fcf_margin=-0.10,
        )
        result = fcf_distress_check(period, config=config)
        assert result.passed is False


# --- Helper to build FinancialPeriod with specific FCF and revenue ---


def _make_period(
    fcf: float,
    revenue: float = 1000.0,
    year: int = 2020,
) -> FinancialPeriod:
    """Build a FinancialPeriod with the given FCF (op_cf + capex) and revenue."""
    # Split FCF into operating CF and capex. Keep capex as negative portion.
    if fcf >= 0:
        op_cf = Decimal(str(fcf + 100))
        capex = Decimal("-100")
    else:
        op_cf = Decimal("100")
        capex = Decimal(str(fcf - 100))  # e.g. fcf=-200 → capex=-300

    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            ebit=Decimal("50"),
            net_income=Decimal("20"),
            shares_outstanding=100,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("1000"),
            total_equity=Decimal("500"),
            shares_outstanding=100,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=op_cf,
            capital_expenditures=capex,
        ),
    )


def _make_history(
    fcf_values: list[float],
    revenues: list[float] | None = None,
    ticker: str = "TEST",
) -> FinancialHistory:
    """Build a FinancialHistory from a list of FCF values (one per year)."""
    if revenues is None:
        revenues = [1000.0] * len(fcf_values)
    periods = [
        _make_period(fcf=fcf, revenue=rev, year=2020 + i)
        for i, (fcf, rev) in enumerate(zip(fcf_values, revenues))
    ]
    return FinancialHistory(ticker=ticker, periods=periods)


class TestFCFDistressV2MultiYear:
    """Tests for the multi-year fcf_distress_check_v2."""

    def test_fcf_distress_3_of_5_positive(self):
        """3 of 5 years positive FCF should PASS."""
        # 3 positive, 2 negative
        history = _make_history([100, -50, 200, -30, 150])
        result = fcf_distress_check_v2(history)
        assert result.passed is True
        assert result.name == "fcf_distress"
        assert result.computed_metrics is not None
        assert result.computed_metrics["positive_years"] == 3
        assert result.computed_metrics["total_years"] == 5

    def test_fcf_distress_1_of_5_positive(self):
        """Only 1 of 5 years positive should FAIL."""
        # No improving trend at the end: -30 then -200 is worsening
        history = _make_history([150, -50, -100, -30, -200])
        result = fcf_distress_check_v2(history)
        assert result.passed is False
        assert result.verdict == FilterVerdict.FAIL
        assert result.computed_metrics is not None
        assert result.computed_metrics["positive_years"] == 1

    def test_fcf_distress_2_of_5_positive_non_cyclical(self):
        """2 of 5 positive should FAIL for non-cyclical sector (default threshold=3)."""
        # No improving trend: last two values go down (150 -> -200)
        history = _make_history([100, -50, 150, -30, -200])
        result = fcf_distress_check_v2(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False

    def test_fcf_distress_5_of_5_positive(self):
        """All 5 years positive should PASS easily."""
        history = _make_history([100, 200, 150, 300, 250])
        result = fcf_distress_check_v2(history)
        assert result.passed is True
        assert result.computed_metrics["positive_years"] == 5

    def test_fcf_distress_positive_trend_rescue(self):
        """Negative but improving for 2+ years -> WARNING, not FAIL."""
        # FCF values: all negative, but consistently improving
        # Use high revenue (10000) so median FCF margin stays above floor
        # Margins: -200/10000=-2%, -150/10000=-1.5%, -80/10000=-0.8%, etc.
        # Explicit permissive floor so the margin check doesn't block the trend rescue
        config = FcfDistressConfig(min_fcf_margin=-0.05, sector_margin_overrides={})
        history = _make_history(
            [-200, -150, -80, -30, -10],
            revenues=[10000, 10000, 10000, 10000, 10000],
        )
        result = fcf_distress_check_v2(history, config=config)
        assert result.passed is True
        assert result.warning is True
        assert result.warning_reason is not None
        assert "trend" in result.warning_reason.lower()
        assert result.computed_metrics is not None
        assert result.computed_metrics["positive_years"] == 0
        assert result.computed_metrics["consecutive_improving_years"] >= 2

    def test_fcf_distress_positive_trend_rescue_disabled(self):
        """Trend rescue disabled via config should FAIL despite improving trend."""
        history = _make_history([-200, -150, -80, -30, -10])
        config = FcfDistressConfig(allow_positive_trend_rescue=False)
        result = fcf_distress_check_v2(history, config=config)
        assert result.passed is False

    def test_fcf_distress_no_trend_rescue_when_worsening(self):
        """Worsening FCF trend should not rescue. Negative and getting worse -> FAIL."""
        history = _make_history([-10, -30, -80, -150, -200])
        result = fcf_distress_check_v2(history)
        assert result.passed is False

    def test_fcf_distress_cyclical_relaxed(self):
        """Energy sector uses 2-of-5 instead of 3-of-5."""
        # 2 positive out of 5 — would FAIL for non-cyclical (needs 3), PASS for cyclical (needs 2)
        # Explicit permissive floor so the margin check doesn't interfere
        config = FcfDistressConfig(min_fcf_margin=-0.25, sector_margin_overrides={})
        history = _make_history([100, -50, -200, -30, 150])
        result = fcf_distress_check_v2(history, config=config, sector=GICSSector.ENERGY)
        assert result.passed is True
        assert result.computed_metrics["positive_years"] == 2

    def test_fcf_distress_cyclical_materials(self):
        """Materials sector also uses cyclical relaxation."""
        config = FcfDistressConfig(min_fcf_margin=-0.25, sector_margin_overrides={})
        history = _make_history([100, -50, -200, -30, 150])
        result = fcf_distress_check_v2(history, config=config, sector=GICSSector.MATERIALS)
        assert result.passed is True

    def test_fcf_distress_cyclical_industrials(self):
        """Industrials sector also uses cyclical relaxation."""
        config = FcfDistressConfig(min_fcf_margin=-0.25, sector_margin_overrides={})
        history = _make_history([100, -50, -200, -30, 150])
        result = fcf_distress_check_v2(history, config=config, sector=GICSSector.INDUSTRIALS)
        assert result.passed is True

    def test_fcf_distress_cyclical_consumer_discretionary(self):
        """Consumer Discretionary sector also uses cyclical relaxation."""
        config = FcfDistressConfig(min_fcf_margin=-0.25, sector_margin_overrides={})
        history = _make_history([100, -50, -200, -30, 150])
        result = fcf_distress_check_v2(
            history, config=config, sector=GICSSector.CONSUMER_DISCRETIONARY
        )
        assert result.passed is True

    def test_fcf_distress_cyclical_still_fails_with_1_of_5(self):
        """Even cyclical sectors need 2 of 5 -- 1 of 5 should FAIL."""
        # No improving trend: end goes from 150 -> -100 (worsening)
        history = _make_history([150, -50, -30, -200, -100])
        result = fcf_distress_check_v2(history, sector=GICSSector.ENERGY)
        assert result.passed is False

    def test_fcf_margin_floor(self):
        """Median FCF margin below -5% should FAIL regardless of positive count."""
        # 3 of 5 positive FCF — would normally pass the count check
        # But margins: FCF/revenue = -60/1000, -50/1000, 10/1000, 20/1000, 30/1000
        # Sorted margins: -0.06, -0.05, 0.01, 0.02, 0.03 → median = 0.01
        # That would pass. Let's make it fail:
        # Very negative margins: FCF/revenue much more negative
        # [-600, -500, -400, 10, 20] / 1000 each → margins: -0.6, -0.5, -0.4, 0.01, 0.02
        # median = -0.4 → below -0.05 → FAIL
        history = _make_history([-600, -500, -400, 10, 20])
        result = fcf_distress_check_v2(history)
        assert result.passed is False
        assert result.computed_metrics is not None
        assert result.computed_metrics["median_fcf_margin"] < -0.05

    def test_fcf_margin_floor_borderline_pass(self):
        """Median FCF margin at exactly the floor should PASS (>=, not >)."""
        # Explicitly set floor to -0.05 to test the >= boundary
        config = FcfDistressConfig(min_fcf_margin=-0.05, sector_margin_overrides={})
        history = _make_history([-100, -50, -50, 20, 100])
        result = fcf_distress_check_v2(history, config=config)
        assert result.passed is True

    def test_fcf_single_period_backward_compat(self):
        """Old FinancialPeriod input still works with v2 function."""
        period = _make_period(fcf=100, revenue=1000)
        result = fcf_distress_check_v2(period)
        assert result.passed is True
        assert result.name == "fcf_distress"

    def test_fcf_single_period_negative_backward_compat(self):
        """Single FinancialPeriod with negative FCF still fails in v2."""
        period = _make_period(fcf=-20, revenue=1000)
        result = fcf_distress_check_v2(period)
        assert result.passed is False

    def test_lookback_years_truncation(self):
        """When history has more periods than lookback_years, use only the most recent."""
        # 7 years of data, lookback=5 means use last 5 only
        # Last 5 years: [100, -50, 200, -30, 150] → 3 of 5 positive → PASS
        history = _make_history([-999, -999, 100, -50, 200, -30, 150])
        config = FcfDistressConfig(lookback_years=5, positive_years_required=3)
        result = fcf_distress_check_v2(history, config=config)
        assert result.passed is True
        assert result.computed_metrics["total_years"] == 5

    def test_fewer_periods_than_lookback(self):
        """When history has fewer periods than lookback, use all available."""
        # Only 3 years, lookback=5 — use all 3
        history = _make_history([100, 200, 150])
        config = FcfDistressConfig(lookback_years=5, positive_years_required=3)
        result = fcf_distress_check_v2(history, config=config)
        assert result.passed is True
        assert result.computed_metrics["total_years"] == 3

    def test_custom_config_thresholds(self):
        """Custom config positive_years_required=4 should FAIL with only 3 positive."""
        history = _make_history([100, -50, 200, -30, 150])  # 3 positive
        config = FcfDistressConfig(positive_years_required=4)
        result = fcf_distress_check_v2(history, config=config)
        assert result.passed is False

    def test_computed_metrics_populated(self):
        """Verify all expected computed_metrics keys are present."""
        history = _make_history([100, -50, 200, -30, 150])
        result = fcf_distress_check_v2(history)
        assert result.computed_metrics is not None
        assert "positive_years" in result.computed_metrics
        assert "total_years" in result.computed_metrics
        assert "positive_years_required" in result.computed_metrics
        assert "median_fcf_margin" in result.computed_metrics
        assert "consecutive_improving_years" in result.computed_metrics
