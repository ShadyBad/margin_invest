"""Tests for the POST /api/v1/auth/admin-login endpoint.

Covers:
- Valid admin creds -> 200 with mfa_required=True and a challenge JWT
- Valid superadmin creds -> 200 with mfa_required=True and a challenge JWT
- Wrong password -> 401
- Regular user role -> 403
- Nonexistent email -> 401
- JWT challenge contains expected claims (sub, role, purpose, exp)
"""

from __future__ import annotations

import time

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.config import Settings, get_settings
from margin_api.db.base import Base
from margin_api.db.models import UserRole
from margin_api.db.session import get_db
from margin_api.services.auth import AuthService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_VALID_PASSWORD = "Str0ng!Pass99"
_JWT_SECRET = "test-secret-for-admin-login"
_auth = AuthService()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def db_setup():
    """Set up in-memory SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


@pytest_asyncio.fixture()
async def admin_user(db_setup):
    """Create an admin user with a valid password."""
    engine, factory = db_setup
    async with factory() as session:
        user = await _auth.register_user(
            session, "admin_user", "admin@example.com", _VALID_PASSWORD
        )
        user.role = UserRole.ADMIN
        await session.commit()
        await session.refresh(user)
    return engine, factory, user.id


@pytest_asyncio.fixture()
async def superadmin_user(db_setup):
    """Create a superadmin user with a valid password."""
    engine, factory = db_setup
    async with factory() as session:
        user = await _auth.register_user(
            session, "superadmin_user", "superadmin@example.com", _VALID_PASSWORD
        )
        user.role = UserRole.SUPERADMIN
        await session.commit()
        await session.refresh(user)
    return engine, factory, user.id


@pytest_asyncio.fixture()
async def regular_user(db_setup):
    """Create a regular (non-admin) user."""
    engine, factory = db_setup
    async with factory() as session:
        user = await _auth.register_user(
            session, "regular_user", "user@example.com", _VALID_PASSWORD
        )
        # role defaults to UserRole.USER
        await session.commit()
        await session.refresh(user)
    return engine, factory, user.id


def _make_app(factory):
    """Create a test app with overridden DB and settings."""
    app = create_app()

    async def override_db():
        async with factory() as session:
            yield session

    def override_settings():
        return Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            jwt_secret=_JWT_SECRET,
            mfa_encryption_key="",
            api_key_encryption_key="",
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings
    return app


async def _make_client(app) -> AsyncClient:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdminLogin:
    @pytest.mark.asyncio
    async def test_valid_admin_returns_mfa_challenge(self, admin_user):
        """Valid admin creds yield 200 with mfa_required=True and a signed challenge."""
        engine, factory, _user_id = admin_user
        app = _make_app(factory)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "admin@example.com", "pw": _VALID_PASSWORD},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["mfa_required"] is True
        assert body["challenge_str"] is not None
        assert isinstance(body["challenge_str"], str)
        assert "message" in body

    @pytest.mark.asyncio
    async def test_valid_superadmin_returns_mfa_challenge(self, superadmin_user):
        """Valid superadmin creds also yield 200 with mfa_required=True."""
        engine, factory, _user_id = superadmin_user
        app = _make_app(factory)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "superadmin@example.com", "pw": _VALID_PASSWORD},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["mfa_required"] is True
        assert body["challenge_str"] is not None

    @pytest.mark.asyncio
    async def test_challenge_jwt_has_correct_claims(self, admin_user):
        """Challenge JWT contains sub, role, purpose=admin_mfa_challenge, expires in ~5 min."""
        engine, factory, user_id = admin_user
        app = _make_app(factory)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "admin@example.com", "pw": _VALID_PASSWORD},
            )
        assert resp.status_code == 200
        token = resp.json()["challenge_str"]

        payload = pyjwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == str(user_id)
        assert payload["role"] == UserRole.ADMIN
        assert payload["purpose"] == "admin_mfa_challenge"

        # exp should be ~5 minutes from now (within 10s tolerance)
        now = int(time.time())
        assert 280 <= payload["exp"] - now <= 310

    @pytest.mark.asyncio
    async def test_superadmin_challenge_jwt_has_superadmin_role(self, superadmin_user):
        """Superadmin challenge JWT encodes the superadmin role."""
        engine, factory, _user_id = superadmin_user
        app = _make_app(factory)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "superadmin@example.com", "pw": _VALID_PASSWORD},
            )
        token = resp.json()["challenge_str"]
        payload = pyjwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
        assert payload["role"] == UserRole.SUPERADMIN

    @pytest.mark.asyncio
    async def test_wrong_password_returns_401(self, admin_user):
        """Wrong password returns 401 Unauthorized."""
        engine, factory, _user_id = admin_user
        app = _make_app(factory)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "admin@example.com", "pw": "WrongPassword99!"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_regular_user_role_returns_403(self, regular_user):
        """User with role=user gets 403 Forbidden."""
        engine, factory, _user_id = regular_user
        app = _make_app(factory)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "user@example.com", "pw": _VALID_PASSWORD},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_nonexistent_email_returns_401(self, db_setup):
        """Email not in DB returns 401 (no user enumeration)."""
        engine, factory = db_setup
        app = _make_app(factory)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "ghost@example.com", "pw": _VALID_PASSWORD},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mfa_is_always_required(self, admin_user):
        """MFA challenge is ALWAYS issued — never skipped — for admin login."""
        engine, factory, _user_id = admin_user
        app = _make_app(factory)
        async with await _make_client(app) as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "admin@example.com", "pw": _VALID_PASSWORD},
            )
        body = resp.json()
        # mfa_required must always be True and a challenge must always be present
        assert body["mfa_required"] is True
        assert body["challenge_str"] is not None and body["challenge_str"] != ""
