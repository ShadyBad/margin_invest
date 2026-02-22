"""Tests for updated ApiKey and new ApiKeyEvent models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import ApiKey, ApiKeyEvent, User
from sqlalchemy import select
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
    u = User(email="a@b.com", name="A")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


class TestApiKeyModel:
    @pytest.mark.asyncio
    async def test_api_key_has_new_fields(self, db, user):
        key = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="encrypted_value",
            is_platform_managed=True,
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)
        assert key.is_platform_managed is True
        assert key.expires_at is None
        assert key.revoked_at is None

    @pytest.mark.asyncio
    async def test_api_key_allows_multiple_per_provider(self, db, user):
        """No unique constraint — allows overlap during rotation."""
        key1 = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="old_key",
            is_platform_managed=True,
        )
        key2 = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="new_key",
            is_platform_managed=True,
        )
        db.add_all([key1, key2])
        await db.commit()
        result = await db.execute(
            select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.provider_name == "fmp")
        )
        keys = list(result.scalars().all())
        assert len(keys) == 2

    @pytest.mark.asyncio
    async def test_api_key_soft_delete_via_revoked_at(self, db, user):
        key = ApiKey(
            user_id=user.id,
            provider_name="polygon",
            encrypted_key="enc",
            revoked_at=datetime.now(UTC),
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)
        assert key.revoked_at is not None


class TestApiKeyEventModel:
    @pytest.mark.asyncio
    async def test_event_creation(self, db, user):
        key = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="enc",
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)

        event = ApiKeyEvent(
            api_key_id=key.id,
            event_type="created",
            ip_address="127.0.0.1",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        assert event.event_type == "created"
        assert event.api_key_id == key.id

    @pytest.mark.asyncio
    async def test_event_relationship(self, db, user):
        key = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="enc",
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)

        event = ApiKeyEvent(
            api_key_id=key.id,
            event_type="accessed",
        )
        db.add(event)
        await db.commit()

        result = await db.execute(select(ApiKey).where(ApiKey.id == key.id))
        loaded_key = result.scalar_one()
        await db.refresh(loaded_key, ["events"])
        assert len(loaded_key.events) == 1
        assert loaded_key.events[0].event_type == "accessed"
