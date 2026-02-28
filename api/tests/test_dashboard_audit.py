"""Tests for dashboard audit endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
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
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def audit_session(async_engine):
    """Seed DB with a score where composite_tier matches raw_score thresholds."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(aapl)
        await session.flush()

        score = Score(
            asset_id=aapl.id,
            composite_percentile=99.5,
            composite_raw_score=82.0,
            conviction_level="exceptional",
            signal="strong",
            quality_percentile=98.0,
            value_percentile=95.0,
            momentum_percentile=97.0,
            data_coverage=1.0,
            scored_at=datetime.now(UTC),
        )
        session.add(score)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def mismatched_session(async_engine):
    """Seed DB with a score where composite_tier DOES NOT match raw_score thresholds.

    raw_score=60.0 should produce composite_tier='none' (< 65 threshold),
    but we store 'high' to simulate a mismatch.
    """
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(aapl)
        await session.flush()

        score = Score(
            asset_id=aapl.id,
            composite_percentile=90.0,
            composite_raw_score=60.0,
            conviction_level="high",  # WRONG: 60.0 < 65 threshold -> should be "none"
            signal="strong",  # WRONG: none tier -> should be "neutral"
            quality_percentile=80.0,
            value_percentile=85.0,
            momentum_percentile=75.0,
            data_coverage=1.0,
            scored_at=datetime.now(UTC),
        )
        session.add(score)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def audit_client(audit_session):
    app = create_app()

    async def override_get_db():
        async with audit_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def mismatched_client(mismatched_session):
    app = create_app()

    async def override_get_db():
        async with mismatched_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestDashboardAudit:
    async def test_audit_returns_entries(self, audit_client):
        """Audit endpoint returns one entry per card with db_values and derived_values."""
        response = await audit_client.get("/api/v1/dashboard/audit")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["ticker"] == "AAPL"
        assert "db_values" in entry
        assert "derived_values" in entry
        assert "mismatches" in entry

    async def test_audit_no_mismatches_when_consistent(self, audit_client):
        """When DB composite_tier matches raw_score thresholds, no mismatches."""
        response = await audit_client.get("/api/v1/dashboard/audit")
        data = response.json()
        entry = data["entries"][0]
        assert entry["mismatches"] == []

    async def test_audit_detects_conviction_mismatch(self, mismatched_client):
        """When stored composite_tier doesn't match raw_score thresholds, flag it."""
        response = await mismatched_client.get("/api/v1/dashboard/audit")
        data = response.json()
        entry = data["entries"][0]
        assert len(entry["mismatches"]) > 0
        mismatch_fields = [m["field"] for m in entry["mismatches"]]
        assert "composite_tier" in mismatch_fields

    async def test_audit_db_values_match_raw_columns(self, audit_client):
        """db_values should contain raw DB column values."""
        response = await audit_client.get("/api/v1/dashboard/audit")
        data = response.json()
        db = data["entries"][0]["db_values"]
        assert db["composite_raw_score"] == 82.0
        assert db["composite_tier"] == "exceptional"
        assert db["signal"] == "strong"
        assert db["quality_percentile"] == 98.0

    async def test_audit_derived_values_use_engine_thresholds(self, audit_client):
        """derived_values should recompute conviction from raw_score using engine thresholds."""
        response = await audit_client.get("/api/v1/dashboard/audit")
        data = response.json()
        derived = data["entries"][0]["derived_values"]
        # raw_score=82.0 >= 79 -> exceptional
        assert derived["composite_tier"] == "exceptional"
