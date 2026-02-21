"""Tests for security-related auth endpoints (Tasks 9-14).

Covers:
- MFA enforcement on change-password (Task 9)
- Recovery code verify + regenerate (Task 10)
- MFA disable (Task 11)
- Provider linking/unlinking, set/remove password (Task 12)
- Security status (Task 13)
- TOTP confirm returning recovery codes (Task 14)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pyotp
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import LinkedProvider, TotpSecret, User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.services.auth import AuthService
from margin_api.services.recovery_codes import RecoveryCodeService
from margin_api.services.totp import TotpService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_TEST_FERNET_KEY = Fernet.generate_key().decode()
_VALID_PASSWORD = "Str0ng!Pass99"
_auth = AuthService()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def db_setup():
    """Set up in-memory SQLite database with tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


@pytest_asyncio.fixture()
async def credential_user(db_setup):
    """Create a credential user with password and MFA enabled."""
    engine, factory = db_setup
    async with factory() as session:
        user = await _auth.register_user(
            session, "alice", "alice@example.com", _VALID_PASSWORD
        )
        # Enable MFA and set up TOTP
        user.mfa_enabled = True
        user.mfa_grace_deadline = None
        await session.commit()
        await session.refresh(user)
    return engine, factory, user.id


@pytest_asyncio.fixture()
async def oauth_user(db_setup):
    """Create an OAuth-only user (no password)."""
    engine, factory = db_setup
    async with factory() as session:
        user = User(email="oauth@example.com", name="OAuth User")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # Add a linked provider
        lp = LinkedProvider(
            user_id=user.id,
            provider="google",
            oauth_id="google-123",
            provider_email="oauth@example.com",
        )
        session.add(lp)
        await session.commit()
    return engine, factory, user.id


def _make_app(factory, user_id):
    """Create a test app with overridden dependencies."""
    from margin_api.config import Settings, get_settings
    from margin_api.routes.auth import _get_totp_service as _auth_get_totp_service

    app = create_app()

    async def override_db():
        async with factory() as session:
            yield session

    def override_settings():
        return Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            mfa_encryption_key=_TEST_FERNET_KEY,
            api_key_encryption_key=_TEST_FERNET_KEY,
            stripe_secret_key="sk_test_fake",
            stripe_portfolio_price_id="price_portfolio_123",
            stripe_institutional_price_id="price_institutional_456",
            stripe_webhook_secret="whsec_fake",
        )

    def override_totp_service():
        return TotpService(encryption_key=_TEST_FERNET_KEY.encode())

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[_auth_get_totp_service] = override_totp_service
    return app


async def _make_client(app):
    """Create an async test client."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Task 9: MFA enforcement on change-password
# ---------------------------------------------------------------------------


class TestMfaEnforcementOnChangePassword:
    @pytest.mark.asyncio
    async def test_change_password_blocked_when_mfa_required(self, db_setup):
        """User with password, no MFA, and expired grace is blocked."""
        engine, factory = db_setup
        async with factory() as session:
            user = await _auth.register_user(
                session, "bob", "bob@example.com", _VALID_PASSWORD
            )
            user.mfa_grace_deadline = datetime.now(UTC) - timedelta(hours=1)
            await session.commit()
            user_id = user.id

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": _VALID_PASSWORD,
                    "new_password": "NewPassword2@",
                },
            )
        assert resp.status_code == 403
        body = resp.json()
        # The error handler may serialize the detail dict as a string
        detail = body.get("detail", body.get("message", ""))
        if isinstance(detail, dict):
            assert detail["error"] == "mfa_required"
        else:
            assert "mfa_required" in str(detail)

    @pytest.mark.asyncio
    async def test_change_password_allowed_within_grace(self, db_setup):
        """User within grace period can change password."""
        engine, factory = db_setup
        async with factory() as session:
            user = await _auth.register_user(
                session, "carol", "carol@example.com", _VALID_PASSWORD
            )
            user.mfa_grace_deadline = datetime.now(UTC) + timedelta(hours=24)
            await session.commit()
            user_id = user.id

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": _VALID_PASSWORD,
                    "new_password": "NewPassword2@",
                },
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_allowed_with_mfa_enabled(self, credential_user):
        """User with MFA enabled can change password."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": _VALID_PASSWORD,
                    "new_password": "NewPassword2@",
                },
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_oauth_only_user_not_blocked_by_mfa(self, oauth_user):
        """OAuth-only user (no password) is NOT blocked by MFA enforcement.

        The MFA enforcement should pass since OAuth-only users have no password
        requirement. The downstream error (attempting to change a non-existent
        password) is a separate concern — we only verify MFA doesn't block.
        """
        engine, factory, user_id = oauth_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "anything",
                    "new_password": "NewPassword2@",
                },
            )
        # The response should NOT be a 403 with "mfa_required" error.
        # It may be 500 (password_hash is None) or other error, but
        # the MFA enforcement must not be the blocker.
        body = resp.json()
        detail_str = str(body.get("detail", body.get("message", "")))
        assert "mfa_required" not in detail_str


# ---------------------------------------------------------------------------
# Task 10: Recovery code endpoints
# ---------------------------------------------------------------------------


class TestVerifyRecoveryCode:
    @pytest.mark.asyncio
    async def test_verify_recovery_success(self, credential_user):
        """Valid recovery code produces MFA token."""
        engine, factory, user_id = credential_user
        recovery_svc = RecoveryCodeService()
        auth_svc = AuthService()

        # Generate recovery codes and a challenge token
        async with factory() as session:
            codes = await recovery_svc.generate_codes(session, user_id)
            token = await auth_svc.create_challenge_token(session, user_id)

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/verify-recovery",
                json={
                    "user_id": user_id,
                    "code": codes[0],
                    "challenge_token": token,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is True
        assert data["mfa_token"] is not None

    @pytest.mark.asyncio
    async def test_verify_recovery_bad_code(self, credential_user):
        """Invalid recovery code returns 401."""
        engine, factory, user_id = credential_user
        auth_svc = AuthService()

        async with factory() as session:
            token = await auth_svc.create_challenge_token(session, user_id)

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/verify-recovery",
                json={
                    "user_id": user_id,
                    "code": "xxxx-xxxx",
                    "challenge_token": token,
                },
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_recovery_bad_challenge(self, credential_user):
        """Invalid challenge token returns 403."""
        engine, factory, user_id = credential_user

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/verify-recovery",
                json={
                    "user_id": user_id,
                    "code": "xxxx-xxxx",
                    "challenge_token": "invalid-token",
                },
            )
        assert resp.status_code == 403


class TestRegenerateRecoveryCodes:
    @pytest.mark.asyncio
    async def test_regenerate_success(self, credential_user):
        """Regenerate returns 8 new codes."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/regenerate-recovery-codes",
                json={"current_password": _VALID_PASSWORD},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["codes"]) == 8
        # Verify format: xxxx-xxxx
        for code in data["codes"]:
            assert "-" in code
            assert len(code) == 9

    @pytest.mark.asyncio
    async def test_regenerate_wrong_password(self, credential_user):
        """Wrong password returns 401."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/regenerate-recovery-codes",
                json={"current_password": "WrongPassword1!"},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Task 11: MFA disable
# ---------------------------------------------------------------------------


class TestDisableMfa:
    @pytest.mark.asyncio
    async def test_disable_mfa_success(self, credential_user):
        """Disable MFA with valid password and TOTP code."""
        engine, factory, user_id = credential_user
        totp_svc = TotpService(encryption_key=_TEST_FERNET_KEY.encode())

        # Set up a confirmed TOTP secret
        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            result = await totp_svc.setup_totp(session, user_id, user.email)
            secret_id = result["secret_id"]

            # Get the raw secret to generate a code
            secret_row = (
                await session.execute(
                    select(TotpSecret).where(TotpSecret.id == secret_id)
                )
            ).scalar_one()
            raw_secret = totp_svc._decrypt(secret_row.encrypted_secret)
            code = pyotp.TOTP(raw_secret).now()

            # Confirm the TOTP
            await totp_svc.confirm_totp(session, secret_id, code)

        # Generate a fresh TOTP code for the disable request
        valid_code = pyotp.TOTP(raw_secret).now()

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/disable",
                json={
                    "current_password": _VALID_PASSWORD,
                    "totp_code": valid_code,
                },
            )
        assert resp.status_code == 200
        assert resp.json()["mfa_disabled"] is True

        # Verify side effects
        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert user.mfa_enabled is False
            assert user.mfa_grace_deadline is not None

            # TOTP secrets should be deleted
            secrets = (
                await session.execute(
                    select(TotpSecret).where(TotpSecret.user_id == user_id)
                )
            ).scalars().all()
            assert len(secrets) == 0

    @pytest.mark.asyncio
    async def test_disable_mfa_wrong_password(self, credential_user):
        """Wrong password returns 401."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/disable",
                json={
                    "current_password": "WrongPassword1!",
                    "totp_code": "123456",
                },
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_disable_mfa_wrong_totp(self, credential_user):
        """Wrong TOTP code returns 401."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/disable",
                json={
                    "current_password": _VALID_PASSWORD,
                    "totp_code": "000000",
                },
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Task 12: Provider linking
# ---------------------------------------------------------------------------


class TestLinkProvider:
    @pytest.mark.asyncio
    async def test_link_provider_success(self, credential_user):
        """Link a new OAuth provider."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/link-provider",
                json={
                    "provider": "github",
                    "oauth_id": "gh-456",
                    "provider_email": "alice@github.com",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["linked"] is True
        assert data["provider"] == "github"

    @pytest.mark.asyncio
    async def test_link_provider_duplicate(self, credential_user):
        """Linking the same provider+oauth_id twice returns 409."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            await client.post(
                "/api/v1/auth/link-provider",
                json={
                    "provider": "github",
                    "oauth_id": "gh-456",
                    "provider_email": "alice@github.com",
                },
            )
            resp = await client.post(
                "/api/v1/auth/link-provider",
                json={
                    "provider": "github",
                    "oauth_id": "gh-456",
                    "provider_email": "alice@github.com",
                },
            )
        assert resp.status_code == 409


class TestUnlinkProvider:
    @pytest.mark.asyncio
    async def test_unlink_provider_success(self, credential_user):
        """Unlink a provider when user has password (and MFA)."""
        engine, factory, user_id = credential_user

        # First link a provider
        async with factory() as session:
            lp = LinkedProvider(
                user_id=user_id,
                provider="google",
                oauth_id="g-123",
                provider_email="alice@gmail.com",
            )
            session.add(lp)
            await session.commit()

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.delete("/api/v1/auth/unlink-provider/google")
        assert resp.status_code == 200
        assert resp.json()["unlinked"] is True

    @pytest.mark.asyncio
    async def test_unlink_only_method_blocked(self, db_setup):
        """Cannot unlink only sign-in method for OAuth-only user."""
        engine, factory = db_setup
        async with factory() as session:
            user = User(email="only-oauth@example.com", name="Only OAuth")
            session.add(user)
            await session.commit()
            await session.refresh(user)
            lp = LinkedProvider(
                user_id=user.id,
                provider="google",
                oauth_id="g-only",
                provider_email="only-oauth@example.com",
            )
            session.add(lp)
            await session.commit()
            user_id = user.id

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.delete("/api/v1/auth/unlink-provider/google")
        assert resp.status_code == 403
        assert "only sign-in method" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_unlink_requires_mfa_setup(self, db_setup):
        """Cannot unlink provider when user has password but no MFA (expired grace)."""
        engine, factory = db_setup
        async with factory() as session:
            user = await _auth.register_user(
                session, "mfa-needed", "mfa@example.com", _VALID_PASSWORD
            )
            user.mfa_grace_deadline = datetime.now(UTC) - timedelta(hours=1)
            await session.commit()
            lp = LinkedProvider(
                user_id=user.id,
                provider="google",
                oauth_id="g-mfa",
                provider_email="mfa@example.com",
            )
            session.add(lp)
            await session.commit()
            user_id = user.id

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.delete("/api/v1/auth/unlink-provider/google")
        assert resp.status_code == 403
        assert "mfa" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_unlink_nonexistent_provider(self, credential_user):
        """Unlinking a non-linked provider returns 404."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.delete("/api/v1/auth/unlink-provider/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Task 12: Password management
# ---------------------------------------------------------------------------


class TestSetPassword:
    @pytest.mark.asyncio
    async def test_set_password_success(self, oauth_user):
        """OAuth user can set a password."""
        engine, factory, user_id = oauth_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/set-password",
                json={"new_password": _VALID_PASSWORD},
            )
        assert resp.status_code == 200
        assert resp.json()["password_set"] is True

        # Verify user now has password and grace deadline
        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert user.has_password is True
            assert user.mfa_grace_deadline is not None

    @pytest.mark.asyncio
    async def test_set_password_weak(self, oauth_user):
        """Weak password returns 400."""
        engine, factory, user_id = oauth_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/set-password",
                json={"new_password": "weakpassword123"},
            )
        # Either 400 (complexity) or 422 (too short)
        assert resp.status_code in (400, 422)


class TestRemovePassword:
    @pytest.mark.asyncio
    async def test_remove_password_success(self, db_setup):
        """User with password + linked provider can remove password."""
        engine, factory = db_setup
        async with factory() as session:
            user = await _auth.register_user(
                session, "removeme", "removeme@example.com", _VALID_PASSWORD
            )
            lp = LinkedProvider(
                user_id=user.id,
                provider="google",
                oauth_id="g-remove",
                provider_email="removeme@example.com",
            )
            session.add(lp)
            await session.commit()
            user_id = user.id

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/remove-password",
                json={"current_password": _VALID_PASSWORD},
            )
        assert resp.status_code == 200
        assert resp.json()["password_removed"] is True

        # Verify password removed
        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert user.has_password is False
            assert user.mfa_enabled is False
            assert user.mfa_grace_deadline is None

    @pytest.mark.asyncio
    async def test_remove_password_no_provider(self, credential_user):
        """Cannot remove password without a linked provider."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/remove-password",
                json={"current_password": _VALID_PASSWORD},
            )
        assert resp.status_code == 403
        assert "provider" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_remove_password_wrong_password(self, db_setup):
        """Wrong current password returns 401."""
        engine, factory = db_setup
        async with factory() as session:
            user = await _auth.register_user(
                session, "wrongpw", "wrongpw@example.com", _VALID_PASSWORD
            )
            lp = LinkedProvider(
                user_id=user.id,
                provider="google",
                oauth_id="g-wrongpw",
                provider_email="wrongpw@example.com",
            )
            session.add(lp)
            await session.commit()
            user_id = user.id

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/remove-password",
                json={"current_password": "WrongPassword1!"},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Task 13: Security status
# ---------------------------------------------------------------------------


class TestSecurityStatus:
    @pytest.mark.asyncio
    async def test_security_status_credential_user(self, credential_user):
        """Credential user with MFA sees correct status."""
        engine, factory, user_id = credential_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.get("/api/v1/auth/security-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_password"] is True
        assert data["mfa_enabled"] is True
        assert data["mfa_method"] == "totp"
        assert data["recovery_codes_remaining"] == 0
        assert isinstance(data["linked_providers"], list)

    @pytest.mark.asyncio
    async def test_security_status_oauth_user(self, oauth_user):
        """OAuth user sees correct status."""
        engine, factory, user_id = oauth_user
        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.get("/api/v1/auth/security-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_password"] is False
        assert data["mfa_enabled"] is False
        assert data["mfa_method"] is None
        assert len(data["linked_providers"]) == 1
        assert data["linked_providers"][0]["provider"] == "google"

    @pytest.mark.asyncio
    async def test_security_status_with_recovery_codes(self, credential_user):
        """Recovery codes remaining shows correct count."""
        engine, factory, user_id = credential_user
        recovery_svc = RecoveryCodeService()

        async with factory() as session:
            await recovery_svc.generate_codes(session, user_id)

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.get("/api/v1/auth/security-status")
        assert resp.status_code == 200
        assert resp.json()["recovery_codes_remaining"] == 8


# ---------------------------------------------------------------------------
# Task 14: TOTP confirm returns recovery codes
# ---------------------------------------------------------------------------


class TestConfirmTotpWithRecoveryCodes:
    @pytest.mark.asyncio
    async def test_confirm_totp_returns_recovery_codes(self, credential_user):
        """Confirming TOTP generates and returns recovery codes."""
        engine, factory, user_id = credential_user
        totp_svc = TotpService(encryption_key=_TEST_FERNET_KEY.encode())

        # Set up an unconfirmed TOTP secret
        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            result = await totp_svc.setup_totp(session, user_id, user.email)
            secret_id = result["secret_id"]

            # Get the raw secret to generate a valid code
            secret_row = (
                await session.execute(
                    select(TotpSecret).where(TotpSecret.id == secret_id)
                )
            ).scalar_one()
            raw_secret = totp_svc._decrypt(secret_row.encrypted_secret)
            code = pyotp.TOTP(raw_secret).now()

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/confirm-totp",
                json={"secret_id": secret_id, "code": code},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confirmed"] is True
        assert len(data["recovery_codes"]) == 8

    @pytest.mark.asyncio
    async def test_confirm_totp_wrong_code_no_recovery_codes(self, credential_user):
        """Failed TOTP confirmation returns no recovery codes."""
        engine, factory, user_id = credential_user
        totp_svc = TotpService(encryption_key=_TEST_FERNET_KEY.encode())

        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            result = await totp_svc.setup_totp(session, user_id, user.email)
            secret_id = result["secret_id"]

        app = _make_app(factory, user_id)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/mfa/confirm-totp",
                json={"secret_id": secret_id, "code": "000000"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confirmed"] is False
        assert data["recovery_codes"] == []


# ---------------------------------------------------------------------------
# Not authenticated tests
# ---------------------------------------------------------------------------


class TestUnauthenticatedAccess:
    @pytest.mark.asyncio
    async def test_security_status_requires_auth(self, db_setup):
        """Security status without auth header returns 401."""
        engine, factory = db_setup
        app = create_app()

        async def override_db():
            async with factory() as session:
                yield session

        def override_settings():
            from margin_api.config import Settings

            return Settings(
                database_url="sqlite+aiosqlite:///:memory:",
                mfa_encryption_key=_TEST_FERNET_KEY,
                api_key_encryption_key=_TEST_FERNET_KEY,
                stripe_secret_key="sk_test_fake",
                stripe_portfolio_price_id="price_portfolio_123",
                stripe_institutional_price_id="price_institutional_456",
                stripe_webhook_secret="whsec_fake",
            )

        from margin_api.config import get_settings

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_settings] = override_settings
        # Do NOT override get_current_user_id — it should fail

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/security-status")
        assert resp.status_code == 401
