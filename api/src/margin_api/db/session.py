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
        settings = get_settings()
        connect_args: dict = {}
        engine_kwargs: dict = {"echo": False}

        # Pool parameters are only valid for non-SQLite backends
        # (SQLite uses StaticPool which rejects pool_size/max_overflow/pool_timeout)
        if not settings.database_url.startswith("sqlite"):
            engine_kwargs.update(
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=settings.db_pool_recycle,
                pool_pre_ping=settings.db_pool_pre_ping,
            )

        # asyncpg doesn't accept sslmode as a URL parameter —
        # strip it and pass SSL via connect_args instead.
        db_url = settings.database_url
        if "sslmode=require" in db_url:
            import ssl

            db_url = db_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
            ssl_ctx = ssl.create_default_context()
            # Railway (and many managed PG services) use self-signed certs
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ssl_ctx

        if connect_args:
            engine_kwargs["connect_args"] = connect_args

        _engine = create_async_engine(db_url, **engine_kwargs)
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


def reset_engine_cache() -> None:
    """Reset the cached engine and session factory globals.

    Call after engine.dispose() to allow recreation on next get_engine() call.
    Used by the ARQ worker where run_scoring/run_scoring_v3 dispose the engine
    but subsequent jobs need a fresh connection.
    """
    global _engine, _session_factory
    _engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields an async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
