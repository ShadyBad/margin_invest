"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Values are loaded from environment variables. Use a .env file for local dev.
    """

    # Database
    database_url: str = "postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest"

    # Connection pool
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_pool_pre_ping: bool = True

    # Environment
    environment: str = "development"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Auth
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"

    # MFA
    mfa_encryption_key: str = ""
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "Margin Invest"
    webauthn_rp_origin: str = "http://localhost:3000"

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    # API Key encryption (separate from MFA encryption key)
    api_key_encryption_key: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # App
    debug: bool = False

    model_config = SettingsConfigDict(env_prefix="MARGIN_")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
