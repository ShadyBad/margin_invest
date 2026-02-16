"""Tests for avatar URL columns on User and CredentialUser models."""

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


class TestUserAvatarFields:
    @pytest.mark.asyncio
    async def test_user_avatar_urls_default_to_none(self, db):
        user = User(email="a@b.com", name="A", provider="google")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.avatar_url is None
        assert user.oauth_avatar_url is None

    @pytest.mark.asyncio
    async def test_user_can_store_avatar_url(self, db):
        user = User(
            email="a@b.com",
            name="A",
            provider="google",
            avatar_url="https://example.com/custom-avatar.png",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.avatar_url == "https://example.com/custom-avatar.png"

    @pytest.mark.asyncio
    async def test_user_can_store_oauth_avatar_url(self, db):
        user = User(
            email="a@b.com",
            name="A",
            provider="google",
            oauth_avatar_url="https://lh3.googleusercontent.com/a/photo.jpg",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.oauth_avatar_url == "https://lh3.googleusercontent.com/a/photo.jpg"

    @pytest.mark.asyncio
    async def test_user_can_store_both_avatar_urls(self, db):
        user = User(
            email="a@b.com",
            name="A",
            provider="github",
            avatar_url="https://example.com/uploaded.png",
            oauth_avatar_url="https://avatars.githubusercontent.com/u/12345",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.avatar_url == "https://example.com/uploaded.png"
        assert user.oauth_avatar_url == "https://avatars.githubusercontent.com/u/12345"


class TestCredentialUserAvatarFields:
    @pytest.mark.asyncio
    async def test_credential_user_avatar_url_defaults_to_none(self, db):
        user = CredentialUser(
            username="alice",
            email="alice@example.com",
            password_hash="hashed",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.avatar_url is None

    @pytest.mark.asyncio
    async def test_credential_user_can_store_avatar_url(self, db):
        user = CredentialUser(
            username="alice",
            email="alice@example.com",
            password_hash="hashed",
            avatar_url="https://example.com/alice-avatar.png",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.avatar_url == "https://example.com/alice-avatar.png"
