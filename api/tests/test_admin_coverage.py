"""Additional admin endpoint tests to cover scoring trigger, redis health,
flush-jobs, and ML training trigger."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.models import User, UserRole
from margin_api.deps import get_admin_user


def _make_admin_user() -> User:
    """Return a mock admin User for dependency override."""
    user = MagicMock(spec=User)
    user.id = 1
    user.role = UserRole.ADMIN
    return user


class TestScoringTrigger:
    """Tests for POST /api/v1/admin/scoring/trigger."""

    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_scoring_trigger_enqueues_job(self):
        mock_job = MagicMock()
        mock_job.job_id = "score-job-456"

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
            resp = client.post("/api/v1/admin/scoring/trigger")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "full_score_v3"
        assert data["job_id"] == "score-job-456"
        mock_pool.enqueue_job.assert_called_once()
        call_args = mock_pool.enqueue_job.call_args
        assert call_args[0][0] == "full_score_v3"

    def test_scoring_trigger_requires_auth(self):
        """Without admin session cookie, returns 401."""
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/scoring/trigger")
        assert resp.status_code == 401

    def test_scoring_trigger_redis_failure(self):
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
            resp = client.post("/api/v1/admin/scoring/trigger")
        assert resp.status_code == 503


class TestMLTrainingTrigger:
    """Tests for POST /api/v1/admin/ml/train."""

    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_ml_train_enqueues_job(self):
        mock_job = MagicMock()
        mock_job.job_id = "ml-job-789"

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
            resp = client.post("/api/v1/admin/ml/train")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "train_ml_models"
        assert data["job_id"] == "ml-job-789"

    def test_ml_train_requires_auth(self):
        """Without admin session cookie, returns 401."""
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/ml/train")
        assert resp.status_code == 401

    def test_ml_train_redis_failure(self):
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
            resp = client.post("/api/v1/admin/ml/train")
        assert resp.status_code == 503


class TestRedisHealth:
    """Tests for GET /api/v1/admin/redis/health."""

    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_redis_health_success(self):
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.zrangebyscore = AsyncMock(return_value=[b"job1", b"job2"])
        mock_client.keys = AsyncMock(return_value=[b"arq:result:abc"])
        mock_client.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.aioredis.from_url", return_value=mock_client),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            resp = client.get("/api/v1/admin/redis/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "connected"
        assert data["queued_count"] == 2
        assert data["queued_jobs"] == ["job1", "job2"]

    def test_redis_health_error(self):
        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.aioredis.from_url",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            resp = client.get("/api/v1/admin/redis/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "Redis down" in data["error"]

    def test_redis_health_redacts_password(self):
        """Password in Redis URL is redacted in response."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.zrangebyscore = AsyncMock(return_value=[])
        mock_client.keys = AsyncMock(return_value=[])
        mock_client.aclose = AsyncMock()

        with (
            patch.dict(
                os.environ,
                {
                    "MARGIN_ADMIN_KEY": "test-key",
                    "MARGIN_REDIS_URL": "redis://:secret@redis-host:6379",
                },
            ),
            patch("margin_api.routes.admin.aioredis.from_url", return_value=mock_client),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            resp = client.get("/api/v1/admin/redis/health")

        data = resp.json()
        # Should not contain the password
        assert "secret" not in data.get("redis_url", "")


class TestFlushRedisJobs:
    """Tests for POST /api/v1/admin/redis/flush-jobs."""

    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_flush_jobs_success(self):
        mock_client = AsyncMock()
        mock_client.zrangebyscore = AsyncMock(return_value=[b"stale-job-1", b"stale-job-2"])
        mock_client.delete = AsyncMock(return_value=1)
        mock_client.keys = AsyncMock(return_value=[b"arq:in-progress:x"])
        mock_client.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.aioredis.from_url", return_value=mock_client),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/redis/flush-jobs")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "flushed"
        assert data["removed_jobs"] == ["stale-job-1", "stale-job-2"]
        assert data["removed_in_progress"] == ["arq:in-progress:x"]

    def test_flush_jobs_error(self):
        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.aioredis.from_url",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/redis/flush-jobs")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"

    def test_flush_jobs_requires_auth(self):
        """Without admin session cookie, returns 401."""
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/redis/flush-jobs")
        assert resp.status_code == 401


class TestUniverseActivateErrors:
    """Additional error paths for POST /api/v1/admin/universe/activate."""

    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_activate_yaml_not_found(self):
        """Returns 500 when universe.yaml is not found."""
        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("pathlib.Path.exists", return_value=False),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/universe/activate")
        assert resp.status_code == 500
        assert "universe.yaml not found" in resp.json()["detail"]

    def test_activate_service_error(self):
        """Returns 500 when stage_universe_activation raises."""
        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "margin_api.routes.admin.stage_universe_activation",
                new_callable=AsyncMock,
                side_effect=RuntimeError("DB error"),
            ),
        ):
            app = create_app()
            app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/universe/activate")
        assert resp.status_code == 500
        assert "Failed to stage universe activation" in resp.json()["detail"]
