"""Bulk-download daily OHLCV prices via yfinance and insert into pit_daily_prices.

This module provides functions to:
1. Convert yfinance DataFrames into row dicts for the PITDailyPrice table.
2. Backfill prices for a list of tickers in batches.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from margin_api.db.models import PITDailyPrice

logger = logging.getLogger(__name__)

DEFAULT_BATCH_DELAY = 1.0  # seconds between batches to avoid rate limiting
MAX_RETRIES = 2  # retry failed tickers up to 2 times
RETRY_BATCH_SIZE = 10  # smaller batches for retries
RETRY_BACKOFF_BASE = 3.0  # seconds, multiplied by attempt number


def build_price_rows(ticker: str, df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a yfinance OHLCV DataFrame into row dicts for pit_daily_prices.

    Args:
        ticker: The stock ticker symbol.
        df: A pandas DataFrame with columns Open, High, Low, Close, Adj Close, Volume
            and a DatetimeIndex.

    Returns:
        List of dicts suitable for bulk insert into pit_daily_prices.
        Rows where Close is NaN are skipped.
        All numeric values are converted to native Python types (float/int).
    """
    if df.empty:
        return []

    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        close_val = row["Close"]
        # Skip rows where Close is NaN
        if isinstance(close_val, float) and math.isnan(close_val):
            continue
        # Also handle numpy NaN
        try:
            if pd.isna(close_val):
                continue
        except (TypeError, ValueError):
            pass

        # Convert pandas Timestamp to date
        row_date: date
        if isinstance(idx, pd.Timestamp):
            row_date = idx.date()
        else:
            row_date = pd.Timestamp(idx).date()

        rows.append(
            {
                "ticker": ticker,
                "date": row_date,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(close_val),
                "adj_close": float(row["Adj Close"]),
                "volume": int(row["Volume"]),
                "source": "yfinance",
            }
        )

    return rows


def _download_and_extract(
    batch: list[str],
    start_date: str,
    end_date: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Download a batch of tickers via yfinance and return (rows, failed_tickers).

    This is a synchronous helper that handles both single-ticker and multi-ticker
    download paths, and separates tickers that returned data from those that didn't.

    Uses auto_adjust=False to get both Close and Adj Close columns
    (yfinance >= 1.1.0 defaults to auto_adjust=True which removes Adj Close).
    Always uses group_by="ticker" so df[ticker] returns flat columns.
    """
    import yfinance as yf

    rows: list[dict[str, Any]] = []
    failed: list[str] = []

    df = yf.download(
        batch,
        start=start_date,
        end=end_date,
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df.empty:
        return [], list(batch)

    for ticker in batch:
        try:
            ticker_df = df[ticker]
        except KeyError:
            failed.append(ticker)
            continue

        try:
            ticker_rows = build_price_rows(ticker, ticker_df)
        except KeyError:
            logger.warning(
                "[price-backfill] Column mismatch for %s, columns: %s",
                ticker,
                list(ticker_df.columns) if hasattr(ticker_df, "columns") else "N/A",
            )
            failed.append(ticker)
            continue

        if ticker_rows:
            rows.extend(ticker_rows)
        else:
            failed.append(ticker)

    return rows, failed


async def _insert_rows(
    rows: list[dict[str, Any]],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Insert price rows into the database with ON CONFLICT DO NOTHING."""
    if not rows:
        return
    async with session_factory() as session:
        stmt = pg_insert(PITDailyPrice).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["ticker", "date"])
        await session.execute(stmt)
        await session.commit()


async def backfill_prices_for_tickers(
    tickers: list[str],
    start_date: str = "2009-01-01",
    end_date: str | None = None,
    batch_size: int = 50,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    batch_delay: float = DEFAULT_BATCH_DELAY,
    max_retries: int = MAX_RETRIES,
) -> dict[str, int]:
    """Download daily prices via yfinance and insert into pit_daily_prices.

    Args:
        tickers: List of ticker symbols to download prices for.
        start_date: Start date for price history (YYYY-MM-DD format).
        end_date: End date for price history (YYYY-MM-DD format). Defaults to today.
        batch_size: Number of tickers to download in each yfinance batch call.
        session_factory: Async SQLAlchemy session factory for database inserts.
        batch_delay: Seconds to wait between batches to avoid rate limiting.
        max_retries: Number of times to retry failed tickers.

    Returns:
        Dict mapping ticker to number of rows inserted.
    """
    if end_date is None:
        end_date = date.today().isoformat()

    summary: dict[str, int] = {}
    all_failed: list[str] = []
    total_tickers = len(tickers)

    # Phase 1: Process all tickers in batches
    for batch_start in range(0, total_tickers, batch_size):
        batch = tickers[batch_start : batch_start + batch_size]
        batch_end = min(batch_start + batch_size, total_tickers)
        logger.info(
            "[price-backfill] Downloading batch %d-%d of %d tickers...",
            batch_start + 1,
            batch_end,
            total_tickers,
        )

        try:
            rows, failed = _download_and_extract(batch, start_date, end_date)

            # Track per-ticker counts
            for row in rows:
                t = row["ticker"]
                summary[t] = summary.get(t, 0) + 1

            all_failed.extend(failed)

            if session_factory is not None:
                await _insert_rows(rows, session_factory)

            batch_ok = len(batch) - len(failed)
            logger.info(
                "[price-backfill] Batch %d-%d: %d ok, %d failed, %d rows",
                batch_start + 1,
                batch_end,
                batch_ok,
                len(failed),
                len(rows),
            )
            if failed:
                logger.debug(
                    "[price-backfill] Failed tickers in batch: %s",
                    ", ".join(failed[:20]),
                )

        except Exception:
            logger.exception(
                "[price-backfill] Error downloading batch %d-%d",
                batch_start + 1,
                batch_end,
            )
            all_failed.extend(batch)

        # Rate-limit delay between batches
        if batch_delay > 0 and batch_start + batch_size < total_tickers:
            await asyncio.sleep(batch_delay)

    # Phase 2: Retry failed tickers with smaller batches and backoff
    if all_failed and max_retries > 0:
        logger.info(
            "[price-backfill] Retrying %d failed tickers (max %d attempts, batch size %d)...",
            len(all_failed),
            max_retries,
            RETRY_BATCH_SIZE,
        )
        for attempt in range(1, max_retries + 1):
            if not all_failed:
                break

            retry_delay = RETRY_BACKOFF_BASE * attempt
            logger.info(
                "[price-backfill] Retry attempt %d/%d for %d tickers (delay %.1fs)...",
                attempt,
                max_retries,
                len(all_failed),
                retry_delay,
            )
            await asyncio.sleep(retry_delay)

            still_failed: list[str] = []
            for rb_start in range(0, len(all_failed), RETRY_BATCH_SIZE):
                retry_batch = all_failed[rb_start : rb_start + RETRY_BATCH_SIZE]
                try:
                    rows, failed = _download_and_extract(
                        retry_batch, start_date, end_date
                    )
                    for row in rows:
                        t = row["ticker"]
                        summary[t] = summary.get(t, 0) + 1
                    still_failed.extend(failed)

                    if session_factory is not None:
                        await _insert_rows(rows, session_factory)

                except Exception:
                    logger.exception(
                        "[price-backfill] Retry error for batch starting at %s",
                        retry_batch[0] if retry_batch else "?",
                    )
                    still_failed.extend(retry_batch)

                if retry_delay > 0:
                    await asyncio.sleep(retry_delay)

            recovered = len(all_failed) - len(still_failed)
            logger.info(
                "[price-backfill] Retry attempt %d: recovered %d, still failing %d",
                attempt,
                recovered,
                len(still_failed),
            )
            all_failed = still_failed

    # Phase 3: Summary and alerting
    success_count = len(summary)
    fail_count = len(all_failed)
    failure_rate = fail_count / total_tickers if total_tickers > 0 else 0.0

    if failure_rate > 0.5:
        logger.error(
            "[price-backfill] HIGH FAILURE RATE: %d/%d tickers (%.0f%%) returned no data. "
            "Possible API rate limiting or outage.",
            fail_count,
            total_tickers,
            failure_rate * 100,
        )
    elif fail_count > 0:
        logger.warning(
            "[price-backfill] %d/%d tickers returned no data after retries",
            fail_count,
            total_tickers,
        )

    if all_failed:
        # Log a sample of persistently failed tickers for debugging
        sample = all_failed[:50]
        logger.info(
            "[price-backfill] Sample of failed tickers (%d total): %s",
            fail_count,
            ", ".join(sample),
        )

    logger.info(
        "[price-backfill] Complete: %d succeeded, %d failed, %d total rows",
        success_count,
        fail_count,
        sum(summary.values()),
    )

    return summary
