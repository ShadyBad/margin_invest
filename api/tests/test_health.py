"""Tests for health check endpoint."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from margin_api.app import create_app
from margin_api.config import get_settings


class TestHealthEndpoint:
    def test_health_returns_ok_when_services_available(self, client):
        """Health check returns structured response with service checks."""
        # Mock Redis to simulate availability
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        with patch("margin_api.routes.health.aioredis.from_url", return_value=mock_redis):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "status" in data
        assert "database" in data
        assert "redis" in data

    def test_health_includes_version(self, client):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        with patch("margin_api.routes.health.aioredis.from_url", return_value=mock_redis):
            response = client.get("/health")

        data = response.json()
        assert data["version"] == "0.1.0"

    def test_health_degraded_when_redis_unavailable(self, client):
        """Health check returns degraded when Redis is unreachable."""
        with patch(
            "margin_api.routes.health.aioredis.from_url",
            side_effect=ConnectionError("Redis down"),
        ):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["redis"] == "error"
        assert data["status"] == "degraded"


class TestProductionGuard:
    def setup_method(self):
        """Clear the settings cache before each test."""
        get_settings.cache_clear()

    def teardown_method(self):
        """Clear the settings cache after each test."""
        get_settings.cache_clear()

    def test_production_with_localhost_raises(self):
        with patch.dict(
            os.environ,
            {
                "MARGIN_ENVIRONMENT": "production",
                "MARGIN_DATABASE_URL": "postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest",
            },
        ):
            with pytest.raises(RuntimeError, match="local address"):
                create_app()

    def test_development_with_localhost_ok(self):
        with patch.dict(
            os.environ,
            {
                "MARGIN_ENVIRONMENT": "development",
                "MARGIN_DATABASE_URL": "postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest",
            },
        ):
            app = create_app()
            assert app is not None

    def test_production_with_ip_localhost_raises(self):
        with patch.dict(
            os.environ,
            {
                "MARGIN_ENVIRONMENT": "production",
                "MARGIN_DATABASE_URL": "postgresql+asyncpg://margin:pass@127.0.0.1:5432/db",
            },
        ):
            with pytest.raises(RuntimeError, match="local address"):
                create_app()

    def test_production_with_remote_url_ok(self):
        with patch.dict(
            os.environ,
            {
                "MARGIN_ENVIRONMENT": "production",
                "MARGIN_DATABASE_URL": "postgresql+asyncpg://user:pass@remote.host:5432/db?sslmode=require",
            },
        ):
            app = create_app()
            assert app is not None
