"""Tests for admin pipeline trigger and universe activation endpoints."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from margin_api.app import create_app
from margin_api.config import get_settings


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
        """Trigger returns 202 and enqueues full_ingest with idempotent job ID."""
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
        # Verify idempotent _job_id was passed
        call_kwargs = mock_pool.enqueue_job.call_args
        assert call_kwargs[0][0] == "full_ingest"
        assert call_kwargs[1]["_job_id"].startswith("full_ingest:")

    def test_trigger_returns_200_when_already_enqueued(self):
        """Trigger returns 200 when job already enqueued today (ARQ returns None)."""
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=None)
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

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_enqueued"

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
