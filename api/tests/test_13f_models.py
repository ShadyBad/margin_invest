"""Tests for 13F institutional holding models and CUSIP column on Asset."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import (
    AccumulationSignal,
    Asset,
    FilingMetadata,
    InstitutionalHolding,
    JobRun,
    Manager,
    SecurityMaster,
)
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload


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


def _make_manager(**overrides) -> Manager:
    defaults = dict(
        cik="0001364742",
        name="Berkshire Hathaway Inc",
        tier="top_aum",
        active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Manager(**defaults)


def _make_job_run(**overrides) -> JobRun:
    defaults = dict(
        job_type="full_13f_ingest",
        status="completed",
        progress=100.0,
        triggered_by="cli",
    )
    defaults.update(overrides)
    return JobRun(**defaults)


# ---------------------------------------------------------------------------
# Asset.cusip column
# ---------------------------------------------------------------------------


class TestAssetCusip:
    @pytest.mark.asyncio
    async def test_asset_cusip_nullable(self, db_session: AsyncSession):
        """Asset can be created without a cusip."""
        asset = _make_asset()
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        assert asset.cusip is None

    @pytest.mark.asyncio
    async def test_asset_cusip_stores_value(self, db_session: AsyncSession):
        """Asset.cusip stores a 9-character CUSIP."""
        asset = _make_asset(cusip="037833100")
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        assert asset.cusip == "037833100"

    @pytest.mark.asyncio
    async def test_asset_cusip_indexed(self, async_engine):
        """The cusip column on assets should have an index."""
        async with async_engine.connect() as conn:
            indexes = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_indexes("assets")
            )
        index_columns = [col for idx in indexes for col in idx["column_names"]]
        assert "cusip" in index_columns


# ---------------------------------------------------------------------------
# Manager model
# ---------------------------------------------------------------------------


class TestManager:
    @pytest.mark.asyncio
    async def test_create_manager_minimal(self, db_session: AsyncSession):
        mgr = _make_manager()
        db_session.add(mgr)
        await db_session.commit()
        await db_session.refresh(mgr)
        assert mgr.id is not None
        assert mgr.cik == "0001364742"
        assert mgr.tier == "top_aum"
        assert mgr.active is True

    @pytest.mark.asyncio
    async def test_manager_optional_fields(self, db_session: AsyncSession):
        mgr = _make_manager(
            short_name="BRK",
            aum_latest=800_000_000_000,
            first_filing_date=date(2000, 5, 15),
            last_filing_date=date(2025, 11, 14),
            metadata_json={"source": "sec"},
        )
        db_session.add(mgr)
        await db_session.commit()
        await db_session.refresh(mgr)
        assert mgr.short_name == "BRK"
        assert mgr.aum_latest == 800_000_000_000
        assert mgr.first_filing_date == date(2000, 5, 15)
        assert mgr.metadata_json == {"source": "sec"}

    @pytest.mark.asyncio
    async def test_manager_cik_unique(self, db_session: AsyncSession):
        db_session.add(_make_manager(cik="0001111111"))
        await db_session.commit()
        db_session.add(_make_manager(cik="0001111111", name="Duplicate"))
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_manager_filings_relationship(self, db_session: AsyncSession):
        mgr = _make_manager()
        db_session.add(mgr)
        await db_session.flush()

        filing = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000001",
            filing_type="13F-HR",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 11, 14),
            created_at=datetime.now(UTC),
        )
        db_session.add(filing)
        await db_session.commit()

        result = await db_session.execute(
            select(Manager).options(selectinload(Manager.filings)).where(Manager.id == mgr.id)
        )
        loaded_mgr = result.scalar_one()
        assert len(loaded_mgr.filings) == 1
        assert loaded_mgr.filings[0].accession_number == "0001364742-25-000001"


# ---------------------------------------------------------------------------
# SecurityMaster model
# ---------------------------------------------------------------------------


class TestSecurityMaster:
    @pytest.mark.asyncio
    async def test_create_security_master(self, db_session: AsyncSession):
        sm = SecurityMaster(
            cusip="037833100",
            issuer_name="APPLE INC",
            resolution_method="unresolved",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(sm)
        await db_session.commit()
        await db_session.refresh(sm)
        assert sm.id is not None
        assert sm.cusip == "037833100"
        assert sm.resolution_method == "unresolved"

    @pytest.mark.asyncio
    async def test_security_master_with_asset_link(self, db_session: AsyncSession):
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        sm = SecurityMaster(
            cusip="037833100",
            ticker="AAPL",
            issuer_name="APPLE INC",
            asset_id=asset.id,
            resolution_method="ticker_match",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(sm)
        await db_session.commit()
        await db_session.refresh(sm)
        assert sm.asset_id == asset.id
        assert sm.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_security_master_cusip_unique(self, db_session: AsyncSession):
        sm1 = SecurityMaster(
            cusip="037833100",
            issuer_name="APPLE INC",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(sm1)
        await db_session.commit()

        sm2 = SecurityMaster(
            cusip="037833100",
            issuer_name="Duplicate",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(sm2)
        with pytest.raises(Exception):
            await db_session.commit()


# ---------------------------------------------------------------------------
# FilingMetadata model
# ---------------------------------------------------------------------------


class TestFilingMetadata:
    @pytest.mark.asyncio
    async def test_create_filing(self, db_session: AsyncSession):
        mgr = _make_manager()
        db_session.add(mgr)
        await db_session.flush()

        filing = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000001",
            filing_type="13F-HR",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 11, 14),
            total_value=300_000_000,
            total_holdings=42,
            is_amendment=False,
            created_at=datetime.now(UTC),
        )
        db_session.add(filing)
        await db_session.commit()
        await db_session.refresh(filing)
        assert filing.id is not None
        assert filing.manager_id == mgr.id
        assert filing.period_of_report == date(2025, 9, 30)

    @pytest.mark.asyncio
    async def test_filing_accession_unique(self, db_session: AsyncSession):
        mgr = _make_manager()
        db_session.add(mgr)
        await db_session.flush()

        f1 = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000001",
            filing_type="13F-HR",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 11, 14),
            created_at=datetime.now(UTC),
        )
        db_session.add(f1)
        await db_session.commit()

        f2 = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000001",
            filing_type="13F-HR",
            period_of_report=date(2025, 12, 31),
            filed_date=date(2026, 2, 14),
            created_at=datetime.now(UTC),
        )
        db_session.add(f2)
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_filing_self_referential_supersedes(self, db_session: AsyncSession):
        mgr = _make_manager()
        db_session.add(mgr)
        await db_session.flush()

        original = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000001",
            filing_type="13F-HR",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 11, 14),
            created_at=datetime.now(UTC),
        )
        db_session.add(original)
        await db_session.flush()

        amendment = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000002",
            filing_type="13F-HR/A",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 12, 1),
            is_amendment=True,
            supersedes_id=original.id,
            created_at=datetime.now(UTC),
        )
        db_session.add(amendment)
        await db_session.commit()
        await db_session.refresh(amendment)
        assert amendment.supersedes_id == original.id

    @pytest.mark.asyncio
    async def test_filing_ingestion_run_fk(self, db_session: AsyncSession):
        mgr = _make_manager()
        job = _make_job_run()
        db_session.add_all([mgr, job])
        await db_session.flush()

        filing = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000003",
            filing_type="13F-HR",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 11, 14),
            ingestion_run_id=job.id,
            created_at=datetime.now(UTC),
        )
        db_session.add(filing)
        await db_session.commit()
        await db_session.refresh(filing)
        assert filing.ingestion_run_id == job.id

    @pytest.mark.asyncio
    async def test_filing_holdings_relationship(self, db_session: AsyncSession):
        mgr = _make_manager()
        db_session.add(mgr)
        await db_session.flush()

        filing = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000004",
            filing_type="13F-HR",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 11, 14),
            created_at=datetime.now(UTC),
        )
        db_session.add(filing)
        await db_session.flush()

        sm = SecurityMaster(
            cusip="037833100",
            issuer_name="APPLE INC",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(sm)
        await db_session.flush()

        holding = InstitutionalHolding(
            filing_id=filing.id,
            manager_id=mgr.id,
            security_master_id=sm.id,
            cusip="037833100",
            period_of_report=date(2025, 9, 30),
            shares_held=915_560_382,
            value_thousands=126_992_000,
            created_at=datetime.now(UTC),
        )
        db_session.add(holding)
        await db_session.commit()

        result = await db_session.execute(
            select(FilingMetadata)
            .options(selectinload(FilingMetadata.holdings))
            .where(FilingMetadata.id == filing.id)
        )
        loaded_filing = result.scalar_one()
        assert len(loaded_filing.holdings) == 1


# ---------------------------------------------------------------------------
# InstitutionalHolding model
# ---------------------------------------------------------------------------


class TestInstitutionalHolding:
    @pytest.mark.asyncio
    async def test_create_holding(self, db_session: AsyncSession):
        mgr = _make_manager()
        db_session.add(mgr)
        await db_session.flush()

        filing = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000005",
            filing_type="13F-HR",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 11, 14),
            created_at=datetime.now(UTC),
        )
        db_session.add(filing)
        await db_session.flush()

        sm = SecurityMaster(
            cusip="037833100",
            issuer_name="APPLE INC",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(sm)
        await db_session.flush()

        holding = InstitutionalHolding(
            filing_id=filing.id,
            manager_id=mgr.id,
            security_master_id=sm.id,
            cusip="037833100",
            period_of_report=date(2025, 9, 30),
            shares_held=915_560_382,
            value_thousands=126_992_000,
            put_call="NONE",
            investment_discretion="SOLE",
            voting_authority_sole=915_560_382,
            voting_authority_shared=0,
            voting_authority_none=0,
            created_at=datetime.now(UTC),
        )
        db_session.add(holding)
        await db_session.commit()
        await db_session.refresh(holding)
        assert holding.id is not None
        assert holding.shares_held == 915_560_382
        assert holding.put_call == "NONE"

    @pytest.mark.asyncio
    async def test_holding_unique_constraint(self, db_session: AsyncSession):
        """Same filing + cusip + put_call should violate unique constraint."""
        mgr = _make_manager()
        db_session.add(mgr)
        await db_session.flush()

        filing = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000006",
            filing_type="13F-HR",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 11, 14),
            created_at=datetime.now(UTC),
        )
        db_session.add(filing)
        await db_session.flush()

        sm = SecurityMaster(
            cusip="037833100",
            issuer_name="APPLE INC",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(sm)
        await db_session.flush()

        common = dict(
            filing_id=filing.id,
            manager_id=mgr.id,
            security_master_id=sm.id,
            cusip="037833100",
            period_of_report=date(2025, 9, 30),
            shares_held=100,
            value_thousands=10,
            put_call="NONE",
            created_at=datetime.now(UTC),
        )
        db_session.add(InstitutionalHolding(**common))
        await db_session.commit()

        db_session.add(InstitutionalHolding(**common))
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_holding_put_call_different_is_ok(self, db_session: AsyncSession):
        """Same filing+cusip but different put_call should be allowed."""
        mgr = _make_manager()
        db_session.add(mgr)
        await db_session.flush()

        filing = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001364742-25-000007",
            filing_type="13F-HR",
            period_of_report=date(2025, 9, 30),
            filed_date=date(2025, 11, 14),
            created_at=datetime.now(UTC),
        )
        db_session.add(filing)
        await db_session.flush()

        sm = SecurityMaster(
            cusip="037833100",
            issuer_name="APPLE INC",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(sm)
        await db_session.flush()

        base = dict(
            filing_id=filing.id,
            manager_id=mgr.id,
            security_master_id=sm.id,
            cusip="037833100",
            period_of_report=date(2025, 9, 30),
            shares_held=100,
            value_thousands=10,
            created_at=datetime.now(UTC),
        )
        db_session.add(InstitutionalHolding(**base, put_call="NONE"))
        db_session.add(InstitutionalHolding(**base, put_call="CALL"))
        db_session.add(InstitutionalHolding(**base, put_call="PUT"))
        await db_session.commit()

        result = await db_session.execute(select(InstitutionalHolding))
        holdings = result.scalars().all()
        assert len(holdings) == 3


# ---------------------------------------------------------------------------
# AccumulationSignal model
# ---------------------------------------------------------------------------


class TestAccumulationSignal:
    @pytest.mark.asyncio
    async def test_create_accumulation_signal(self, db_session: AsyncSession):
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        sig = AccumulationSignal(
            asset_id=asset.id,
            period_of_report=date(2025, 9, 30),
            curated_holders=15,
            total_holders=250,
            curated_new_positions=3,
            total_new_positions=40,
            curated_net_shares=500_000,
            total_net_shares=2_000_000,
            signal_score=0.72,
            computed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(sig)
        await db_session.commit()
        await db_session.refresh(sig)
        assert sig.id is not None
        assert sig.signal_score == 0.72
        assert sig.curated_holders == 15

    @pytest.mark.asyncio
    async def test_accumulation_signal_defaults(self, db_session: AsyncSession):
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        sig = AccumulationSignal(
            asset_id=asset.id,
            period_of_report=date(2025, 9, 30),
            computed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(sig)
        await db_session.commit()
        await db_session.refresh(sig)
        assert sig.curated_holders == 0
        assert sig.total_holders == 0
        assert sig.signal_score == 0.0

    @pytest.mark.asyncio
    async def test_accumulation_unique_asset_period(self, db_session: AsyncSession):
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        common = dict(
            asset_id=asset.id,
            period_of_report=date(2025, 9, 30),
            computed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(AccumulationSignal(**common))
        await db_session.commit()

        db_session.add(AccumulationSignal(**common))
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_accumulation_asset_relationship(self, db_session: AsyncSession):
        asset = _make_asset()
        db_session.add(asset)
        await db_session.flush()

        sig = AccumulationSignal(
            asset_id=asset.id,
            period_of_report=date(2025, 9, 30),
            computed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(sig)
        await db_session.commit()
        await db_session.refresh(sig)
        assert sig.asset is not None
        assert sig.asset.ticker == "AAPL"


# ---------------------------------------------------------------------------
# Schema / index checks
# ---------------------------------------------------------------------------


class TestSchemaConstraints:
    @pytest.mark.asyncio
    async def test_managers_table_exists(self, async_engine):
        async with async_engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        assert "managers" in tables

    @pytest.mark.asyncio
    async def test_security_master_table_exists(self, async_engine):
        async with async_engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        assert "security_master" in tables

    @pytest.mark.asyncio
    async def test_filing_metadata_table_exists(self, async_engine):
        async with async_engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        assert "filing_metadata" in tables

    @pytest.mark.asyncio
    async def test_institutional_holdings_table_exists(self, async_engine):
        async with async_engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        assert "institutional_holdings" in tables

    @pytest.mark.asyncio
    async def test_accumulation_signals_table_exists(self, async_engine):
        async with async_engine.connect() as conn:
            tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        assert "accumulation_signals" in tables

    @pytest.mark.asyncio
    async def test_filing_metadata_manager_period_index(self, async_engine):
        async with async_engine.connect() as conn:
            indexes = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_indexes("filing_metadata")
            )
        idx_names = [idx["name"] for idx in indexes]
        assert "ix_filing_manager_period" in idx_names

    @pytest.mark.asyncio
    async def test_holding_indexes_exist(self, async_engine):
        async with async_engine.connect() as conn:
            indexes = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_indexes("institutional_holdings")
            )
        idx_names = [idx["name"] for idx in indexes]
        assert "ix_holding_cusip_period" in idx_names
        assert "ix_holding_manager_period" in idx_names
        assert "ix_holding_secmaster_period" in idx_names
