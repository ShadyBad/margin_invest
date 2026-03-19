"""Tests for admin webhook subscription CRUD endpoints.

Covers:
- POST /api/v1/admin/webhooks — create subscription (201)
- GET /api/v1/admin/webhooks — list subscriptions (200)
- DELETE /api/v1/admin/webhooks/{id} — delete subscription (204)
- POST duplicate — 409 conflict
- Invalid event_type — 422
- Unauthorized (no session) — 401
- GET /{id}/deliveries — paginated delivery history
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import Settings, get_settings
from margin_api.db.base import Base
from margin_api.db.models import User, UserRole, WebhookDelivery, WebhookSubscription
from margin_api.db.session import get_db
from margin_api.deps import get_admin_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENCRYPTION_KEY = Fernet.generate_key().decode()
_VALID_EVENT_TYPE = "score.staged"
_VALID_URL = "https://example.com/hooks"


# ---------------------------------------------------------------------------
# Helper: mock admin user
# ---------------------------------------------------------------------------


def _make_admin_user() -> User:
    user = MagicMock(spec=User)
    user.id = 42
    user.role = UserRole.ADMIN
    return user


# ---------------------------------------------------------------------------
# Fixtures
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
# App factory
# ---------------------------------------------------------------------------


def _make_app_and_client(session_factory=None) -> tuple:
    """Create app and TestClient with admin dependency overridden."""
    get_settings.cache_clear()
    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
        os.environ, {"MARGIN_ADMIN_KEY": "test-admin-key"}
    ):
        app = create_app()

    async def override_admin():
        return _make_admin_user()

    app.dependency_overrides[get_admin_user] = override_admin

    if session_factory is not None:

        async def db_override():
            async with session_factory() as s:
                yield s

        app.dependency_overrides[get_db] = db_override

    def override_settings():
        return Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            mfa_encryption_key=_ENCRYPTION_KEY,
            api_key_encryption_key=_ENCRYPTION_KEY,
        )

    app.dependency_overrides[get_settings] = override_settings

    client = TestClient(app)
    return app, client


# ---------------------------------------------------------------------------
# Tests: POST (create)
# ---------------------------------------------------------------------------


class TestCreateWebhook:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_create_returns_201_with_hmac_key(self, session_factory):
        """POST returns 201 with hmac_key_plaintext in response."""
        _, client = _make_app_and_client(session_factory)
        response = client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == _VALID_EVENT_TYPE
        assert data["url"] == _VALID_URL
        assert data["is_active"] is True
        assert "hmac_key_plaintext" in data
        assert len(data["hmac_key_plaintext"]) == 64  # secrets.token_hex(32) = 64 hex chars
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_stores_encrypted_key(self, session_factory, db_session):
        """POST stores encrypted HMAC key in DB (not plaintext)."""
        _, client = _make_app_and_client(session_factory)
        response = client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL},
        )
        assert response.status_code == 201
        plaintext_key = response.json()["hmac_key_plaintext"]

        async with session_factory() as session:
            result = await session.execute(select(WebhookSubscription))
            sub = result.scalar_one()

        # Stored key is NOT the plaintext key
        assert sub.hmac_key_encrypted != plaintext_key
        # But decrypts to the plaintext key
        fernet = Fernet(_ENCRYPTION_KEY.encode())
        decrypted = fernet.decrypt(sub.hmac_key_encrypted.encode()).decode()
        assert decrypted == plaintext_key

    @pytest.mark.asyncio
    async def test_create_all_valid_event_types(self, session_factory):
        """POST accepts all 6 valid event types."""
        valid_types = [
            "score.staged",
            "score.approved",
            "score.published",
            "model.promoted",
            "circuit_breaker.tripped",
            "config.updated",
        ]
        _, client = _make_app_and_client(session_factory)
        for i, event_type in enumerate(valid_types):
            response = client.post(
                "/api/v1/admin/webhooks",
                json={"event_type": event_type, "url": f"https://example.com/hook/{i}"},
            )
            assert response.status_code == 201, f"Failed for {event_type}: {response.json()}"

    @pytest.mark.asyncio
    async def test_create_invalid_event_type_returns_422(self, session_factory):
        """POST with unknown event_type returns 422."""
        _, client = _make_app_and_client(session_factory)
        response = client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": "bogus.event", "url": _VALID_URL},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_duplicate_returns_409(self, session_factory):
        """POST with same event_type + url returns 409."""
        _, client = _make_app_and_client(session_factory)
        payload = {"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL}
        resp1 = client.post("/api/v1/admin/webhooks", json=payload)
        assert resp1.status_code == 201

        resp2 = client.post("/api/v1/admin/webhooks", json=payload)
        assert resp2.status_code == 409

    def test_create_requires_admin(self):
        """POST returns 401 without admin session cookie."""
        get_settings.cache_clear()
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {"MARGIN_ADMIN_KEY": "test-key"}
        ):
            app = create_app()
            client = TestClient(app)
        response = client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET (list)
# ---------------------------------------------------------------------------


class TestListWebhooks:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_list_empty_returns_empty_list(self, session_factory):
        """GET with no subscriptions returns empty list."""
        _, client = _make_app_and_client(session_factory)
        response = client.get("/api/v1/admin/webhooks")

        assert response.status_code == 200
        data = response.json()
        assert data["subscriptions"] == []

    @pytest.mark.asyncio
    async def test_list_returns_created_subscriptions(self, session_factory):
        """GET returns all created subscriptions."""
        _, client = _make_app_and_client(session_factory)

        client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": "score.staged", "url": "https://example.com/a"},
        )
        client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": "score.published", "url": "https://example.com/b"},
        )

        response = client.get("/api/v1/admin/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data["subscriptions"]) == 2

        event_types = {s["event_type"] for s in data["subscriptions"]}
        assert event_types == {"score.staged", "score.published"}

    @pytest.mark.asyncio
    async def test_list_does_not_include_hmac_key(self, session_factory):
        """GET list response does NOT expose hmac_key_plaintext."""
        _, client = _make_app_and_client(session_factory)
        client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL},
        )

        response = client.get("/api/v1/admin/webhooks")
        data = response.json()
        for sub in data["subscriptions"]:
            assert "hmac_key_plaintext" not in sub
            assert "hmac_key_encrypted" not in sub

    def test_list_requires_admin(self):
        """GET returns 401 without admin session cookie."""
        get_settings.cache_clear()
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {"MARGIN_ADMIN_KEY": "test-key"}
        ):
            app = create_app()
            client = TestClient(app)
        response = client.get("/api/v1/admin/webhooks")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: DELETE
# ---------------------------------------------------------------------------


class TestDeleteWebhook:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_delete_returns_204(self, session_factory):
        """DELETE /{id} removes subscription and returns 204."""
        _, client = _make_app_and_client(session_factory)

        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL},
        )
        sub_id = create_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/admin/webhooks/{sub_id}")
        assert del_resp.status_code == 204

        # Confirm it's gone from list
        list_resp = client.get("/api/v1/admin/webhooks")
        assert list_resp.json()["subscriptions"] == []

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, session_factory):
        """DELETE /{id} for unknown ID returns 404."""
        _, client = _make_app_and_client(session_factory)
        response = client.delete("/api/v1/admin/webhooks/99999")
        assert response.status_code == 404

    def test_delete_requires_admin(self):
        """DELETE returns 401 without admin session cookie."""
        get_settings.cache_clear()
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {"MARGIN_ADMIN_KEY": "test-key"}
        ):
            app = create_app()
            client = TestClient(app)
        response = client.delete("/api/v1/admin/webhooks/1")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /{id}/deliveries
# ---------------------------------------------------------------------------


class TestWebhookDeliveries:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_deliveries_empty_when_none(self, session_factory):
        """GET /{id}/deliveries returns empty list when no deliveries exist."""
        _, client = _make_app_and_client(session_factory)

        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL},
        )
        sub_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/admin/webhooks/{sub_id}/deliveries")
        assert response.status_code == 200
        data = response.json()
        assert data["deliveries"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_deliveries_returns_existing_deliveries(self, session_factory):
        """GET /{id}/deliveries returns delivery records."""
        _, client = _make_app_and_client(session_factory)

        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL},
        )
        sub_id = create_resp.json()["id"]

        # Insert deliveries directly into the DB
        async with session_factory() as session:
            for i in range(3):
                d = WebhookDelivery(
                    subscription_id=sub_id,
                    event_type=_VALID_EVENT_TYPE,
                    payload={"i": i},
                    status="delivered",
                    attempts=1,
                )
                session.add(d)
            await session.commit()

        response = client.get(f"/api/v1/admin/webhooks/{sub_id}/deliveries")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["deliveries"]) == 3

    @pytest.mark.asyncio
    async def test_deliveries_pagination(self, session_factory):
        """GET /{id}/deliveries supports limit/offset pagination."""
        _, client = _make_app_and_client(session_factory)

        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL},
        )
        sub_id = create_resp.json()["id"]

        async with session_factory() as session:
            for i in range(5):
                d = WebhookDelivery(
                    subscription_id=sub_id,
                    event_type=_VALID_EVENT_TYPE,
                    payload={"i": i},
                    status="pending",
                    attempts=0,
                )
                session.add(d)
            await session.commit()

        # Page 1
        resp1 = client.get(f"/api/v1/admin/webhooks/{sub_id}/deliveries?limit=2&offset=0")
        assert resp1.status_code == 200
        d1 = resp1.json()
        assert d1["total"] == 5
        assert len(d1["deliveries"]) == 2

        # Page 2
        resp2 = client.get(f"/api/v1/admin/webhooks/{sub_id}/deliveries?limit=2&offset=2")
        assert resp2.status_code == 200
        d2 = resp2.json()
        assert d2["total"] == 5
        assert len(d2["deliveries"]) == 2

    @pytest.mark.asyncio
    async def test_deliveries_nonexistent_subscription_returns_404(self, session_factory):
        """GET /99999/deliveries returns 404."""
        _, client = _make_app_and_client(session_factory)
        response = client.get("/api/v1/admin/webhooks/99999/deliveries")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deliveries_response_fields(self, session_factory):
        """Delivery response includes required fields."""
        _, client = _make_app_and_client(session_factory)

        create_resp = client.post(
            "/api/v1/admin/webhooks",
            json={"event_type": _VALID_EVENT_TYPE, "url": _VALID_URL},
        )
        sub_id = create_resp.json()["id"]

        async with session_factory() as session:
            d = WebhookDelivery(
                subscription_id=sub_id,
                event_type=_VALID_EVENT_TYPE,
                payload={"test": "data"},
                status="failed",
                attempts=2,
                last_status_code=500,
                last_error="Server error",
            )
            session.add(d)
            await session.commit()

        response = client.get(f"/api/v1/admin/webhooks/{sub_id}/deliveries")
        data = response.json()
        delivery = data["deliveries"][0]

        assert delivery["event_type"] == _VALID_EVENT_TYPE
        assert delivery["status"] == "failed"
        assert delivery["attempts"] == 2
        assert delivery["last_status_code"] == 500
        assert delivery["last_error"] == "Server error"
        assert "id" in delivery
        assert "created_at" in delivery

    def test_deliveries_requires_admin(self):
        """GET /{id}/deliveries returns 401 without admin session cookie."""
        get_settings.cache_clear()
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            os.environ, {"MARGIN_ADMIN_KEY": "test-key"}
        ):
            app = create_app()
            client = TestClient(app)
        response = client.get("/api/v1/admin/webhooks/1/deliveries")
        assert response.status_code == 401
