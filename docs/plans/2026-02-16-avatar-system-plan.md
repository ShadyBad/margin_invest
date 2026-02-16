# Avatar System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add custom avatar uploads with deterministic fallback (custom → OAuth → generated initials → default icon) rendered consistently across all views.

**Architecture:** Backend adds avatar columns to both user tables, a new upload/delete endpoint using Pillow for image processing and boto3 for Cloudflare R2 storage, and wires `get_current_user_id` to extract X-User-Id headers. Frontend gets a shared `<Avatar>` component with the 4-tier fallback chain, integrated into nav and settings, with upload UI in account settings.

**Tech Stack:** Pillow (image processing), boto3 (R2/S3 storage), NextAuth session augmentation, inline SVG (generated avatars)

---

### Task 1: Add avatar columns to User and CredentialUser models

**Files:**
- Modify: `api/src/margin_api/db/models.py:137-151` (User class)
- Modify: `api/src/margin_api/db/models.py:263-292` (CredentialUser class)
- Test: `api/tests/test_avatar_models.py`

**Step 1: Write the failing test**

Create `api/tests/test_avatar_models.py`:

```python
"""Tests for avatar columns on user models."""

import pytest
import pytest_asyncio
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker as async_sessionmaker

from margin_api.db.base import Base
from margin_api.db.models import User, CredentialUser


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_avatar_columns_default_null(db: AsyncSession):
    """Avatar columns should default to None."""
    user = User(
        email="test@example.com",
        name="Test User",
        provider="google",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    assert user.avatar_url is None
    assert user.oauth_avatar_url is None


@pytest.mark.asyncio
async def test_user_avatar_columns_store_values(db: AsyncSession):
    """Avatar columns should store and retrieve URLs."""
    user = User(
        email="test@example.com",
        name="Test User",
        provider="google",
        avatar_url="https://r2.example.com/avatars/1.webp",
        oauth_avatar_url="https://lh3.googleusercontent.com/photo.jpg",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    assert user.avatar_url == "https://r2.example.com/avatars/1.webp"
    assert user.oauth_avatar_url == "https://lh3.googleusercontent.com/photo.jpg"


@pytest.mark.asyncio
async def test_credential_user_avatar_columns(db: AsyncSession):
    """CredentialUser should also have avatar_url (but not oauth_avatar_url)."""
    user = CredentialUser(
        username="alice",
        email="alice@example.com",
        password_hash="hashed",
        avatar_url="https://r2.example.com/avatars/c1.webp",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    assert user.avatar_url == "https://r2.example.com/avatars/c1.webp"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_avatar_models.py -v`
Expected: FAIL with `TypeError` — `avatar_url` is not a valid column.

**Step 3: Write minimal implementation**

In `api/src/margin_api/db/models.py`, add to `User` class (after `created_at`, before `api_keys`):

```python
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    oauth_avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
```

Add to `CredentialUser` class (after `updated_at`, before `totp_secrets`):

```python
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_avatar_models.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_avatar_models.py
git commit -m "feat: add avatar_url and oauth_avatar_url columns to user models"
```

---

### Task 2: Generate Alembic migration for avatar columns

**Files:**
- Create: `api/alembic/versions/<auto>_add_avatar_columns.py`

**Step 1: Generate migration**

```bash
cd /Users/brandon/repos/margin_invest
uv run alembic -c api/alembic.ini revision --autogenerate -m "add_avatar_columns_to_users"
```

**Step 2: Review the generated migration**

Open the generated file in `api/alembic/versions/`. Verify it contains:
- `op.add_column('users', sa.Column('avatar_url', sa.String(length=512), nullable=True))`
- `op.add_column('users', sa.Column('oauth_avatar_url', sa.String(length=512), nullable=True))`
- `op.add_column('credential_users', sa.Column('avatar_url', sa.String(length=512), nullable=True))`

**Step 3: Run the migration**

```bash
uv run alembic -c api/alembic.ini upgrade head
```

Expected: migration applies without errors.

**Step 4: Verify columns exist**

```bash
/opt/homebrew/opt/postgresql@16/bin/psql -U margin -d margin_invest -c "\d users" | grep avatar
/opt/homebrew/opt/postgresql@16/bin/psql -U margin -d margin_invest -c "\d credential_users" | grep avatar
```

Expected: both tables show `avatar_url` and (for users) `oauth_avatar_url`.

**Step 5: Commit**

```bash
git add api/alembic/versions/
git commit -m "feat: add alembic migration for avatar columns"
```

---

### Task 3: Wire `get_current_user_id` to extract X-User-Id header

**Files:**
- Modify: `api/src/margin_api/deps.py:15-21`
- Test: `api/tests/test_deps.py`

**Step 1: Write the failing test**

Create `api/tests/test_deps.py`:

```python
"""Tests for FastAPI dependency helpers."""

import pytest
from httpx import ASGITransport, AsyncClient

from margin_api.app import create_app


@pytest.mark.asyncio
async def test_get_current_user_id_from_header():
    """X-User-Id header should be extracted as the current user ID."""
    app = create_app()

    # Add a tiny test route that uses the dependency
    from fastapi import Depends
    from margin_api.deps import get_current_user_id

    @app.get("/test-user-id")
    async def _test_route(user_id: int = Depends(get_current_user_id)):
        return {"user_id": user_id}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/test-user-id", headers={"X-User-Id": "42"})
        assert resp.status_code == 200
        assert resp.json() == {"user_id": 42}


@pytest.mark.asyncio
async def test_get_current_user_id_missing_header():
    """Missing X-User-Id header should return 401."""
    app = create_app()

    from fastapi import Depends
    from margin_api.deps import get_current_user_id

    @app.get("/test-user-id")
    async def _test_route(user_id: int = Depends(get_current_user_id)):
        return {"user_id": user_id}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/test-user-id")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_id_invalid_header():
    """Non-integer X-User-Id header should return 401."""
    app = create_app()

    from fastapi import Depends
    from margin_api.deps import get_current_user_id

    @app.get("/test-user-id")
    async def _test_route(user_id: int = Depends(get_current_user_id)):
        return {"user_id": user_id}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/test-user-id", headers={"X-User-Id": "not-a-number"})
        assert resp.status_code == 401
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_deps.py -v`
Expected: FAIL — `get_current_user_id` always raises 401.

**Step 3: Write minimal implementation**

Replace `get_current_user_id` in `api/src/margin_api/deps.py`:

```python
from fastapi import Depends, Header, HTTPException


def get_current_user_id(
    x_user_id: str | None = Header(None),
) -> int:
    """Extract the current user's ID from the X-User-Id header.

    The Next.js frontend injects this header via serverFetch after
    authenticating with NextAuth.
    """
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return int(x_user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_deps.py -v`
Expected: 3 passed

**Step 5: Run full API test suite to check for regressions**

Run: `uv run pytest api/tests/ -v`
Expected: all pass

**Step 6: Commit**

```bash
git add api/src/margin_api/deps.py api/tests/test_deps.py
git commit -m "feat: implement get_current_user_id from X-User-Id header"
```

---

### Task 4: Add R2 storage service and install dependencies

**Files:**
- Create: `api/src/margin_api/services/storage.py`
- Modify: `api/pyproject.toml` (add Pillow and boto3)
- Test: `api/tests/test_storage.py`

**Step 1: Install dependencies**

```bash
uv add pillow boto3 --package margin-api
```

**Step 2: Write the failing test**

Create `api/tests/test_storage.py`:

```python
"""Tests for R2/S3 storage service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

from margin_api.services.storage import AvatarStorageService


class TestAvatarStorageService:
    def test_init_with_env(self, monkeypatch):
        monkeypatch.setenv("R2_ACCOUNT_ID", "test-account")
        monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-key")
        monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-secret")
        monkeypatch.setenv("R2_BUCKET_NAME", "avatars")
        monkeypatch.setenv("R2_PUBLIC_URL", "https://avatars.example.com")

        svc = AvatarStorageService()
        assert svc.bucket_name == "avatars"
        assert svc.public_url == "https://avatars.example.com"

    def test_storage_key_for_user(self):
        svc = AvatarStorageService.__new__(AvatarStorageService)
        svc.bucket_name = "avatars"
        assert svc._storage_key(42) == "avatars/42.webp"

    def test_public_url_for_user(self):
        svc = AvatarStorageService.__new__(AvatarStorageService)
        svc.public_url = "https://avatars.example.com"
        assert svc.get_public_url(42) == "https://avatars.example.com/avatars/42.webp"
```

**Step 3: Run test to verify it fails**

Run: `uv run pytest api/tests/test_storage.py -v`
Expected: FAIL — module not found.

**Step 4: Write minimal implementation**

Create `api/src/margin_api/services/storage.py`:

```python
"""Cloudflare R2 avatar storage service."""

from __future__ import annotations

import os
from io import BytesIO

import boto3


class AvatarStorageService:
    """Manages avatar image uploads and deletions on Cloudflare R2."""

    def __init__(self) -> None:
        account_id = os.environ["R2_ACCOUNT_ID"]
        self.bucket_name = os.environ.get("R2_BUCKET_NAME", "margin-avatars")
        self.public_url = os.environ["R2_PUBLIC_URL"].rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )

    def _storage_key(self, user_id: int) -> str:
        return f"avatars/{user_id}.webp"

    def get_public_url(self, user_id: int) -> str:
        return f"{self.public_url}/{self._storage_key(user_id)}"

    def upload(self, user_id: int, image_bytes: bytes) -> str:
        """Upload avatar bytes to R2. Returns the public URL."""
        key = self._storage_key(user_id)
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=image_bytes,
            ContentType="image/webp",
        )
        return self.get_public_url(user_id)

    def delete(self, user_id: int) -> None:
        """Delete avatar from R2."""
        key = self._storage_key(user_id)
        self._client.delete_object(Bucket=self.bucket_name, Key=key)
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest api/tests/test_storage.py -v`
Expected: 3 passed

**Step 6: Commit**

```bash
git add api/src/margin_api/services/storage.py api/tests/test_storage.py api/pyproject.toml uv.lock
git commit -m "feat: add R2 avatar storage service with Pillow and boto3"
```

---

### Task 5: Add image processing service (validate, resize, compress)

**Files:**
- Create: `api/src/margin_api/services/image_processing.py`
- Test: `api/tests/test_image_processing.py`

**Step 1: Write the failing test**

Create `api/tests/test_image_processing.py`:

```python
"""Tests for avatar image processing."""

import pytest
from io import BytesIO
from PIL import Image

from margin_api.services.image_processing import (
    process_avatar,
    validate_image,
    InvalidImageError,
)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB


def _make_png(width: int = 200, height: int = 200) -> bytes:
    """Create a minimal PNG image in memory."""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(0, 255, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestValidateImage:
    def test_valid_png(self):
        validate_image(_make_png(), "image/png")

    def test_valid_jpeg(self):
        validate_image(_make_jpeg(), "image/jpeg")

    def test_rejects_unsupported_mime(self):
        with pytest.raises(InvalidImageError, match="Unsupported image type"):
            validate_image(_make_png(), "image/gif")

    def test_rejects_oversized(self):
        big = b"\x00" * (MAX_SIZE + 1)
        with pytest.raises(InvalidImageError, match="exceeds maximum"):
            validate_image(big, "image/png")

    def test_rejects_fake_mime(self):
        """Claiming image/png but sending JPEG bytes should be rejected."""
        with pytest.raises(InvalidImageError, match="does not match"):
            validate_image(_make_jpeg(), "image/png")

    def test_rejects_non_image_bytes(self):
        with pytest.raises(InvalidImageError, match="not a valid image"):
            validate_image(b"not an image at all", "image/png")


class TestProcessAvatar:
    def test_output_is_webp(self):
        result = process_avatar(_make_png())
        img = Image.open(BytesIO(result))
        assert img.format == "WEBP"

    def test_output_is_256x256(self):
        result = process_avatar(_make_png(800, 600))
        img = Image.open(BytesIO(result))
        assert img.size == (256, 256)

    def test_square_input_stays_square(self):
        result = process_avatar(_make_png(100, 100))
        img = Image.open(BytesIO(result))
        assert img.size == (256, 256)

    def test_tall_input_center_cropped(self):
        result = process_avatar(_make_png(200, 400))
        img = Image.open(BytesIO(result))
        assert img.size == (256, 256)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_image_processing.py -v`
Expected: FAIL — module not found.

**Step 3: Write minimal implementation**

Create `api/src/margin_api/services/image_processing.py`:

```python
"""Avatar image validation and processing."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB
OUTPUT_SIZE = 256
OUTPUT_QUALITY = 85

# Magic byte signatures for image types
_MAGIC_BYTES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG"],
    "image/webp": [b"RIFF"],
}


class InvalidImageError(Exception):
    """Raised when image validation fails."""


def validate_image(data: bytes, content_type: str) -> None:
    """Validate image data against type, size, and magic byte checks."""
    if content_type not in ALLOWED_TYPES:
        raise InvalidImageError(f"Unsupported image type: {content_type}")

    if len(data) > MAX_SIZE:
        raise InvalidImageError(
            f"File size {len(data)} exceeds maximum {MAX_SIZE} bytes"
        )

    # Magic byte check
    expected_magic = _MAGIC_BYTES.get(content_type, [])
    if expected_magic and not any(data.startswith(m) for m in expected_magic):
        raise InvalidImageError(
            f"File header does not match declared type {content_type}"
        )

    # Verify Pillow can actually open it
    try:
        img = Image.open(BytesIO(data))
        img.verify()
    except Exception:
        raise InvalidImageError("File is not a valid image")


def process_avatar(data: bytes) -> bytes:
    """Resize and center-crop to 256x256 WebP."""
    img = Image.open(BytesIO(data))
    img = img.convert("RGB")

    # Center crop to square
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))

    # Resize to output dimensions
    img = img.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)

    # Encode as WebP
    buf = BytesIO()
    img.save(buf, format="WEBP", quality=OUTPUT_QUALITY)
    return buf.getvalue()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_image_processing.py -v`
Expected: 10 passed

**Step 5: Commit**

```bash
git add api/src/margin_api/services/image_processing.py api/tests/test_image_processing.py
git commit -m "feat: add avatar image validation and processing service"
```

---

### Task 6: Add avatar upload and delete API routes

**Files:**
- Create: `api/src/margin_api/routes/avatar.py`
- Create: `api/src/margin_api/schemas/avatar.py`
- Modify: `api/src/margin_api/app.py` (register router)
- Test: `api/tests/test_avatar_routes.py`

**Step 1: Write the failing test**

Create `api/tests/test_avatar_routes.py`:

```python
"""Tests for avatar upload and delete routes."""

import pytest
import pytest_asyncio
from io import BytesIO
from unittest.mock import MagicMock, patch

from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker as async_sessionmaker

from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User, CredentialUser
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id


def _make_png(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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
    yield app, factory
    await engine.dispose()


@pytest_asyncio.fixture()
async def oauth_user(app_and_db):
    _, factory = app_and_db
    async with factory() as session:
        user = User(email="test@example.com", name="Test", provider="google")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.mark.asyncio
async def test_upload_avatar(app_and_db, oauth_user):
    app, _ = app_and_db
    app.dependency_overrides[get_current_user_id] = lambda: oauth_user.id

    mock_storage = MagicMock()
    mock_storage.upload.return_value = "https://avatars.example.com/avatars/1.webp"

    with patch("margin_api.routes.avatar._get_storage", return_value=mock_storage):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/users/me/avatar",
                files={"file": ("photo.png", _make_png(), "image/png")},
            )
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] == "https://avatars.example.com/avatars/1.webp"


@pytest.mark.asyncio
async def test_upload_rejects_oversized(app_and_db, oauth_user):
    app, _ = app_and_db
    app.dependency_overrides[get_current_user_id] = lambda: oauth_user.id

    big_file = b"\x89PNG" + b"\x00" * (6 * 1024 * 1024)  # >5MB

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("big.png", big_file, "image/png")},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_wrong_type(app_and_db, oauth_user):
    app, _ = app_and_db
    app.dependency_overrides[get_current_user_id] = lambda: oauth_user.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("doc.pdf", b"%PDF-fake", "application/pdf")},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_avatar(app_and_db, oauth_user):
    app, factory = app_and_db
    app.dependency_overrides[get_current_user_id] = lambda: oauth_user.id

    # Set an avatar first
    async with factory() as session:
        from sqlalchemy import update
        await session.execute(
            update(User).where(User.id == oauth_user.id).values(avatar_url="https://example.com/old.webp")
        )
        await session.commit()

    mock_storage = MagicMock()

    with patch("margin_api.routes.avatar._get_storage", return_value=mock_storage):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/v1/users/me/avatar")
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] is None
    mock_storage.delete.assert_called_once()


@pytest.mark.asyncio
async def test_upload_without_auth(app_and_db):
    app, _ = app_and_db
    # Don't override get_current_user_id — should return 401

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("photo.png", _make_png(), "image/png")},
        )
    assert resp.status_code == 401
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_avatar_routes.py -v`
Expected: FAIL — routes don't exist yet.

**Step 3: Create the schema**

Create `api/src/margin_api/schemas/avatar.py`:

```python
"""Schemas for avatar endpoints."""

from pydantic import BaseModel


class AvatarResponse(BaseModel):
    avatar_url: str | None
```

**Step 4: Create the route**

Create `api/src/margin_api/routes/avatar.py`:

```python
"""Avatar upload and delete routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User, CredentialUser
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.schemas.avatar import AvatarResponse
from margin_api.services.image_processing import (
    InvalidImageError,
    process_avatar,
    validate_image,
)
from margin_api.services.storage import AvatarStorageService

router = APIRouter(prefix="/api/v1/users/me", tags=["avatar"])


def _get_storage() -> AvatarStorageService:
    return AvatarStorageService()


@router.post("/avatar", response_model=AvatarResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    storage: AvatarStorageService = Depends(_get_storage),
) -> AvatarResponse:
    """Upload or replace a user's avatar image."""
    data = await file.read()

    try:
        validate_image(data, file.content_type or "")
    except InvalidImageError as e:
        raise HTTPException(status_code=400, detail=str(e))

    processed = process_avatar(data)
    url = storage.upload(user_id, processed)

    # Update whichever user table this user belongs to
    result = await db.execute(
        update(User).where(User.id == user_id).values(avatar_url=url)
    )
    if result.rowcount == 0:
        await db.execute(
            update(CredentialUser)
            .where(CredentialUser.id == user_id)
            .values(avatar_url=url)
        )
    await db.commit()

    return AvatarResponse(avatar_url=url)


@router.delete("/avatar", response_model=AvatarResponse)
async def delete_avatar(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    storage: AvatarStorageService = Depends(_get_storage),
) -> AvatarResponse:
    """Remove a user's custom avatar."""
    storage.delete(user_id)

    result = await db.execute(
        update(User).where(User.id == user_id).values(avatar_url=None)
    )
    if result.rowcount == 0:
        await db.execute(
            update(CredentialUser)
            .where(CredentialUser.id == user_id)
            .values(avatar_url=None)
        )
    await db.commit()

    return AvatarResponse(avatar_url=None)
```

**Step 5: Register the router**

In `api/src/margin_api/app.py`, add:

```python
from margin_api.routes.avatar import router as avatar_router
```

And in `create_app()`:

```python
    app.include_router(avatar_router)
```

**Step 6: Run test to verify it passes**

Run: `uv run pytest api/tests/test_avatar_routes.py -v`
Expected: 5 passed

**Step 7: Run full API test suite**

Run: `uv run pytest api/tests/ -v`
Expected: all pass

**Step 8: Commit**

```bash
git add api/src/margin_api/routes/avatar.py api/src/margin_api/schemas/avatar.py api/src/margin_api/app.py api/tests/test_avatar_routes.py
git commit -m "feat: add avatar upload and delete API routes"
```

---

### Task 7: Persist OAuth avatar URL at login time

**Files:**
- Modify: `api/src/margin_api/routes/auth.py` (add `avatar_url` to verify-credentials response)
- Modify: `api/src/margin_api/schemas/auth.py:31-38` (add field)
- Modify: `web/src/lib/auth.ts:57-94` (persist OAuth image, pass avatar through session)
- Test: `api/tests/test_auth_routes.py` (update existing test)

**Step 1: Add `avatar_url` to VerifyCredentialsResponse**

In `api/src/margin_api/schemas/auth.py`, add to `VerifyCredentialsResponse`:

```python
class VerifyCredentialsResponse(BaseModel):
    """Response after successful credential verification."""

    id: int
    username: str
    email: str
    mfa_status: str
    challenge_token: str
    avatar_url: str | None = None
```

**Step 2: Update the auth route to return avatar_url**

In `api/src/margin_api/routes/auth.py`, update `verify_credentials` to include avatar from the user record:

```python
    return VerifyCredentialsResponse(
        id=result["id"],
        username=result["username"],
        email=result["email"],
        mfa_status=mfa_status,
        challenge_token=challenge_token,
        avatar_url=result.get("avatar_url"),
    )
```

And update the `AuthService.verify_credentials` method in `api/src/margin_api/services/auth.py` to include `avatar_url` in its return dict.

**Step 3: Update NextAuth callbacks to persist avatar data**

In `web/src/lib/auth.ts`, update the JWT callback (line 77):

```typescript
    jwt({ token, user, account, profile }) {
      if (user) {
        token.userId = user.id
        token.authMethod = account?.type === "oauth" || account?.type === "oidc"
          ? "oauth"
          : "credentials"
        token.mfaVerified = token.authMethod === "oauth"
          ? true
          : !!(user as Record<string, unknown>).mfaToken

        // Avatar: OAuth providers include image in user profile
        if (token.authMethod === "oauth" && user.image) {
          token.oauthAvatarUrl = user.image
        }
        // Avatar: credentials provider returns avatar_url from API
        const avatarUrl = (user as Record<string, unknown>).avatarUrl as string | undefined
        if (avatarUrl) {
          token.avatarUrl = avatarUrl
        }
      }
      return token
    },
```

Update the session callback (line 89):

```typescript
    session({ session, token }) {
      session.userId = token.userId as string
      session.authMethod = token.authMethod as string
      session.mfaVerified = token.mfaVerified as boolean
      session.avatarUrl = (token.avatarUrl as string) || null
      session.oauthAvatarUrl = (token.oauthAvatarUrl as string) || null
      return session
    },
```

Update the credentials `authorize` return (line 38):

```typescript
        return {
          id: data.userId,
          name: data.name,
          email: data.email,
          mfaStatus: data.mfaStatus,
          challengeToken: data.challengeToken,
          mfaToken: credentials.mfaToken as string | undefined,
          avatarUrl: data.avatar_url,
        }
```

**Step 4: Run existing auth tests to check for regressions**

Run: `uv run pytest api/tests/test_auth_routes.py -v`
Expected: all pass

**Step 5: Run web tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: all pass

**Step 6: Commit**

```bash
git add api/src/margin_api/schemas/auth.py api/src/margin_api/routes/auth.py api/src/margin_api/services/auth.py web/src/lib/auth.ts
git commit -m "feat: persist OAuth avatar URL and pass avatar through session"
```

---

### Task 8: Create the shared `<Avatar>` frontend component

**Files:**
- Create: `web/src/components/ui/avatar.tsx`
- Create: `web/src/lib/avatar.ts` (initials + color generation)
- Test: `web/src/components/ui/__tests__/avatar.test.tsx`
- Test: `web/src/lib/__tests__/avatar.test.ts`

**Step 1: Write the failing tests**

Create `web/src/lib/__tests__/avatar.test.ts`:

```typescript
import { describe, it, expect } from "vitest"
import { getInitials, getAvatarColor } from "../avatar"

describe("getInitials", () => {
  it("extracts two initials from two-word name", () => {
    expect(getInitials("Brandon Lee")).toBe("BL")
  })

  it("extracts one initial from single name", () => {
    expect(getInitials("Brandon")).toBe("B")
  })

  it("handles email fallback", () => {
    expect(getInitials("brandon@example.com")).toBe("B")
  })

  it("handles empty string", () => {
    expect(getInitials("")).toBe("?")
  })

  it("uppercases initials", () => {
    expect(getInitials("john doe")).toBe("JD")
  })
})

describe("getAvatarColor", () => {
  it("returns a consistent color for the same input", () => {
    const a = getAvatarColor("test@example.com")
    const b = getAvatarColor("test@example.com")
    expect(a).toBe(b)
  })

  it("returns different colors for different inputs", () => {
    const a = getAvatarColor("alice@example.com")
    const b = getAvatarColor("bob@example.com")
    // Not guaranteed to differ but highly likely with 10 colors
    expect(typeof a).toBe("string")
    expect(typeof b).toBe("string")
  })

  it("returns a valid hex color", () => {
    const color = getAvatarColor("test")
    expect(color).toMatch(/^#[0-9a-fA-F]{6}$/)
  })
})
```

Create `web/src/components/ui/__tests__/avatar.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { Avatar } from "../avatar"

describe("Avatar", () => {
  it("renders custom avatar when avatarUrl is provided", () => {
    render(<Avatar name="Test" avatarUrl="https://example.com/photo.webp" size="md" />)
    const img = screen.getByRole("img")
    expect(img).toHaveAttribute("src", "https://example.com/photo.webp")
  })

  it("renders oauth avatar when only oauthAvatarUrl is provided", () => {
    render(<Avatar name="Test" oauthAvatarUrl="https://google.com/photo.jpg" size="md" />)
    const img = screen.getByRole("img")
    expect(img).toHaveAttribute("src", "https://google.com/photo.jpg")
  })

  it("renders initials when no URLs provided", () => {
    render(<Avatar name="Brandon Lee" size="md" />)
    const svg = document.querySelector("svg")
    expect(svg).toBeTruthy()
    expect(svg?.textContent).toContain("BL")
  })

  it("falls back to initials when image fails to load", () => {
    render(<Avatar name="Test User" avatarUrl="https://broken.url/photo.webp" size="md" />)
    const img = screen.getByRole("img")
    fireEvent.error(img)
    const svg = document.querySelector("svg")
    expect(svg).toBeTruthy()
    expect(svg?.textContent).toContain("TU")
  })

  it("renders correct size for sm", () => {
    render(<Avatar name="Test" size="sm" />)
    const svg = document.querySelector("svg")
    expect(svg).toHaveAttribute("width", "24")
    expect(svg).toHaveAttribute("height", "24")
  })

  it("renders correct size for lg", () => {
    render(<Avatar name="Test" size="lg" />)
    const svg = document.querySelector("svg")
    expect(svg).toHaveAttribute("width", "48")
    expect(svg).toHaveAttribute("height", "48")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/lib/__tests__/avatar.test.ts src/components/ui/__tests__/avatar.test.tsx`
Expected: FAIL — modules not found.

**Step 3: Implement the avatar utility**

Create `web/src/lib/avatar.ts`:

```typescript
/**
 * Deterministic avatar utilities — initials and color generation.
 * Pure functions, SSR-safe, no randomness.
 */

const AVATAR_COLORS = [
  "#6366f1", // indigo
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#ef4444", // red
  "#f97316", // orange
  "#eab308", // yellow
  "#22c55e", // green
  "#14b8a6", // teal
  "#06b6d4", // cyan
  "#3b82f6", // blue
]

export function getInitials(name: string): string {
  if (!name || !name.trim()) return "?"

  // If it looks like an email, use the part before @
  const cleanName = name.includes("@") ? name.split("@")[0] : name

  const parts = cleanName.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return parts[0][0].toUpperCase()
}

export function getAvatarColor(identifier: string): string {
  // Simple deterministic hash
  let hash = 0
  for (let i = 0; i < identifier.length; i++) {
    hash = (hash * 31 + identifier.charCodeAt(i)) | 0
  }
  const index = Math.abs(hash) % AVATAR_COLORS.length
  return AVATAR_COLORS[index]
}
```

**Step 4: Implement the Avatar component**

Create `web/src/components/ui/avatar.tsx`:

```tsx
"use client"

import { useState } from "react"
import { getInitials, getAvatarColor } from "@/lib/avatar"

const SIZES = { sm: 24, md: 32, lg: 48 } as const

type AvatarSize = keyof typeof SIZES

interface AvatarProps {
  name: string
  avatarUrl?: string | null
  oauthAvatarUrl?: string | null
  size: AvatarSize
  className?: string
}

function InitialsAvatar({ name, size, className }: { name: string; size: number; className?: string }) {
  const initials = getInitials(name)
  const color = getAvatarColor(name)
  const fontSize = Math.round(size * 0.4)

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={`rounded-full flex-shrink-0 ${className ?? ""}`}
    >
      <circle cx={size / 2} cy={size / 2} r={size / 2} fill={color} />
      <text
        x="50%"
        y="50%"
        dy=".1em"
        textAnchor="middle"
        dominantBaseline="central"
        fill="white"
        fontSize={fontSize}
        fontWeight="600"
        fontFamily="system-ui, sans-serif"
      >
        {initials}
      </text>
    </svg>
  )
}

export function Avatar({ name, avatarUrl, oauthAvatarUrl, size, className }: AvatarProps) {
  const px = SIZES[size]
  const [failedUrls, setFailedUrls] = useState<Set<string>>(new Set())

  const urls = [avatarUrl, oauthAvatarUrl].filter(
    (u): u is string => !!u && !failedUrls.has(u)
  )

  const activeUrl = urls[0]

  if (!activeUrl) {
    return <InitialsAvatar name={name} size={px} className={className} />
  }

  return (
    <img
      src={activeUrl}
      alt={`${name}'s avatar`}
      width={px}
      height={px}
      className={`rounded-full object-cover flex-shrink-0 ${className ?? ""}`}
      onError={() => setFailedUrls((prev) => new Set(prev).add(activeUrl))}
    />
  )
}
```

**Step 5: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/lib/__tests__/avatar.test.ts src/components/ui/__tests__/avatar.test.tsx`
Expected: all pass

**Step 6: Commit**

```bash
git add web/src/lib/avatar.ts web/src/components/ui/avatar.tsx web/src/lib/__tests__/avatar.test.ts web/src/components/ui/__tests__/avatar.test.tsx
git commit -m "feat: add Avatar component with deterministic initials fallback"
```

---

### Task 9: Integrate Avatar into navbar and account settings

**Files:**
- Modify: `web/src/components/layout/nav.tsx:59-70` (desktop), `:116-127` (mobile)
- Modify: `web/src/components/settings/account-section.tsx:14-20`

**Step 1: Update the navbar (desktop)**

In `web/src/components/layout/nav.tsx`, import Avatar:

```typescript
import { Avatar } from "@/components/ui/avatar"
```

Replace lines 59-70 (desktop user menu):

```tsx
{session?.user ? (
  <div className="flex items-center gap-3">
    <Avatar
      name={session.user.name || session.user.email || ""}
      avatarUrl={(session as any).avatarUrl}
      oauthAvatarUrl={(session as any).oauthAvatarUrl ?? session.user.image}
      size="sm"
    />
    <span className="text-sm text-text-secondary">
      {session.user.name || session.user.email}
    </span>
    <button
      onClick={() => signOut()}
      className="text-sm text-text-secondary hover:text-text-primary transition-colors"
    >
      Sign Out
    </button>
  </div>
) : (
```

Replace lines 116-122 (mobile user menu — add avatar before sign out):

```tsx
{session?.user ? (
  <div className="flex items-center gap-3 py-2">
    <Avatar
      name={session.user.name || session.user.email || ""}
      avatarUrl={(session as any).avatarUrl}
      oauthAvatarUrl={(session as any).oauthAvatarUrl ?? session.user.image}
      size="sm"
    />
    <button
      onClick={() => signOut()}
      className="text-sm text-text-secondary"
    >
      Sign Out
    </button>
  </div>
) : (
```

**Step 2: Update account settings**

In `web/src/components/settings/account-section.tsx`, import Avatar:

```typescript
import { Avatar } from "@/components/ui/avatar"
```

Replace lines 14-20 (the conditional img):

```tsx
<div className="flex items-center gap-4">
  <Avatar
    name={session.user.name || session.user.email || ""}
    avatarUrl={(session as any).avatarUrl}
    oauthAvatarUrl={(session as any).oauthAvatarUrl ?? session.user.image}
    size="lg"
  />
  <div>
    <div className="text-text-primary font-medium">
      {session.user.name || "User"}
    </div>
    <div className="text-sm text-text-secondary">
      {session.user.email}
    </div>
  </div>
</div>
```

**Step 3: Run web tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: all pass

**Step 4: Commit**

```bash
git add web/src/components/layout/nav.tsx web/src/components/settings/account-section.tsx
git commit -m "feat: integrate Avatar component into navbar and account settings"
```

---

### Task 10: Add avatar upload UI to account settings

**Files:**
- Modify: `web/src/components/settings/account-section.tsx`
- Create: `web/src/components/settings/__tests__/account-section.test.tsx`

**Step 1: Write the test**

Create `web/src/components/settings/__tests__/account-section.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

const mockSession = {
  user: { name: "Test User", email: "test@example.com", image: null },
  authMethod: "credentials",
  avatarUrl: null,
  oauthAvatarUrl: null,
}

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: mockSession }),
}))

const { AccountSection } = await import("../account-section")

describe("AccountSection", () => {
  it("renders upload button when no custom avatar exists", () => {
    render(<AccountSection />)
    expect(screen.getByText("Upload Avatar")).toBeTruthy()
  })

  it("renders user name", () => {
    render(<AccountSection />)
    expect(screen.getByText("Test User")).toBeTruthy()
  })

  it("renders user email", () => {
    render(<AccountSection />)
    expect(screen.getByText("test@example.com")).toBeTruthy()
  })
})
```

**Step 2: Add upload/remove controls to account-section.tsx**

Update `web/src/components/settings/account-section.tsx` to add an upload button below the avatar, and a remove button when a custom avatar exists. Use a hidden `<input type="file">` triggered by the button. On file selection, POST to `/api/v1/users/me/avatar` as `multipart/form-data`. On success, update the session (this may require a page refresh or `useRouter().refresh()`).

```tsx
"use client"

import { useSession } from "next-auth/react"
import { useRef, useState } from "react"
import { Avatar } from "@/components/ui/avatar"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function AccountSection() {
  const { data: session, update } = useSession()
  const authMethod = (session as any)?.authMethod
  const avatarUrl = (session as any)?.avatarUrl as string | null
  const oauthAvatarUrl = (session as any)?.oauthAvatarUrl ?? session?.user?.image
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)

    const formData = new FormData()
    formData.append("file", file)

    try {
      const res = await fetch(`${API_URL}/api/v1/users/me/avatar`, {
        method: "POST",
        headers: {
          "X-User-Id": (session as any)?.userId || "",
        },
        body: formData,
      })

      if (!res.ok) {
        const data = await res.json().catch(() => null)
        throw new Error(data?.detail || "Upload failed")
      }

      // Trigger session refresh to pick up new avatar
      await update()
      window.location.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  async function handleRemove() {
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/users/me/avatar`, {
        method: "DELETE",
        headers: {
          "X-User-Id": (session as any)?.userId || "",
        },
      })
      if (!res.ok) throw new Error("Delete failed")
      await update()
      window.location.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed")
    }
  }

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-4">Account</h2>
      {session?.user ? (
        <div className="space-y-3">
          <div className="flex items-center gap-4">
            <Avatar
              name={session.user.name || session.user.email || ""}
              avatarUrl={avatarUrl}
              oauthAvatarUrl={oauthAvatarUrl}
              size="lg"
            />
            <div>
              <div className="text-text-primary font-medium">
                {session.user.name || "User"}
              </div>
              <div className="text-sm text-text-secondary">
                {session.user.email}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleUpload}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="text-sm text-accent hover:text-accent-hover transition-colors disabled:opacity-50"
            >
              {uploading ? "Uploading..." : "Upload Avatar"}
            </button>
            {avatarUrl && (
              <button
                onClick={handleRemove}
                className="text-sm text-text-secondary hover:text-red-400 transition-colors"
              >
                Remove
              </button>
            )}
          </div>
          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

          {authMethod === "credentials" && (
            <div className="border-t border-border-primary pt-4">
              <h3 className="text-md font-medium text-text-primary mb-2">Multi-Factor Authentication</h3>
              <p className="text-sm text-text-secondary">MFA is enabled for your account. You can manage your authentication methods below.</p>
            </div>
          )}
        </div>
      ) : (
        <p className="text-text-secondary">Loading account information...</p>
      )}
    </section>
  )
}
```

**Step 3: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: all pass

**Step 4: Commit**

```bash
git add web/src/components/settings/account-section.tsx web/src/components/settings/__tests__/account-section.test.tsx
git commit -m "feat: add avatar upload and remove UI to account settings"
```

---

### Task 11: Add R2 environment variables and final integration test

**Files:**
- Modify: `web/.env.local` (add R2 config placeholder)
- Modify: `api/src/margin_api/config.py` (add R2 settings if using pydantic-settings)

**Step 1: Add environment variable documentation**

Add the following to the project's `.env.example` or document in the design doc:

```bash
# Cloudflare R2 — Avatar Storage
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret-key
R2_BUCKET_NAME=margin-avatars
R2_PUBLIC_URL=https://avatars.yourdomain.com
```

**Step 2: Run the full test suite across all three packages**

```bash
cd /Users/brandon/repos/margin_invest
uv run pytest engine/tests/ -v       # 816+ tests
uv run pytest api/tests/ -v          # 430+ tests
cd web && npx vitest run             # 193+ tests
```

Expected: all pass with zero failures.

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: complete avatar system with R2 config and integration"
```
