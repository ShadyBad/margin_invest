"""Tests for market_cap field in ScoreResponse."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _score_detail(ticker: str = "AAPL") -> dict:
    """Create a minimal score_detail JSONB payload."""
    return {
        "ticker": ticker,
        "composite_percentile": 92.0,
        "composite_raw_score": 0.85,
        "composite_tier": "high",
        "signal": "buy",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 90.0,
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [],
            "average_percentile": 88.0,
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 91.0,
        },
        "filters_passed": [],
        "data_coverage": 1.0,
        "growth_stage": None,
    }


@pytest_asyncio.fixture
async def async_engine():
    """Create an async in-memory SQLite engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def v4_seeded_session(async_engine):
    """Seed the DB with an Asset + V4Score, return a session factory."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(aapl)
        await session.flush()

        v4 = V4Score(
            asset_id=aapl.id,
            scored_at=datetime.now(UTC),
            opportunity_type="deep_value",
            conviction="high",
            rules_conviction="high",
            style="value",
            timing_signal="hold",
            max_position_pct=5.0,
            regime="expansion",
            composite_score=0.85,
            ml_override="none",
            detail=_score_detail("AAPL"),
            published=True,
        )
        session.add(v4)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def v4_unpublished_session(async_engine):
    """Seed the DB with an Asset + unpublished V4Score, return a session factory."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        msft = Asset(
            ticker="MSFT",
            name="Microsoft Corp.",
            sector="Information Technology",
            market_cap=Decimal("2800000000000"),
        )
        session.add(msft)
        await session.flush()

        v4 = V4Score(
            asset_id=msft.id,
            scored_at=datetime.now(UTC),
            opportunity_type="compounder",
            conviction="high",
            rules_conviction="high",
            style="growth",
            timing_signal="buy_now",
            max_position_pct=5.0,
            regime="normal",
            composite_score=88.0,
            ml_override="none",
            detail=_score_detail("MSFT"),
            published=False,  # unpublished — tests V4 any fallback
        )
        session.add(v4)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def null_market_cap_session(async_engine):
    """Seed the DB with an Asset that has market_cap=0 and a V4Score."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        xyz = Asset(
            ticker="XYZ",
            name="XYZ Corp.",
            sector="Industrials",
            market_cap=Decimal("0"),
        )
        session.add(xyz)
        await session.flush()

        v4 = V4Score(
            asset_id=xyz.id,
            scored_at=datetime.now(UTC),
            opportunity_type="growth",
            conviction="medium",
            rules_conviction="medium",
            style="growth",
            timing_signal="hold",
            max_position_pct=3.0,
            regime="expansion",
            composite_score=0.60,
            ml_override="none",
            detail=_score_detail("XYZ"),
            published=True,
        )
        session.add(v4)
        await session.commit()
    return factory


def _make_client(session_factory):
    """Create an AsyncClient with the given session factory."""
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
class TestMarketCapV4Response:
    """Test market_cap is returned via V4Score path."""

    async def test_market_cap_in_v4_response(self, v4_seeded_session):
        async with _make_client(v4_seeded_session) as client:
            response = await client.get("/api/v1/scores/AAPL")
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "AAPL"
            assert data["market_cap"] == 3500000000000.0

    async def test_market_cap_is_float(self, v4_seeded_session):
        async with _make_client(v4_seeded_session) as client:
            response = await client.get("/api/v1/scores/AAPL")
            data = response.json()
            assert isinstance(data["market_cap"], float)


@pytest.mark.asyncio
class TestMarketCapV4UnpublishedFallback:
    """Test market_cap is returned via unpublished V4Score fallback path."""

    async def test_market_cap_in_unpublished_v4_response(self, v4_unpublished_session):
        async with _make_client(v4_unpublished_session) as client:
            response = await client.get("/api/v1/scores/MSFT")
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "MSFT"
            assert data["market_cap"] == 2800000000000.0


@pytest.mark.asyncio
class TestMarketCapZero:
    """Test market_cap when Asset has market_cap=0 (default)."""

    async def test_zero_market_cap_returned(self, null_market_cap_session):
        async with _make_client(null_market_cap_session) as client:
            response = await client.get("/api/v1/scores/XYZ")
            assert response.status_code == 200
            data = response.json()
            # 0 is still a valid float, should be returned as 0.0
            assert data["market_cap"] == 0.0
