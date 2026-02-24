"""Tests for V4Score ML field enrichment on dashboard picks."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
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


def _make_client(session_factory):
    """Build an AsyncClient with DB override."""
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
class TestDashboardV4Enrichment:
    async def test_dashboard_picks_include_ml_fields(self, session_factory):
        """Dashboard picks should include ml_override and style from V4Score."""
        async with session_factory() as session:
            asset = Asset(
                ticker="MLT",
                name="ML Test",
                sector="Technology",
                market_cap=Decimal("100000000000"),
            )
            session.add(asset)
            await session.flush()

            # Add a Score (v2) for the asset — needed for dashboard query
            score = Score(
                asset_id=asset.id,
                composite_percentile=90.0,
                composite_raw_score=85.0,
                conviction_level="exceptional",
                signal="buy",
                quality_percentile=80.0,
                value_percentile=75.0,
                momentum_percentile=85.0,
                data_coverage=0.95,
                scored_at=datetime.now(UTC),
            )
            session.add(score)

            # Add a V4Score with ML data
            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="exceptional",
                rules_conviction="high",
                style="growth",
                timing_signal="buy_now",
                max_position_pct=5.0,
                regime="normal",
                composite_score=85.0,
                ml_alpha=0.05,
                ml_confidence=0.82,
                ml_override="promoted",
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["picks"]) > 0
            pick = next((p for p in data["picks"] if p["ticker"] == "MLT"), None)
            assert pick is not None
            assert pick["ml_override"] == "promoted"
            assert pick["style"] == "growth"

    async def test_dashboard_picks_without_v4_have_null_ml_fields(self, session_factory):
        """Dashboard picks with no V4Score should have null ml_override and style."""
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
                composite_percentile=92.0,
                composite_raw_score=88.0,
                conviction_level="exceptional",
                signal="buy",
                quality_percentile=85.0,
                value_percentile=80.0,
                momentum_percentile=90.0,
                data_coverage=0.9,
                scored_at=datetime.now(UTC),
            )
            session.add(score)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            assert resp.status_code == 200
            data = resp.json()
            pick = next((p for p in data["picks"] if p["ticker"] == "OLD"), None)
            assert pick is not None
            assert pick["ml_override"] is None
            assert pick["style"] is None

    async def test_dashboard_enriches_multiple_picks(self, session_factory):
        """V4 enrichment works across multiple picks with different V4 states."""
        async with session_factory() as session:
            # Asset with V4
            a1 = Asset(
                ticker="V4A",
                name="V4 Asset",
                sector="Technology",
                market_cap=Decimal("100000000000"),
            )
            # Asset without V4
            a2 = Asset(
                ticker="NOV4",
                name="No V4 Asset",
                sector="Healthcare",
                market_cap=Decimal("80000000000"),
            )
            session.add_all([a1, a2])
            await session.flush()

            s1 = Score(
                asset_id=a1.id,
                composite_percentile=95.0,
                composite_raw_score=90.0,
                conviction_level="exceptional",
                signal="buy",
                quality_percentile=88.0,
                value_percentile=85.0,
                momentum_percentile=92.0,
                data_coverage=0.95,
                scored_at=datetime.now(UTC),
            )
            s2 = Score(
                asset_id=a2.id,
                composite_percentile=91.0,
                composite_raw_score=86.0,
                conviction_level="exceptional",
                signal="buy",
                quality_percentile=82.0,
                value_percentile=78.0,
                momentum_percentile=88.0,
                data_coverage=0.9,
                scored_at=datetime.now(UTC),
            )
            session.add_all([s1, s2])

            v4 = V4Score(
                asset_id=a1.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="exceptional",
                rules_conviction="high",
                style="value",
                timing_signal="buy_now",
                max_position_pct=8.0,
                regime="normal",
                composite_score=90.0,
                ml_alpha=0.07,
                ml_confidence=0.88,
                ml_override="none",
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            assert resp.status_code == 200
            data = resp.json()

            v4_pick = next((p for p in data["picks"] if p["ticker"] == "V4A"), None)
            assert v4_pick is not None
            assert v4_pick["ml_override"] == "none"
            assert v4_pick["style"] == "value"

            nov4_pick = next((p for p in data["picks"] if p["ticker"] == "NOV4"), None)
            assert nov4_pick is not None
            assert nov4_pick["ml_override"] is None
            assert nov4_pick["style"] is None
