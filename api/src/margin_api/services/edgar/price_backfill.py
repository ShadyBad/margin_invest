"""Bulk-download daily OHLCV prices via yfinance and insert into pit_daily_prices.

This module provides functions to:
1. Convert yfinance DataFrames into row dicts for the PITDailyPrice table.
2. Backfill prices for a list of tickers in batches.
"""

from __future__ import annotations

import logging
import math
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from margin_api.db.models import PITDailyPrice

logger = logging.getLogger(__name__)


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


async def backfill_prices_for_tickers(
    tickers: list[str],
    start_date: str = "2009-01-01",
    end_date: str | None = None,
    batch_size: int = 500,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> dict[str, int]:
    """Download daily prices via yfinance and insert into pit_daily_prices.

    Args:
        tickers: List of ticker symbols to download prices for.
        start_date: Start date for price history (YYYY-MM-DD format).
        end_date: End date for price history (YYYY-MM-DD format). Defaults to today.
        batch_size: Number of tickers to download in each yfinance batch call.
        session_factory: Async SQLAlchemy session factory for database inserts.

    Returns:
        Dict mapping ticker to number of rows inserted.
    """
    import yfinance as yf

    if end_date is None:
        end_date = date.today().isoformat()

    summary: dict[str, int] = {}
    total_tickers = len(tickers)

    # Process in batches
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
            # yfinance.download for bulk download
            if len(batch) == 1:
                df = yf.download(
                    batch,
                    start=start_date,
                    end=end_date,
                    group_by="column",
                    progress=False,
                    threads=True,
                )
                # Single ticker: df is already a flat DataFrame
                all_rows = build_price_rows(batch[0], df)
                if all_rows:
                    summary[batch[0]] = len(all_rows)
            else:
                df = yf.download(
                    batch,
                    start=start_date,
                    end=end_date,
                    group_by="ticker",
                    progress=False,
                    threads=True,
                )
                # Multi-ticker: df has MultiIndex columns (ticker, field)
                all_rows = []
                for ticker in batch:
                    try:
                        ticker_df = df[ticker]
                        rows = build_price_rows(ticker, ticker_df)
                        if rows:
                            summary[ticker] = len(rows)
                            all_rows.extend(rows)
                    except KeyError:
                        logger.warning(
                            "[price-backfill] No data returned for %s", ticker
                        )
                        continue

            # Insert into database
            if all_rows and session_factory is not None:
                async with session_factory() as session:
                    # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING
                    stmt = pg_insert(PITDailyPrice).values(all_rows)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=["ticker", "date"]
                    )
                    await session.execute(stmt)
                    await session.commit()

                logger.info(
                    "[price-backfill] Inserted %d rows for batch %d-%d",
                    len(all_rows),
                    batch_start + 1,
                    batch_end,
                )

        except Exception:
            logger.exception(
                "[price-backfill] Error downloading batch %d-%d",
                batch_start + 1,
                batch_end,
            )

    return summary
