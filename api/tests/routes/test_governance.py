"""Tests for admin governance approval endpoints."""

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
from margin_api.db.models import PipelineApproval
from margin_api.db.session import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# ---------------------------------------------------------------------------
# Async DB fixtures (real SQLite, same pattern as test_universe_gate)
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


def _make_app_and_client(
    admin_key: str = "test-admin-key",
    db_override=None,
) -> tuple:
    """Create app and client with admin key and optional DB override."""
    get_settings.cache_clear()
    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": admin_key}):
        app = create_app()
        if db_override is not None:
            app.dependency_overrides[get_db] = db_override
        client = TestClient(app)
    return app, client


async def _create_approval(
    session: AsyncSession,
    gate_type: str = "score_publish",
    status: str = "staged",
    pipeline_id: str | None = None,
    payload_ref: dict | None = None,
    impact_summary: dict | None = None,
    decision_reason: str | None = None,
    decided_at: datetime | None = None,
) -> PipelineApproval:
    """Create a PipelineApproval record in the database."""
    approval = PipelineApproval(
        gate_type=gate_type,
        status=status,
        pipeline_id=pipeline_id,
        payload_ref=payload_ref or {"run_id": 42},
        impact_summary=impact_summary or {"tickers_affected": 10},
        submitted_at=datetime.now(UTC),
        decided_at=decided_at,
        decision_reason=decision_reason,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    session.add(approval)
    await session.commit()
    await session.refresh(approval)
    return approval


def _make_mock_db_override(mock_session):
    """Build a get_db dependency override that returns the given mock session."""
    async def _override():
        return mock_session

    return _override


def _build_mock_session_with_approvals(approvals: list[PipelineApproval]):
    """Build a mock AsyncSession that returns the given approvals from execute."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = approvals
    mock_result.scalar_one_or_none.return_value = approvals[0] if approvals else None

    async def mock_execute(stmt):
        return mock_result

    mock_session = AsyncMock()
    mock_session.execute = mock_execute
    return mock_session


# ---------------------------------------------------------------------------
# Tests: List approvals
# ---------------------------------------------------------------------------


class TestListApprovals:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_list_approvals_returns_all(self):
        """GET /admin/approvals returns all approvals."""
        now = datetime.now(UTC)
        approval1 = MagicMock(spec=PipelineApproval)
        approval1.id = 1
        approval1.gate_type = "score_publish"
        approval1.status = "staged"
        approval1.pipeline_id = None
        approval1.payload_ref = {"run_id": 1}
        approval1.impact_summary = {"tickers": 5}
        approval1.submitted_at = now
        approval1.decided_at = None
        approval1.decided_by = None
        approval1.decision_reason = None
        approval1.expires_at = now + timedelta(hours=24)

        approval2 = MagicMock(spec=PipelineApproval)
        approval2.id = 2
        approval2.gate_type = "ml_model_deploy"
        approval2.status = "approved"
        approval2.pipeline_id = "pipe-123"
        approval2.payload_ref = {"model_id": 7}
        approval2.impact_summary = {"rank_ic": 0.22}
        approval2.submitted_at = now - timedelta(hours=1)
        approval2.decided_at = now
        approval2.decided_by = 1
        approval2.decision_reason = "Looks good"
        approval2.expires_at = now + timedelta(hours=23)

        mock_session = _build_mock_session_with_approvals([approval1, approval2])

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/approvals",
            headers={"X-Admin-Key": "test-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["approvals"]) == 2
        assert data["approvals"][0]["id"] == 1
        assert data["approvals"][0]["gate_type"] == "score_publish"
        assert data["approvals"][1]["id"] == 2
        assert data["approvals"][1]["gate_type"] == "ml_model_deploy"

    def test_list_approvals_filtered_by_status(self):
        """GET /admin/approvals?status=staged returns only staged approvals."""
        now = datetime.now(UTC)
        staged = MagicMock(spec=PipelineApproval)
        staged.id = 1
        staged.gate_type = "score_publish"
        staged.status = "staged"
        staged.pipeline_id = None
        staged.payload_ref = {}
        staged.impact_summary = {}
        staged.submitted_at = now
        staged.decided_at = None
        staged.decided_by = None
        staged.decision_reason = None
        staged.expires_at = now + timedelta(hours=24)

        mock_session = _build_mock_session_with_approvals([staged])

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/approvals?status=staged",
            headers={"X-Admin-Key": "test-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["approvals"]) == 1
        assert data["approvals"][0]["status"] == "staged"

    def test_list_approvals_requires_admin_key(self):
        """GET /admin/approvals returns 422 without X-Admin-Key header."""
        _, client = _make_app_and_client(admin_key="test-key")
        response = client.get("/api/v1/admin/approvals")
        assert response.status_code == 422

    def test_list_approvals_rejects_wrong_key(self):
        """GET /admin/approvals returns 403 with wrong admin key."""
        _, client = _make_app_and_client(admin_key="correct-key")
        response = client.get(
            "/api/v1/admin/approvals",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Tests: Get single approval
# ---------------------------------------------------------------------------


class TestGetApproval:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_get_approval_by_id(self):
        """GET /admin/approvals/1 returns the approval."""
        now = datetime.now(UTC)
        approval = MagicMock(spec=PipelineApproval)
        approval.id = 1
        approval.gate_type = "score_publish"
        approval.status = "staged"
        approval.pipeline_id = None
        approval.payload_ref = {"run_id": 42}
        approval.impact_summary = {"tickers_affected": 10}
        approval.submitted_at = now
        approval.decided_at = None
        approval.decided_by = None
        approval.decision_reason = None
        approval.expires_at = now + timedelta(hours=24)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = approval

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/approvals/1",
            headers={"X-Admin-Key": "test-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["gate_type"] == "score_publish"
        assert data["status"] == "staged"

    def test_get_approval_not_found(self):
        """GET /admin/approvals/999 returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/approvals/999",
            headers={"X-Admin-Key": "test-key"},
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Approve
# ---------------------------------------------------------------------------


class TestApproveApproval:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_approve_transitions_to_approved(self):
        """POST /admin/approvals/1/approve transitions status to approved."""
        now = datetime.now(UTC)
        approval = MagicMock(spec=PipelineApproval)
        approval.id = 1
        approval.gate_type = "score_publish"
        approval.status = "staged"
        approval.pipeline_id = None
        approval.payload_ref = {"run_id": 42}
        approval.impact_summary = {"tickers_affected": 10}
        approval.submitted_at = now
        approval.decided_at = None
        approval.decided_by = None
        approval.decision_reason = None
        approval.expires_at = now + timedelta(hours=24)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = approval

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )

        with patch(
            "margin_api.routes.governance._enqueue_publish_job",
            new_callable=AsyncMock,
        ) as mock_enqueue:
            response = client.post(
                "/api/v1/admin/approvals/1/approve",
                headers={"X-Admin-Key": "test-key"},
                json={"reason": "LGTM"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approval_id"] == 1

        # Verify the approval object was mutated
        assert approval.status == "approved"
        assert approval.decision_reason == "LGTM"
        assert approval.decided_at is not None
        mock_enqueue.assert_called_once()

    def test_approve_not_found(self):
        """POST /admin/approvals/999/approve returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/999/approve",
            headers={"X-Admin-Key": "test-key"},
            json={},
        )

        assert response.status_code == 404

    def test_approve_non_staged_returns_409(self):
        """POST /admin/approvals/1/approve returns 409 if not staged."""
        approval = MagicMock(spec=PipelineApproval)
        approval.id = 1
        approval.status = "approved"  # Already approved

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = approval

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/1/approve",
            headers={"X-Admin-Key": "test-key"},
            json={},
        )

        assert response.status_code == 409

    def test_approve_rejects_wrong_key(self):
        """POST /admin/approvals/1/approve returns 403 with wrong key."""
        _, client = _make_app_and_client(admin_key="correct-key")
        response = client.post(
            "/api/v1/admin/approvals/1/approve",
            headers={"X-Admin-Key": "wrong-key"},
            json={},
        )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Tests: Reject
# ---------------------------------------------------------------------------


class TestRejectApproval:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_reject_transitions_to_rejected(self):
        """POST /admin/approvals/1/reject transitions status to rejected."""
        now = datetime.now(UTC)
        approval = MagicMock(spec=PipelineApproval)
        approval.id = 1
        approval.gate_type = "score_publish"
        approval.status = "staged"
        approval.pipeline_id = None
        approval.payload_ref = {}
        approval.impact_summary = {}
        approval.submitted_at = now
        approval.decided_at = None
        approval.decided_by = None
        approval.decision_reason = None
        approval.expires_at = now + timedelta(hours=24)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = approval

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute
        mock_session.commit = AsyncMock()

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/1/reject",
            headers={"X-Admin-Key": "test-key"},
            json={"reason": "Scores look off"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["approval_id"] == 1

        # Verify the approval object was mutated
        assert approval.status == "rejected"
        assert approval.decision_reason == "Scores look off"
        assert approval.decided_at is not None

    def test_reject_not_found(self):
        """POST /admin/approvals/999/reject returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/999/reject",
            headers={"X-Admin-Key": "test-key"},
            json={},
        )

        assert response.status_code == 404

    def test_reject_non_staged_returns_409(self):
        """POST /admin/approvals/1/reject returns 409 if not staged."""
        approval = MagicMock(spec=PipelineApproval)
        approval.id = 1
        approval.status = "rejected"  # Already rejected

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = approval

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/1/reject",
            headers={"X-Admin-Key": "test-key"},
            json={},
        )

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Tests: Integration with real SQLite DB
# ---------------------------------------------------------------------------


class TestGovernanceIntegration:
    """Integration tests using a real async SQLite database."""

    @pytest.mark.asyncio
    async def test_approve_updates_db(self, db_session, session_factory):
        """Approve endpoint persists status change to the database."""
        approval = await _create_approval(db_session, gate_type="score_publish")
        approval_id = approval.id

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.governance._enqueue_publish_job",
                new_callable=AsyncMock,
            ),
        ):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            client = TestClient(app)
            response = client.post(
                f"/api/v1/admin/approvals/{approval_id}/approve",
                headers={"X-Admin-Key": "test-key"},
                json={"reason": "Ship it"},
            )

        assert response.status_code == 200

        # Verify in DB
        async with session_factory() as verify_session:
            result = await verify_session.execute(
                select(PipelineApproval).where(PipelineApproval.id == approval_id)
            )
            updated = result.scalar_one()
            assert updated.status == "approved"
            assert updated.decision_reason == "Ship it"

    @pytest.mark.asyncio
    async def test_reject_updates_db(self, db_session, session_factory):
        """Reject endpoint persists status change to the database."""
        approval = await _create_approval(db_session, gate_type="ml_model_deploy")
        approval_id = approval.id

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            client = TestClient(app)
            response = client.post(
                f"/api/v1/admin/approvals/{approval_id}/reject",
                headers={"X-Admin-Key": "test-key"},
                json={"reason": "Rank IC too low"},
            )

        assert response.status_code == 200

        # Verify in DB
        async with session_factory() as verify_session:
            result = await verify_session.execute(
                select(PipelineApproval).where(PipelineApproval.id == approval_id)
            )
            updated = result.scalar_one()
            assert updated.status == "rejected"
            assert updated.decision_reason == "Rank IC too low"

    @pytest.mark.asyncio
    async def test_list_all_approvals_from_db(self, db_session, session_factory):
        """List endpoint returns all approvals from the database."""
        await _create_approval(db_session, gate_type="score_publish", status="staged")
        await _create_approval(
            db_session, gate_type="ml_model_deploy", status="approved"
        )

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            client = TestClient(app)
            response = client.get(
                "/api/v1/admin/approvals",
                headers={"X-Admin-Key": "test-key"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["approvals"]) == 2
