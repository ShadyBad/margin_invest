"""Tests for subscription-related model fields."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import CredentialUser, User
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


class TestUserSubscriptionFields:
    @pytest.mark.asyncio
    async def test_user_defaults_to_free_plan(self, db):
        user = User(email="a@b.com", name="A", provider="google")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.subscription_plan == "free"
        assert user.stripe_customer_id is None
        assert user.stripe_subscription_id is None

    @pytest.mark.asyncio
    async def test_user_can_set_margin_invest_plan(self, db):
        user = User(
            email="a@b.com",
            name="A",
            provider="google",
            subscription_plan="margin_invest",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_456",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.subscription_plan == "margin_invest"
        assert user.stripe_customer_id == "cus_123"
        assert user.stripe_subscription_id == "sub_456"


class TestCredentialUserSubscriptionFields:
    @pytest.mark.asyncio
    async def test_credential_user_defaults_to_free_plan(self, db):
        user = CredentialUser(
            username="alice",
            email="alice@example.com",
            password_hash="hashed",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.subscription_plan == "free"
        assert user.stripe_customer_id is None
        assert user.stripe_subscription_id is None

    @pytest.mark.asyncio
    async def test_credential_user_can_set_plan(self, db):
        user = CredentialUser(
            username="alice",
            email="alice@example.com",
            password_hash="hashed",
            subscription_plan="margin_invest",
            stripe_customer_id="cus_abc",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.subscription_plan == "margin_invest"
