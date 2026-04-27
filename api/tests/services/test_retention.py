"""Tests for retention policies — purge_job_runs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import JobRun
from margin_api.services.retention import purge_job_runs
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Async DB fixtures (SQLite in-memory for speed)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_job_runs_deletes_rows_older_than_cutoff(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    old_run = JobRun(
        job_type="full_score",
        status="completed",
        triggered_by="schedule",
        started_at=now - timedelta(days=45),
        completed_at=now - timedelta(days=45),
    )
    fresh_run = JobRun(
        job_type="full_score",
        status="completed",
        triggered_by="schedule",
        started_at=now - timedelta(days=5),
        completed_at=now - timedelta(days=5),
    )
    session.add(old_run)
    session.add(fresh_run)
    await session.flush()

    deleted = await purge_job_runs(session, days=30)

    assert deleted == 1
    remaining = (await session.execute(select(JobRun))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == fresh_run.id


@pytest.mark.asyncio
async def test_purge_job_runs_with_no_old_rows_returns_zero(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    fresh_run = JobRun(
        job_type="full_score",
        status="completed",
        triggered_by="chained",
        started_at=now - timedelta(days=1),
        completed_at=now - timedelta(days=1),
    )
    session.add(fresh_run)
    await session.flush()

    deleted = await purge_job_runs(session, days=30)

    assert deleted == 0
    remaining = (await session.execute(select(JobRun))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == fresh_run.id
