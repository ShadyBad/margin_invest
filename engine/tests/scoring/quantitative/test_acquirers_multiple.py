"""Tests for Acquirer's Multiple (EV/EBIT) value factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.acquirers_multiple import acquirers_multiple


class TestAcquirersMultiple:
    def test_apple_golden_value(self):
        """Apple FY2024: EV/EBIT = 3,587,747,000,000 / 122,571,000,000 ~ 29.2708."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = acquirers_multiple(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.raw_value == pytest.approx(29.2708, rel=1e-3)

    def test_name(self):
        """Factor name should be 'acquirers_multiple'."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = acquirers_multiple(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.name == "acquirers_multiple"

    def test_percentile_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = acquirers_multiple(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.percentile_rank == 0.0

    def test_negative_ebit(self):
        """When EBIT < 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            ebit=Decimal("-5000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("2000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = acquirers_multiple(period, Decimal("100000"))
        assert result.raw_value == 0.0
        assert "non-positive" in result.detail.lower() or "ebit" in result.detail.lower()

    def test_zero_ebit(self):
        """When EBIT = 0 exactly, raw_value should be 0.0."""
        period = _make_period(
            ebit=Decimal("0"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("2000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = acquirers_multiple(period, Decimal("100000"))
        assert result.raw_value == 0.0

    def test_zero_market_cap(self):
        """When market_cap <= 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            ebit=Decimal("10000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("3000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = acquirers_multiple(period, Decimal("0"))
        assert result.raw_value == 0.0
        assert "market cap" in result.detail.lower()

    def test_negative_market_cap(self):
        """When market_cap < 0, raw_value should be 0.0."""
        period = _make_period(
            ebit=Decimal("10000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("3000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = acquirers_multiple(period, Decimal("-100"))
        assert result.raw_value == 0.0

    def test_detail_contains_key_values(self):
        """Detail string should contain EV, EBIT, and the ratio."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = acquirers_multiple(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert "3587747000000" in result.detail
        assert "122571000000" in result.detail
        assert "29.27" in result.detail

    def test_simple_synthetic_computation(self):
        """Verify computation with simple synthetic values.

        market_cap=100, total_debt=30 (LTD=20 + STD=10), cash=10 -> EV=120
        EBIT=15
        EV/EBIT = 120/15 = 8.0
        """
        period = _make_period(
            ebit=Decimal("15"),
            short_term_debt=Decimal("10"),
            long_term_debt=Decimal("20"),
            cash_and_equivalents=Decimal("10"),
        )
        result = acquirers_multiple(period, Decimal("100"))
        assert result.raw_value == pytest.approx(8.0, rel=1e-3)

    def test_none_cash_treated_as_zero(self):
        """When cash_and_equivalents is None, treat as 0."""
        period = _make_period(
            ebit=Decimal("10"),
            short_term_debt=Decimal("5"),
            long_term_debt=Decimal("15"),
            cash_and_equivalents=None,
        )
        # EV = 100 + 20 - 0 = 120, EV/EBIT = 120/10 = 12.0
        result = acquirers_multiple(period, Decimal("100"))
        assert result.raw_value == pytest.approx(12.0, rel=1e-3)


class TestCyclicalNormalization:
    """Tests for cyclical EBIT normalization in Acquirer's Multiple."""

    def test_cyclical_uses_median_ebit(self):
        """Cyclical company should use 7-year median EBIT instead of current.

        History EBIT: [80, 90, 100, 110, 120, 130, 140] -> median = 110
        Current period EBIT = 200 (peak), but median 110 should be used.
        market_cap=1000, debt=200, cash=100 -> EV=1100
        EV/median_EBIT = 1100 / 110 = 10.0
        """
        ebit_values = [80, 90, 100, 110, 120, 130, 140]
        history = _make_history("XOM", ebit_values)
        profile = AssetProfile(
            ticker="XOM",
            name="Exxon Mobil",
            sector=GICSSector.ENERGY,
            market_cap=Decimal("1000"),
        )
        # Current period has peak EBIT=200
        period = _make_period(
            ebit=Decimal("200"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        result = acquirers_multiple(period, Decimal("1000"), history=history, profile=profile)
        # EV = 1000 + 200 - 100 = 1100; median EBIT = 110; ratio = 10.0
        assert result.raw_value == pytest.approx(10.0, rel=1e-3)
        assert "cyclical_norm" in result.detail
        assert "7yr_median" in result.detail

    def test_non_cyclical_ignores_normalization(self):
        """Non-cyclical company should use current EBIT even with history provided.

        Current EBIT=200, history median=110.
        market_cap=1000, debt=200, cash=100 -> EV=1100
        EV/EBIT = 1100 / 200 = 5.5
        """
        ebit_values = [80, 90, 100, 110, 120, 130, 140]
        history = _make_history("MSFT", ebit_values)
        profile = AssetProfile(
            ticker="MSFT",
            name="Microsoft",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("1000"),
        )
        period = _make_period(
            ebit=Decimal("200"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        result = acquirers_multiple(period, Decimal("1000"), history=history, profile=profile)
        # EV = 1100; current EBIT = 200; ratio = 5.5
        assert result.raw_value == pytest.approx(5.5, rel=1e-3)
        assert "cyclical_norm" not in result.detail

    def test_no_history_backward_compatible(self):
        """Without history/profile params, behaves identically to original.

        Current EBIT=200.
        market_cap=1000, debt=200, cash=100 -> EV=1100
        EV/EBIT = 1100 / 200 = 5.5
        """
        period = _make_period(
            ebit=Decimal("200"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        result = acquirers_multiple(period, Decimal("1000"))
        assert result.raw_value == pytest.approx(5.5, rel=1e-3)
        assert "cyclical_norm" not in result.detail

    def test_cyclical_insufficient_history_uses_current(self):
        """Cyclical company with < 3 periods falls back to current EBIT.

        normalize_metric requires >= 3 periods for meaningful median.
        """
        ebit_values = [80, 90]  # Only 2 periods
        history = _make_history("XOM", ebit_values)
        profile = AssetProfile(
            ticker="XOM",
            name="Exxon Mobil",
            sector=GICSSector.ENERGY,
            market_cap=Decimal("1000"),
        )
        period = _make_period(
            ebit=Decimal("200"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        result = acquirers_multiple(period, Decimal("1000"), history=history, profile=profile)
        # Falls back to current EBIT=200; EV=1100; ratio=5.5
        assert result.raw_value == pytest.approx(5.5, rel=1e-3)

    def test_cyclical_with_negative_historical_ebit_filtered(self):
        """Historical periods with negative EBIT are filtered out by normalizer.

        History: [-50, -30, 100, 120, 140, 160, 180] -> valid positives: [100,120,140,160,180]
        Median of valid = 140.
        market_cap=1000, debt=200, cash=100 -> EV=1100
        EV/median_EBIT = 1100/140 ~ 7.857
        """
        ebit_values = [-50, -30, 100, 120, 140, 160, 180]
        history = _make_history("FCX", ebit_values)
        profile = AssetProfile(
            ticker="FCX",
            name="Freeport-McMoRan",
            sector=GICSSector.MATERIALS,
            market_cap=Decimal("1000"),
        )
        period = _make_period(
            ebit=Decimal("50"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        result = acquirers_multiple(period, Decimal("1000"), history=history, profile=profile)
        # median of [100, 120, 140, 160, 180] = 140; EV=1100; ratio=1100/140
        assert result.raw_value == pytest.approx(1100.0 / 140.0, rel=1e-3)

    def test_cyclical_history_none_profile_provided(self):
        """If history is None but profile is provided, use current EBIT."""
        profile = AssetProfile(
            ticker="XOM",
            name="Exxon Mobil",
            sector=GICSSector.ENERGY,
            market_cap=Decimal("1000"),
        )
        period = _make_period(
            ebit=Decimal("200"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        result = acquirers_multiple(period, Decimal("1000"), history=None, profile=profile)
        assert result.raw_value == pytest.approx(5.5, rel=1e-3)

    def test_cyclical_profile_none_history_provided(self):
        """If profile is None but history is provided, use current EBIT."""
        ebit_values = [80, 90, 100, 110, 120, 130, 140]
        history = _make_history("XOM", ebit_values)
        period = _make_period(
            ebit=Decimal("200"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        result = acquirers_multiple(period, Decimal("1000"), history=history, profile=None)
        assert result.raw_value == pytest.approx(5.5, rel=1e-3)


def _make_period(
    ebit: Decimal,
    short_term_debt: Decimal = Decimal("0"),
    long_term_debt: Decimal | None = None,
    cash_and_equivalents: Decimal | None = None,
) -> FinancialPeriod:
    """Helper to build a minimal FinancialPeriod for testing Acquirer's Multiple."""
    income = IncomeStatement(revenue=Decimal("0"), ebit=ebit)
    balance = BalanceSheet(
        total_assets=Decimal("100000"),
        short_term_debt=short_term_debt,
        long_term_debt=long_term_debt,
        cash_and_equivalents=cash_and_equivalents,
    )
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("0"),
        capital_expenditures=Decimal("0"),
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


def _make_history(ticker: str, ebit_values: list[float]) -> FinancialHistory:
    """Helper to build a FinancialHistory with varying EBIT values across periods."""
    periods = []
    for i, ebit in enumerate(ebit_values):
        year = 2018 + i
        income = IncomeStatement(
            revenue=Decimal("10000"),
            ebit=Decimal(str(ebit)),
            net_income=Decimal(str(ebit * 0.75)),
            shares_outstanding=1000,
        )
        balance = BalanceSheet(
            total_assets=Decimal("100000"),
            total_equity=Decimal("50000"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal(str(ebit * 1.2)),
            capital_expenditures=Decimal(str(-abs(ebit) * 0.3)),
        )
        periods.append(
            FinancialPeriod(
                period_end=f"{year}-12-31",
                filing_date=f"{year + 1}-02-15",
                current_income=income,
                current_balance=balance,
                current_cash_flow=cf,
            )
        )
    return FinancialHistory(ticker=ticker, periods=periods)
