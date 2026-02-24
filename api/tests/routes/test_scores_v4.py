"""Tests for V4Score serving via the score endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, MlModelRun, Score, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _v4_detail() -> dict:
    """Minimal V4Score detail JSONB payload."""
    return {
        "ticker": "TEST",
        "name": "Test Corp",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [
                {"name": "roe", "raw_value": 0.3, "percentile_rank": 80.0, "detail": ""}
            ],
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [
                {"name": "ev_ebit", "raw_value": 12.0, "percentile_rank": 70.0, "detail": ""}
            ],
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [
                {"name": "price_mom", "raw_value": 0.1, "percentile_rank": 65.0, "detail": ""}
            ],
        },
        "filters_passed": [
            {"name": "market_cap", "passed": True, "detail": "", "verdict": "pass"}
        ],
        "data_coverage": 0.95,
        "signal": "buy",
        "composite_percentile": 85.0,
    }


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
    """Build an AsyncClient with DB override."""
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
class TestV4ScoreEndpoint:
    async def test_get_score_serves_v4_ml_fields(self, session_factory):
        """When V4Score exists, response includes ML fields."""
        async with session_factory() as session:
            asset = Asset(
                ticker="TEST",
                name="Test Corp",
                sector="Technology",
                market_cap=Decimal("100000000000"),
            )
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="high",
                rules_conviction="medium",
                style="growth",
                timing_signal="buy_now",
                max_position_pct=5.0,
                regime="normal",
                composite_score=75.0,
                ml_alpha=0.05,
                ml_confidence=0.82,
                ml_override="promoted",
                detail=_v4_detail(),
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/TEST")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ml_alpha"] == 0.05
            assert data["ml_confidence"] == 0.82
            assert data["ml_override"] == "promoted"
            assert data["rules_conviction"] == "medium"
            assert data["style"] == "growth"
            assert data["conviction_level"] == "high"
            assert data["regime"] == "normal"

    async def test_get_score_serves_v4_track_fields(self, session_factory):
        """V4Score track_a/b/c are included in response."""
        async with session_factory() as session:
            asset = Asset(
                ticker="TRK",
                name="Track Corp",
                sector="Technology",
                market_cap=Decimal("50000000000"),
            )
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="exceptional",
                rules_conviction="high",
                style="value",
                timing_signal="buy_now",
                max_position_pct=10.0,
                regime="normal",
                composite_score=90.0,
                ml_alpha=0.08,
                ml_confidence=0.9,
                ml_override="none",
                track_a={"name": "compounder", "score": 92.0},
                track_b={"name": "mispricing", "score": 55.0},
                track_c={"name": "ml_alpha", "score": 88.0},
                detail=_v4_detail(),
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/TRK")
            assert resp.status_code == 200
            data = resp.json()
            assert data["track_a"] == {"name": "compounder", "score": 92.0}
            assert data["track_b"] == {"name": "mispricing", "score": 55.0}
            assert data["track_c"] == {"name": "ml_alpha", "score": 88.0}

    async def test_get_score_serves_ml_model_metadata(self, session_factory):
        """When MlModelRun exists, model metadata is populated."""
        async with session_factory() as session:
            asset = Asset(
                ticker="MLM",
                name="ML Model Corp",
                sector="Technology",
                market_cap=Decimal("100000000000"),
            )
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="high",
                rules_conviction="medium",
                style="growth",
                timing_signal="buy_now",
                max_position_pct=5.0,
                regime="normal",
                composite_score=75.0,
                ml_alpha=0.05,
                ml_confidence=0.82,
                ml_override="promoted",
                detail=_v4_detail(),
            )
            ml_run = MlModelRun(
                model_type="lightgbm_cluster",
                n_clusters=5,
                n_features=20,
                n_samples=500,
                status="completed",
                model_qualifies=True,
                overall_rank_ic=0.12,
                created_at=datetime(2026, 2, 20, 10, 0, 0, tzinfo=UTC),
            )
            session.add_all([v4, ml_run])
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/MLM")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ml_model_qualified"] is True
            assert data["ml_model_rank_ic"] == 0.12
            assert "2026-02-20" in data["ml_model_trained_at"]

    async def test_get_score_falls_back_to_v2(self, session_factory):
        """When no V4Score exists, falls back to Score table with null ML fields."""
        async with session_factory() as session:
            asset = Asset(
                ticker="OLD",
                name="Old Corp",
                sector="Financials",
                market_cap=Decimal("50000000000"),
            )
            session.add(asset)
            await session.flush()

            score = Score(
                asset_id=asset.id,
                composite_percentile=60.0,
                composite_raw_score=55.0,
                conviction_level="medium",
                signal="watch",
                quality_percentile=50.0,
                value_percentile=55.0,
                momentum_percentile=45.0,
                data_coverage=0.8,
                scored_at=datetime.now(UTC),
            )
            session.add(score)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/OLD")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ml_alpha"] is None
            assert data["ml_override"] is None
            assert data["conviction_level"] == "medium"

    async def test_v4_preferred_over_v2(self, session_factory):
        """When both V4Score and Score exist, V4Score is preferred."""
        async with session_factory() as session:
            asset = Asset(
                ticker="BOTH",
                name="Both Corp",
                sector="Technology",
                market_cap=Decimal("100000000000"),
            )
            session.add(asset)
            await session.flush()

            # Old v2 score
            score = Score(
                asset_id=asset.id,
                composite_percentile=50.0,
                composite_raw_score=45.0,
                conviction_level="none",
                signal="no_action",
                quality_percentile=40.0,
                value_percentile=45.0,
                momentum_percentile=35.0,
                data_coverage=0.7,
                scored_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
            # Newer v4 score
            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime(2026, 2, 1, tzinfo=UTC),
                opportunity_type="compounder",
                conviction="exceptional",
                rules_conviction="high",
                style="growth",
                timing_signal="buy_now",
                max_position_pct=10.0,
                regime="normal",
                composite_score=95.0,
                ml_alpha=0.1,
                ml_confidence=0.95,
                ml_override="none",
                detail=_v4_detail(),
            )
            session.add_all([score, v4])
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/BOTH")
            assert resp.status_code == 200
            data = resp.json()
            # Should use V4 score, not V2
            assert data["conviction_level"] == "exceptional"
            assert data["ml_alpha"] == 0.1
