"""Tests for 13F manager API endpoints."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import (
    FilingMetadata,
    InstitutionalHolding,
    Manager,
    SecurityMaster,
    User,
)
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
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
async def seeded_db(db_session: AsyncSession):
    """Seed test data for manager queries."""
    # Create a test user with institutional plan for auth gating
    test_user = User(
        email="test@test.com",
        name="Test User",
        subscription_plan="institutional",
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

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

    sec1 = SecurityMaster(
        cusip="037833100",
        ticker="AAPL",
        issuer_name="APPLE INC",
        resolution_method="openfigi",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    sec2 = SecurityMaster(
        cusip="594918104",
        ticker="MSFT",
        issuer_name="MICROSOFT CORP",
        resolution_method="openfigi",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add_all([sec1, sec2])
    await db_session.commit()

    filing1 = FilingMetadata(
        manager_id=mgr1.id,
        accession_number="0001067983-26-000012",
        filing_type="13F-HR",
        period_of_report=date(2025, 12, 31),
        filed_date=date(2026, 2, 14),
        total_value=200000000,
        total_holdings=2,
        is_amendment=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(filing1)
    await db_session.commit()

    h1 = InstitutionalHolding(
        filing_id=filing1.id,
        manager_id=mgr1.id,
        security_master_id=sec1.id,
        cusip="037833100",
        period_of_report=date(2025, 12, 31),
        shares_held=915560382,
        value_thousands=142300000,
        created_at=datetime.now(UTC),
    )
    h2 = InstitutionalHolding(
        filing_id=filing1.id,
        manager_id=mgr1.id,
        security_master_id=sec2.id,
        cusip="594918104",
        period_of_report=date(2025, 12, 31),
        shares_held=50000000,
        value_thousands=57700000,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([h1, h2])
    await db_session.commit()

    return {"mgr1": mgr1, "mgr2": mgr2, "filing1": filing1, "user": test_user}


@pytest_asyncio.fixture
async def client(db_session, seeded_db):
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: seeded_db["user"].id
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_managers(client):
    resp = await client.get("/api/v1/13f/managers")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_managers_filter_by_tier(client):
    resp = await client.get("/api/v1/13f/managers?tier=curated")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tier"] == "curated"


@pytest.mark.asyncio
async def test_list_managers_ordered_by_name(client):
    resp = await client.get("/api/v1/13f/managers")
    assert resp.status_code == 200
    data = resp.json()
    names = [m["name"] for m in data]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_list_managers_includes_filing_data(client, seeded_db):
    resp = await client.get("/api/v1/13f/managers?tier=curated")
    assert resp.status_code == 200
    data = resp.json()
    mgr = data[0]
    assert mgr["name"] == "Berkshire"
    assert mgr["total_holdings"] == 2
    assert mgr["aum_millions"] is not None
    assert mgr["last_filing"] == "2026-02-14"
    assert mgr["period_of_report"] == "2025-12-31"
    assert len(mgr["top_positions"]) == 2


@pytest.mark.asyncio
async def test_list_managers_no_filing_data(client, seeded_db):
    """Manager with no filings should still appear with null fields."""
    resp = await client.get("/api/v1/13f/managers?tier=top_aum")
    assert resp.status_code == 200
    data = resp.json()
    mgr = data[0]
    assert mgr["name"] == "Bridgewater"
    assert mgr["total_holdings"] == 0
    assert mgr["aum_millions"] is None
    assert mgr["last_filing"] is None
    assert mgr["top_positions"] == []


@pytest.mark.asyncio
async def test_get_manager_portfolio(client, seeded_db):
    mgr_id = seeded_db["mgr1"].id
    resp = await client.get(f"/api/v1/13f/managers/{mgr_id}/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["manager"] == "Berkshire"
    assert data["period_of_report"] == "2025-12-31"
    assert len(data["holdings"]) == 2
    # Holdings should be ordered by value descending
    assert data["holdings"][0]["value_millions"] >= data["holdings"][1]["value_millions"]
    # Percentages should sum to ~100
    total_pct = sum(h["pct_portfolio"] for h in data["holdings"])
    assert 99.9 <= total_pct <= 100.1


@pytest.mark.asyncio
async def test_get_manager_portfolio_not_found(client):
    resp = await client.get("/api/v1/13f/managers/99999/portfolio")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_manager_portfolio_no_filing(client, seeded_db):
    """Manager with no filings should return 404."""
    mgr_id = seeded_db["mgr2"].id
    resp = await client.get(f"/api/v1/13f/managers/{mgr_id}/portfolio")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_managers_invalid_tier(client):
    """Invalid tier parameter should be rejected."""
    resp = await client.get("/api/v1/13f/managers?tier=invalid")
    assert resp.status_code == 422
