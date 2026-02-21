"""Tests for AuthService password reset methods."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import MfaChallengeToken, User
from margin_api.services.auth import AuthService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_auth = AuthService()


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        user = await _auth.register_user(
            session, "testuser", "test@example.com", "OldPassword1!"
        )

    yield factory, user.id
    await engine.dispose()


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_creates_token_with_60min_ttl(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)
            assert len(raw_token) == 64  # 32 bytes hex

            # Token should exist in DB
            tokens = (
                await session.execute(
                    select(MfaChallengeToken).where(
                        MfaChallengeToken.user_id == user_id
                    )
                )
            ).scalars().all()
            assert len(tokens) >= 1

    @pytest.mark.asyncio
    async def test_reset_password_success(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            await _auth.reset_password(session, user_id, raw_token, "NewPassword2@")

        # Verify new password works
        async with factory() as session:
            result = await _auth.verify_credentials(
                session, "test@example.com", "NewPassword2@"
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_reset_password_sets_changed_at(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            await _auth.reset_password(session, user_id, raw_token, "NewPassword2@")

        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert user.password_changed_at is not None

    @pytest.mark.asyncio
    async def test_reset_password_clears_lockout(self, db):
        factory, user_id = db
        # Lock the account with failed attempts
        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            user.failed_login_attempts = 5
            await session.commit()

        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            await _auth.reset_password(session, user_id, raw_token, "NewPassword2@")

        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert user.failed_login_attempts == 0
            assert user.locked_until is None

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, db):
        factory, user_id = db
        async with factory() as session:
            with pytest.raises(LookupError, match="Invalid or expired"):
                await _auth.reset_password(session, user_id, "badtoken", "NewPassword2@")

    @pytest.mark.asyncio
    async def test_reset_password_token_single_use(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            await _auth.reset_password(session, user_id, raw_token, "NewPassword2@")

        async with factory() as session:
            with pytest.raises(LookupError, match="Invalid or expired"):
                await _auth.reset_password(session, user_id, raw_token, "AnotherPass3#")

    @pytest.mark.asyncio
    async def test_reset_password_weak_password_rejected(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            with pytest.raises(ValueError, match="special character"):
                await _auth.reset_password(session, user_id, raw_token, "NoSpecialChar123")
