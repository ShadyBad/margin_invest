"""Tests for DatabasePITProvider — point-in-time data provider backed by PostgreSQL PIT tables."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import (
    PITDailyPrice,
    PITFinancialSnapshot,
    PITUniverseMembership,
    SICSectorMap,
)
from margin_api.services.pit_provider import DatabasePITProvider
from margin_engine.models.financial import GICSSector
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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


def _make_filing(
    ticker: str = "AAPL",
    cik: str = "0000320193",
    filing_date: date = date(2024, 11, 1),
    period_end: date = date(2024, 9, 28),
    accession_number: str = "0000320193-24-000001",
    shares_outstanding: int = 15_000_000_000,
    fiscal_year: int = 2024,
    fiscal_quarter: int | None = 4,
    sic_code: int | None = None,
    **kw,
) -> PITFinancialSnapshot:
    return PITFinancialSnapshot(
        cik=cik,
        ticker=ticker,
        filing_date=filing_date,
        period_end=period_end,
        form_type="10-K",
        accession_number=accession_number,
        income_statement=kw.get("income_statement", _make_income_statement()),
        balance_sheet=kw.get("balance_sheet", _make_balance_sheet()),
        cash_flow=kw.get("cash_flow", _make_cash_flow()),
        shares_outstanding=shares_outstanding,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        sic_code=sic_code,
        ingested_at=datetime.now(UTC),
    )


def _make_price(
    ticker: str = "AAPL",
    price_date: date = date(2024, 11, 1),
    close: float = 150.0,
) -> PITDailyPrice:
    return PITDailyPrice(
        ticker=ticker,
        date=price_date,
        open=close - 1.0,
        high=close + 2.0,
        low=close - 2.0,
        close=close,
        adj_close=close,
        volume=50_000_000,
        source="yfinance",
    )


def _make_member(
    ticker: str = "AAPL",
    cik: str = "0000320193",
    quarter_date: date = date(2024, 9, 30),
    is_active: bool = True,
    market_cap: float | None = 2_500_000_000_000.0,
    delist_detected_at: date | None = None,
    last_known_price: float | None = None,
) -> PITUniverseMembership:
    return PITUniverseMembership(
        ticker=ticker,
        cik=cik,
        quarter_date=quarter_date,
        is_active=is_active,
        market_cap=market_cap,
        last_filing_date=date(2024, 11, 1),
        delist_detected_at=delist_detected_at,
        last_known_price=last_known_price,
    )


# ---------------------------------------------------------------------------
# get_price tests
# ---------------------------------------------------------------------------


class TestGetPrice:
    @pytest.mark.asyncio
    async def test_get_price_exact_date(self, session: AsyncSession):
        """Insert price, query exact date, verify correct close."""
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 1), close=150.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        result = await provider.get_price("AAPL", date(2024, 11, 1))

        assert result == 150.0

    @pytest.mark.asyncio
    async def test_get_price_nearest_prior(self, session: AsyncSession):
        """Query weekend/holiday, verify Friday's price returned."""
        # Friday 2024-11-01
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 1), close=150.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        # Query Saturday 2024-11-02 — should return Friday's price
        result = await provider.get_price("AAPL", date(2024, 11, 2))

        assert result == 150.0

    @pytest.mark.asyncio
    async def test_get_price_no_data(self, session: AsyncSession):
        """Query with no data, verify None."""
        provider = DatabasePITProvider(session)
        result = await provider.get_price("AAPL", date(2024, 11, 1))

        assert result is None

    @pytest.mark.asyncio
    async def test_get_price_future_date_excluded(self, session: AsyncSession):
        """Price after as_of_date should NOT be returned."""
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 5), close=155.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        result = await provider.get_price("AAPL", date(2024, 11, 1))

        assert result is None


# ---------------------------------------------------------------------------
# get_prices (batch) tests
# ---------------------------------------------------------------------------


class TestGetPrices:
    @pytest.mark.asyncio
    async def test_get_prices_batch(self, session: AsyncSession):
        """get_prices returns prices for multiple tickers in one call."""
        session.add_all(
            [
                _make_price(ticker="AAPL", price_date=date(2020, 3, 1), close=100.0),
                _make_price(ticker="MSFT", price_date=date(2020, 3, 1), close=200.0),
            ]
        )
        await session.commit()

        provider = DatabasePITProvider(session)
        prices = await provider.get_prices(["AAPL", "MSFT", "NOPE"], date(2020, 3, 15))
        assert prices["AAPL"] == pytest.approx(100.0)
        assert prices["MSFT"] == pytest.approx(200.0)
        assert "NOPE" not in prices

    @pytest.mark.asyncio
    async def test_get_prices_empty_tickers(self, session: AsyncSession):
        """get_prices with empty ticker list returns empty dict."""
        provider = DatabasePITProvider(session)
        prices = await provider.get_prices([], date(2020, 3, 15))
        assert prices == {}

    @pytest.mark.asyncio
    async def test_get_prices_uses_most_recent(self, session: AsyncSession):
        """get_prices returns the most recent price at or before as_of_date."""
        session.add_all(
            [
                _make_price(ticker="AAPL", price_date=date(2020, 2, 1), close=90.0),
                _make_price(ticker="AAPL", price_date=date(2020, 3, 1), close=100.0),
                _make_price(ticker="AAPL", price_date=date(2020, 4, 1), close=110.0),
            ]
        )
        await session.commit()

        provider = DatabasePITProvider(session)
        prices = await provider.get_prices(["AAPL"], date(2020, 3, 15))
        assert prices["AAPL"] == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_get_prices_excludes_future(self, session: AsyncSession):
        """get_prices must not return prices after as_of_date."""
        session.add(_make_price(ticker="AAPL", price_date=date(2020, 4, 1), close=110.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        prices = await provider.get_prices(["AAPL"], date(2020, 3, 15))
        assert "AAPL" not in prices


# ---------------------------------------------------------------------------
# get_snapshot tests
# ---------------------------------------------------------------------------


class TestGetSnapshot:
    @pytest.mark.asyncio
    async def test_get_snapshot_returns_latest_filing(self, session: AsyncSession):
        """Insert 2 filings, query date after both, verify latest returned."""
        # Older filing
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 5, 1),
                period_end=date(2024, 3, 30),
                accession_number="0000320193-24-000001",
                fiscal_year=2024,
                fiscal_quarter=2,
            )
        )
        # Newer filing
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000002",
                fiscal_year=2024,
                fiscal_quarter=4,
            )
        )
        # Price
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 12, 1), close=175.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        snap = await provider.get_snapshot("AAPL", date(2024, 12, 1))

        assert snap is not None
        assert snap.ticker == "AAPL"
        assert snap.filing_date == date(2024, 11, 1)
        assert snap.price == 175.0
        assert snap.as_of_date == date(2024, 12, 1)

    @pytest.mark.asyncio
    async def test_get_snapshot_respects_filing_date(self, session: AsyncSession):
        """Filing with filing_date after as_of_date must NOT be returned."""
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 15),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000001",
            )
        )
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 1), close=150.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        # Query date BEFORE filing_date
        snap = await provider.get_snapshot("AAPL", date(2024, 11, 1))

        assert snap is None

    @pytest.mark.asyncio
    async def test_get_snapshot_no_data(self, session: AsyncSession):
        """No filings, verify None."""
        provider = DatabasePITProvider(session)
        snap = await provider.get_snapshot("AAPL", date(2024, 12, 1))

        assert snap is None

    @pytest.mark.asyncio
    async def test_get_snapshot_no_price(self, session: AsyncSession):
        """Filing exists but no price — should return None."""
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000001",
            )
        )
        await session.commit()

        provider = DatabasePITProvider(session)
        snap = await provider.get_snapshot("AAPL", date(2024, 12, 1))

        assert snap is None

    @pytest.mark.asyncio
    async def test_get_snapshot_builds_financial_period(self, session: AsyncSession):
        """Verify financial period is correctly built from JSONB data."""
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000001",
                shares_outstanding=15_000_000_000,
                income_statement=_make_income_statement(revenue=2_000_000, net_income=200_000),
                balance_sheet=_make_balance_sheet(total_assets=10_000_000),
                cash_flow=_make_cash_flow(operating_cash_flow=500_000),
            )
        )
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 1), close=175.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        snap = await provider.get_snapshot("AAPL", date(2024, 11, 1))

        assert snap is not None
        # Verify income statement mapping
        assert float(snap.period.current_income.revenue) == 2_000_000
        assert float(snap.period.current_income.net_income) == 200_000
        assert snap.period.current_income.shares_outstanding == 15_000_000_000
        # Verify balance sheet mapping
        assert float(snap.period.current_balance.total_assets) == 10_000_000
        assert snap.period.current_balance.shares_outstanding == 15_000_000_000
        # Verify cash flow mapping (capex -> capital_expenditures)
        assert float(snap.period.current_cash_flow.operating_cash_flow) == 500_000
        # Verify period metadata
        assert snap.period.period_end == "2024-09-28"
        assert snap.period.filing_date == "2024-11-01"

    @pytest.mark.asyncio
    async def test_get_snapshot_builds_prior_period(self, session: AsyncSession):
        """When 2 filings exist, prior period should be populated."""
        # Prior filing
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 5, 1),
                period_end=date(2024, 3, 30),
                accession_number="0000320193-24-000001",
                income_statement=_make_income_statement(revenue=800_000),
            )
        )
        # Current filing
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000002",
                income_statement=_make_income_statement(revenue=1_200_000),
            )
        )
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 15), close=175.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        snap = await provider.get_snapshot("AAPL", date(2024, 11, 15))

        assert snap is not None
        assert float(snap.period.current_income.revenue) == 1_200_000
        assert snap.period.prior_income is not None
        assert float(snap.period.prior_income.revenue) == 800_000

    @pytest.mark.asyncio
    async def test_get_snapshot_profile(self, session: AsyncSession):
        """Verify AssetProfile is correctly built."""
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000001",
                shares_outstanding=15_000_000_000,
            )
        )
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 1), close=175.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        snap = await provider.get_snapshot("AAPL", date(2024, 11, 1))

        assert snap is not None
        assert snap.profile.ticker == "AAPL"
        assert snap.profile.shares_outstanding == 15_000_000_000
        # market_cap = shares * price
        expected_market_cap = Decimal("15000000000") * Decimal("175.0")
        assert snap.profile.market_cap == expected_market_cap


# ---------------------------------------------------------------------------
# get_universe tests
# ---------------------------------------------------------------------------


class TestGetUniverse:
    @pytest.mark.asyncio
    async def test_get_universe_filters_by_market_cap(self, session: AsyncSession):
        """Insert members with varying market caps, verify filtering."""
        # Large cap — should be included
        session.add(
            _make_member(
                ticker="AAPL", market_cap=2_500_000_000_000.0, quarter_date=date(2024, 9, 30)
            )
        )
        # Small cap — below default 100M threshold
        session.add(
            _make_member(
                ticker="TINY",
                cik="0000000001",
                market_cap=50_000_000.0,
                quarter_date=date(2024, 9, 30),
            )
        )
        # Add filings + prices for both
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000001",
            )
        )
        # TINY: shares * price = 10_000_000 * 5.0 = 50M < 100M threshold
        session.add(
            _make_filing(
                ticker="TINY",
                cik="0000000001",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000000001-24-000001",
                shares_outstanding=10_000_000,
            )
        )
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 15), close=175.0))
        session.add(_make_price(ticker="TINY", price_date=date(2024, 11, 15), close=5.0))
        await session.commit()

        provider = DatabasePITProvider(session, min_market_cap=100_000_000)
        universe = await provider.get_universe(date(2024, 11, 15))

        tickers = [s.ticker for s in universe]
        assert "AAPL" in tickers
        assert "TINY" not in tickers

    @pytest.mark.asyncio
    async def test_get_universe_includes_inactive(self, session: AsyncSession):
        """Inactive tickers are included — delisting detection is unreliable
        for tickers that started filing after the dataset start date, so
        is_active is not used as a filter. Delistings are handled downstream
        via get_delisting() and elimination filters."""
        session.add(
            _make_member(
                ticker="DEAD",
                cik="0000000002",
                is_active=False,
                quarter_date=date(2024, 9, 30),
                market_cap=1_000_000_000.0,
            )
        )
        session.add(
            _make_filing(
                ticker="DEAD",
                cik="0000000002",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000000002-24-000001",
            )
        )
        session.add(_make_price(ticker="DEAD", price_date=date(2024, 11, 15), close=0.50))
        await session.commit()

        provider = DatabasePITProvider(session)
        universe = await provider.get_universe(date(2024, 11, 15))

        # Inactive tickers ARE returned — filtering happens downstream
        assert len(universe) == 1
        assert universe[0].ticker == "DEAD"

    @pytest.mark.asyncio
    async def test_get_universe_uses_nearest_quarter(self, session: AsyncSession):
        """Query date between quarters, verify nearest prior quarter used."""
        session.add(
            _make_member(
                ticker="AAPL", quarter_date=date(2024, 6, 30), market_cap=2_000_000_000_000.0
            )
        )
        session.add(
            _make_member(
                ticker="MSFT",
                cik="0000789019",
                quarter_date=date(2024, 9, 30),
                market_cap=3_000_000_000_000.0,
            )
        )
        # AAPL filed in August (before query date)
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 8, 1),
                period_end=date(2024, 6, 30),
                accession_number="0000320193-24-000001",
            )
        )
        # MSFT filed in October (before query date of Nov 15)
        session.add(
            _make_filing(
                ticker="MSFT",
                cik="0000789019",
                filing_date=date(2024, 10, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000789019-24-000001",
            )
        )
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 15), close=175.0))
        session.add(_make_price(ticker="MSFT", price_date=date(2024, 11, 15), close=400.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        # Query date is 2024-11-15 — nearest quarter_date <= that is 2024-09-30
        universe = await provider.get_universe(date(2024, 11, 15))

        tickers = [s.ticker for s in universe]
        # Only MSFT had quarter_date=2024-09-30 (the nearest)
        # AAPL had quarter_date=2024-06-30 (not the nearest quarter)
        assert "MSFT" in tickers
        assert "AAPL" not in tickers

    @pytest.mark.asyncio
    async def test_get_universe_skips_ticker_without_snapshot(self, session: AsyncSession):
        """If a member has no filing or price, it's skipped (not an error)."""
        session.add(
            _make_member(ticker="NOFILING", cik="0000000099", quarter_date=date(2024, 9, 30))
        )
        await session.commit()

        provider = DatabasePITProvider(session)
        universe = await provider.get_universe(date(2024, 11, 15))

        assert len(universe) == 0


# ---------------------------------------------------------------------------
# get_delisting tests
# ---------------------------------------------------------------------------


class TestGetDelisting:
    @pytest.mark.asyncio
    async def test_get_delisting_found(self, session: AsyncSession):
        """Insert member with delist_detected_at, verify DelistingEvent returned."""
        session.add(
            _make_member(
                ticker="GONE",
                cik="0000000003",
                quarter_date=date(2024, 9, 30),
                delist_detected_at=date(2024, 10, 15),
                last_known_price=12.50,
            )
        )
        await session.commit()

        provider = DatabasePITProvider(session)
        event = await provider.get_delisting("GONE")

        assert event is not None
        assert event.ticker == "GONE"
        assert event.delist_date == date(2024, 10, 15)
        assert event.last_price == 12.50

    @pytest.mark.asyncio
    async def test_get_delisting_not_found(self, session: AsyncSession):
        """Active member, verify None."""
        session.add(_make_member(ticker="AAPL", quarter_date=date(2024, 9, 30)))
        await session.commit()

        provider = DatabasePITProvider(session)
        event = await provider.get_delisting("AAPL")

        assert event is None

    @pytest.mark.asyncio
    async def test_get_delisting_no_records(self, session: AsyncSession):
        """No records at all for ticker, verify None."""
        provider = DatabasePITProvider(session)
        event = await provider.get_delisting("NONEXISTENT")

        assert event is None

    @pytest.mark.asyncio
    async def test_get_delisting_uses_latest_quarter(self, session: AsyncSession):
        """Multiple quarters, uses the most recent with delist_detected_at."""
        session.add(
            _make_member(
                ticker="GONE",
                cik="0000000003",
                quarter_date=date(2024, 6, 30),
                delist_detected_at=date(2024, 7, 15),
                last_known_price=10.0,
            )
        )
        session.add(
            _make_member(
                ticker="GONE",
                cik="0000000003",
                quarter_date=date(2024, 9, 30),
                delist_detected_at=date(2024, 10, 15),
                last_known_price=12.50,
            )
        )
        await session.commit()

        provider = DatabasePITProvider(session)
        event = await provider.get_delisting("GONE")

        assert event is not None
        assert event.delist_date == date(2024, 10, 15)
        assert event.last_price == 12.50


# ---------------------------------------------------------------------------
# SIC sector mapping tests
# ---------------------------------------------------------------------------


class TestSICSectorMapping:
    @pytest.mark.asyncio
    async def test_profile_uses_sic_sector(self, session: AsyncSession):
        """_build_profile should use SIC->GICS mapping instead of hardcoded sector."""
        # Seed SIC->GICS mapping
        session.add(SICSectorMap(sic_code=2830, gics_sector="Health Care"))
        # Seed snapshot with sic_code
        session.add(
            _make_filing(
                ticker="PFE",
                cik="0000078003",
                filing_date=date(2020, 2, 15),
                period_end=date(2019, 12, 31),
                accession_number="0000078003-20-000001",
                shares_outstanding=5_000_000,
                fiscal_year=2019,
                sic_code=2830,
            )
        )
        session.add(_make_price(ticker="PFE", price_date=date(2020, 3, 1), close=35.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        snapshot = await provider.get_snapshot("PFE", date(2020, 3, 15))

        assert snapshot is not None
        assert snapshot.profile.sector == GICSSector.HEALTHCARE

    @pytest.mark.asyncio
    async def test_profile_falls_back_to_industrials_without_sic(self, session: AsyncSession):
        """Without SIC code, profile should default to INDUSTRIALS (not TECHNOLOGY)."""
        session.add(
            _make_filing(
                ticker="XYZ",
                cik="0000099999",
                filing_date=date(2020, 2, 15),
                period_end=date(2019, 12, 31),
                accession_number="0000099999-20-000001",
                shares_outstanding=1_000_000,
                fiscal_year=2019,
            )
        )
        session.add(_make_price(ticker="XYZ", price_date=date(2020, 3, 1), close=10.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        snapshot = await provider.get_snapshot("XYZ", date(2020, 3, 15))

        assert snapshot is not None
        assert snapshot.profile.sector == GICSSector.INDUSTRIALS

    @pytest.mark.asyncio
    async def test_profile_falls_back_to_industrials_for_unknown_sic(self, session: AsyncSession):
        """SIC code not in the mapping table should fall back to INDUSTRIALS."""
        # No SICSectorMap rows — so sic_code 9999 won't match anything
        session.add(
            _make_filing(
                ticker="UNK",
                cik="0000088888",
                filing_date=date(2020, 2, 15),
                period_end=date(2019, 12, 31),
                accession_number="0000088888-20-000001",
                shares_outstanding=1_000_000,
                fiscal_year=2019,
                sic_code=9999,
            )
        )
        session.add(_make_price(ticker="UNK", price_date=date(2020, 3, 1), close=10.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        snapshot = await provider.get_snapshot("UNK", date(2020, 3, 15))

        assert snapshot is not None
        assert snapshot.profile.sector == GICSSector.INDUSTRIALS


# ---------------------------------------------------------------------------
# Volume and history enrichment tests
# ---------------------------------------------------------------------------


class TestVolumeAndHistory:
    @pytest.mark.asyncio
    async def test_universe_populates_avg_daily_volume(self, session: AsyncSession):
        """get_universe should populate avg_daily_volume from membership rows."""
        session.add(
            PITUniverseMembership(
                ticker="AAPL",
                cik="0000320193",
                quarter_date=date(2024, 9, 30),
                is_active=True,
                market_cap=2_500_000_000_000.0,
                avg_daily_volume=5_000_000.0,
                last_filing_date=date(2024, 11, 1),
            )
        )
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000001",
            )
        )
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 15), close=175.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        universe = await provider.get_universe(date(2024, 11, 15))

        assert len(universe) == 1
        assert universe[0].profile.avg_daily_volume == Decimal("5000000.0")

    @pytest.mark.asyncio
    async def test_universe_populates_years_of_history(self, session: AsyncSession):
        """get_universe should compute years_of_history from earliest filing."""
        session.add(
            _make_member(
                ticker="AAPL",
                quarter_date=date(2024, 9, 30),
                market_cap=2_500_000_000_000.0,
            )
        )
        # Two filings ~4 years apart
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2020, 11, 1),
                period_end=date(2020, 9, 28),
                accession_number="0000320193-20-000001",
                fiscal_year=2020,
            )
        )
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000001",
                fiscal_year=2024,
            )
        )
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 15), close=175.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        universe = await provider.get_universe(date(2024, 11, 15))

        assert len(universe) == 1
        # Earliest filing was 2020-11-01, as_of_date is 2024-11-15
        # (2024-11-15 - 2020-11-01).days // 365 = 1475 // 365 = 4
        assert universe[0].profile.years_of_history == 4

    @pytest.mark.asyncio
    async def test_universe_zero_volume_when_null(self, session: AsyncSession):
        """avg_daily_volume should be 0 when membership row has no volume data."""
        session.add(
            _make_member(
                ticker="AAPL",
                quarter_date=date(2024, 9, 30),
                market_cap=2_500_000_000_000.0,
            )
        )
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000320193-24-000001",
            )
        )
        session.add(_make_price(ticker="AAPL", price_date=date(2024, 11, 15), close=175.0))
        await session.commit()

        provider = DatabasePITProvider(session)
        universe = await provider.get_universe(date(2024, 11, 15))

        assert len(universe) == 1
        assert universe[0].profile.avg_daily_volume == Decimal("0")


# ---------------------------------------------------------------------------
# get_price_series tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_price_series_returns_date_price_dict(session):
    """get_price_series returns {date: float} for a ticker in a date range."""
    for day, close in [(1, 100.0), (2, 101.0), (3, 102.0)]:
        session.add(PITDailyPrice(
            ticker="SPY", date=date(2020, 1, day),
            open=close, high=close, low=close, close=close,
            adj_close=close, volume=1000000,
        ))
    await session.flush()

    provider = DatabasePITProvider(session)
    prices = await provider.get_price_series("SPY", date(2020, 1, 1), date(2020, 1, 3))

    assert len(prices) == 3
    assert prices[date(2020, 1, 1)] == 100.0
    assert prices[date(2020, 1, 2)] == 101.0
    assert prices[date(2020, 1, 3)] == 102.0


@pytest.mark.asyncio
async def test_get_price_series_filters_by_date_range(session):
    """get_price_series only returns prices within the requested range."""
    for day in range(1, 6):
        session.add(PITDailyPrice(
            ticker="SPY", date=date(2020, 1, day),
            open=100.0, high=100.0, low=100.0, close=float(100 + day),
            adj_close=float(100 + day), volume=1000000,
        ))
    await session.flush()

    provider = DatabasePITProvider(session)
    prices = await provider.get_price_series("SPY", date(2020, 1, 2), date(2020, 1, 4))

    assert len(prices) == 3
    assert date(2020, 1, 1) not in prices
    assert date(2020, 1, 5) not in prices


@pytest.mark.asyncio
async def test_get_price_series_empty_when_no_data(session):
    """get_price_series returns empty dict when ticker has no data."""
    provider = DatabasePITProvider(session)
    prices = await provider.get_price_series("NODATA", date(2020, 1, 1), date(2020, 12, 31))
    assert prices == {}
