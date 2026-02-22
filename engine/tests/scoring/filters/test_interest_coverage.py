"""Tests for Interest Coverage Ratio filter."""

from decimal import Decimal

import pytest
from margin_engine.config.filter_config import InterestCoverageConfig
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.filters.interest_coverage import (
    interest_coverage_check,
    interest_coverage_check_v2,
)


class TestInterestCoverage:
    def test_apple_passes(self):
        """Apple FY2024 with ICR ~34x should PASS for Technology."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = interest_coverage_check(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True
        assert result.value == pytest.approx(34.21, abs=0.1)

    def test_low_coverage_fails_tech(self):
        """Company with ICR = 2.0 should FAIL for Technology (threshold > 5.0)."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            interest_expense=Decimal("50"),
            net_income=Decimal("30"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
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
        result = interest_coverage_check(period, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False
        assert result.value == pytest.approx(2.0)

    def test_same_coverage_passes_default(self):
        """ICR = 2.0 should PASS for non-tech default threshold (> 1.5)."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            interest_expense=Decimal("50"),
            net_income=Decimal("30"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
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
        result = interest_coverage_check(period, sector=GICSSector.CONSUMER_STAPLES)
        assert result.passed is True

    def test_no_interest_expense_passes(self):
        """No interest expense means no debt service -> PASS."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            net_income=Decimal("80"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
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
        result = interest_coverage_check(period)
        assert result.passed is True

    def test_utilities_lower_threshold(self):
        """Utilities have a lower threshold of 1.2."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("130"),
            interest_expense=Decimal("100"),
            net_income=Decimal("20"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("5000"),
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
        # ICR = 130/100 = 1.3, passes utilities threshold of 1.2
        result = interest_coverage_check(period, sector=GICSSector.UTILITIES)
        assert result.passed is True
        assert result.value == pytest.approx(1.3)

    def test_filter_name(self):
        """Filter should have correct name."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = interest_coverage_check(APPLE_PERIOD_2024)
        assert result.name == "interest_coverage"


class TestInterestCoverageWithConfig:
    """Tests for config-driven interest coverage thresholds."""

    def test_config_parameter_accepted(self):
        """Config parameter should be accepted without error."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        config = InterestCoverageConfig()
        result = interest_coverage_check(
            APPLE_PERIOD_2024,
            sector=GICSSector.TECHNOLOGY,
            config=config,
        )
        assert result.passed is True

    def test_config_threshold_overrides_hardcoded(self):
        """Config default threshold should override the hardcoded 1.5.

        ICR = 2.0 passes default threshold of 1.5 but should fail with
        a stricter config threshold of 2.5.
        """
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            interest_expense=Decimal("50"),
            net_income=Decimal("30"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
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
        # ICR = 100/50 = 2.0, passes default 1.5 but fails config 2.5
        config = InterestCoverageConfig(default=2.5, sector_overrides={})
        result = interest_coverage_check(period, sector=GICSSector.CONSUMER_STAPLES, config=config)
        assert result.passed is False
        assert result.threshold == 2.5

    def test_config_sector_overrides(self):
        """Config sector_overrides should override sector thresholds."""
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            interest_expense=Decimal("50"),
            net_income=Decimal("30"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("800"),
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
        # ICR = 2.0. Default tech threshold is 5.0 (would fail).
        # Config sets "information technology" threshold to 1.5 (should pass).
        config = InterestCoverageConfig(
            default=1.5,
            sector_overrides={"information technology": 1.5},
        )
        result = interest_coverage_check(period, sector=GICSSector.TECHNOLOGY, config=config)
        assert result.passed is True
        assert result.threshold == 1.5

    def test_without_config_backward_compatible(self):
        """Without config, behavior matches original hardcoded thresholds."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = interest_coverage_check(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True


# --- Helpers for v2 tests ---


def _make_period(ebit: float, interest_expense: float | None, year: int = 2024) -> FinancialPeriod:
    """Create a minimal FinancialPeriod with given EBIT and interest expense."""
    ie = Decimal(str(interest_expense)) if interest_expense is not None else None
    income = IncomeStatement(
        revenue=Decimal("1000"),
        ebit=Decimal(str(ebit)),
        interest_expense=ie,
        net_income=Decimal("30"),
        shares_outstanding=100,
    )
    balance = BalanceSheet(
        total_assets=Decimal("2000"),
        total_equity=Decimal("800"),
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("80"),
        capital_expenditures=Decimal("-20"),
    )
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


def _make_icr_history(
    icr_values: list[float],
    interest_expense: float = 100.0,
    ticker: str = "TEST",
) -> FinancialHistory:
    """Build a FinancialHistory from desired ICR values.

    Each ICR value is achieved by setting EBIT = icr * interest_expense.
    Periods are created with ascending year dates.
    """
    periods = []
    base_year = 2024 - len(icr_values) + 1
    for i, icr in enumerate(icr_values):
        ebit = icr * interest_expense
        periods.append(_make_period(ebit, interest_expense, year=base_year + i))
    return FinancialHistory(ticker=ticker, periods=periods)


class TestInterestCoverageV2:
    """Tests for multi-year interest_coverage_check_v2."""

    def test_icr_3yr_median(self):
        """Uses 3-year median, not spot value."""
        # ICR values: [5.0, 2.5, 3.0] -> median 3.0, passes Industrials threshold 1.5
        history = _make_icr_history([5.0, 2.5, 3.0])
        result = interest_coverage_check_v2(history, sector=GICSSector.INDUSTRIALS)
        assert result.passed is True
        assert result.computed_metrics is not None
        assert result.computed_metrics["median_icr"] == pytest.approx(3.0, abs=0.01)
        assert result.value == pytest.approx(3.0, abs=0.01)

    def test_icr_trend_guard(self):
        """Current ICR >20% below median triggers warning."""
        # ICR values: [4.0, 3.5, 2.5] -> median 3.5, current 2.5
        # decline = (3.5 - 2.5) / 3.5 = 0.2857 = ~28%
        history = _make_icr_history([4.0, 3.5, 2.5])
        result = interest_coverage_check_v2(history, sector=GICSSector.INDUSTRIALS)
        assert result.passed is True  # median 3.5 > 1.5 threshold
        assert result.warning is True
        assert result.warning_reason == "ICR deteriorating"
        assert result.computed_metrics is not None
        assert result.computed_metrics["decline_pct"] == pytest.approx(0.2857, abs=0.01)

    def test_icr_negative_ebit_auto_fail(self):
        """Negative EBIT with interest expense = auto FAIL."""
        # Build history: two good years, then negative EBIT
        periods = [
            _make_period(ebit=300.0, interest_expense=100.0, year=2022),
            _make_period(ebit=250.0, interest_expense=100.0, year=2023),
            _make_period(ebit=-50.0, interest_expense=100.0, year=2024),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = interest_coverage_check_v2(history, sector=GICSSector.INDUSTRIALS)
        assert result.passed is False
        assert "negative EBIT" in result.detail

    def test_icr_expanded_sector_thresholds(self):
        """Tech requires ICR > 5.0, not the old 3.0."""
        history = _make_icr_history([4.5, 4.0, 4.8])  # median = 4.5
        result = interest_coverage_check_v2(history, sector=GICSSector.TECHNOLOGY)
        assert not result.passed  # 4.5 < 5.0 new tech threshold

    def test_icr_no_interest_expense_pass(self):
        """No interest expense -> PASS (no debt service)."""
        periods = [
            _make_period(ebit=200.0, interest_expense=None, year=2022),
            _make_period(ebit=250.0, interest_expense=None, year=2023),
            _make_period(ebit=300.0, interest_expense=None, year=2024),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = interest_coverage_check_v2(history, sector=GICSSector.INDUSTRIALS)
        assert result.passed is True

    def test_icr_single_period_backward_compat(self):
        """Old FinancialPeriod input still works via v2 entry point."""
        period = _make_period(ebit=300.0, interest_expense=100.0)
        # ICR = 3.0, passes Industrials threshold 1.5
        result = interest_coverage_check_v2(period, sector=GICSSector.INDUSTRIALS)
        assert result.passed is True
        assert result.value == pytest.approx(3.0)
        assert result.name == "interest_coverage"
