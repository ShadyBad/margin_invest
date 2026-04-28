"""Incremental daily PIT data update pipeline.

Keeps point-in-time tables current by:
1. Checking EDGAR for new 10-K/10-Q filings
2. Appending yesterday's prices for active universe tickers
3. Refreshing universe membership near quarter ends

Designed to run daily at 23:00 UTC via the ARQ worker.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from margin_api.db.models import PITFinancialSnapshot, PITUniverseMembership
from margin_api.services.edgar.backfill import (
    _infer_fiscal_info,
    fetch_and_parse_filing,
    insert_pit_snapshot,
)
from margin_api.services.edgar.index_builder import (
    USER_AGENT,
    fetch_quarter_index,
    load_cik_ticker_map,
)
from margin_api.services.edgar.price_backfill import backfill_prices_for_tickers
from margin_api.services.edgar.universe_assembly import (
    assemble_universe,
    fill_last_known_prices,
)

if TYPE_CHECKING:
    from arq.connections import ArqRedis

logger = logging.getLogger(__name__)


def _is_near_quarter_end(today: date) -> bool:
    """Check if today is within 5 days of a quarter end.

    Quarter ends: Mar 31, Jun 30, Sep 30, Dec 31.

    Args:
        today: The date to check.

    Returns:
        True if today is in a quarter-end month and day >= 26.
    """
    return today.month in (3, 6, 9, 12) and today.day >= 26


def _current_quarter(today: date) -> tuple[int, int]:
    """Determine the current EDGAR quarter (year, quarter) from today's date.

    Returns:
        Tuple of (year, quarter_number) where quarter_number is 1-4.
    """
    month = today.month
    if month <= 3:
        return today.year, 1
    elif month <= 6:
        return today.year, 2
    elif month <= 9:
        return today.year, 3
    else:
        return today.year, 4


async def check_new_filings(
    session_factory: async_sessionmaker[AsyncSession],
    lookback_days: int = 2,
    redis: ArqRedis | None = None,
) -> dict[str, int]:
    """Check EDGAR for new 10-K/10-Q filings and ingest them.

    Fetches the current quarter's EDGAR index, filters to filings with known
    tickers, skips those already in the database, and inserts new ones.
    If *redis* is provided, enqueues an ``analyze_filing_text`` ARQ job for
    each newly inserted filing.

    Args:
        session_factory: Async SQLAlchemy session factory.
        lookback_days: Not currently used (kept for API consistency). The
            function checks the entire current quarter's index.
        redis: Optional ARQ redis connection for enqueueing NLP analysis jobs.

    Returns:
        Dict with keys: new_filings, failed.
    """
    today = date.today()
    year, quarter = _current_quarter(today)

    logger.info(
        "[daily-update] Checking EDGAR Q%d %d for new filings...",
        quarter,
        year,
    )

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30.0),
    ) as client:
        # Fetch current quarter index
        entries = await fetch_quarter_index(client, year, quarter)

        if not entries:
            logger.info("[daily-update] No entries in Q%d %d index", quarter, year)
            return {"new_filings": 0, "failed": 0}

        # Load CIK->ticker map
        cik_map = await load_cik_ticker_map(client)

    # Filter to entries with known tickers and 10-K/10-Q forms
    entries_with_ticker = [
        (entry, cik_map[entry.cik_int]) for entry in entries if entry.cik_int in cik_map
    ]

    if not entries_with_ticker:
        logger.info("[daily-update] No entries with known tickers")
        return {"new_filings": 0, "failed": 0}

    # Check which accession numbers already exist in the database
    async with session_factory() as session:
        result = await session.execute(select(PITFinancialSnapshot.accession_number))
        existing_accessions = {row[0] for row in result.all()}

    # Filter to new filings only
    new_entries = [
        (entry, ticker)
        for entry, ticker in entries_with_ticker
        if entry.accession_number not in existing_accessions
    ]

    if not new_entries:
        logger.info("[daily-update] No new filings to ingest")
        return {"new_filings": 0, "failed": 0}

    logger.info("[daily-update] Found %d new filings to ingest", len(new_entries))

    # Fetch, parse, and insert each new filing
    new_filings = 0
    failed = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(30.0),
    ) as client:
        for entry, ticker in new_entries:
            fiscal_year, fiscal_quarter = _infer_fiscal_info(entry)

            financials = await fetch_and_parse_filing(client, entry)
            if financials is None:
                failed += 1
                continue

            async with session_factory() as session:
                was_inserted = await insert_pit_snapshot(
                    session,
                    entry,
                    financials,
                    ticker,
                    fiscal_year,
                    fiscal_quarter,
                )
                await session.commit()
                if was_inserted:
                    new_filings += 1
                    # Enqueue text extraction + NLP analysis if redis is available
                    if redis is not None:
                        # Fetch the snapshot id just inserted
                        from sqlalchemy import select as _select

                        result = await session.execute(
                            _select(PITFinancialSnapshot).where(
                                PITFinancialSnapshot.accession_number == entry.accession_number
                            )
                        )
                        snapshot = result.scalar_one_or_none()
                        if snapshot is not None:
                            job_id = f"analyze-filing-{snapshot.id}"
                            await redis.enqueue_job(
                                "analyze_filing_text",
                                ticker,
                                snapshot.id,
                                _job_id=job_id,
                            )
                            logger.info(
                                "[daily-update] Enqueued analyze_filing_text for %s (id=%d)",
                                ticker,
                                snapshot.id,
                            )

    logger.info(
        "[daily-update] Filing check complete: %d new, %d failed",
        new_filings,
        failed,
    )

    return {"new_filings": new_filings, "failed": failed}


async def append_daily_prices(
    session_factory: async_sessionmaker[AsyncSession],
    lookback_days: int = 3,
) -> dict[str, int]:
    """Append recent daily prices for all active universe tickers.

    Queries pit_universe_memberships for active tickers and downloads
    the last few days of price data via yfinance.

    Args:
        session_factory: Async SQLAlchemy session factory.
        lookback_days: Number of days to look back for price data.

    Returns:
        Dict with keys: tickers_updated, rows_inserted.
    """
    today = date.today()
    start = (today - timedelta(days=lookback_days)).isoformat()
    end = today.isoformat()

    # Query active tickers from the most recent quarter's universe membership
    async with session_factory() as session:
        stmt = (
            select(PITUniverseMembership.ticker)
            .where(PITUniverseMembership.is_active.is_(True))
            .distinct()
        )
        result = await session.execute(stmt)
        tickers = [row[0] for row in result.all()]

    # Benchmarks are NOT in pit_universe_memberships (they're ETFs, not
    # candidate stocks). The audit and dashboard read benchmark prices from
    # pit_daily_prices and need them updated daily, same cadence as the universe.
    # Without this union, benchmark series silently lag by however long it has
    # been since the last manual price-backfill --tickers BENCH run.
    benchmarks = {"SPY"}
    tickers = list(set(tickers) | benchmarks)

    if not tickers:
        logger.info("[daily-update] No active tickers in universe — skipping price append")
        return {"tickers_updated": 0, "rows_inserted": 0}

    logger.info(
        "[daily-update] Appending prices for %d tickers (%s to %s)...",
        len(tickers),
        start,
        end,
    )

    summary = await backfill_prices_for_tickers(
        tickers=tickers,
        start_date=start,
        end_date=end,
        session_factory=session_factory,
    )

    tickers_updated = len(summary)
    rows_inserted = sum(summary.values())

    logger.info(
        "[daily-update] Price append complete: %d tickers, %d rows",
        tickers_updated,
        rows_inserted,
    )

    return {"tickers_updated": tickers_updated, "rows_inserted": rows_inserted}


async def refresh_universe_if_quarter_end(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict | None:
    """Refresh universe membership if today is near a quarter end.

    Checks if today is within 5 days of Mar 31, Jun 30, Sep 30, or Dec 31.
    If so, runs assemble_universe and fill_last_known_prices.

    Args:
        session_factory: Async SQLAlchemy session factory.

    Returns:
        Summary dict if refresh ran, None if skipped.
    """
    today = date.today()

    if not _is_near_quarter_end(today):
        logger.info(
            "[daily-update] Not near quarter end (%s) — skipping universe refresh",
            today.isoformat(),
        )
        return None

    logger.info(
        "[daily-update] Near quarter end (%s) — refreshing universe membership...",
        today.isoformat(),
    )

    async with session_factory() as session:
        assembly_result = await assemble_universe(session)
        prices_filled = await fill_last_known_prices(session)

    logger.info(
        "[daily-update] Universe refresh complete: %d quarters, %d delistings, %d prices filled",
        assembly_result["quarters_processed"],
        assembly_result["delistings_detected"],
        prices_filled,
    )

    return {
        "quarters_refreshed": assembly_result["quarters_processed"],
        "delistings": assembly_result["delistings_detected"],
        "prices_filled": prices_filled,
    }


async def run_daily_pit_update(
    session_factory: async_sessionmaker[AsyncSession],
    redis: ArqRedis | None = None,
) -> dict:
    """Run the complete daily PIT data update pipeline.

    Calls all three sub-functions in sequence:
    1. check_new_filings — discover and ingest new EDGAR filings
    2. append_daily_prices — download recent prices for active universe
    3. refresh_universe_if_quarter_end — rebuild membership near quarter ends

    Args:
        session_factory: Async SQLAlchemy session factory.
        redis: Optional ARQ redis connection for enqueueing NLP analysis jobs.

    Returns:
        Combined summary dict with filings, prices, and universe results.
    """
    logger.info("[daily-update] Starting daily PIT update pipeline...")

    filings_result = await check_new_filings(session_factory, redis=redis)
    prices_result = await append_daily_prices(session_factory)
    universe_result = await refresh_universe_if_quarter_end(session_factory)

    result = {
        "filings": filings_result,
        "prices": prices_result,
        "universe": universe_result,
    }

    logger.info("[daily-update] Daily PIT update complete: %s", result)

    return result
