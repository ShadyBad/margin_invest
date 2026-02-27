"""Tests for the synthetic PIT data test helper."""

from datetime import date
from decimal import Decimal

from margin_engine.backtesting.pit_provider import InMemoryPITProvider
from margin_engine.models.financial import GICSSector

from .helpers import TICKER_SECTORS, build_pit_provider_with_tickers


class TestBuildProviderReturnsCorrectUniverseSize:
    """Verify the helper produces the right number of tickers in the universe."""

    def test_single_ticker(self):
        provider = build_pit_provider_with_tickers(
            tickers=["AAPL"],
            start=date(2020, 1, 1),
            end=date(2020, 3, 1),
        )
        universe = provider.get_universe(date(2020, 3, 1))
        assert len(universe) == 1
        assert universe[0].ticker == "AAPL"

    def test_multiple_tickers(self):
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "JNJ", "XOM", "PG", "META"]
        provider = build_pit_provider_with_tickers(
            tickers=tickers,
            start=date(2020, 1, 1),
            end=date(2020, 6, 1),
        )
        universe = provider.get_universe(date(2020, 6, 1))
        assert len(universe) == len(tickers)
        universe_tickers = {s.ticker for s in universe}
        assert universe_tickers == set(tickers)

    def test_unknown_ticker_defaults_to_technology(self):
        provider = build_pit_provider_with_tickers(
            tickers=["FAKE"],
            start=date(2020, 1, 1),
            end=date(2020, 1, 1),
        )
        universe = provider.get_universe(date(2020, 1, 1))
        assert len(universe) == 1
        assert universe[0].profile.sector == GICSSector.TECHNOLOGY

    def test_universe_at_midpoint_includes_all_tickers(self):
        """Universe queried in the middle of the date range should still include all."""
        tickers = ["AAPL", "MSFT"]
        provider = build_pit_provider_with_tickers(
            tickers=tickers,
            start=date(2020, 1, 1),
            end=date(2020, 12, 1),
        )
        universe = provider.get_universe(date(2020, 6, 15))
        assert len(universe) == 2

    def test_returns_inmemory_pit_provider(self):
        provider = build_pit_provider_with_tickers(
            tickers=["AAPL"],
            start=date(2020, 1, 1),
            end=date(2020, 1, 1),
        )
        assert isinstance(provider, InMemoryPITProvider)


class TestBuildProviderSnapshotsHaveValidFinancials:
    """Verify snapshots contain realistic, filter-passing financial data."""

    def test_profile_has_required_fields(self):
        provider = build_pit_provider_with_tickers(
            tickers=["AAPL"],
            start=date(2020, 6, 1),
            end=date(2020, 6, 1),
        )
        snap = provider.get_snapshot("AAPL", date(2020, 6, 1))
        assert snap is not None
        profile = snap.profile
        assert profile.ticker == "AAPL"
        assert profile.name == "Apple Inc."
        assert profile.sector == GICSSector.TECHNOLOGY
        assert profile.market_cap > Decimal("10_000_000_000")  # > $10B
        assert profile.years_of_history > 5

    def test_financial_period_populated(self):
        provider = build_pit_provider_with_tickers(
            tickers=["MSFT"],
            start=date(2020, 6, 1),
            end=date(2020, 6, 1),
        )
        snap = provider.get_snapshot("MSFT", date(2020, 6, 1))
        assert snap is not None
        period = snap.period

        # Income statement
        assert period.current_income.revenue > 0
        assert period.current_income.ebit > 0
        assert period.current_income.net_income > 0
        assert period.current_income.interest_expense is not None
        assert period.current_income.interest_expense > 0

        # Balance sheet
        assert period.current_balance.total_assets > 0
        assert period.current_balance.current_assets > 0
        assert period.current_balance.total_equity > 0
        assert period.current_balance.current_ratio > 1.0

        # Cash flow
        assert period.current_cash_flow.operating_cash_flow > 0
        assert period.current_cash_flow.free_cash_flow > 0

    def test_prior_period_populated(self):
        """Prior period data must exist for Beneish M-Score calculation."""
        provider = build_pit_provider_with_tickers(
            tickers=["AAPL"],
            start=date(2020, 1, 1),
            end=date(2020, 1, 1),
        )
        snap = provider.get_snapshot("AAPL", date(2020, 1, 1))
        assert snap is not None
        assert snap.period.prior_income is not None
        assert snap.period.prior_balance is not None
        assert snap.period.prior_cash_flow is not None

    def test_interest_coverage_passes_for_tech(self):
        """IT sector needs EBIT / interest_expense > 5.0."""
        provider = build_pit_provider_with_tickers(
            tickers=["AAPL"],
            start=date(2020, 1, 1),
            end=date(2020, 1, 1),
        )
        snap = provider.get_snapshot("AAPL", date(2020, 1, 1))
        assert snap is not None
        income = snap.period.current_income
        assert income.interest_expense is not None
        assert income.interest_expense > 0
        coverage = float(income.ebit / income.interest_expense)
        assert coverage > 5.0, f"IT sector needs >5.0, got {coverage:.2f}"

    def test_price_grows_over_time(self):
        provider = build_pit_provider_with_tickers(
            tickers=["AAPL"],
            start=date(2020, 1, 1),
            end=date(2020, 12, 1),
            monthly_return=0.01,
        )
        snap_jan = provider.get_snapshot("AAPL", date(2020, 1, 1))
        snap_dec = provider.get_snapshot("AAPL", date(2020, 12, 1))
        assert snap_jan is not None and snap_dec is not None
        assert snap_dec.price > snap_jan.price

    def test_sectors_match_known_tickers(self):
        tickers = list(TICKER_SECTORS.keys())
        provider = build_pit_provider_with_tickers(
            tickers=tickers,
            start=date(2020, 1, 1),
            end=date(2020, 1, 1),
        )
        for ticker in tickers:
            snap = provider.get_snapshot(ticker, date(2020, 1, 1))
            assert snap is not None
            assert snap.profile.sector == TICKER_SECTORS[ticker], (
                f"{ticker}: expected {TICKER_SECTORS[ticker]}, got {snap.profile.sector}"
            )

    def test_altman_z_score_safe(self):
        """Verify Altman Z'' > 1.1 with the synthetic data."""
        provider = build_pit_provider_with_tickers(
            tickers=["AAPL"],
            start=date(2020, 1, 1),
            end=date(2020, 1, 1),
        )
        snap = provider.get_snapshot("AAPL", date(2020, 1, 1))
        assert snap is not None
        cb = snap.period.current_balance
        ci = snap.period.current_income
        ta = float(cb.total_assets)
        wc = float(cb.current_assets - cb.current_liabilities)
        re = float(cb.retained_earnings or 0)
        ebit = float(ci.ebit)
        equity = float(cb.total_equity)
        tl = float(cb.total_liabilities)

        z = 6.56 * (wc / ta) + 3.26 * (re / ta) + 6.72 * (ebit / ta) + 1.05 * (equity / tl)
        assert z > 1.1, f"Altman Z'' should be > 1.1, got {z:.4f}"
