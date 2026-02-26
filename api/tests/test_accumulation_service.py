"""Tests for accumulation signal computation service (DB layer)."""
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
    Manager,
    SecurityMaster,
)
from margin_api.services.accumulation_service import AccumulationService
from sqlalchemy import select
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


@pytest_asyncio.fixture
async def seeded_data(db_session: AsyncSession):
    """Seed two quarters of holdings for one asset by one curated fund."""
    asset = Asset(
        ticker="AAPL",
        name="Apple Inc",
        sector="Technology",
        cusip="037833100",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mgr = Manager(
        cik="0001067983",
        name="BERKSHIRE",
        short_name="Berkshire",
        tier="curated",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    sec = SecurityMaster(
        cusip="037833100",
        issuer_name="APPLE INC",
        resolution_method="openfigi",
        ticker="AAPL",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add_all([asset, mgr, sec])
    await db_session.commit()

    # Q3 filing
    f1 = FilingMetadata(
        manager_id=mgr.id,
        accession_number="acc-q3",
        filing_type="13F-HR",
        period_of_report=date(2025, 9, 30),
        filed_date=date(2025, 11, 14),
        is_amendment=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(f1)
    await db_session.commit()
    db_session.add(
        InstitutionalHolding(
            filing_id=f1.id,
            manager_id=mgr.id,
            security_master_id=sec.id,
            cusip="037833100",
            period_of_report=date(2025, 9, 30),
            shares_held=900_000_000,
            value_thousands=130_000_000,
            put_call="NONE",
            created_at=datetime.now(UTC),
        )
    )
    # Q4 filing
    f2 = FilingMetadata(
        manager_id=mgr.id,
        accession_number="acc-q4",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(f2)
    await db_session.commit()
    db_session.add(
        InstitutionalHolding(
            filing_id=f2.id,
            manager_id=mgr.id,
            security_master_id=sec.id,
            cusip="037833100",
            period_of_report=date(2025, 12, 31),
            shares_held=915_000_000,
            value_thousands=142_000_000,
            put_call="NONE",
            created_at=datetime.now(UTC),
        )
    )
    await db_session.commit()
    return {"asset": asset, "sec": sec, "mgr": mgr}


@pytest.mark.asyncio
async def test_compute_signals_for_quarter(db_session: AsyncSession, seeded_data):
    service = AccumulationService(db_session)
    count = await service.compute_signals(period_of_report=date(2025, 12, 31))
    assert count == 1

    result = await db_session.execute(
        select(AccumulationSignal).where(
            AccumulationSignal.period_of_report == date(2025, 12, 31)
        )
    )
    signal = result.scalar_one()
    assert signal.curated_holders == 1
    assert signal.total_holders == 1
    assert signal.curated_new_positions == 0  # existed in Q3
    assert signal.curated_net_shares == 15_000_000  # 915M - 900M


@pytest.mark.asyncio
async def test_compute_signals_idempotent(db_session: AsyncSession, seeded_data):
    """Running twice updates rather than duplicates."""
    service = AccumulationService(db_session)
    await service.compute_signals(period_of_report=date(2025, 12, 31))
    await service.compute_signals(period_of_report=date(2025, 12, 31))
    result = await db_session.execute(
        select(AccumulationSignal).where(
            AccumulationSignal.period_of_report == date(2025, 12, 31)
        )
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_new_position_detected(db_session: AsyncSession, seeded_data):
    """Q3 is a new position (no previous quarter data)."""
    service = AccumulationService(db_session)
    count = await service.compute_signals(period_of_report=date(2025, 9, 30))
    assert count == 1

    result = await db_session.execute(
        select(AccumulationSignal).where(
            AccumulationSignal.period_of_report == date(2025, 9, 30)
        )
    )
    signal = result.scalar_one()
    assert signal.curated_new_positions == 1  # no Q2 data = new position
    assert signal.curated_net_shares == 900_000_000


@pytest.mark.asyncio
async def test_empty_quarter(db_session: AsyncSession):
    """No holdings for a quarter produces no signals."""
    service = AccumulationService(db_session)
    count = await service.compute_signals(period_of_report=date(2020, 3, 31))
    assert count == 0
