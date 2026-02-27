"""Tests for the public governance transparency endpoint."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import IngestionRun, PipelineApproval, UniverseSnapshot
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# ---------------------------------------------------------------------------
# Async DB fixtures (real SQLite)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(session_factory) -> TestClient:
    """Create an app + test client with DB override and no admin key required."""
    get_settings.cache_clear()

    async def db_override():
        async with session_factory() as s:
            yield s

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-admin-key"}):
        app = create_app()
        app.dependency_overrides[get_db] = db_override
        client = TestClient(app)
    return client


async def _create_snapshot(session: AsyncSession) -> UniverseSnapshot:
    """Create a minimal UniverseSnapshot (required FK for IngestionRun)."""
    snapshot = UniverseSnapshot(
        version="v1",
        config_hash="abc123",
        ticker_count=10,
        tickers=["AAPL", "MSFT"],
        is_active=True,
        activated_at=datetime.now(UTC),
    )
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot


async def _create_ingestion_run(
    session: AsyncSession,
    snapshot_id: int,
    status: str = "completed",
    completed_at: datetime | None = None,
) -> IngestionRun:
    """Create an IngestionRun record."""
    run = IngestionRun(
        snapshot_id=snapshot_id,
        run_type="full",
        tickers_requested=10,
        tickers_succeeded=10,
        status=status,
        started_at=datetime.now(UTC) - timedelta(hours=1),
        completed_at=completed_at or datetime.now(UTC),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def _create_approval(
    session: AsyncSession,
    gate_type: str = "score_publish",
    status: str = "approved",
    decided_at: datetime | None = None,
) -> PipelineApproval:
    """Create a PipelineApproval record."""
    approval = PipelineApproval(
        gate_type=gate_type,
        status=status,
        payload_ref={"run_id": 42},
        impact_summary={"tickers_affected": 10},
        submitted_at=datetime.now(UTC) - timedelta(hours=1),
        decided_at=decided_at or datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    session.add(approval)
    await session.commit()
    await session.refresh(approval)
    return approval


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTransparencyEndpoint:
    """Tests for GET /api/v1/governance/transparency."""

    @pytest.mark.asyncio
    async def test_returns_oversight_levels_with_all_three_categories(
        self, db_session, session_factory
    ):
        """Response includes oversight_levels with in/on/out of the loop."""
        client = _make_client(session_factory)
        response = client.get("/api/v1/governance/transparency")

        assert response.status_code == 200
        data = response.json()
        levels = data["oversight_levels"]
        assert "in_the_loop" in levels
        assert "on_the_loop" in levels
        assert "out_of_the_loop" in levels

        # Verify specific items in each category
        assert "score_publication" in levels["in_the_loop"]
        assert "ml_model_deployment" in levels["in_the_loop"]
        assert "universe_activation" in levels["in_the_loop"]
        assert "filter_config" in levels["in_the_loop"]

        assert "daily_scoring_pipeline" in levels["on_the_loop"]
        assert "13f_ingest" in levels["on_the_loop"]
        assert "backtest_replay" in levels["on_the_loop"]

        assert "data_ingestion" in levels["out_of_the_loop"]
        assert "live_pricing" in levels["out_of_the_loop"]
        assert "data_quality" in levels["out_of_the_loop"]
        assert "accumulation_signals" in levels["out_of_the_loop"]

    @pytest.mark.asyncio
    async def test_returns_pipeline_health_with_status_field(
        self, db_session, session_factory
    ):
        """Response includes pipeline_health with status field."""
        client = _make_client(session_factory)
        response = client.get("/api/v1/governance/transparency")

        assert response.status_code == 200
        data = response.json()
        health = data["pipeline_health"]
        assert "status" in health
        assert health["status"] == "idle"
        # No completed runs yet, so last_successful_run is None
        assert health["last_successful_run"] is None

    @pytest.mark.asyncio
    async def test_returns_pipeline_health_with_last_successful_run(
        self, db_session, session_factory
    ):
        """pipeline_health.last_successful_run is set when a completed run exists."""
        snapshot = await _create_snapshot(db_session)
        completed_at = datetime(2026, 2, 27, 12, 0, 0, tzinfo=UTC)
        await _create_ingestion_run(
            db_session, snapshot.id, status="completed", completed_at=completed_at
        )

        client = _make_client(session_factory)
        response = client.get("/api/v1/governance/transparency")

        assert response.status_code == 200
        data = response.json()
        health = data["pipeline_health"]
        assert health["last_successful_run"] is not None
        assert "2026-02-27" in health["last_successful_run"]

    @pytest.mark.asyncio
    async def test_returns_last_approvals_for_approved_gate_types(
        self, db_session, session_factory
    ):
        """last_approvals includes entries for gate types with decisions."""
        decided_at = datetime(2026, 2, 27, 10, 0, 0, tzinfo=UTC)
        await _create_approval(
            db_session,
            gate_type="score_publish",
            status="approved",
            decided_at=decided_at,
        )
        await _create_approval(
            db_session,
            gate_type="ml_model_deploy",
            status="rejected",
            decided_at=decided_at,
        )

        client = _make_client(session_factory)
        response = client.get("/api/v1/governance/transparency")

        assert response.status_code == 200
        data = response.json()
        approvals = data["last_approvals"]

        assert "score_publish" in approvals
        assert approvals["score_publish"]["status"] == "approved"
        assert approvals["score_publish"]["decided_at"] is not None

        assert "ml_model_deploy" in approvals
        assert approvals["ml_model_deploy"]["status"] == "rejected"

        # universe_activate has no decisions, so not present
        assert "universe_activate" not in approvals

    @pytest.mark.asyncio
    async def test_no_auth_required(self, db_session, session_factory):
        """Endpoint returns 200 without any auth headers."""
        client = _make_client(session_factory)
        # No Authorization, no X-Admin-Key, no X-User-Id headers
        response = client.get("/api/v1/governance/transparency")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_database_returns_valid_response(
        self, db_session, session_factory
    ):
        """With no data at all, endpoint returns valid defaults."""
        client = _make_client(session_factory)
        response = client.get("/api/v1/governance/transparency")

        assert response.status_code == 200
        data = response.json()

        assert data["oversight_levels"] is not None
        assert data["last_approvals"] == {}
        assert data["pipeline_health"]["status"] == "idle"
        assert data["pipeline_health"]["last_successful_run"] is None

    @pytest.mark.asyncio
    async def test_only_latest_approval_per_gate_type(
        self, db_session, session_factory
    ):
        """When multiple decisions exist, only the most recent is returned."""
        old_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        new_time = datetime(2026, 2, 27, 12, 0, 0, tzinfo=UTC)

        await _create_approval(
            db_session,
            gate_type="score_publish",
            status="rejected",
            decided_at=old_time,
        )
        await _create_approval(
            db_session,
            gate_type="score_publish",
            status="approved",
            decided_at=new_time,
        )

        client = _make_client(session_factory)
        response = client.get("/api/v1/governance/transparency")

        assert response.status_code == 200
        data = response.json()
        assert data["last_approvals"]["score_publish"]["status"] == "approved"
        assert "2026-02-27" in data["last_approvals"]["score_publish"]["decided_at"]
