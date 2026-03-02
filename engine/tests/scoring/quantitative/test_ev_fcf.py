"""Tests for EV/FCF (Enterprise Value / Free Cash Flow) value factor."""

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
from margin_engine.scoring.quantitative.ev_fcf import ev_fcf


class TestEvFcf:
    def test_apple_golden_value(self):
        """Apple FY2024: EV/FCF = 3,587,747,000,000 / 108,295,000,000 ~ 33.1294."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = ev_fcf(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.raw_value == pytest.approx(33.1294, rel=1e-3)

    def test_name(self):
        """Factor name should be 'ev_fcf'."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = ev_fcf(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.name == "ev_fcf"

    def test_percentile_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = ev_fcf(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert result.percentile_rank == 0.0

    def test_negative_fcf(self):
        """When FCF <= 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            operating_cash_flow=Decimal("5000"),
            capital_expenditures=Decimal("-8000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("2000"),
            cash_and_equivalents=Decimal("500"),
        )
        market_cap = Decimal("100000")
        result = ev_fcf(period, market_cap)
        assert result.raw_value == 0.0
        assert "negative" in result.detail.lower() or "zero" in result.detail.lower()

    def test_zero_fcf(self):
        """When FCF = 0 exactly, raw_value should be 0.0."""
        period = _make_period(
            operating_cash_flow=Decimal("5000"),
            capital_expenditures=Decimal("-5000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("2000"),
            cash_and_equivalents=Decimal("500"),
        )
        market_cap = Decimal("100000")
        result = ev_fcf(period, market_cap)
        assert result.raw_value == 0.0

    def test_zero_market_cap(self):
        """When market_cap <= 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            operating_cash_flow=Decimal("10000"),
            capital_expenditures=Decimal("-2000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("3000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = ev_fcf(period, Decimal("0"))
        assert result.raw_value == 0.0
        assert "market cap" in result.detail.lower()

    def test_negative_market_cap(self):
        """When market_cap < 0, raw_value should be 0.0."""
        period = _make_period(
            operating_cash_flow=Decimal("10000"),
            capital_expenditures=Decimal("-2000"),
            short_term_debt=Decimal("1000"),
            long_term_debt=Decimal("3000"),
            cash_and_equivalents=Decimal("500"),
        )
        result = ev_fcf(period, Decimal("-100"))
        assert result.raw_value == 0.0

    def test_detail_contains_key_values(self):
        """Detail string should contain EV, FCF, and the ratio."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = ev_fcf(APPLE_PERIOD_2024, APPLE_PROFILE.market_cap)
        assert "3587747000000" in result.detail
        assert "108295000000" in result.detail
        assert "33.12" in result.detail

    def test_simple_synthetic_computation(self):
        """Verify computation with simple synthetic values.

        market_cap=100, total_debt=30 (LTD=20 + STD=10), cash=10 -> EV=120
        CFO=20, CapEx=-5 -> FCF=15
        EV/FCF = 120/15 = 8.0
        """
        period = _make_period(
            operating_cash_flow=Decimal("20"),
            capital_expenditures=Decimal("-5"),
            short_term_debt=Decimal("10"),
            long_term_debt=Decimal("20"),
            cash_and_equivalents=Decimal("10"),
        )
        result = ev_fcf(period, Decimal("100"))
        assert result.raw_value == pytest.approx(8.0, rel=1e-3)

    def test_cyclical_company_uses_median_fcf(self):
        """Cyclical company should use 7-year median FCF, not current.

        History FCFs: [300, 400, 500, 600, 700, 800, 900] -> median=600
        Current FCF (peak): 900  (from current period)
        EV = 1000 + 200 - 100 = 1100
        Using median FCF=600: EV/FCF = 1100/600 ~ 1.8333
        Using current FCF=900: EV/FCF = 1100/900 ~ 1.2222
        Normalized ratio should be HIGHER (more expensive apparent).
        """
        # Current period has peak FCF=900 (CFO=1000, CapEx=-100)
        current = _make_period(
            operating_cash_flow=Decimal("1000"),
            capital_expenditures=Decimal("-100"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        # Build 7 years of history with ascending FCFs
        fcf_values = [300, 400, 500, 600, 700, 800, 900]
        history = _make_history("XOM", fcf_values)
        profile = _make_profile("XOM", GICSSector.ENERGY, market_cap=Decimal("1000"))

        result = ev_fcf(current, Decimal("1000"), history=history, profile=profile)

        # Median of [300,400,500,600,700,800,900] = 600
        # EV = 1000 + 200 - 100 = 1100, EV/FCF = 1100/600 ~ 1.8333
        assert result.raw_value == pytest.approx(1100.0 / 600.0, rel=1e-3)
        assert "7yr_median" in result.detail

    def test_non_cyclical_ignores_normalization(self):
        """Non-cyclical company with history should still use current FCF.

        Tech company (not cyclical) with history: should use current FCF=900.
        EV = 1000 + 200 - 100 = 1100
        EV/FCF = 1100/900 ~ 1.2222
        """
        current = _make_period(
            operating_cash_flow=Decimal("1000"),
            capital_expenditures=Decimal("-100"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        fcf_values = [300, 400, 500, 600, 700, 800, 900]
        history = _make_history("AAPL", fcf_values)
        profile = _make_profile("AAPL", GICSSector.TECHNOLOGY, market_cap=Decimal("1000"))

        result = ev_fcf(current, Decimal("1000"), history=history, profile=profile)

        # Non-cyclical: uses current FCF=900
        # EV = 1000 + 200 - 100 = 1100, EV/FCF = 1100/900 ~ 1.2222
        assert result.raw_value == pytest.approx(1100.0 / 900.0, rel=1e-3)

    def test_no_history_backward_compat(self):
        """Without history param, original behavior preserved.

        Same current period as cyclical test, but no history/profile.
        Should use current FCF=900.
        EV = 1000 + 200 - 100 = 1100, EV/FCF = 1100/900 ~ 1.2222
        """
        current = _make_period(
            operating_cash_flow=Decimal("1000"),
            capital_expenditures=Decimal("-100"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        result = ev_fcf(current, Decimal("1000"))

        # No history: uses current FCF=900
        assert result.raw_value == pytest.approx(1100.0 / 900.0, rel=1e-3)

    def test_cyclical_insufficient_history_uses_current(self):
        """Cyclical company with < 3 periods falls back to current FCF."""
        current = _make_period(
            operating_cash_flow=Decimal("1000"),
            capital_expenditures=Decimal("-100"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
        )
        # Only 2 periods -- below the MIN_HISTORY=3 threshold
        history = _make_history("XOM", [500, 900])
        profile = _make_profile("XOM", GICSSector.ENERGY, market_cap=Decimal("1000"))

        result = ev_fcf(current, Decimal("1000"), history=history, profile=profile)

        # Fallback to current FCF=900
        assert result.raw_value == pytest.approx(1100.0 / 900.0, rel=1e-3)


def _make_period(
    operating_cash_flow: Decimal,
    capital_expenditures: Decimal,
    short_term_debt: Decimal = Decimal("0"),
    long_term_debt: Decimal | None = None,
    cash_and_equivalents: Decimal | None = None,
    period_end: str = "2024-09-28",
) -> FinancialPeriod:
    """Helper to build a minimal FinancialPeriod for testing EV/FCF."""
    income = IncomeStatement(revenue=Decimal("0"))
    balance = BalanceSheet(
        total_assets=Decimal("100000"),
        short_term_debt=short_term_debt,
        long_term_debt=long_term_debt,
        cash_and_equivalents=cash_and_equivalents,
    )
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


def _make_history(ticker: str, fcf_values: list[int | float]) -> FinancialHistory:
    """Build a FinancialHistory with N periods having specified FCF values.

    Each FCF is created via operating_cash_flow = fcf + 100, capital_expenditures = -100.
    """
    periods = []
    for i, fcf in enumerate(fcf_values):
        year = 2018 + i
        period = _make_period(
            operating_cash_flow=Decimal(str(fcf + 100)),
            capital_expenditures=Decimal("-100"),
            short_term_debt=Decimal("100"),
            long_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
            period_end=f"{year}-12-31",
        )
        periods.append(period)
    return FinancialHistory(ticker=ticker, periods=periods)


def _make_profile(
    ticker: str,
    sector: GICSSector,
    market_cap: Decimal = Decimal("1000"),
) -> AssetProfile:
    """Build an AssetProfile for testing cyclical normalization."""
    return AssetProfile(
        ticker=ticker,
        name=f"{ticker} Inc.",
        sector=sector,
        market_cap=market_cap,
    )
