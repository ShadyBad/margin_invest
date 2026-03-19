"""Tests for universe activation gate: stage_universe_activation endpoint."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import PipelineApproval, UniverseSnapshot, User, UserRole
from margin_api.deps import get_admin_user
from margin_api.routes.admin import stage_universe_activation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _make_admin_user() -> User:
    user = MagicMock(spec=User)
    user.id = 1
    user.role = UserRole.ADMIN
    return user


# ---------------------------------------------------------------------------
# Async DB fixtures (real SQLite, same pattern as test_ml_deployment_gate)
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


def _make_client(admin_key: str = "test-admin-key") -> TestClient:
    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": admin_key}):
        app = create_app()
        return TestClient(app)


async def _create_active_snapshot(
    session: AsyncSession,
    tickers: list[str] | None = None,
    version: str = "2026.02.01",
) -> UniverseSnapshot:
    """Create an active UniverseSnapshot in the database."""
    if tickers is None:
        tickers = ["AAPL", "MSFT", "GOOG"]
    snap = UniverseSnapshot(
        version=version,
        config_hash="existing_hash",
        ticker_count=len(tickers),
        tickers=tickers,
        exclusion_rules={},
        is_active=True,
        activated_at=datetime.now(UTC),
    )
    session.add(snap)
    await session.flush()
    return snap


# ---------------------------------------------------------------------------
# HTTP-level tests
# ---------------------------------------------------------------------------


class TestUniverseActivateEndpoint:
    """Test the /admin/universe/activate HTTP endpoint returns 202 with staging."""

    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_endpoint_returns_202_with_staged_status(self):
        """Endpoint returns 202 Accepted with staged status."""
        mock_result = {
            "status": "staged",
            "approval_id": 42,
            "added_tickers": ["NVDA"],
            "removed_tickers": ["INTC"],
        }

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.stage_universe_activation",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.post("/api/v1/admin/universe/activate")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "staged"
        assert data["approval_id"] == 42
        assert data["added_tickers"] == ["NVDA"]
        assert data["removed_tickers"] == ["INTC"]

    def test_endpoint_requires_auth(self):
        """Endpoint rejects requests without admin session cookie."""
        client = _make_client(admin_key="correct-key")
        response = client.post("/api/v1/admin/universe/activate")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Unit tests for stage_universe_activation
# ---------------------------------------------------------------------------


class TestStageUniverseActivation:
    """Test the stage_universe_activation helper function."""

    @pytest.mark.asyncio
    async def test_creates_pipeline_approval_with_correct_gate_type(self, db_session):
        """stage_universe_activation creates a PipelineApproval with universe_activate gate."""
        # Create an existing active snapshot
        await _create_active_snapshot(db_session, tickers=["AAPL", "MSFT", "GOOG"])
        await db_session.commit()

        # Mock the universe config to return a different set of tickers
        mock_config = MagicMock()
        mock_config.tickers = ["AAPL", "MSFT", "NVDA", "TSLA"]

        config_path = MagicMock()
        config_path.exists.return_value = True

        with patch(
            "margin_api.routes.admin.load_universe_config",
            return_value=mock_config,
        ):
            result = await stage_universe_activation(db_session, config_path)

        assert result["status"] == "staged"
        assert "approval_id" in result

        # Check the PipelineApproval record
        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        assert len(approvals) == 1

        approval = approvals[0]
        assert approval.gate_type == "universe_activate"
        assert approval.status == "staged"
        assert approval.payload_ref is not None
        assert approval.payload_ref["proposed_tickers"] == ["AAPL", "MSFT", "NVDA", "TSLA"]

    @pytest.mark.asyncio
    async def test_computes_added_and_removed_tickers(self, db_session):
        """stage_universe_activation correctly diffs added and removed tickers."""
        await _create_active_snapshot(db_session, tickers=["AAPL", "MSFT", "GOOG", "INTC"])
        await db_session.commit()

        mock_config = MagicMock()
        mock_config.tickers = ["AAPL", "MSFT", "NVDA", "TSLA"]

        config_path = MagicMock()

        with patch(
            "margin_api.routes.admin.load_universe_config",
            return_value=mock_config,
        ):
            result = await stage_universe_activation(db_session, config_path)

        assert sorted(result["added_tickers"]) == ["NVDA", "TSLA"]
        assert sorted(result["removed_tickers"]) == ["GOOG", "INTC"]

        # Check the impact summary
        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        summary = approvals[0].impact_summary
        assert summary["current_count"] == 4
        assert summary["proposed_count"] == 4
        assert sorted(summary["added_tickers"]) == ["NVDA", "TSLA"]
        assert sorted(summary["removed_tickers"]) == ["GOOG", "INTC"]

    @pytest.mark.asyncio
    async def test_handles_no_existing_snapshot(self, db_session):
        """stage_universe_activation works when there is no current active snapshot."""
        mock_config = MagicMock()
        mock_config.tickers = ["AAPL", "MSFT"]

        config_path = MagicMock()

        with patch(
            "margin_api.routes.admin.load_universe_config",
            return_value=mock_config,
        ):
            result = await stage_universe_activation(db_session, config_path)

        assert result["status"] == "staged"
        assert sorted(result["added_tickers"]) == ["AAPL", "MSFT"]
        assert result["removed_tickers"] == []

        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        summary = approvals[0].impact_summary
        assert summary["current_count"] == 0
        assert summary["proposed_count"] == 2

    @pytest.mark.asyncio
    async def test_expires_at_roughly_24_hours(self, db_session):
        """stage_universe_activation sets expires_at ~24 hours from now."""
        mock_config = MagicMock()
        mock_config.tickers = ["AAPL"]

        config_path = MagicMock()

        with patch(
            "margin_api.routes.admin.load_universe_config",
            return_value=mock_config,
        ):
            await stage_universe_activation(db_session, config_path)

        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        expires = approvals[0].expires_at
        # Strip tz for comparison (sqlite may not preserve it)
        expires_naive = expires.replace(tzinfo=None) if expires.tzinfo else expires
        now_naive = datetime.now(UTC).replace(tzinfo=None)
        delta = expires_naive - now_naive
        assert timedelta(hours=23) < delta < timedelta(hours=25)
