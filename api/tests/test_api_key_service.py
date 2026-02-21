"""Tests for ApiKeyService — encryption, CRUD, rotation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from margin_api.db.base import Base
from margin_api.db.models import ApiKeyEvent, User
from margin_api.services.api_keys import ApiKeyService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
    u = User(email="a@b.com", name="A")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
def service():
    return ApiKeyService(encryption_key=_TEST_KEY)


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self, service):
        plaintext = "sk_live_abc123"
        encrypted = service.encrypt(plaintext)
        assert encrypted != plaintext
        assert service.decrypt(encrypted) == plaintext

    def test_encrypted_values_are_different_each_time(self, service):
        """Fernet includes a timestamp, so encryptions of the same value differ."""
        a = service.encrypt("same")
        b = service.encrypt("same")
        assert a != b


class TestSaveKey:
    @pytest.mark.asyncio
    async def test_save_user_provided_key(self, db, user, service):
        key = await service.save_key(
            session=db,
            user_id=user.id,
            provider_name="fmp",
            plaintext_key="sk_live_fmp_123",
            is_platform_managed=False,
        )
        assert key.provider_name == "fmp"
        assert key.is_platform_managed is False
        assert key.encrypted_key != "sk_live_fmp_123"
        # Decrypt should roundtrip
        assert service.decrypt(key.encrypted_key) == "sk_live_fmp_123"

    @pytest.mark.asyncio
    async def test_save_key_revokes_existing(self, db, user, service):
        """Saving a new key for the same provider revokes the old one."""
        old = await service.save_key(db, user.id, "fmp", "old_key", False)
        new = await service.save_key(db, user.id, "fmp", "new_key", False)
        await db.refresh(old)
        assert old.revoked_at is not None
        assert new.revoked_at is None

    @pytest.mark.asyncio
    async def test_save_key_creates_event(self, db, user, service):
        key = await service.save_key(db, user.id, "polygon", "pk_123", False)
        result = await db.execute(
            select(ApiKeyEvent).where(ApiKeyEvent.api_key_id == key.id)
        )
        events = list(result.scalars().all())
        assert len(events) == 1
        assert events[0].event_type == "created"


class TestGetActiveKey:
    @pytest.mark.asyncio
    async def test_get_active_key(self, db, user, service):
        await service.save_key(db, user.id, "fmp", "the_key", False)
        key = await service.get_active_key(db, user.id, "fmp")
        assert key is not None
        assert service.decrypt(key.encrypted_key) == "the_key"

    @pytest.mark.asyncio
    async def test_get_active_key_returns_none_when_revoked(self, db, user, service):
        k = await service.save_key(db, user.id, "fmp", "the_key", False)
        k.revoked_at = datetime.now(UTC)
        await db.commit()
        key = await service.get_active_key(db, user.id, "fmp")
        assert key is None

    @pytest.mark.asyncio
    async def test_get_active_key_excludes_expired(self, db, user, service):
        k = await service.save_key(db, user.id, "fmp", "the_key", False)
        k.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await db.commit()
        key = await service.get_active_key(db, user.id, "fmp")
        assert key is None


class TestListKeys:
    @pytest.mark.asyncio
    async def test_list_active_keys(self, db, user, service):
        await service.save_key(db, user.id, "fmp", "key1", False)
        await service.save_key(db, user.id, "polygon", "key2", True)
        keys = await service.list_active_keys(db, user.id)
        assert len(keys) == 2
        providers = {k.provider_name for k in keys}
        assert providers == {"fmp", "polygon"}


class TestRevokeKey:
    @pytest.mark.asyncio
    async def test_revoke_key(self, db, user, service):
        key = await service.save_key(db, user.id, "fmp", "key1", False)
        revoked = await service.revoke_key(db, user.id, "fmp")
        assert revoked is True
        await db.refresh(key)
        assert key.revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_creates_event(self, db, user, service):
        key = await service.save_key(db, user.id, "fmp", "key1", False)
        await service.revoke_key(db, user.id, "fmp")
        result = await db.execute(
            select(ApiKeyEvent).where(
                ApiKeyEvent.api_key_id == key.id,
                ApiKeyEvent.event_type == "revoked",
            )
        )
        assert result.scalar_one_or_none() is not None
