"""Tests for sector_stats service — list_sector_summaries and get_sector_champion_detail.

compute_sector_filter_pass_rates, compute_sector_distribution, and
compute_all_sector_distributions are already tested in test_inject_sector_stats.py.
This file covers the async DB query helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.services.sector_stats import get_sector_champion_detail, list_sector_summaries
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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


async def _seed_published_scores(session_factory, records: list[dict]) -> None:
    """Seed Asset + V4Score rows. Each record: {ticker, sector, market_cap, score, published}."""
    async with session_factory() as session:
        for rec in records:
            asset = Asset(
                ticker=rec["ticker"],
                name=f"{rec['ticker']} Inc.",
                sector=rec["sector"],
                market_cap=Decimal(str(rec.get("market_cap", 1_000_000_000))),
            )
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                composite_score=rec["score"],
                conviction=rec.get("conviction", "high"),
                rules_conviction=rec.get("conviction", "high"),
                timing_signal=rec.get("timing_signal", "stable"),
                opportunity_type=rec.get("opportunity_type", "compounder"),
                style="quality",
                regime="normal",
                published=rec.get("published", True),
                scored_at=datetime.now(UTC),
                detail=rec.get("detail", {}),
            )
            session.add(v4)
        await session.commit()


@pytest.mark.asyncio
class TestListSectorSummaries:
    async def test_empty_returns_empty_list(self, session_factory):
        async with session_factory() as session:
            result = await list_sector_summaries(session)
        assert result == []

    async def test_no_published_scores(self, session_factory):
        await _seed_published_scores(
            session_factory,
            [{"ticker": "AAPL", "sector": "Technology", "score": 90.0, "published": False}],
        )
        async with session_factory() as session:
            result = await list_sector_summaries(session)
        assert result == []

    async def test_single_sector_single_ticker(self, session_factory):
        await _seed_published_scores(
            session_factory,
            [{"ticker": "AAPL", "sector": "Technology", "score": 85.0, "published": True}],
        )
        async with session_factory() as session:
            result = await list_sector_summaries(session)

        assert len(result) == 1
        entry = result[0]
        assert entry["sector"] == "Technology"
        assert entry["asset_count"] == 1
        assert entry["avg_composite_score"] == pytest.approx(85.0)
        assert entry["top_ticker"] == "AAPL"
        assert entry["top_score"] == pytest.approx(85.0)

    async def test_multiple_sectors(self, session_factory):
        await _seed_published_scores(
            session_factory,
            [
                {"ticker": "AAPL", "sector": "Technology", "score": 85.0, "published": True},
                {"ticker": "MSFT", "sector": "Technology", "score": 70.0, "published": True},
                {"ticker": "JNJ", "sector": "Healthcare", "score": 60.0, "published": True},
            ],
        )
        async with session_factory() as session:
            result = await list_sector_summaries(session)

        sectors = {r["sector"]: r for r in result}
        assert "Technology" in sectors
        assert "Healthcare" in sectors

        tech = sectors["Technology"]
        assert tech["asset_count"] == 2
        assert tech["top_ticker"] == "AAPL"
        assert tech["top_score"] == pytest.approx(85.0)
        assert tech["avg_composite_score"] == pytest.approx(77.5)

        health = sectors["Healthcare"]
        assert health["asset_count"] == 1
        assert health["top_ticker"] == "JNJ"

    async def test_champion_is_highest_score_in_sector(self, session_factory):
        await _seed_published_scores(
            session_factory,
            [
                {"ticker": "LOW_SCORE", "sector": "Finance", "score": 40.0, "published": True},
                {"ticker": "HIGH_SCORE", "sector": "Finance", "score": 95.0, "published": True},
                {"ticker": "MID_SCORE", "sector": "Finance", "score": 65.0, "published": True},
            ],
        )
        async with session_factory() as session:
            result = await list_sector_summaries(session)

        assert len(result) == 1
        assert result[0]["top_ticker"] == "HIGH_SCORE"


@pytest.mark.asyncio
class TestGetSectorChampionDetail:
    async def test_returns_none_for_empty_sector(self, session_factory):
        async with session_factory() as session:
            result = await get_sector_champion_detail(session, "Technology")
        assert result is None

    async def test_returns_none_for_unpublished_scores(self, session_factory):
        await _seed_published_scores(
            session_factory,
            [{"ticker": "AAPL", "sector": "Technology", "score": 90.0, "published": False}],
        )
        async with session_factory() as session:
            result = await get_sector_champion_detail(session, "Technology")
        assert result is None

    async def test_returns_champion_for_sector(self, session_factory):
        await _seed_published_scores(
            session_factory,
            [
                {
                    "ticker": "MSFT",
                    "sector": "Technology",
                    "score": 88.0,
                    "published": True,
                    "market_cap": 3_000_000_000_000,
                    "conviction": "exceptional",
                    "timing_signal": "strong",
                    "detail": {"composite_tier": "exceptional", "signal": "strong"},
                },
                {
                    "ticker": "AAPL",
                    "sector": "Technology",
                    "score": 75.0,
                    "published": True,
                    "market_cap": 2_500_000_000_000,
                },
            ],
        )
        async with session_factory() as session:
            result = await get_sector_champion_detail(session, "Technology")

        assert result is not None
        assert result["ticker"] == "MSFT"
        assert result["sector"] == "Technology"
        assert result["composite_score"] == pytest.approx(88.0)
        assert result["composite_tier"] == "exceptional"
        assert result["signal"] == "strong"
        assert result["market_cap"] == pytest.approx(3_000_000_000_000.0)

    async def test_returns_none_for_missing_sector(self, session_factory):
        await _seed_published_scores(
            session_factory,
            [{"ticker": "JNJ", "sector": "Healthcare", "score": 70.0, "published": True}],
        )
        async with session_factory() as session:
            result = await get_sector_champion_detail(session, "Technology")
        assert result is None

    async def test_champion_uses_detail_fallback(self, session_factory):
        """When detail has no composite_tier, falls back to conviction field."""
        await _seed_published_scores(
            session_factory,
            [
                {
                    "ticker": "IBM",
                    "sector": "Technology",
                    "score": 55.0,
                    "published": True,
                    "conviction": "medium",
                    "timing_signal": "neutral",
                    "detail": {},  # no composite_tier in detail
                }
            ],
        )
        async with session_factory() as session:
            result = await get_sector_champion_detail(session, "Technology")

        assert result is not None
        assert result["composite_tier"] == "medium"
        assert result["signal"] == "neutral"
