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


class TestStripeSettings:
    def test_stripe_settings_exist(self):
        """Settings class has Stripe fields with empty defaults."""
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            mfa_encryption_key="",
        )
        assert s.stripe_secret_key == ""
        assert s.stripe_publishable_key == ""
        assert s.stripe_webhook_secret == ""
        assert s.stripe_portfolio_price_id == ""
        assert s.stripe_institutional_price_id == ""

    def test_api_key_encryption_key_exists(self):
        """Settings class has API key encryption field."""
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            mfa_encryption_key="",
        )
        assert s.api_key_encryption_key == ""

    def test_stripe_settings_from_env(self, monkeypatch):
        """Stripe settings load from MARGIN_-prefixed env vars."""
        monkeypatch.setenv("MARGIN_STRIPE_SECRET_KEY", "sk_test_123")
        monkeypatch.setenv("MARGIN_STRIPE_PUBLISHABLE_KEY", "pk_test_456")
        monkeypatch.setenv("MARGIN_STRIPE_WEBHOOK_SECRET", "whsec_789")
        monkeypatch.setenv("MARGIN_STRIPE_PORTFOLIO_PRICE_ID", "price_portfolio_abc")
        monkeypatch.setenv("MARGIN_STRIPE_INSTITUTIONAL_PRICE_ID", "price_institutional_def")
        monkeypatch.setenv("MARGIN_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        s = Settings()
        assert s.stripe_secret_key == "sk_test_123"
        assert s.stripe_publishable_key == "pk_test_456"
        assert s.stripe_webhook_secret == "whsec_789"
        assert s.stripe_portfolio_price_id == "price_portfolio_abc"
        assert s.stripe_institutional_price_id == "price_institutional_def"


class TestPoolSettings:
    def test_pool_defaults(self):
        settings = Settings()
        assert settings.db_pool_size == 5
        assert settings.db_max_overflow == 10
        assert settings.db_pool_timeout == 30
        assert settings.db_pool_recycle == 1800
        assert settings.db_pool_pre_ping is True

    def test_environment_default(self):
        settings = Settings()
        assert settings.environment == "development"

    def test_environment_from_env(self, monkeypatch):
        monkeypatch.setenv("MARGIN_ENVIRONMENT", "production")
        monkeypatch.setenv("MARGIN_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        settings = Settings()
        assert settings.environment == "production"

    def test_pool_size_from_env(self, monkeypatch):
        monkeypatch.setenv("MARGIN_DB_POOL_SIZE", "20")
        monkeypatch.setenv("MARGIN_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        settings = Settings()
        assert settings.db_pool_size == 20
