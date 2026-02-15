"""Tests for platform API key rotation worker task."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import ApiKey, ApiKeyEvent, User
from margin_api.services.api_keys import ApiKeyService
from margin_api.worker import rotate_platform_keys

_TEST_KEY = Fernet.generate_key()


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
    u = User(email="a@b.com", name="A", provider="google", subscription_plan="margin_invest")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
def service():
    return ApiKeyService(encryption_key=_TEST_KEY)


class TestRotatePlatformKeys:
    @pytest.mark.asyncio
    async def test_rotates_old_platform_key(self, db, user, service):
        """Keys older than 90 days get an expires_at set and a new key created."""
        old_key = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key=service.encrypt("old_fmp_key"),
            is_platform_managed=True,
            created_at=datetime.now(UTC) - timedelta(days=91),
        )
        db.add(old_key)
        await db.commit()
        await db.refresh(old_key)

        rotated = await rotate_platform_keys(session=db, service=service)
        assert rotated == 1

        await db.refresh(old_key)
        assert old_key.expires_at is not None  # Overlap window set

        # New key should exist
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.user_id == user.id,
                ApiKey.provider_name == "fmp",
                ApiKey.revoked_at.is_(None),
                ApiKey.id != old_key.id,
            )
        )
        new_key = result.scalar_one_or_none()
        assert new_key is not None
        assert new_key.is_platform_managed is True

    @pytest.mark.asyncio
    async def test_skips_recent_keys(self, db, user, service):
        """Keys less than 90 days old should NOT be rotated."""
        recent_key = ApiKey(
            user_id=user.id,
            provider_name="polygon",
            encrypted_key=service.encrypt("pg_key"),
            is_platform_managed=True,
            created_at=datetime.now(UTC) - timedelta(days=30),
        )
        db.add(recent_key)
        await db.commit()

        rotated = await rotate_platform_keys(session=db, service=service)
        assert rotated == 0

    @pytest.mark.asyncio
    async def test_skips_user_provided_keys(self, db, user, service):
        """BYOK keys should never be rotated."""
        byok = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key=service.encrypt("user_key"),
            is_platform_managed=False,
            created_at=datetime.now(UTC) - timedelta(days=200),
        )
        db.add(byok)
        await db.commit()

        rotated = await rotate_platform_keys(session=db, service=service)
        assert rotated == 0
