"""Tests for admin JWT verification and role-based dependencies."""

from __future__ import annotations

import time

import jwt as pyjwt
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.config import Settings
from margin_api.db.base import Base
from margin_api.db.models import User, UserRole
from margin_api.db.session import get_db
from margin_api.deps import _verify_admin_jwt, get_admin_user, get_superadmin_user

# ─── Fixtures ────────────────────────────────────────────────────────────────

TEST_JWT_SECRET = "test-admin-jwt-secret-xyz"
OTHER_JWT_SECRET = "wrong-secret-key"


def _make_settings(jwt_secret: str = TEST_JWT_SECRET) -> Settings:
    return Settings(
        jwt_secret=jwt_secret,
        database_url="sqlite+aiosqlite:///:memory:",
    )


def _mint_token(
    user_id: int,
    role: str,
    secret: str = TEST_JWT_SECRET,
    exp_offset: int = 3600,
) -> str:
    now = int(time.time())
    return pyjwt.encode(
        {"sub": str(user_id), "role": role, "iat": now, "exp": now + exp_offset},
        secret,
        algorithm="HS256",
    )


# ─── Unit tests for _verify_admin_jwt ────────────────────────────────────────


class TestVerifyAdminJwt:
    def test_valid_admin_token_returns_user_id_and_role(self):
        token = _mint_token(user_id=5, role="admin")
        settings = _make_settings()
        user_id, role = _verify_admin_jwt(token, settings)
        assert user_id == 5
        assert role == "admin"

    def test_valid_superadmin_token_returns_user_id_and_role(self):
        token = _mint_token(user_id=1, role="superadmin")
        settings = _make_settings()
        user_id, role = _verify_admin_jwt(token, settings)
        assert user_id == 1
        assert role == "superadmin"

    def test_expired_token_raises_401(self):
        token = _mint_token(user_id=5, role="admin", exp_offset=-10)
        settings = _make_settings()
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _verify_admin_jwt(token, settings)
        assert exc_info.value.status_code == 401

    def test_wrong_key_raises_401(self):
        token = _mint_token(user_id=5, role="admin", secret=OTHER_JWT_SECRET)
        settings = _make_settings(jwt_secret=TEST_JWT_SECRET)
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _verify_admin_jwt(token, settings)
        assert exc_info.value.status_code == 401

    def test_missing_role_claim_raises_401(self):
        now = int(time.time())
        token = pyjwt.encode(
            {"sub": "5", "iat": now, "exp": now + 3600},
            TEST_JWT_SECRET,
            algorithm="HS256",
        )
        settings = _make_settings()
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _verify_admin_jwt(token, settings)
        assert exc_info.value.status_code == 401

    def test_missing_sub_claim_raises_401(self):
        now = int(time.time())
        token = pyjwt.encode(
            {"role": "admin", "iat": now, "exp": now + 3600},
            TEST_JWT_SECRET,
            algorithm="HS256",
        )
        settings = _make_settings()
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _verify_admin_jwt(token, settings)
        assert exc_info.value.status_code == 401

    def test_non_integer_sub_raises_401(self):
        now = int(time.time())
        token = pyjwt.encode(
            {"sub": "not-a-number", "role": "admin", "iat": now, "exp": now + 3600},
            TEST_JWT_SECRET,
            algorithm="HS256",
        )
        settings = _make_settings()
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _verify_admin_jwt(token, settings)
        assert exc_info.value.status_code == 401


# ─── Integration tests for get_admin_user / get_superadmin_user ──────────────


@pytest_asyncio.fixture()
async def admin_app_setup():
    """Set up in-memory DB with admin/superadmin/regular users and a FastAPI app."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        regular = User(email="user@test.com", name="Regular", role=UserRole.USER)
        admin = User(email="admin@test.com", name="Admin", role=UserRole.ADMIN)
        superadmin = User(
            email="superadmin@test.com", name="Super", role=UserRole.SUPERADMIN
        )
        session.add_all([regular, admin, superadmin])
        await session.commit()
        await session.refresh(regular)
        await session.refresh(admin)
        await session.refresh(superadmin)
        regular_id = regular.id
        admin_id = admin.id
        superadmin_id = superadmin.id

    settings = _make_settings()

    app = FastAPI()

    async def override_db():
        async with factory() as session:
            yield session

    def override_settings():
        return settings

    from margin_api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings

    @app.get("/admin-only")
    async def admin_only(user: User = Depends(get_admin_user)):
        return {"user_id": user.id, "role": user.role}

    @app.get("/superadmin-only")
    async def superadmin_only(user: User = Depends(get_superadmin_user)):
        return {"user_id": user.id, "role": user.role}

    yield app, regular_id, admin_id, superadmin_id, settings
    await engine.dispose()


class TestGetAdminUser:
    @pytest.mark.asyncio
    async def test_admin_cookie_grants_access(self, admin_app_setup):
        app, _, admin_id, _, settings = admin_app_setup
        token = _mint_token(user_id=admin_id, role="admin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/admin-only", cookies={"admin_session": token}
            )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == admin_id
        assert resp.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_superadmin_cookie_grants_admin_access(self, admin_app_setup):
        app, _, _, superadmin_id, settings = admin_app_setup
        token = _mint_token(user_id=superadmin_id, role="superadmin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/admin-only", cookies={"admin_session": token}
            )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == superadmin_id

    @pytest.mark.asyncio
    async def test_missing_cookie_returns_401(self, admin_app_setup):
        app, *_ = admin_app_setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin-only")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_regular_user_with_admin_role_claim_returns_403(
        self, admin_app_setup
    ):
        """DB role must be admin/superadmin even if JWT claims it."""
        app, regular_id, _, _, settings = admin_app_setup
        # JWT claims admin but DB user has role=user
        token = _mint_token(user_id=regular_id, role="admin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/admin-only", cookies={"admin_session": token}
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, admin_app_setup):
        app, _, admin_id, _, settings = admin_app_setup
        token = _mint_token(user_id=admin_id, role="admin", exp_offset=-10)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/admin-only", cookies={"admin_session": token}
            )
        assert resp.status_code == 401


class TestGetSuperadminUser:
    @pytest.mark.asyncio
    async def test_superadmin_cookie_grants_access(self, admin_app_setup):
        app, _, _, superadmin_id, settings = admin_app_setup
        token = _mint_token(user_id=superadmin_id, role="superadmin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/superadmin-only", cookies={"admin_session": token}
            )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == superadmin_id

    @pytest.mark.asyncio
    async def test_admin_cannot_access_superadmin_route(self, admin_app_setup):
        app, _, admin_id, _, settings = admin_app_setup
        token = _mint_token(user_id=admin_id, role="admin")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/superadmin-only", cookies={"admin_session": token}
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_cookie_returns_401(self, admin_app_setup):
        app, *_ = admin_app_setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/superadmin-only")
        assert resp.status_code == 401
