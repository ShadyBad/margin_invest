"""Tests for admin governance config CRUD endpoints."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import GovernanceConfig, GovernanceEvent, User, UserRole
from margin_api.db.session import get_db
from margin_api.deps import get_superadmin_user
from margin_api.services.governance_config import CONFIG_REGISTRY
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# ---------------------------------------------------------------------------
# Superadmin user mock
# ---------------------------------------------------------------------------


def _make_superadmin_user() -> User:
    """Return a mock superadmin User for dependency override."""
    user = MagicMock(spec=User)
    user.id = 99
    user.role = UserRole.SUPERADMIN
    return user


# ---------------------------------------------------------------------------
# Async DB fixtures
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


def _make_app_and_client(session_factory=None) -> tuple:
    """Create app and TestClient with superadmin dependency overridden."""
    get_settings.cache_clear()
    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-admin-key"}):
        app = create_app()

    async def override_superadmin():
        return _make_superadmin_user()

    app.dependency_overrides[get_superadmin_user] = override_superadmin

    if session_factory is not None:
        async def db_override():
            async with session_factory() as s:
                yield s
        app.dependency_overrides[get_db] = db_override

    client = TestClient(app)
    return app, client


# ---------------------------------------------------------------------------
# Tests: List configs
# ---------------------------------------------------------------------------


class TestListGovernanceConfigs:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_list_returns_all_registry_keys(self, session_factory):
        """GET /admin/governance-config returns all registry keys with defaults."""
        _, client = _make_app_and_client(session_factory)
        response = client.get("/api/v1/admin/governance-config")

        assert response.status_code == 200
        data = response.json()
        returned_keys = {c["config_key"] for c in data["configs"]}
        registry_keys = set(CONFIG_REGISTRY.keys())
        assert returned_keys == registry_keys

    @pytest.mark.asyncio
    async def test_list_shows_defaults_when_no_overrides(self, session_factory):
        """All returned configs have is_default=True when no DB overrides exist."""
        _, client = _make_app_and_client(session_factory)
        response = client.get("/api/v1/admin/governance-config")

        assert response.status_code == 200
        data = response.json()
        for config in data["configs"]:
            assert config["is_default"] is True

    def test_list_requires_superadmin(self):
        """GET /admin/governance-config returns 401 without session cookie."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
        response = client.get("/api/v1/admin/governance-config")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: Get single config
# ---------------------------------------------------------------------------


class TestGetGovernanceConfig:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_get_known_key_returns_default(self, session_factory):
        """GET /{key} returns the default value when no DB override exists."""
        _, client = _make_app_and_client(session_factory)
        key = "circuit_breaker.score_drift"
        response = client.get(f"/api/v1/admin/governance-config/{key}")

        assert response.status_code == 200
        data = response.json()
        assert data["config_key"] == key
        assert data["is_default"] is True
        assert data["config_value"] == CONFIG_REGISTRY[key].default
        assert data["description"] == CONFIG_REGISTRY[key].description

    @pytest.mark.asyncio
    async def test_get_unknown_key_returns_404(self, session_factory):
        """GET /{key} returns 404 for unknown keys."""
        _, client = _make_app_and_client(session_factory)
        response = client.get("/api/v1/admin/governance-config/nonexistent.key")
        assert response.status_code == 404

    def test_get_requires_superadmin(self):
        """GET /{key} returns 401 without session cookie."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
        response = client.get("/api/v1/admin/governance-config/circuit_breaker.score_drift")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: PUT upsert
# ---------------------------------------------------------------------------


class TestPutGovernanceConfig:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_put_upserts_and_marks_not_default(self, session_factory, db_session):
        """PUT /{key} creates override and returns is_default=False."""
        _, client = _make_app_and_client(session_factory)
        key = "circuit_breaker.score_drift"
        response = client.put(
            f"/api/v1/admin/governance-config/{key}",
            json={"config_value": {"threshold": 42.0}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["config_key"] == key
        assert data["is_default"] is False
        assert data["config_value"] == {"threshold": 42.0}

    @pytest.mark.asyncio
    async def test_put_creates_governance_event(self, session_factory, db_session):
        """PUT /{key} logs a config.updated GovernanceEvent."""
        _, client = _make_app_and_client(session_factory)
        key = "circuit_breaker.ingestion_failure"
        client.put(
            f"/api/v1/admin/governance-config/{key}",
            json={"config_value": {"threshold": 15.0}},
        )

        async with session_factory() as session:
            result = await session.execute(
                select(GovernanceEvent).where(GovernanceEvent.event_type == "config.updated")
            )
            events = result.scalars().all()

        assert len(events) == 1
        assert events[0].source == "admin_api"
        assert events[0].detail["config_key"] == key
        assert events[0].detail["new_value"] == {"threshold": 15.0}
        assert events[0].detail["admin_user_id"] == 99

    @pytest.mark.asyncio
    async def test_put_out_of_range_returns_422(self, session_factory):
        """PUT /{key} with value outside allowed range returns 422."""
        _, client = _make_app_and_client(session_factory)
        key = "circuit_breaker.score_drift"
        response = client.put(
            f"/api/v1/admin/governance-config/{key}",
            json={"config_value": {"threshold": 150.0}},  # max is 100.0
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_put_unknown_key_returns_422(self, session_factory):
        """PUT with unknown key returns 422 (validate_config_value catches it)."""
        _, client = _make_app_and_client(session_factory)
        response = client.put(
            "/api/v1/admin/governance-config/unknown.key",
            json={"config_value": {"threshold": 10.0}},
        )
        assert response.status_code == 422

    def test_put_requires_superadmin(self):
        """PUT /{key} returns 401 without session cookie."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
        response = client.put(
            "/api/v1/admin/governance-config/circuit_breaker.score_drift",
            json={"config_value": {"threshold": 25.0}},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: DELETE
# ---------------------------------------------------------------------------


class TestDeleteGovernanceConfig:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_delete_removes_override_and_reverts_to_default(self, session_factory):
        """DELETE /{key} removes override; subsequent GET shows is_default=True."""
        _, client = _make_app_and_client(session_factory)
        key = "circuit_breaker.ml_regression"

        # First upsert an override
        client.put(
            f"/api/v1/admin/governance-config/{key}",
            json={"config_value": {"threshold": 60.0}},
        )

        # Confirm it's not default
        get_resp = client.get(f"/api/v1/admin/governance-config/{key}")
        assert get_resp.json()["is_default"] is False

        # Delete the override
        del_resp = client.delete(f"/api/v1/admin/governance-config/{key}")
        assert del_resp.status_code == 204

        # Now should be back to default
        get_resp2 = client.get(f"/api/v1/admin/governance-config/{key}")
        assert get_resp2.status_code == 200
        assert get_resp2.json()["is_default"] is True

    @pytest.mark.asyncio
    async def test_delete_creates_governance_event(self, session_factory):
        """DELETE /{key} logs a config.deleted GovernanceEvent."""
        _, client = _make_app_and_client(session_factory)
        key = "circuit_breaker.score_drift"

        # Create an override first
        client.put(
            f"/api/v1/admin/governance-config/{key}",
            json={"config_value": {"threshold": 25.0}},
        )

        # Delete it
        client.delete(f"/api/v1/admin/governance-config/{key}")

        async with session_factory() as session:
            result = await session.execute(
                select(GovernanceEvent).where(GovernanceEvent.event_type == "config.deleted")
            )
            events = result.scalars().all()

        assert len(events) == 1
        assert events[0].source == "admin_api"
        assert events[0].detail["config_key"] == key
        assert events[0].detail["admin_user_id"] == 99

    @pytest.mark.asyncio
    async def test_delete_unknown_key_returns_404(self, session_factory):
        """DELETE with unknown key returns 404."""
        _, client = _make_app_and_client(session_factory)
        response = client.delete("/api/v1/admin/governance-config/bogus.key")
        assert response.status_code == 404

    def test_delete_requires_superadmin(self):
        """DELETE /{key} returns 401 without session cookie."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
        response = client.delete(
            "/api/v1/admin/governance-config/circuit_breaker.score_drift"
        )
        assert response.status_code == 401
