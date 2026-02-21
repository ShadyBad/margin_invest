"""Tests for billing API routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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
        user = User(email="a@b.com", name="A")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

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
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    yield app, user_id
    await engine.dispose()


class TestCheckout:
    @pytest.mark.asyncio
    async def test_checkout_returns_url(self, setup):
        app, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("margin_api.services.billing.stripe.StripeClient") as mock_client_cls:
                mock_stripe = mock_client_cls.return_value
                mock_customer = MagicMock()
                mock_customer.id = "cus_123"
                mock_stripe.v1.customers.create.return_value = mock_customer
                mock_session = MagicMock()
                mock_session.url = "https://checkout.stripe.com/s/123"
                mock_stripe.v1.checkout.sessions.create.return_value = mock_session

                resp = await client.post(
                    "/api/v1/billing/checkout",
                    json={"plan": "portfolio"},
                )

        assert resp.status_code == 200
        assert resp.json()["checkout_url"] == "https://checkout.stripe.com/s/123"


class TestBillingStatus:
    @pytest.mark.asyncio
    async def test_status_returns_analyst_by_default(self, setup):
        app, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/billing/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "analyst"
        assert data["is_active"] is False
