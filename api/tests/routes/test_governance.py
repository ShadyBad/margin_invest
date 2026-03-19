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
from margin_api.db.models import GovernanceEvent, PipelineApproval, User, UserRole
from margin_api.db.session import get_db
from margin_api.deps import get_admin_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Shared admin user mock
# ---------------------------------------------------------------------------


def _make_admin_user() -> User:
    """Return a mock admin User for dependency override."""
    user = MagicMock(spec=User)
    user.id = 1
    user.role = UserRole.ADMIN
    return user


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
    db_override=None,
) -> tuple:
    """Create app and client with get_admin_user overridden and optional DB override."""
    get_settings.cache_clear()
    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-admin-key"}):
        app = create_app()

    async def override_admin():
        return _make_admin_user()

    app.dependency_overrides[get_admin_user] = override_admin
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
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get("/api/v1/admin/approvals")

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
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get("/api/v1/admin/approvals?status=staged")

        assert response.status_code == 200
        data = response.json()
        assert len(data["approvals"]) == 1
        assert data["approvals"][0]["status"] == "staged"

    def test_list_approvals_requires_auth(self):
        """GET /admin/approvals returns 401 without admin session cookie."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
        response = client.get("/api/v1/admin/approvals")
        assert response.status_code == 401


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
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get("/api/v1/admin/approvals/1")

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
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get("/api/v1/admin/approvals/999")

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
            db_override=_make_mock_db_override(mock_session),
        )

        with patch(
            "margin_api.routes.governance._enqueue_publish_job",
            new_callable=AsyncMock,
        ) as mock_enqueue:
            response = client.post(
                "/api/v1/admin/approvals/1/approve",
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
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/999/approve",
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
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/1/approve",
            json={},
        )

        assert response.status_code == 409

    def test_approve_requires_auth(self):
        """POST /admin/approvals/1/approve returns 401 without admin session cookie."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "correct-key"}):
            app = create_app()
            client = TestClient(app)
        response = client.post("/api/v1/admin/approvals/1/approve", json={})
        assert response.status_code == 401


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
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/1/reject",
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
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/999/reject",
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
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.post(
            "/api/v1/admin/approvals/1/reject",
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
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.post(
                f"/api/v1/admin/approvals/{approval_id}/approve",
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
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.post(
                f"/api/v1/admin/approvals/{approval_id}/reject",
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
        await _create_approval(db_session, gate_type="ml_model_deploy", status="approved")

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/approvals")

        assert response.status_code == 200
        data = response.json()
        assert len(data["approvals"]) == 2


# ---------------------------------------------------------------------------
# Helpers for dashboard/events tests
# ---------------------------------------------------------------------------


async def _create_event(
    session: AsyncSession,
    event_type: str = "score.staged",
    source: str = "stage_scores",
    detail: dict | None = None,
    created_at: datetime | None = None,
) -> GovernanceEvent:
    """Create a GovernanceEvent record in the database."""
    event = GovernanceEvent(
        event_type=event_type,
        source=source,
        detail=detail or {"info": "test"},
    )
    if created_at is not None:
        event.created_at = created_at
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


# ---------------------------------------------------------------------------
# Tests: Governance Dashboard
# ---------------------------------------------------------------------------


class TestGovernanceDashboard:
    """Integration tests for GET /governance/dashboard."""

    @pytest.mark.asyncio
    async def test_dashboard_pending_count(self, db_session, session_factory):
        """Dashboard returns correct pending_count for staged approvals."""
        await _create_approval(db_session, status="staged")
        await _create_approval(db_session, status="staged")
        await _create_approval(db_session, status="approved", decided_at=datetime.now(UTC))

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["pending_count"] == 2

    @pytest.mark.asyncio
    async def test_dashboard_avg_approval_latency(self, db_session, session_factory):
        """Dashboard returns avg_approval_latency_hours for approved approvals."""
        now = datetime.now(UTC)
        # Create an approved approval with known submitted_at and decided_at
        approval = PipelineApproval(
            gate_type="score_publish",
            status="approved",
            payload_ref={"run_id": 1},
            impact_summary={"tickers": 5},
            submitted_at=now - timedelta(hours=2),
            decided_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval)
        # Create a second approved with 4-hour latency
        approval2 = PipelineApproval(
            gate_type="score_publish",
            status="approved",
            payload_ref={"run_id": 2},
            impact_summary={"tickers": 3},
            submitted_at=now - timedelta(hours=4),
            decided_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval2)
        await db_session.commit()

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/dashboard")

        assert response.status_code == 200
        data = response.json()
        # Average of 2h and 4h = 3h
        assert data["avg_approval_latency_hours"] is not None
        assert abs(data["avg_approval_latency_hours"] - 3.0) < 0.5

    @pytest.mark.asyncio
    async def test_dashboard_no_approved_returns_none_latency(self, db_session, session_factory):
        """Dashboard returns None for avg_approval_latency_hours when no approved."""
        await _create_approval(db_session, status="staged")

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["avg_approval_latency_hours"] is None

    @pytest.mark.asyncio
    async def test_dashboard_rejection_rate(self, db_session, session_factory):
        """Dashboard returns rejection_rate = rejected / (approved + rejected)."""
        now = datetime.now(UTC)
        # 2 approved, 1 rejected => rate = 1/3 ≈ 0.3333
        for _ in range(2):
            a = PipelineApproval(
                gate_type="score_publish",
                status="approved",
                payload_ref={},
                impact_summary={},
                submitted_at=now - timedelta(hours=1),
                decided_at=now,
                expires_at=now + timedelta(hours=24),
            )
            db_session.add(a)
        r = PipelineApproval(
            gate_type="score_publish",
            status="rejected",
            payload_ref={},
            impact_summary={},
            submitted_at=now - timedelta(hours=1),
            decided_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(r)
        await db_session.commit()

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["rejection_rate"] is not None
        assert abs(data["rejection_rate"] - 0.3333) < 0.01

    @pytest.mark.asyncio
    async def test_dashboard_no_decisions_returns_none_rate(self, db_session, session_factory):
        """Dashboard returns None for rejection_rate when no decisions exist."""
        await _create_approval(db_session, status="staged")

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["rejection_rate"] is None

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, db_session, session_factory):
        """Dashboard endpoint requires admin session cookie."""
        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/dashboard")

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: Governance Events
# ---------------------------------------------------------------------------


class TestGovernanceEvents:
    """Integration tests for GET /governance/events."""

    @pytest.mark.asyncio
    async def test_events_returns_paginated(self, db_session, session_factory):
        """Events endpoint returns paginated event list with total count."""
        for i in range(5):
            await _create_event(
                db_session,
                event_type=f"score.staged.{i}",
                source="stage_scores",
            )

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/events?limit=3&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["events"]) == 3

    @pytest.mark.asyncio
    async def test_events_offset(self, db_session, session_factory):
        """Events endpoint respects offset for pagination."""
        for i in range(5):
            await _create_event(
                db_session,
                event_type=f"score.staged.{i}",
                source="stage_scores",
            )

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/events?limit=50&offset=3")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["events"]) == 2  # 5 total - 3 offset = 2 remaining

    @pytest.mark.asyncio
    async def test_events_filters_by_event_type_prefix(self, db_session, session_factory):
        """Events endpoint filters by event_type prefix match."""
        await _create_event(db_session, event_type="score.staged")
        await _create_event(db_session, event_type="score.published")
        await _create_event(db_session, event_type="ml.deployed")
        await _create_event(db_session, event_type="circuit.tripped")

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/events?event_type=score")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["events"]) == 2
        for event in data["events"]:
            assert event["event_type"].startswith("score")

    @pytest.mark.asyncio
    async def test_events_returns_event_fields(self, db_session, session_factory):
        """Events endpoint returns all expected fields for each event."""
        await _create_event(
            db_session,
            event_type="score.staged",
            source="stage_scores",
            detail={"run_id": 42},
        )

        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/events")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        event = data["events"][0]
        assert "id" in event
        assert event["event_type"] == "score.staged"
        assert event["source"] == "stage_scores"
        assert event["detail"] == {"run_id": 42}
        assert "created_at" in event

    @pytest.mark.asyncio
    async def test_events_requires_auth(self, db_session, session_factory):
        """Events endpoint requires admin session cookie."""
        get_settings.cache_clear()

        async def db_override():
            async with session_factory() as s:
                yield s

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_db] = db_override
            client = TestClient(app)
            response = client.get("/api/v1/admin/governance/events")

        assert response.status_code == 401
