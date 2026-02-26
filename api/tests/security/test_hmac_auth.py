"""Tests for HMAC-signed service-to-service authentication."""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from margin_api.config import Settings
from margin_api.db.models import Base, User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_TEST_SECRET = "a" * 64  # 64-byte hex secret for testing


def _sign_request(user_id: int, secret: str, timestamp: int | None = None) -> dict:
    """Create HMAC-signed auth headers."""
    ts = timestamp or int(time.time())
    payload = f"{user_id}:{ts}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {
        "X-User-Id": str(user_id),
        "X-Auth-Timestamp": str(ts),
        "X-Auth-Signature": sig,
    }


@pytest_asyncio.fixture
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        user = User(id=42, email="test@test.com", name="Test")
        session.add(user)
        await session.commit()

    app = FastAPI()

    async def override_db():
        async with factory() as session:
            yield session

    def override_settings():
        return Settings(
            service_auth_secret=_TEST_SECRET,
            require_signed_auth=True,
        )

    app.dependency_overrides[get_db] = override_db
    from margin_api.config import get_settings
    app.dependency_overrides[get_settings] = override_settings

    @app.get("/test")
    async def test_endpoint(user_id: int = Depends(get_current_user_id)):
        return {"user_id": user_id}

    return app


class TestHmacAuth:
    @pytest.mark.asyncio
    async def test_valid_hmac_returns_user_id(self, setup):
        app = setup
        headers = _sign_request(42, _TEST_SECRET)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["user_id"] == 42

    @pytest.mark.asyncio
    async def test_missing_signature_rejected_when_required(self, setup):
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"X-User-Id": "42"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_rejected(self, setup):
        app = setup
        headers = _sign_request(42, "wrong" * 13)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_timestamp_rejected(self, setup):
        app = setup
        old_ts = int(time.time()) - 120  # 2 minutes ago
        headers = _sign_request(42, _TEST_SECRET, timestamp=old_ts)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_no_headers_returns_401(self, setup):
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test")
        assert resp.status_code == 401


class TestHmacAuthFlagOff:
    @pytest.mark.asyncio
    async def test_unsigned_allowed_when_flag_off(self):
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
                require_signed_auth=False,  # Flag OFF
            )

        app.dependency_overrides[get_db] = override_db
        from margin_api.config import get_settings
        app.dependency_overrides[get_settings] = override_settings

        @app.get("/test")
        async def test_endpoint(user_id: int = Depends(get_current_user_id)):
            return {"user_id": user_id}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"X-User-Id": "42"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == 42
