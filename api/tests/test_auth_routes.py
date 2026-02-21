"""Tests for auth API routes."""

from __future__ import annotations

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# A valid Fernet key for testing
_TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest_asyncio.fixture()
async def app_and_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    app = create_app()

    async def override_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    # Override settings to provide a valid Fernet key
    def override_settings():
        from margin_api.config import Settings

        return Settings(
            mfa_encryption_key=_TEST_FERNET_KEY,
            database_url="sqlite+aiosqlite:///:memory:",
        )

    from margin_api.config import get_settings as _gs

    app.dependency_overrides[_gs] = override_settings

    yield app
    await engine.dispose()


@pytest_asyncio.fixture()
async def client(app_and_db):
    transport = ASGITransport(app=app_and_db)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_VALID_PASSWORD = "Str0ng!Pass99"


async def _register_user(client: AsyncClient, username: str = "alice") -> dict:
    """Register a user and return the response JSON."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": _VALID_PASSWORD,
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": _VALID_PASSWORD,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "alice"
        assert data["email"] == "alice@example.com"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        # Password meets length (12+) but lacks uppercase — fails complexity check
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "nouppercase1!a",
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        # Custom exception handler wraps in ErrorResponse — verify `detail` is present
        assert "detail" in data
        assert "uppercase" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_different_name_same_email(self, client):
        """Duplicate email should be rejected regardless of name."""
        await _register_user(client, "alice")
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "bob",
                "email": "alice@example.com",
                "password": _VALID_PASSWORD,
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
        assert "email" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client):
        await _register_user(client, "alice")
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "bob",
                "email": "alice@example.com",
                "password": _VALID_PASSWORD,
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
        assert "email" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_error_response_has_detail_and_message(self, client):
        """Verify that error responses include both `detail` and `message`."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "nouppercase1!a",
            },
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"] == data["message"]
        assert "request_id" in data


# ---------------------------------------------------------------------------
# Verify credentials tests
# ---------------------------------------------------------------------------


class TestVerifyCredentials:
    @pytest.mark.asyncio
    async def test_verify_credentials_success(self, client):
        await _register_user(client, "alice")
        resp = await client.post(
            "/api/v1/auth/verify-credentials",
            json={"username": "alice@example.com", "password": _VALID_PASSWORD},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "alice@example.com"
        assert data["email"] == "alice@example.com"
        assert "mfa_status" in data
        assert "challenge_token" in data
        assert len(data["challenge_token"]) == 64  # hex of 32 bytes

    @pytest.mark.asyncio
    async def test_verify_credentials_wrong_password(self, client):
        await _register_user(client, "alice")
        resp = await client.post(
            "/api/v1/auth/verify-credentials",
            json={"username": "alice@example.com", "password": "WrongPassword1!"},
        )
        assert resp.status_code == 401
