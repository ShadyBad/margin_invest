"""Database session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.config import get_settings

_engine = None
_session_factory = None


def get_engine(url: str | None = None):
    """Create or return the cached async SQLAlchemy engine."""
    global _engine
    if url is not None:
        # Explicit URL bypasses cache (used in tests)
        return create_async_engine(url, echo=False)
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, echo=False)
    return _engine


def get_session_factory(engine=None):
    """Create or return the cached async session factory."""
    global _session_factory
    if engine is not None:
        # Explicit engine bypasses cache (used in tests)
        return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields an async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
