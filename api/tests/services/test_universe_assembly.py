"""Tests for the universe assembly service.

Covers:
- detect_delistings: detecting tickers missing 8+ consecutive quarters (default)
- build_quarterly_membership: building row dicts for pit_universe_memberships
- assemble_universe: end-to-end integration querying pit_financial_snapshots
- fill_last_known_prices: backfilling last_known_price for delisted tickers
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import PITDailyPrice, PITFinancialSnapshot, PITUniverseMembership
from margin_api.services.edgar.universe_assembly import (
    _batch_compute_avg_volumes,
    _batch_compute_market_caps,
    assemble_universe,
    build_quarterly_membership,
    detect_delistings,
    fill_last_known_prices,
)
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
        """Ticker missing 2+ consecutive quarters is marked delisted (with threshold=2)."""
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
        result = detect_delistings(filing_quarters, all_quarters, consecutive_miss_threshold=2)
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
        """Delist detected at = the quarter where threshold consecutive misses are confirmed."""
        filing_quarters = {
            "GONE": [date(2020, 3, 31)],
        }
        all_quarters = [
            date(2020, 3, 31),
            date(2020, 6, 30),
            date(2020, 9, 30),
            date(2020, 12, 31),
        ]
        result = detect_delistings(filing_quarters, all_quarters, consecutive_miss_threshold=2)
        assert "GONE" in result
        # Missing Q2 and Q3 → detected at Q3 (the quarter where 2 consecutive misses are confirmed)
        assert result["GONE"] == date(2020, 9, 30)

    def test_detect_delistings_missing_at_end(self) -> None:
        """Ticker missing the last 2 quarters is delisted (with threshold=2)."""
        filing_quarters = {
            "LATE": [date(2020, 3, 31), date(2020, 6, 30)],
        }
        all_quarters = [
            date(2020, 3, 31),
            date(2020, 6, 30),
            date(2020, 9, 30),
            date(2020, 12, 31),
        ]
        result = detect_delistings(filing_quarters, all_quarters, consecutive_miss_threshold=2)
        assert "LATE" in result
        assert result["LATE"] == date(2020, 12, 31)

    def test_detect_delistings_three_missing_uses_first_detection(self) -> None:
        """With 3+ consecutive misses, detection date is at the threshold-th miss."""
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
        result = detect_delistings(filing_quarters, all_quarters, consecutive_miss_threshold=2)
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
        result = detect_delistings(filing_quarters, all_quarters, consecutive_miss_threshold=2)
        # Missing all quarters — detected at Q2 (2nd consecutive miss)
        assert "GHOST" in result
        assert result["GHOST"] == date(2020, 6, 30)

    def test_annual_filer_not_delisted_with_8q_threshold(self) -> None:
        """Annual filers that miss 3-4 quarters between 10-Ks should NOT be marked delisted."""
        quarters = [date(2020, m, d) for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]]
        quarters += [date(2021, m, d) for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]]

        # Annual filer: files only in Q4 (10-K)
        filing_quarters = {"ANNUAL": [date(2020, 12, 31), date(2021, 12, 31)]}

        delistings = detect_delistings(filing_quarters, quarters)
        assert "ANNUAL" not in delistings

    def test_truly_delisted_after_8_quarters(self) -> None:
        """A ticker missing 8+ consecutive quarters should be delisted."""
        quarters = [
            date(2019 + y, m, d)
            for y in range(4)
            for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]
        ]

        # Filed in Q1 2019 only
        filing_quarters = {"GONE": [date(2019, 3, 31)]}

        delistings = detect_delistings(filing_quarters, quarters)
        assert "GONE" in delistings


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
        # With threshold=8, GONE only misses 2 quarters — NOT delisted
        assert result["delistings_detected"] == 0

        # Verify rows were inserted
        from sqlalchemy import select

        stmt = select(PITUniverseMembership)
        rows = (await session.execute(stmt)).scalars().all()
        assert len(rows) > 0

        # GONE still active — only 2 consecutive misses, well below threshold of 8
        gone_q4 = [r for r in rows if r.ticker == "GONE" and r.quarter_date == date(2020, 12, 31)]
        assert len(gone_q4) == 1
        assert gone_q4[0].is_active is True
        assert gone_q4[0].delist_detected_at is None

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

        stmt = select(PITUniverseMembership).where(PITUniverseMembership.ticker == "GONE")
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


# ---------------------------------------------------------------------------
# _batch_compute_market_caps tests
# ---------------------------------------------------------------------------


class TestBatchComputeMarketCaps:
    @pytest.mark.asyncio
    async def test_market_cap_from_shares_and_price(self, session: AsyncSession) -> None:
        """market_cap = shares_outstanding * close for membership rows with NULL market_cap."""
        # Create a membership row with NULL market_cap
        session.add(
            PITUniverseMembership(
                ticker="AAPL",
                cik="0000320193",
                quarter_date=date(2020, 9, 30),
                is_active=True,
                market_cap=None,
                last_filing_date=date(2020, 9, 30),
            )
        )
        # Filing with shares_outstanding at or before quarter_date
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2020, 8, 1),
                period_end=date(2020, 6, 30),
                accession_number="0000320193-20-000001",
                fiscal_year=2020,
                fiscal_quarter=2,
            )
        )
        # Price at quarter_date
        session.add(_make_price(ticker="AAPL", price_date=date(2020, 9, 30), close=115.0))
        await session.commit()

        updated = await _batch_compute_market_caps(session)
        assert updated == 1

        from sqlalchemy import select

        row = (
            await session.execute(
                select(PITUniverseMembership).where(PITUniverseMembership.ticker == "AAPL")
            )
        ).scalars().first()
        assert row is not None
        # shares_outstanding=1_000_000_000 (from _make_filing) * close=115.0
        assert row.market_cap == pytest.approx(1_000_000_000 * 115.0)

    @pytest.mark.asyncio
    async def test_market_cap_skips_already_filled(self, session: AsyncSession) -> None:
        """Rows with existing market_cap are not recomputed."""
        session.add(
            PITUniverseMembership(
                ticker="AAPL",
                cik="0000320193",
                quarter_date=date(2020, 9, 30),
                is_active=True,
                market_cap=2.5e12,
                last_filing_date=date(2020, 9, 30),
            )
        )
        await session.commit()

        updated = await _batch_compute_market_caps(session)
        assert updated == 0

    @pytest.mark.asyncio
    async def test_market_cap_no_price_data(self, session: AsyncSession) -> None:
        """If there's no price data, market_cap stays NULL."""
        session.add(
            PITUniverseMembership(
                ticker="AAPL",
                cik="0000320193",
                quarter_date=date(2020, 9, 30),
                is_active=True,
                market_cap=None,
                last_filing_date=date(2020, 9, 30),
            )
        )
        session.add(
            _make_filing(
                ticker="AAPL",
                filing_date=date(2020, 8, 1),
                period_end=date(2020, 6, 30),
                accession_number="0000320193-20-000001",
            )
        )
        # No price data at all
        await session.commit()

        updated = await _batch_compute_market_caps(session)
        assert updated == 0


# ---------------------------------------------------------------------------
# _batch_compute_avg_volumes tests
# ---------------------------------------------------------------------------


class TestBatchComputeAvgVolumes:
    @pytest.mark.asyncio
    async def test_avg_volume_computed(self, session: AsyncSession) -> None:
        """avg_daily_volume = mean(close * volume) over trailing trading days."""
        session.add(
            PITUniverseMembership(
                ticker="AAPL",
                cik="0000320193",
                quarter_date=date(2020, 9, 30),
                is_active=True,
                market_cap=2.5e12,
                avg_daily_volume=None,
                last_filing_date=date(2020, 9, 30),
            )
        )
        # Add 5 trading days of price data before quarter_date
        for i in range(5):
            d = date(2020, 9, 25 + i)  # Sep 25-29
            session.add(
                PITDailyPrice(
                    ticker="AAPL",
                    date=d,
                    open=110.0,
                    high=120.0,
                    low=100.0,
                    close=115.0,
                    adj_close=115.0,
                    volume=10_000_000,
                    source="yfinance",
                )
            )
        await session.commit()

        updated = await _batch_compute_avg_volumes(session)
        assert updated == 1

        from sqlalchemy import select

        row = (
            await session.execute(
                select(PITUniverseMembership).where(PITUniverseMembership.ticker == "AAPL")
            )
        ).scalars().first()
        assert row is not None
        # All 5 days: close=115, volume=10M => dollar_vol = 1.15B each
        expected = 115.0 * 10_000_000
        assert row.avg_daily_volume == pytest.approx(expected)

    @pytest.mark.asyncio
    async def test_avg_volume_skips_already_filled(self, session: AsyncSession) -> None:
        """Rows with existing avg_daily_volume are not recomputed."""
        session.add(
            PITUniverseMembership(
                ticker="AAPL",
                cik="0000320193",
                quarter_date=date(2020, 9, 30),
                is_active=True,
                market_cap=2.5e12,
                avg_daily_volume=1.5e9,
                last_filing_date=date(2020, 9, 30),
            )
        )
        await session.commit()

        updated = await _batch_compute_avg_volumes(session)
        assert updated == 0

    @pytest.mark.asyncio
    async def test_avg_volume_no_price_data(self, session: AsyncSession) -> None:
        """If there's no price data, avg_daily_volume stays NULL."""
        session.add(
            PITUniverseMembership(
                ticker="AAPL",
                cik="0000320193",
                quarter_date=date(2020, 9, 30),
                is_active=True,
                market_cap=2.5e12,
                avg_daily_volume=None,
                last_filing_date=date(2020, 9, 30),
            )
        )
        await session.commit()

        updated = await _batch_compute_avg_volumes(session)
        assert updated == 0
