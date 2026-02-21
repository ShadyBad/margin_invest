"""Tests for FastAPI dependency helpers."""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id, require_plan
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed a free user and a paid user
    async with factory() as session:
        free_user = User(email="free@test.com", name="Free")
        paid_user = User(
            email="paid@test.com",
            name="Paid",
            subscription_plan="margin_invest",
        )
        session.add_all([free_user, paid_user])
        await session.commit()
        await session.refresh(free_user)
        await session.refresh(paid_user)
        free_id = free_user.id
        paid_id = paid_user.id

    app = FastAPI()

    async def override_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    # Test endpoint gated by require_plan
    @app.get("/premium")
    async def premium_endpoint(
        _=Depends(require_plan("margin_invest")),
    ):
        return {"access": "granted"}

    yield app, free_id, paid_id
    await engine.dispose()


class TestGetCurrentUserId:
    """Tests for the get_current_user_id dependency."""

    @pytest_asyncio.fixture()
    async def user_id_app(self):
        """Minimal FastAPI app with a route that uses get_current_user_id."""
        app = FastAPI()

        @app.get("/me")
        async def me(user_id: int = Depends(get_current_user_id)):
            return {"user_id": user_id}

        yield app

    @pytest.mark.asyncio
    async def test_valid_header_returns_user_id(self, user_id_app):
        transport = ASGITransport(app=user_id_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/me", headers={"X-User-Id": "42"})
        assert resp.status_code == 200
        assert resp.json() == {"user_id": 42}

    @pytest.mark.asyncio
    async def test_missing_header_returns_401(self, user_id_app):
        transport = ASGITransport(app=user_id_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/me")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"

    @pytest.mark.asyncio
    async def test_non_integer_header_returns_401(self, user_id_app):
        transport = ASGITransport(app=user_id_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/me", headers={"X-User-Id": "not-a-number"})
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Unknown user"


class TestRequirePlan:
    @pytest.mark.asyncio
    async def test_free_user_denied(self, setup):
        app, free_id, _ = setup
        app.dependency_overrides[get_current_user_id] = lambda: free_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/premium")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_paid_user_allowed(self, setup):
        app, _, paid_id = setup
        app.dependency_overrides[get_current_user_id] = lambda: paid_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/premium")
        assert resp.status_code == 200
        assert resp.json() == {"access": "granted"}
