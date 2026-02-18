"""Tests for BillingService — Stripe Checkout, portal, webhooks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.services.billing import BillingService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def user(db):
    u = User(email="a@b.com", name="A", provider="google")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
def service():
    return BillingService(
        stripe_secret_key="sk_test_fake",
        stripe_portfolio_price_id="price_portfolio_123",
        stripe_institutional_price_id="price_institutional_456",
        stripe_webhook_secret="whsec_fake",
    )


class TestCreateCheckoutSession:
    @pytest.mark.asyncio
    async def test_creates_portfolio_checkout_and_sets_customer(self, db, user, service):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session_123"

        mock_customer = MagicMock()
        mock_customer.id = "cus_new_123"

        with patch.object(service, "_stripe") as mock_stripe:
            mock_stripe.v1.customers.create.return_value = mock_customer
            mock_stripe.v1.checkout.sessions.create.return_value = mock_session

            url = await service.create_checkout_session(
                db,
                user_id=user.id,
                plan="portfolio",
                success_url="http://localhost:3000/account?subscription=active",
                cancel_url="http://localhost:3000/account",
            )

        assert url == "https://checkout.stripe.com/session_123"
        await db.refresh(user)
        assert user.stripe_customer_id == "cus_new_123"

        # Verify correct price_id used
        call_args = mock_stripe.v1.checkout.sessions.create.call_args
        line_items = call_args[1]["params"]["line_items"]
        assert line_items[0]["price"] == "price_portfolio_123"

    @pytest.mark.asyncio
    async def test_creates_institutional_checkout(self, db, user, service):
        user.stripe_customer_id = "cus_existing"
        await db.commit()

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session_inst"

        with patch.object(service, "_stripe") as mock_stripe:
            mock_stripe.v1.checkout.sessions.create.return_value = mock_session

            url = await service.create_checkout_session(
                db,
                user_id=user.id,
                plan="institutional",
                success_url="http://localhost:3000/account?subscription=active",
                cancel_url="http://localhost:3000/account",
            )

        assert url == "https://checkout.stripe.com/session_inst"
        call_args = mock_stripe.v1.checkout.sessions.create.call_args
        line_items = call_args[1]["params"]["line_items"]
        assert line_items[0]["price"] == "price_institutional_456"

    @pytest.mark.asyncio
    async def test_unknown_plan_raises(self, db, user, service):
        with pytest.raises(ValueError, match="Unknown plan"):
            await service.create_checkout_session(
                db,
                user_id=user.id,
                plan="invalid_plan",
                success_url="http://localhost:3000/account",
                cancel_url="http://localhost:3000/account",
            )

    @pytest.mark.asyncio
    async def test_reuses_existing_customer(self, db, user, service):
        user.stripe_customer_id = "cus_existing"
        await db.commit()

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session_456"

        with patch.object(service, "_stripe") as mock_stripe:
            mock_stripe.v1.checkout.sessions.create.return_value = mock_session

            url = await service.create_checkout_session(
                db,
                user_id=user.id,
                plan="portfolio",
                success_url="http://localhost:3000/account",
                cancel_url="http://localhost:3000/account",
            )

        # Should NOT create a new customer
        mock_stripe.v1.customers.create.assert_not_called()
        assert url == "https://checkout.stripe.com/session_456"


class TestHandleSubscriptionCreated:
    @pytest.mark.asyncio
    async def test_sets_portfolio_plan_and_subscription_id(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="active",
            price_id="price_portfolio_123",
            current_period_end=1700000000,
        )

        await db.refresh(user)
        assert user.subscription_plan == "portfolio"
        assert user.stripe_subscription_id == "sub_abc"
        assert user.subscription_status == "active"
        assert user.current_period_end is not None

    @pytest.mark.asyncio
    async def test_sets_institutional_plan(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="active",
            price_id="price_institutional_456",
        )

        await db.refresh(user)
        assert user.subscription_plan == "institutional"
        assert user.stripe_subscription_id == "sub_abc"
        assert user.subscription_status == "active"

    @pytest.mark.asyncio
    async def test_defaults_to_portfolio_when_no_price_id(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="active",
        )

        await db.refresh(user)
        assert user.subscription_plan == "portfolio"


class TestHandleSubscriptionDeleted:
    @pytest.mark.asyncio
    async def test_downgrades_to_analyst(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        user.subscription_plan = "portfolio"
        user.stripe_subscription_id = "sub_abc"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="canceled",
        )

        await db.refresh(user)
        assert user.subscription_plan == "analyst"
        assert user.subscription_status == "canceled"


class TestHandleSubscriptionPastDue:
    @pytest.mark.asyncio
    async def test_past_due_downgrades_to_analyst(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        user.subscription_plan = "portfolio"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="past_due",
        )

        await db.refresh(user)
        assert user.subscription_plan == "analyst"
        assert user.subscription_status == "past_due"
