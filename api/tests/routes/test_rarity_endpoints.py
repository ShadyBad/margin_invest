"""Tests for rarity API endpoints: GET /api/v1/rarity/picks and GET /api/v1/rarity/{ticker}."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, RarityScore
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
    """Helper: add ORM objects and commit synchronously."""

    async def _run():
        async with factory() as session:
            for obj in rows:
                session.add(obj)
            await session.commit()

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_run())


class TestRarityPicksEndpoint:
    def test_returns_empty_when_no_rarity_scores(self, client):
        """GET /api/v1/rarity/picks returns 200 with empty picks list when DB has no data."""
        tc, _factory = client
        response = tc.get("/api/v1/rarity/picks")
        assert response.status_code == 200
        data = response.json()
        assert data["picks"] == []
        assert data["regime"] == "unknown"
        assert data["universe_size"] == 0

    def test_returns_picks_ordered_by_score(self, client):
        """Seed 2 RarityScore rows; response picks must be in descending rarity_score order."""
        tc, factory = client
        scored_at = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

        asset_a = Asset(ticker="HIGH", name="High Score Co", sector="Technology")
        asset_b = Asset(ticker="LOW", name="Low Score Co", sector="Healthcare")
        _seed(factory, [asset_a, asset_b])

        async def _get_ids():
            async with factory() as session:
                from sqlalchemy import select

                rows = (await session.execute(select(Asset.id, Asset.ticker))).all()
                return {ticker: aid for aid, ticker in rows}

        id_map = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_get_ids())

        rs_high = RarityScore(
            asset_id=id_map["HIGH"],
            scored_at=scored_at,
            rarity_score=90.0,
            joint_rarity_pctl=80.0,
            convergence_score=0.9,
            historical_frequency=0.1,
            quality_momentum=0.8,
            smart_money_score=0.7,
            regime_alignment=0.85,
            combination_signature="ABC",
            regime="bull",
            conviction_score=0.9,
            is_generational=True,
            universe_size=500,
        )
        rs_low = RarityScore(
            asset_id=id_map["LOW"],
            scored_at=scored_at,
            rarity_score=40.0,
            joint_rarity_pctl=35.0,
            convergence_score=0.4,
            historical_frequency=0.5,
            quality_momentum=0.3,
            smart_money_score=0.2,
            regime_alignment=0.4,
            combination_signature="XYZ",
            regime="bull",
            conviction_score=0.4,
            is_generational=False,
            universe_size=500,
        )
        _seed(factory, [rs_high, rs_low])

        response = tc.get("/api/v1/rarity/picks")
        assert response.status_code == 200
        data = response.json()
        picks = data["picks"]
        assert len(picks) == 2
        assert picks[0]["ticker"] == "HIGH"
        assert picks[1]["ticker"] == "LOW"
        assert picks[0]["rarity_score"] > picks[1]["rarity_score"]
        assert data["regime"] == "bull"
        assert data["universe_size"] == 500
        assert data["scored_at"] is not None


class TestRarityTickerEndpoint:
    def test_returns_404_when_no_data(self, client):
        """GET /api/v1/rarity/NODATA returns 404 when ticker has no rarity rows."""
        tc, _factory = client
        response = tc.get("/api/v1/rarity/NODATA")
        assert response.status_code == 404
        assert "NODATA" in response.json()["detail"]

    def test_returns_rarity_for_ticker(self, client):
        """Seed a RarityScore + Asset for AAPL; verify response fields are correct."""
        tc, factory = client
        scored_at = datetime(2026, 3, 2, 10, 0, 0, tzinfo=UTC)

        asset = Asset(ticker="AAPL", name="Apple Inc.", sector="Technology")
        _seed(factory, [asset])

        async def _get_id():
            async with factory() as session:
                from sqlalchemy import select

                row = (
                    await session.execute(select(Asset.id).where(Asset.ticker == "AAPL"))
                ).scalar_one()
                return row

        asset_id = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_get_id())

        rs = RarityScore(
            asset_id=asset_id,
            scored_at=scored_at,
            rarity_score=75.5,
            joint_rarity_pctl=70.0,
            convergence_score=0.75,
            historical_frequency=0.08,
            quality_momentum=0.65,
            smart_money_score=0.60,
            regime_alignment=0.72,
            combination_signature="TECH-HIGH",
            regime="expansion",
            conviction_score=0.78,
            is_generational=True,
            universe_size=450,
            detail={
                "composite_tier": "strong",
                "pillar_percentiles": {"value": 80.0, "growth": 70.0},
                "dimensions": {
                    "joint_rarity_pctl": 70.0,
                    "convergence_score": 0.75,
                    "historical_frequency": 0.08,
                    "quality_momentum": 0.65,
                    "smart_money_score": 0.60,
                    "regime_alignment": 0.72,
                },
            },
        )
        _seed(factory, [rs])

        response = tc.get("/api/v1/rarity/AAPL")
        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "AAPL"
        assert data["rarity_score"] == pytest.approx(75.5)
        assert data["conviction_score"] == pytest.approx(0.78)
        assert data["is_generational"] is True
        assert data["combination_signature"] == "TECH-HIGH"
        assert data["regime"] == "expansion"
        assert data["universe_size"] == 450
        assert data["scored_at"] is not None

        dims = data["dimensions"]
        assert dims["joint_rarity_pctl"] == pytest.approx(70.0)
        assert dims["convergence_score"] == pytest.approx(0.75)
        assert dims["historical_frequency"] == pytest.approx(0.08)
        assert dims["quality_momentum"] == pytest.approx(0.65)
        assert dims["smart_money_score"] == pytest.approx(0.60)
        assert dims["regime_alignment"] == pytest.approx(0.72)

        pillar_pctls = data["pillar_percentiles"]
        assert pillar_pctls["value"] == pytest.approx(80.0)
        assert pillar_pctls["growth"] == pytest.approx(70.0)
