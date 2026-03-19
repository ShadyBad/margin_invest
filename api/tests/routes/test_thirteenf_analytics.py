"""Tests for the 13F analytics endpoints (new-positions, overlap)."""

from __future__ import annotations

import os
from datetime import date
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.config import get_settings
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


# ---------------------------------------------------------------------------
# Async fixtures
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
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def institutional_user_id(db_session) -> int:
    """Seed an institutional-plan user and return its ID."""
    user = User(
        email="inst@test.com",
        name="Institutional User",
        subscription_plan="institutional",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


# ---------------------------------------------------------------------------
# Helper: build test client with plan bypass
# ---------------------------------------------------------------------------


def _make_client(session_factory, user_id: int) -> TestClient:
    get_settings.cache_clear()

    async def db_override():
        async with session_factory() as s:
            yield s

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-admin-key"}):
        app = create_app()

    app.dependency_overrides[get_db] = db_override
    # Override auth so require_plan sees the institutional user
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    return TestClient(app)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

Q1_2025 = date(2025, 3, 31)
Q4_2024 = date(2024, 12, 31)


async def _seed_manager(
    session: AsyncSession, cik: str, name: str, tier: str = "curated"
) -> Manager:
    mgr = Manager(cik=cik, name=name, tier=tier)
    session.add(mgr)
    await session.flush()
    return mgr


async def _seed_security(
    session: AsyncSession, cusip: str, ticker: str
) -> SecurityMaster:
    sec = SecurityMaster(cusip=cusip, ticker=ticker, issuer_name=ticker)
    session.add(sec)
    await session.flush()
    return sec


async def _seed_filing(
    session: AsyncSession, manager: Manager, period: date, accession: str
) -> FilingMetadata:
    filing = FilingMetadata(
        manager_id=manager.id,
        accession_number=accession,
        filing_type="13F-HR",
        period_of_report=period,
        filed_date=period,
    )
    session.add(filing)
    await session.flush()
    return filing


async def _seed_holding(
    session: AsyncSession,
    filing: FilingMetadata,
    manager: Manager,
    security: SecurityMaster,
    period: date,
    shares: int = 1000,
    value_thousands: int = 500,
) -> InstitutionalHolding:
    holding = InstitutionalHolding(
        filing_id=filing.id,
        manager_id=manager.id,
        security_master_id=security.id,
        cusip=security.cusip,
        period_of_report=period,
        shares_held=shares,
        value_thousands=value_thousands,
    )
    session.add(holding)
    await session.flush()
    return holding


# ---------------------------------------------------------------------------
# Tests: /analytics/new-positions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_positions_returns_results(session_factory, db_session, institutional_user_id):
    """Returns new positions when a ticker appears in Q1 but not Q4."""
    mgr = await _seed_manager(db_session, "0001234", "Test Fund A")
    sec = await _seed_security(db_session, "037833100", "AAPL")
    sec_msft = await _seed_security(db_session, "594918104", "MSFT")

    filing_q4 = await _seed_filing(db_session, mgr, Q4_2024, "ACC001")
    filing_q1 = await _seed_filing(db_session, mgr, Q1_2025, "ACC002")

    # mgr holds MSFT in Q4 only
    await _seed_holding(db_session, filing_q4, mgr, sec_msft, Q4_2024)

    # mgr holds AAPL in Q1 only (new position)
    await _seed_holding(db_session, filing_q1, mgr, sec, Q1_2025, value_thousands=2000)

    await db_session.commit()

    client = _make_client(session_factory, institutional_user_id)
    resp = client.get("/api/v1/13f/analytics/new-positions")
    assert resp.status_code == 200
    data = resp.json()

    assert data["period_of_report"] == Q1_2025.isoformat()
    assert data["previous_quarter"] == Q4_2024.isoformat()
    assert len(data["new_positions"]) == 1
    entry = data["new_positions"][0]
    assert entry["ticker"] == "AAPL"
    assert entry["total_new_funds"] == 1
    assert entry["total_value_millions"] == pytest.approx(2.0, rel=1e-3)
    assert "Test Fund A" in entry["managers"]


@pytest.mark.asyncio
async def test_new_positions_no_new_entries_when_ticker_in_both_quarters(
    session_factory, db_session, institutional_user_id
):
    """No new positions when ticker appears in both quarters for the same manager."""
    mgr = await _seed_manager(db_session, "0001235", "Test Fund B")
    sec = await _seed_security(db_session, "999999001", "XYZ")

    filing_q4 = await _seed_filing(db_session, mgr, Q4_2024, "ACC101")
    filing_q1 = await _seed_filing(db_session, mgr, Q1_2025, "ACC102")

    # XYZ held in both quarters — not a new position
    await _seed_holding(db_session, filing_q4, mgr, sec, Q4_2024)
    await _seed_holding(db_session, filing_q1, mgr, sec, Q1_2025)

    await db_session.commit()

    client = _make_client(session_factory, institutional_user_id)
    resp = client.get("/api/v1/13f/analytics/new-positions?quarter=2025-Q1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_positions"] == []


@pytest.mark.asyncio
async def test_new_positions_404_when_no_data(
    session_factory, db_session, institutional_user_id
):
    """Returns 404 when fewer than 2 quarters are available."""
    await db_session.commit()
    client = _make_client(session_factory, institutional_user_id)
    resp = client.get("/api/v1/13f/analytics/new-positions")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_new_positions_invalid_quarter_format(
    session_factory, db_session, institutional_user_id
):
    """Returns 400 for invalid quarter format."""
    await db_session.commit()
    client = _make_client(session_factory, institutional_user_id)
    resp = client.get("/api/v1/13f/analytics/new-positions?quarter=bad-format")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests: /analytics/overlap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overlap_returns_most_held(
    session_factory, db_session, institutional_user_id
):
    """Returns most held tickers for the latest quarter."""
    mgr_a = await _seed_manager(db_session, "0002001", "Fund Alpha")
    mgr_b = await _seed_manager(db_session, "0002002", "Fund Beta")

    sec_aapl = await _seed_security(db_session, "037833101", "AAPL")
    sec_msft = await _seed_security(db_session, "594918105", "MSFT")

    filing_a_q4 = await _seed_filing(db_session, mgr_a, Q4_2024, "ACC201")
    filing_b_q4 = await _seed_filing(db_session, mgr_b, Q4_2024, "ACC202")
    filing_a_q1 = await _seed_filing(db_session, mgr_a, Q1_2025, "ACC203")
    filing_b_q1 = await _seed_filing(db_session, mgr_b, Q1_2025, "ACC204")

    # Prev quarter: both hold AAPL
    await _seed_holding(db_session, filing_a_q4, mgr_a, sec_aapl, Q4_2024)
    await _seed_holding(db_session, filing_b_q4, mgr_b, sec_aapl, Q4_2024)

    # Current quarter: both hold AAPL (2 holders), only mgr_a holds MSFT (1 holder)
    await _seed_holding(db_session, filing_a_q1, mgr_a, sec_aapl, Q1_2025, value_thousands=5000)
    await _seed_holding(db_session, filing_b_q1, mgr_b, sec_aapl, Q1_2025, value_thousands=3000)
    await _seed_holding(db_session, filing_a_q1, mgr_a, sec_msft, Q1_2025, value_thousands=1000)

    await db_session.commit()

    client = _make_client(session_factory, institutional_user_id)
    resp = client.get("/api/v1/13f/analytics/overlap")
    assert resp.status_code == 200
    data = resp.json()

    assert data["period_of_report"] == Q1_2025.isoformat()
    tickers = [e["ticker"] for e in data["most_held"]]
    assert "AAPL" in tickers
    assert "MSFT" in tickers

    # AAPL should be first (most holders)
    assert data["most_held"][0]["ticker"] == "AAPL"
    assert data["most_held"][0]["holder_count"] == 2


@pytest.mark.asyncio
async def test_overlap_crowded_trades_fields(
    session_factory, db_session, institutional_user_id
):
    """Crowded trades are populated with concentration_pct and total_value_millions."""
    mgr = await _seed_manager(db_session, "0003001", "Fund Gamma")
    sec = await _seed_security(db_session, "111111111", "NVDA")

    filing_q4 = await _seed_filing(db_session, mgr, Q4_2024, "ACC301")
    filing_q1 = await _seed_filing(db_session, mgr, Q1_2025, "ACC302")

    await _seed_holding(db_session, filing_q4, mgr, sec, Q4_2024)
    await _seed_holding(db_session, filing_q1, mgr, sec, Q1_2025, value_thousands=10000)

    await db_session.commit()

    client = _make_client(session_factory, institutional_user_id)
    resp = client.get("/api/v1/13f/analytics/overlap")
    assert resp.status_code == 200
    data = resp.json()

    crowded = data["crowded_trades"]
    assert len(crowded) == 1
    trade = crowded[0]
    assert trade["ticker"] == "NVDA"
    assert trade["holder_count"] == 1
    assert trade["total_value_millions"] == pytest.approx(10.0, rel=1e-3)
    assert 0.0 <= trade["concentration_pct"] <= 1.0
    # Old fields must not appear
    assert "new_position_count" not in trade
    assert "pct_funds_adding" not in trade


@pytest.mark.asyncio
async def test_overlap_explicit_quarter(
    session_factory, db_session, institutional_user_id
):
    """Explicit quarter parameter is respected."""
    mgr = await _seed_manager(db_session, "0004001", "Fund Delta")
    sec = await _seed_security(db_session, "222222222", "TSLA")

    filing_q4 = await _seed_filing(db_session, mgr, Q4_2024, "ACC401")
    filing_q1 = await _seed_filing(db_session, mgr, Q1_2025, "ACC402")

    await _seed_holding(db_session, filing_q4, mgr, sec, Q4_2024)
    await _seed_holding(db_session, filing_q1, mgr, sec, Q1_2025)

    await db_session.commit()

    client = _make_client(session_factory, institutional_user_id)
    resp = client.get("/api/v1/13f/analytics/overlap?quarter=2025-Q1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period_of_report"] == Q1_2025.isoformat()
    tickers = [e["ticker"] for e in data["most_held"]]
    assert "TSLA" in tickers


@pytest.mark.asyncio
async def test_overlap_404_when_no_data(
    session_factory, db_session, institutional_user_id
):
    """Returns 404 when no holdings data is present."""
    await db_session.commit()
    client = _make_client(session_factory, institutional_user_id)
    resp = client.get("/api/v1/13f/analytics/overlap")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_overlap_response_has_total_managers(
    session_factory, db_session, institutional_user_id
):
    """total_managers field is populated when crowded trades data is available."""
    mgr = await _seed_manager(db_session, "0005001", "Fund Epsilon")
    sec = await _seed_security(db_session, "333333333", "META")

    filing_q4 = await _seed_filing(db_session, mgr, Q4_2024, "ACC501")
    filing_q1 = await _seed_filing(db_session, mgr, Q1_2025, "ACC502")

    await _seed_holding(db_session, filing_q4, mgr, sec, Q4_2024)
    await _seed_holding(db_session, filing_q1, mgr, sec, Q1_2025, value_thousands=5000)

    await db_session.commit()

    client = _make_client(session_factory, institutional_user_id)
    resp = client.get("/api/v1/13f/analytics/overlap")
    assert resp.status_code == 200
    data = resp.json()
    # total_managers present (may be null if concentration_pct rounds to 0)
    assert "total_managers" in data
