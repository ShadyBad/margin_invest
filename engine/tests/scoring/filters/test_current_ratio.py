"""Tests for Current Ratio filter."""

from decimal import Decimal

import pytest
from margin_engine.config.filter_config import CurrentRatioConfig
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.filters.current_ratio import (
    current_ratio_check,
    current_ratio_check_v2,
)


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


class TestCurrentRatioWithConfig:
    """Tests for config-driven current ratio thresholds."""

    def test_config_parameter_accepted(self):
        """Config parameter should be accepted without error."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        config = CurrentRatioConfig()
        result = current_ratio_check(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY, config=config)
        assert result.passed is True

    def test_config_threshold_overrides_hardcoded(self):
        """Config default threshold should override the hardcoded 0.8.

        Apple CR is approx 0.87. With a stricter threshold of 1.0,
        Apple should FAIL because 0.87 < 1.0.
        """
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        strict_config = CurrentRatioConfig(
            default=1.0,
            sector_overrides={"information technology": 1.0},
        )
        result = current_ratio_check(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY, config=strict_config)
        assert result.passed is False
        assert result.threshold == 1.0

    def test_config_sector_overrides(self):
        """Config sector_overrides should override sector thresholds."""
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
        # CR = 0.7. Default utilities threshold is 0.6 (would pass).
        # Config sets utilities threshold to 0.8 (should fail).
        config = CurrentRatioConfig(
            default=0.8,
            sector_overrides={"utilities": 0.8},
        )
        result = current_ratio_check(period, sector=GICSSector.UTILITIES, config=config)
        assert result.passed is False
        assert result.threshold == 0.8

    def test_without_config_backward_compatible(self):
        """Without config, behavior matches original hardcoded thresholds."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = current_ratio_check(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True


def _make_period(
    current_assets: str,
    current_liabilities: str,
    period_end: str = "2024-09-28",
    cash_and_equivalents: str | None = None,
    receivables: str | None = None,
) -> FinancialPeriod:
    """Helper to build a FinancialPeriod with given balance sheet values."""
    balance = BalanceSheet(
        total_assets=Decimal("5000"),
        current_assets=Decimal(current_assets),
        current_liabilities=Decimal(current_liabilities),
        cash_and_equivalents=Decimal(cash_and_equivalents) if cash_and_equivalents else None,
        receivables=Decimal(receivables) if receivables else None,
        total_liabilities=Decimal("2000"),
        total_equity=Decimal("3000"),
        shares_outstanding=100,
    )
    income = IncomeStatement(
        revenue=Decimal("1000"),
        ebit=Decimal("100"),
        net_income=Decimal("50"),
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("80"),
        capital_expenditures=Decimal("-20"),
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


def _make_history(periods: list[FinancialPeriod], ticker: str = "TEST") -> FinancialHistory:
    """Helper to build a FinancialHistory from a list of periods."""
    return FinancialHistory(ticker=ticker, periods=periods)


class TestCurrentRatioV2:
    """Tests for multi-year current_ratio_check_v2."""

    def test_cr_3yr_median(self):
        """Uses 3-year median: CR values [1.2, 0.9, 1.0] -> median=1.0, passes threshold 0.8."""
        periods = [
            _make_period("1200", "1000", period_end="2022-09-28"),  # CR = 1.2
            _make_period("900", "1000", period_end="2023-09-28"),   # CR = 0.9
            _make_period("1000", "1000", period_end="2024-09-28"),  # CR = 1.0
        ]
        history = _make_history(periods)
        result = current_ratio_check_v2(history)

        assert result.passed is True
        assert result.name == "current_ratio"
        assert result.computed_metrics is not None
        assert result.computed_metrics["median_cr"] == pytest.approx(1.0)
        assert result.computed_metrics["current_cr"] == pytest.approx(1.0)

    def test_cr_quick_ratio_rescue(self):
        """CR < threshold but quick ratio > 0.5 -> PASS with warning.

        All 3 periods have CR = 0.6 (below 0.8 threshold), but the most recent
        period has cash_and_equivalents=300 + receivables=300 giving
        quick_ratio = 600/1000 = 0.6 > 0.5 rescue threshold.
        """
        periods = [
            _make_period("600", "1000", period_end="2022-09-28"),  # CR = 0.6
            _make_period("600", "1000", period_end="2023-09-28"),  # CR = 0.6
            _make_period(
                "600", "1000",
                period_end="2024-09-28",
                cash_and_equivalents="300",
                receivables="300",
            ),  # CR = 0.6, QR = 0.6
        ]
        history = _make_history(periods)
        result = current_ratio_check_v2(history)

        assert result.passed is True
        assert result.warning is True
        assert result.computed_metrics is not None
        assert result.computed_metrics["quick_ratio"] == pytest.approx(0.6)
        assert "quick ratio rescue" in result.detail.lower() or "rescue" in (result.warning_reason or "").lower()

    def test_cr_3yr_decline_guard(self):
        """>30% decline over 3 years triggers warning.

        CR values: [1.5, 1.2, 0.95] -> decline from 1.5 to 0.95 = 36.7%
        Median = 1.2 (passes threshold 0.8), but decline > 30% triggers warning.
        """
        periods = [
            _make_period("1500", "1000", period_end="2022-09-28"),  # CR = 1.5
            _make_period("1200", "1000", period_end="2023-09-28"),  # CR = 1.2
            _make_period("950", "1000", period_end="2024-09-28"),   # CR = 0.95
        ]
        history = _make_history(periods)
        result = current_ratio_check_v2(history)

        assert result.passed is True  # Median 1.2 > 0.8 threshold
        assert result.warning is True
        assert result.warning_reason is not None
        assert "decline" in result.warning_reason.lower()
        assert result.computed_metrics is not None
        decline = result.computed_metrics["decline_pct"]
        assert decline == pytest.approx(36.67, abs=0.5)

    def test_cr_single_period_backward_compat(self):
        """Old FinancialPeriod input still works via fallback."""
        period = _make_period("900", "1000")  # CR = 0.9
        result = current_ratio_check_v2(period)

        assert result.passed is True  # 0.9 > 0.8 threshold
        assert result.name == "current_ratio"
        assert result.value == pytest.approx(0.9)

    def test_cr_zero_liabilities_pass(self):
        """No current liabilities in all periods -> PASS."""
        periods = [
            _make_period("500", "0", period_end="2022-09-28"),
            _make_period("600", "0", period_end="2023-09-28"),
            _make_period("700", "0", period_end="2024-09-28"),
        ]
        history = _make_history(periods)
        result = current_ratio_check_v2(history)

        assert result.passed is True

    def test_cr_median_below_threshold_no_rescue(self):
        """CR below threshold and no quick ratio rescue -> FAIL."""
        periods = [
            _make_period("500", "1000", period_end="2022-09-28"),  # CR = 0.5
            _make_period("600", "1000", period_end="2023-09-28"),  # CR = 0.6
            _make_period("500", "1000", period_end="2024-09-28"),  # CR = 0.5
        ]
        history = _make_history(periods)
        result = current_ratio_check_v2(history)

        # Median = 0.5, below 0.8 threshold
        # No cash/receivables -> quick ratio = 0 -> no rescue
        assert result.passed is False
        assert result.computed_metrics is not None
        assert result.computed_metrics["median_cr"] == pytest.approx(0.5)

    def test_cr_quick_ratio_rescue_insufficient(self):
        """CR below threshold and quick ratio <= 0.5 -> FAIL (no rescue)."""
        periods = [
            _make_period(
                "600", "1000",
                period_end="2024-09-28",
                cash_and_equivalents="200",
                receivables="200",
            ),  # CR = 0.6, QR = 400/1000 = 0.4
        ]
        history = _make_history(periods)
        result = current_ratio_check_v2(history)

        assert result.passed is False
        assert result.computed_metrics is not None
        assert result.computed_metrics["quick_ratio"] == pytest.approx(0.4)

    def test_cr_v2_with_sector_config(self):
        """V2 respects sector overrides from config."""
        periods = [
            _make_period("650", "1000", period_end="2022-09-28"),  # CR = 0.65
            _make_period("700", "1000", period_end="2023-09-28"),  # CR = 0.7
            _make_period("650", "1000", period_end="2024-09-28"),  # CR = 0.65
        ]
        history = _make_history(periods)
        # Utilities threshold is 0.6 by default -> median 0.65 passes
        result = current_ratio_check_v2(history, sector=GICSSector.UTILITIES)
        assert result.passed is True
        assert result.computed_metrics is not None
        assert result.computed_metrics["median_cr"] == pytest.approx(0.65)

    def test_cr_v2_uses_only_3_most_recent_periods(self):
        """When more than 3 periods given, only use the 3 most recent."""
        periods = [
            _make_period("400", "1000", period_end="2020-09-28"),  # CR = 0.4 (old, excluded)
            _make_period("400", "1000", period_end="2021-09-28"),  # CR = 0.4 (old, excluded)
            _make_period("1200", "1000", period_end="2022-09-28"),  # CR = 1.2
            _make_period("1000", "1000", period_end="2023-09-28"),  # CR = 1.0
            _make_period("1100", "1000", period_end="2024-09-28"),  # CR = 1.1
        ]
        history = _make_history(periods)
        result = current_ratio_check_v2(history)

        # Should use [1.2, 1.0, 1.1] -> median = 1.1
        assert result.passed is True
        assert result.computed_metrics is not None
        assert result.computed_metrics["median_cr"] == pytest.approx(1.1)
        assert result.computed_metrics["periods_used"] == 3.0

    def test_cr_v2_decline_guard_no_warning_under_threshold(self):
        """Decline < 30% should NOT trigger warning."""
        periods = [
            _make_period("1200", "1000", period_end="2022-09-28"),  # CR = 1.2
            _make_period("1100", "1000", period_end="2023-09-28"),  # CR = 1.1
            _make_period("1000", "1000", period_end="2024-09-28"),  # CR = 1.0
        ]
        history = _make_history(periods)
        result = current_ratio_check_v2(history)

        # Decline from 1.2 to 1.0 = 16.7%, under 30% threshold
        assert result.passed is True
        assert result.warning is False
