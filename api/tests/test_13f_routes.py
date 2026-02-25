"""Tests for 13F holdings API endpoints."""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import (
    AccumulationSignal,
    Asset,
    FilingMetadata,
    InstitutionalHolding,
    Manager,
    SecurityMaster,
)
from margin_api.db.session import get_db


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
async def seeded_db(db_session: AsyncSession):
    """Seed database with test data for holdings queries."""
    asset = Asset(
        ticker="AAPL",
        name="Apple Inc",
        sector="Technology",
        market_cap=Decimal("3000000000000"),
        cusip="037833100",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(asset)
    await db_session.commit()

    mgr1 = Manager(
        cik="0001067983",
        name="BERKSHIRE HATHAWAY",
        short_name="Berkshire",
        tier="curated",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mgr2 = Manager(
        cik="0001336528",
        name="BRIDGEWATER ASSOCIATES",
        short_name="Bridgewater",
        tier="top_aum",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add_all([mgr1, mgr2])
    await db_session.commit()

    sec = SecurityMaster(
        cusip="037833100",
        ticker="AAPL",
        issuer_name="APPLE INC",
        resolution_method="openfigi",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(sec)
    await db_session.commit()

    filing1 = FilingMetadata(
        manager_id=mgr1.id,
        accession_number="0001067983-26-000012",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
        created_at=datetime.now(UTC),
    )
    filing2 = FilingMetadata(
        manager_id=mgr2.id,
        accession_number="0001336528-26-000005",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        is_amendment=False,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([filing1, filing2])
    await db_session.commit()

    h1 = InstitutionalHolding(
        filing_id=filing1.id,
        manager_id=mgr1.id,
        security_master_id=sec.id,
        cusip="037833100",
        period_of_report=date(2025, 12, 31),
        shares_held=915560382,
        value_thousands=142300000,
        created_at=datetime.now(UTC),
    )
    h2 = InstitutionalHolding(
        filing_id=filing2.id,
        manager_id=mgr2.id,
        security_master_id=sec.id,
        cusip="037833100",
        period_of_report=date(2025, 12, 31),
        shares_held=50000000,
        value_thousands=7750000,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([h1, h2])
    await db_session.commit()

    signal = AccumulationSignal(
        asset_id=asset.id,
        period_of_report=date(2025, 12, 31),
        curated_holders=1,
        total_holders=2,
        curated_new_positions=0,
        total_new_positions=0,
        curated_net_shares=0,
        total_net_shares=0,
        signal_score=72.5,
        computed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(signal)
    await db_session.commit()

    return {
        "asset": asset,
        "mgr1": mgr1,
        "mgr2": mgr2,
        "sec": sec,
        "filing1": filing1,
        "filing2": filing2,
    }


@pytest_asyncio.fixture
async def client(db_session, seeded_db):
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_holdings(client):
    resp = await client.get("/api/v1/13f/holdings/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert len(data["curated_holders"]) == 1
    assert len(data["other_holders"]) == 1
    assert data["summary"]["total_holders"] == 2
    assert data["summary"]["curated_holders"] == 1


@pytest.mark.asyncio
async def test_get_holdings_curated_holder_details(client):
    resp = await client.get("/api/v1/13f/holdings/AAPL")
    data = resp.json()
    curated = data["curated_holders"][0]
    assert curated["manager_name"] == "Berkshire"
    assert curated["tier"] == "curated"
    assert curated["shares_held"] == 915560382
    assert curated["value_millions"] == 142300.0


@pytest.mark.asyncio
async def test_get_holdings_signal_score(client):
    resp = await client.get("/api/v1/13f/holdings/AAPL")
    data = resp.json()
    assert data["summary"]["signal_score"] == 72.5


@pytest.mark.asyncio
async def test_get_holdings_not_found(client):
    resp = await client.get("/api/v1/13f/holdings/ZZZZ")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_holders"] == 0


@pytest.mark.asyncio
async def test_get_holdings_history(client):
    resp = await client.get("/api/v1/13f/holdings/AAPL/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert len(data["quarters"]) >= 1
    quarter = data["quarters"][0]
    assert quarter["period"] == "2025-12-31"
    assert quarter["total_holders"] == 2
    assert quarter["curated_holders"] == 1


@pytest.mark.asyncio
async def test_get_holdings_history_empty(client):
    resp = await client.get("/api/v1/13f/holdings/ZZZZ/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "ZZZZ"
    assert len(data["quarters"]) == 0
