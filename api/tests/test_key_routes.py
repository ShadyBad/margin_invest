"""Tests for API key management routes."""

from __future__ import annotations

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest_asyncio.fixture()
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        paid_user = User(
            email="paid@test.com",
            name="Paid",
            subscription_plan="margin_invest",
        )
        free_user = User(email="free@test.com", name="Free")
        session.add_all([paid_user, free_user])
        await session.commit()
        await session.refresh(paid_user)
        await session.refresh(free_user)
        paid_id = paid_user.id
        free_id = free_user.id

    app = create_app()

    async def override_db():
        async with factory() as session:
            yield session

    def override_settings():
        from margin_api.config import Settings

        return Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            mfa_encryption_key=_TEST_FERNET_KEY,
            api_key_encryption_key=_TEST_FERNET_KEY,
            stripe_secret_key="sk_test_fake",
            stripe_portfolio_price_id="price_portfolio_123",
            stripe_institutional_price_id="price_institutional_456",
            stripe_webhook_secret="whsec_fake",
        )

    from margin_api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings

    yield app, paid_id, free_id
    await engine.dispose()


class TestPlanGating:
    @pytest.mark.asyncio
    async def test_free_user_cannot_list_keys(self, setup):
        app, _, free_id = setup
        app.dependency_overrides[get_current_user_id] = lambda: free_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/keys/")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_paid_user_can_list_keys(self, setup):
        app, paid_id, _ = setup
        app.dependency_overrides[get_current_user_id] = lambda: paid_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/keys/")
        assert resp.status_code == 200
        assert resp.json()["keys"] == []


class TestSaveKey:
    @pytest.mark.asyncio
    async def test_save_and_list_key(self, setup):
        app, paid_id, _ = setup
        app.dependency_overrides[get_current_user_id] = lambda: paid_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/keys/",
                json={"provider_name": "fmp", "api_key": "sk_live_fmp_abc123"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["provider_name"] == "fmp"
            assert "abc123" in data["masked_key"]  # Last 6 chars visible
            assert data["is_platform_managed"] is False

            # List should include it
            list_resp = await client.get("/api/v1/keys/")
            assert len(list_resp.json()["keys"]) == 1


class TestDeleteKey:
    @pytest.mark.asyncio
    async def test_delete_key(self, setup):
        app, paid_id, _ = setup
        app.dependency_overrides[get_current_user_id] = lambda: paid_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/keys/",
                json={"provider_name": "fmp", "api_key": "sk_live_fmp_abc123"},
            )
            resp = await client.delete("/api/v1/keys/fmp")
            assert resp.status_code == 200

            list_resp = await client.get("/api/v1/keys/")
            assert len(list_resp.json()["keys"]) == 0
