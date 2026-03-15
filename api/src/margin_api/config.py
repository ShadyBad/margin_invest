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
    stripe_portfolio_price_id: str = ""
    stripe_institutional_price_id: str = ""

    # API Key encryption (separate from MFA encryption key)
    api_key_encryption_key: str = ""

    # Data providers
    polygon_api_key: str = ""
    fmp_api_key: str = ""
    finnhub_api_key: str = ""
    edgar_user_agent: str = ""

    # Email (Resend)
    resend_api_key: str = ""
    app_url: str = "http://localhost:3000"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Admin
    admin_key: str = ""

    # Rate limiting
    rate_limit_enabled: bool = True

    # Service-to-service auth
    service_auth_secret: str = ""
    require_signed_auth: bool = False

    # ML
    ml_artifact_dir: str = "ml_models"
    ml_train_min_samples: int = 100
    ml_n_clusters: int = 5
    vae_enable: bool = True
    ml_n_seeds: int = 20
    ml_bootstrap_mode: bool = True  # Use relaxed IC gates for PIT-bootstrapped training
    ml_live_weight: float = 0.0  # Blend weight for live data (0.0 = all historical, 1.0 = all live)

    # Batched ingest
    ingest_batch_size: int = 50
    ingest_rate_limit: int = 36
    ingest_concurrency: int = 3

    # App
    debug: bool = False

    model_config = SettingsConfigDict(
        env_prefix="MARGIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
