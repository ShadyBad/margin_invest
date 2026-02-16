"""Tests for health check endpoint."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from margin_api.app import create_app
from margin_api.config import get_settings


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_includes_version(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "0.1.0"


class TestProductionGuard:
    def setup_method(self):
        """Clear the settings cache before each test."""
        get_settings.cache_clear()

    def teardown_method(self):
        """Clear the settings cache after each test."""
        get_settings.cache_clear()

    def test_production_with_localhost_raises(self):
        with patch.dict(os.environ, {
            "MARGIN_ENVIRONMENT": "production",
            "MARGIN_DATABASE_URL": "postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest",
        }):
            with pytest.raises(RuntimeError, match="local address"):
                create_app()

    def test_development_with_localhost_ok(self):
        with patch.dict(os.environ, {
            "MARGIN_ENVIRONMENT": "development",
            "MARGIN_DATABASE_URL": "postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest",
        }):
            app = create_app()
            assert app is not None

    def test_production_with_ip_localhost_raises(self):
        with patch.dict(os.environ, {
            "MARGIN_ENVIRONMENT": "production",
            "MARGIN_DATABASE_URL": "postgresql+asyncpg://margin:pass@127.0.0.1:5432/db",
        }):
            with pytest.raises(RuntimeError, match="local address"):
                create_app()

    def test_production_with_remote_url_ok(self):
        with patch.dict(os.environ, {
            "MARGIN_ENVIRONMENT": "production",
            "MARGIN_DATABASE_URL": "postgresql+asyncpg://user:pass@remote.host:5432/db?sslmode=require",
        }):
            app = create_app()
            assert app is not None
