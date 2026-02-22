"""Tests for admin pipeline trigger, universe activation, and quarantine endpoints."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.models import Asset


class TestPipelineTrigger:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def _make_client(self, admin_key: str = "test-admin-key"):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": admin_key}):
            app = create_app()
            return TestClient(app)

    def test_trigger_requires_admin_key_header(self):
        client = self._make_client()
        response = client.post("/api/v1/admin/pipeline/trigger")
        assert response.status_code == 422  # Missing required header

    def test_trigger_rejects_wrong_key(self):
        client = self._make_client(admin_key="correct-key")
        response = client.post(
            "/api/v1/admin/pipeline/trigger",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 403

    def test_trigger_rejects_empty_admin_key_config(self):
        """Trigger returns 503 when admin key is not configured."""
        client = self._make_client(admin_key="")
        response = client.post(
            "/api/v1/admin/pipeline/trigger",
            headers={"X-Admin-Key": "any-key"},
        )
        assert response.status_code == 503

    def test_trigger_enqueues_job(self):
        """Trigger returns 202 and enqueues full_ingest with correct key."""
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
            client = TestClient(app)
            response = client.post(
                "/api/v1/admin/pipeline/trigger",
                headers={"X-Admin-Key": "test-key"},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "full_ingest"
        assert data["job_id"] == "test-job-123"
        mock_pool.enqueue_job.assert_called_once()
        call_args = mock_pool.enqueue_job.call_args
        assert call_args[0][0] == "full_ingest"
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
            client = TestClient(app)
            response = client.post(
                "/api/v1/admin/pipeline/trigger",
                headers={"X-Admin-Key": "test-key"},
            )

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

    def test_activate_requires_admin_key(self):
        client = self._make_client()
        response = client.post("/api/v1/admin/universe/activate")
        assert response.status_code == 422

    def test_activate_rejects_wrong_key(self):
        client = self._make_client(admin_key="correct-key")
        response = client.post(
            "/api/v1/admin/universe/activate",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 403

    def test_activate_succeeds_with_yaml(self):
        """Activate universe loads YAML and creates snapshot."""
        mock_snapshot = MagicMock()
        mock_snapshot.version = "2026.02.18"
        mock_snapshot.ticker_count = 3057
        mock_snapshot.config_hash = "abc123"

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.services.universe.activate_universe",
                new_callable=AsyncMock,
                return_value=mock_snapshot,
            ),
            patch("pathlib.Path.exists", return_value=True),
        ):
            app = create_app()
            client = TestClient(app)
            response = client.post(
                "/api/v1/admin/universe/activate",
                headers={"X-Admin-Key": "test-key"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "activated"
        assert data["version"] == "2026.02.18"
        assert data["ticker_count"] == 3057


class TestQuarantinedEndpoint:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_quarantined_requires_admin_key(self):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
            response = client.get("/api/v1/admin/ingestion/quarantined")
        assert response.status_code == 422

    def test_quarantined_rejects_wrong_key(self):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "correct-key"}):
            app = create_app()
            client = TestClient(app)
            response = client.get(
                "/api/v1/admin/ingestion/quarantined",
                headers={"X-Admin-Key": "wrong-key"},
            )
        assert response.status_code == 403

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
            app.dependency_overrides[
                __import__("margin_api.db.session", fromlist=["get_db"]).get_db
            ] = mock_get_db
            client = TestClient(app)
            response = client.get(
                "/api/v1/admin/ingestion/quarantined",
                headers={"X-Admin-Key": "test-key"},
            )

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
            app.dependency_overrides[
                __import__("margin_api.db.session", fromlist=["get_db"]).get_db
            ] = mock_get_db
            client = TestClient(app)
            response = client.get(
                "/api/v1/admin/ingestion/quarantined",
                headers={"X-Admin-Key": "test-key"},
            )

        assert response.status_code == 200
        assert response.json() == []
