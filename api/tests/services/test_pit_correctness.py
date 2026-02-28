"""PIT correctness tests — prove no lookahead bias, no survivorship bias, correct price alignment.

These are the most critical tests in the PIT pipeline. Every test here validates
a property that, if violated, would silently corrupt all backtest results.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import PITDailyPrice, PITFinancialSnapshot, PITUniverseMembership
from margin_api.services.pit_provider import DatabasePITProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_income_statement(
    revenue: float = 1_000_000,
    net_income: float = 100_000,
    **overrides: float,
) -> dict:
    base = {
        "revenue": revenue,
        "cost_of_revenue": 600_000,
        "gross_profit": 400_000,
        "sga_expense": 100_000,
        "rd_expense": 50_000,
        "ebit": 200_000,
        "interest_expense": 10_000,
        "net_income": net_income,
        "depreciation": 20_000,
        "tax_provision": 40_000,
    }
    base.update(overrides)
    return base


def _make_balance_sheet(**overrides: float) -> dict:
    base = {
        "total_assets": 5_000_000,
        "current_assets": 2_000_000,
        "cash_and_equivalents": 500_000,
        "total_liabilities": 2_000_000,
        "current_liabilities": 800_000,
        "long_term_debt": 1_000_000,
        "short_term_debt": 200_000,
        "total_equity": 3_000_000,
        "retained_earnings": 1_500_000,
        "pp_and_e": 1_000_000,
        "receivables": 300_000,
    }
    base.update(overrides)
    return base


def _make_cash_flow(**overrides: float) -> dict:
    base = {
        "operating_cash_flow": 300_000,
        "capex": -50_000,
        "dividends_paid": -20_000,
        "share_repurchases": -30_000,
    }
    base.update(overrides)
    return base


async def insert_filing(
    session: AsyncSession,
    ticker: str,
    filing_date: date,
    period_end: date,
    accession_number: str,
    cik: str = "0000320193",
    shares_outstanding: int = 15_000_000_000,
    fiscal_year: int = 2024,
    fiscal_quarter: int | None = None,
    income_statement: dict | None = None,
    balance_sheet: dict | None = None,
    cash_flow: dict | None = None,
) -> None:
    """Helper to insert a PITFinancialSnapshot."""
    filing = PITFinancialSnapshot(
        cik=cik,
        ticker=ticker,
        filing_date=filing_date,
        period_end=period_end,
        form_type="10-Q",
        accession_number=accession_number,
        income_statement=income_statement or _make_income_statement(),
        balance_sheet=balance_sheet or _make_balance_sheet(),
        cash_flow=cash_flow or _make_cash_flow(),
        shares_outstanding=shares_outstanding,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        ingested_at=datetime.now(UTC),
    )
    session.add(filing)
    await session.flush()


async def insert_price(
    session: AsyncSession,
    ticker: str,
    dt: date,
    close: float = 150.0,
) -> None:
    """Helper to insert a PITDailyPrice."""
    price = PITDailyPrice(
        ticker=ticker,
        date=dt,
        open=close - 1.0,
        high=close + 2.0,
        low=close - 2.0,
        close=close,
        adj_close=close,
        volume=50_000_000,
        source="yfinance",
    )
    session.add(price)
    await session.flush()


async def insert_member(
    session: AsyncSession,
    ticker: str,
    quarter_date: date,
    is_active: bool = True,
    market_cap: float | None = 2_500_000_000_000.0,
    cik: str = "0000320193",
    delist_detected_at: date | None = None,
    last_known_price: float | None = None,
    last_filing_date: date | None = None,
) -> None:
    """Helper to insert a PITUniverseMembership."""
    member = PITUniverseMembership(
        ticker=ticker,
        cik=cik,
        quarter_date=quarter_date,
        is_active=is_active,
        market_cap=market_cap,
        last_filing_date=last_filing_date or quarter_date,
        delist_detected_at=delist_detected_at,
        last_known_price=last_known_price,
    )
    session.add(member)
    await session.flush()


# ===========================================================================
# TestNoLookaheadBias
# ===========================================================================


class TestNoLookaheadBias:
    """Prove that DatabasePITProvider never returns data that was not yet public."""

    @pytest.mark.asyncio
    async def test_filing_lag_respected(self, session: AsyncSession):
        """Filing A (Q1) filed 2024-06-30; Filing B (Q4) filed 2024-11-01.

        Querying on 2024-10-31 (before B is filed) must return Filing A.
        Querying on 2024-11-02 (after B is filed) must return Filing B.
        """
        # Filing A: Q1 report, filed on 2024-06-30
        await insert_filing(
            session,
            ticker="AAPL",
            filing_date=date(2024, 6, 30),
            period_end=date(2024, 3, 31),
            accession_number="AAPL-2024-Q1",
            fiscal_quarter=1,
        )
        # Filing B: Q4 report, filed on 2024-11-01
        await insert_filing(
            session,
            ticker="AAPL",
            filing_date=date(2024, 11, 1),
            period_end=date(2024, 9, 28),
            accession_number="AAPL-2024-Q4",
            fiscal_quarter=4,
        )
        # Price data spanning both query dates
        await insert_price(session, "AAPL", date(2024, 10, 31), close=170.0)
        await insert_price(session, "AAPL", date(2024, 11, 2), close=175.0)
        await session.commit()

        provider = DatabasePITProvider(session)

        # Before Filing B is public: should see Filing A (Q1)
        snap_before = await provider.get_snapshot("AAPL", date(2024, 10, 31))
        assert snap_before is not None
        assert snap_before.filing_date == date(2024, 6, 30)
        assert snap_before.period.period_end == "2024-03-31"

        # After Filing B is public: should see Filing B (Q4)
        snap_after = await provider.get_snapshot("AAPL", date(2024, 11, 2))
        assert snap_after is not None
        assert snap_after.filing_date == date(2024, 11, 1)
        assert snap_after.period.period_end == "2024-09-28"

    @pytest.mark.asyncio
    async def test_future_filing_invisible(self, session: AsyncSession):
        """A filing dated in 2099 must NEVER appear for any reasonable query date.

        This is a poison test: if a filing with filing_date=2099-01-01 appears
        in results for date(2025, 12, 31), the lookahead guard is broken.
        """
        # Poison filing far in the future
        await insert_filing(
            session,
            ticker="AAPL",
            filing_date=date(2099, 1, 1),
            period_end=date(2098, 12, 31),
            accession_number="AAPL-POISON",
        )
        # Price available at query date
        await insert_price(session, "AAPL", date(2025, 12, 31), close=200.0)
        await session.commit()

        provider = DatabasePITProvider(session)
        snap = await provider.get_snapshot("AAPL", date(2025, 12, 31))

        # No filing should be found — the only filing is in the future
        assert snap is None

    @pytest.mark.asyncio
    async def test_universe_respects_filing_dates(self, session: AsyncSession):
        """Two companies in the universe: A filed before as_of, B filed after.

        get_universe should include A's snapshot but NOT B's latest data.
        Since B has no filing before as_of_date, B should be excluded entirely
        (get_snapshot returns None when no filing exists).
        """
        as_of = date(2024, 10, 15)

        # Company A: filed before as_of_date
        await insert_member(
            session,
            ticker="EARLY",
            quarter_date=date(2024, 9, 30),
            cik="0000000001",
            market_cap=500_000_000_000.0,
        )
        await insert_filing(
            session,
            ticker="EARLY",
            filing_date=date(2024, 10, 1),  # Before as_of
            period_end=date(2024, 9, 28),
            accession_number="EARLY-2024-Q3",
            cik="0000000001",
        )
        await insert_price(session, "EARLY", as_of, close=100.0)

        # Company B: filed AFTER as_of_date (no earlier filing exists)
        await insert_member(
            session,
            ticker="LATE",
            quarter_date=date(2024, 9, 30),
            cik="0000000002",
            market_cap=500_000_000_000.0,
        )
        await insert_filing(
            session,
            ticker="LATE",
            filing_date=date(2024, 11, 1),  # After as_of
            period_end=date(2024, 9, 28),
            accession_number="LATE-2024-Q3",
            cik="0000000002",
        )
        await insert_price(session, "LATE", as_of, close=100.0)
        await session.commit()

        provider = DatabasePITProvider(session)
        universe = await provider.get_universe(as_of)

        tickers = [s.ticker for s in universe]
        assert "EARLY" in tickers, "Company with filing before as_of should be included"
        assert "LATE" not in tickers, "Company with filing only after as_of should be excluded"


# ===========================================================================
# TestSurvivorshipBias
# ===========================================================================


class TestSurvivorshipBias:
    """Prove that delisted companies are properly excluded after delist and included before."""

    @pytest.mark.asyncio
    async def test_delisted_excluded_from_universe(self, session: AsyncSession):
        """A company delisted in Q3 2020 must NOT appear in Q1 2021 universe."""
        # Delisted company — marked inactive + delist_detected_at set
        await insert_member(
            session,
            ticker="GONE",
            quarter_date=date(2020, 9, 30),
            cik="0000000099",
            is_active=False,
            market_cap=1_000_000_000.0,
            delist_detected_at=date(2020, 8, 15),
            last_known_price=5.0,
        )
        # Filing and price for the delisted company
        await insert_filing(
            session,
            ticker="GONE",
            filing_date=date(2020, 7, 1),
            period_end=date(2020, 6, 30),
            accession_number="GONE-2020-Q2",
            cik="0000000099",
        )
        await insert_price(session, "GONE", date(2021, 3, 31), close=0.0)
        await session.commit()

        provider = DatabasePITProvider(session)
        universe = await provider.get_universe(date(2021, 3, 31))

        tickers = [s.ticker for s in universe]
        assert "GONE" not in tickers, "Delisted company should not be in post-delist universe"

    @pytest.mark.asyncio
    async def test_delisted_included_before_delist(self, session: AsyncSession):
        """Same company should be in the universe BEFORE its delisting quarter.

        We need a quarter record where the company was still active (before delist).
        """
        # Active record for Q2 2020 (before delisting in Q3 2020)
        await insert_member(
            session,
            ticker="GONE",
            quarter_date=date(2020, 6, 30),
            cik="0000000099",
            is_active=True,
            market_cap=1_000_000_000.0,
        )
        # Filing before the query date
        await insert_filing(
            session,
            ticker="GONE",
            filing_date=date(2020, 5, 1),
            period_end=date(2020, 3, 31),
            accession_number="GONE-2020-Q1",
            cik="0000000099",
        )
        await insert_price(session, "GONE", date(2020, 6, 30), close=25.0)
        await session.commit()

        provider = DatabasePITProvider(session)
        universe = await provider.get_universe(date(2020, 6, 30))

        tickers = [s.ticker for s in universe]
        assert "GONE" in tickers, "Company should be in universe before its delisting"

    @pytest.mark.asyncio
    async def test_delisting_event_returned(self, session: AsyncSession):
        """get_delisting for a delisted ticker should return a DelistingEvent."""
        await insert_member(
            session,
            ticker="GONE",
            quarter_date=date(2020, 9, 30),
            cik="0000000099",
            is_active=False,
            delist_detected_at=date(2020, 8, 15),
            last_known_price=5.25,
        )
        await session.commit()

        provider = DatabasePITProvider(session)
        event = await provider.get_delisting("GONE")

        assert event is not None
        assert event.ticker == "GONE"
        assert event.delist_date == date(2020, 8, 15)
        assert event.last_price == 5.25

    @pytest.mark.asyncio
    async def test_active_company_no_delisting(self, session: AsyncSession):
        """get_delisting for an active company should return None."""
        await insert_member(
            session,
            ticker="AAPL",
            quarter_date=date(2024, 9, 30),
            is_active=True,
        )
        await session.commit()

        provider = DatabasePITProvider(session)
        event = await provider.get_delisting("AAPL")

        assert event is None


# ===========================================================================
# TestPriceAlignment
# ===========================================================================


class TestPriceAlignment:
    """Prove that price lookups handle exact dates, weekends, gaps, and missing data."""

    @pytest.mark.asyncio
    async def test_exact_date_match(self, session: AsyncSession):
        """Price on an exact trading day returns that day's close.

        Insert Mon-Fri prices, query Wednesday, get Wednesday's close.
        """
        # Mon Jan 1 2024 to Fri Jan 5 2024
        prices = [
            (date(2024, 1, 1), 148.0),  # Mon
            (date(2024, 1, 2), 149.0),  # Tue
            (date(2024, 1, 3), 150.0),  # Wed
            (date(2024, 1, 4), 151.0),  # Thu
            (date(2024, 1, 5), 152.0),  # Fri
        ]
        for dt, close in prices:
            await insert_price(session, "AAPL", dt, close)
        await session.commit()

        provider = DatabasePITProvider(session)
        result = await provider.get_price("AAPL", date(2024, 1, 3))

        assert result == 150.0, "Exact date query should return that date's close"

    @pytest.mark.asyncio
    async def test_weekend_returns_friday(self, session: AsyncSession):
        """Querying Saturday should return Friday's close (most recent prior)."""
        # Insert Friday's price
        await insert_price(session, "AAPL", date(2024, 1, 5), close=152.0)
        await session.commit()

        provider = DatabasePITProvider(session)
        # Query Saturday Jan 6
        result = await provider.get_price("AAPL", date(2024, 1, 6))

        assert result == 152.0, "Saturday query should return Friday's close"

    @pytest.mark.asyncio
    async def test_no_future_price(self, session: AsyncSession):
        """Querying a date before any prices exist should return None.

        Prices start in 2024; querying 2020-01-01 should yield None.
        """
        await insert_price(session, "AAPL", date(2024, 1, 2), close=149.0)
        await insert_price(session, "AAPL", date(2024, 1, 3), close=150.0)
        await session.commit()

        provider = DatabasePITProvider(session)
        result = await provider.get_price("AAPL", date(2020, 1, 1))

        assert result is None, "No price should exist before the earliest data point"

    @pytest.mark.asyncio
    async def test_price_gap_uses_prior(self, session: AsyncSession):
        """When a trading day is missing (gap), the most recent prior close is used.

        Insert Mon, Tue, Thu, Fri — skip Wednesday.
        Querying Wednesday should return Tuesday's close.
        """
        await insert_price(session, "AAPL", date(2024, 1, 1), close=148.0)  # Mon
        await insert_price(session, "AAPL", date(2024, 1, 2), close=149.0)  # Tue
        # No Wednesday (gap)
        await insert_price(session, "AAPL", date(2024, 1, 4), close=151.0)  # Thu
        await insert_price(session, "AAPL", date(2024, 1, 5), close=152.0)  # Fri
        await session.commit()

        provider = DatabasePITProvider(session)
        # Query the gap day (Wednesday)
        result = await provider.get_price("AAPL", date(2024, 1, 3))

        assert result == 149.0, "Gap day should return the most recent prior close (Tuesday)"


# ===========================================================================
# TestAntiRegressionSentinels
# ===========================================================================


class TestAntiRegressionSentinels:
    """Sentinel tests that catch regressions across wide date ranges.

    These are designed to be run on every CI build. If any sentinel fails,
    a fundamental invariant of the PIT system has been violated.
    """

    @pytest.mark.asyncio
    async def test_poison_filing_sentinel(self, session: AsyncSession):
        """A filing dated 2099-01-01 must never appear for any date 2020-2025.

        Loop through 5 different as_of dates and verify the poison filing
        is invisible at every single one.
        """
        # Poison filing
        await insert_filing(
            session,
            ticker="AAPL",
            filing_date=date(2099, 1, 1),
            period_end=date(2098, 12, 31),
            accession_number="AAPL-POISON-SENTINEL",
        )
        # Prices at every query date so the provider doesn't bail on missing price
        sentinel_dates = [
            date(2020, 6, 30),
            date(2021, 12, 31),
            date(2023, 3, 15),
            date(2024, 7, 4),
            date(2025, 11, 30),
        ]
        for dt in sentinel_dates:
            await insert_price(session, "AAPL", dt, close=100.0)
        await session.commit()

        provider = DatabasePITProvider(session)

        for as_of in sentinel_dates:
            snap = await provider.get_snapshot("AAPL", as_of)
            assert snap is None, (
                f"Poison filing (2099-01-01) leaked into snapshot at as_of={as_of}"
            )

    @pytest.mark.asyncio
    async def test_survivorship_sentinel(self, session: AsyncSession):
        """Company delisted in 2015: present in 2014 universe, absent from 2016."""
        # 2014 record: still active
        await insert_member(
            session,
            ticker="OLDCO",
            quarter_date=date(2014, 12, 31),
            cik="0000000077",
            is_active=True,
            market_cap=500_000_000.0,
        )
        # 2015 record: delisted
        await insert_member(
            session,
            ticker="OLDCO",
            quarter_date=date(2015, 6, 30),
            cik="0000000077",
            is_active=False,
            market_cap=500_000_000.0,
            delist_detected_at=date(2015, 5, 1),
            last_known_price=2.0,
        )
        # Filing that was available before both query dates
        await insert_filing(
            session,
            ticker="OLDCO",
            filing_date=date(2014, 11, 1),
            period_end=date(2014, 9, 30),
            accession_number="OLDCO-2014-Q3",
            cik="0000000077",
            fiscal_year=2014,
        )
        # Prices for both query dates
        await insert_price(session, "OLDCO", date(2014, 12, 31), close=10.0)
        await insert_price(session, "OLDCO", date(2016, 3, 31), close=0.0)
        await session.commit()

        provider = DatabasePITProvider(session)

        # 2014: should be present (active quarter record exists)
        universe_2014 = await provider.get_universe(date(2014, 12, 31))
        tickers_2014 = [s.ticker for s in universe_2014]
        assert "OLDCO" in tickers_2014, "Delisted company should be present before delisting"

        # 2016: should be absent (most recent quarter record is inactive)
        universe_2016 = await provider.get_universe(date(2016, 3, 31))
        tickers_2016 = [s.ticker for s in universe_2016]
        assert "OLDCO" not in tickers_2016, "Delisted company should be absent after delisting"
