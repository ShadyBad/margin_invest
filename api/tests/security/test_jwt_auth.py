"""Tests for JWT service token verification."""

from __future__ import annotations

import time

import jwt
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.config import Settings, get_settings
from margin_api.db.base import Base
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id

_TEST_SECRET = "jwt-test-secret-64-bytes-" + "x" * 39


def _make_token(user_id: int, secret: str = _TEST_SECRET, **overrides) -> str:
    payload = {
        "sub": str(user_id),
        "email": "test@test.com",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        **overrides,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest_asyncio.fixture()
async def app():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = FastAPI()

    async def override_db():
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session

    def override_settings():
        return Settings(
            service_auth_secret=_TEST_SECRET,
            require_signed_auth=True,
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings

    @app.get("/test")
    async def test_endpoint(user_id: int = Depends(get_current_user_id)):
        return {"user_id": user_id}

    return app


class TestJwtAuth:
    @pytest.mark.asyncio
    async def test_valid_jwt_returns_user_id(self, app):
        token = _make_token(42)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == 42

    @pytest.mark.asyncio
    async def test_expired_jwt_rejected(self, app):
        token = _make_token(42, exp=int(time.time()) - 60)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_rejected(self, app):
        token = _make_token(42, secret="wrong-secret-" + "x" * 50)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_sub_claim_rejected(self, app):
        payload = {
            "email": "test@test.com",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        token = jwt.encode(payload, _TEST_SECRET, algorithm="HS256")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_non_integer_sub_rejected(self, app):
        token = _make_token(42)
        # Override sub with non-integer
        payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        payload["sub"] = "not-an-integer"
        bad_token = jwt.encode(payload, _TEST_SECRET, algorithm="HS256")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/test", headers={"Authorization": f"Bearer {bad_token}"}
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_token_rejected(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/test", headers={"Authorization": "Bearer not.a.jwt"}
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_no_auth_header_returns_401(self, app):
        """When require_signed_auth=True, missing Authorization header returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_header_auth_still_works_when_signed_auth_not_required(self):
        """Legacy X-User-Id header auth still works when require_signed_auth=False."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        test_app = FastAPI()

        async def override_db():
            factory = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            async with factory() as session:
                yield session

        def override_settings():
            return Settings(
                service_auth_secret="",
                require_signed_auth=False,
            )

        test_app.dependency_overrides[get_db] = override_db
        test_app.dependency_overrides[get_settings] = override_settings

        @test_app.get("/test")
        async def test_endpoint(user_id: int = Depends(get_current_user_id)):
            return {"user_id": user_id}

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"X-User-Id": "42"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == 42
        await engine.dispose()
