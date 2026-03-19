"""Tests for sector endpoints: GET /api/v1/sectors and GET /api/v1/sectors/{sector}/champion."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def client():
    """TestClient backed by an in-memory SQLite DB."""

    async def _setup():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return engine, factory

    engine, factory = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_setup())

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    tc = TestClient(app)
    yield tc, factory
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(engine.dispose())


def _seed(factory, rows: list) -> None:
    """Synchronously add ORM objects and commit."""

    async def _run():
        async with factory() as session:
            for obj in rows:
                session.add(obj)
            await session.commit()

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_run())


def _get_asset_ids(factory, tickers: list[str]) -> dict[str, int]:
    """Return a {ticker: id} map for the given tickers."""
    from sqlalchemy import select

    async def _run():
        async with factory() as session:
            rows = (await session.execute(select(Asset.id, Asset.ticker))).all()
            return {ticker: aid for aid, ticker in rows if ticker in tickers}

    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_run())


def _make_v4(asset_id: int, composite_score: float, published: bool = True) -> V4Score:
    return V4Score(
        asset_id=asset_id,
        scored_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
        opportunity_type="growth",
        conviction="strong",
        rules_conviction="strong",
        style="growth",
        timing_signal="bullish",
        regime="bull",
        composite_score=composite_score,
        published=published,
        detail={"composite_tier": "strong", "signal": "bullish"},
    )


class TestListSectors:
    def test_returns_empty_list_when_no_published_scores(self, client):
        """GET /api/v1/sectors returns [] when DB has no published V4Scores."""
        tc, _factory = client
        response = tc.get("/api/v1/sectors")
        assert response.status_code == 200
        assert response.json() == []

    def test_unpublished_scores_excluded(self, client):
        """Unpublished V4Scores are not counted in sector summaries."""
        tc, factory = client
        asset = Asset(ticker="UNPU", name="Unpublished Co", sector="Technology")
        _seed(factory, [asset])
        ids = _get_asset_ids(factory, ["UNPU"])
        v4 = _make_v4(ids["UNPU"], composite_score=80.0, published=False)
        _seed(factory, [v4])

        response = tc.get("/api/v1/sectors")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_sectors_with_correct_summary(self, client):
        """Seed two tickers in Technology; verify count, avg, top_ticker, top_score."""
        tc, factory = client
        asset_a = Asset(ticker="HIGH", name="High Score Co", sector="Technology")
        asset_b = Asset(ticker="LOW", name="Low Score Co", sector="Technology")
        _seed(factory, [asset_a, asset_b])
        ids = _get_asset_ids(factory, ["HIGH", "LOW"])

        v4_high = _make_v4(ids["HIGH"], composite_score=90.0)
        v4_low = _make_v4(ids["LOW"], composite_score=50.0)
        _seed(factory, [v4_high, v4_low])

        response = tc.get("/api/v1/sectors")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        tech = data[0]
        assert tech["sector"] == "Technology"
        assert tech["asset_count"] == 2
        assert tech["avg_composite_score"] == pytest.approx(70.0, rel=1e-4)
        assert tech["top_ticker"] == "HIGH"
        assert tech["top_score"] == pytest.approx(90.0)

    def test_returns_multiple_sectors(self, client):
        """Seed tickers in two different sectors; both appear in the list."""
        tc, factory = client
        asset_tech = Asset(ticker="TECH", name="Tech Co", sector="Technology")
        asset_health = Asset(ticker="HLTH", name="Health Co", sector="Healthcare")
        _seed(factory, [asset_tech, asset_health])
        ids = _get_asset_ids(factory, ["TECH", "HLTH"])

        v4_tech = _make_v4(ids["TECH"], composite_score=75.0)
        v4_health = _make_v4(ids["HLTH"], composite_score=60.0)
        _seed(factory, [v4_tech, v4_health])

        response = tc.get("/api/v1/sectors")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        sectors = {row["sector"] for row in data}
        assert sectors == {"Technology", "Healthcare"}


class TestSectorChampion:
    def test_returns_404_for_unknown_sector(self, client):
        """GET /api/v1/sectors/UNKNOWN/champion returns 404."""
        tc, _factory = client
        response = tc.get("/api/v1/sectors/UNKNOWN/champion")
        assert response.status_code == 404
        assert "UNKNOWN" in response.json()["detail"]

    def test_returns_404_when_no_published_scores_in_sector(self, client):
        """404 when the sector exists as an Asset but has no published scores."""
        tc, factory = client
        asset = Asset(ticker="NOPE", name="No Published", sector="Energy")
        _seed(factory, [asset])
        ids = _get_asset_ids(factory, ["NOPE"])
        v4 = _make_v4(ids["NOPE"], composite_score=70.0, published=False)
        _seed(factory, [v4])

        response = tc.get("/api/v1/sectors/Energy/champion")
        assert response.status_code == 404

    def test_returns_highest_scored_ticker(self, client):
        """Champion endpoint returns the ticker with the highest composite_score."""
        tc, factory = client
        asset_a = Asset(ticker="BEST", name="Best Co", sector="Technology", market_cap=1_000_000)
        asset_b = Asset(ticker="GOOD", name="Good Co", sector="Technology", market_cap=500_000)
        _seed(factory, [asset_a, asset_b])
        ids = _get_asset_ids(factory, ["BEST", "GOOD"])

        v4_best = _make_v4(ids["BEST"], composite_score=95.0)
        v4_good = _make_v4(ids["GOOD"], composite_score=70.0)
        _seed(factory, [v4_best, v4_good])

        response = tc.get("/api/v1/sectors/Technology/champion")
        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "BEST"
        assert data["sector"] == "Technology"
        assert data["composite_score"] == pytest.approx(95.0)
        assert data["composite_tier"] == "strong"
        assert data["signal"] == "bullish"
        assert data["market_cap"] == pytest.approx(1_000_000.0)

    def test_champion_market_cap_can_be_none(self, client):
        """market_cap is None when Asset.market_cap is 0 / unset."""
        tc, factory = client
        asset = Asset(ticker="NOMC", name="No Market Cap Co", sector="Utilities")
        _seed(factory, [asset])
        ids = _get_asset_ids(factory, ["NOMC"])
        v4 = _make_v4(ids["NOMC"], composite_score=55.0)
        _seed(factory, [v4])

        response = tc.get("/api/v1/sectors/Utilities/champion")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "NOMC"
        # market_cap 0 treated as None
        assert data["market_cap"] is None
