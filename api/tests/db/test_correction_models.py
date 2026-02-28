"""Tests for CorrectionEventRecord and SectorDistributionSnapshot DB models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import (
    Asset,
    CorrectionEventRecord,
    SectorDistributionSnapshot,
)
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_asset(**overrides) -> Asset:
    defaults = dict(
        ticker="AAPL",
        name="Apple Inc",
        sector="Technology",
        market_cap=3_000_000_000_000,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Asset(**defaults)


def _make_correction_event(**overrides) -> CorrectionEventRecord:
    defaults = dict(
        correction_id="corr-001",
        asset_id=1,
        period_end="2025-12-31",
        field_path="income_statement.revenue",
        detection_tier="tier_1",
        detection_detail="Revenue is negative for non-financial company",
        original_value=-1_000_000.0,
        corrected_value=1_000_000.0,
        correction_method="median_replace",
        correction_source="sector_median",
        correction_confidence=0.85,
        correction_config_version="1.0.0",
        sector_distribution_snapshot=None,
        scoring_run_id=None,
    )
    defaults.update(overrides)
    return CorrectionEventRecord(**defaults)


def _make_sector_snapshot(**overrides) -> SectorDistributionSnapshot:
    defaults = dict(
        scoring_run_id="run-001",
        sector="Technology",
        field_path="income_statement.revenue",
        median=5_000_000.0,
        mad=1_200_000.0,
        n_observations=45,
        period="2025-12-31",
    )
    defaults.update(overrides)
    return SectorDistributionSnapshot(**defaults)


# ---------------------------------------------------------------------------
# CorrectionEventRecord model
# ---------------------------------------------------------------------------


class TestCorrectionEventRecord:
    @pytest.mark.asyncio
    async def test_create_correction_event(self, db_session: AsyncSession):
        """CorrectionEventRecord can be created, committed, and queried back."""
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        event = _make_correction_event(asset_id=asset.id)
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        assert event.id is not None
        assert event.correction_id == "corr-001"
        assert event.field_path == "income_statement.revenue"
        assert event.detection_tier == "tier_1"
        assert event.original_value == -1_000_000.0
        assert event.corrected_value == 1_000_000.0
        assert event.correction_method == "median_replace"
        assert event.correction_source == "sector_median"
        assert event.correction_confidence == 0.85
        assert event.correction_config_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_correction_event_unique_correction_id(self, db_session: AsyncSession):
        """Duplicate correction_id should violate unique constraint."""
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        event1 = _make_correction_event(asset_id=asset.id, correction_id="dup-id")
        db_session.add(event1)
        await db_session.commit()

        event2 = _make_correction_event(asset_id=asset.id, correction_id="dup-id")
        db_session.add(event2)
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_correction_event_nullable_original_value(self, db_session: AsyncSession):
        """original_value can be None (e.g., missing data corrected from nothing)."""
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        event = _make_correction_event(
            asset_id=asset.id,
            correction_id="corr-null-orig",
            original_value=None,
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)
        assert event.original_value is None

    @pytest.mark.asyncio
    async def test_correction_event_json_snapshot(self, db_session: AsyncSession):
        """sector_distribution_snapshot stores and round-trips JSON."""
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        snapshot = {"median": 5000000.0, "mad": 1200000.0, "n": 45}
        event = _make_correction_event(
            asset_id=asset.id,
            correction_id="corr-json",
            sector_distribution_snapshot=snapshot,
        )
        db_session.add(event)
        await db_session.commit()

        result = await db_session.execute(
            select(CorrectionEventRecord).where(CorrectionEventRecord.correction_id == "corr-json")
        )
        loaded = result.scalar_one()
        assert loaded.sector_distribution_snapshot == snapshot
        assert loaded.sector_distribution_snapshot["median"] == 5000000.0

    @pytest.mark.asyncio
    async def test_correction_event_scoring_run_id_nullable(self, db_session: AsyncSession):
        """scoring_run_id is optional."""
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        event = _make_correction_event(
            asset_id=asset.id,
            correction_id="corr-no-run",
            scoring_run_id=None,
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)
        assert event.scoring_run_id is None

    @pytest.mark.asyncio
    async def test_correction_event_created_at_defaults(self, db_session: AsyncSession):
        """created_at should default to approximately now."""
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        before = datetime.now(UTC)
        event = _make_correction_event(asset_id=asset.id, correction_id="corr-ts")
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)
        after = datetime.now(UTC)
        assert before <= event.created_at.replace(tzinfo=UTC) <= after

    @pytest.mark.asyncio
    async def test_correction_event_asset_fk(self, db_session: AsyncSession):
        """asset_id must reference a valid asset row."""
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        event = _make_correction_event(asset_id=asset.id, correction_id="corr-fk")
        db_session.add(event)
        await db_session.commit()

        result = await db_session.execute(
            select(CorrectionEventRecord).where(CorrectionEventRecord.correction_id == "corr-fk")
        )
        loaded = result.scalar_one()
        assert loaded.asset_id == asset.id


# ---------------------------------------------------------------------------
# SectorDistributionSnapshot model
# ---------------------------------------------------------------------------


class TestSectorDistributionSnapshot:
    @pytest.mark.asyncio
    async def test_create_sector_distribution_snapshot(self, db_session: AsyncSession):
        """SectorDistributionSnapshot can be created, committed, and queried back."""
        snapshot = _make_sector_snapshot()
        db_session.add(snapshot)
        await db_session.commit()
        await db_session.refresh(snapshot)

        assert snapshot.id is not None
        assert snapshot.scoring_run_id == "run-001"
        assert snapshot.sector == "Technology"
        assert snapshot.field_path == "income_statement.revenue"
        assert snapshot.median == 5_000_000.0
        assert snapshot.mad == 1_200_000.0
        assert snapshot.n_observations == 45
        assert snapshot.period == "2025-12-31"

    @pytest.mark.asyncio
    async def test_sector_snapshot_created_at_defaults(self, db_session: AsyncSession):
        """created_at should default to approximately now."""
        before = datetime.now(UTC)
        snapshot = _make_sector_snapshot(scoring_run_id="run-ts")
        db_session.add(snapshot)
        await db_session.commit()
        await db_session.refresh(snapshot)
        after = datetime.now(UTC)
        assert before <= snapshot.created_at.replace(tzinfo=UTC) <= after

    @pytest.mark.asyncio
    async def test_sector_snapshot_multiple_per_run(self, db_session: AsyncSession):
        """Multiple snapshots can exist for the same scoring_run_id."""
        s1 = _make_sector_snapshot(
            scoring_run_id="run-multi",
            sector="Technology",
            field_path="income_statement.revenue",
        )
        s2 = _make_sector_snapshot(
            scoring_run_id="run-multi",
            sector="Healthcare",
            field_path="income_statement.revenue",
        )
        s3 = _make_sector_snapshot(
            scoring_run_id="run-multi",
            sector="Technology",
            field_path="balance_sheet.total_assets",
        )
        db_session.add_all([s1, s2, s3])
        await db_session.commit()

        result = await db_session.execute(
            select(SectorDistributionSnapshot).where(
                SectorDistributionSnapshot.scoring_run_id == "run-multi"
            )
        )
        snapshots = result.scalars().all()
        assert len(snapshots) == 3

    @pytest.mark.asyncio
    async def test_sector_snapshot_query_by_sector(self, db_session: AsyncSession):
        """Can query snapshots by sector."""
        s1 = _make_sector_snapshot(scoring_run_id="run-q", sector="Technology")
        s2 = _make_sector_snapshot(scoring_run_id="run-q", sector="Healthcare")
        db_session.add_all([s1, s2])
        await db_session.commit()

        result = await db_session.execute(
            select(SectorDistributionSnapshot).where(
                SectorDistributionSnapshot.sector == "Technology"
            )
        )
        snapshots = result.scalars().all()
        assert len(snapshots) == 1
        assert snapshots[0].sector == "Technology"


# ---------------------------------------------------------------------------
# Schema / index checks
# ---------------------------------------------------------------------------


class TestCorrectionSchemaConstraints:
    @pytest.mark.asyncio
    async def test_correction_events_table_exists(self, async_engine):
        async with async_engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "correction_events" in tables

    @pytest.mark.asyncio
    async def test_sector_distribution_snapshots_table_exists(self, async_engine):
        async with async_engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        assert "sector_distribution_snapshots" in tables

    @pytest.mark.asyncio
    async def test_correction_events_correction_id_indexed(self, async_engine):
        async with async_engine.connect() as conn:
            indexes = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_indexes("correction_events")
            )
        index_columns = [col for idx in indexes for col in idx["column_names"]]
        assert "correction_id" in index_columns

    @pytest.mark.asyncio
    async def test_correction_events_asset_id_indexed(self, async_engine):
        async with async_engine.connect() as conn:
            indexes = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_indexes("correction_events")
            )
        index_columns = [col for idx in indexes for col in idx["column_names"]]
        assert "asset_id" in index_columns

    @pytest.mark.asyncio
    async def test_sector_snapshots_scoring_run_id_indexed(self, async_engine):
        async with async_engine.connect() as conn:
            indexes = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_indexes("sector_distribution_snapshots")
            )
        index_columns = [col for idx in indexes for col in idx["column_names"]]
        assert "scoring_run_id" in index_columns
