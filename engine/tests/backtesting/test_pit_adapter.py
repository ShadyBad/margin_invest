"""Tests for PIT-to-pipeline adapter (PITSnapshot -> TickerV3Data)."""

from datetime import date
from decimal import Decimal

from margin_engine.backtesting.pit_adapter import (
    _MAX_GROWTH_RATE,
    _MIN_GROWTH_RATE,
    build_ticker_data_from_pit,
)
from margin_engine.backtesting.pit_provider import PITSnapshot
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.v3_pipeline import TickerV3Data


def _make_profile(
    ticker: str = "AAPL",
    sector: GICSSector = GICSSector.TECHNOLOGY,
) -> AssetProfile:
    return AssetProfile(
        ticker=ticker,
        name=f"{ticker} Inc",
        sector=sector,
        sub_industry="Software",
        market_cap=Decimal("50_000_000_000"),
        avg_daily_volume=Decimal("10_000_000"),
        shares_outstanding=1_000_000_000,
    )


def _make_period(
    *,
    period_end: str = "2024-12-31",
    revenue: Decimal = Decimal("50_000_000_000"),
    net_income: Decimal = Decimal("10_000_000_000"),
    operating_cash_flow: Decimal = Decimal("15_000_000_000"),
    capital_expenditures: Decimal = Decimal("-3_000_000_000"),
    total_equity: Decimal = Decimal("50_000_000_000"),
    shares_outstanding: int = 1_000_000_000,
    gross_profit: Decimal | None = None,
) -> FinancialPeriod:
    income = IncomeStatement(
        revenue=revenue,
        cost_of_revenue=revenue * Decimal("0.55"),
        gross_profit=gross_profit if gross_profit is not None else revenue * Decimal("0.45"),
        sga_expense=revenue * Decimal("0.10"),
        depreciation=revenue * Decimal("0.03"),
        ebit=revenue * Decimal("0.24"),
        interest_expense=revenue * Decimal("0.005"),
        tax_provision=revenue * Decimal("0.05"),
        net_income=net_income,
        shares_outstanding=shares_outstanding,
    )
    balance = BalanceSheet(
        total_assets=revenue * Decimal("2"),
        current_assets=revenue * Decimal("0.8"),
        cash_and_equivalents=revenue * Decimal("0.3"),
        receivables=revenue * Decimal("0.2"),
        total_liabilities=revenue * Decimal("0.9"),
        current_liabilities=revenue * Decimal("0.3"),
        long_term_debt=revenue * Decimal("0.2"),
        total_equity=total_equity,
        retained_earnings=total_equity * Decimal("0.6"),
        shares_outstanding=shares_outstanding,
    )
    cash_flow = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
        dividends_paid=Decimal("-1_000_000_000"),
        share_repurchases=Decimal("-2_000_000_000"),
        share_issuance=Decimal("0"),
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date=period_end,
        current_income=income,
        current_balance=balance,
        current_cash_flow=cash_flow,
    )


def _make_snapshot(
    ticker: str = "AAPL",
    price: float = 150.0,
    as_of_date: date | None = None,
    period: FinancialPeriod | None = None,
    profile: AssetProfile | None = None,
) -> PITSnapshot:
    return PITSnapshot(
        ticker=ticker,
        as_of_date=as_of_date or date(2025, 1, 15),
        profile=profile or _make_profile(ticker),
        period=period or _make_period(),
        price=price,
    )


class TestBuildTickerDataFromPit:
    """Tests for build_ticker_data_from_pit adapter function."""

    def test_returns_ticker_v3_data(self):
        snapshot = _make_snapshot()
        result = build_ticker_data_from_pit(snapshot)
        assert isinstance(result, TickerV3Data)

    def test_ticker_matches_snapshot(self):
        snapshot = _make_snapshot(ticker="MSFT")
        result = build_ticker_data_from_pit(snapshot)
        assert result.ticker == "MSFT"

    def test_current_price_comes_from_snapshot(self):
        snapshot = _make_snapshot(price=195.50)
        result = build_ticker_data_from_pit(snapshot)
        assert result.current_price == 195.50

    def test_fcf_per_share_computed_correctly(self):
        """FCF per share = (OCF + capex) / shares."""
        period = _make_period(
            operating_cash_flow=Decimal("15_000_000_000"),
            capital_expenditures=Decimal("-3_000_000_000"),
            shares_outstanding=1_000_000_000,
        )
        snapshot = _make_snapshot(period=period)
        result = build_ticker_data_from_pit(snapshot)

        expected_fcf = 15_000_000_000 + (-3_000_000_000)  # 12B
        expected_per_share = expected_fcf / 1_000_000_000  # 12.0
        assert result.current_fcf_per_share == expected_per_share

    def test_sustainable_growth_rate_is_positive_and_capped(self):
        snapshot = _make_snapshot()
        result = build_ticker_data_from_pit(snapshot)
        assert result.sustainable_growth_rate >= _MIN_GROWTH_RATE
        assert result.sustainable_growth_rate <= _MAX_GROWTH_RATE

    def test_zero_shares_returns_safe_defaults(self):
        """When shares_outstanding is 0, avoid division by zero."""
        period = _make_period(shares_outstanding=0)
        # Also set balance sheet shares to 0
        period.current_balance.shares_outstanding = 0
        snapshot = _make_snapshot(period=period)
        result = build_ticker_data_from_pit(snapshot)

        # With shares=1 fallback, FCF per share will be huge but not error
        assert isinstance(result.current_fcf_per_share, float)
        assert not result.current_fcf_per_share != result.current_fcf_per_share  # not NaN

    def test_dcf_iv_is_positive_for_profitable_company(self):
        """A profitable company with positive FCF should have a positive DCF IV."""
        snapshot = _make_snapshot()
        result = build_ticker_data_from_pit(snapshot)
        assert result.dcf_iv > 0.0

    def test_history_contains_at_least_one_period(self):
        snapshot = _make_snapshot()
        result = build_ticker_data_from_pit(snapshot)
        assert len(result.history.periods) >= 1
        assert result.history.ticker == snapshot.ticker

    def test_missing_optional_fields_dont_raise(self):
        """gross_profit=None and other optional fields should not cause errors."""
        period = _make_period(gross_profit=None)
        # gross_profit defaults to Decimal("0") in IncomeStatement
        snapshot = _make_snapshot(period=period)
        result = build_ticker_data_from_pit(snapshot)
        assert isinstance(result, TickerV3Data)

    def test_prior_snapshots_included_in_history(self):
        """Prior snapshots should appear in the history periods."""
        prior_1 = _make_snapshot(
            period=_make_period(period_end="2023-12-31"),
            as_of_date=date(2024, 2, 15),
        )
        prior_2 = _make_snapshot(
            period=_make_period(period_end="2022-12-31"),
            as_of_date=date(2023, 2, 15),
        )
        current = _make_snapshot(
            period=_make_period(period_end="2024-12-31"),
            as_of_date=date(2025, 2, 15),
        )

        result = build_ticker_data_from_pit(current, prior_snapshots=[prior_1, prior_2])
        assert len(result.history.periods) == 3
        # Periods should be sorted by period_end ascending
        ends = [p.period_end for p in result.history.periods]
        assert ends == sorted(ends)

    def test_negative_fcf_produces_zero_dcf_iv(self):
        """Negative FCF should result in dcf_iv = 0 (no Gordon Growth with negative numerator)."""
        period = _make_period(
            operating_cash_flow=Decimal("1_000_000_000"),
            capital_expenditures=Decimal("-5_000_000_000"),
        )
        snapshot = _make_snapshot(period=period)
        result = build_ticker_data_from_pit(snapshot)
        assert result.dcf_iv == 0.0

    def test_profile_passed_through(self):
        """AssetProfile should be passed through unchanged."""
        profile = _make_profile(ticker="GOOGL", sector=GICSSector.TECHNOLOGY)
        snapshot = _make_snapshot(ticker="GOOGL", profile=profile)
        result = build_ticker_data_from_pit(snapshot)
        assert result.profile.ticker == "GOOGL"
        assert result.profile.sector == GICSSector.TECHNOLOGY

    def test_latest_period_matches_snapshot_period(self):
        """latest_period should be the snapshot's period, not a prior one."""
        period = _make_period(period_end="2024-12-31")
        snapshot = _make_snapshot(period=period)
        result = build_ticker_data_from_pit(snapshot)
        assert result.latest_period.period_end == "2024-12-31"

    def test_default_optional_fields(self):
        """Optional fields should have sensible defaults."""
        snapshot = _make_snapshot()
        result = build_ticker_data_from_pit(snapshot)
        assert result.buyback_yield is None
        assert result.insider_ownership_pct is None
        assert result.sbc_pct is None
        assert result.recent_acquisition_count == 0
        assert result.sue_percentile == 50.0
        assert result.momentum_percentile == 50.0
        assert result.beta is None

    def test_growth_rate_clamped_at_minimum(self):
        """Very low ROE should still produce at least MIN_GROWTH_RATE."""
        period = _make_period(
            net_income=Decimal("1"),  # tiny net income
            total_equity=Decimal("50_000_000_000"),
        )
        snapshot = _make_snapshot(period=period)
        result = build_ticker_data_from_pit(snapshot)
        assert result.sustainable_growth_rate == _MIN_GROWTH_RATE

    def test_growth_rate_clamped_at_maximum(self):
        """Very high ROE should be capped at MAX_GROWTH_RATE."""
        period = _make_period(
            net_income=Decimal("50_000_000_000"),  # 100% ROE
            total_equity=Decimal("50_000_000_000"),
        )
        snapshot = _make_snapshot(period=period)
        result = build_ticker_data_from_pit(snapshot)
        # ROE=1.0, retention=0.70 -> g=0.70 -> capped at 0.30
        assert result.sustainable_growth_rate == _MAX_GROWTH_RATE
