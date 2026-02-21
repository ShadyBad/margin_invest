"""Tests for POST /api/v1/auth/forgot-password and /api/v1/auth/reset-password."""

from __future__ import annotations

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.session import get_db
from margin_api.services.auth import AuthService
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
        user = await _auth.register_user(
            session, "testuser", "test@example.com", "OldPassword1!"
        )
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
            resend_api_key="",
            app_url="https://app.test",
        )

    from margin_api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings

    yield app, user_id, factory
    await engine.dispose()


class TestForgotPassword:
    @pytest.mark.asyncio
    async def test_returns_200_for_existing_email(self, setup):
        app, _, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@example.com"},
            )
        assert resp.status_code == 200
        assert "reset" in resp.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_returns_200_for_nonexistent_email(self, setup):
        """No email enumeration — same response for unknown email."""
        app, _, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "nobody@example.com"},
            )
        assert resp.status_code == 200


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_success(self, setup):
        app, user_id, factory = setup
        # Create a reset token directly
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(
                session, user_id, ttl_minutes=60
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/reset-password",
                json={
                    "user_id": user_id,
                    "token": raw_token,
                    "new_password": "NewPassword2@",
                },
            )
        assert resp.status_code == 200

        # Verify new password works
        async with factory() as session:
            result = await _auth.verify_credentials(
                session, "test@example.com", "NewPassword2@"
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_token(self, setup):
        app, user_id, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/reset-password",
                json={
                    "user_id": user_id,
                    "token": "invalid_token_hex",
                    "new_password": "NewPassword2@",
                },
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_weak_password(self, setup):
        app, user_id, factory = setup
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(
                session, user_id, ttl_minutes=60
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/reset-password",
                json={
                    "user_id": user_id,
                    "token": raw_token,
                    "new_password": "weak",
                },
            )
        assert resp.status_code == 422  # Pydantic min_length

    @pytest.mark.asyncio
    async def test_token_consumed_after_use(self, setup):
        app, user_id, factory = setup
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(
                session, user_id, ttl_minutes=60
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First use succeeds
            resp1 = await client.post(
                "/api/v1/auth/reset-password",
                json={
                    "user_id": user_id,
                    "token": raw_token,
                    "new_password": "NewPassword2@",
                },
            )
            assert resp1.status_code == 200

            # Second use fails
            resp2 = await client.post(
                "/api/v1/auth/reset-password",
                json={
                    "user_id": user_id,
                    "token": raw_token,
                    "new_password": "AnotherPass3#",
                },
            )
            assert resp2.status_code == 400
