"""Tests for avatar upload and delete API routes."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import CredentialUser, User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.routes.avatar import _get_storage

_TEST_FERNET_KEY = Fernet.generate_key().decode()
_TEST_USER_ID = 1


def _make_png(width: int = 64, height: int = 64) -> bytes:
    """Create a minimal valid PNG image in memory."""
    buf = BytesIO()
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_large_png() -> bytes:
    """Create a PNG that exceeds the 5 MB limit."""
    # 5 MB + 1 byte of raw data, but we need the actual encoded file to exceed the limit.
    # A large uncompressed image will do.
    buf = BytesIO()
    # 2000x2000 RGB image is ~12 MB uncompressed; PNG compression won't bring it under 5 MB
    # Actually, solid-color PNGs compress extremely well. Use random-ish data instead.
    import os

    # Just return raw bytes larger than 5MB with a valid PNG header at the start
    # But validate_image checks real PNG parsing, so let's make a real large PNG.
    # Simplest approach: make a real small PNG and pad it.
    small_png = _make_png(10, 10)
    # The validator checks len(data) > MAX_SIZE first, before Pillow,
    # so we can just pad with zeros.
    padding = b"\x00" * (5 * 1024 * 1024 + 1 - len(small_png))
    return small_png[:8] + padding + small_png[8:]


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

    # Seed a User row so the avatar update has something to target
    async with factory() as session:
        user = User(
            id=_TEST_USER_ID,
            email="test@example.com",
            name="Test User",
            provider="google",
        )
        session.add(user)
        await session.commit()

    yield app, factory
    await engine.dispose()


@pytest_asyncio.fixture()
async def authed_client(app_and_db):
    app, _factory = app_and_db

    # Override auth to return a known user ID
    app.dependency_overrides[get_current_user_id] = lambda: _TEST_USER_ID

    # Mock the storage service to avoid real R2 calls
    mock_storage = MagicMock()
    mock_storage.upload.return_value = "https://avatars.example.com/avatars/1.webp"
    app.dependency_overrides[_get_storage] = lambda: mock_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, mock_storage, _factory


@pytest_asyncio.fixture()
async def unauthed_client(app_and_db):
    app, _factory = app_and_db
    # Do NOT override get_current_user_id — let it require X-User-Id header
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUploadAvatar:
    @pytest.mark.asyncio
    async def test_upload_avatar(self, authed_client):
        client, mock_storage, factory = authed_client
        png_data = _make_png()

        resp = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.png", png_data, "image/png")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["avatar_url"] == "https://avatars.example.com/avatars/1.webp"

        # Verify storage.upload was called
        mock_storage.upload.assert_called_once()
        call_args = mock_storage.upload.call_args
        assert call_args[0][0] == _TEST_USER_ID  # user_id
        assert isinstance(call_args[0][1], bytes)  # processed image bytes

        # Verify DB was updated
        async with factory() as session:
            result = await session.execute(select(User).where(User.id == _TEST_USER_ID))
            user = result.scalar_one()
            assert user.avatar_url == "https://avatars.example.com/avatars/1.webp"

    @pytest.mark.asyncio
    async def test_upload_rejects_oversized(self, authed_client):
        client, _mock_storage, _factory = authed_client
        # Create data larger than 5 MB with PNG content-type header bytes
        oversized = _make_large_png()
        assert len(oversized) > 5 * 1024 * 1024

        resp = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("big.png", oversized, "image/png")},
        )

        assert resp.status_code == 400
        assert "exceeds maximum" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_rejects_wrong_type(self, authed_client):
        client, _mock_storage, _factory = authed_client

        resp = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )

        assert resp.status_code == 400
        assert "Unsupported image type" in resp.json()["detail"]


class TestDeleteAvatar:
    @pytest.mark.asyncio
    async def test_delete_avatar(self, authed_client):
        client, mock_storage, factory = authed_client

        # Set an avatar URL first so we can verify it gets cleared
        async with factory() as session:
            from sqlalchemy import update

            await session.execute(
                update(User)
                .where(User.id == _TEST_USER_ID)
                .values(avatar_url="https://old-avatar.example.com/1.webp")
            )
            await session.commit()

        resp = await client.delete("/api/v1/users/me/avatar")

        assert resp.status_code == 200
        data = resp.json()
        assert data["avatar_url"] is None

        # Verify storage.delete was called
        mock_storage.delete.assert_called_once_with(_TEST_USER_ID)

        # Verify DB was updated
        async with factory() as session:
            result = await session.execute(select(User).where(User.id == _TEST_USER_ID))
            user = result.scalar_one()
            assert user.avatar_url is None


class TestAvatarAuth:
    @pytest.mark.asyncio
    async def test_upload_without_auth(self, unauthed_client):
        client = unauthed_client
        png_data = _make_png()

        resp = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.png", png_data, "image/png")},
        )

        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated"
