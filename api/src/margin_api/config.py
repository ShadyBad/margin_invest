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

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Auth
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # App
    debug: bool = False

    model_config = SettingsConfigDict(env_prefix="MARGIN_")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
