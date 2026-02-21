"""Tests for the TotpService layer."""

from __future__ import annotations

from urllib.parse import unquote

import pyotp
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from margin_api.db.base import Base
from margin_api.db.models import TotpSecret, User
from margin_api.services.totp import TotpService
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
def encryption_key() -> bytes:
    return Fernet.generate_key()


@pytest.fixture()
def totp_service(encryption_key) -> TotpService:
    return TotpService(encryption_key=encryption_key)


@pytest_asyncio.fixture()
async def user(session) -> User:
    u = User(
        email="totp@example.com",
        name="totptest",
        password_hash="hash",
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Setup tests
# ---------------------------------------------------------------------------


class TestSetupTotp:
    @pytest.mark.asyncio
    async def test_returns_provisioning_uri(self, totp_service, session, user):
        result = await totp_service.setup_totp(session, user.id, user.email)
        uri = unquote(result["provisioning_uri"])
        assert "otpauth://totp/" in uri
        assert "Margin Invest" in uri
        assert "secret_id" in result

    @pytest.mark.asyncio
    async def test_uri_contains_user_email(self, totp_service, session, user):
        result = await totp_service.setup_totp(session, user.id, user.email)
        uri = unquote(result["provisioning_uri"])
        assert user.email in uri

    @pytest.mark.asyncio
    async def test_stores_encrypted_secret(self, totp_service, session, user):
        result = await totp_service.setup_totp(session, user.id, user.email)
        stmt = select(TotpSecret).where(TotpSecret.id == result["secret_id"])
        secret_row = (await session.execute(stmt)).scalar_one()
        # Encrypted secret should not be the raw base32 value
        assert secret_row.encrypted_secret != ""
        assert secret_row.confirmed is False

    @pytest.mark.asyncio
    async def test_encrypted_secret_is_decryptable(
        self, totp_service, session, user, encryption_key
    ):
        result = await totp_service.setup_totp(session, user.id, user.email)
        stmt = select(TotpSecret).where(TotpSecret.id == result["secret_id"])
        secret_row = (await session.execute(stmt)).scalar_one()
        fernet = Fernet(encryption_key)
        decrypted = fernet.decrypt(secret_row.encrypted_secret.encode()).decode()
        # Should be a valid base32 string
        assert len(decrypted) == 32  # pyotp uses 32-char base32 secrets


# ---------------------------------------------------------------------------
# Confirm tests
# ---------------------------------------------------------------------------


class TestConfirmTotp:
    @pytest.mark.asyncio
    async def test_confirm_with_valid_code(self, totp_service, session, user, encryption_key):
        result = await totp_service.setup_totp(session, user.id, user.email)
        secret_id = result["secret_id"]
        # Decrypt to get the raw secret and generate a valid code
        stmt = select(TotpSecret).where(TotpSecret.id == secret_id)
        secret_row = (await session.execute(stmt)).scalar_one()
        fernet = Fernet(encryption_key)
        raw_secret = fernet.decrypt(secret_row.encrypted_secret.encode()).decode()
        valid_code = pyotp.TOTP(raw_secret).now()

        confirmed = await totp_service.confirm_totp(session, secret_id, valid_code)
        assert confirmed is True

        # Check state was updated
        await session.refresh(secret_row)
        assert secret_row.confirmed is True
        # Check user.mfa_enabled
        stmt_user = select(User).where(User.id == user.id)
        updated_user = (await session.execute(stmt_user)).scalar_one()
        assert updated_user.mfa_enabled is True

    @pytest.mark.asyncio
    async def test_confirm_with_invalid_code(self, totp_service, session, user):
        result = await totp_service.setup_totp(session, user.id, user.email)
        confirmed = await totp_service.confirm_totp(session, result["secret_id"], "000000")
        assert confirmed is False


# ---------------------------------------------------------------------------
# Verify tests
# ---------------------------------------------------------------------------


class TestVerifyTotp:
    @pytest.mark.asyncio
    async def test_verify_valid_code(self, totp_service, session, user, encryption_key):
        result = await totp_service.setup_totp(session, user.id, user.email)
        # Manually confirm the secret
        stmt = select(TotpSecret).where(TotpSecret.id == result["secret_id"])
        secret_row = (await session.execute(stmt)).scalar_one()
        secret_row.confirmed = True
        await session.commit()

        fernet = Fernet(encryption_key)
        raw_secret = fernet.decrypt(secret_row.encrypted_secret.encode()).decode()
        valid_code = pyotp.TOTP(raw_secret).now()

        verified = await totp_service.verify_totp(session, user.id, valid_code)
        assert verified is True

    @pytest.mark.asyncio
    async def test_verify_invalid_code(self, totp_service, session, user):
        result = await totp_service.setup_totp(session, user.id, user.email)
        stmt = select(TotpSecret).where(TotpSecret.id == result["secret_id"])
        secret_row = (await session.execute(stmt)).scalar_one()
        secret_row.confirmed = True
        await session.commit()

        verified = await totp_service.verify_totp(session, user.id, "000000")
        assert verified is False

    @pytest.mark.asyncio
    async def test_verify_no_confirmed_secret(self, totp_service, session, user):
        # Setup but don't confirm
        await totp_service.setup_totp(session, user.id, user.email)
        verified = await totp_service.verify_totp(session, user.id, "123456")
        assert verified is False
