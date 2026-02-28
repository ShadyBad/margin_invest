"""Tests for universe API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class TestUniverseStatusSchema:
    def test_universe_status_model(self):
        from margin_api.schemas.universe import UniverseStatusResponse

        status = UniverseStatusResponse(
            universe_version="2026.02.15",
            universe_size=4847,
            assets_ingested=4812,
            assets_scored=4790,
            assets_fresh=4780,
            assets_stale=10,
            assets_expired=0,
            assets_quarantined=8,
            assets_permanently_skipped=3,
            ingestion_coverage=0.993,
            scoring_coverage=0.988,
            last_ingestion_run=datetime.now(UTC),
            last_scoring_run=datetime.now(UTC),
            is_complete=True,
        )
        assert status.is_complete is True
        assert status.ingestion_coverage == 0.993


class TestUniverseSummarySchema:
    def test_universe_summary_model(self):
        from margin_api.schemas.universe import UniverseSummary

        summary = UniverseSummary(
            version="2026.02.15",
            size=4847,
            scoring_coverage=0.988,
            is_complete=True,
            last_scoring_run=datetime.now(UTC),
        )
        data = summary.model_dump()
        assert data["version"] == "2026.02.15"
        assert data["is_complete"] is True


class TestWarningSchema:
    def test_warning_model(self):
        from margin_api.schemas.universe import Warning

        w = Warning(code="LOW_COVERAGE", message="Only 30% scored", severity="error")
        assert w.code == "LOW_COVERAGE"
        assert w.severity == "error"


# ---------------------------------------------------------------------------
# UniverseFunnelResponse schema tests
# ---------------------------------------------------------------------------


class TestUniverseFunnelSchema:
    def test_funnel_schema_instantiation(self):
        from margin_api.schemas.universe import UniverseFunnelResponse

        funnel = UniverseFunnelResponse(
            universe_size=3200,
            survived_filters=280,
            exceptional_count=12,
            high_count=35,
            medium_count=58,
            last_scored_at=datetime(2026, 2, 26, 4, 30, tzinfo=UTC),
        )
        assert funnel.universe_size == 3200
        assert funnel.survived_filters == 280
        assert funnel.exceptional_count == 12
        assert funnel.high_count == 35
        assert funnel.medium_count == 58
        assert funnel.last_scored_at is not None

    def test_funnel_schema_none_last_scored_at(self):
        from margin_api.schemas.universe import UniverseFunnelResponse

        funnel = UniverseFunnelResponse(
            universe_size=0,
            survived_filters=0,
            exceptional_count=0,
            high_count=0,
            medium_count=0,
            last_scored_at=None,
        )
        assert funnel.last_scored_at is None
        assert funnel.universe_size == 0


# ---------------------------------------------------------------------------
# _compute_funnel integration tests (async SQLite)
# ---------------------------------------------------------------------------


def _score_detail() -> dict:
    return {
        "ticker": "TEST",
        "composite_percentile": 80.0,
        "composite_tier": "high",
        "signal": "buy",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 80.0,
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [],
            "average_percentile": 75.0,
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 85.0,
        },
        "filters_passed": [],
        "data_coverage": 1.0,
    }


@pytest_asyncio.fixture
async def funnel_engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        from margin_api.db.base import Base

        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        from margin_api.db.base import Base

        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def funnel_seeded_factory(funnel_engine):
    """Session factory with snapshot + 3 assets at exceptional/high/medium."""
    from margin_api.db.models import Asset, Score, UniverseSnapshot

    factory = async_sessionmaker(funnel_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        snapshot = UniverseSnapshot(
            version="2026.02.26",
            config_hash="funnel123",
            ticker_count=100,
            tickers=["AAPL", "MSFT", "GOOG"],
            exclusion_rules={},
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.flush()

        levels = [
            ("AAPL", "exceptional"),
            ("MSFT", "high"),
            ("GOOG", "medium"),
        ]
        for ticker, conviction in levels:
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
    return factory


@pytest_asyncio.fixture
async def funnel_empty_factory(funnel_engine):
    """Session factory with no data."""
    return async_sessionmaker(funnel_engine, class_=AsyncSession, expire_on_commit=False)


class TestComputeFunnel:
    @pytest.mark.asyncio
    async def test_compute_funnel_with_seeded_data(self, funnel_seeded_factory):
        from margin_api.routes.universe import _compute_funnel

        async with funnel_seeded_factory() as session:
            result = await _compute_funnel(session)

        assert result.universe_size == 100
        assert result.survived_filters == 3
        assert result.exceptional_count == 1
        assert result.high_count == 1
        assert result.medium_count == 1
        assert result.last_scored_at is not None

    @pytest.mark.asyncio
    async def test_compute_funnel_empty_db(self, funnel_empty_factory):
        from margin_api.routes.universe import _compute_funnel

        async with funnel_empty_factory() as session:
            result = await _compute_funnel(session)

        assert result.universe_size == 0
        assert result.survived_filters == 0
        assert result.exceptional_count == 0
        assert result.high_count == 0
        assert result.medium_count == 0
        assert result.last_scored_at is None


class TestFunnelEndpoint:
    @pytest.mark.asyncio
    async def test_funnel_endpoint_returns_200(self, funnel_seeded_factory):
        from margin_api.app import create_app
        from margin_api.db.session import get_db

        app = create_app()

        async def override_db():
            async with funnel_seeded_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/universe/funnel")

        assert resp.status_code == 200
        data = resp.json()
        assert data["universe_size"] == 100
        assert data["survived_filters"] == 3
        assert data["exceptional_count"] == 1
        assert data["high_count"] == 1
        assert data["medium_count"] == 1
        assert data["last_scored_at"] is not None
