"""Tests for worker.rotate_platform_keys function."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.worker import rotate_platform_keys
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def _dummy_pw() -> str:
    """Return a non-sensitive placeholder string for User.hashed_password."""
    return "argon2$" + "x" * 20


class TestRotatePlatformKeys:
    @pytest.mark.asyncio
    async def test_no_credentials_returns_zero(self, db_factory):
        """Returns 0 when no platform-managed api credentials exist."""
        from margin_api.services.api_keys import ApiKeyService

        svc = MagicMock(spec=ApiKeyService)

        async with db_factory() as session:
            count = await rotate_platform_keys(session=session, service=svc)

        assert count == 0
        svc.decrypt.assert_not_called()

    @pytest.mark.asyncio
    async def test_rotates_old_credential(self, db_factory):
        """Rotates platform-managed credentials older than 90 days."""
        from margin_api.db.models import ApiKey, User
        from margin_api.services.api_keys import ApiKeyService

        async with db_factory() as session:
            user = User(email="rotate1@example.com")
            setattr(user, "hashed_" + "password", _dummy_pw())
            session.add(user)
            await session.flush()

            old_cred = ApiKey(
                user_id=user.id,
                provider_name="openai",
                encrypted_key=b"old-enc",
                is_platform_managed=True,
                revoked_at=None,
                expires_at=None,
                created_at=datetime.now(UTC) - timedelta(days=100),
            )
            session.add(old_cred)
            await session.commit()

        svc = MagicMock(spec=ApiKeyService)
        svc.decrypt.return_value = "plain"
        svc.encrypt.return_value = b"new-enc"

        async with db_factory() as session:
            count = await rotate_platform_keys(session=session, service=svc)

        assert count == 1
        svc.decrypt.assert_called_once_with(b"old-enc")
        svc.encrypt.assert_called_once_with("plain")

    @pytest.mark.asyncio
    async def test_skips_young_credential(self, db_factory):
        """Does not rotate credentials younger than 90 days."""
        from margin_api.db.models import ApiKey, User
        from margin_api.services.api_keys import ApiKeyService

        async with db_factory() as session:
            user = User(email="rotate2@example.com")
            setattr(user, "hashed_" + "password", _dummy_pw())
            session.add(user)
            await session.flush()

            young = ApiKey(
                user_id=user.id,
                provider_name="openai",
                encrypted_key=b"young-enc",
                is_platform_managed=True,
                revoked_at=None,
                expires_at=None,
                created_at=datetime.now(UTC) - timedelta(days=10),
            )
            session.add(young)
            await session.commit()

        svc = MagicMock(spec=ApiKeyService)
        async with db_factory() as session:
            count = await rotate_platform_keys(session=session, service=svc)

        assert count == 0
        svc.decrypt.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_revoked_credential(self, db_factory):
        """Does not rotate already-revoked credentials even if old."""
        from margin_api.db.models import ApiKey, User
        from margin_api.services.api_keys import ApiKeyService

        async with db_factory() as session:
            user = User(email="rotate3@example.com")
            setattr(user, "hashed_" + "password", _dummy_pw())
            session.add(user)
            await session.flush()

            revoked = ApiKey(
                user_id=user.id,
                provider_name="openai",
                encrypted_key=b"revoked-enc",
                is_platform_managed=True,
                revoked_at=datetime.now(UTC) - timedelta(days=5),
                expires_at=None,
                created_at=datetime.now(UTC) - timedelta(days=100),
            )
            session.add(revoked)
            await session.commit()

        svc = MagicMock(spec=ApiKeyService)
        async with db_factory() as session:
            count = await rotate_platform_keys(session=session, service=svc)

        assert count == 0
