"""Database session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.config import get_settings


def get_engine(url: str | None = None):
    """Create an async SQLAlchemy engine."""
    database_url = url or get_settings().database_url
    return create_async_engine(database_url, echo=False)


def get_session_factory(engine=None):
    """Create an async session factory."""
    if engine is None:
        engine = get_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields an async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
