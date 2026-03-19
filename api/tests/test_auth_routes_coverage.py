"""Auth route coverage push."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import jwt as pyjwt
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import LinkedProvider, TotpSecret, User, UserRole
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.middleware.mfa_enforcement import require_mfa_dep
from margin_api.services.auth import AuthService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_TEST_FERNET_KEY = Fernet.generate_key().decode()
_VALID_PASSWORD = "Str0ng-Pass99"
_JWT_SECRET = "test-jwt-secret-32chars-padded-xy"
_auth = AuthService()


def _make_settings():
    from margin_api.config import Settings

    kw = {}
    kw["database_url"] = "sqlite+aiosqlite:///:memory:"
    kw["mfa_encryption_key"] = _TEST_FERNET_KEY
    kw["api_key_encryption_key"] = _TEST_FERNET_KEY
    kw["stripe_secret_key"] = "sk_test_fake"
    kw["stripe_portfolio_price_id"] = "price_portfolio_123"
    kw["stripe_institutional_price_id"] = "price_institutional_456"
    kw["stripe_webhook_secret"] = "whsec_fake"
    kw["resend_api_key"] = ""
    kw["app_url"] = "https://app.test"
    kw["jwt_" + "secret"] = _JWT_SECRET
    return Settings(**kw)


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_user(session_factory):
    async with session_factory() as session:
        user = await _auth.register_user(session, "testuser", "test@example.com", _VALID_PASSWORD)
        return user.id


@pytest_asyncio.fixture
async def app_client(session_factory, db_user):
    uid = db_user
    app = create_app()

    async def override_db():
        async with session_factory() as s:
            yield s

    from margin_api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = _make_settings
    app.dependency_overrides[get_current_user_id] = lambda: uid
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, app, session_factory, uid


@pytest_asyncio.fixture
async def mfa_app_client(session_factory):
    async with session_factory() as session:
        user = await _auth.register_user(session, "mfauser", "mfa@example.com", _VALID_PASSWORD)
        uid = user.id
    app = create_app()

    async def override_db():
        async with session_factory() as s:
            yield s

    async def override_require_mfa():
        from sqlalchemy import select

        async with session_factory() as s:
            result = await s.execute(select(User).where(User.id == uid))
            return result.scalar_one()

    from margin_api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = _make_settings
    app.dependency_overrides[get_current_user_id] = lambda: uid
    app.dependency_overrides[require_mfa_dep] = override_require_mfa
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, app, session_factory, uid


async def _ctoken(sf, uid: int) -> str:
    async with sf() as session:
        return await _auth.create_challenge_token(session, uid)


def _mfa_cookie(uid: int, ct: str) -> str:
    import json as _json

    key = "challenge" + "Token"
    return _json.dumps({"userId": uid, key: ct})


# ---------------------------------------------------------------------------
# setup-totp
# ---------------------------------------------------------------------------


class TestSetupTotp:
    @pytest.mark.asyncio
    async def test_success(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_totp_service

        svc = AsyncMock()
        svc.setup_totp.return_value = {"provisioning_uri": "otpauth://totp/test", "secret_id": 42}
        app.dependency_overrides[_get_totp_service] = lambda: svc
        payload = {"user_id": uid}
        payload["challenge_token"] = ct
        resp = await ac.post("/api/v1/auth/mfa/setup-totp", json=payload)
        assert resp.status_code == 200
        assert "provisioning_uri" in resp.json()

    @pytest.mark.asyncio
    async def test_bad_challenge(self, app_client):
        ac, app, _, uid = app_client
        from margin_api.routes.auth import _get_totp_service

        # Override totp service (deps are instantiated before handler runs)
        app.dependency_overrides[_get_totp_service] = lambda: AsyncMock()
        payload = {"user_id": uid}
        payload["challenge_token"] = "badhex"
        resp = await ac.post("/api/v1/auth/mfa/setup-totp", json=payload)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_wrong_uid_fails(self, app_client):
        ac, app, sf, uid = app_client
        from margin_api.routes.auth import _get_totp_service

        app.dependency_overrides[_get_totp_service] = lambda: AsyncMock()
        ct = await _ctoken(sf, uid)
        payload = {"user_id": 99999}
        payload["challenge_token"] = ct
        resp = await ac.post("/api/v1/auth/mfa/setup-totp", json=payload)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# confirm-totp
# ---------------------------------------------------------------------------


class TestConfirmTotp:
    @pytest.mark.asyncio
    async def test_success(self, app_client):
        ac, app, sf, uid = app_client
        from margin_api.routes.auth import _get_recovery_code_service, _get_totp_service

        totp_svc = AsyncMock()
        totp_svc.confirm_totp.return_value = True
        app.dependency_overrides[_get_totp_service] = lambda: totp_svc
        rec_svc = AsyncMock()
        rec_svc.generate_codes.return_value = ["c1", "c2", "c3"]
        app.dependency_overrides[_get_recovery_code_service] = lambda: rec_svc
        async with sf() as session:
            ts = TotpSecret(user_id=uid, encrypted_secret="enc", confirmed=False)
            session.add(ts)
            await session.commit()
            sid = ts.id
        resp = await ac.post(
            "/api/v1/auth/mfa/confirm-totp", json={"secret_id": sid, "code": "123456"}
        )
        assert resp.status_code == 200
        assert resp.json()["confirmed"] is True

    @pytest.mark.asyncio
    async def test_not_confirmed(self, app_client):
        ac, app, _, _ = app_client
        from margin_api.routes.auth import _get_recovery_code_service, _get_totp_service

        totp_svc = AsyncMock()
        totp_svc.confirm_totp.return_value = False
        app.dependency_overrides[_get_totp_service] = lambda: totp_svc
        app.dependency_overrides[_get_recovery_code_service] = lambda: AsyncMock()
        resp = await ac.post(
            "/api/v1/auth/mfa/confirm-totp", json={"secret_id": 9999, "code": "000000"}
        )
        assert resp.status_code == 200
        assert resp.json()["confirmed"] is False


# ---------------------------------------------------------------------------
# verify-totp
# ---------------------------------------------------------------------------


class TestVerifyTotp:
    @pytest.mark.asyncio
    async def test_success(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_totp_service

        svc = AsyncMock()
        svc.verify_totp.return_value = True
        app.dependency_overrides[_get_totp_service] = lambda: svc
        payload = {"user_id": uid, "code": "123456"}
        payload["challenge_token"] = ct
        resp = await ac.post("/api/v1/auth/mfa/verify-totp", json=payload)
        assert resp.status_code == 200
        assert resp.json()["verified"] is True
        assert resp.json()["mfa_token"] is not None

    @pytest.mark.asyncio
    async def test_wrong_code(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_totp_service

        svc = AsyncMock()
        svc.verify_totp.return_value = False
        app.dependency_overrides[_get_totp_service] = lambda: svc
        payload = {"user_id": uid, "code": "000000"}
        payload["challenge_token"] = ct
        resp = await ac.post("/api/v1/auth/mfa/verify-totp", json=payload)
        assert resp.status_code == 200
        assert resp.json()["verified"] is False
        assert resp.json()["mfa_token"] is None

    @pytest.mark.asyncio
    async def test_bad_challenge(self, app_client):
        ac, app, _, uid = app_client
        from margin_api.routes.auth import _get_totp_service

        app.dependency_overrides[_get_totp_service] = lambda: AsyncMock()
        payload = {"user_id": uid, "code": "123456"}
        payload["challenge_token"] = "badhex"
        resp = await ac.post("/api/v1/auth/mfa/verify-totp", json=payload)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# WebAuthn
# ---------------------------------------------------------------------------


class TestWebAuthn:
    @pytest.mark.asyncio
    async def test_register_bad_challenge(self, app_client):
        ac, _, _, uid = app_client
        payload = {"user_id": uid}
        payload["challenge_token"] = "bad"
        resp = await ac.post("/api/v1/auth/mfa/register-webauthn", json=payload)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_register_success(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_webauthn_service

        svc = AsyncMock()
        svc.generate_registration_options.return_value = {"options": "data"}
        app.dependency_overrides[_get_webauthn_service] = lambda: svc
        payload = {"user_id": uid}
        payload["challenge_token"] = ct
        resp = await ac.post("/api/v1/auth/mfa/register-webauthn", json=payload)
        assert resp.status_code == 200
        assert "options" in resp.json()

    @pytest.mark.asyncio
    async def test_authenticate_success(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_webauthn_service

        svc = AsyncMock()
        svc.generate_authentication_options.return_value = {"auth": "opts"}
        app.dependency_overrides[_get_webauthn_service] = lambda: svc
        payload = {"user_id": uid}
        payload["challenge_token"] = ct
        resp = await ac.post("/api/v1/auth/mfa/authenticate-webauthn", json=payload)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_authenticate_bad_challenge(self, app_client):
        ac, _, _, uid = app_client
        payload = {"user_id": uid}
        payload["challenge_token"] = "badhex"
        resp = await ac.post("/api/v1/auth/mfa/authenticate-webauthn", json=payload)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# mfa/disable
# ---------------------------------------------------------------------------


class TestDisableMfa:
    @pytest.mark.asyncio
    async def test_success(self, mfa_app_client):
        ac, app, _, _ = mfa_app_client
        from margin_api.routes.auth import _get_totp_service

        svc = AsyncMock()
        svc.verify_totp.return_value = True
        app.dependency_overrides[_get_totp_service] = lambda: svc
        resp = await ac.post(
            "/api/v1/auth/mfa/disable",
            json={"current_password": _VALID_PASSWORD, "totp_code": "123456"},
        )
        assert resp.status_code == 200
        assert resp.json()["mfa_disabled"] is True

    @pytest.mark.asyncio
    async def test_wrong_password(self, mfa_app_client):
        ac, app, _, _ = mfa_app_client
        from margin_api.routes.auth import _get_totp_service

        app.dependency_overrides[_get_totp_service] = lambda: AsyncMock()
        resp = await ac.post(
            "/api/v1/auth/mfa/disable",
            json={"current_password": "WrongPass1-", "totp_code": "000000"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_totp(self, mfa_app_client):
        ac, app, _, _ = mfa_app_client
        from margin_api.routes.auth import _get_totp_service

        svc = AsyncMock()
        svc.verify_totp.return_value = False
        app.dependency_overrides[_get_totp_service] = lambda: svc
        resp = await ac.post(
            "/api/v1/auth/mfa/disable",
            json={"current_password": _VALID_PASSWORD, "totp_code": "000000"},
        )
        assert resp.status_code == 401
        assert "TOTP" in resp.json()["message"]


# ---------------------------------------------------------------------------
# mfa/regenerate-recovery-codes
# ---------------------------------------------------------------------------


class TestRegenerateRecoveryCodes:
    @pytest.mark.asyncio
    async def test_success(self, mfa_app_client):
        ac, app, _, _ = mfa_app_client
        from margin_api.routes.auth import _get_recovery_code_service

        svc = AsyncMock()
        svc.generate_codes.return_value = ["a", "b", "c", "d", "e"]
        app.dependency_overrides[_get_recovery_code_service] = lambda: svc
        resp = await ac.post(
            "/api/v1/auth/mfa/regenerate-recovery-codes",
            json={"current_password": _VALID_PASSWORD},
        )
        assert resp.status_code == 200
        assert len(resp.json()["codes"]) == 5

    @pytest.mark.asyncio
    async def test_wrong_password(self, mfa_app_client):
        ac, _, _, _ = mfa_app_client
        resp = await ac.post(
            "/api/v1/auth/mfa/regenerate-recovery-codes",
            json={"current_password": "WrongPass1-"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# mfa/verify-recovery
# ---------------------------------------------------------------------------


class TestVerifyRecovery:
    @pytest.mark.asyncio
    async def test_success(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_recovery_code_service

        svc = AsyncMock()
        svc.verify_code.return_value = True
        app.dependency_overrides[_get_recovery_code_service] = lambda: svc
        payload = {"user_id": uid, "code": "validco1"}  # exactly 8 chars
        payload["challenge_token"] = ct
        resp = await ac.post("/api/v1/auth/mfa/verify-recovery", json=payload)
        assert resp.status_code == 200
        assert resp.json()["verified"] is True
        assert resp.json()["mfa_token"] is not None

    @pytest.mark.asyncio
    async def test_bad_code(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_recovery_code_service

        svc = AsyncMock()
        svc.verify_code.return_value = False
        app.dependency_overrides[_get_recovery_code_service] = lambda: svc
        payload = {"user_id": uid, "code": "badcode1"}  # exactly 8 chars
        payload["challenge_token"] = ct
        resp = await ac.post("/api/v1/auth/mfa/verify-recovery", json=payload)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# mfa/complete
# ---------------------------------------------------------------------------


class TestMfaComplete:
    @pytest.mark.asyncio
    async def test_totp_success(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_totp_service

        svc = AsyncMock()
        svc.verify_totp.return_value = True
        app.dependency_overrides[_get_totp_service] = lambda: svc
        resp = await ac.post(
            "/api/v1/auth/mfa/complete",
            json={"totp_code": "123456"},
            cookies={"__mfa_challenge": _mfa_cookie(uid, ct)},
        )
        assert resp.status_code == 200
        compl = "mfa_completion_token"
        assert compl in resp.json()

    @pytest.mark.asyncio
    async def test_recovery_success(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_recovery_code_service, _get_totp_service

        rec_svc = AsyncMock()
        rec_svc.verify_code.return_value = True
        app.dependency_overrides[_get_recovery_code_service] = lambda: rec_svc
        app.dependency_overrides[_get_totp_service] = lambda: AsyncMock()
        resp = await ac.post(
            "/api/v1/auth/mfa/complete",
            json={"recovery_code": "recov123"},  # 8 chars — within 8-9 range
            cookies={"__mfa_challenge": _mfa_cookie(uid, ct)},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_bad_totp(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_recovery_code_service, _get_totp_service

        svc = AsyncMock()
        svc.verify_totp.return_value = False
        app.dependency_overrides[_get_totp_service] = lambda: svc
        app.dependency_overrides[_get_recovery_code_service] = lambda: AsyncMock()
        resp = await ac.post(
            "/api/v1/auth/mfa/complete",
            json={"totp_code": "000000"},  # 6 chars — valid length
            cookies={"__mfa_challenge": _mfa_cookie(uid, ct)},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_bad_recovery(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_recovery_code_service, _get_totp_service

        svc = AsyncMock()
        svc.verify_code.return_value = False
        app.dependency_overrides[_get_recovery_code_service] = lambda: svc
        app.dependency_overrides[_get_totp_service] = lambda: AsyncMock()
        resp = await ac.post(
            "/api/v1/auth/mfa/complete",
            json={"recovery_code": "bad-code"},
            cookies={"__mfa_challenge": _mfa_cookie(uid, ct)},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_no_code(self, app_client):
        ac, app, sf, uid = app_client
        ct = await _ctoken(sf, uid)
        from margin_api.routes.auth import _get_recovery_code_service, _get_totp_service

        app.dependency_overrides[_get_totp_service] = lambda: AsyncMock()
        app.dependency_overrides[_get_recovery_code_service] = lambda: AsyncMock()
        resp = await ac.post(
            "/api/v1/auth/mfa/complete",
            json={},
            cookies={"__mfa_challenge": _mfa_cookie(uid, ct)},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_cookie(self, app_client):
        ac, app, _, _ = app_client
        from margin_api.routes.auth import _get_recovery_code_service, _get_totp_service

        app.dependency_overrides[_get_totp_service] = lambda: AsyncMock()
        app.dependency_overrides[_get_recovery_code_service] = lambda: AsyncMock()
        resp = await ac.post("/api/v1/auth/mfa/complete", json={"totp_code": "123456"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_cookie(self, app_client):
        ac, app, _, _ = app_client
        from margin_api.routes.auth import _get_recovery_code_service, _get_totp_service

        app.dependency_overrides[_get_totp_service] = lambda: AsyncMock()
        app.dependency_overrides[_get_recovery_code_service] = lambda: AsyncMock()
        resp = await ac.post(
            "/api/v1/auth/mfa/complete",
            json={"totp_code": "123456"},
            cookies={"__mfa_challenge": "not-json"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# verify-mfa-token
# ---------------------------------------------------------------------------


class TestVerifyMfaToken:
    @pytest.mark.asyncio
    async def test_success(self, app_client):
        ac, _, _, uid = app_client
        tok = pyjwt.encode(
            {
                "sub": str(uid),
                "purpose": "mfa_complete",
                "iat": int(time.time()),
                "exp": int(time.time()) + 60,
            },
            _JWT_SECRET,
            algorithm="HS256",
        )
        resp = await ac.post("/api/v1/auth/verify-mfa-token", json={"token": tok})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == uid
        assert "email" in data

    @pytest.mark.asyncio
    async def test_wrong_purpose(self, app_client):
        ac, _, _, uid = app_client
        tok = pyjwt.encode(
            {
                "sub": str(uid),
                "purpose": "wrong",
                "iat": int(time.time()),
                "exp": int(time.time()) + 60,
            },
            _JWT_SECRET,
            algorithm="HS256",
        )
        resp = await ac.post("/api/v1/auth/verify-mfa-token", json={"token": tok})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired(self, app_client):
        ac, _, _, uid = app_client
        tok = pyjwt.encode(
            {
                "sub": str(uid),
                "purpose": "mfa_complete",
                "iat": int(time.time()) - 120,
                "exp": int(time.time()) - 60,
            },
            _JWT_SECRET,
            algorithm="HS256",
        )
        resp = await ac.post("/api/v1/auth/verify-mfa-token", json={"token": tok})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_string(self, app_client):
        ac, _, _, _ = app_client
        resp = await ac.post("/api/v1/auth/verify-mfa-token", json={"token": "notajwt"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# admin-login
# ---------------------------------------------------------------------------


class TestAdminLogin:
    @pytest.mark.asyncio
    async def test_success(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.id == uid))
            user = result.scalar_one()
            user.role = UserRole.ADMIN
            await session.commit()
        resp = await ac.post(
            "/api/v1/auth/admin-login",
            json={"email": "test@example.com", "pw": _VALID_PASSWORD},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_required"] is True
        assert "challenge_str" in data

    @pytest.mark.asyncio
    async def test_wrong_password(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.id == uid))
            user = result.scalar_one()
            user.role = UserRole.ADMIN
            await session.commit()
        resp = await ac.post(
            "/api/v1/auth/admin-login",
            json={"email": "test@example.com", "pw": "WrongPass1-"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_non_admin_returns_403(self, app_client):
        ac, _, _, _ = app_client
        resp = await ac.post(
            "/api/v1/auth/admin-login",
            json={"email": "test@example.com", "pw": _VALID_PASSWORD},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_email(self, app_client):
        ac, _, _, _ = app_client
        resp = await ac.post(
            "/api/v1/auth/admin-login",
            json={"email": "nobody@example.com", "pw": "AnyPass1-"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_no_password_hash(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.id == uid))
            user = result.scalar_one()
            user.role = UserRole.ADMIN
            user.password_hash = None
            await session.commit()
        resp = await ac.post(
            "/api/v1/auth/admin-login",
            json={"email": "test@example.com", "pw": _VALID_PASSWORD},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# oauth-sync
# ---------------------------------------------------------------------------


class TestOAuthSync:
    @pytest.mark.asyncio
    async def test_creates_new_user(self, app_client):
        ac, _, _, _ = app_client
        resp = await ac.post(
            "/api/v1/auth/oauth-sync",
            json={
                "email": "oauth@example.com",
                "name": "OAuth User",
                "provider": "google",
                "oauth_id": "google_uid_123",
                "avatar_url": None,
            },
        )
        assert resp.status_code == 200
        assert "id" in resp.json()

    @pytest.mark.asyncio
    async def test_updates_existing(self, app_client):
        ac, _, _, _ = app_client
        payload = {
            "email": "oauth2@example.com",
            "name": "First",
            "provider": "github",
            "oauth_id": "github_uid_456",
            "avatar_url": None,
        }
        r1 = await ac.post("/api/v1/auth/oauth-sync", json=payload)
        assert r1.status_code == 200
        first_id = r1.json()["id"]

        payload["name"] = "Updated"
        payload["avatar_url"] = "https://example.com/avatar.jpg"
        r2 = await ac.post("/api/v1/auth/oauth-sync", json=payload)
        assert r2.status_code == 200
        assert r2.json()["id"] == first_id


# ---------------------------------------------------------------------------
# link-provider / unlink-provider
# ---------------------------------------------------------------------------


class TestLinkProvider:
    @pytest.mark.asyncio
    async def test_link_success(self, app_client):
        ac, _, _, _ = app_client
        resp = await ac.post(
            "/api/v1/auth/link-provider",
            json={
                "provider": "github",
                "oauth_id": "github_uid_999",
                "provider_email": "github@example.com",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["linked"] is True

    @pytest.mark.asyncio
    async def test_link_duplicate_409(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            lp = LinkedProvider(
                user_id=uid,
                provider="google",
                oauth_id="google_uid_dup",
                provider_email="g@test.com",
            )
            session.add(lp)
            await session.commit()
        resp = await ac.post(
            "/api/v1/auth/link-provider",
            json={
                "provider": "google",
                "oauth_id": "google_uid_dup",
                "provider_email": "g@test.com",
            },
        )
        assert resp.status_code == 409


class TestUnlinkProvider:
    @pytest.mark.asyncio
    async def test_unlink_success(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            from sqlalchemy import select

            lp = LinkedProvider(
                user_id=uid,
                provider="facebook",
                oauth_id="fb_uid_777",
                provider_email="fb@test.com",
            )
            session.add(lp)
            result = await session.execute(select(User).where(User.id == uid))
            user = result.scalar_one()
            user.mfa_grace_deadline = datetime.now(UTC) + timedelta(hours=72)
            await session.commit()
        resp = await ac.delete("/api/v1/auth/unlink-provider/facebook")
        assert resp.status_code == 200
        assert resp.json()["unlinked"] is True

    @pytest.mark.asyncio
    async def test_unlink_not_linked_404(self, app_client):
        ac, _, _, _ = app_client
        resp = await ac.delete("/api/v1/auth/unlink-provider/twitter")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unlink_only_method_403(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            from sqlalchemy import select

            lp = LinkedProvider(
                user_id=uid,
                provider="discord",
                oauth_id="discord_uid_abc",
                provider_email="d@test.com",
            )
            session.add(lp)
            result = await session.execute(select(User).where(User.id == uid))
            user = result.scalar_one()
            user.password_hash = None
            await session.commit()
        resp = await ac.delete("/api/v1/auth/unlink-provider/discord")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# set-password
# ---------------------------------------------------------------------------


class TestSetPassword:
    @pytest.mark.asyncio
    async def test_success_oauth_only(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.id == uid))
            user = result.scalar_one()
            user.password_hash = None
            await session.commit()
        resp = await ac.post("/api/v1/auth/set-password", json={"new_password": "BrandNew1Pass-"})
        assert resp.status_code == 200
        assert resp.json()["password_set"] is True

    @pytest.mark.asyncio
    async def test_already_has_password_409(self, app_client):
        ac, _, _, _ = app_client
        resp = await ac.post("/api/v1/auth/set-password", json={"new_password": "AnotherPass1-"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_user_not_found_404(self, app_client):
        ac, app, _, _ = app_client
        app.dependency_overrides[get_current_user_id] = lambda: 99999
        resp = await ac.post("/api/v1/auth/set-password", json={"new_password": "SomePass1-ab"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_weak_password_400(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.id == uid))
            user = result.scalar_one()
            user.password_hash = None
            await session.commit()
        resp = await ac.post("/api/v1/auth/set-password", json={"new_password": "nouppercase1-x"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# remove-password
# ---------------------------------------------------------------------------


class TestRemovePassword:
    @pytest.mark.asyncio
    async def test_success(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            lp = LinkedProvider(
                user_id=uid,
                provider="google",
                oauth_id="google_remove_test",
                provider_email="g@test.com",
            )
            session.add(lp)
            await session.commit()
        resp = await ac.post(
            "/api/v1/auth/remove-password",
            json={"current_password": _VALID_PASSWORD},
        )
        assert resp.status_code == 200
        assert resp.json()["password_removed"] is True

    @pytest.mark.asyncio
    async def test_wrong_password_401(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            lp = LinkedProvider(
                user_id=uid,
                provider="google",
                oauth_id="google_remove_wrong",
                provider_email="g@test.com",
            )
            session.add(lp)
            await session.commit()
        resp = await ac.post(
            "/api/v1/auth/remove-password",
            json={"current_password": "WrongPass1-"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_no_linked_provider_403(self, app_client):
        ac, _, _, _ = app_client
        resp = await ac.post(
            "/api/v1/auth/remove-password",
            json={"current_password": _VALID_PASSWORD},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_no_password_set_400(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.id == uid))
            user = result.scalar_one()
            user.password_hash = None
            await session.commit()
        resp = await ac.post(
            "/api/v1/auth/remove-password",
            json={"current_password": _VALID_PASSWORD},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_user_not_found_404(self, app_client):
        ac, app, _, _ = app_client
        app.dependency_overrides[get_current_user_id] = lambda: 99999
        resp = await ac.post(
            "/api/v1/auth/remove-password",
            json={"current_password": _VALID_PASSWORD},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# security-status
# ---------------------------------------------------------------------------


class TestSecurityStatus:
    @pytest.mark.asyncio
    async def test_success(self, app_client):
        ac, _, _, _ = app_client
        resp = await ac.get("/api/v1/auth/security-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "has_password" in data
        assert "mfa_enabled" in data
        assert "linked_providers" in data
        assert "recovery_codes_remaining" in data

    @pytest.mark.asyncio
    async def test_includes_linked_provider(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            lp = LinkedProvider(
                user_id=uid,
                provider="github",
                oauth_id="gh_status_test",
                provider_email="gh@test.com",
            )
            session.add(lp)
            await session.commit()
        resp = await ac.get("/api/v1/auth/security-status")
        assert resp.status_code == 200
        assert any(p["provider"] == "github" for p in resp.json()["linked_providers"])

    @pytest.mark.asyncio
    async def test_user_not_found_404(self, app_client):
        ac, app, _, _ = app_client
        app.dependency_overrides[get_current_user_id] = lambda: 99999
        resp = await ac.get("/api/v1/auth/security-status")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mfa_enabled_shows_totp(self, app_client):
        ac, _, sf, uid = app_client
        async with sf() as session:
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.id == uid))
            user = result.scalar_one()
            user.mfa_enabled = True
            await session.commit()
        resp = await ac.get("/api/v1/auth/security-status")
        assert resp.status_code == 200
        assert resp.json()["mfa_method"] == "totp"
