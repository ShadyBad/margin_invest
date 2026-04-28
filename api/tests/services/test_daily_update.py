"""Tests for the daily PIT update pipeline.

Covers:
- check_new_filings: discovering and ingesting new EDGAR filings
- append_daily_prices: appending recent prices for active universe
- refresh_universe_if_quarter_end: quarter-end detection and universe refresh
- run_daily_pit_update: orchestrator combining all three
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import PITFinancialSnapshot, PITUniverseMembership
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


# ---------------------------------------------------------------------------
# refresh_universe_if_quarter_end tests
# ---------------------------------------------------------------------------


class TestRefreshUniverseIfQuarterEnd:
    def test_refresh_universe_skips_non_quarter_end(self) -> None:
        """Should return None when not near quarter end."""
        from margin_api.services.edgar.daily_update import _is_near_quarter_end

        # Feb 15 is not near any quarter end
        assert _is_near_quarter_end(date(2026, 2, 15)) is False
        # Jan 10 is not near any quarter end
        assert _is_near_quarter_end(date(2026, 1, 10)) is False
        # Jul 5 is not near any quarter end
        assert _is_near_quarter_end(date(2026, 7, 5)) is False

    def test_refresh_universe_runs_at_quarter_end(self) -> None:
        """Should detect quarter end when near quarter boundary."""
        from margin_api.services.edgar.daily_update import _is_near_quarter_end

        # Mar 28 — within 5 days of Mar 31
        assert _is_near_quarter_end(date(2026, 3, 28)) is True
        # Jun 30 — exact quarter end
        assert _is_near_quarter_end(date(2026, 6, 30)) is True
        # Sep 26 — within 5 days of Sep 30
        assert _is_near_quarter_end(date(2026, 9, 26)) is True
        # Dec 31 — exact quarter end
        assert _is_near_quarter_end(date(2026, 12, 31)) is True
        # Dec 27 — within 5 days of Dec 31
        assert _is_near_quarter_end(date(2026, 12, 27)) is True

    @pytest.mark.asyncio
    async def test_refresh_universe_returns_none_when_not_quarter_end(
        self, session_factory
    ) -> None:
        """refresh_universe_if_quarter_end should return None mid-quarter."""
        from margin_api.services.edgar.daily_update import refresh_universe_if_quarter_end

        with patch("margin_api.services.edgar.daily_update.date") as mock_date:
            mock_date.today.return_value = date(2026, 2, 15)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            result = await refresh_universe_if_quarter_end(session_factory)
            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_universe_calls_assembly_at_quarter_end(self, session_factory) -> None:
        """refresh_universe_if_quarter_end should call assemble_universe near quarter end."""
        from margin_api.services.edgar.daily_update import refresh_universe_if_quarter_end

        mock_assemble = AsyncMock(
            return_value={
                "quarters_processed": 1,
                "tickers_tracked": 5,
                "delistings_detected": 0,
            }
        )
        mock_fill = AsyncMock(return_value=0)

        with (
            patch("margin_api.services.edgar.daily_update.date") as mock_date,
            patch(
                "margin_api.services.edgar.daily_update.assemble_universe",
                mock_assemble,
            ),
            patch(
                "margin_api.services.edgar.daily_update.fill_last_known_prices",
                mock_fill,
            ),
        ):
            mock_date.today.return_value = date(2026, 3, 28)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            result = await refresh_universe_if_quarter_end(session_factory)

            assert result is not None
            assert result["quarters_refreshed"] == 1
            mock_assemble.assert_called_once()
            mock_fill.assert_called_once()


# ---------------------------------------------------------------------------
# append_daily_prices tests
# ---------------------------------------------------------------------------


class TestAppendDailyPrices:
    @pytest.mark.asyncio
    async def test_append_daily_prices_empty_universe_still_updates_benchmarks(
        self, session_factory
    ) -> None:
        """Empty universe still updates benchmarks (SPY) — they're not in pit_universe_memberships."""
        from margin_api.services.edgar.daily_update import append_daily_prices

        mock_backfill = AsyncMock(return_value={"SPY": 3})

        with patch(
            "margin_api.services.edgar.daily_update.backfill_prices_for_tickers",
            mock_backfill,
        ):
            result = await append_daily_prices(session_factory, lookback_days=3)

        assert result["tickers_updated"] == 1
        assert result["rows_inserted"] == 3
        # Benchmarks always passed to backfill, even with empty universe.
        call_args = mock_backfill.call_args
        tickers_arg = call_args[0][0] if call_args[0] else call_args[1].get("tickers")
        assert set(tickers_arg) == {"SPY"}

    @pytest.mark.asyncio
    async def test_append_daily_prices_with_active_tickers(self, session, session_factory) -> None:
        """Should call backfill_prices_for_tickers for active universe tickers."""
        from margin_api.services.edgar.daily_update import append_daily_prices

        # Insert active universe members
        session.add(
            PITUniverseMembership(
                ticker="AAPL",
                cik="0000320193",
                quarter_date=date(2026, 3, 31),
                is_active=True,
                market_cap=3e12,
                last_filing_date=date(2026, 2, 1),
            )
        )
        session.add(
            PITUniverseMembership(
                ticker="MSFT",
                cik="0000789019",
                quarter_date=date(2026, 3, 31),
                is_active=True,
                market_cap=2.8e12,
                last_filing_date=date(2026, 2, 1),
            )
        )
        # Inactive ticker — should NOT be included
        session.add(
            PITUniverseMembership(
                ticker="GONE",
                cik="0000123456",
                quarter_date=date(2026, 3, 31),
                is_active=False,
                market_cap=1e9,
                last_filing_date=date(2025, 6, 30),
                delist_detected_at=date(2025, 12, 31),
            )
        )
        await session.commit()

        mock_backfill = AsyncMock(return_value={"AAPL": 3, "MSFT": 3, "SPY": 3})

        with patch(
            "margin_api.services.edgar.daily_update.backfill_prices_for_tickers",
            mock_backfill,
        ):
            result = await append_daily_prices(session_factory, lookback_days=3)

        # Universe (2 active) + benchmarks (SPY) = 3 tickers, 9 rows.
        assert result["tickers_updated"] == 3
        assert result["rows_inserted"] == 9

        # Verify universe tickers AND SPY benchmark were passed.
        call_args = mock_backfill.call_args
        tickers_arg = call_args[0][0] if call_args[0] else call_args[1].get("tickers")
        assert set(tickers_arg) == {"AAPL", "MSFT", "SPY"}


# ---------------------------------------------------------------------------
# check_new_filings tests
# ---------------------------------------------------------------------------


class TestCheckNewFilings:
    @pytest.mark.asyncio
    async def test_check_new_filings_no_new(self, session_factory) -> None:
        """Should handle no new filings gracefully."""
        from margin_api.services.edgar.daily_update import check_new_filings

        # Mock fetch_quarter_index to return empty list
        mock_fetch = AsyncMock(return_value=[])
        mock_cik_map = AsyncMock(return_value={})

        with (
            patch(
                "margin_api.services.edgar.daily_update.fetch_quarter_index",
                mock_fetch,
            ),
            patch(
                "margin_api.services.edgar.daily_update.load_cik_ticker_map",
                mock_cik_map,
            ),
        ):
            result = await check_new_filings(session_factory, lookback_days=2)

        assert result["new_filings"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_check_new_filings_skips_existing(self, session, session_factory) -> None:
        """Should skip filings that already exist in the database."""
        from margin_api.services.edgar.daily_update import check_new_filings
        from margin_api.services.edgar.index_builder import EdgarIndexEntry

        # Insert an existing filing
        session.add(
            PITFinancialSnapshot(
                cik="320193",
                ticker="AAPL",
                filing_date=date(2026, 2, 15),
                period_end=date(2025, 12, 31),
                form_type="10-K",
                accession_number="0000320193-26-000001",
                income_statement={"revenue": 100},
                balance_sheet={"assets": 200},
                cash_flow={"operating": 50},
                shares_outstanding=15_000_000_000,
                fiscal_year=2025,
                fiscal_quarter=None,
                ingested_at=datetime.now(UTC),
            )
        )
        await session.commit()

        # Mock the index to return the same filing that's already in DB
        existing_entry = EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-K",
            cik="320193",
            date_filed="2026-02-15",
            accession_number="0000320193-26-000001",
            filename="edgar/data/320193/0000320193-26-000001.txt",
        )
        mock_fetch = AsyncMock(return_value=[existing_entry])
        mock_cik_map = AsyncMock(return_value={320193: "AAPL"})

        with (
            patch(
                "margin_api.services.edgar.daily_update.fetch_quarter_index",
                mock_fetch,
            ),
            patch(
                "margin_api.services.edgar.daily_update.load_cik_ticker_map",
                mock_cik_map,
            ),
        ):
            result = await check_new_filings(session_factory, lookback_days=2)

        # Existing filing should be skipped — no new filings
        assert result["new_filings"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_check_new_filings_ingests_new(self, session, session_factory) -> None:
        """Should fetch and ingest genuinely new filings."""
        from margin_api.services.edgar.daily_update import check_new_filings
        from margin_api.services.edgar.index_builder import EdgarIndexEntry
        from margin_api.services.edgar.xbrl_parser import XBRLFinancials

        new_entry = EdgarIndexEntry(
            company_name="APPLE INC",
            form_type="10-Q",
            cik="320193",
            date_filed="2026-02-20",
            accession_number="0000320193-26-000099",
            filename="edgar/data/320193/0000320193-26-000099.txt",
        )
        mock_fetch = AsyncMock(return_value=[new_entry])
        mock_cik_map = AsyncMock(return_value={320193: "AAPL"})
        mock_parse = AsyncMock(
            return_value=XBRLFinancials(
                income_statement={"revenue": 95_000_000_000},
                balance_sheet={"total_assets": 350_000_000_000},
                cash_flow={"operating_cash_flow": 26_000_000_000},
                shares_outstanding=15_000_000_000,
            )
        )

        with (
            patch(
                "margin_api.services.edgar.daily_update.fetch_quarter_index",
                mock_fetch,
            ),
            patch(
                "margin_api.services.edgar.daily_update.load_cik_ticker_map",
                mock_cik_map,
            ),
            patch(
                "margin_api.services.edgar.daily_update.fetch_and_parse_filing",
                mock_parse,
            ),
        ):
            result = await check_new_filings(session_factory, lookback_days=2)

        assert result["new_filings"] == 1
        assert result["failed"] == 0


# ---------------------------------------------------------------------------
# run_daily_pit_update tests
# ---------------------------------------------------------------------------


class TestRunDailyPitUpdate:
    @pytest.mark.asyncio
    async def test_run_daily_pit_update_combines_results(self, session_factory) -> None:
        """run_daily_pit_update should call all 3 sub-functions and combine results."""
        from margin_api.services.edgar.daily_update import run_daily_pit_update

        with (
            patch(
                "margin_api.services.edgar.daily_update.check_new_filings",
                AsyncMock(return_value={"new_filings": 2, "failed": 1}),
            ),
            patch(
                "margin_api.services.edgar.daily_update.append_daily_prices",
                AsyncMock(return_value={"tickers_updated": 10, "rows_inserted": 30}),
            ),
            patch(
                "margin_api.services.edgar.daily_update.refresh_universe_if_quarter_end",
                AsyncMock(return_value=None),
            ),
        ):
            result = await run_daily_pit_update(session_factory)

        assert result["filings"]["new_filings"] == 2
        assert result["filings"]["failed"] == 1
        assert result["prices"]["tickers_updated"] == 10
        assert result["prices"]["rows_inserted"] == 30
        assert result["universe"] is None

    @pytest.mark.asyncio
    async def test_run_daily_pit_update_with_universe_refresh(self, session_factory) -> None:
        """run_daily_pit_update should include universe results when near quarter end."""
        from margin_api.services.edgar.daily_update import run_daily_pit_update

        with (
            patch(
                "margin_api.services.edgar.daily_update.check_new_filings",
                AsyncMock(return_value={"new_filings": 0, "failed": 0}),
            ),
            patch(
                "margin_api.services.edgar.daily_update.append_daily_prices",
                AsyncMock(return_value={"tickers_updated": 5, "rows_inserted": 15}),
            ),
            patch(
                "margin_api.services.edgar.daily_update.refresh_universe_if_quarter_end",
                AsyncMock(return_value={"quarters_refreshed": 1, "delistings": 0}),
            ),
        ):
            result = await run_daily_pit_update(session_factory)

        assert result["universe"] is not None
        assert result["universe"]["quarters_refreshed"] == 1
