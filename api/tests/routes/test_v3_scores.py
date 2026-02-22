"""Tests for V3 Score API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V3Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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
async def empty_client(async_engine):
    """AsyncClient with empty DB (no assets or v3 scores)."""
    app = create_app()
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seeded_session(async_engine):
    """Seed the DB with test assets and v3 scores, return a session factory."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        nvda = Asset(
            ticker="NVDA",
            name="NVIDIA Corp",
            sector="Information Technology",
            market_cap=Decimal("2000000000000"),
        )
        session.add_all([aapl, nvda])
        await session.flush()

        aapl_v3 = V3Score(
            asset_id=aapl.id,
            opportunity_type="compounder",
            conviction="exceptional",
            track_a={"name": "compounder", "score": 92.0},
            track_b={"name": "mispricing", "score": 55.0},
            timing_signal="buy_now",
            max_position_pct=10.0,
            regime="normal",
            composite_score=92.0,
            scored_at=datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC),
        )
        nvda_v3 = V3Score(
            asset_id=nvda.id,
            opportunity_type="mispricing",
            conviction="high",
            track_a={"name": "compounder", "score": 60.0},
            track_b={"name": "mispricing", "score": 85.0},
            timing_signal="add_on_pullback",
            max_position_pct=7.5,
            regime="normal",
            composite_score=85.0,
            scored_at=datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC),
        )
        session.add_all([aapl_v3, nvda_v3])
        await session.commit()

    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    """AsyncClient with DB dependency overridden to use seeded async SQLite."""
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestListV3Scores:
    async def test_returns_empty_list(self, empty_client):
        """No scores yet -> empty list."""
        resp = await empty_client.get("/api/v3/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scores"] == []
        assert data["total"] == 0

    async def test_returns_all_scores(self, client):
        """Returns all v3 scores sorted by composite_score descending."""
        resp = await client.get("/api/v3/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        tickers = [s["ticker"] for s in data["scores"]]
        assert tickers[0] == "AAPL"
        assert tickers[1] == "NVDA"

    async def test_filter_by_conviction(self, client):
        """Filter by conviction level."""
        resp = await client.get("/api/v3/scores?conviction=exceptional")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["scores"][0]["ticker"] == "AAPL"
        assert data["scores"][0]["conviction"] == "exceptional"

    async def test_response_fields(self, client):
        """Verify all expected fields present in response."""
        resp = await client.get("/api/v3/scores")
        assert resp.status_code == 200
        score = resp.json()["scores"][0]
        assert score["ticker"] == "AAPL"
        assert score["name"] == "Apple Inc."
        assert score["opportunity_type"] == "compounder"
        assert score["conviction"] == "exceptional"
        assert score["track_a"] == {"name": "compounder", "score": 92.0}
        assert score["track_b"] == {"name": "mispricing", "score": 55.0}
        assert score["timing_signal"] == "buy_now"
        assert score["max_position_pct"] == 10.0
        assert score["regime"] == "normal"
        assert score["composite_score"] == 92.0
        assert "2026-02-17" in score["scored_at"]


@pytest.mark.asyncio
class TestGetV3Score:
    async def test_not_found(self, empty_client):
        """Unknown ticker -> 404."""
        resp = await empty_client.get("/api/v3/scores/ZZZZ")
        assert resp.status_code == 404

    async def test_get_score_success(self, client):
        """Get the latest v3 score for a specific ticker."""
        resp = await client.get("/api/v3/scores/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["opportunity_type"] == "compounder"
        assert data["conviction"] == "exceptional"
        assert data["composite_score"] == 92.0

    async def test_get_score_case_insensitive(self, client):
        """Ticker lookup is case insensitive."""
        resp = await client.get("/api/v3/scores/aapl")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
