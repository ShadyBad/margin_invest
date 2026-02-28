"""Tests for DatabasePITProvider — point-in-time data provider backed by PostgreSQL PIT tables."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

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
        """Insert filing with filing_date after as_of_date, verify it's NOT returned (lookahead prevention)."""
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
            _make_member(ticker="AAPL", market_cap=2_500_000_000_000.0, quarter_date=date(2024, 9, 30))
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
        session.add(
            _make_filing(
                ticker="TINY",
                cik="0000000001",
                filing_date=date(2024, 11, 1),
                period_end=date(2024, 9, 28),
                accession_number="0000000001-24-000001",
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
    async def test_get_universe_excludes_inactive(self, session: AsyncSession):
        """Insert inactive member, verify excluded."""
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

        assert len(universe) == 0

    @pytest.mark.asyncio
    async def test_get_universe_uses_nearest_quarter(self, session: AsyncSession):
        """Query date between quarters, verify nearest prior quarter used."""
        session.add(
            _make_member(ticker="AAPL", quarter_date=date(2024, 6, 30), market_cap=2_000_000_000_000.0)
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
        session.add(
            _make_member(ticker="AAPL", quarter_date=date(2024, 9, 30))
        )
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
