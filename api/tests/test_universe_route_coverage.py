"""Tests for routes/universe.py — GET /api/v1/universe/status endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, IngestionRun, Score, UniverseSnapshot
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _score_detail() -> dict:
    return {
        "ticker": "AAPL",
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
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def empty_factory(engine):
    """Session factory with no seeded data."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeded_factory(engine):
    """Session factory with universe snapshot, assets, and scores."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        snapshot = UniverseSnapshot(
            version="2026.02.20",
            config_hash="abc123",
            ticker_count=10,
            tickers=["AAPL", "MSFT", "GOOG", "AMZN", "META", "NVDA", "TSLA", "JNJ", "V", "COST"],
            exclusion_rules={},
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.flush()

        # Add an ingestion run
        run = IngestionRun(
            snapshot_id=snapshot.id,
            run_type="full",
            tickers_requested=10,
            tickers_succeeded=8,
            tickers_failed=2,
            status="completed",
            started_at=datetime.now(UTC),
        )
        session.add(run)
        await session.flush()

        # Add assets with scores
        for ticker in ["AAPL", "MSFT", "GOOG"]:
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
                conviction_level="high",
                signal="buy",
                quality_percentile=80.0,
                value_percentile=75.0,
                momentum_percentile=85.0,
                data_coverage=1.0,
                score_detail=_score_detail(),
            )
            session.add(score)

        # Add a quarantined asset
        q_asset = Asset(
            ticker="BADTK",
            name="Bad Ticker",
            sector="Technology",
            market_cap=Decimal("500000"),
            ingestion_status="quarantined",
        )
        session.add(q_asset)

        # Add permanently skipped asset
        s_asset = Asset(
            ticker="SKIP",
            name="Skipped Corp",
            sector="Technology",
            market_cap=Decimal("100000"),
            ingestion_status="permanently_skipped",
        )
        session.add(s_asset)

        await session.commit()
    return factory


class TestUniverseStatusNoSnapshot:
    @pytest.mark.asyncio
    async def test_returns_empty_status_without_snapshot(self, empty_factory):
        """When no active snapshot exists, returns zeroed-out status."""
        app = create_app()

        async def override_db():
            async with empty_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/universe/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["universe_version"] == "none"
        assert data["universe_size"] == 0
        assert data["is_complete"] is False
        assert data["ingestion_coverage"] == 0.0
        assert data["scoring_coverage"] == 0.0


class TestUniverseStatusWithData:
    @pytest.mark.asyncio
    async def test_returns_status_with_snapshot(self, seeded_factory):
        """With seeded data, returns universe status with counts."""
        app = create_app()

        async def override_db():
            async with seeded_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/universe/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["universe_version"] == "2026.02.20"
        assert data["universe_size"] == 10
        assert data["assets_scored"] == 3
        assert data["assets_quarantined"] == 1
        assert data["assets_permanently_skipped"] == 1
        assert isinstance(data["ingestion_coverage"], float)
        assert isinstance(data["scoring_coverage"], float)
