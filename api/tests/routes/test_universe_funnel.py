"""Tests for the /api/v1/universe/funnel endpoint and _compute_funnel helper.

The test_universe_route_coverage.py covers /universe/status but not /universe/funnel.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score, UniverseSnapshot
from margin_api.db.session import get_db
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


def _make_client(session_factory):
    app = create_app()

    async def db_override():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = db_override
    return app


def _score_detail() -> dict:
    return {
        "ticker": "AAPL",
        "composite_percentile": 80.0,
        "composite_tier": "high",
        "signal": "buy",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": []},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": []},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": []},
        "filters_passed": [],
        "data_coverage": 1.0,
    }


@pytest.mark.asyncio
class TestUniverseFunnel:
    async def test_funnel_no_snapshot(self, session_factory):
        """Without a snapshot, funnel returns universe_size=0."""
        app = _make_client(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/universe/funnel")

        assert resp.status_code == 200
        data = resp.json()
        assert data["universe_size"] == 0
        assert data["survived_filters"] == 0
        assert data["exceptional_count"] == 0
        assert data["high_count"] == 0
        assert data["medium_count"] == 0

    async def test_funnel_with_scores(self, session_factory):
        """Funnel returns correct counts per conviction level."""
        factory = session_factory
        async with factory() as session:
            snapshot = UniverseSnapshot(
                version="v1",
                config_hash="abc",
                ticker_count=10,
                tickers=["AAPL", "MSFT", "GOOG"],
                is_active=True,
                activated_at=datetime.now(UTC),
            )
            session.add(snapshot)
            await session.flush()

            conviction_map = {
                "AAPL": "exceptional",
                "MSFT": "high",
                "GOOG": "medium",
            }
            for ticker, conviction in conviction_map.items():
                asset = Asset(
                    ticker=ticker,
                    name=f"{ticker} Inc.",
                    sector="Technology",
                    market_cap=Decimal("1000000000"),
                )
                session.add(asset)
                await session.flush()
                score = Score(
                    asset_id=asset.id,
                    composite_percentile=80.0,
                    composite_raw_score=75.0,
                    conviction_level=conviction,
                    signal="buy",
                    quality_percentile=80.0,
                    value_percentile=75.0,
                    momentum_percentile=85.0,
                    data_coverage=1.0,
                    score_detail=_score_detail(),
                )
                session.add(score)
            await session.commit()

        app = _make_client(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/universe/funnel")

        assert resp.status_code == 200
        data = resp.json()
        assert data["universe_size"] == 10
        assert data["survived_filters"] == 3
        assert data["exceptional_count"] == 1
        assert data["high_count"] == 1
        assert data["medium_count"] == 1
        assert data["last_scored_at"] is not None

    async def test_funnel_no_scores(self, session_factory):
        """With a snapshot but no scores, all counts are zero."""
        async with session_factory() as session:
            snapshot = UniverseSnapshot(
                version="v2",
                config_hash="def",
                ticker_count=5,
                tickers=["A", "B", "C"],
                is_active=True,
                activated_at=datetime.now(UTC),
            )
            session.add(snapshot)
            await session.commit()

        app = _make_client(session_factory)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/universe/funnel")

        assert resp.status_code == 200
        data = resp.json()
        assert data["universe_size"] == 5
        assert data["survived_filters"] == 0
        assert data["exceptional_count"] == 0
