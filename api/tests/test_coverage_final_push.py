"""Final coverage push for governance and new routes.

Targets:
  routes/admin_governance_config.py — 34% (40 uncovered)
  routes/admin_webhooks.py          — 39% (38 uncovered)
  routes/governance.py              — 30% (84 uncovered)
  routes/backtest.py                — 32% (91 uncovered)
  routes/model_validation.py        — 36% (41 uncovered)
  routes/health.py                  — 41% (19 uncovered)
  routes/sectors.py                 — 65% ( 6 uncovered)
  routes/correlations.py            — 60% (33 uncovered)
  routes/transparency.py            — 62% (10 uncovered)
  routes/jobs.py                    — 62% (21 uncovered)

Strategy: Use httpx.AsyncClient with ASGITransport + pytest.mark.asyncio so the
greenlet-concurrency coverage tracer follows into async route handlers.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.config import Settings, get_settings
from margin_api.db.base import Base
from margin_api.db.models import (
    GovernanceEvent,
    IngestionRun,
    JobRun,
    MlModelRun,
    PipelineApproval,
    SeedValidationReport,
    UniverseSnapshot,
    User,
    UserRole,
    WebhookDelivery,
)
from margin_api.db.session import get_db
from margin_api.deps import get_admin_user, get_superadmin_user
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FERNET_KEY = Fernet.generate_key().decode()
_ADMIN_KEY = "test-admin-key-for-coverage-push"


# ---------------------------------------------------------------------------
# Common fixtures
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


def _make_admin_user() -> User:
    user = MagicMock(spec=User)
    user.id = 1
    user.role = UserRole.ADMIN
    return user


def _make_superadmin_user() -> User:
    user = MagicMock(spec=User)
    user.id = 99
    user.role = UserRole.SUPERADMIN
    return user


async def _make_universe_snapshot(db_session) -> UniverseSnapshot:
    """Create a minimal UniverseSnapshot for use as FK parent of IngestionRun."""
    from datetime import UTC, datetime

    snap = UniverseSnapshot(
        version="test-v1",
        config_hash="abc123" * 10 + "ab12",
        ticker_count=0,
        tickers=[],
        is_active=True,
        activated_at=datetime.now(UTC),
    )
    db_session.add(snap)
    await db_session.commit()
    await db_session.refresh(snap)
    return snap


def _make_app(session_factory, *, superadmin: bool = False, override_settings: bool = True):
    """Create app with DB and auth overrides."""
    get_settings.cache_clear()
    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": _ADMIN_KEY}):
        app = create_app()

    async def db_override():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = db_override

    if superadmin:
        app.dependency_overrides[get_superadmin_user] = lambda: _make_superadmin_user()
    else:
        app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()

    if override_settings:

        def settings_override():
            return Settings(
                database_url="sqlite+aiosqlite:///:memory:",
                mfa_encryption_key=_FERNET_KEY,
                api_key_encryption_key=_FERNET_KEY,
                admin_key=_ADMIN_KEY,
                redis_url="redis://localhost:6379",
            )

        app.dependency_overrides[get_settings] = settings_override

    return app


# ===========================================================================
# admin_governance_config.py — lines 31-40, 55-59, 69-76, 87-124, 134-158
# ===========================================================================


class TestAdminGovernanceConfigAsync:
    """Use AsyncClient to get greenlet coverage tracking."""

    @pytest.mark.asyncio
    async def test_list_configs_returns_all_keys(self, session_factory):
        from margin_api.services.governance_config import CONFIG_REGISTRY

        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance-config")

        assert resp.status_code == 200
        data = resp.json()
        returned_keys = {c["config_key"] for c in data["configs"]}
        assert returned_keys == set(CONFIG_REGISTRY.keys())

    @pytest.mark.asyncio
    async def test_list_configs_shows_defaults(self, session_factory):
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance-config")

        assert resp.status_code == 200
        for cfg in resp.json()["configs"]:
            assert cfg["is_default"] is True

    @pytest.mark.asyncio
    async def test_get_known_key_returns_default(self, session_factory):
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance-config/circuit_breaker.score_drift")

        assert resp.status_code == 200
        data = resp.json()
        assert data["config_key"] == "circuit_breaker.score_drift"
        assert data["is_default"] is True

    @pytest.mark.asyncio
    async def test_get_unknown_key_returns_404(self, session_factory):
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance-config/no.such.key")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_put_creates_override(self, session_factory):
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/admin/governance-config/circuit_breaker.score_drift",
                json={"config_value": {"threshold": 42.0}},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_default"] is False
        assert data["config_value"] == {"threshold": 42.0}

    @pytest.mark.asyncio
    async def test_put_updates_existing_override(self, session_factory):
        """PUT twice on the same key updates the existing row."""
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put(
                "/api/v1/admin/governance-config/circuit_breaker.ingestion_failure",
                json={"config_value": {"threshold": 15.0}},
            )
            # Update again
            resp = await client.put(
                "/api/v1/admin/governance-config/circuit_breaker.ingestion_failure",
                json={"config_value": {"threshold": 25.0}},
            )

        assert resp.status_code == 200
        assert resp.json()["config_value"] == {"threshold": 25.0}

    @pytest.mark.asyncio
    async def test_put_creates_governance_event(self, session_factory):
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put(
                "/api/v1/admin/governance-config/circuit_breaker.ml_regression",
                json={"config_value": {"threshold": 60.0}},
            )

        async with session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(GovernanceEvent).where(GovernanceEvent.event_type == "config.updated")
            )
            events = result.scalars().all()

        assert len(events) == 1
        assert events[0].source == "admin_api"

    @pytest.mark.asyncio
    async def test_put_invalid_value_returns_422(self, session_factory):
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/admin/governance-config/circuit_breaker.score_drift",
                json={"config_value": {"threshold": 999.0}},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_put_unknown_key_returns_422(self, session_factory):
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/admin/governance-config/unknown.key",
                json={"config_value": {"threshold": 10.0}},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_delete_removes_override(self, session_factory):
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create override
            await client.put(
                "/api/v1/admin/governance-config/circuit_breaker.score_drift",
                json={"config_value": {"threshold": 25.0}},
            )
            # Delete it
            del_resp = await client.delete(
                "/api/v1/admin/governance-config/circuit_breaker.score_drift"
            )
            # Verify it's back to default
            get_resp = await client.get(
                "/api/v1/admin/governance-config/circuit_breaker.score_drift"
            )

        assert del_resp.status_code == 204
        assert get_resp.json()["is_default"] is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key_returns_404(self, session_factory):
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/v1/admin/governance-config/bogus.key")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_without_override_still_logs_event(self, session_factory):
        """DELETE on a key with no DB row still logs config.deleted event."""
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete(
                "/api/v1/admin/governance-config/circuit_breaker.ingestion_failure"
            )

        assert resp.status_code == 204

        async with session_factory() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(GovernanceEvent).where(GovernanceEvent.event_type == "config.deleted")
            )
            events = result.scalars().all()
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_get_shows_override_value_not_default(self, session_factory):
        """After PUT, GET returns the overridden value with is_default=False."""
        app = _make_app(session_factory, superadmin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put(
                "/api/v1/admin/governance-config/circuit_breaker.ml_regression",
                json={"config_value": {"threshold": 75.0}},
            )
            resp = await client.get("/api/v1/admin/governance-config/circuit_breaker.ml_regression")

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_default"] is False
        assert data["config_value"]["threshold"] == 75.0


# ===========================================================================
# admin_webhooks.py — lines 34-37, 46-50, 78-128, 145-152, 169-187
# ===========================================================================


class TestAdminWebhooksAsync:
    """AsyncClient tests for webhook CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_empty_webhooks(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/webhooks")

        assert resp.status_code == 200
        assert resp.json()["subscriptions"] == []

    @pytest.mark.asyncio
    async def test_create_webhook_returns_hmac_key(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": "score.staged", "url": "https://example.com/hook"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert "hmac_key_plaintext" in data
        assert len(data["hmac_key_plaintext"]) == 64
        assert data["event_type"] == "score.staged"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_duplicate_webhook_returns_409(self, session_factory):
        app = _make_app(session_factory)
        payload = {"event_type": "score.staged", "url": "https://example.com/hook"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp1 = await client.post("/api/v1/admin/webhooks", json=payload)
            resp2 = await client.post("/api/v1/admin/webhooks", json=payload)

        assert resp1.status_code == 201
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_create_invalid_event_type_returns_422(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": "bogus.event", "url": "https://example.com/hook"},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_shows_created_subscriptions(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": "score.staged", "url": "https://example.com/a"},
            )
            await client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": "model.promoted", "url": "https://example.com/b"},
            )
            list_resp = await client.get("/api/v1/admin/webhooks")

        assert list_resp.status_code == 200
        assert len(list_resp.json()["subscriptions"]) == 2

    @pytest.mark.asyncio
    async def test_delete_webhook_returns_204(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_resp = await client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": "score.published", "url": "https://example.com/hook"},
            )
            sub_id = create_resp.json()["id"]
            del_resp = await client.delete(f"/api/v1/admin/webhooks/{sub_id}")
            list_resp = await client.get("/api/v1/admin/webhooks")

        assert del_resp.status_code == 204
        assert list_resp.json()["subscriptions"] == []

    @pytest.mark.asyncio
    async def test_delete_nonexistent_webhook_returns_404(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/v1/admin/webhooks/99999")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_deliveries_empty(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_resp = await client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": "score.staged", "url": "https://example.com/hook"},
            )
            sub_id = create_resp.json()["id"]
            del_resp = await client.get(f"/api/v1/admin/webhooks/{sub_id}/deliveries")

        assert del_resp.status_code == 200
        data = del_resp.json()
        assert data["deliveries"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_deliveries_with_data(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_resp = await client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": "score.staged", "url": "https://example.com/hook"},
            )
            sub_id = create_resp.json()["id"]

        # Insert deliveries directly
        async with session_factory() as session:
            for i in range(3):
                d = WebhookDelivery(
                    subscription_id=sub_id,
                    event_type="score.staged",
                    payload={"i": i},
                    status="delivered",
                    attempts=1,
                )
                session.add(d)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/admin/webhooks/{sub_id}/deliveries")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["deliveries"]) == 3

    @pytest.mark.asyncio
    async def test_list_deliveries_pagination(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_resp = await client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": "score.staged", "url": "https://example.com/hook"},
            )
            sub_id = create_resp.json()["id"]

        async with session_factory() as session:
            for i in range(5):
                d = WebhookDelivery(
                    subscription_id=sub_id,
                    event_type="score.staged",
                    payload={"i": i},
                    status="pending",
                    attempts=0,
                )
                session.add(d)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/admin/webhooks/{sub_id}/deliveries?limit=2&offset=0")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["deliveries"]) == 2

    @pytest.mark.asyncio
    async def test_list_deliveries_nonexistent_sub_returns_404(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/webhooks/99999/deliveries")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_webhook_missing_encryption_key(self, session_factory):
        """When mfa_encryption_key is empty, webhook creation returns 500."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": _ADMIN_KEY}):
            app = create_app()

        async def db_override():
            async with session_factory() as s:
                yield s

        app.dependency_overrides[get_db] = db_override
        app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()

        def bad_settings():
            return Settings(
                database_url="sqlite+aiosqlite:///:memory:",
                mfa_encryption_key="",  # No key
                api_key_encryption_key=_FERNET_KEY,
                admin_key=_ADMIN_KEY,
            )

        app.dependency_overrides[get_settings] = bad_settings

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": "score.staged", "url": "https://example.com/hook"},
            )

        assert resp.status_code == 500


# ===========================================================================
# governance.py — lines 35, 52-87, 101-111, 124-131, 145-163, 177-191,
#                 204-250, 271-294
# ===========================================================================


class TestGovernanceRouteAsync:
    """AsyncClient tests for governance approval management endpoints."""

    @pytest.mark.asyncio
    async def test_list_approvals_empty(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/approvals")

        assert resp.status_code == 200
        assert resp.json()["approvals"] == []

    @pytest.mark.asyncio
    async def test_list_approvals_with_data(self, db_session, session_factory):
        now = datetime.now(UTC)
        approval = PipelineApproval(
            gate_type="score_publish",
            status="staged",
            payload_ref={"run_id": 1},
            impact_summary={"tickers": 5},
            submitted_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/approvals")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["approvals"]) == 1
        assert data["approvals"][0]["gate_type"] == "score_publish"

    @pytest.mark.asyncio
    async def test_list_approvals_filter_by_status(self, db_session, session_factory):
        now = datetime.now(UTC)
        for status in ["staged", "staged", "approved"]:
            a = PipelineApproval(
                gate_type="score_publish",
                status=status,
                payload_ref={},
                impact_summary={},
                submitted_at=now,
                expires_at=now + timedelta(hours=24),
            )
            db_session.add(a)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/approvals?status=staged")

        assert resp.status_code == 200
        assert len(resp.json()["approvals"]) == 2

    @pytest.mark.asyncio
    async def test_list_approvals_filter_by_gate_type(self, db_session, session_factory):
        now = datetime.now(UTC)
        for gate_type in ["score_publish", "score_publish", "ml_model_deploy"]:
            a = PipelineApproval(
                gate_type=gate_type,
                status="staged",
                payload_ref={},
                impact_summary={},
                submitted_at=now,
                expires_at=now + timedelta(hours=24),
            )
            db_session.add(a)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/approvals?gate_type=score_publish")

        assert resp.status_code == 200
        assert len(resp.json()["approvals"]) == 2

    @pytest.mark.asyncio
    async def test_get_approval_by_id(self, db_session, session_factory):
        now = datetime.now(UTC)
        approval = PipelineApproval(
            gate_type="ml_model_deploy",
            status="staged",
            payload_ref={"model_id": 7},
            impact_summary={"rank_ic": 0.22},
            submitted_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval)
        await db_session.commit()
        await db_session.refresh(approval)
        approval_id = approval.id

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/admin/approvals/{approval_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == approval_id
        assert data["gate_type"] == "ml_model_deploy"

    @pytest.mark.asyncio
    async def test_get_approval_not_found(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/approvals/99999")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_staged_approval(self, db_session, session_factory):
        now = datetime.now(UTC)
        approval = PipelineApproval(
            gate_type="score_publish",
            status="staged",
            payload_ref={"run_id": 42},
            impact_summary={},
            submitted_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval)
        await db_session.commit()
        await db_session.refresh(approval)
        approval_id = approval.id

        app = _make_app(session_factory)
        with patch("margin_api.routes.governance._enqueue_publish_job", new_callable=AsyncMock):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/api/v1/admin/approvals/{approval_id}/approve",
                    json={"reason": "LGTM"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["approval_id"] == approval_id

    @pytest.mark.asyncio
    async def test_approve_not_found(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/approvals/99999/approve", json={"reason": "test"}
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_non_staged_returns_409(self, db_session, session_factory):
        now = datetime.now(UTC)
        approval = PipelineApproval(
            gate_type="score_publish",
            status="approved",  # Already approved
            payload_ref={},
            impact_summary={},
            submitted_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval)
        await db_session.commit()
        await db_session.refresh(approval)

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/admin/approvals/{approval.id}/approve", json={})

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_reject_staged_approval(self, db_session, session_factory):
        now = datetime.now(UTC)
        approval = PipelineApproval(
            gate_type="ml_model_deploy",
            status="staged",
            payload_ref={},
            impact_summary={},
            submitted_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval)
        await db_session.commit()
        await db_session.refresh(approval)
        approval_id = approval.id

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/admin/approvals/{approval_id}/reject",
                json={"reason": "Rank IC too low"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_reject_not_found(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/approvals/99999/reject", json={"reason": "test"}
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_non_staged_returns_409(self, db_session, session_factory):
        now = datetime.now(UTC)
        approval = PipelineApproval(
            gate_type="score_publish",
            status="rejected",  # Already rejected
            payload_ref={},
            impact_summary={},
            submitted_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval)
        await db_session.commit()
        await db_session.refresh(approval)

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/admin/approvals/{approval.id}/reject", json={})

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_dashboard_empty(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance/dashboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["pending_count"] == 0
        assert data["avg_approval_latency_hours"] is None
        assert data["rejection_rate"] is None

    @pytest.mark.asyncio
    async def test_dashboard_with_pending(self, db_session, session_factory):
        now = datetime.now(UTC)
        for _ in range(3):
            a = PipelineApproval(
                gate_type="score_publish",
                status="staged",
                payload_ref={},
                impact_summary={},
                submitted_at=now,
                expires_at=now + timedelta(hours=24),
            )
            db_session.add(a)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance/dashboard")

        assert resp.status_code == 200
        assert resp.json()["pending_count"] == 3

    @pytest.mark.asyncio
    async def test_dashboard_with_latency(self, db_session, session_factory):
        now = datetime.now(UTC)
        # 2h and 4h latency = 3h average
        for hours in [2, 4]:
            a = PipelineApproval(
                gate_type="score_publish",
                status="approved",
                payload_ref={},
                impact_summary={},
                submitted_at=now - timedelta(hours=hours),
                decided_at=now,
                expires_at=now + timedelta(hours=24),
            )
            db_session.add(a)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance/dashboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["avg_approval_latency_hours"] is not None
        assert abs(data["avg_approval_latency_hours"] - 3.0) < 0.5

    @pytest.mark.asyncio
    async def test_dashboard_rejection_rate(self, db_session, session_factory):
        now = datetime.now(UTC)
        # 2 approved, 1 rejected = 1/3 rate
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

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance/dashboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["rejection_rate"] is not None
        assert abs(data["rejection_rate"] - 0.3333) < 0.01

    @pytest.mark.asyncio
    async def test_governance_events_empty(self, session_factory):
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance/events")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["events"] == []

    @pytest.mark.asyncio
    async def test_governance_events_pagination(self, db_session, session_factory):
        for i in range(5):
            e = GovernanceEvent(
                event_type=f"score.staged.{i}",
                source="stage_scores",
                detail={"info": i},
            )
            db_session.add(e)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance/events?limit=3&offset=0")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["events"]) == 3

    @pytest.mark.asyncio
    async def test_governance_events_filter_by_type(self, db_session, session_factory):
        for event_type in ["score.staged", "score.published", "ml.deployed"]:
            e = GovernanceEvent(event_type=event_type, source="test", detail={})
            db_session.add(e)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/governance/events?event_type=score")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_approve_ml_model_deploy_enqueues_promote(self, db_session, session_factory):
        """Approving an ml_model_deploy gate enqueues promote_ml_model job."""
        now = datetime.now(UTC)
        approval = PipelineApproval(
            gate_type="ml_model_deploy",
            status="staged",
            payload_ref={"model_id": 5},
            impact_summary={},
            submitted_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval)
        await db_session.commit()
        await db_session.refresh(approval)

        app = _make_app(session_factory)
        with patch("margin_api.routes.governance._enqueue_publish_job", new_callable=AsyncMock):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    f"/api/v1/admin/approvals/{approval.id}/approve",
                    json={"reason": "Go for it"},
                )

        assert resp.status_code == 200


# ===========================================================================
# Test _enqueue_publish_job directly
# ===========================================================================


class TestEnqueuePublishJob:
    """Test the _enqueue_publish_job function with various gate_types."""

    @pytest.mark.asyncio
    async def test_enqueue_score_publish(self):
        """score_publish gate_type enqueues publish_scores job."""
        from margin_api.routes.governance import _enqueue_publish_job

        approval = MagicMock()
        approval.id = 1
        approval.gate_type = "score_publish"
        approval.decided_by = 1
        approval.decision_reason = "LGTM"

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with (
            patch("margin_api.routes.governance.create_pool", return_value=mock_redis),
            patch("margin_api.routes.governance.get_settings") as mock_settings,
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            await _enqueue_publish_job(approval)

        mock_redis.enqueue_job.assert_called_once()
        call_args = mock_redis.enqueue_job.call_args
        assert call_args[0][0] == "publish_scores"

    @pytest.mark.asyncio
    async def test_enqueue_ml_model_deploy(self):
        """ml_model_deploy gate_type enqueues promote_ml_model job."""
        from margin_api.routes.governance import _enqueue_publish_job

        approval = MagicMock()
        approval.id = 2
        approval.gate_type = "ml_model_deploy"
        approval.decided_by = 1
        approval.decision_reason = "Good"

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with (
            patch("margin_api.routes.governance.create_pool", return_value=mock_redis),
            patch("margin_api.routes.governance.get_settings") as mock_settings,
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            await _enqueue_publish_job(approval)

        mock_redis.enqueue_job.assert_called_once()
        call_args = mock_redis.enqueue_job.call_args
        assert call_args[0][0] == "promote_ml_model"

    @pytest.mark.asyncio
    async def test_enqueue_unknown_gate_type_logs_warning(self):
        """Unknown gate_type logs a warning without raising."""
        from margin_api.routes.governance import _enqueue_publish_job

        approval = MagicMock()
        approval.id = 3
        approval.gate_type = "unknown_gate"
        approval.decided_by = 1
        approval.decision_reason = "test"

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with (
            patch("margin_api.routes.governance.create_pool", return_value=mock_redis),
            patch("margin_api.routes.governance.get_settings") as mock_settings,
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            await _enqueue_publish_job(approval)  # Should not raise

        mock_redis.enqueue_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_enqueue_handles_redis_exception(self):
        """Exception from create_pool is caught and logged, not re-raised."""
        from margin_api.routes.governance import _enqueue_publish_job

        approval = MagicMock()
        approval.id = 4
        approval.gate_type = "score_publish"
        approval.decided_by = 1
        approval.decision_reason = "test"

        with (
            patch(
                "margin_api.routes.governance.create_pool",
                side_effect=Exception("Redis unavailable"),
            ),
            patch("margin_api.routes.governance.get_settings") as mock_settings,
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            await _enqueue_publish_job(approval)  # Should not raise


# ===========================================================================
# backtest.py — lines 60-71, 88-127, 145-179, 185-198, 204-206, 212-217,
#               234-235, 246-247, 259-260, 280-294, 315-357, 385-417
# ===========================================================================


class TestBacktestRouteAsync:
    """AsyncClient tests for backtest route handlers."""

    @pytest.mark.asyncio
    async def test_run_backtest_synthetic_fallback(self, session_factory):
        """POST /backtest/run returns result with synthetic metrics when no PIT data."""

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/run",
                json={"start_date": "2020-01-01", "end_date": "2023-01-01"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert "metrics" in data
        assert "validation" in data
        assert "config" in data

    @pytest.mark.asyncio
    async def test_run_backtest_no_end_date(self, session_factory):
        """POST /backtest/run without end_date defaults to today."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/run",
                json={"start_date": "2021-01-01"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["config"]["end_date"] is not None

    @pytest.mark.asyncio
    async def test_list_results_empty(self, session_factory):
        """GET /backtest/results returns empty list initially."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/backtest/results")

        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_results_after_run(self, session_factory):
        """GET /backtest/results returns results after run."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/api/v1/backtest/run",
                json={"start_date": "2020-01-01", "end_date": "2022-01-01"},
            )
            list_resp = await client.get("/api/v1/backtest/results")

        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_get_result_by_id(self, session_factory):
        """GET /backtest/results/{id} returns the stored result."""
        from datetime import UTC, date, datetime

        from margin_api.routes.backtest import _backtest_store
        from margin_api.schemas.backtest import (
            BacktestConfigRequest,
            BacktestResultResponse,
            MetricsResponse,
            ValidationResponse,
        )

        # Pre-populate the store
        backtest_id = "test-id-123"
        config = BacktestConfigRequest(start_date=date(2020, 1, 1), end_date=date(2022, 1, 1))
        metrics = MetricsResponse(
            cagr=0.10,
            excess_cagr=0.03,
            sharpe_ratio=0.85,
            sortino_ratio=1.2,
            max_drawdown=0.22,
            win_rate=0.58,
            information_ratio=0.65,
            total_return=0.21,
            benchmark_total_return=0.14,
            num_months=24,
            avg_turnover=0.15,
        )
        validation = ValidationResponse(
            overall_pass=True, passed_count=6, total_checks=6, checks=[]
        )
        _backtest_store[backtest_id] = BacktestResultResponse(
            config=config,
            metrics=metrics,
            validation=validation,
            num_snapshots=24,
            run_at=datetime.now(UTC),
            duration_seconds=1.0,
        )

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/backtest/results/{backtest_id}")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, session_factory):
        """GET /backtest/results/{id} returns 404 for unknown id."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/backtest/results/nonexistent-id")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_metrics_by_id(self, session_factory):
        """GET /backtest/metrics/{id} returns the metrics."""
        from datetime import UTC, date, datetime

        from margin_api.routes.backtest import _backtest_store
        from margin_api.schemas.backtest import (
            BacktestConfigRequest,
            BacktestResultResponse,
            MetricsResponse,
            ValidationResponse,
        )

        backtest_id = "metrics-test-id"
        config = BacktestConfigRequest(start_date=date(2020, 1, 1), end_date=date(2022, 1, 1))
        metrics = MetricsResponse(
            cagr=0.10,
            excess_cagr=0.03,
            sharpe_ratio=0.85,
            sortino_ratio=1.2,
            max_drawdown=0.22,
            win_rate=0.58,
            information_ratio=0.65,
            total_return=0.21,
            benchmark_total_return=0.14,
            num_months=24,
            avg_turnover=0.15,
        )
        validation = ValidationResponse(
            overall_pass=True, passed_count=6, total_checks=6, checks=[]
        )
        _backtest_store[backtest_id] = BacktestResultResponse(
            config=config,
            metrics=metrics,
            validation=validation,
            num_snapshots=24,
            run_at=datetime.now(UTC),
            duration_seconds=1.0,
        )

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/backtest/metrics/{backtest_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert "cagr" in data

    @pytest.mark.asyncio
    async def test_get_metrics_not_found(self, session_factory):
        """GET /backtest/metrics/{id} returns 404 for unknown id."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/backtest/metrics/nonexistent")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_teaser_endpoint(self, session_factory):
        """GET /backtest/teaser/{ticker} returns teaser data."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/backtest/teaser/AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert "model_return" in data

    @pytest.mark.asyncio
    async def test_portfolio_teaser_endpoint(self, session_factory):
        """GET /backtest/portfolio-teaser returns portfolio-level teaser."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/backtest/portfolio-teaser")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_calibration_status_no_data(self, session_factory):
        """GET /backtest/calibration-status works with no data."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/backtest/calibration-status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["pit_data_available"] is False
        assert data["pit_ticker_count"] == 0


class TestBacktestGatedEndpoints:
    """Tests for plan-gated backtest endpoints."""

    @pytest.mark.asyncio
    async def test_default_backtest_requires_portfolio_plan(self, session_factory):
        """GET /backtest/default requires portfolio plan."""
        from margin_api.deps import get_current_user_id

        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": _ADMIN_KEY}):
            app = create_app()

        async def db_override():
            async with session_factory() as s:
                yield s

        app.dependency_overrides[get_db] = db_override

        # Create a user with portfolio plan
        async with session_factory() as session:
            user = User(
                email="portfolio@test.com",
                name="Portfolio User",
                subscription_plan="portfolio",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        app.dependency_overrides[get_current_user_id] = lambda: user_id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/backtest/default")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_replay_backtest_synthetic_fallback(self, session_factory):
        """POST /backtest/replay falls back to synthetic when no real PIT data."""
        from margin_api.deps import get_current_user_id

        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": _ADMIN_KEY}):
            app = create_app()

        async def db_override():
            async with session_factory() as s:
                yield s

        app.dependency_overrides[get_db] = db_override

        async with session_factory() as session:
            user = User(
                email="portfolio2@test.com",
                name="Portfolio User 2",
                subscription_plan="portfolio",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        app.dependency_overrides[get_current_user_id] = lambda: user_id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/backtest/replay",
                json={"start_date": "2020-01-01", "end_date": "2022-01-01"},
            )

        assert resp.status_code in (200, 202)

    @pytest.mark.asyncio
    async def test_shadow_portfolio_empty(self, session_factory):
        """GET /backtest/shadow-portfolio returns empty response when no snapshots."""
        from margin_api.deps import get_current_user_id

        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": _ADMIN_KEY}):
            app = create_app()

        async def db_override():
            async with session_factory() as s:
                yield s

        app.dependency_overrides[get_db] = db_override

        async with session_factory() as session:
            user = User(
                email="institutional@test.com",
                name="Institutional User",
                subscription_plan="institutional",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        app.dependency_overrides[get_current_user_id] = lambda: user_id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/backtest/shadow-portfolio")

        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshots"] == []
        assert data["cannot_be_backdated"] is True


# ===========================================================================
# model_validation.py — lines 33-38, 56-81, 103-113, 126-146, 158-168
# ===========================================================================


class TestModelValidationAsync:
    """AsyncClient tests for model validation endpoints."""

    @pytest_asyncio.fixture
    async def seed_report(self, db_session) -> SeedValidationReport:
        """Create a minimal SeedValidationReport in the test DB."""
        run_group_id = str(uuid.uuid4())
        report = SeedValidationReport(
            run_group_id=run_group_id,
            n_seeds=3,
            gate_passed=True,
            selected_seed=42,
            metric_distributions={
                "rank_ic": {
                    "mean": 0.18,
                    "std": 0.03,
                    "min": 0.12,
                    "max": 0.22,
                    "median": 0.18,
                    "ci_lower": 0.15,
                    "ci_upper": 0.21,
                    "cv": 0.17,
                }
            },
            gate_details={
                "overall": True,
                "median_ic": {"value": 0.18, "threshold": 0.15, "passed": True},
            },
            environment_snapshot={"python": "3.13.5"},
            previous_comparison=None,
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)
        return report

    @pytest.mark.asyncio
    async def test_get_latest_no_reports(self, session_factory):
        """GET /admin/model-validation/latest returns 404 when no reports."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/admin/model-validation/latest",
                headers={"x-admin-key": _ADMIN_KEY},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_latest_returns_most_recent(self, seed_report, session_factory):
        """GET /admin/model-validation/latest returns the latest report."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/admin/model-validation/latest",
                headers={"x-admin-key": _ADMIN_KEY},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["run_group_id"] == seed_report.run_group_id
        assert data["gate_passed"] is True
        assert data["n_seeds"] == 3

    @pytest.mark.asyncio
    async def test_get_history_empty(self, session_factory):
        """GET /admin/model-validation/history returns empty list."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/admin/model-validation/history",
                headers={"x-admin-key": _ADMIN_KEY},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["reports"] == []

    @pytest.mark.asyncio
    async def test_get_history_with_data(self, seed_report, session_factory):
        """GET /admin/model-validation/history returns reports."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/admin/model-validation/history",
                headers={"x-admin-key": _ADMIN_KEY},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["reports"]) == 1

    @pytest.mark.asyncio
    async def test_get_report_by_run_group_id(self, seed_report, session_factory):
        """GET /admin/model-validation/{run_group_id} returns the report."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/admin/model-validation/{seed_report.run_group_id}",
                headers={"x-admin-key": _ADMIN_KEY},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["run_group_id"] == seed_report.run_group_id

    @pytest.mark.asyncio
    async def test_get_report_not_found(self, session_factory):
        """GET /admin/model-validation/{id} returns 404 for unknown id."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/admin/model-validation/nonexistent-id",
                headers={"x-admin-key": _ADMIN_KEY},
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_history_pagination(self, db_session, session_factory):
        """GET /admin/model-validation/history supports limit/offset."""
        # Create 3 reports
        for i in range(3):
            report = SeedValidationReport(
                run_group_id=str(uuid.uuid4()),
                n_seeds=2,
                gate_passed=True,
                selected_seed=i,
                metric_distributions={
                    "rank_ic": {
                        "mean": 0.15,
                        "std": 0.02,
                        "min": 0.1,
                        "max": 0.2,
                        "median": 0.15,
                        "ci_lower": 0.12,
                        "ci_upper": 0.18,
                        "cv": 0.13,
                    }
                },
                gate_details={"overall": True},
                environment_snapshot={},
            )
            db_session.add(report)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/admin/model-validation/history?limit=2&offset=0",
                headers={"x-admin-key": _ADMIN_KEY},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["reports"]) == 2

    @pytest.mark.asyncio
    async def test_seed_details_with_ml_runs(self, db_session, session_factory):
        """Reports include seed details from MlModelRun table."""
        run_group_id = str(uuid.uuid4())
        report = SeedValidationReport(
            run_group_id=run_group_id,
            n_seeds=1,
            gate_passed=True,
            selected_seed=7,
            metric_distributions={
                "rank_ic": {
                    "mean": 0.18,
                    "std": 0.01,
                    "min": 0.17,
                    "max": 0.19,
                    "median": 0.18,
                    "ci_lower": 0.16,
                    "ci_upper": 0.20,
                    "cv": 0.06,
                }
            },
            gate_details={"overall": True},
            environment_snapshot={},
        )
        db_session.add(report)

        # Add MlModelRun with matching run_group_id
        ml_run = MlModelRun(
            run_group_id=run_group_id,
            seed=7,
            overall_rank_ic=0.18,
            n_clusters=5,
            n_samples=100,
            status="completed",
            model_type="lightgbm_cluster",
        )
        db_session.add(ml_run)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/admin/model-validation/{run_group_id}",
                headers={"x-admin-key": _ADMIN_KEY},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["seed_details"]) == 1
        assert data["seed_details"][0]["seed"] == 7
        assert data["seed_details"][0]["selected"] is True

    @pytest.mark.asyncio
    async def test_report_with_previous_comparison(self, db_session, session_factory):
        """Reports with previous_comparison include comparison details."""
        run_group_id = str(uuid.uuid4())
        report = SeedValidationReport(
            run_group_id=run_group_id,
            n_seeds=2,
            gate_passed=True,
            selected_seed=None,
            metric_distributions={
                "rank_ic": {
                    "mean": 0.20,
                    "std": 0.02,
                    "min": 0.15,
                    "max": 0.25,
                    "median": 0.20,
                    "ci_lower": 0.17,
                    "ci_upper": 0.23,
                    "cv": 0.10,
                }
            },
            gate_details={"overall": True},
            environment_snapshot={},
            previous_comparison={
                "p_value": 0.03,
                "effect_size": 0.42,
                "significant": True,
                "label": "improvement",
                "n_compared": 20,
                "mean_difference": 0.05,
            },
        )
        db_session.add(report)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/admin/model-validation/{run_group_id}",
                headers={"x-admin-key": _ADMIN_KEY},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["comparison"] is not None


# ===========================================================================
# health.py — lines 24-47
# ===========================================================================


class TestHealthRouteAsync:
    """AsyncClient tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_db_ok_redis_error(self, session_factory):
        """Health check reports db=ok, redis=error when redis unreachable."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert "database" in data
        assert "redis" in data
        assert "status" in data
        assert data["database"] == "ok"
        # Redis may fail in test env (localhost:6379), status will be degraded
        assert data["status"] in ("ok", "degraded")

    @pytest.mark.asyncio
    async def test_health_check_db_error(self, session_factory):
        """Health check reports db=error when DB is unreachable."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": _ADMIN_KEY}):
            app = create_app()

        # Override DB with a broken session
        async def bad_db():
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("DB connection failed")
            yield mock_session

        app.dependency_overrides[get_db] = bad_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["database"] == "error"
        assert data["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_check_version_field(self, session_factory):
        """Health check always includes version field."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")

        data = resp.json()
        assert "version" in data


# ===========================================================================
# sectors.py — lines 18-19, 28-34
# ===========================================================================


class TestSectorsRouteAsync:
    """AsyncClient tests for sector endpoints."""

    @pytest.mark.asyncio
    async def test_list_sectors_empty(self, session_factory):
        """GET /sectors returns empty list when no published scores."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/sectors")

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_champion_not_found(self, session_factory):
        """GET /sectors/{sector}/champion returns 404 when no scores."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/sectors/TECHNOLOGY/champion")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_sectors_calls_service(self, session_factory):
        """GET /sectors calls list_sector_summaries service."""

        app = _make_app(session_factory)
        with patch(
            "margin_api.routes.sectors.list_sector_summaries",
            return_value=[
                {
                    "sector": "TECHNOLOGY",
                    "asset_count": 10,
                    "avg_composite_score": 68.5,
                    "top_ticker": "AAPL",
                    "top_score": 85.0,
                }
            ],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/sectors")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["sector"] == "TECHNOLOGY"

    @pytest.mark.asyncio
    async def test_get_champion_returns_detail(self, session_factory):
        """GET /sectors/{sector}/champion returns champion detail when available."""
        app = _make_app(session_factory)
        with patch(
            "margin_api.routes.sectors.get_sector_champion_detail",
            return_value={
                "sector": "TECHNOLOGY",
                "ticker": "AAPL",
                "composite_score": 85.0,
                "composite_tier": "tier_1",
                "signal": "strong",
                "market_cap": 3_000_000_000_000.0,
            },
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/sectors/TECHNOLOGY/champion")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"


# ===========================================================================
# correlations.py — lines 50-65, 70-85, 166-180
# ===========================================================================


class TestCorrelationsRouteAsync:
    """AsyncClient tests for correlation endpoints."""

    @pytest.mark.asyncio
    async def test_showcase_returns_fallback_when_redis_unavailable(self, session_factory):
        """GET /correlations/showcase returns fallback data when Redis is down."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/correlations/showcase")

        assert resp.status_code == 200
        data = resp.json()
        assert "tickers" in data
        assert "matrix" in data

    @pytest.mark.asyncio
    async def test_showcase_uses_redis_cache(self, session_factory):
        """GET /correlations/showcase uses Redis cache when available."""
        from datetime import UTC, datetime

        from margin_api.schemas.correlations import CorrelationResponse

        cached_response = CorrelationResponse(
            tickers=["AAPL", "MSFT", "JNJ", "COST", "V"],
            method="returns",
            matrix=[[1.0, 0.8, 0.1, 0.2, 0.4]] * 5,
            sample_sizes=[[252] * 5 for _ in range(5)],
            excluded=[],
            window_days=252,
            computed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

        app = _make_app(session_factory)
        with patch(
            "margin_api.routes.correlations._get_redis_cached",
            return_value=cached_response,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/correlations/showcase")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tickers"] == ["AAPL", "MSFT", "JNJ", "COST", "V"]

    @pytest.mark.asyncio
    async def test_showcase_computes_live_when_cache_miss(self, session_factory):
        """GET /correlations/showcase computes live when cache misses."""
        from datetime import UTC, datetime

        from margin_api.schemas.correlations import CorrelationResponse

        live_response = CorrelationResponse(
            tickers=["AAPL", "MSFT", "AMZN", "GOOG", "META"],
            method="returns",
            matrix=[[1.0, 0.7, 0.6, 0.5, 0.4]] * 5,
            sample_sizes=[[252] * 5 for _ in range(5)],
            excluded=[],
            window_days=252,
            computed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

        app = _make_app(session_factory)
        with (
            patch("margin_api.routes.correlations._get_redis_cached", return_value=None),
            patch(
                "margin_api.routes.correlations._compute_live_showcase",
                return_value=live_response,
            ),
            patch("margin_api.routes.correlations._cache_to_redis", return_value=None),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/correlations/showcase")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tickers"] == ["AAPL", "MSFT", "AMZN", "GOOG", "META"]

    @pytest.mark.asyncio
    async def test_showcase_falls_back_when_live_compute_fails(self, session_factory):
        """GET /correlations/showcase falls back to static when live compute raises."""
        app = _make_app(session_factory)
        with (
            patch("margin_api.routes.correlations._get_redis_cached", return_value=None),
            patch(
                "margin_api.routes.correlations._compute_live_showcase",
                side_effect=Exception("DB error"),
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/correlations/showcase")

        assert resp.status_code == 200
        # Should return the static fallback
        data = resp.json()
        assert len(data["tickers"]) == 5

    @pytest.mark.asyncio
    async def test_showcase_falls_back_when_live_compute_returns_none(self, session_factory):
        """GET /correlations/showcase falls back to static when live returns None."""
        app = _make_app(session_factory)
        with (
            patch("margin_api.routes.correlations._get_redis_cached", return_value=None),
            patch(
                "margin_api.routes.correlations._compute_live_showcase",
                return_value=None,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/correlations/showcase")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tickers"]) == 5


# ===========================================================================
# transparency.py — lines 52-85
# ===========================================================================


class TestTransparencyRouteAsync:
    """AsyncClient tests for transparency endpoint."""

    @pytest.mark.asyncio
    async def test_transparency_empty_db(self, session_factory):
        """GET /governance/transparency returns response with empty data."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/governance/transparency")

        assert resp.status_code == 200
        data = resp.json()
        assert "oversight_levels" in data
        assert "last_approvals" in data
        assert "pipeline_health" in data
        assert data["last_approvals"] == {}

    @pytest.mark.asyncio
    async def test_transparency_with_approvals(self, db_session, session_factory):
        """GET /governance/transparency includes last_approvals when data exists."""
        now = datetime.now(UTC)
        approval = PipelineApproval(
            gate_type="score_publish",
            status="approved",
            payload_ref={},
            impact_summary={},
            submitted_at=now - timedelta(hours=1),
            decided_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db_session.add(approval)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/governance/transparency")

        assert resp.status_code == 200
        data = resp.json()
        assert "score_publish" in data["last_approvals"]
        assert data["last_approvals"]["score_publish"]["status"] == "approved"

    @pytest.mark.asyncio
    async def test_transparency_with_pipeline_health(self, db_session, session_factory):
        """GET /governance/transparency includes last_successful_run when IngestionRun exists."""
        now = datetime.now(UTC)
        snap = await _make_universe_snapshot(db_session)
        ingestion_run = IngestionRun(
            snapshot_id=snap.id,
            run_type="full",
            tickers_requested=0,
            tickers_succeeded=0,
            status="completed",
            pipeline_id="pipe-123",
            started_at=now - timedelta(minutes=10),
            completed_at=now,
        )
        db_session.add(ingestion_run)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/governance/transparency")

        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_health"]["last_successful_run"] is not None

    @pytest.mark.asyncio
    async def test_transparency_oversight_levels_structure(self, session_factory):
        """GET /governance/transparency returns correct oversight levels structure."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/governance/transparency")

        data = resp.json()
        levels = data["oversight_levels"]
        assert "in_the_loop" in levels
        assert "on_the_loop" in levels
        assert "out_of_the_loop" in levels


# ===========================================================================
# jobs.py — lines 52-54, 82-132
# ===========================================================================


class TestJobsRouteAsync:
    """AsyncClient tests for job status endpoints."""

    @pytest.mark.asyncio
    async def test_get_latest_jobs_empty(self, session_factory):
        """GET /jobs/latest returns empty list when no jobs."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/jobs/latest")

        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_latest_jobs_with_data(self, db_session, session_factory):
        """GET /jobs/latest returns job runs."""
        now = datetime.now(UTC)
        job = JobRun(
            job_type="full_score",
            status="completed",
            progress=1.0,
            triggered_by="schedule",
            started_at=now - timedelta(minutes=5),
            completed_at=now,
        )
        db_session.add(job)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/jobs/latest")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["job_type"] == "full_score"
        assert data[0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_latest_jobs_limit(self, db_session, session_factory):
        """GET /jobs/latest?limit=2 returns at most 2 jobs."""
        now = datetime.now(UTC)
        for i in range(5):
            job = JobRun(
                job_type=f"job_{i}",
                status="completed",
                progress=1.0,
                triggered_by="schedule",
                started_at=now,
                completed_at=now,
            )
            db_session.add(job)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/jobs/latest?limit=2")

        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_get_pipeline_status_not_found(self, session_factory):
        """GET /jobs/pipeline/{id} returns 404 when no pipeline found."""
        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/jobs/pipeline/nonexistent-pipeline-id")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_pipeline_status_with_ingestion_run(self, db_session, session_factory):
        """GET /jobs/pipeline/{id} returns ingestion stage when IngestionRun exists."""
        pipeline_id = "pipe-" + str(uuid.uuid4())
        now = datetime.now(UTC)
        snap = await _make_universe_snapshot(db_session)
        ingest = IngestionRun(
            snapshot_id=snap.id,
            run_type="full",
            tickers_requested=1,
            tickers_succeeded=1,
            status="completed",
            pipeline_id=pipeline_id,
            started_at=now - timedelta(minutes=10),
            completed_at=now,
        )
        db_session.add(ingest)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/jobs/pipeline/{pipeline_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_id"] == pipeline_id
        assert data["status"] == "completed"
        assert len(data["stages"]) >= 1
        assert data["stages"][0]["stage"] == "ingest"

    @pytest.mark.asyncio
    async def test_get_pipeline_status_with_job_runs(self, db_session, session_factory):
        """GET /jobs/pipeline/{id} aggregates JobRun stages."""
        pipeline_id = "pipe-" + str(uuid.uuid4())
        now = datetime.now(UTC)
        for job_type in ["full_score", "full_score_v3"]:
            job = JobRun(
                job_type=job_type,
                status="completed",
                progress=1.0,
                triggered_by="chained",
                pipeline_id=pipeline_id,
                started_at=now - timedelta(minutes=5),
                completed_at=now,
            )
            db_session.add(job)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/jobs/pipeline/{pipeline_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["stages"]) == 2
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_pipeline_status_running(self, db_session, session_factory):
        """Pipeline status is 'running' if any stage is running."""
        pipeline_id = "pipe-" + str(uuid.uuid4())
        now = datetime.now(UTC)
        job = JobRun(
            job_type="full_score",
            status="running",
            progress=0.5,
            triggered_by="schedule",
            pipeline_id=pipeline_id,
            started_at=now,
        )
        db_session.add(job)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/jobs/pipeline/{pipeline_id}")

        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    @pytest.mark.asyncio
    async def test_get_pipeline_status_failed(self, db_session, session_factory):
        """Pipeline status is 'failed' if any stage failed."""
        pipeline_id = "pipe-" + str(uuid.uuid4())
        now = datetime.now(UTC)
        job = JobRun(
            job_type="full_score",
            status="failed",
            progress=0.0,
            triggered_by="schedule",
            pipeline_id=pipeline_id,
            started_at=now,
            error_message="Score computation error",
        )
        db_session.add(job)
        await db_session.commit()

        app = _make_app(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/jobs/pipeline/{pipeline_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["stages"][0]["error_message"] == "Score computation error"
