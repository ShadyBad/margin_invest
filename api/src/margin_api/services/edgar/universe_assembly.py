"""Universe assembly service: builds quarterly universe membership from PIT financial snapshots.

Scans pit_financial_snapshots to determine which tickers were active each quarter,
detects delistings when a company stops filing for 2+ consecutive quarters, and
populates pit_universe_memberships. Also backfills last_known_price for delisted tickers.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import PITDailyPrice, PITFinancialSnapshot, PITUniverseMembership

logger = logging.getLogger(__name__)

# Standard quarter end dates (month, day)
QUARTER_ENDS = [(3, 31), (6, 30), (9, 30), (12, 31)]


def _filing_date_to_quarter(filing_date: date) -> date:
    """Map a filing date to its nearest quarter end date.

    A filing is assigned to the quarter end that most recently passed.
    For example, a filing on 2020-05-01 maps to Q1 (2020-03-31).
    A filing on 2020-01-15 maps to Q4 of the previous year (2019-12-31).
    """
    year = filing_date.year
    for month, day in QUARTER_ENDS:
        qend = date(year, month, day)
        if filing_date <= qend:
            # This quarter hasn't ended yet — use the previous quarter
            idx = QUARTER_ENDS.index((month, day))
            if idx == 0:
                return date(year - 1, 12, 31)
            prev_month, prev_day = QUARTER_ENDS[idx - 1]
            return date(year, prev_month, prev_day)
    # Past Dec 31 — shouldn't happen, but return Q4 of current year
    return date(year, 12, 31)


def _period_end_to_quarter(period_end: date) -> date:
    """Map a period_end date to the nearest standard quarter end.

    Period end dates like 2020-09-28 map to 2020-09-30,
    and 2020-03-28 maps to 2020-03-31.
    """
    year = period_end.year
    best = None
    best_diff = None
    for month, day in QUARTER_ENDS:
        qend = date(year, month, day)
        diff = abs((qend - period_end).days)
        if best_diff is None or diff < best_diff:
            best = qend
            best_diff = diff
    return best  # type: ignore[return-value]


def detect_delistings(
    filing_quarters: dict[str, list[date]],
    all_quarters: list[date],
) -> dict[str, date]:
    """Detect tickers that stopped filing for 2+ consecutive quarters.

    Args:
        filing_quarters: {ticker: [quarter_dates_they_filed]}
        all_quarters: sorted list of all quarter end dates

    Returns:
        {ticker: delist_detected_date} for tickers missing 2+ consecutive quarters.
        "Detected at" = the quarter where 2 consecutive misses are confirmed
        (i.e., the 2nd consecutive missing quarter).
    """
    if len(all_quarters) < 2:
        return {}

    delistings: dict[str, date] = {}

    for ticker, filed_quarters in filing_quarters.items():
        filed_set = set(filed_quarters)
        consecutive_misses = 0

        for q in all_quarters:
            if q in filed_set:
                consecutive_misses = 0
            else:
                consecutive_misses += 1
                if consecutive_misses >= 2:
                    delistings[ticker] = q
                    break

    return delistings


def build_quarterly_membership(
    quarter_date: date,
    active_tickers: dict[str, tuple[str, date, float | None]],
    delistings: dict[str, date],
) -> list[dict[str, Any]]:
    """Build row dicts for pit_universe_memberships for a single quarter.

    Args:
        quarter_date: The quarter end date.
        active_tickers: {ticker: (cik, last_filing_date, market_cap)}
        delistings: {ticker: delist_detected_date}

    Returns:
        List of row dicts for insertion into pit_universe_memberships.
    """
    rows: list[dict[str, Any]] = []

    for ticker, (cik, last_filing_date, market_cap) in active_tickers.items():
        delist_date = delistings.get(ticker)
        is_delisted = delist_date is not None and quarter_date >= delist_date

        rows.append(
            {
                "ticker": ticker,
                "cik": cik,
                "quarter_date": quarter_date,
                "is_active": not is_delisted,
                "market_cap": market_cap,
                "last_filing_date": last_filing_date,
                "delist_detected_at": delist_date if is_delisted else None,
                "last_known_price": None,
            }
        )

    return rows


async def assemble_universe(session: AsyncSession) -> dict[str, int]:
    """Scan pit_financial_snapshots and populate pit_universe_memberships.

    1. Query all unique (ticker, cik, filing_date, period_end) from pit_financial_snapshots
    2. Group filings into quarters using period_end
    3. For each quarter: determine which tickers filed
    4. Detect delistings across all quarters
    5. For each quarter: build membership rows and insert with on_conflict_do_nothing
    6. Returns {"quarters_processed": N, "tickers_tracked": M, "delistings_detected": K}
    """
    # Step 1: Query all filings
    stmt = select(
        PITFinancialSnapshot.ticker,
        PITFinancialSnapshot.cik,
        PITFinancialSnapshot.filing_date,
        PITFinancialSnapshot.period_end,
    )
    result = await session.execute(stmt)
    filings = result.all()

    if not filings:
        return {"quarters_processed": 0, "tickers_tracked": 0, "delistings_detected": 0}

    # Step 2: Group into quarters using period_end
    # Track: ticker -> set of quarter dates, and ticker -> (cik, last_filing_date, market_cap)
    filing_quarters: dict[str, set[date]] = {}
    ticker_info: dict[str, dict[date, tuple[str, date]]] = {}
    # ticker_info maps: ticker -> {quarter_date: (cik, filing_date)}

    all_quarter_set: set[date] = set()

    for ticker, cik, filing_date, period_end in filings:
        quarter = _period_end_to_quarter(period_end)
        all_quarter_set.add(quarter)

        if ticker not in filing_quarters:
            filing_quarters[ticker] = set()
        filing_quarters[ticker].add(quarter)

        if ticker not in ticker_info:
            ticker_info[ticker] = {}
        # Keep the latest filing_date for each quarter
        existing = ticker_info[ticker].get(quarter)
        if existing is None or filing_date > existing[1]:
            ticker_info[ticker][quarter] = (cik, filing_date)

    all_quarters = sorted(all_quarter_set)

    # Convert filing_quarters sets to sorted lists for detect_delistings
    filing_quarters_lists: dict[str, list[date]] = {
        ticker: sorted(quarters) for ticker, quarters in filing_quarters.items()
    }

    # Step 3: Detect delistings
    delistings = detect_delistings(filing_quarters_lists, all_quarters)

    # Step 4: Build and insert membership rows per quarter
    all_tickers = set(filing_quarters.keys())
    total_rows_inserted = 0

    # Detect dialect for insert strategy
    dialect_name = session.bind.dialect.name if session.bind else "postgresql"

    for quarter in all_quarters:
        # Build active_tickers for this quarter: all tickers that have ever filed up to this quarter
        active_tickers: dict[str, tuple[str, date, float | None]] = {}
        for ticker in all_tickers:
            # Find the most recent filing info for this ticker up to this quarter
            best_quarter = None
            for q in all_quarters:
                if q > quarter:
                    break
                if q in ticker_info.get(ticker, {}):
                    best_quarter = q
            if best_quarter is not None:
                cik, filing_date = ticker_info[ticker][best_quarter]
                active_tickers[ticker] = (cik, filing_date, None)

        rows = build_quarterly_membership(quarter, active_tickers, delistings)

        if rows:
            if dialect_name == "sqlite":
                # SQLite fallback: INSERT OR IGNORE
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert

                for row in rows:
                    stmt_ins = sqlite_insert(PITUniverseMembership).values(**row)
                    stmt_ins = stmt_ins.on_conflict_do_nothing(
                        index_elements=["ticker", "quarter_date"]
                    )
                    await session.execute(stmt_ins)
            else:
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                # Batch inserts to stay under asyncpg's 32767 parameter limit.
                # Each row has 8 columns, so max ~4000 rows per batch.
                batch_size = 4000
                for i in range(0, len(rows), batch_size):
                    batch = rows[i : i + batch_size]
                    stmt_ins = pg_insert(PITUniverseMembership).values(batch)
                    stmt_ins = stmt_ins.on_conflict_do_nothing(
                        constraint="uq_pit_universe_ticker_quarter"
                    )
                    await session.execute(stmt_ins)

            total_rows_inserted += len(rows)

    await session.commit()

    logger.info(
        "[universe-assembly] Processed %d quarters, %d tickers, %d delistings detected",
        len(all_quarters),
        len(all_tickers),
        len(delistings),
    )

    return {
        "quarters_processed": len(all_quarters),
        "tickers_tracked": len(all_tickers),
        "delistings_detected": len(delistings),
    }


async def fill_last_known_prices(session: AsyncSession) -> int:
    """Fill last_known_price for delisted tickers from pit_daily_prices.

    For each delisted ticker in pit_universe_memberships where last_known_price IS NULL:
    - Query pit_daily_prices for the most recent close before delist_detected_at
    - Update the last_known_price field

    Returns:
        Count of updated rows.
    """
    # Find delisted membership rows with NULL last_known_price
    stmt = select(PITUniverseMembership).where(
        PITUniverseMembership.delist_detected_at.isnot(None),
        PITUniverseMembership.last_known_price.is_(None),
    )
    result = await session.execute(stmt)
    members = result.scalars().all()

    if not members:
        return 0

    updated_count = 0

    for member in members:
        # Find most recent price before delist date
        price_stmt = (
            select(PITDailyPrice.close)
            .where(
                PITDailyPrice.ticker == member.ticker,
                PITDailyPrice.date < member.delist_detected_at,
            )
            .order_by(PITDailyPrice.date.desc())
            .limit(1)
        )
        price_result = await session.execute(price_stmt)
        price = price_result.scalar_one_or_none()

        if price is not None:
            stmt_update = (
                update(PITUniverseMembership)
                .where(PITUniverseMembership.id == member.id)
                .values(last_known_price=price)
            )
            await session.execute(stmt_update)
            updated_count += 1

    await session.commit()

    logger.info(
        "[universe-assembly] Filled last_known_price for %d delisted tickers",
        updated_count,
    )

    return updated_count
