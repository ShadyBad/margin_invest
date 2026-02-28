"""Tests for the universe assembly service.

Covers:
- detect_delistings: detecting tickers missing 2+ consecutive quarters
- build_quarterly_membership: building row dicts for pit_universe_memberships
- assemble_universe: end-to-end integration querying pit_financial_snapshots
- fill_last_known_prices: backfilling last_known_price for delisted tickers
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import PITDailyPrice, PITFinancialSnapshot, PITUniverseMembership
from margin_api.services.edgar.universe_assembly import (
    assemble_universe,
    build_quarterly_membership,
    detect_delistings,
    fill_last_known_prices,
)


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


def _make_filing(
    ticker: str = "AAPL",
    cik: str = "0000320193",
    filing_date: date = date(2020, 5, 1),
    period_end: date = date(2020, 3, 31),
    accession_number: str = "0000320193-20-000001",
    fiscal_year: int = 2020,
    fiscal_quarter: int | None = 1,
) -> PITFinancialSnapshot:
    return PITFinancialSnapshot(
        cik=cik,
        ticker=ticker,
        filing_date=filing_date,
        period_end=period_end,
        form_type="10-Q",
        accession_number=accession_number,
        income_statement={"revenue": 1_000_000},
        balance_sheet={"total_assets": 5_000_000},
        cash_flow={"operating_cash_flow": 300_000},
        shares_outstanding=1_000_000_000,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        ingested_at=datetime.now(UTC),
    )


def _make_price(
    ticker: str = "AAPL",
    price_date: date = date(2020, 6, 15),
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


# ---------------------------------------------------------------------------
# detect_delistings tests
# ---------------------------------------------------------------------------


class TestDetectDelistings:
    def test_detect_delistings_two_missing_quarters(self) -> None:
        """Ticker missing 2+ consecutive quarters is marked delisted."""
        filing_quarters = {
            "AAPL": [date(2020, 3, 31), date(2020, 6, 30), date(2020, 9, 30), date(2020, 12, 31)],
            "GONE": [date(2020, 3, 31), date(2020, 6, 30)],
        }
        all_quarters = [
            date(2020, 3, 31),
            date(2020, 6, 30),
            date(2020, 9, 30),
            date(2020, 12, 31),
        ]
        result = detect_delistings(filing_quarters, all_quarters)
        assert "GONE" in result
        assert "AAPL" not in result

    def test_detect_delistings_one_missing_not_delisted(self) -> None:
        """One missing quarter is not enough to trigger delisting."""
        filing_quarters = {
            "SKIP": [date(2020, 3, 31), date(2020, 9, 30), date(2020, 12, 31)],
        }
        all_quarters = [
            date(2020, 3, 31),
            date(2020, 6, 30),
            date(2020, 9, 30),
            date(2020, 12, 31),
        ]
        result = detect_delistings(filing_quarters, all_quarters)
        assert "SKIP" not in result

    def test_detect_delistings_empty_filings(self) -> None:
        """Empty filing_quarters returns empty dict."""
        result = detect_delistings({}, [date(2020, 3, 31), date(2020, 6, 30)])
        assert result == {}

    def test_detect_delistings_delist_detected_at_correct_quarter(self) -> None:
        """Delist detected at = the quarter after 2 consecutive misses."""
        filing_quarters = {
            "GONE": [date(2020, 3, 31)],
        }
        all_quarters = [
            date(2020, 3, 31),
            date(2020, 6, 30),
            date(2020, 9, 30),
            date(2020, 12, 31),
        ]
        result = detect_delistings(filing_quarters, all_quarters)
        assert "GONE" in result
        # Missing Q2 and Q3 → detected at Q3 (the quarter where 2 consecutive misses are confirmed)
        assert result["GONE"] == date(2020, 9, 30)

    def test_detect_delistings_missing_at_end(self) -> None:
        """Ticker missing the last 2 quarters is delisted."""
        filing_quarters = {
            "LATE": [date(2020, 3, 31), date(2020, 6, 30)],
        }
        all_quarters = [
            date(2020, 3, 31),
            date(2020, 6, 30),
            date(2020, 9, 30),
            date(2020, 12, 31),
        ]
        result = detect_delistings(filing_quarters, all_quarters)
        assert "LATE" in result
        assert result["LATE"] == date(2020, 12, 31)

    def test_detect_delistings_three_missing_uses_first_detection(self) -> None:
        """With 3+ consecutive misses, detection date is at the 2nd miss."""
        filing_quarters = {
            "GONE": [date(2020, 3, 31)],
        }
        all_quarters = [
            date(2020, 3, 31),
            date(2020, 6, 30),
            date(2020, 9, 30),
            date(2020, 12, 31),
            date(2021, 3, 31),
        ]
        result = detect_delistings(filing_quarters, all_quarters)
        assert "GONE" in result
        # Missing Q2, Q3, Q4, Q1'21 — detected at Q3 (2nd consecutive miss)
        assert result["GONE"] == date(2020, 9, 30)

    def test_detect_delistings_single_quarter(self) -> None:
        """With only one quarter, no delisting can be detected."""
        filing_quarters = {
            "AAPL": [date(2020, 3, 31)],
        }
        all_quarters = [date(2020, 3, 31)]
        result = detect_delistings(filing_quarters, all_quarters)
        assert result == {}

    def test_detect_delistings_ticker_never_filed(self) -> None:
        """Ticker that exists in filing_quarters but has empty list."""
        filing_quarters = {
            "GHOST": [],
        }
        all_quarters = [
            date(2020, 3, 31),
            date(2020, 6, 30),
            date(2020, 9, 30),
        ]
        result = detect_delistings(filing_quarters, all_quarters)
        # Missing all quarters — detected at Q2 (2nd consecutive miss)
        assert "GHOST" in result
        assert result["GHOST"] == date(2020, 6, 30)


# ---------------------------------------------------------------------------
# build_quarterly_membership tests
# ---------------------------------------------------------------------------


class TestBuildQuarterlyMembership:
    def test_build_quarterly_membership_active(self) -> None:
        """Active ticker gets is_active=True."""
        active = {"AAPL": ("320193", date(2020, 9, 30), 2.5e12)}
        rows = build_quarterly_membership(date(2020, 9, 30), active, delistings={})
        assert len(rows) == 1
        assert rows[0]["is_active"] is True
        assert rows[0]["ticker"] == "AAPL"
        assert rows[0]["cik"] == "320193"
        assert rows[0]["quarter_date"] == date(2020, 9, 30)
        assert rows[0]["market_cap"] == 2.5e12
        assert rows[0]["last_filing_date"] == date(2020, 9, 30)
        assert rows[0]["delist_detected_at"] is None
        assert rows[0]["last_known_price"] is None

    def test_build_quarterly_membership_delisted(self) -> None:
        """Delisted ticker gets is_active=False and delist_detected_at set."""
        active = {"GONE": ("123456", date(2020, 6, 30), 1e9)}
        delistings = {"GONE": date(2020, 12, 31)}
        rows = build_quarterly_membership(date(2020, 12, 31), active, delistings)
        assert len(rows) == 1
        assert rows[0]["is_active"] is False
        assert rows[0]["delist_detected_at"] == date(2020, 12, 31)

    def test_build_quarterly_membership_delisted_future_quarter(self) -> None:
        """Ticker delisted in a future quarter is still active in current quarter."""
        active = {"GONE": ("123456", date(2020, 6, 30), 1e9)}
        delistings = {"GONE": date(2020, 12, 31)}
        rows = build_quarterly_membership(date(2020, 6, 30), active, delistings)
        assert len(rows) == 1
        # Quarter is before delist date — should still be active
        assert rows[0]["is_active"] is True
        assert rows[0]["delist_detected_at"] is None

    def test_build_quarterly_membership_multiple_tickers(self) -> None:
        """Multiple tickers produce one row each."""
        active = {
            "AAPL": ("320193", date(2020, 9, 30), 2.5e12),
            "MSFT": ("789019", date(2020, 9, 30), 1.8e12),
        }
        rows = build_quarterly_membership(date(2020, 9, 30), active, delistings={})
        assert len(rows) == 2
        tickers = {r["ticker"] for r in rows}
        assert tickers == {"AAPL", "MSFT"}

    def test_build_quarterly_membership_none_market_cap(self) -> None:
        """Ticker with None market_cap is handled."""
        active = {"NOCAP": ("999999", date(2020, 9, 30), None)}
        rows = build_quarterly_membership(date(2020, 9, 30), active, delistings={})
        assert len(rows) == 1
        assert rows[0]["market_cap"] is None

    def test_build_quarterly_membership_empty(self) -> None:
        """No active tickers returns empty list."""
        rows = build_quarterly_membership(date(2020, 9, 30), {}, delistings={})
        assert rows == []


# ---------------------------------------------------------------------------
# assemble_universe integration tests
# ---------------------------------------------------------------------------


class TestAssembleUniverse:
    @pytest.mark.asyncio
    async def test_assemble_universe_basic(self, session: AsyncSession) -> None:
        """Insert filings across quarters and verify universe assembly."""
        # AAPL files all 4 quarters of 2020
        for i, (fd, pe, fq) in enumerate(
            [
                (date(2020, 5, 1), date(2020, 3, 31), 1),
                (date(2020, 8, 1), date(2020, 6, 30), 2),
                (date(2020, 11, 1), date(2020, 9, 30), 3),
                (date(2021, 2, 1), date(2020, 12, 31), 4),
            ]
        ):
            session.add(
                _make_filing(
                    ticker="AAPL",
                    filing_date=fd,
                    period_end=pe,
                    accession_number=f"0000320193-20-{i + 1:06d}",
                    fiscal_year=2020,
                    fiscal_quarter=fq,
                )
            )

        # GONE files only Q1 and Q2 of 2020
        for i, (fd, pe, fq) in enumerate(
            [
                (date(2020, 5, 1), date(2020, 3, 31), 1),
                (date(2020, 8, 1), date(2020, 6, 30), 2),
            ]
        ):
            session.add(
                _make_filing(
                    ticker="GONE",
                    cik="0000123456",
                    filing_date=fd,
                    period_end=pe,
                    accession_number=f"0000123456-20-{i + 1:06d}",
                    fiscal_year=2020,
                    fiscal_quarter=fq,
                )
            )

        await session.commit()

        result = await assemble_universe(session)

        assert result["quarters_processed"] == 4
        assert result["tickers_tracked"] >= 2
        assert result["delistings_detected"] >= 1

        # Verify rows were inserted
        from sqlalchemy import select

        stmt = select(PITUniverseMembership)
        rows = (await session.execute(stmt)).scalars().all()
        assert len(rows) > 0

        # GONE should be inactive in Q4
        gone_q4 = [
            r
            for r in rows
            if r.ticker == "GONE" and r.quarter_date == date(2020, 12, 31)
        ]
        assert len(gone_q4) == 1
        assert gone_q4[0].is_active is False
        assert gone_q4[0].delist_detected_at is not None

        # AAPL should be active in all quarters
        aapl_rows = [r for r in rows if r.ticker == "AAPL"]
        assert all(r.is_active is True for r in aapl_rows)

    @pytest.mark.asyncio
    async def test_assemble_universe_empty_db(self, session: AsyncSession) -> None:
        """Empty database returns zeros."""
        result = await assemble_universe(session)
        assert result["quarters_processed"] == 0
        assert result["tickers_tracked"] == 0
        assert result["delistings_detected"] == 0

    @pytest.mark.asyncio
    async def test_assemble_universe_idempotent(self, session: AsyncSession) -> None:
        """Running assemble_universe twice should not duplicate rows."""
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2020, 5, 1),
                period_end=date(2020, 3, 31),
                accession_number="0000320193-20-000001",
                fiscal_year=2020,
                fiscal_quarter=1,
            )
        )
        await session.commit()

        result1 = await assemble_universe(session)
        result2 = await assemble_universe(session)

        # Both should succeed
        assert result1["quarters_processed"] == 1
        assert result2["quarters_processed"] == 1

        # Verify no duplicates
        from sqlalchemy import func, select

        count = (
            await session.execute(select(func.count()).select_from(PITUniverseMembership))
        ).scalar()
        assert count == 1


# ---------------------------------------------------------------------------
# fill_last_known_prices integration tests
# ---------------------------------------------------------------------------


class TestFillLastKnownPrices:
    @pytest.mark.asyncio
    async def test_fill_last_known_prices_basic(self, session: AsyncSession) -> None:
        """Fill last_known_price from pit_daily_prices for delisted ticker."""
        # Create a delisted membership row
        session.add(
            PITUniverseMembership(
                ticker="GONE",
                cik="0000123456",
                quarter_date=date(2020, 12, 31),
                is_active=False,
                market_cap=1e9,
                last_filing_date=date(2020, 6, 30),
                delist_detected_at=date(2020, 12, 31),
                last_known_price=None,
            )
        )
        # Add a price before delist date
        session.add(_make_price(ticker="GONE", price_date=date(2020, 12, 28), close=42.50))
        # Add a price after delist date (should NOT be used)
        session.add(_make_price(ticker="GONE", price_date=date(2021, 1, 5), close=0.01))
        await session.commit()

        updated = await fill_last_known_prices(session)

        assert updated == 1

        # Verify the price was filled
        from sqlalchemy import select

        stmt = select(PITUniverseMembership).where(
            PITUniverseMembership.ticker == "GONE"
        )
        row = (await session.execute(stmt)).scalars().first()
        assert row is not None
        assert row.last_known_price == 42.50

    @pytest.mark.asyncio
    async def test_fill_last_known_prices_no_delisted(self, session: AsyncSession) -> None:
        """No delisted tickers returns 0."""
        session.add(
            PITUniverseMembership(
                ticker="AAPL",
                cik="0000320193",
                quarter_date=date(2020, 12, 31),
                is_active=True,
                market_cap=2.5e12,
                last_filing_date=date(2020, 12, 31),
                delist_detected_at=None,
                last_known_price=None,
            )
        )
        await session.commit()

        updated = await fill_last_known_prices(session)
        assert updated == 0

    @pytest.mark.asyncio
    async def test_fill_last_known_prices_already_filled(self, session: AsyncSession) -> None:
        """Delisted ticker with existing last_known_price is skipped."""
        session.add(
            PITUniverseMembership(
                ticker="GONE",
                cik="0000123456",
                quarter_date=date(2020, 12, 31),
                is_active=False,
                market_cap=1e9,
                last_filing_date=date(2020, 6, 30),
                delist_detected_at=date(2020, 12, 31),
                last_known_price=42.50,  # Already filled
            )
        )
        await session.commit()

        updated = await fill_last_known_prices(session)
        assert updated == 0

    @pytest.mark.asyncio
    async def test_fill_last_known_prices_no_price_data(self, session: AsyncSession) -> None:
        """Delisted ticker with no price data is not updated."""
        session.add(
            PITUniverseMembership(
                ticker="GONE",
                cik="0000123456",
                quarter_date=date(2020, 12, 31),
                is_active=False,
                market_cap=1e9,
                last_filing_date=date(2020, 6, 30),
                delist_detected_at=date(2020, 12, 31),
                last_known_price=None,
            )
        )
        await session.commit()

        updated = await fill_last_known_prices(session)
        assert updated == 0
