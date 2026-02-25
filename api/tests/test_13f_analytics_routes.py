"""Tests for 13F analytics API endpoints."""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import (
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
    """Seed data for analytics queries -- multiple managers holding overlapping tickers."""
    # Create managers
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
        tier="curated",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mgr3 = Manager(
        cik="0001061768",
        name="BAUPOST GROUP",
        short_name="Baupost",
        tier="top_aum",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add_all([mgr1, mgr2, mgr3])
    await db_session.commit()

    # Securities
    sec_aapl = SecurityMaster(
        cusip="037833100",
        ticker="AAPL",
        issuer_name="APPLE INC",
        resolution_method="openfigi",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    sec_msft = SecurityMaster(
        cusip="594918104",
        ticker="MSFT",
        issuer_name="MICROSOFT CORP",
        resolution_method="openfigi",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    sec_goog = SecurityMaster(
        cusip="02079K305",
        ticker="GOOG",
        issuer_name="ALPHABET INC",
        resolution_method="openfigi",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add_all([sec_aapl, sec_msft, sec_goog])
    await db_session.commit()

    # Filings for each manager
    f1 = FilingMetadata(
        manager_id=mgr1.id,
        accession_number="acc-1",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        total_value=200000000,
        total_holdings=2,
        is_amendment=False,
        created_at=datetime.now(UTC),
    )
    f2 = FilingMetadata(
        manager_id=mgr2.id,
        accession_number="acc-2",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        total_value=100000000,
        total_holdings=2,
        is_amendment=False,
        created_at=datetime.now(UTC),
    )
    f3 = FilingMetadata(
        manager_id=mgr3.id,
        accession_number="acc-3",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        total_value=50000000,
        total_holdings=1,
        is_amendment=False,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([f1, f2, f3])
    await db_session.commit()

    # Holdings: AAPL held by all 3, MSFT by 2, GOOG by 1 (not seeded here)
    holdings = [
        InstitutionalHolding(
            filing_id=f1.id,
            manager_id=mgr1.id,
            security_master_id=sec_aapl.id,
            cusip="037833100",
            period_of_report=date(2025, 12, 31),
            shares_held=100000,
            value_thousands=15000,
            created_at=datetime.now(UTC),
        ),
        InstitutionalHolding(
            filing_id=f1.id,
            manager_id=mgr1.id,
            security_master_id=sec_msft.id,
            cusip="594918104",
            period_of_report=date(2025, 12, 31),
            shares_held=50000,
            value_thousands=10000,
            created_at=datetime.now(UTC),
        ),
        InstitutionalHolding(
            filing_id=f2.id,
            manager_id=mgr2.id,
            security_master_id=sec_aapl.id,
            cusip="037833100",
            period_of_report=date(2025, 12, 31),
            shares_held=80000,
            value_thousands=12000,
            created_at=datetime.now(UTC),
        ),
        InstitutionalHolding(
            filing_id=f2.id,
            manager_id=mgr2.id,
            security_master_id=sec_msft.id,
            cusip="594918104",
            period_of_report=date(2025, 12, 31),
            shares_held=30000,
            value_thousands=6000,
            created_at=datetime.now(UTC),
        ),
        InstitutionalHolding(
            filing_id=f3.id,
            manager_id=mgr3.id,
            security_master_id=sec_aapl.id,
            cusip="037833100",
            period_of_report=date(2025, 12, 31),
            shares_held=20000,
            value_thousands=3000,
            created_at=datetime.now(UTC),
        ),
    ]
    db_session.add_all(holdings)
    await db_session.commit()

    return {"mgr1": mgr1, "mgr2": mgr2, "mgr3": mgr3}


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
async def test_overlap(client):
    resp = await client.get("/api/v1/13f/analytics/overlap")
    assert resp.status_code == 200
    data = resp.json()
    assert "most_held" in data
    assert "crowded_trades" in data
    # AAPL held by 3, MSFT by 2
    tickers = {e["ticker"] for e in data["most_held"]}
    assert "AAPL" in tickers
    # AAPL should be first (most holders)
    assert data["most_held"][0]["ticker"] == "AAPL"
    assert data["most_held"][0]["holder_count"] == 3
    # 2 of the 3 are curated
    assert data["most_held"][0]["curated_count"] == 2


@pytest.mark.asyncio
async def test_new_positions(client):
    resp = await client.get("/api/v1/13f/analytics/new-positions")
    assert resp.status_code == 200
    data = resp.json()
    assert "new_positions" in data


@pytest.mark.asyncio
async def test_clone_portfolio(client, seeded_db):
    mgr_id = seeded_db["mgr1"].id
    resp = await client.get(f"/api/v1/13f/analytics/clone/{mgr_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["manager"] == "Berkshire"
    assert len(data["positions"]) > 0
    # Weights should sum to ~100
    total = sum(p["target_weight"] for p in data["positions"])
    assert 99.0 <= total <= 101.0


@pytest.mark.asyncio
async def test_clone_manager_not_found(client):
    resp = await client.get("/api/v1/13f/analytics/clone/99999")
    assert resp.status_code == 404
