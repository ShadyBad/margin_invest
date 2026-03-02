"""Tests for score history endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def history_engine():
    """Create an async in-memory SQLite engine for history tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def history_client(history_engine):
    """Seed DB with multiple score rows per ticker for history testing."""
    factory = async_sessionmaker(history_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(aapl)
        await session.flush()

        base_time = datetime(2026, 1, 1, tzinfo=UTC)
        for i in range(5):
            score = Score(
                asset_id=aapl.id,
                composite_percentile=80.0 + i * 2,
                composite_raw_score=70.0 + i * 3,  # Different from percentile to catch mixups
                conviction_level="high",
                signal="buy",
                quality_percentile=85.0 + i,
                value_percentile=80.0 + i,
                momentum_percentile=82.0 + i,
                data_coverage=1.0,
                scored_at=base_time + timedelta(days=i * 7),
                margin_invest_value=200.0,
                buy_price=150.0,
                sell_price=250.0,
                actual_price=185.0,
                score_detail={},
            )
            session.add(score)
        await session.commit()

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestScoreHistory:
    async def test_score_history_returns_multiple_points(self, history_client):
        resp = await history_client.get("/api/v1/scores/AAPL/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert len(data["points"]) == 5
        assert data["total_runs"] == 5

    async def test_score_history_ordered_ascending(self, history_client):
        resp = await history_client.get("/api/v1/scores/AAPL/history")
        points = resp.json()["points"]
        dates = [p["scored_at"] for p in points]
        assert dates == sorted(dates)

    async def test_score_history_delta_computed(self, history_client):
        resp = await history_client.get("/api/v1/scores/AAPL/history")
        points = resp.json()["points"]
        assert points[0]["delta"] is None  # first point has no prior
        assert points[1]["delta"] == pytest.approx(2.0)  # 82 - 80

    async def test_score_history_404_unknown_ticker(self, history_client):
        resp = await history_client.get("/api/v1/scores/ZZZZ/history")
        assert resp.status_code == 404

    async def test_score_history_case_insensitive(self, history_client):
        resp = await history_client.get("/api/v1/scores/aapl/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"

    async def test_score_history_limit_parameter(self, history_client):
        resp = await history_client.get("/api/v1/scores/AAPL/history?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["points"]) == 2
        assert data["total_runs"] == 5  # total in DB, not limited count

    async def test_score_history_points_include_price_data(self, history_client):
        resp = await history_client.get("/api/v1/scores/AAPL/history")
        points = resp.json()["points"]
        for point in points:
            assert "margin_invest_value" in point
            assert "buy_price" in point
            assert "sell_price" in point
            assert "actual_price" in point

    async def test_score_field_matches_composite_raw_score(self, history_client):
        resp = await history_client.get("/api/v1/scores/AAPL/history")
        points = resp.json()["points"]
        for i, point in enumerate(points):
            expected_raw = 70.0 + i * 3
            assert point["score"] == pytest.approx(expected_raw)
            assert point["score"] == point["composite_raw_score"]
