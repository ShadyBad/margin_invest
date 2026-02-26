"""Tests for the MFA complete and verify-mfa-token endpoints."""

from __future__ import annotations

import time

import jwt
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from margin_api.config import Settings
from margin_api.db.models import Base, User
from margin_api.db.session import get_db
from margin_api.routes.auth import router as auth_router
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_TEST_JWT_SECRET = "test-jwt-secret-for-mfa"


@pytest_asyncio.fixture
async def app_and_user():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create test user
    async with factory() as session:
        user = User(id=1, email="test@test.com", name="testuser")
        session.add(user)
        await session.commit()

    app = FastAPI()
    app.include_router(auth_router)

    async def override_db():
        async with factory() as session:
            yield session

    def override_settings():
        return Settings(
            jwt_secret=_TEST_JWT_SECRET,
        )

    app.dependency_overrides[get_db] = override_db
    from margin_api.config import get_settings

    app.dependency_overrides[get_settings] = override_settings

    return app, factory


class TestVerifyMfaToken:
    @pytest.mark.asyncio
    async def test_valid_mfa_token_returns_user(self, app_and_user):
        app, _ = app_and_user
        token = jwt.encode(
            {
                "sub": "1",
                "purpose": "mfa_complete",
                "exp": int(time.time()) + 60,
                "iat": int(time.time()),
            },
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["email"] == "test@test.com"
        assert data["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_expired_mfa_token_rejected(self, app_and_user):
        app, _ = app_and_user
        token = jwt.encode(
            {
                "sub": "1",
                "purpose": "mfa_complete",
                "exp": int(time.time()) - 60,
                "iat": int(time.time()) - 120,
            },
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": token},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_purpose_rejected(self, app_and_user):
        app, _ = app_and_user
        token = jwt.encode(
            {
                "sub": "1",
                "purpose": "password_reset",
                "exp": int(time.time()) + 60,
                "iat": int(time.time()),
            },
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": token},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_nonexistent_user_rejected(self, app_and_user):
        app, _ = app_and_user
        token = jwt.encode(
            {
                "sub": "999",
                "purpose": "mfa_complete",
                "exp": int(time.time()) + 60,
                "iat": int(time.time()),
            },
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": token},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_token_string_rejected(self, app_and_user):
        app, _ = app_and_user
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": "not-a-real-token"},
            )
        assert resp.status_code == 401
