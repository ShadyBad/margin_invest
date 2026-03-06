"""Universe assembly service: builds quarterly universe membership from PIT financial snapshots.

Scans pit_financial_snapshots to determine which tickers were active each quarter,
detects delistings when a company stops filing for 8+ consecutive quarters (~2 years), and
populates pit_universe_memberships. Also backfills last_known_price for delisted tickers,
and computes market_cap and avg_daily_volume for each membership row.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
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
    *,
    consecutive_miss_threshold: int = 8,
) -> dict[str, date]:
    """Detect tickers that stopped filing for 8+ consecutive quarters (~2 years).

    A threshold of 8 avoids false positives from annual filers (10-K only) who
    naturally miss 3 quarters between filings.

    Args:
        filing_quarters: {ticker: [quarter_dates_they_filed]}
        all_quarters: sorted list of all quarter end dates
        consecutive_miss_threshold: number of consecutive missing quarters to
            trigger a delisting detection (default 8, i.e. ~2 years).

    Returns:
        {ticker: delist_detected_date} for tickers missing ``consecutive_miss_threshold``+
        consecutive quarters. "Detected at" = the quarter where the threshold is reached.
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
                if consecutive_misses >= consecutive_miss_threshold:
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

    # Step 5: Batch-compute market_cap and avg_daily_volume for newly inserted rows
    market_cap_count = await _batch_compute_market_caps(session)
    avg_vol_count = await _batch_compute_avg_volumes(session)

    logger.info(
        "[universe-assembly] Processed %d quarters, %d tickers, %d delistings detected, "
        "%d market_caps computed, %d avg_volumes computed",
        len(all_quarters),
        len(all_tickers),
        len(delistings),
        market_cap_count,
        avg_vol_count,
    )

    return {
        "quarters_processed": len(all_quarters),
        "tickers_tracked": len(all_tickers),
        "delistings_detected": len(delistings),
        "market_caps_computed": market_cap_count,
        "avg_volumes_computed": avg_vol_count,
    }


async def fill_last_known_prices(session: AsyncSession) -> int:
    """Fill last_known_price for delisted tickers using a batch window query.

    For each delisted ticker in pit_universe_memberships where last_known_price IS NULL:
    - Query pit_daily_prices for the most recent close before delist_detected_at
    - Update the last_known_price field

    Uses a single batch query with ROW_NUMBER() window function instead of
    per-ticker N+1 queries (~5000x fewer round-trips for large universes).

    Returns:
        Count of updated rows.
    """
    # Find all distinct (ticker, delist_detected_at) pairs needing price fill
    stmt = (
        select(
            PITUniverseMembership.ticker,
            PITUniverseMembership.delist_detected_at,
        )
        .where(
            PITUniverseMembership.delist_detected_at.isnot(None),
            PITUniverseMembership.last_known_price.is_(None),
        )
        .distinct()
    )
    result = await session.execute(stmt)
    delisted = result.all()

    if not delisted:
        return 0

    # Build {ticker: earliest_delist_date} for batch price lookup
    delist_dates: dict[str, date] = {}
    for ticker, delist_date in delisted:
        if ticker not in delist_dates or delist_date < delist_dates[ticker]:
            delist_dates[ticker] = delist_date

    tickers = list(delist_dates.keys())

    # Batch: for each ticker, get the latest price BEFORE its delist date.
    # We filter prices to only those before the delist date, then use
    # ROW_NUMBER() partitioned by ticker to pick the most recent one.
    #
    # SQLite does not support lateral joins, so we filter using a CASE
    # expression in an application-side loop to build per-ticker cutoff dates.
    # For simplicity, we fetch all candidate prices in one query with a
    # generous date range, then pick the best per ticker in Python.
    #
    # For large ticker sets we chunk to avoid excessive parameter counts.
    last_prices: dict[str, float] = {}
    chunk_size = 500
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]

        # Find the latest delist date in this chunk to set the upper bound
        max_delist = max(delist_dates[t] for t in chunk)

        # Get the latest price per ticker (before its delist date).
        # We use ROW_NUMBER to pick the most recent price per ticker,
        # but we need to respect per-ticker delist dates.  We first
        # fetch candidate rows (all prices for these tickers before
        # the max delist date), then filter in Python.
        price_stmt = (
            select(PITDailyPrice.ticker, PITDailyPrice.date, PITDailyPrice.close)
            .where(
                PITDailyPrice.ticker.in_(chunk),
                PITDailyPrice.date < max_delist,
            )
            .order_by(PITDailyPrice.ticker, PITDailyPrice.date.desc())
        )
        price_result = await session.execute(price_stmt)

        for row in price_result.all():
            t, d, close = row.ticker, row.date, row.close
            # Only use prices before the ticker's specific delist date
            if d < delist_dates[t] and t not in last_prices:
                last_prices[t] = float(close)

    # Batch update membership rows
    updated = 0
    for ticker, price in last_prices.items():
        stmt_upd = (
            update(PITUniverseMembership)
            .where(
                PITUniverseMembership.ticker == ticker,
                PITUniverseMembership.delist_detected_at.isnot(None),
                PITUniverseMembership.last_known_price.is_(None),
            )
            .values(last_known_price=price)
        )
        result = await session.execute(stmt_upd)
        updated += result.rowcount

    await session.commit()
    logger.info("[universe-assembly] Filled last_known_price for %d delisted tickers", updated)
    return updated


async def _batch_compute_market_caps(session: AsyncSession) -> int:
    """Compute market_cap = shares_outstanding * close_price for universe memberships.

    For each membership row where market_cap IS NULL:
    - Look up shares_outstanding from the most recent pit_financial_snapshot
      at or before the quarter_date
    - Look up the closest close price from pit_daily_prices at or before the
      quarter_date
    - Set market_cap = shares_outstanding * close

    Returns:
        Count of updated rows.
    """
    # Find membership rows needing market_cap
    stmt = select(
        PITUniverseMembership.id,
        PITUniverseMembership.ticker,
        PITUniverseMembership.quarter_date,
    ).where(PITUniverseMembership.market_cap.is_(None))
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return 0

    # Collect unique tickers
    tickers = list({r.ticker for r in rows})

    # Batch fetch: latest shares_outstanding per (ticker, quarter_date)
    # Query all snapshots for these tickers
    snap_stmt = (
        select(
            PITFinancialSnapshot.ticker,
            PITFinancialSnapshot.period_end,
            PITFinancialSnapshot.shares_outstanding,
        )
        .where(
            PITFinancialSnapshot.ticker.in_(tickers),
            PITFinancialSnapshot.shares_outstanding.isnot(None),
        )
        .order_by(PITFinancialSnapshot.ticker, PITFinancialSnapshot.period_end.desc())
    )
    snap_result = await session.execute(snap_stmt)
    # Build {ticker: [(period_end, shares_outstanding)]} sorted desc by period_end
    ticker_shares: dict[str, list[tuple[date, int]]] = {}
    for snap in snap_result.all():
        ticker_shares.setdefault(snap.ticker, []).append(
            (snap.period_end, snap.shares_outstanding)
        )

    # Batch fetch: latest close price per (ticker, quarter_date)
    # Query all prices for these tickers
    price_stmt = (
        select(PITDailyPrice.ticker, PITDailyPrice.date, PITDailyPrice.close)
        .where(PITDailyPrice.ticker.in_(tickers))
        .order_by(PITDailyPrice.ticker, PITDailyPrice.date.desc())
    )
    price_result = await session.execute(price_stmt)
    # Build {ticker: [(date, close)]} sorted desc by date
    ticker_prices: dict[str, list[tuple[date, float]]] = {}
    for p in price_result.all():
        ticker_prices.setdefault(p.ticker, []).append((p.date, float(p.close)))

    # For each membership row, find the best shares and price
    updated = 0
    for row_id, ticker, quarter_date in rows:
        # Find most recent shares_outstanding at or before quarter_date
        shares = None
        for pe, so in ticker_shares.get(ticker, []):
            if pe <= quarter_date:
                shares = so
                break

        # Find most recent close price at or before quarter_date
        close = None
        for d, c in ticker_prices.get(ticker, []):
            if d <= quarter_date:
                close = c
                break

        if shares is not None and close is not None:
            market_cap = float(shares) * close
            stmt_upd = (
                update(PITUniverseMembership)
                .where(PITUniverseMembership.id == row_id)
                .values(market_cap=market_cap)
            )
            await session.execute(stmt_upd)
            updated += 1

    await session.commit()
    logger.info("[universe-assembly] Computed market_cap for %d membership rows", updated)
    return updated


async def _batch_compute_avg_volumes(session: AsyncSession) -> int:
    """Compute trailing 60-trading-day average dollar volume for universe memberships.

    avg_daily_volume = mean(close * volume) over the 60 trading days ending at
    or before each membership's quarter_date.

    Returns:
        Count of updated rows.
    """
    # Find membership rows needing avg_daily_volume
    stmt = select(
        PITUniverseMembership.id,
        PITUniverseMembership.ticker,
        PITUniverseMembership.quarter_date,
    ).where(PITUniverseMembership.avg_daily_volume.is_(None))
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return 0

    # Collect unique (ticker, quarter_date) pairs
    pairs: dict[str, set[date]] = {}
    for _, ticker, quarter_date in rows:
        pairs.setdefault(ticker, set()).add(quarter_date)

    tickers = list(pairs.keys())

    # Batch fetch prices for these tickers within the relevant date range.
    # 60 trading days ~ 90 calendar days, use 100 days for safety margin.
    all_quarter_dates = set()
    for qs in pairs.values():
        all_quarter_dates.update(qs)
    min_quarter = min(all_quarter_dates)
    lookback_start = min_quarter - timedelta(days=100)

    price_stmt = (
        select(
            PITDailyPrice.ticker,
            PITDailyPrice.date,
            PITDailyPrice.close,
            PITDailyPrice.volume,
        )
        .where(
            PITDailyPrice.ticker.in_(tickers),
            PITDailyPrice.date >= lookback_start,
        )
        .order_by(PITDailyPrice.ticker, PITDailyPrice.date.desc())
    )
    price_result = await session.execute(price_stmt)

    # Build {ticker: [(date, dollar_volume)]} sorted desc by date
    ticker_dv: dict[str, list[tuple[date, float]]] = {}
    for p in price_result.all():
        dv = float(p.close) * float(p.volume)
        ticker_dv.setdefault(p.ticker, []).append((p.date, dv))

    # For each membership row, compute trailing 60-day average
    # Build a lookup from (row_id) -> avg_daily_volume
    updates: dict[int, float] = {}
    for row_id, ticker, quarter_date in rows:
        dvs = ticker_dv.get(ticker, [])
        # Take up to 60 trading days at or before quarter_date
        trailing = [dv for d, dv in dvs if d <= quarter_date][:60]
        if trailing:
            avg_vol = sum(trailing) / len(trailing)
            updates[row_id] = avg_vol

    # Batch update
    updated = 0
    for row_id, avg_vol in updates.items():
        stmt_upd = (
            update(PITUniverseMembership)
            .where(PITUniverseMembership.id == row_id)
            .values(avg_daily_volume=avg_vol)
        )
        await session.execute(stmt_upd)
        updated += 1

    await session.commit()
    logger.info("[universe-assembly] Computed avg_daily_volume for %d membership rows", updated)
    return updated
