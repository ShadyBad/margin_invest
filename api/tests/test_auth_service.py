"""Tests for the AuthService layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import MfaChallengeToken, User
from margin_api.services.auth import AuthService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture()
def auth_service():
    return AuthService()


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestRegisterUser:
    @pytest.mark.asyncio
    async def test_register_success(self, auth_service, session):
        user = await auth_service.register_user(
            session, "alice", "alice@example.com", "Str0ng!Pass99"
        )
        assert user.id is not None
        assert user.name == "alice"
        assert user.email == "alice@example.com"
        assert user.password_hash != "Str0ng!Pass99"  # must be hashed
        assert user.mfa_enabled is False
        assert user.mfa_grace_deadline is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service, session):
        await auth_service.register_user(session, "alice", "alice@example.com", "Str0ng!Pass99")
        with pytest.raises(ValueError, match="email"):
            await auth_service.register_user(session, "bob", "alice@example.com", "Str0ng!Pass99")

    @pytest.mark.asyncio
    async def test_register_weak_password_too_short(self, auth_service, session):
        with pytest.raises(ValueError, match="12"):
            await auth_service.register_user(session, "alice", "alice@example.com", "Short1!")

    @pytest.mark.asyncio
    async def test_register_weak_password_no_uppercase(self, auth_service, session):
        with pytest.raises(ValueError, match="uppercase"):
            await auth_service.register_user(
                session, "alice", "alice@example.com", "nouppercase1!a"
            )

    @pytest.mark.asyncio
    async def test_register_weak_password_no_lowercase(self, auth_service, session):
        with pytest.raises(ValueError, match="lowercase"):
            await auth_service.register_user(
                session, "alice", "alice@example.com", "NOLOWERCASE1!A"
            )

    @pytest.mark.asyncio
    async def test_register_weak_password_no_digit(self, auth_service, session):
        with pytest.raises(ValueError, match="digit"):
            await auth_service.register_user(
                session, "alice", "alice@example.com", "NoDigitHere!abc"
            )

    @pytest.mark.asyncio
    async def test_register_weak_password_no_special(self, auth_service, session):
        with pytest.raises(ValueError, match="special"):
            await auth_service.register_user(
                session, "alice", "alice@example.com", "NoSpecial1abcde"
            )


# ---------------------------------------------------------------------------
# Verify credentials tests
# ---------------------------------------------------------------------------


class TestVerifyCredentials:
    @pytest.mark.asyncio
    async def test_verify_success(self, auth_service, session):
        await auth_service.register_user(session, "alice", "alice@example.com", "Str0ng!Pass99")
        result = await auth_service.verify_credentials(
            session, "alice@example.com", "Str0ng!Pass99"
        )
        assert result is not None
        assert result["email"] == "alice@example.com"
        assert "id" in result
        assert "mfa_enabled" in result

    @pytest.mark.asyncio
    async def test_verify_wrong_password(self, auth_service, session):
        await auth_service.register_user(session, "alice", "alice@example.com", "Str0ng!Pass99")
        result = await auth_service.verify_credentials(session, "alice@example.com", "WrongPass1!")
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_nonexistent_user(self, auth_service, session):
        result = await auth_service.verify_credentials(
            session, "nobody@example.com", "Str0ng!Pass99"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_failed_attempts_increment(self, auth_service, session):
        await auth_service.register_user(session, "alice", "alice@example.com", "Str0ng!Pass99")
        await auth_service.verify_credentials(session, "alice@example.com", "Wrong1!abcde")
        await auth_service.verify_credentials(session, "alice@example.com", "Wrong2!abcde")
        stmt = select(User).where(User.email == "alice@example.com")
        user = (await session.execute(stmt)).scalar_one()
        assert user.failed_login_attempts == 2

    @pytest.mark.asyncio
    async def test_lockout_after_five_failures(self, auth_service, session):
        await auth_service.register_user(session, "alice", "alice@example.com", "Str0ng!Pass99")
        for _ in range(5):
            await auth_service.verify_credentials(session, "alice@example.com", "Wrong1!abcde")
        stmt = select(User).where(User.email == "alice@example.com")
        user = (await session.execute(stmt)).scalar_one()
        assert user.locked_until is not None
        # Even correct password should fail during lockout
        result = await auth_service.verify_credentials(
            session, "alice@example.com", "Str0ng!Pass99"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_reset_on_success(self, auth_service, session):
        await auth_service.register_user(session, "alice", "alice@example.com", "Str0ng!Pass99")
        # Build up some failures
        await auth_service.verify_credentials(session, "alice@example.com", "Wrong1!abcde")
        await auth_service.verify_credentials(session, "alice@example.com", "Wrong2!abcde")
        # Succeed
        result = await auth_service.verify_credentials(
            session, "alice@example.com", "Str0ng!Pass99"
        )
        assert result is not None
        stmt = select(User).where(User.email == "alice@example.com")
        user = (await session.execute(stmt)).scalar_one()
        assert user.failed_login_attempts == 0

    @pytest.mark.asyncio
    async def test_lockout_expires(self, auth_service, session):
        await auth_service.register_user(session, "alice", "alice@example.com", "Str0ng!Pass99")
        # Lock user manually with expired time
        stmt = select(User).where(User.email == "alice@example.com")
        user = (await session.execute(stmt)).scalar_one()
        user.locked_until = datetime.now(UTC) - timedelta(minutes=1)
        user.failed_login_attempts = 5
        await session.commit()
        # Should succeed now
        result = await auth_service.verify_credentials(
            session, "alice@example.com", "Str0ng!Pass99"
        )
        assert result is not None


# ---------------------------------------------------------------------------
# Challenge token tests
# ---------------------------------------------------------------------------


class TestChallengeToken:
    @pytest.mark.asyncio
    async def test_create_token(self, auth_service, session):
        user = await auth_service.register_user(
            session, "alice", "alice@example.com", "Str0ng!Pass99"
        )
        raw_token = await auth_service.create_challenge_token(session, user.id)
        assert isinstance(raw_token, str)
        assert len(raw_token) == 64  # hex of 32 bytes

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, auth_service, session):
        user = await auth_service.register_user(
            session, "alice", "alice@example.com", "Str0ng!Pass99"
        )
        raw_token = await auth_service.create_challenge_token(session, user.id)
        result = await auth_service.verify_challenge_token(session, user.id, raw_token)
        assert result is True

    @pytest.mark.asyncio
    async def test_token_single_use(self, auth_service, session):
        user = await auth_service.register_user(
            session, "alice", "alice@example.com", "Str0ng!Pass99"
        )
        raw_token = await auth_service.create_challenge_token(session, user.id)
        await auth_service.verify_challenge_token(session, user.id, raw_token)
        # Second use should fail
        result = await auth_service.verify_challenge_token(session, user.id, raw_token)
        assert result is False

    @pytest.mark.asyncio
    async def test_token_expired(self, auth_service, session):
        user = await auth_service.register_user(
            session, "alice", "alice@example.com", "Str0ng!Pass99"
        )
        raw_token = await auth_service.create_challenge_token(session, user.id, ttl_minutes=0)
        # Manually expire the token
        stmt = select(MfaChallengeToken).where(MfaChallengeToken.user_id == user.id)
        token_row = (await session.execute(stmt)).scalar_one()
        token_row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()
        result = await auth_service.verify_challenge_token(session, user.id, raw_token)
        assert result is False

    @pytest.mark.asyncio
    async def test_token_wrong_value(self, auth_service, session):
        user = await auth_service.register_user(
            session, "alice", "alice@example.com", "Str0ng!Pass99"
        )
        await auth_service.create_challenge_token(session, user.id)
        result = await auth_service.verify_challenge_token(session, user.id, "bad" * 20)
        assert result is False
