"""Tests for the public score endpoint."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score, V4Score
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


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


def _make_client(session_factory) -> TestClient:
    get_settings.cache_clear()

    async def db_override():
        async with session_factory() as s:
            yield s

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-admin-key"}):
        app = create_app()
        app.dependency_overrides[get_db] = db_override
        client = TestClient(app)
    return client


async def _seed_asset(
    session: AsyncSession, ticker: str = "AAPL", name: str = "Apple Inc"
) -> Asset:
    asset = Asset(ticker=ticker, name=name, sector="Technology")
    session.add(asset)
    await session.flush()
    return asset


async def _seed_v4_score(
    session: AsyncSession,
    asset: Asset,
    published: bool = True,
    conviction: str = "high",
    composite_score: float = 78.5,
    detail: dict | None = None,
) -> V4Score:
    if detail is None:
        detail = {
            "quality": {"average_percentile": 72.0, "sub_scores": []},
            "value": {"average_percentile": 81.0, "sub_scores": []},
            "momentum": {"average_percentile": 65.0, "sub_scores": []},
            "filters_passed": [
                {"name": "positive_earnings", "passed": True, "value": 5.0, "threshold": 0.0},
            ],
            "signal": "strong",
        }
    v4 = V4Score(
        asset_id=asset.id,
        scored_at=datetime.now(UTC),
        opportunity_type="value_compounder",
        conviction=conviction,
        rules_conviction=conviction,
        style="value",
        timing_signal="accumulate",
        max_position_pct=5.0,
        regime="expansion",
        composite_score=composite_score,
        ml_override="none",
        detail=detail,
        published=published,
    )
    session.add(v4)
    await session.flush()
    return v4


async def _seed_base_score(
    session: AsyncSession,
    asset: Asset,
    quality_pct: float = 70.0,
    value_pct: float = 75.0,
    momentum_pct: float = 60.0,
) -> Score:
    score = Score(
        asset_id=asset.id,
        scored_at=datetime.now(UTC),
        composite_raw_score=68.0,
        composite_percentile=72.0,
        quality_percentile=quality_pct,
        value_percentile=value_pct,
        momentum_percentile=momentum_pct,
        conviction_level="medium",
        signal="stable",
        data_coverage=0.95,
        score_detail={
            "filters_passed": [
                {"name": "positive_earnings", "passed": True, "value": 5.0, "threshold": 0.0},
            ],
        },
    )
    session.add(score)
    await session.flush()
    return score


@pytest.mark.asyncio
class TestPublicScoreEndpoint:
    async def test_happy_path_published_v4(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset, published=True)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["company_name"] == "Apple Inc"
        assert data["composite_score"] == 78.5
        assert data["composite_tier"] == "high"
        assert data["signal"] == "strong"
        assert data["factor_summary"]["quality_percentile"] == 72.0
        assert data["factor_summary"]["value_percentile"] == 81.0
        assert data["factor_summary"]["momentum_percentile"] == 65.0
        assert data["eliminated"] is False
        assert data["elimination_reason"] is None
        assert "scored_at" in data

    async def test_cache_control_header(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.headers.get("cache-control") == "public, max-age=300"

    async def test_fallback_to_unpublished_v4(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset, published=False)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"

    async def test_fallback_to_base_score(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_base_score(db_session, asset)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["factor_summary"]["quality_percentile"] == 70.0
        assert data["factor_summary"]["value_percentile"] == 75.0
        assert data["factor_summary"]["momentum_percentile"] == 60.0

    async def test_404_unknown_ticker(self, db_session, session_factory):
        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/ZZZZ")
        assert resp.status_code == 404

    async def test_eliminated_ticker(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        detail = {
            "quality": {"average_percentile": 15.0, "sub_scores": []},
            "value": {"average_percentile": 30.0, "sub_scores": []},
            "momentum": {"average_percentile": 10.0, "sub_scores": []},
            "filters_passed": [
                {"name": "positive_earnings", "passed": True, "value": 5.0, "threshold": 0.0},
                {"name": "debt_coverage", "passed": False, "value": 0.3, "threshold": 1.0},
            ],
            "signal": "failed",
        }
        await _seed_v4_score(db_session, asset, detail=detail, conviction="none")
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["eliminated"] is True
        assert data["elimination_reason"] == "debt_coverage"

    async def test_case_insensitive_ticker(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/aapl")
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"

    async def test_response_does_not_contain_forensic_fields(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        data = resp.json()
        forbidden = [
            "ml_alpha", "ml_confidence", "price_history", "signal_history",
            "buy_price", "sell_price", "margin_invest_value",
            "opportunity_type", "track_a", "track_b", "track_c",
            "sub_scores", "filters_passed",
        ]
        for field in forbidden:
            assert field not in data, f"Forensic field '{field}' leaked into public response"
