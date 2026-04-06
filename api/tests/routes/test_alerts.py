"""Tests for score alert CRUD endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

AUTH_HEADERS = {"X-User-Id": "1"}

_USER_ID = 1


# ---------------------------------------------------------------------------
# Fixtures
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
async def seeded_db(session_factory):
    """Seed a User(id=1) into the test DB."""
    async with session_factory() as session:
        user = User(
            id=_USER_ID,
            email="test@example.com",
            name="Test User",
        )
        session.add(user)
        await session.commit()
    return session_factory


async def _make_client(sf) -> AsyncClient:
    """Build an AsyncClient with the DB overridden and user_id=1."""
    app = create_app()

    async def override_get_db():
        async with sf() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_empty_alerts(seeded_db):
    """GET /alerts returns an empty list when no alerts exist."""
    async with await _make_client(seeded_db) as client:
        resp = await client.get("/api/v1/me/alerts", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_create_above_alert(seeded_db):
    """POST /alerts with above type and threshold returns 201."""
    payload = {"ticker": "AAPL", "alert_type": "above", "threshold": 75.0}
    async with await _make_client(seeded_db) as client:
        resp = await client.post("/api/v1/me/alerts", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert data["alert_type"] == "above"
    assert data["threshold"] == 75.0
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_survivor_alert_ignores_threshold(seeded_db):
    """POST /alerts with survivor type sets threshold to None even if provided."""
    payload = {"ticker": "MSFT", "alert_type": "survivor", "threshold": 50.0}
    async with await _make_client(seeded_db) as client:
        resp = await client.post("/api/v1/me/alerts", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["alert_type"] == "survivor"
    assert data["threshold"] is None


@pytest.mark.asyncio
async def test_create_above_alert_without_threshold_fails(seeded_db):
    """POST /alerts with above type and no threshold returns 422."""
    payload = {"ticker": "AAPL", "alert_type": "above"}
    async with await _make_client(seeded_db) as client:
        resp = await client.post("/api/v1/me/alerts", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_invalid_alert_type_fails(seeded_db):
    """POST /alerts with an unrecognized alert_type returns 422."""
    payload = {"ticker": "AAPL", "alert_type": "unknown", "threshold": 50.0}
    async with await _make_client(seeded_db) as client:
        resp = await client.post("/api/v1/me/alerts", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_duplicate_alert_returns_409(seeded_db):
    """POST /alerts with duplicate user+ticker+type returns 409."""
    payload = {"ticker": "AAPL", "alert_type": "above", "threshold": 70.0}
    async with await _make_client(seeded_db) as client:
        await client.post("/api/v1/me/alerts", json=payload, headers=AUTH_HEADERS)
        resp = await client.post("/api/v1/me/alerts", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_alert(seeded_db):
    """DELETE /alerts/{alert_id} returns 204 for an existing alert."""
    payload = {"ticker": "AAPL", "alert_type": "above", "threshold": 80.0}
    async with await _make_client(seeded_db) as client:
        create_resp = await client.post("/api/v1/me/alerts", json=payload, headers=AUTH_HEADERS)
        alert_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/me/alerts/{alert_id}", headers=AUTH_HEADERS)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent_alert_returns_404(seeded_db):
    """DELETE /alerts/{alert_id} returns 404 for an unknown ID."""
    async with await _make_client(seeded_db) as client:
        resp = await client.delete("/api/v1/me/alerts/99999", headers=AUTH_HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_alert_limit_enforced(seeded_db):
    """Creating more than 20 alerts returns 400."""
    async with await _make_client(seeded_db) as client:
        # Create 20 alerts using different tickers
        for i in range(20):
            ticker = f"T{i:03d}"
            payload = {"ticker": ticker, "alert_type": "above", "threshold": float(i + 1)}
            resp = await client.post("/api/v1/me/alerts", json=payload, headers=AUTH_HEADERS)
            assert resp.status_code == 201, f"Alert {i + 1} failed: {resp.json()}"

        # 21st should be rejected
        payload = {"ticker": "OVER", "alert_type": "above", "threshold": 99.0}
        resp = await client.post("/api/v1/me/alerts", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 400
