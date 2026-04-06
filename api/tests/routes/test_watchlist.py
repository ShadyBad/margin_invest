"""Tests for watchlist CRUD endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, User
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
    """Seed a User(id=1) and Asset(id=1, ticker='AAPL') into the test DB."""
    async with session_factory() as session:
        user = User(
            id=_USER_ID,
            email="test@example.com",
            name="Test User",
        )
        asset = Asset(
            id=1,
            ticker="AAPL",
            name="Apple Inc.",
            sector="TECHNOLOGY",
        )
        session.add(user)
        session.add(asset)
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
async def test_get_empty_watchlist(seeded_db):
    """GET /watchlist returns an empty list when no items have been added."""
    async with await _make_client(seeded_db) as client:
        resp = await client.get("/api/v1/me/watchlist", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_add_ticker_to_watchlist(seeded_db):
    """POST /watchlist/{ticker} returns 201 when a ticker is added."""
    async with await _make_client(seeded_db) as client:
        resp = await client.post("/api/v1/me/watchlist/AAPL", headers=AUTH_HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert data["added"] is True


@pytest.mark.asyncio
async def test_add_duplicate_ticker_returns_409(seeded_db):
    """POST /watchlist/{ticker} twice returns 409 on the duplicate."""
    async with await _make_client(seeded_db) as client:
        await client.post("/api/v1/me/watchlist/AAPL", headers=AUTH_HEADERS)
        resp = await client.post("/api/v1/me/watchlist/AAPL", headers=AUTH_HEADERS)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_from_watchlist(seeded_db):
    """DELETE /watchlist/{ticker} returns 204 after adding the ticker."""
    async with await _make_client(seeded_db) as client:
        await client.post("/api/v1/me/watchlist/AAPL", headers=AUTH_HEADERS)
        resp = await client.delete("/api/v1/me/watchlist/AAPL", headers=AUTH_HEADERS)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_404(seeded_db):
    """DELETE /watchlist/{ticker} returns 404 for an unknown ticker."""
    async with await _make_client(seeded_db) as client:
        resp = await client.delete("/api/v1/me/watchlist/TSLA", headers=AUTH_HEADERS)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_watchlist_returns_added_items(seeded_db):
    """GET /watchlist returns previously added items."""
    async with await _make_client(seeded_db) as client:
        await client.post("/api/v1/me/watchlist/AAPL", headers=AUTH_HEADERS)
        resp = await client.get("/api/v1/me/watchlist", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(seeded_db):
    """Requests without auth headers return 401."""
    app = create_app()

    async def override_get_db():
        async with seeded_db() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # Do NOT override get_current_user_id — let auth fail naturally

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/me/watchlist")
    assert resp.status_code == 401
