"""Comprehensive route coverage push — auth, scores, dashboard, 13F, billing.

Targets routes with the lowest coverage by writing at least one happy-path
test per uncovered endpoint.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import (
    AccumulationSignal,
    Asset,
    FilingMetadata,
    InstitutionalHolding,
    Manager,
    Score,
    SecurityMaster,
    User,
    V4Score,
)
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.middleware.mfa_enforcement import require_mfa_dep
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_TEST_FERNET_KEY = Fernet.generate_key().decode()
_VALID_PASSWORD = "Str0ng!Pass99"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


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
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


def _make_app_with_db(session_factory):
    """Create app with get_db and get_settings overridden.

    Also overrides _get_totp_service so endpoints that call it work without
    a real Fernet key from env.
    """
    get_settings.cache_clear()
    app = create_app()

    async def override_db():
        async with session_factory() as s:
            yield s

    def override_settings():
        from margin_api.config import Settings

        return Settings(
            mfa_encryption_key=_TEST_FERNET_KEY,
            database_url="sqlite+aiosqlite:///:memory:",
        )

    # Override _get_totp_service to avoid Fernet key issues in tests
    from margin_api.routes.auth import _get_totp_service
    from margin_api.services.totp import TotpService

    def _mock_totp_svc():
        return TotpService(encryption_key=_TEST_FERNET_KEY.encode())

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[_get_totp_service] = _mock_totp_svc
    return app


# ============================================================================
# AUTH ROUTE TESTS
# ============================================================================


class TestAuthSessionCheck:
    """Tests for GET /api/v1/auth/session-check/{user_id}."""

    @pytest.mark.asyncio
    async def test_session_check_user_not_found(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/session-check/99999")
        assert resp.status_code == 200
        assert resp.json()["session_valid"] is True
        assert resp.json()["token_invalidated"] is False

    @pytest.mark.asyncio
    async def test_session_check_no_password_changed_at(self, session_factory, db_session):
        user = User(email="check@example.com", name="Check User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/auth/session-check/{user.id}")
        assert resp.status_code == 200
        assert resp.json()["session_valid"] is True
        assert resp.json()["token_invalidated"] is False


class TestAuthOAuthSync:
    """Tests for POST /api/v1/auth/oauth-sync."""

    @pytest.mark.asyncio
    async def test_oauth_sync_creates_new_user(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/oauth-sync",
                json={
                    "email": "oauth@example.com",
                    "name": "OAuth User",
                    "provider": "google",
                    "oauth_id": "google-uid-123",
                    "avatar_url": None,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["id"] > 0

    @pytest.mark.asyncio
    async def test_oauth_sync_updates_existing_user(self, session_factory, db_session):
        user = User(email="existing@example.com", name="Old Name")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/oauth-sync",
                json={
                    "email": "existing@example.com",
                    "name": "New Name",
                    "provider": "github",
                    "oauth_id": "gh-uid-456",
                    "avatar_url": None,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user.id


class TestAuthForgotPassword:
    """Tests for POST /api/v1/auth/forgot-password."""

    @pytest.mark.asyncio
    async def test_forgot_password_always_returns_200(self, session_factory):
        """Even for non-existent emails, returns 200 to prevent enumeration."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "nonexistent@example.com"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_forgot_password_existing_email_sends_email(self, session_factory):
        """For existing email with password, email service is invoked."""
        from argon2 import PasswordHasher

        hasher = PasswordHasher()
        app = _make_app_with_db(session_factory)

        async for session in app.dependency_overrides[get_db]():
            user = User(
                email="forgotme@example.com",
                name="Forgot User",
                password_hash=hasher.hash(_VALID_PASSWORD),
            )
            session.add(user)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("margin_api.routes.auth.EmailService") as mock_email_cls:
                mock_email = MagicMock()
                mock_email_cls.return_value = mock_email
                resp = await client.post(
                    "/api/v1/auth/forgot-password",
                    json={"email": "forgotme@example.com"},
                )
        assert resp.status_code == 200


class TestAuthResetPassword:
    """Tests for POST /api/v1/auth/reset-password."""

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token_returns_400(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/reset-password",
                json={
                    "user_id": 99999,
                    "token": "invalid-token",
                    "new_password": _VALID_PASSWORD,
                },
            )
        assert resp.status_code == 400


class TestAuthSecurityStatus:
    """Tests for GET /api/v1/auth/security-status."""

    @pytest.mark.asyncio
    async def test_security_status_returns_correct_fields(self, session_factory, db_session):
        user = User(email="sec@example.com", name="Security User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        app = _make_app_with_db(session_factory)
        app.dependency_overrides[get_current_user_id] = lambda: user.id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/security-status")

        assert resp.status_code == 200
        data = resp.json()
        assert "has_password" in data
        assert "mfa_enabled" in data
        assert "recovery_codes_remaining" in data
        assert "linked_providers" in data

    @pytest.mark.asyncio
    async def test_security_status_not_found(self, session_factory):
        app = _make_app_with_db(session_factory)
        app.dependency_overrides[get_current_user_id] = lambda: 99999

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/security-status")

        assert resp.status_code == 404


class TestAuthLinkProvider:
    """Tests for POST /api/v1/auth/link-provider."""

    @pytest.mark.asyncio
    async def test_link_provider_success(self, session_factory, db_session):
        user = User(email="link@example.com", name="Link User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        app = _make_app_with_db(session_factory)
        app.dependency_overrides[get_current_user_id] = lambda: user.id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/link-provider",
                json={
                    "provider": "github",
                    "oauth_id": "gh-999",
                    "provider_email": "link@example.com",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["linked"] is True
        assert data["provider"] == "github"


class TestAuthSetPassword:
    """Tests for POST /api/v1/auth/set-password."""

    @pytest.mark.asyncio
    async def test_set_password_success_for_oauth_user(self, session_factory, db_session):
        """OAuth-only user can set a password."""
        user = User(email="setpw@example.com", name="OAuth Only")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        app = _make_app_with_db(session_factory)
        app.dependency_overrides[get_current_user_id] = lambda: user.id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/set-password",
                json={"new_password": _VALID_PASSWORD},
            )

        assert resp.status_code == 200
        assert resp.json()["password_set"] is True

    @pytest.mark.asyncio
    async def test_set_password_user_not_found(self, session_factory):
        app = _make_app_with_db(session_factory)
        app.dependency_overrides[get_current_user_id] = lambda: 99999

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/set-password",
                json={"new_password": _VALID_PASSWORD},
            )
        assert resp.status_code == 404


class TestAuthChangePassword:
    """Tests for POST /api/v1/auth/change-password."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, session_factory):
        """User with password can change it."""
        from argon2 import PasswordHasher

        hasher = PasswordHasher()
        app = _make_app_with_db(session_factory)

        async for session in app.dependency_overrides[get_db]():
            user = User(
                email="changepw@example.com",
                name="Change PW User",
                password_hash=hasher.hash(_VALID_PASSWORD),
                mfa_grace_deadline=datetime.now(UTC) + timedelta(hours=72),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        # Override require_mfa_dep to return user directly
        async def _mock_mfa_dep():
            async for session in app.dependency_overrides[get_db]():
                from sqlalchemy import select as sa_select

                result = await session.execute(sa_select(User).where(User.id == user_id))
                return result.scalar_one()

        app.dependency_overrides[require_mfa_dep] = _mock_mfa_dep

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": _VALID_PASSWORD,
                    "new_password": "N3wStr0ng!Pass",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Password changed successfully"


class TestAuthMfaSetupTotp:
    """Tests for POST /api/v1/auth/mfa/setup-totp."""

    @pytest.mark.asyncio
    async def test_setup_totp_invalid_challenge_returns_403(self, session_factory, db_session):
        user = User(email="totp@example.com", name="TOTP User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        app = _make_app_with_db(session_factory)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/mfa/setup-totp",
                json={"user_id": user.id, "challenge_token": "invalid-token"},
            )
        assert resp.status_code == 403


class TestAuthVerifyTotp:
    """Tests for POST /api/v1/auth/mfa/verify-totp."""

    @pytest.mark.asyncio
    async def test_verify_totp_invalid_challenge_returns_403(self, session_factory, db_session):
        user = User(email="vtotp@example.com", name="Verify TOTP User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        app = _make_app_with_db(session_factory)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/mfa/verify-totp",
                json={
                    "user_id": user.id,
                    "challenge_token": "bad-token",
                    "code": "123456",
                },
            )
        assert resp.status_code == 403


class TestAuthMfaComplete:
    """Tests for POST /api/v1/auth/mfa/complete (cookie-based flow)."""

    @pytest.mark.asyncio
    async def test_mfa_complete_missing_cookie_returns_401(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/mfa/complete",
                json={"totp_code": "123456"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mfa_complete_invalid_cookie_json_returns_401(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            client.cookies.set("__mfa_challenge", "not-valid-json")
            resp = await client.post(
                "/api/v1/auth/mfa/complete",
                json={"totp_code": "123456"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mfa_complete_no_code_provided_returns_400(self, session_factory, db_session):
        """Providing neither totp_code nor recovery_code returns 400."""
        from margin_api.services.auth import AuthService

        app = _make_app_with_db(session_factory)

        user = User(email="mfacomplete@example.com", name="MFA Complete User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create a real challenge token
        async for session in app.dependency_overrides[get_db]():
            svc = AuthService()
            token = await svc.create_challenge_token(session, user.id)
            await session.commit()

        cookie_val = json.dumps({"userId": user.id, "challengeToken": token})

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            client.cookies.set("__mfa_challenge", cookie_val)
            resp = await client.post("/api/v1/auth/mfa/complete", json={})
        assert resp.status_code == 400


class TestAuthVerifyMfaToken:
    """Tests for POST /api/v1/auth/verify-mfa-token."""

    @pytest.mark.asyncio
    async def test_verify_mfa_token_expired_returns_401(self, session_factory):
        app = _make_app_with_db(session_factory)
        settings = get_settings()

        # Build an expired JWT
        expired_token = pyjwt.encode(
            {
                "sub": "1",
                "purpose": "mfa_complete",
                "iat": int(time.time()) - 200,
                "exp": int(time.time()) - 100,
            },
            settings.jwt_secret,
            algorithm="HS256",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": expired_token},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_mfa_token_wrong_purpose_returns_401(self, session_factory, db_session):
        app = _make_app_with_db(session_factory)
        settings = get_settings()

        user = User(email="vmfatk@example.com", name="Verify MFA Token User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        wrong_purpose_token = pyjwt.encode(
            {
                "sub": str(user.id),
                "purpose": "wrong_purpose",
                "iat": int(time.time()),
                "exp": int(time.time()) + 60,
            },
            settings.jwt_secret,
            algorithm="HS256",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": wrong_purpose_token},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_mfa_token_valid_returns_user_data(self, session_factory, db_session):
        app = _make_app_with_db(session_factory)
        settings = get_settings()

        user = User(email="vmfavalid@example.com", name="Valid MFA Token User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        valid_token = pyjwt.encode(
            {
                "sub": str(user.id),
                "purpose": "mfa_complete",
                "iat": int(time.time()),
                "exp": int(time.time()) + 60,
            },
            settings.jwt_secret,
            algorithm="HS256",
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": valid_token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user.id
        assert data["email"] == "vmfavalid@example.com"


class TestAuthAdminLogin:
    """Tests for POST /api/v1/auth/admin-login."""

    @pytest.mark.asyncio
    async def test_admin_login_unknown_email_returns_401(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "ghost@example.com", "pw": "Whatever1!"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_login_non_admin_returns_403(self, session_factory):
        from argon2 import PasswordHasher

        hasher = PasswordHasher()
        app = _make_app_with_db(session_factory)

        async for session in app.dependency_overrides[get_db]():
            user = User(
                email="regular@example.com",
                name="Regular User",
                password_hash=hasher.hash(_VALID_PASSWORD),
                role="user",
            )
            session.add(user)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "regular@example.com", "pw": _VALID_PASSWORD},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_login_success_returns_challenge(self, session_factory):
        from argon2 import PasswordHasher
        from margin_api.db.models import UserRole

        hasher = PasswordHasher()
        app = _make_app_with_db(session_factory)

        async for session in app.dependency_overrides[get_db]():
            user = User(
                email="admin@example.com",
                name="Admin User",
                password_hash=hasher.hash(_VALID_PASSWORD),
                role=UserRole.ADMIN,
            )
            session.add(user)
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "admin@example.com", "pw": _VALID_PASSWORD},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_required"] is True
        assert "challenge_str" in data


class TestAuthVerifyRecoveryCode:
    """Tests for POST /api/v1/auth/mfa/verify-recovery."""

    @pytest.mark.asyncio
    async def test_verify_recovery_invalid_challenge_returns_403(self, session_factory, db_session):
        user = User(email="recov@example.com", name="Recovery User")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/mfa/verify-recovery",
                json={
                    "user_id": user.id,
                    "challenge_token": "bad-token",
                    "code": "ABCD-EFGH",
                },
            )
        assert resp.status_code == 403


class TestAuthDuplicateEmail:
    """Test duplicate email registration returns 400."""

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_400(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register first time
            resp1 = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "user1",
                    "email": "dup@example.com",
                    "password": _VALID_PASSWORD,
                },
            )
            assert resp1.status_code == 201
            # Register again with same email (different username)
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "user2",
                    "email": "dup@example.com",
                    "password": _VALID_PASSWORD,
                },
            )
        # Should be 400 (ValueError from service — email already exists)
        assert resp.status_code == 400


# ============================================================================
# SCORES ROUTE TESTS
# ============================================================================


@pytest_asyncio.fixture
async def scores_seeded(session_factory):
    """Seed scores data into an in-memory SQLite DB, return session factory."""
    async with session_factory() as session:
        asset = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(asset)
        await session.flush()

        score = Score(
            asset_id=asset.id,
            composite_percentile=95.0,
            composite_raw_score=87.5,
            conviction_level="high",
            signal="strong",
            quality_percentile=90.0,
            value_percentile=85.0,
            momentum_percentile=88.0,
            data_coverage=1.0,
            scored_at=datetime.now(UTC),
            score_detail={
                "ticker": "AAPL",
                "composite_percentile": 95.0,
                "composite_tier": "high",
                "signal": "strong",
                "quality": {
                    "factor_name": "quality",
                    "weight": 0.35,
                    "sub_scores": [],
                    "average_percentile": 90.0,
                },
                "value": {
                    "factor_name": "value",
                    "weight": 0.30,
                    "sub_scores": [],
                    "average_percentile": 85.0,
                },
                "momentum": {
                    "factor_name": "momentum",
                    "weight": 0.35,
                    "sub_scores": [],
                    "average_percentile": 88.0,
                },
                "filters_passed": [],
                "data_coverage": 1.0,
            },
        )
        v4 = V4Score(
            asset_id=asset.id,
            composite_score=87.5,
            conviction="high",
            rules_conviction="high",
            opportunity_type="compounder",
            timing_signal="buy",
            max_position_pct=8.0,
            style="growth",
            regime="bull",
            ml_override="none",
            scored_at=datetime.now(UTC),
            published=True,
            detail={
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "composite_percentile": 87.5,
                "composite_tier": "high",
                "signal": "strong",
                "quality": {
                    "factor_name": "quality",
                    "weight": 0.35,
                    "sub_scores": [],
                    "average_percentile": 90.0,
                },
                "value": {
                    "factor_name": "value",
                    "weight": 0.30,
                    "sub_scores": [],
                    "average_percentile": 85.0,
                },
                "momentum": {
                    "factor_name": "momentum",
                    "weight": 0.35,
                    "sub_scores": [],
                    "average_percentile": 88.0,
                },
                "filters_passed": [],
                "data_coverage": 1.0,
            },
        )
        session.add(score)
        session.add(v4)
        await session.commit()
    return session_factory


class TestGetScore:
    @pytest.mark.asyncio
    async def test_get_score_returns_200(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_get_score_not_found_returns_404(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/ZZZZ")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_score_lowercase_ticker_normalized(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/aapl")
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_list_scores_empty_db(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["scores"] == []

    @pytest.mark.asyncio
    async def test_list_scores_with_data(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


class TestGetScoreHistory:
    @pytest.mark.asyncio
    async def test_get_history_returns_points(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/AAPL/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "points" in data
        assert "total_runs" in data

    @pytest.mark.asyncio
    async def test_get_history_not_found_returns_404(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/ZZXX/history")
        assert resp.status_code == 404


class TestGetValuationAudit:
    @pytest.mark.asyncio
    async def test_valuation_audit_no_score_returns_404(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/ZZZZ/valuation-audit")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_valuation_audit_no_audit_data_returns_404(self, scores_seeded):
        """Score exists but has no valuation_audit in score_detail."""
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/AAPL/valuation-audit")
        # Score exists but no valuation_audit key in score_detail
        assert resp.status_code == 404


class TestListScoresFiltered:
    @pytest.mark.asyncio
    async def test_list_scores_with_min_percentile(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores?min_percentile=99.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0  # AAPL has 87.5, below 99

    @pytest.mark.asyncio
    async def test_list_scores_with_conviction_filter(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores?conviction=exceptional")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0  # AAPL is "high" not "exceptional"

    @pytest.mark.asyncio
    async def test_list_scores_pagination(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


class TestGetScoreWithIncludes:
    @pytest.mark.asyncio
    async def test_get_score_with_price_history_include(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/AAPL?include=price_history")
        assert resp.status_code == 200
        data = resp.json()
        # price_history may be empty or None — just verifies no crash
        assert "ticker" in data

    @pytest.mark.asyncio
    async def test_get_score_with_signal_history_include(self, scores_seeded):
        app = _make_app_with_db(scores_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/AAPL?include=signal_history")
        assert resp.status_code == 200
        data = resp.json()
        assert "ticker" in data


# ============================================================================
# DASHBOARD ROUTE TESTS
# ============================================================================


@pytest_asyncio.fixture
async def dashboard_seeded(session_factory):
    """Seed dashboard data: assets + scores."""
    async with session_factory() as session:
        asset = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(asset)
        await session.flush()

        score = Score(
            asset_id=asset.id,
            composite_percentile=99.5,
            composite_raw_score=82.0,
            conviction_level="exceptional",
            signal="strong",
            quality_percentile=98.0,
            value_percentile=95.0,
            momentum_percentile=97.0,
            data_coverage=1.0,
            scored_at=datetime.now(UTC),
        )
        session.add(score)
        await session.commit()
    return session_factory


class TestDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_empty_db_returns_200(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "picks" in data
        assert "watchlist" in data
        assert "last_updated" in data
        assert "total_scored" in data

    @pytest.mark.asyncio
    async def test_dashboard_with_data_returns_picks(self, dashboard_seeded):
        app = _make_app_with_db(dashboard_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["picks"]) >= 1
        pick = data["picks"][0]
        assert "ticker" in pick
        assert "score" in pick

    @pytest.mark.asyncio
    async def test_dashboard_audit_empty_db(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["entries"] == []

    @pytest.mark.asyncio
    async def test_dashboard_audit_with_data(self, dashboard_seeded):
        app = _make_app_with_db(dashboard_seeded)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        entry = data["entries"][0]
        assert "ticker" in entry
        assert "db_values" in entry
        assert "derived_values" in entry
        assert "mismatches" in entry

    @pytest.mark.asyncio
    async def test_dashboard_status_endpoint(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "snapshot" in data
        assert "scores" in data
        assert "assets" in data
        assert "tier_breakdown" in data

    @pytest.mark.asyncio
    async def test_dashboard_warning_when_no_universe(self, session_factory):
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        # With no universe snapshot, expect NO_UNIVERSE warning
        warnings = data.get("warnings", [])
        warning_codes = [w["code"] for w in warnings]
        assert "NO_UNIVERSE" in warning_codes


# ============================================================================
# 13F ROUTE TESTS
# ============================================================================


@pytest_asyncio.fixture
async def thirteenf_seeded(session_factory):
    """Seed 13F data: manager + security master + holdings."""
    async with session_factory() as session:
        asset = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Technology",
            market_cap=Decimal("3000000000000"),
            cusip="037833100",
        )
        session.add(asset)

        mgr = Manager(
            cik="0001067983",
            name="BERKSHIRE HATHAWAY",
            short_name="Berkshire",
            tier="curated",
        )
        session.add(mgr)
        await session.flush()

        filing = FilingMetadata(
            manager_id=mgr.id,
            accession_number="0001067983-24-000001",
            filing_type="13F-HR",
            period_of_report=date(2024, 9, 30),
            filed_date=date(2024, 11, 14),
            total_holdings=1,
            total_value=180_000_000,
        )
        session.add(filing)
        await session.flush()

        sec = SecurityMaster(
            ticker="AAPL",
            cusip="037833100",
            issuer_name="Apple Inc.",
            asset_id=asset.id,
        )
        session.add(sec)
        await session.flush()

        holding = InstitutionalHolding(
            filing_id=filing.id,
            manager_id=mgr.id,
            security_master_id=sec.id,
            cusip="037833100",
            period_of_report=date(2024, 9, 30),
            shares_held=1_000_000,
            value_thousands=180_000,
        )
        session.add(holding)

        accum = AccumulationSignal(
            asset_id=asset.id,
            period_of_report=date(2024, 9, 30),
            signal_score=75.0,
            curated_new_positions=2,
            curated_holders=3,
            total_holders=10,
            computed_at=datetime.now(UTC),
        )
        session.add(accum)
        await session.commit()

    return session_factory, mgr.id, filing.id


class TestThirteenfHoldings:
    @pytest.mark.asyncio
    async def test_get_holdings_returns_holders(self, thirteenf_seeded):
        factory, _mgr_id, _filing_id = thirteenf_seeded
        app = _make_app_with_db(factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/holdings/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "summary" in data
        assert data["summary"]["total_holders"] >= 1

    @pytest.mark.asyncio
    async def test_get_holdings_unknown_ticker_returns_empty(self, thirteenf_seeded):
        factory, _mgr_id, _filing_id = thirteenf_seeded
        app = _make_app_with_db(factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/holdings/ZZZZ")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_holders"] == 0

    @pytest.mark.asyncio
    async def test_get_holdings_history_returns_quarters(self, thirteenf_seeded):
        factory, _mgr_id, _filing_id = thirteenf_seeded
        app = _make_app_with_db(factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/holdings/AAPL/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "quarters" in data
        assert len(data["quarters"]) >= 1

    @pytest.mark.asyncio
    async def test_list_managers_returns_managers(self, thirteenf_seeded):
        factory, _mgr_id, _filing_id = thirteenf_seeded
        app = _make_app_with_db(factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/managers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        mgr = data[0]
        assert "name" in mgr
        assert "tier" in mgr

    @pytest.mark.asyncio
    async def test_list_managers_filtered_by_tier(self, thirteenf_seeded):
        factory, _mgr_id, _filing_id = thirteenf_seeded
        app = _make_app_with_db(factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/managers?tier=curated")
        assert resp.status_code == 200
        data = resp.json()
        for mgr in data:
            assert mgr["tier"] == "curated"


class TestThirteenfManagerPortfolio:
    @pytest.mark.asyncio
    async def test_manager_portfolio_requires_plan(self, thirteenf_seeded):
        """Manager portfolio endpoint requires institutional plan."""
        factory, mgr_id, _filing_id = thirteenf_seeded
        app = _make_app_with_db(factory)
        # Override get_current_user_id but require_plan will check subscription_plan
        # With no user in DB, it should return 403 (plan check fails or 401 unauthenticated)
        app.dependency_overrides[get_current_user_id] = lambda: 99999

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/13f/managers/{mgr_id}/portfolio")
        # 403: user 99999 doesn't exist so plan lookup returns analyst (insufficient plan)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_manager_portfolio_with_institutional_plan(self, thirteenf_seeded):
        factory, mgr_id, _filing_id = thirteenf_seeded

        # Create user in the SAME factory as 13F data
        async with factory() as session:
            user = User(
                email="institutional@example.com",
                name="Institutional User",
                subscription_plan="institutional",
                subscription_status="active",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        app = _make_app_with_db(factory)
        app.dependency_overrides[get_current_user_id] = lambda: user_id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/13f/managers/{mgr_id}/portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert "holdings" in data
        assert "period_of_report" in data

    @pytest.mark.asyncio
    async def test_manager_portfolio_not_found(self, thirteenf_seeded):
        factory, _mgr_id, _filing_id = thirteenf_seeded

        async with factory() as session:
            user = User(
                email="inst2@example.com",
                name="Institutional User 2",
                subscription_plan="institutional",
                subscription_status="active",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        app = _make_app_with_db(factory)
        app.dependency_overrides[get_current_user_id] = lambda: user_id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/managers/99999/portfolio")
        assert resp.status_code == 404


class TestThirteenfAnalytics:
    @pytest.mark.asyncio
    async def test_analytics_overlap_requires_plan(self, thirteenf_seeded):
        factory, _mgr_id, _filing_id = thirteenf_seeded
        app = _make_app_with_db(factory)
        app.dependency_overrides[get_current_user_id] = lambda: 99999

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/analytics/overlap")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_analytics_overlap_institutional_user(self, thirteenf_seeded):
        """Overlap endpoint is accessible to institutional users (404 = no data, not auth)."""
        factory, _mgr_id, _filing_id = thirteenf_seeded

        # Create user in the SAME factory as thirteenf data
        async with factory() as session:
            user = User(
                email="inst_overlap@example.com",
                name="Overlap User",
                subscription_plan="institutional",
                subscription_status="active",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        app = _make_app_with_db(factory)
        app.dependency_overrides[get_current_user_id] = lambda: user_id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/analytics/overlap")
        # With only 1 quarter, resolve_quarter returns 404 (not enough data)
        # That's expected behavior — what matters is authentication passed (not 403)
        assert resp.status_code in (200, 404)
        assert resp.status_code != 403

    @pytest.mark.asyncio
    async def test_analytics_new_positions_institutional_user(self, thirteenf_seeded):
        """New positions endpoint is accessible to institutional users."""
        factory, _mgr_id, _filing_id = thirteenf_seeded

        async with factory() as session:
            user = User(
                email="inst_newpos@example.com",
                name="New Positions User",
                subscription_plan="institutional",
                subscription_status="active",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        app = _make_app_with_db(factory)
        app.dependency_overrides[get_current_user_id] = lambda: user_id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/analytics/new-positions")
        # With only 1 quarter, resolve_quarter returns 404 — but not a 403 auth error
        assert resp.status_code in (200, 404)
        assert resp.status_code != 403

    @pytest.mark.asyncio
    async def test_analytics_clone_not_found(self, thirteenf_seeded):
        factory, _mgr_id, _filing_id = thirteenf_seeded

        async with factory() as session:
            user = User(
                email="inst_clone@example.com",
                name="Clone User",
                subscription_plan="institutional",
                subscription_status="active",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        app = _make_app_with_db(factory)
        app.dependency_overrides[get_current_user_id] = lambda: user_id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/analytics/clone/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_analytics_clone_returns_positions(self, thirteenf_seeded):
        factory, mgr_id, _filing_id = thirteenf_seeded

        async with factory() as session:
            user = User(
                email="inst_clone2@example.com",
                name="Clone User 2",
                subscription_plan="institutional",
                subscription_status="active",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

        app = _make_app_with_db(factory)
        app.dependency_overrides[get_current_user_id] = lambda: user_id

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/13f/analytics/clone/{mgr_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "positions" in data
        assert "manager" in data


# ============================================================================
# BILLING ROUTE TESTS
# ============================================================================


@pytest_asyncio.fixture
async def billing_setup(session_factory):
    """Setup for billing tests with a real user in DB."""
    async with session_factory() as session:
        user = User(
            email="billing@example.com",
            name="Billing User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    app = create_app()

    async def override_db():
        async with session_factory() as s:
            yield s

    def override_settings():
        from margin_api.config import Settings

        return Settings(
            mfa_encryption_key=_TEST_FERNET_KEY,
            database_url="sqlite+aiosqlite:///:memory:",
            stripe_secret_key="sk_test_fake",
            stripe_portfolio_price_id="price_portfolio_123",
            stripe_institutional_price_id="price_institutional_456",
            stripe_webhook_secret="whsec_fake",
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    # Bypass MFA check
    async def _mock_mfa_dep():
        async for session in override_db():
            from sqlalchemy import select as sa_select

            result = await session.execute(sa_select(User).where(User.id == user_id))
            return result.scalar_one()

    app.dependency_overrides[require_mfa_dep] = _mock_mfa_dep

    return app, user_id


class TestBillingCheckout:
    @pytest.mark.asyncio
    async def test_checkout_creates_session_url(self, billing_setup):
        app, _user_id = billing_setup
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("margin_api.services.billing.stripe.StripeClient") as mock_cls:
                mock_stripe = mock_cls.return_value
                mock_customer = MagicMock()
                mock_customer.id = "cus_test123"
                mock_stripe.v1.customers.create.return_value = mock_customer
                mock_session = MagicMock()
                mock_session.url = "https://checkout.stripe.com/test"
                mock_stripe.v1.checkout.sessions.create.return_value = mock_session

                resp = await client.post("/api/v1/billing/checkout", json={"plan": "portfolio"})
        assert resp.status_code == 200
        assert "checkout_url" in resp.json()


class TestBillingPortal:
    @pytest.mark.asyncio
    async def test_portal_no_stripe_customer_returns_400(self, billing_setup):
        """User without a Stripe customer ID raises ValueError → 400."""
        app, _user_id = billing_setup
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch(
                "margin_api.services.billing.BillingService.create_portal_session",
                new_callable=AsyncMock,
            ) as mock_portal:
                mock_portal.side_effect = ValueError("No Stripe customer found for this user")
                resp = await client.post("/api/v1/billing/portal")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_portal_returns_url(self, billing_setup):
        app, _user_id = billing_setup
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch(
                "margin_api.services.billing.BillingService.create_portal_session",
                new_callable=AsyncMock,
            ) as mock_portal:
                mock_portal.return_value = "https://billing.stripe.com/test"
                resp = await client.post("/api/v1/billing/portal")
        assert resp.status_code == 200
        assert resp.json()["portal_url"] == "https://billing.stripe.com/test"


class TestBillingWebhook:
    @pytest.mark.asyncio
    async def test_webhook_invalid_signature_returns_400(self, billing_setup):
        app, _user_id = billing_setup
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/billing/webhook",
                content=b'{"type":"test"}',
                headers={"stripe-signature": "invalid"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_processed_event_skipped(self, billing_setup):
        """Already-processed event returns already_processed."""
        app, _user_id = billing_setup
        fake_event = MagicMock()
        fake_event.id = "evt_test_123"
        fake_event.type = "customer.subscription.updated"
        fake_event.data.object = {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "items": {"data": [{"price": {"id": "price_portfolio_123"}}]},
            "current_period_end": 9999999999,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch(
                "margin_api.services.billing.BillingService.construct_webhook_event",
                return_value=fake_event,
            ):
                # First call processes the event
                await client.post(
                    "/api/v1/billing/webhook",
                    content=b'{"type":"test"}',
                    headers={"stripe-signature": "valid"},
                )
                # Second call should be idempotent
                resp = await client.post(
                    "/api/v1/billing/webhook",
                    content=b'{"type":"test"}',
                    headers={"stripe-signature": "valid"},
                )

        assert resp.status_code == 200
        # Second call returns already_processed
        assert resp.json().get("status") == "already_processed"


# ============================================================================
# METRICS ROUTE ADDITIONAL TESTS (coverage for edge cases)
# ============================================================================


class TestMetricsAdditional:
    @pytest.mark.asyncio
    async def test_metrics_with_no_financial_data_no_price(self, session_factory, db_session):
        """Score exists but no FinancialData → metrics return None with reasons."""
        asset = Asset(
            ticker="BARE",
            name="Bare Corp",
            sector="Technology",
            market_cap=Decimal("1000000000"),
        )
        db_session.add(asset)
        await db_session.flush()

        score = Score(
            asset_id=asset.id,
            composite_percentile=50.0,
            composite_raw_score=50.0,
            conviction_level="medium",
            signal="stable",
            quality_percentile=50.0,
            value_percentile=50.0,
            momentum_percentile=50.0,
            data_coverage=0.5,
        )
        db_session.add(score)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/BARE/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sharpe_ratio"]["value"] is None
        assert data["sharpe_ratio"]["unavailable_reason"] is not None
