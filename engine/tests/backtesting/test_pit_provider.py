"""Tests for point-in-time data provider."""

from datetime import date

from margin_engine.backtesting.pit_provider import (
    DelistingEvent,
    DelistingType,
    InMemoryPITProvider,
    PointInTimeProvider,
)
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)


def _make_profile(ticker: str, sector: GICSSector = GICSSector.TECHNOLOGY) -> AssetProfile:
    return AssetProfile(
        ticker=ticker,
        name=f"{ticker} Inc",
        sector=sector,
        sub_industry="Software",
        market_cap=50_000_000_000,
        avg_daily_volume=10_000_000,
        shares_outstanding=1_000_000_000,
    )


def _make_period() -> FinancialPeriod:
    income = IncomeStatement(
        revenue=10_000,
        cost_of_revenue=4_000,
        gross_profit=6_000,
        sga_expense=1_000,
        depreciation=500,
        ebit=4_500,
        interest_expense=200,
        tax_provision=1_000,
        net_income=3_300,
        shares_outstanding=1_000_000_000,
    )
    balance = BalanceSheet(
        total_assets=50_000,
        current_assets=20_000,
        cash_and_equivalents=10_000,
        receivables=5_000,
        total_liabilities=20_000,
        current_liabilities=8_000,
        long_term_debt=10_000,
        total_equity=30_000,
        retained_earnings=15_000,
        shares_outstanding=1_000_000_000,
    )
    cash_flow = CashFlowStatement(
        operating_cash_flow=5_000,
        capital_expenditures=-1_000,
    )
    return FinancialPeriod(
        period_end="2008-12-31",
        filing_date="2009-02-15",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cash_flow,
        prior_income=income,
        prior_balance=balance,
        prior_cash_flow=cash_flow,
    )


class TestInMemoryPITProvider:
    def test_get_universe_returns_known_tickers(self):
        provider = InMemoryPITProvider()
        provider.add_snapshot(
            date(2008, 3, 1), "AAPL", _make_profile("AAPL"), _make_period(), 150.0
        )
        provider.add_snapshot(date(2008, 3, 1), "MSFT", _make_profile("MSFT"), _make_period(), 28.0)

        universe = provider.get_universe(date(2008, 3, 1))
        assert len(universe) == 2
        tickers = {s.ticker for s in universe}
        assert tickers == {"AAPL", "MSFT"}

    def test_get_universe_excludes_delisted(self):
        provider = InMemoryPITProvider()
        provider.add_snapshot(
            date(2008, 3, 1), "AAPL", _make_profile("AAPL"), _make_period(), 150.0
        )
        provider.add_snapshot(date(2008, 3, 1), "LEH", _make_profile("LEH"), _make_period(), 40.0)
        provider.add_delisting(
            "LEH",
            DelistingEvent(
                ticker="LEH",
                delist_date=date(2008, 9, 15),
                delist_type=DelistingType.BANKRUPTCY,
                last_price=0.20,
            ),
        )

        # Before delisting: both present
        universe_before = provider.get_universe(date(2008, 3, 1))
        assert len(universe_before) == 2

        # After delisting: LEH excluded
        universe_after = provider.get_universe(date(2008, 10, 1))
        assert len(universe_after) == 1
        assert universe_after[0].ticker == "AAPL"

    def test_get_snapshot_returns_pit_data(self):
        provider = InMemoryPITProvider()
        profile = _make_profile("AAPL")
        period = _make_period()
        provider.add_snapshot(date(2008, 3, 1), "AAPL", profile, period, 150.0)

        snapshot = provider.get_snapshot("AAPL", date(2008, 3, 1))
        assert snapshot is not None
        assert snapshot.ticker == "AAPL"
        assert snapshot.price == 150.0
        assert snapshot.profile.sector == GICSSector.TECHNOLOGY

    def test_get_snapshot_returns_none_for_unknown(self):
        provider = InMemoryPITProvider()
        assert provider.get_snapshot("FAKE", date(2008, 3, 1)) is None

    def test_delisting_bankruptcy_returns_zero_value(self):
        provider = InMemoryPITProvider()
        provider.add_delisting(
            "LEH",
            DelistingEvent(
                ticker="LEH",
                delist_date=date(2008, 9, 15),
                delist_type=DelistingType.BANKRUPTCY,
                last_price=0.20,
            ),
        )
        event = provider.get_delisting("LEH")
        assert event is not None
        assert event.delist_type == DelistingType.BANKRUPTCY
        assert event.settlement_value == 0.0

    def test_delisting_acquisition_returns_acquisition_price(self):
        provider = InMemoryPITProvider()
        provider.add_delisting(
            "ATVI",
            DelistingEvent(
                ticker="ATVI",
                delist_date=date(2023, 10, 13),
                delist_type=DelistingType.ACQUISITION,
                last_price=95.0,
                acquisition_price=95.0,
            ),
        )
        event = provider.get_delisting("ATVI")
        assert event is not None
        assert event.settlement_value == 95.0

    def test_implements_protocol(self):
        provider = InMemoryPITProvider()
        assert isinstance(provider, PointInTimeProvider)
