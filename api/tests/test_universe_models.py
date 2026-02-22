"""Tests for pipeline database models.

Covers UniverseSnapshot, IngestionRun, IngestionTickerStatus,
JobRun, and Asset failure tracking.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import (
    Asset,
    IngestionRun,
    IngestionTickerStatus,
    JobRun,
    UniverseSnapshot,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


class TestUniverseSnapshot:
    @pytest.mark.asyncio
    async def test_create_snapshot(self, session: AsyncSession):
        snapshot = UniverseSnapshot(
            version="2026-02-15",
            config_hash="abc123" * 10 + "abcd",
            ticker_count=500,
            tickers=["AAPL", "MSFT", "GOOG"],
            exclusion_rules={"min_market_cap": 1_000_000_000},
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.commit()

        result = await session.execute(
            select(UniverseSnapshot).where(UniverseSnapshot.version == "2026-02-15")
        )
        found = result.scalar_one()
        assert found.ticker_count == 500
        assert found.tickers == ["AAPL", "MSFT", "GOOG"]
        assert found.is_active is True
        assert found.config_hash == "abc123" * 10 + "abcd"

    @pytest.mark.asyncio
    async def test_snapshot_table_name(self):
        assert UniverseSnapshot.__tablename__ == "universe_snapshots"

    @pytest.mark.asyncio
    async def test_snapshot_columns(self):
        columns = {c.name for c in UniverseSnapshot.__table__.columns}
        expected = {
            "id", "version", "config_hash", "ticker_count",
            "tickers", "exclusion_rules", "is_active", "activated_at",
        }
        assert expected.issubset(columns)


class TestIngestionRun:
    @pytest.mark.asyncio
    async def test_create_run_with_snapshot(self, session: AsyncSession):
        snapshot = UniverseSnapshot(
            version="2026-02-15",
            config_hash="hash123",
            ticker_count=3,
            tickers=["AAPL", "MSFT", "GOOG"],
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.flush()

        run = IngestionRun(
            snapshot_id=snapshot.id,
            run_type="full",
            tickers_requested=3,
            tickers_succeeded=2,
            tickers_failed=1,
            tickers_skipped=0,
            failed_tickers=["GOOG"],
            status="completed",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_seconds=45.2,
        )
        session.add(run)
        await session.commit()

        result = await session.execute(
            select(IngestionRun).where(IngestionRun.snapshot_id == snapshot.id)
        )
        found = result.scalar_one()
        assert found.run_type == "full"
        assert found.tickers_requested == 3
        assert found.tickers_succeeded == 2
        assert found.tickers_failed == 1
        assert found.failed_tickers == ["GOOG"]
        assert found.status == "completed"
        assert found.duration_seconds == pytest.approx(45.2)

    @pytest.mark.asyncio
    async def test_run_table_name(self):
        assert IngestionRun.__tablename__ == "ingestion_runs"

    @pytest.mark.asyncio
    async def test_run_columns(self):
        columns = {c.name for c in IngestionRun.__table__.columns}
        expected = {
            "id", "snapshot_id", "run_type", "tickers_requested",
            "tickers_succeeded", "tickers_failed", "tickers_skipped",
            "failed_tickers", "status", "started_at", "completed_at",
            "duration_seconds",
        }
        assert expected.issubset(columns)

    @pytest.mark.asyncio
    async def test_run_has_snapshot_fk(self):
        col = IngestionRun.__table__.columns["snapshot_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "universe_snapshots.id"


class TestIngestionTickerStatus:
    @pytest.mark.asyncio
    async def test_create_ticker_status(self, session: AsyncSession):
        snapshot = UniverseSnapshot(
            version="2026-02-15",
            config_hash="hash456",
            ticker_count=1,
            tickers=["AAPL"],
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.flush()

        run = IngestionRun(
            snapshot_id=snapshot.id,
            run_type="subset",
            tickers_requested=1,
            status="running",
            started_at=datetime.now(UTC),
        )
        session.add(run)
        await session.flush()

        ticker_status = IngestionTickerStatus(
            run_id=run.id,
            ticker="AAPL",
            status="succeeded",
            data_fetched={"income_statement": True, "balance_sheet": True},
            duration_ms=1200,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add(ticker_status)
        await session.commit()

        result = await session.execute(
            select(IngestionTickerStatus).where(IngestionTickerStatus.run_id == run.id)
        )
        found = result.scalar_one()
        assert found.ticker == "AAPL"
        assert found.status == "succeeded"
        assert found.duration_ms == 1200
        assert found.data_fetched == {"income_statement": True, "balance_sheet": True}

    @pytest.mark.asyncio
    async def test_ticker_status_with_error(self, session: AsyncSession):
        snapshot = UniverseSnapshot(
            version="2026-02-15",
            config_hash="hash789",
            ticker_count=1,
            tickers=["BAD"],
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.flush()

        run = IngestionRun(
            snapshot_id=snapshot.id,
            run_type="subset",
            tickers_requested=1,
            status="completed",
            started_at=datetime.now(UTC),
        )
        session.add(run)
        await session.flush()

        ticker_status = IngestionTickerStatus(
            run_id=run.id,
            ticker="BAD",
            status="failed",
            error_message="No data found for ticker BAD",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add(ticker_status)
        await session.commit()

        result = await session.execute(
            select(IngestionTickerStatus).where(IngestionTickerStatus.ticker == "BAD")
        )
        found = result.scalar_one()
        assert found.status == "failed"
        assert found.error_message == "No data found for ticker BAD"

    @pytest.mark.asyncio
    async def test_ticker_status_table_name(self):
        assert IngestionTickerStatus.__tablename__ == "ingestion_ticker_status"

    @pytest.mark.asyncio
    async def test_ticker_status_has_run_fk(self):
        col = IngestionTickerStatus.__table__.columns["run_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "ingestion_runs.id"


class TestJobRun:
    @pytest.mark.asyncio
    async def test_create_job_run(self, session: AsyncSession):
        job = JobRun(
            job_type="ingestion",
            status="completed",
            progress=100.0,
            progress_detail="Finished 500/500 tickers",
            triggered_by="schedule",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()

        result = await session.execute(
            select(JobRun).where(JobRun.job_type == "ingestion")
        )
        found = result.scalar_one()
        assert found.status == "completed"
        assert found.progress == pytest.approx(100.0)
        assert found.triggered_by == "schedule"
        assert found.progress_detail == "Finished 500/500 tickers"

    @pytest.mark.asyncio
    async def test_chained_job(self, session: AsyncSession):
        parent_job = JobRun(
            job_type="ingestion",
            status="completed",
            progress=100.0,
            triggered_by="schedule",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add(parent_job)
        await session.flush()

        child_job = JobRun(
            job_type="scoring",
            status="running",
            progress=50.0,
            triggered_by="chained",
            parent_job_id=parent_job.id,
            started_at=datetime.now(UTC),
        )
        session.add(child_job)
        await session.commit()

        result = await session.execute(
            select(JobRun).where(JobRun.parent_job_id == parent_job.id)
        )
        found = result.scalar_one()
        assert found.job_type == "scoring"
        assert found.triggered_by == "chained"
        assert found.parent_job_id == parent_job.id

    @pytest.mark.asyncio
    async def test_job_run_table_name(self):
        assert JobRun.__tablename__ == "job_runs"

    @pytest.mark.asyncio
    async def test_job_run_columns(self):
        columns = {c.name for c in JobRun.__table__.columns}
        expected = {
            "id", "job_type", "status", "progress", "progress_detail",
            "triggered_by", "parent_job_id", "error_message",
            "started_at", "completed_at",
        }
        assert expected.issubset(columns)

    @pytest.mark.asyncio
    async def test_job_run_self_referential_fk(self):
        col = JobRun.__table__.columns["parent_job_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "job_runs.id"


class TestAssetFailureTracking:
    @pytest.mark.asyncio
    async def test_default_ingestion_status(self, session: AsyncSession):
        asset = Asset(
            ticker="AAPL",
            name="Apple Inc",
            sector="Information Technology",
        )
        session.add(asset)
        await session.commit()

        result = await session.execute(
            select(Asset).where(Asset.ticker == "AAPL")
        )
        found = result.scalar_one()
        assert found.ingestion_status == "active"
        assert found.consecutive_failures == 0
        assert found.last_failure_reason is None
        assert found.quarantined_at is None
        assert found.last_retry_at is None

    @pytest.mark.asyncio
    async def test_quarantine_asset(self, session: AsyncSession):
        now = datetime.now(UTC)
        asset = Asset(
            ticker="BAD",
            name="Bad Corp",
            sector="Financials",
            ingestion_status="quarantined",
            consecutive_failures=5,
            last_failure_reason="API rate limit exceeded",
            quarantined_at=now,
            last_retry_at=now,
        )
        session.add(asset)
        await session.commit()

        result = await session.execute(
            select(Asset).where(Asset.ticker == "BAD")
        )
        found = result.scalar_one()
        assert found.ingestion_status == "quarantined"
        assert found.consecutive_failures == 5
        assert found.last_failure_reason == "API rate limit exceeded"
        assert found.quarantined_at is not None
        assert found.last_retry_at is not None

    @pytest.mark.asyncio
    async def test_asset_failure_columns_exist(self):
        columns = {c.name for c in Asset.__table__.columns}
        expected = {
            "ingestion_status", "consecutive_failures",
            "last_failure_reason", "quarantined_at", "last_retry_at",
        }
        assert expected.issubset(columns)
