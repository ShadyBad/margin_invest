"""Tests for owner earnings yield factor (Buffett-adjusted FCF / EV)."""

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
from margin_engine.scoring.quantitative.owner_earnings import owner_earnings_yield


def _make_period(
    *,
    depreciation: Decimal | None = Decimal("50"),
    operating_cash_flow: Decimal = Decimal("200"),
    long_term_debt: Decimal | None = Decimal("300"),
    short_term_debt: Decimal = Decimal("100"),
    cash_and_equivalents: Decimal | None = Decimal("50"),
    period_end: str = "2024-09-28",
) -> FinancialPeriod:
    """Build a minimal FinancialPeriod for unit tests."""
    income = IncomeStatement(
        revenue=Decimal("1000"),
        ebit=Decimal("200"),
        depreciation=depreciation,
        net_income=Decimal("150"),
        shares_outstanding=100,
    )
    balance = BalanceSheet(
        total_assets=Decimal("1500"),
        total_equity=Decimal("600"),
        long_term_debt=long_term_debt,
        short_term_debt=short_term_debt,
        cash_and_equivalents=cash_and_equivalents,
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=Decimal("-80"),
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


def _make_profile(
    *,
    market_cap: Decimal = Decimal("5000"),
    sector: GICSSector = GICSSector.TECHNOLOGY,
) -> AssetProfile:
    return AssetProfile(
        ticker="TEST",
        name="Test Corp",
        sector=sector,
        market_cap=market_cap,
    )


def _make_history(
    cfo_depr_pairs: list[tuple[Decimal, Decimal]],
    ticker: str = "TEST",
) -> FinancialHistory:
    """Build a FinancialHistory with varying CFO/depreciation values.

    Each pair is (operating_cash_flow, depreciation). Periods are given
    sequential year-end dates so they sort properly.
    """
    periods = []
    for i, (cfo, depr) in enumerate(cfo_depr_pairs):
        periods.append(
            _make_period(
                operating_cash_flow=cfo,
                depreciation=depr,
                period_end=f"{2017 + i}-12-31",
            )
        )
    return FinancialHistory(ticker=ticker, periods=periods)


class TestOwnerEarningsYield:
    def test_basic_computation(self):
        """Basic computation with known values."""
        period = _make_period()
        profile = _make_profile(market_cap=Decimal("5000"))
        score = owner_earnings_yield(period, profile)

        # Maintenance CapEx = Depreciation * 1.1 = 50 * 1.1 = 55
        # Owner Earnings = CFO - Maintenance CapEx = 200 - 55 = 145
        # EV = Market Cap + Total Debt - Cash = 5000 + 400 - 50 = 5350
        # Yield = 145 / 5350 ≈ 0.02710
        assert score.name == "owner_earnings_yield"
        assert score.raw_value == pytest.approx(0.02710, abs=1e-3)

    def test_zero_ev(self):
        """EV <= 0 → 0.0."""
        period = _make_period(
            long_term_debt=Decimal("0"),
            short_term_debt=Decimal("0"),
            cash_and_equivalents=Decimal("6000"),
        )
        profile = _make_profile(market_cap=Decimal("5000"))
        score = owner_earnings_yield(period, profile)
        assert score.raw_value == 0.0

    def test_negative_owner_earnings(self):
        """Negative owner earnings → 0.0."""
        # CFO = 10, Maintenance CapEx = 50 * 1.1 = 55 → OE = 10 - 55 = -45
        period = _make_period(
            operating_cash_flow=Decimal("10"),
            depreciation=Decimal("50"),
        )
        profile = _make_profile()
        score = owner_earnings_yield(period, profile)
        assert score.raw_value == 0.0

    def test_percentile_rank_always_zero(self):
        """Percentile rank is always 0.0 (placeholder)."""
        period = _make_period()
        profile = _make_profile()
        score = owner_earnings_yield(period, profile)
        assert score.percentile_rank == 0.0


class TestOwnerEarningsCyclicalNormalization:
    """Tests for cyclical normalization of owner earnings yield."""

    def test_cyclical_uses_median_owner_earnings(self):
        """Cyclical company with history uses 7-year median owner earnings."""
        # Current period: CFO=200, depr=50 → OE = 200 - 55 = 145
        current = _make_period(
            operating_cash_flow=Decimal("200"),
            depreciation=Decimal("50"),
            period_end="2024-12-31",
        )
        # History with varying OE values (CFO, depreciation):
        # Year 1: 100 - 22*1.1 = 100 - 24.2 = 75.8
        # Year 2: 150 - 33*1.1 = 150 - 36.3 = 113.7
        # Year 3: 120 - 27.5*1.1 = 120 - 30.25 = 89.75
        # Year 4: 180 - 44*1.1 = 180 - 48.4 = 131.6
        # Year 5: 160 - 38.5*1.1 = 160 - 42.35 = 117.65
        # Year 6: 140 - 33*1.1 = 140 - 36.3 = 103.7
        # Year 7: 200 - 50*1.1 = 200 - 55 = 145.0
        history = _make_history([
            (Decimal("100"), Decimal("22")),
            (Decimal("150"), Decimal("33")),
            (Decimal("120"), Decimal("27.5")),
            (Decimal("180"), Decimal("44")),
            (Decimal("160"), Decimal("38.5")),
            (Decimal("140"), Decimal("33")),
            (Decimal("200"), Decimal("50")),
        ])
        profile = _make_profile(sector=GICSSector.ENERGY)

        score = owner_earnings_yield(current, profile, history=history)

        # Historical OE: [75.8, 113.7, 89.75, 131.6, 117.65, 103.7, 145.0]
        # Sorted: [75.8, 89.75, 103.7, 113.7, 117.65, 131.6, 145.0]
        # Median = 113.7
        # EV = 5000 + 400 - 50 = 5350
        # Yield = 113.7 / 5350 ≈ 0.02125
        expected_median_oe = 113.7
        ev = 5000 + 400 - 50
        expected_yield = expected_median_oe / ev
        assert score.raw_value == pytest.approx(expected_yield, abs=1e-4)
        assert "norm=" in score.detail
        assert "7yr_median" in score.detail

    def test_non_cyclical_ignores_normalization(self):
        """Non-cyclical company uses current-period OE even with history."""
        current = _make_period(
            operating_cash_flow=Decimal("200"),
            depreciation=Decimal("50"),
        )
        # History with much lower OE values (would change result if normalized)
        history = _make_history([
            (Decimal("50"), Decimal("10")),
            (Decimal("60"), Decimal("12")),
            (Decimal("55"), Decimal("11")),
            (Decimal("65"), Decimal("13")),
            (Decimal("70"), Decimal("14")),
            (Decimal("60"), Decimal("12")),
            (Decimal("200"), Decimal("50")),
        ])
        profile = _make_profile(sector=GICSSector.TECHNOLOGY)

        score_with_hist = owner_earnings_yield(current, profile, history=history)
        score_without = owner_earnings_yield(current, profile)

        # Non-cyclical: should match no-history result exactly
        assert score_with_hist.raw_value == pytest.approx(score_without.raw_value, abs=1e-6)
        assert "norm=" not in score_with_hist.detail

    def test_no_history_backward_compatible(self):
        """Without history param, result matches original behavior."""
        period = _make_period()
        profile = _make_profile(sector=GICSSector.ENERGY)

        score = owner_earnings_yield(period, profile)

        # Same as basic computation: OE = 145, EV = 5350, Yield ≈ 0.02710
        assert score.raw_value == pytest.approx(0.02710, abs=1e-3)
        assert "norm=" not in score.detail

    def test_cyclical_insufficient_history_uses_current(self):
        """Cyclical with < 3 periods falls back to current value."""
        current = _make_period(
            operating_cash_flow=Decimal("200"),
            depreciation=Decimal("50"),
        )
        # Only 2 periods — below _MIN_HISTORY=3 threshold
        history = _make_history([
            (Decimal("50"), Decimal("10")),
            (Decimal("200"), Decimal("50")),
        ])
        profile = _make_profile(sector=GICSSector.ENERGY)

        score = owner_earnings_yield(current, profile, history=history)
        score_no_hist = owner_earnings_yield(current, profile)

        # Should fall back to current OE since insufficient history
        assert score.raw_value == pytest.approx(score_no_hist.raw_value, abs=1e-6)

    def test_cyclical_normalization_detail_string(self):
        """Cyclical normalization includes median detail in output."""
        current = _make_period(
            operating_cash_flow=Decimal("200"),
            depreciation=Decimal("50"),
            period_end="2024-12-31",
        )
        history = _make_history([
            (Decimal("100"), Decimal("20")),
            (Decimal("120"), Decimal("25")),
            (Decimal("130"), Decimal("28")),
            (Decimal("140"), Decimal("30")),
            (Decimal("200"), Decimal("50")),
        ])
        profile = _make_profile(sector=GICSSector.MATERIALS)

        score = owner_earnings_yield(current, profile, history=history)

        assert "norm=" in score.detail
        assert "7yr_median" in score.detail
        assert "periods_used=" in score.detail
