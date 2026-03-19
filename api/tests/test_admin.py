"""Tests for admin pipeline trigger, universe activation, and quarantine endpoints."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.models import Asset, User, UserRole
from margin_api.deps import get_admin_user


def _make_admin_user() -> User:
    """Create a mock admin User for dependency override."""
    user = MagicMock(spec=User)
    user.id = 1
    user.role = UserRole.ADMIN
    return user


def _make_client_with_admin(admin_key: str = "test-admin-key", db_override=None):
    """Create app and TestClient with get_admin_user overridden."""
    get_settings.cache_clear()
    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": admin_key}):
        app = create_app()

    async def override_admin_user():
        return _make_admin_user()

    app.dependency_overrides[get_admin_user] = override_admin_user
    if db_override is not None:
        from margin_api.db.session import get_db

        app.dependency_overrides[get_db] = db_override
    return TestClient(app)


class TestPipelineTrigger:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def _make_client(self, admin_key: str = "test-admin-key"):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": admin_key}):
            app = create_app()
            return TestClient(app)

    def test_trigger_requires_auth(self):
        """Without a valid admin session cookie, endpoint returns 401."""
        client = self._make_client()
        response = client.post("/api/v1/admin/pipeline/trigger")
        assert response.status_code == 401  # No admin_session cookie

    def test_trigger_enqueues_job(self):
        """Trigger returns 202 and enqueues orchestrate_ingest with admin auth."""
        mock_job = MagicMock()
        mock_job.job_id = "test-job-123"

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        mock_pool.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.create_pool", return_value=mock_pool),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.post("/api/v1/admin/pipeline/trigger")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "orchestrate_ingest"
        assert data["job_id"] == "test-job-123"
        mock_pool.enqueue_job.assert_called_once()
        call_args = mock_pool.enqueue_job.call_args
        assert call_args[0][0] == "orchestrate_ingest"
        assert "_job_id" in call_args[1]

    def test_trigger_handles_redis_failure(self):
        """Trigger returns 503 when Redis is unreachable."""
        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.create_pool",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.post("/api/v1/admin/pipeline/trigger")

        assert response.status_code == 503


class TestUniverseActivate:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def _make_client(self, admin_key: str = "test-admin-key"):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": admin_key}):
            app = create_app()
            return TestClient(app)

    def test_activate_requires_auth(self):
        """Without admin session cookie, endpoint returns 401."""
        client = self._make_client()
        response = client.post("/api/v1/admin/universe/activate")
        assert response.status_code == 401

    def test_activate_stages_with_yaml(self):
        """Activate universe now returns 202 with staged status."""
        mock_staging_result = {
            "status": "staged",
            "approval_id": 1,
            "added_tickers": ["AAPL"],
            "removed_tickers": [],
        }

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.stage_universe_activation",
                new_callable=AsyncMock,
                return_value=mock_staging_result,
            ),
            patch("pathlib.Path.exists", return_value=True),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            response = client.post("/api/v1/admin/universe/activate")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "staged"
        assert data["approval_id"] == 1


class TestQuarantinedEndpoint:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_quarantined_requires_auth(self):
        """Without admin session cookie, endpoint returns 401."""
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
            response = client.get("/api/v1/admin/ingestion/quarantined")
        assert response.status_code == 401

    def test_quarantined_returns_quarantined_assets(self):
        """GET /admin/ingestion/quarantined returns quarantined assets."""
        quarantined_at = datetime(2026, 2, 20, 12, 0, 0, tzinfo=UTC)
        mock_asset = MagicMock(spec=Asset)
        mock_asset.ticker = "BADTK"
        mock_asset.name = "Bad Ticker Inc"
        mock_asset.ingestion_status = "quarantined"
        mock_asset.consecutive_failures = 5
        mock_asset.last_failure_reason = "429 Too Many Requests"
        mock_asset.quarantined_at = quarantined_at
        mock_asset.last_retry_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_asset]

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        async def mock_get_db():
            return mock_session

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            app.dependency_overrides[
                __import__("margin_api.db.session", fromlist=["get_db"]).get_db
            ] = mock_get_db
            client = TestClient(app)
            response = client.get("/api/v1/admin/ingestion/quarantined")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["ticker"] == "BADTK"
        assert data[0]["ingestion_status"] == "quarantined"
        assert data[0]["consecutive_failures"] == 5

    def test_quarantined_returns_empty_list(self):
        """GET /admin/ingestion/quarantined returns [] when no quarantined assets."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        async def mock_execute(stmt):
            return mock_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        async def mock_get_db():
            return mock_session

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            app.dependency_overrides[
                __import__("margin_api.db.session", fromlist=["get_db"]).get_db
            ] = mock_get_db
            client = TestClient(app)
            response = client.get("/api/v1/admin/ingestion/quarantined")

        assert response.status_code == 200
        assert response.json() == []
