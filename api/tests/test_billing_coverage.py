"""Additional billing route tests — portal, webhook, billing_status 404."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_TEST_FERNET_KEY = Fernet.generate_key().decode()


def _make_settings():
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


@pytest_asyncio.fixture
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        user = User(email="test@example.com", name="Test User")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    app = create_app()

    async def override_db():
        async with factory() as session:
            yield session

    from margin_api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = _make_settings
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    yield app, user_id, factory
    await engine.dispose()


class TestPortalEndpoint:
    @pytest.mark.asyncio
    async def test_portal_returns_url(self, setup):
        app, user_id, factory = setup

        # Give user a stripe_customer_id so portal session can be created
        async with factory() as session:
            user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
            user.stripe_customer_id = "cus_test_123"
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("margin_api.services.billing.stripe.StripeClient") as mock_cls:
                mock_stripe = mock_cls.return_value
                mock_portal = MagicMock()
                mock_portal.url = "https://billing.stripe.com/portal/123"
                mock_stripe.v1.billing_portal.sessions.create.return_value = mock_portal

                resp = await client.post("/api/v1/billing/portal")

        assert resp.status_code == 200
        assert resp.json()["portal_url"] == "https://billing.stripe.com/portal/123"

    @pytest.mark.asyncio
    async def test_portal_no_customer_returns_400(self, setup):
        """Portal returns 400 when user has no Stripe customer ID."""
        app, user_id, factory = setup

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("margin_api.services.billing.stripe.StripeClient"):
                # The BillingService.create_portal_session raises ValueError when no customer
                resp = await client.post("/api/v1/billing/portal")

        assert resp.status_code == 400


class TestWebhookEndpoint:
    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self, setup):
        """Webhook with invalid signature returns 400."""
        app, _, _ = setup

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/billing/webhook",
                content=b'{"invalid": "payload"}',
                headers={
                    "stripe-signature": "bad_sig",
                    "content-type": "application/json",
                },
            )

        assert resp.status_code == 400
        assert "Invalid webhook signature" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_subscription_event(self, setup):
        """Webhook processes subscription event and returns received."""
        app, user_id, factory = setup

        # Create a mock Stripe event
        mock_event = MagicMock()
        mock_event.id = "evt_test_123"
        mock_event.type = "customer.subscription.created"
        mock_event.data.object = {
            "customer": "cus_test_123",
            "id": "sub_test_456",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_portfolio_123"}}]},
            "current_period_end": 1740000000,
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch(
                "margin_api.services.billing.BillingService.construct_webhook_event",
                return_value=mock_event,
            ):
                with patch(
                    "margin_api.services.billing.BillingService.handle_subscription_change",
                    new_callable=AsyncMock,
                ):
                    resp = await client.post(
                        "/api/v1/billing/webhook",
                        content=b"test_payload",
                        headers={
                            "stripe-signature": "valid",
                            "content-type": "application/json",
                        },
                    )

        assert resp.status_code == 200
        assert resp.json()["received"] is True

    @pytest.mark.asyncio
    async def test_webhook_idempotency_skip(self, setup):
        """Second delivery of same event ID returns already_processed."""
        app, _, factory = setup

        mock_event = MagicMock()
        mock_event.id = "evt_idempotent_test"
        mock_event.type = "customer.subscription.updated"
        mock_event.data.object = {
            "customer": "cus_test",
            "id": "sub_test",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_portfolio_123"}}]},
            "current_period_end": 1740000000,
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch(
                "margin_api.services.billing.BillingService.construct_webhook_event",
                return_value=mock_event,
            ):
                with patch(
                    "margin_api.services.billing.BillingService.handle_subscription_change",
                    new_callable=AsyncMock,
                ):
                    # First delivery
                    resp1 = await client.post(
                        "/api/v1/billing/webhook",
                        content=b"payload",
                        headers={"stripe-signature": "sig", "content-type": "application/json"},
                    )
                    assert resp1.status_code == 200
                    assert resp1.json()["received"] is True

                    # Second delivery (same event ID)
                    resp2 = await client.post(
                        "/api/v1/billing/webhook",
                        content=b"payload",
                        headers={"stripe-signature": "sig", "content-type": "application/json"},
                    )
                    assert resp2.status_code == 200
                    assert resp2.json()["status"] == "already_processed"

    @pytest.mark.asyncio
    async def test_webhook_non_subscription_event(self, setup):
        """Webhook with non-subscription event type just records and returns."""
        app, _, _ = setup

        mock_event = MagicMock()
        mock_event.id = "evt_other_123"
        mock_event.type = "payment_intent.succeeded"
        mock_event.data.object = {}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch(
                "margin_api.services.billing.BillingService.construct_webhook_event",
                return_value=mock_event,
            ):
                resp = await client.post(
                    "/api/v1/billing/webhook",
                    content=b"payload",
                    headers={"stripe-signature": "sig", "content-type": "application/json"},
                )

        assert resp.status_code == 200
        assert resp.json()["received"] is True

    @pytest.mark.asyncio
    async def test_webhook_subscription_missing_price(self, setup):
        """Webhook handles subscription event even when price_id extraction fails."""
        app, _, _ = setup

        mock_event = MagicMock()
        mock_event.id = "evt_no_price"
        mock_event.type = "customer.subscription.deleted"
        mock_event.data.object = {
            "customer": "cus_test",
            "id": "sub_test",
            "status": "canceled",
            "items": {},  # Missing data key
        }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch(
                "margin_api.services.billing.BillingService.construct_webhook_event",
                return_value=mock_event,
            ):
                with patch(
                    "margin_api.services.billing.BillingService.handle_subscription_change",
                    new_callable=AsyncMock,
                ):
                    resp = await client.post(
                        "/api/v1/billing/webhook",
                        content=b"payload",
                        headers={"stripe-signature": "sig", "content-type": "application/json"},
                    )

        assert resp.status_code == 200
        assert resp.json()["received"] is True


class TestBillingStatusNotFound:
    @pytest.mark.asyncio
    async def test_billing_status_user_not_found(self):
        """Returns 404 when the user ID doesn't exist."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        app = create_app()

        async def override_db():
            async with factory() as session:
                yield session

        from margin_api.config import get_settings

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_settings] = _make_settings
        app.dependency_overrides[get_current_user_id] = lambda: 99999  # Non-existent

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/billing/status")

        assert resp.status_code == 404
        await engine.dispose()


class TestBillingStatusOperator:
    @pytest.mark.asyncio
    async def test_operator_user_is_active(self, setup):
        """An operator user with active status should be marked as active."""
        app, user_id, factory = setup
        async with factory() as session:
            user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
            user.subscription_plan = "operator"
            user.subscription_status = "active"
            await session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/billing/status")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True
