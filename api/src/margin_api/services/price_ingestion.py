"""Batch price bar ingestion for prices_intraday."""
from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import PriceIntraday

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


def prepare_price_values(
    ticker: str,
    bars: list[dict],
    source: str,
) -> list[dict[str, Any]]:
    """Transform raw bar dicts into values ready for insert."""
    if not bars:
        return []
    return [
        {
            "time": bar.get("time") or bar.get("Time") or bar.get("date") or bar.get("Date"),
            "ticker": ticker,
            "open": bar.get("open") or bar.get("Open"),
            "high": bar.get("high") or bar.get("High"),
            "low": bar.get("low") or bar.get("Low"),
            "close": bar.get("close") or bar.get("Close"),
            "volume": bar.get("volume") or bar.get("Volume"),
            "source": source,
        }
        for bar in bars
    ]


def chunk_bars(bars: list, batch_size: int = BATCH_SIZE) -> Iterator[list]:
    """Yield successive chunks of bars."""
    for i in range(0, len(bars), batch_size):
        yield bars[i : i + batch_size]


async def upsert_price_bars(
    session: AsyncSession,
    ticker: str,
    bars: list[dict],
    source: str = "unknown",
) -> int:
    """Batch upsert price bars into prices_intraday. Idempotent.

    Uses INSERT ... ON CONFLICT DO UPDATE on PostgreSQL.
    Falls back to individual inserts on SQLite (tests).
    """
    values = prepare_price_values(ticker, bars, source)
    if not values:
        return 0

    dialect = session.bind.dialect.name if session.bind else "unknown"

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        stmt = insert(PriceIntraday).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ticker", "time"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "source": stmt.excluded.source,
            },
        )
        await session.execute(stmt)
    else:
        # SQLite fallback for tests — use INSERT OR REPLACE for idempotency
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        for val in values:
            stmt = sqlite_insert(PriceIntraday).values(**val)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker", "time"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                    "source": stmt.excluded.source,
                },
            )
            await session.execute(stmt)

    return len(values)


async def ingest_price_bars_batched(
    session: AsyncSession,
    ticker: str,
    bars: list[dict],
    source: str = "unknown",
) -> int:
    """Insert price bars in batches, committing between chunks."""
    total = 0
    for chunk in chunk_bars(bars, BATCH_SIZE):
        count = await upsert_price_bars(session, ticker, chunk, source)
        total += count
        await session.commit()
    logger.info("Ingested %d bars for %s", total, ticker)
    return total
