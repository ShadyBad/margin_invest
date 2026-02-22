"""Tests for the WebAuthnService layer."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import User, WebAuthnCredential
from margin_api.services.webauthn import WebAuthnService
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
def webauthn_service() -> WebAuthnService:
    return WebAuthnService(
        rp_id="localhost",
        rp_name="Margin Invest",
        rp_origin="https://localhost",
    )


@pytest_asyncio.fixture()
async def user(session) -> User:
    u = User(
        email="wa@example.com",
        name="watest",
        password_hash="hash",
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


# ---------------------------------------------------------------------------
# Registration options tests
# ---------------------------------------------------------------------------


class TestGenerateRegistrationOptions:
    @pytest.mark.asyncio
    async def test_includes_rp_info(self, webauthn_service, session, user):
        options = await webauthn_service.generate_registration_options(
            session, user.id, user.name, user.email
        )
        assert options["rp"]["name"] == "Margin Invest"
        assert options["rp"]["id"] == "localhost"

    @pytest.mark.asyncio
    async def test_includes_user_info(self, webauthn_service, session, user):
        options = await webauthn_service.generate_registration_options(
            session, user.id, user.name, user.email
        )
        assert options["user"]["name"] == user.name
        assert options["user"]["displayName"] == user.email

    @pytest.mark.asyncio
    async def test_includes_challenge(self, webauthn_service, session, user):
        options = await webauthn_service.generate_registration_options(
            session, user.id, user.name, user.email
        )
        assert "challenge" in options
        assert len(options["challenge"]) > 0

    @pytest.mark.asyncio
    async def test_excludes_existing_credentials(self, webauthn_service, session, user):
        # Add an existing credential
        cred = WebAuthnCredential(
            user_id=user.id,
            credential_id="existing_cred_abc",
            public_key="pk1",
        )
        session.add(cred)
        await session.commit()

        options = await webauthn_service.generate_registration_options(
            session, user.id, user.name, user.email
        )
        exclude_ids = [c["id"] for c in options["excludeCredentials"]]
        assert "existing_cred_abc" in exclude_ids

    @pytest.mark.asyncio
    async def test_empty_exclude_when_no_credentials(self, webauthn_service, session, user):
        options = await webauthn_service.generate_registration_options(
            session, user.id, user.name, user.email
        )
        assert options["excludeCredentials"] == []


# ---------------------------------------------------------------------------
# Authentication options tests
# ---------------------------------------------------------------------------


class TestGenerateAuthenticationOptions:
    @pytest.mark.asyncio
    async def test_includes_allow_credentials(self, webauthn_service, session, user):
        cred = WebAuthnCredential(
            user_id=user.id,
            credential_id="auth_cred_xyz",
            public_key="pk1",
        )
        session.add(cred)
        await session.commit()

        options = await webauthn_service.generate_authentication_options(session, user.id)
        allow_ids = [c["id"] for c in options["allowCredentials"]]
        assert "auth_cred_xyz" in allow_ids

    @pytest.mark.asyncio
    async def test_includes_challenge(self, webauthn_service, session, user):
        options = await webauthn_service.generate_authentication_options(session, user.id)
        assert "challenge" in options
        assert len(options["challenge"]) > 0

    @pytest.mark.asyncio
    async def test_empty_allow_when_no_credentials(self, webauthn_service, session, user):
        options = await webauthn_service.generate_authentication_options(session, user.id)
        assert options["allowCredentials"] == []

    @pytest.mark.asyncio
    async def test_includes_rp_id(self, webauthn_service, session, user):
        options = await webauthn_service.generate_authentication_options(session, user.id)
        assert options["rpId"] == "localhost"


# ---------------------------------------------------------------------------
# Store credential tests
# ---------------------------------------------------------------------------


class TestStoreCredential:
    @pytest.mark.asyncio
    async def test_store_credential(self, webauthn_service, session, user):
        await webauthn_service.store_credential(session, user.id, "new_cred_123", "public_key_data")
        stmt = select(WebAuthnCredential).where(WebAuthnCredential.credential_id == "new_cred_123")
        cred = (await session.execute(stmt)).scalar_one()
        assert cred.user_id == user.id
        assert cred.public_key == "public_key_data"
        assert cred.sign_count == 0

    @pytest.mark.asyncio
    async def test_store_credential_enables_mfa(self, webauthn_service, session, user):
        await webauthn_service.store_credential(session, user.id, "new_cred_456", "public_key_data")
        stmt = select(User).where(User.id == user.id)
        updated_user = (await session.execute(stmt)).scalar_one()
        assert updated_user.mfa_enabled is True
