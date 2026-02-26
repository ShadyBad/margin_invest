"""Async tests for services/price_ingestion.py — upsert + batched ingestion."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import PriceIntraday
from margin_api.services.price_ingestion import (
    ingest_price_bars_batched,
    upsert_price_bars,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


def _bars(n: int = 3) -> list[dict]:
    """Generate n price bar dicts with proper datetime objects for SQLite."""
    return [
        {
            "time": datetime(2025, 1, 15, 10, i, 0, tzinfo=UTC),
            "open": 150.0 + i,
            "high": 151.0 + i,
            "low": 149.0 + i,
            "close": 150.5 + i,
            "volume": 1000 * (i + 1),
        }
        for i in range(n)
    ]


class TestUpsertPriceBars:
    @pytest.mark.asyncio
    async def test_upsert_inserts_bars(self, session):
        """Bars are inserted into the database via SQLite fallback path."""
        count = await upsert_price_bars(session, "AAPL", _bars(3), source="test")
        await session.commit()
        assert count == 3

        result = await session.execute(select(PriceIntraday))
        rows = result.scalars().all()
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_upsert_empty_bars(self, session):
        """Empty bars list returns 0 without error."""
        count = await upsert_price_bars(session, "AAPL", [], source="test")
        assert count == 0

    @pytest.mark.asyncio
    async def test_upsert_idempotent(self, session):
        """Upserting same bars twice doesn't create duplicates."""
        bars = _bars(2)
        await upsert_price_bars(session, "AAPL", bars, source="test")
        await session.commit()

        # Upsert again with updated source
        count = await upsert_price_bars(session, "AAPL", _bars(2), source="updated")
        await session.commit()
        assert count == 2

        result = await session.execute(select(PriceIntraday))
        rows = result.scalars().all()
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_upsert_capitalized_keys(self, session):
        """Bars with capitalized keys (yfinance format) are handled."""
        bars = [
            {
                "Time": datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
                "Open": 150.0,
                "High": 151.0,
                "Low": 149.0,
                "Close": 150.5,
                "Volume": 5000,
            }
        ]
        count = await upsert_price_bars(session, "MSFT", bars, source="yf")
        await session.commit()
        assert count == 1


class TestIngestPriceBarsBatched:
    @pytest.mark.asyncio
    async def test_batched_ingestion(self, session):
        """Batched ingestion processes all bars across chunks."""
        bars = _bars(5)
        total = await ingest_price_bars_batched(session, "GOOG", bars, source="test")
        assert total == 5

    @pytest.mark.asyncio
    async def test_batched_empty(self, session):
        """Batched ingestion with no bars returns 0."""
        total = await ingest_price_bars_batched(session, "GOOG", [], source="test")
        assert total == 0
