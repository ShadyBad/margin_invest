"""Tests for 13F ingestion service."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import (
    FilingMetadata,
    InstitutionalHolding,
    Manager,
    SecurityMaster,
)
from margin_api.services.thirteenf_ingest import ThirteenFIngestService
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


@pytest.mark.asyncio
async def test_upsert_managers(db_session: AsyncSession):
    """Seed managers from a list of fund dicts."""
    service = ThirteenFIngestService(db_session)
    funds = [
        {
            "cik": "0001067983",
            "name": "BERKSHIRE HATHAWAY INC",
            "short_name": "Berkshire Hathaway",
            "tier": "curated",
        },
        {
            "cik": "0001061768",
            "name": "BAUPOST GROUP LLC",
            "short_name": "Baupost Group",
            "tier": "curated",
        },
    ]
    await service.upsert_managers(funds)
    result = await db_session.execute(select(Manager))
    managers = result.scalars().all()
    assert len(managers) == 2
    assert managers[0].cik == "0001067983"


@pytest.mark.asyncio
async def test_upsert_managers_idempotent(db_session: AsyncSession):
    """Upserting same managers twice doesn't create duplicates."""
    service = ThirteenFIngestService(db_session)
    funds = [
        {"cik": "0001067983", "name": "BERKSHIRE", "short_name": "Berkshire", "tier": "curated"}
    ]
    await service.upsert_managers(funds)
    await service.upsert_managers(funds)
    result = await db_session.execute(select(Manager))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_upsert_managers_updates_existing(db_session: AsyncSession):
    """Upserting a manager with updated name reflects the change."""
    service = ThirteenFIngestService(db_session)
    funds = [{"cik": "0001067983", "name": "BERKSHIRE OLD", "short_name": "BH", "tier": "curated"}]
    await service.upsert_managers(funds)

    funds[0]["name"] = "BERKSHIRE HATHAWAY INC"
    await service.upsert_managers(funds)

    result = await db_session.execute(select(Manager))
    managers = result.scalars().all()
    assert len(managers) == 1
    assert managers[0].name == "BERKSHIRE HATHAWAY INC"


@pytest.mark.asyncio
async def test_skip_already_ingested_filing(db_session: AsyncSession):
    """Filings with known accession numbers are skipped."""
    service = ThirteenFIngestService(db_session)
    mgr = Manager(
        cik="0001067983",
        name="BERKSHIRE",
        short_name="Berkshire",
        tier="curated",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(mgr)
    await db_session.commit()

    filing = FilingMetadata(
        manager_id=mgr.id,
        accession_number="0001067983-26-000012",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
    )
    db_session.add(filing)
    await db_session.commit()

    is_new = await service.is_filing_new("0001067983-26-000012")
    assert is_new is False


@pytest.mark.asyncio
async def test_new_filing_detected(db_session: AsyncSession):
    """Unknown accession numbers are detected as new."""
    service = ThirteenFIngestService(db_session)
    is_new = await service.is_filing_new("0001067983-26-999999")
    assert is_new is True


@pytest.mark.asyncio
async def test_store_holdings(db_session: AsyncSession):
    """Parsed holdings are stored correctly."""
    service = ThirteenFIngestService(db_session)
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
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add_all([mgr, sec])
    await db_session.commit()

    filing = FilingMetadata(
        manager_id=mgr.id,
        accession_number="0001067983-26-000012",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
    )
    db_session.add(filing)
    await db_session.commit()

    parsed_holdings = [
        {
            "cusip": "037833100",
            "issuer_name": "APPLE INC",
            "shares": 915560382,
            "value_thousands": 142300000,
            "put_call": "NONE",
            "investment_discretion": "SOLE",
            "voting_sole": 915560382,
            "voting_shared": 0,
            "voting_none": 0,
        }
    ]
    count = await service.store_holdings(filing, mgr, parsed_holdings)
    assert count == 1

    result = await db_session.execute(select(InstitutionalHolding))
    holding = result.scalar_one()
    assert holding.shares_held == 915560382
    assert holding.cusip == "037833100"


@pytest.mark.asyncio
async def test_get_or_create_security_existing(db_session: AsyncSession):
    """get_or_create_security returns existing security by CUSIP."""
    service = ThirteenFIngestService(db_session)
    sec = SecurityMaster(
        cusip="037833100",
        issuer_name="APPLE INC",
        resolution_method="openfigi",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(sec)
    await db_session.commit()

    result = await service.get_or_create_security("037833100", "APPLE INC")
    assert result.id == sec.id


@pytest.mark.asyncio
async def test_get_or_create_security_new(db_session: AsyncSession):
    """get_or_create_security creates new security if CUSIP not found."""
    service = ThirteenFIngestService(db_session)
    result = await service.get_or_create_security("594918104", "MSFT")
    assert result.cusip == "594918104"
    assert result.resolution_method == "unresolved"


@pytest.mark.asyncio
async def test_handle_amendment_finds_original(db_session: AsyncSession):
    """handle_amendment returns original filing id for an amendment."""
    service = ThirteenFIngestService(db_session)
    mgr = Manager(
        cik="0001067983",
        name="BERKSHIRE",
        short_name="Berkshire",
        tier="curated",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(mgr)
    await db_session.commit()

    original = FilingMetadata(
        manager_id=mgr.id,
        accession_number="0001067983-26-000010",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
    )
    db_session.add(original)
    await db_session.commit()

    result = await service.handle_amendment(mgr, date(2025, 12, 31), "0001067983-26-000015")
    assert result == original.id


@pytest.mark.asyncio
async def test_handle_amendment_returns_none_when_no_original(db_session: AsyncSession):
    """handle_amendment returns None when no original filing exists."""
    service = ThirteenFIngestService(db_session)
    mgr = Manager(
        cik="0001067983",
        name="BERKSHIRE",
        short_name="Berkshire",
        tier="curated",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(mgr)
    await db_session.commit()

    result = await service.handle_amendment(mgr, date(2025, 12, 31), "0001067983-26-000015")
    assert result is None
