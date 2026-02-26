"""Tests for POST /api/v1/auth/change-password and GET /api/v1/auth/session-check."""

from __future__ import annotations

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.services.auth import AuthService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_TEST_FERNET_KEY = Fernet.generate_key().decode()
_auth = AuthService()


@pytest_asyncio.fixture()
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        user = await _auth.register_user(session, "testuser", "test@example.com", "OldPassword1!")
        user_id = user.id

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
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    yield app, user_id, factory
    await engine.dispose()


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_success(self, setup):
        app, _, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "OldPassword1!",
                    "new_password": "NewPassword2@",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password changed successfully"

    @pytest.mark.asyncio
    async def test_wrong_current_password(self, setup):
        app, _, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "WrongPassword1!",
                    "new_password": "NewPassword2@",
                },
            )
        assert resp.status_code == 401
        assert "Invalid current password" in resp.json()["message"]

    @pytest.mark.asyncio
    async def test_weak_new_password_too_short(self, setup):
        """Pydantic min_length=12 rejects short passwords with 422."""
        app, _, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "OldPassword1!",
                    "new_password": "weak",
                },
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_weak_new_password_missing_special(self, setup):
        """Password meets length but fails complexity rules -> 400."""
        app, _, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "OldPassword1!",
                    "new_password": "NoSpecialChar123",
                },
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_sets_password_changed_at(self, setup):
        app, user_id, factory = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "OldPassword1!",
                    "new_password": "NewPassword2@",
                },
            )
        async with factory() as session:
            user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
            assert user.password_changed_at is not None

    @pytest.mark.asyncio
    async def test_new_password_works_after_change(self, setup):
        app, user_id, factory = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "OldPassword1!",
                    "new_password": "NewPassword2@",
                },
            )
        async with factory() as session:
            result = await _auth.verify_credentials(session, "test@example.com", "NewPassword2@")
            assert result is not None
            assert result["id"] == user_id


class TestSessionCheck:
    @pytest.mark.asyncio
    async def test_token_invalidated_after_password_change(self, setup):
        """After a password change, session-check with old iat returns token_invalidated=True."""
        app, user_id, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Use iat from before the password change
            import time

            old_iat = int(time.time()) - 10

            # Change password to populate password_changed_at
            await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "OldPassword1!",
                    "new_password": "NewPassword2@",
                },
            )
            resp = await client.get(
                f"/api/v1/auth/session-check/{user_id}?iat={old_iat}"
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_valid"] is True
        assert data["token_invalidated"] is True

    @pytest.mark.asyncio
    async def test_token_not_invalidated_without_iat(self, setup):
        """Without iat param, token_invalidated is always False."""
        app, user_id, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Change password first
            await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "OldPassword1!",
                    "new_password": "NewPassword2@",
                },
            )
            resp = await client.get(f"/api/v1/auth/session-check/{user_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_valid"] is True
        assert data["token_invalidated"] is False

    @pytest.mark.asyncio
    async def test_no_leak_of_password_changed_at(self, setup):
        """Response must NOT contain raw password_changed_at timestamp."""
        app, user_id, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "OldPassword1!",
                    "new_password": "NewPassword2@",
                },
            )
            resp = await client.get(f"/api/v1/auth/session-check/{user_id}?iat=1")
        data = resp.json()
        assert "password_changed_at" not in data

    @pytest.mark.asyncio
    async def test_returns_valid_for_no_change(self, setup):
        """Before any password change, session-check returns valid session."""
        app, user_id, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/auth/session-check/{user_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_valid"] is True
        assert data["token_invalidated"] is False

    @pytest.mark.asyncio
    async def test_returns_valid_for_nonexistent_user(self, setup):
        """A bogus user_id returns session_valid=True, token_invalidated=False."""
        app, _, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/session-check/99999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_valid"] is True
        assert data["token_invalidated"] is False
