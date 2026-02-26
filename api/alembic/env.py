"""Alembic environment configuration for async SQLAlchemy."""

from __future__ import annotations

import asyncio

# Import all models so they register with Base.metadata
import margin_api.db.models  # noqa: F401
from alembic import context
from margin_api.config import get_settings
from margin_api.db.base import Base
from sqlalchemy.ext.asyncio import create_async_engine

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode -- emit SQL without connecting."""
    url = get_settings().database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    url = get_settings().database_url
    connect_args: dict = {}

    # asyncpg doesn't accept sslmode as a URL parameter —
    # strip it and pass SSL via connect_args instead.
    if "sslmode=require" in url:
        from margin_api.db.ssl import create_pg_ssl_context

        url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
        connect_args["ssl"] = create_pg_ssl_context()

    engine = create_async_engine(url, connect_args=connect_args)
    async with engine.begin() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
