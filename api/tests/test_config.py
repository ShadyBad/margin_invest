"""Tests for application configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

from margin_api.config import Settings


class TestSettings:
    def test_default_settings(self):
        settings = Settings()
        assert "postgresql" in settings.database_url
        assert "redis" in settings.redis_url
        assert settings.debug is False

    def test_cors_origins_default(self):
        settings = Settings()
        assert "http://localhost:3000" in settings.cors_origins

    def test_env_override(self):
        with patch.dict(os.environ, {"MARGIN_DEBUG": "true"}):
            settings = Settings()
            assert settings.debug is True

    def test_jwt_defaults(self):
        settings = Settings()
        assert settings.jwt_algorithm == "HS256"
        assert len(settings.jwt_secret) > 0
