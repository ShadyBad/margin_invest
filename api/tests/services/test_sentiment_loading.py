"""Tests for loading NLP sentiment values from FilingSentimentCache."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import FilingSentimentCache, FilingText
from margin_api.services.nlp_analyzer import NLP_ANALYSIS_VERSION
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Async DB fixtures (SQLite in-memory for speed)
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
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _filing_text(ticker: str, filing_date: date) -> FilingText:
    """Create a minimal FilingText parent record."""
    return FilingText(
        ticker=ticker,
        cik="0001234567",
        filing_type="10-K",
        filing_date=filing_date,
        period_end=filing_date,
        mda_text="Sample MD&A text.",
    )


def _sentiment_cache(
    filing_text_id: int,
    ticker: str,
    sentiment_value: float,
    created_at: datetime,
) -> FilingSentimentCache:
    return FilingSentimentCache(
        filing_text_id=filing_text_id,
        ticker=ticker,
        analysis_version=NLP_ANALYSIS_VERSION,
        prompt_hash="abc123",
        sentiment_value=sentiment_value,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSentimentCacheLoading:
    @pytest.mark.asyncio
    async def test_sentiment_cache_query_returns_latest(self, session: AsyncSession) -> None:
        """When multiple cache rows exist for a ticker, the latest should win."""
        # Create parent FilingText records
        ft_old = _filing_text("AAPL", date(2025, 6, 1))
        ft_new = _filing_text("AAPL", date(2025, 12, 1))
        # Assign different period_end to satisfy unique constraint
        ft_old.period_end = date(2025, 6, 30)
        ft_new.period_end = date(2025, 12, 31)
        session.add_all([ft_old, ft_new])
        await session.flush()

        now = datetime.now(UTC)
        old_cache = _sentiment_cache(ft_old.id, "AAPL", 1.5, now - timedelta(days=30))
        new_cache = _sentiment_cache(ft_new.id, "AAPL", 3.2, now)
        session.add_all([old_cache, new_cache])
        await session.commit()

        # Query: latest sentiment for AAPL
        result = await session.execute(
            select(FilingSentimentCache)
            .where(
                FilingSentimentCache.ticker == "AAPL",
                FilingSentimentCache.analysis_version == NLP_ANALYSIS_VERSION,
            )
            .order_by(FilingSentimentCache.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.sentiment_value == pytest.approx(3.2)
        assert row.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_sentiment_cache_returns_none_for_unknown_ticker(
        self, session: AsyncSession
    ) -> None:
        """Querying a ticker with no cache rows should return None."""
        result = await session.execute(
            select(FilingSentimentCache)
            .where(
                FilingSentimentCache.ticker == "ZZZZ",
                FilingSentimentCache.analysis_version == NLP_ANALYSIS_VERSION,
            )
            .order_by(FilingSentimentCache.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        assert row is None
