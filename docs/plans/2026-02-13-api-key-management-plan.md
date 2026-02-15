# API Key Management & Stripe Subscription Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add subscription-gated API key management with full Stripe billing integration — free users get yfinance-only, paid subscribers unlock premium providers via encrypted API keys.

**Architecture:** Stripe Checkout + webhooks for billing. Subscription plan stored on User/CredentialUser models, enforced via `require_plan` FastAPI dependency. API keys encrypted with Fernet (separate key from MFA). Platform-managed keys rotate every 90 days via ARQ worker.

**Tech Stack:** stripe (Python SDK), cryptography.fernet, FastAPI, SQLAlchemy 2.0 async, ARQ, Next.js 16

---

### Task 1: Install stripe dependency and add config settings

**Files:**
- Modify: `api/pyproject.toml`
- Modify: `api/src/margin_api/config.py:10-37`
- Test: `api/tests/test_config.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_config.py`:

```python
"""Tests for config settings."""

from __future__ import annotations

import os
import pytest
from margin_api.config import Settings


class TestStripeSettings:
    def test_stripe_settings_exist(self):
        """Settings class has Stripe fields with empty defaults."""
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            mfa_encryption_key="",
        )
        assert s.stripe_secret_key == ""
        assert s.stripe_publishable_key == ""
        assert s.stripe_webhook_secret == ""
        assert s.stripe_price_id == ""

    def test_api_key_encryption_key_exists(self):
        """Settings class has API key encryption field."""
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            mfa_encryption_key="",
        )
        assert s.api_key_encryption_key == ""

    def test_stripe_settings_from_env(self, monkeypatch):
        """Stripe settings load from MARGIN_-prefixed env vars."""
        monkeypatch.setenv("MARGIN_STRIPE_SECRET_KEY", "sk_test_123")
        monkeypatch.setenv("MARGIN_STRIPE_PUBLISHABLE_KEY", "pk_test_456")
        monkeypatch.setenv("MARGIN_STRIPE_WEBHOOK_SECRET", "whsec_789")
        monkeypatch.setenv("MARGIN_STRIPE_PRICE_ID", "price_abc")
        monkeypatch.setenv("MARGIN_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        s = Settings()
        assert s.stripe_secret_key == "sk_test_123"
        assert s.stripe_publishable_key == "pk_test_456"
        assert s.stripe_webhook_secret == "whsec_789"
        assert s.stripe_price_id == "price_abc"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_config.py -v`
Expected: FAIL — `Settings` has no `stripe_secret_key` attribute.

**Step 3: Install stripe and add config fields**

```bash
uv add stripe --package margin-api
```

Then modify `api/src/margin_api/config.py` — add after the MFA section (line 26-29):

```python
    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    # API Key encryption (separate from MFA encryption key)
    api_key_encryption_key: str = ""
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_config.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add api/pyproject.toml uv.lock api/src/margin_api/config.py api/tests/test_config.py
git commit -m "feat: add Stripe and API key encryption config settings"
```

---

### Task 2: Update User and CredentialUser models with subscription fields

**Files:**
- Modify: `api/src/margin_api/db/models.py:66-78` (User) and `:142-165` (CredentialUser)
- Test: `api/tests/test_subscription_models.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_subscription_models.py`:

```python
"""Tests for subscription-related model fields."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import CredentialUser, User


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


class TestUserSubscriptionFields:
    @pytest.mark.asyncio
    async def test_user_defaults_to_free_plan(self, db):
        user = User(email="a@b.com", name="A", provider="google")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.subscription_plan == "free"
        assert user.stripe_customer_id is None
        assert user.stripe_subscription_id is None

    @pytest.mark.asyncio
    async def test_user_can_set_margin_invest_plan(self, db):
        user = User(
            email="a@b.com",
            name="A",
            provider="google",
            subscription_plan="margin_invest",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_456",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.subscription_plan == "margin_invest"
        assert user.stripe_customer_id == "cus_123"
        assert user.stripe_subscription_id == "sub_456"


class TestCredentialUserSubscriptionFields:
    @pytest.mark.asyncio
    async def test_credential_user_defaults_to_free_plan(self, db):
        user = CredentialUser(
            username="alice",
            email="alice@example.com",
            password_hash="hashed",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.subscription_plan == "free"
        assert user.stripe_customer_id is None
        assert user.stripe_subscription_id is None

    @pytest.mark.asyncio
    async def test_credential_user_can_set_plan(self, db):
        user = CredentialUser(
            username="alice",
            email="alice@example.com",
            password_hash="hashed",
            subscription_plan="margin_invest",
            stripe_customer_id="cus_abc",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        assert user.subscription_plan == "margin_invest"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_subscription_models.py -v`
Expected: FAIL — `User` has no `subscription_plan` attribute.

**Step 3: Add subscription fields to models**

In `api/src/margin_api/db/models.py`, add three fields to the `User` class (after `provider` on line 72):

```python
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="free")
```

Add the same three fields to `CredentialUser` (after `last_totp_counter` on line 153):

```python
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="free")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_subscription_models.py -v`
Expected: PASS (4 tests)

**Step 5: Run existing tests to verify nothing breaks**

Run: `uv run pytest api/tests/ -v`
Expected: All existing tests still pass.

**Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_subscription_models.py
git commit -m "feat: add subscription and Stripe fields to User and CredentialUser models"
```

---

### Task 3: Update ApiKey model and add ApiKeyEvent model

**Files:**
- Modify: `api/src/margin_api/db/models.py:120-134` (ApiKey)
- Modify: `api/src/margin_api/db/models.py` (add ApiKeyEvent class)
- Test: `api/tests/test_api_key_models.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_api_key_models.py`:

```python
"""Tests for updated ApiKey and new ApiKeyEvent models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import ApiKey, ApiKeyEvent, User


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def user(db):
    u = User(email="a@b.com", name="A", provider="google")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


class TestApiKeyModel:
    @pytest.mark.asyncio
    async def test_api_key_has_new_fields(self, db, user):
        key = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="encrypted_value",
            is_platform_managed=True,
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)
        assert key.is_platform_managed is True
        assert key.expires_at is None
        assert key.revoked_at is None

    @pytest.mark.asyncio
    async def test_api_key_allows_multiple_per_provider(self, db, user):
        """No unique constraint — allows overlap during rotation."""
        key1 = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="old_key",
            is_platform_managed=True,
        )
        key2 = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="new_key",
            is_platform_managed=True,
        )
        db.add_all([key1, key2])
        await db.commit()
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.user_id == user.id, ApiKey.provider_name == "fmp"
            )
        )
        keys = list(result.scalars().all())
        assert len(keys) == 2

    @pytest.mark.asyncio
    async def test_api_key_soft_delete_via_revoked_at(self, db, user):
        key = ApiKey(
            user_id=user.id,
            provider_name="polygon",
            encrypted_key="enc",
            revoked_at=datetime.now(UTC),
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)
        assert key.revoked_at is not None


class TestApiKeyEventModel:
    @pytest.mark.asyncio
    async def test_event_creation(self, db, user):
        key = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="enc",
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)

        event = ApiKeyEvent(
            api_key_id=key.id,
            event_type="created",
            ip_address="127.0.0.1",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        assert event.event_type == "created"
        assert event.api_key_id == key.id

    @pytest.mark.asyncio
    async def test_event_relationship(self, db, user):
        key = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key="enc",
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)

        event = ApiKeyEvent(
            api_key_id=key.id,
            event_type="accessed",
        )
        db.add(event)
        await db.commit()

        result = await db.execute(select(ApiKey).where(ApiKey.id == key.id))
        loaded_key = result.scalar_one()
        await db.refresh(loaded_key, ["events"])
        assert len(loaded_key.events) == 1
        assert loaded_key.events[0].event_type == "accessed"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_api_key_models.py -v`
Expected: FAIL — `ApiKey` has no `is_platform_managed` attribute and `ApiKeyEvent` doesn't exist.

**Step 3: Update ApiKey and add ApiKeyEvent**

In `api/src/margin_api/db/models.py`, replace the entire `ApiKey` class (lines 120-134) with:

```python
class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_name: Mapped[str] = mapped_column(String(50))
    encrypted_key: Mapped[str] = mapped_column(Text)
    is_platform_managed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="api_keys")
    events: Mapped[list[ApiKeyEvent]] = relationship(back_populates="api_key")
```

Note: The old `UniqueConstraint("user_id", "provider_name")` is removed — multiple keys per provider are needed for rotation overlap.

Add a new `ApiKeyEvent` class right after `ApiKey`:

```python
class ApiKeyEvent(Base):
    """Audit trail for API key lifecycle events."""

    __tablename__ = "api_key_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(20))  # created, rotated, revoked, accessed
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    api_key: Mapped[ApiKey] = relationship(back_populates="events")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_api_key_models.py -v`
Expected: PASS (5 tests)

**Step 5: Run all tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass. Note: the old `uq_user_provider` constraint removal may cause existing tests that relied on it to need adjustment — check and fix if needed.

**Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_api_key_models.py
git commit -m "feat: update ApiKey model with rotation fields, add ApiKeyEvent audit model"
```

---

### Task 4: Create ApiKeyService with Fernet encryption

**Files:**
- Create: `api/src/margin_api/services/api_keys.py`
- Test: `api/tests/test_api_key_service.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_api_key_service.py`:

```python
"""Tests for ApiKeyService — encryption, CRUD, rotation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import ApiKey, ApiKeyEvent, User
from margin_api.services.api_keys import ApiKeyService

_TEST_KEY = Fernet.generate_key()


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def user(db):
    u = User(email="a@b.com", name="A", provider="google")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
def service():
    return ApiKeyService(encryption_key=_TEST_KEY)


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self, service):
        plaintext = "sk_live_abc123"
        encrypted = service.encrypt(plaintext)
        assert encrypted != plaintext
        assert service.decrypt(encrypted) == plaintext

    def test_encrypted_values_are_different_each_time(self, service):
        """Fernet includes a timestamp, so encryptions of the same value differ."""
        a = service.encrypt("same")
        b = service.encrypt("same")
        assert a != b


class TestSaveKey:
    @pytest.mark.asyncio
    async def test_save_user_provided_key(self, db, user, service):
        key = await service.save_key(
            session=db,
            user_id=user.id,
            provider_name="fmp",
            plaintext_key="sk_live_fmp_123",
            is_platform_managed=False,
        )
        assert key.provider_name == "fmp"
        assert key.is_platform_managed is False
        assert key.encrypted_key != "sk_live_fmp_123"
        # Decrypt should roundtrip
        assert service.decrypt(key.encrypted_key) == "sk_live_fmp_123"

    @pytest.mark.asyncio
    async def test_save_key_revokes_existing(self, db, user, service):
        """Saving a new key for the same provider revokes the old one."""
        old = await service.save_key(db, user.id, "fmp", "old_key", False)
        new = await service.save_key(db, user.id, "fmp", "new_key", False)
        await db.refresh(old)
        assert old.revoked_at is not None
        assert new.revoked_at is None

    @pytest.mark.asyncio
    async def test_save_key_creates_event(self, db, user, service):
        key = await service.save_key(db, user.id, "polygon", "pk_123", False)
        result = await db.execute(
            select(ApiKeyEvent).where(ApiKeyEvent.api_key_id == key.id)
        )
        events = list(result.scalars().all())
        assert len(events) == 1
        assert events[0].event_type == "created"


class TestGetActiveKey:
    @pytest.mark.asyncio
    async def test_get_active_key(self, db, user, service):
        await service.save_key(db, user.id, "fmp", "the_key", False)
        key = await service.get_active_key(db, user.id, "fmp")
        assert key is not None
        assert service.decrypt(key.encrypted_key) == "the_key"

    @pytest.mark.asyncio
    async def test_get_active_key_returns_none_when_revoked(self, db, user, service):
        k = await service.save_key(db, user.id, "fmp", "the_key", False)
        k.revoked_at = datetime.now(UTC)
        await db.commit()
        key = await service.get_active_key(db, user.id, "fmp")
        assert key is None

    @pytest.mark.asyncio
    async def test_get_active_key_excludes_expired(self, db, user, service):
        k = await service.save_key(db, user.id, "fmp", "the_key", False)
        k.expires_at = datetime.now(UTC) - timedelta(hours=1)
        await db.commit()
        key = await service.get_active_key(db, user.id, "fmp")
        assert key is None


class TestListKeys:
    @pytest.mark.asyncio
    async def test_list_active_keys(self, db, user, service):
        await service.save_key(db, user.id, "fmp", "key1", False)
        await service.save_key(db, user.id, "polygon", "key2", True)
        keys = await service.list_active_keys(db, user.id)
        assert len(keys) == 2
        providers = {k.provider_name for k in keys}
        assert providers == {"fmp", "polygon"}


class TestRevokeKey:
    @pytest.mark.asyncio
    async def test_revoke_key(self, db, user, service):
        key = await service.save_key(db, user.id, "fmp", "key1", False)
        revoked = await service.revoke_key(db, user.id, "fmp")
        assert revoked is True
        await db.refresh(key)
        assert key.revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_creates_event(self, db, user, service):
        key = await service.save_key(db, user.id, "fmp", "key1", False)
        await service.revoke_key(db, user.id, "fmp")
        result = await db.execute(
            select(ApiKeyEvent).where(
                ApiKeyEvent.api_key_id == key.id,
                ApiKeyEvent.event_type == "revoked",
            )
        )
        assert result.scalar_one_or_none() is not None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_api_key_service.py -v`
Expected: FAIL — `margin_api.services.api_keys` does not exist.

**Step 3: Implement ApiKeyService**

Create `api/src/margin_api/services/api_keys.py`:

```python
"""API key management service with Fernet encryption."""

from __future__ import annotations

from datetime import UTC, datetime

from cryptography.fernet import Fernet
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import ApiKey, ApiKeyEvent


class ApiKeyService:
    """Manages encrypted API key lifecycle: save, retrieve, revoke."""

    def __init__(self, encryption_key: bytes) -> None:
        self._fernet = Fernet(encryption_key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()

    async def save_key(
        self,
        session: AsyncSession,
        user_id: int,
        provider_name: str,
        plaintext_key: str,
        is_platform_managed: bool,
        ip_address: str | None = None,
    ) -> ApiKey:
        """Encrypt and save a key. Revokes any existing active key for the same provider."""
        # Revoke existing active key for this provider
        existing = await self.get_active_key(session, user_id, provider_name)
        if existing is not None:
            existing.revoked_at = datetime.now(UTC)
            session.add(
                ApiKeyEvent(
                    api_key_id=existing.id,
                    event_type="revoked",
                    ip_address=ip_address,
                )
            )

        encrypted = self.encrypt(plaintext_key)
        key = ApiKey(
            user_id=user_id,
            provider_name=provider_name,
            encrypted_key=encrypted,
            is_platform_managed=is_platform_managed,
        )
        session.add(key)
        await session.commit()
        await session.refresh(key)

        session.add(
            ApiKeyEvent(
                api_key_id=key.id,
                event_type="created",
                ip_address=ip_address,
            )
        )
        await session.commit()
        return key

    async def get_active_key(
        self,
        session: AsyncSession,
        user_id: int,
        provider_name: str,
    ) -> ApiKey | None:
        """Get the currently active (non-revoked, non-expired) key for a provider."""
        now = datetime.now(UTC)
        stmt = (
            select(ApiKey)
            .where(
                ApiKey.user_id == user_id,
                ApiKey.provider_name == provider_name,
                ApiKey.revoked_at.is_(None),
            )
            .where(
                # Not expired: either no expiry or expiry in the future
                (ApiKey.expires_at.is_(None)) | (ApiKey.expires_at > now)
            )
            .order_by(ApiKey.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_keys(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> list[ApiKey]:
        """List all active (non-revoked, non-expired) keys for a user."""
        now = datetime.now(UTC)
        stmt = (
            select(ApiKey)
            .where(
                ApiKey.user_id == user_id,
                ApiKey.revoked_at.is_(None),
            )
            .where((ApiKey.expires_at.is_(None)) | (ApiKey.expires_at > now))
            .order_by(ApiKey.provider_name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def revoke_key(
        self,
        session: AsyncSession,
        user_id: int,
        provider_name: str,
        ip_address: str | None = None,
    ) -> bool:
        """Revoke the active key for a provider. Returns True if a key was revoked."""
        key = await self.get_active_key(session, user_id, provider_name)
        if key is None:
            return False
        key.revoked_at = datetime.now(UTC)
        session.add(
            ApiKeyEvent(
                api_key_id=key.id,
                event_type="revoked",
                ip_address=ip_address,
            )
        )
        await session.commit()
        return True
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_api_key_service.py -v`
Expected: PASS (11 tests)

**Step 5: Commit**

```bash
git add api/src/margin_api/services/api_keys.py api/tests/test_api_key_service.py
git commit -m "feat: add ApiKeyService with Fernet encryption, CRUD, and audit events"
```

---

### Task 5: Create billing schemas

**Files:**
- Create: `api/src/margin_api/schemas/billing.py`
- Create: `api/src/margin_api/schemas/keys.py`

**Step 1: Create billing schemas**

Create `api/src/margin_api/schemas/billing.py`:

```python
"""Billing API request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class CheckoutResponse(BaseModel):
    """Response with Stripe Checkout URL."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Response with Stripe Customer Portal URL."""

    portal_url: str


class BillingStatusResponse(BaseModel):
    """Current subscription status."""

    subscription_plan: str  # "free" | "margin_invest"
    stripe_subscription_id: str | None = None
    is_active: bool
```

Create `api/src/margin_api/schemas/keys.py`:

```python
"""API key management request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SaveKeyRequest(BaseModel):
    """Request body for saving an API key."""

    provider_name: str = Field(min_length=1, max_length=50)
    api_key: str = Field(min_length=1)


class ApiKeyResponse(BaseModel):
    """Response for a single API key (masked, never plaintext)."""

    id: int
    provider_name: str
    masked_key: str  # e.g., "sk_live_...abc"
    is_platform_managed: bool
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    """Response for listing API keys."""

    keys: list[ApiKeyResponse]
```

**Step 2: Commit**

```bash
git add api/src/margin_api/schemas/billing.py api/src/margin_api/schemas/keys.py
git commit -m "feat: add billing and API key Pydantic schemas"
```

---

### Task 6: Create require_plan dependency

**Files:**
- Create: `api/src/margin_api/deps.py`
- Test: `api/tests/test_deps.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_deps.py`:

```python
"""Tests for FastAPI dependency helpers."""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import require_plan, get_current_user_id


@pytest_asyncio.fixture()
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed a free user and a paid user
    async with factory() as session:
        free_user = User(email="free@test.com", name="Free", provider="google")
        paid_user = User(
            email="paid@test.com",
            name="Paid",
            provider="google",
            subscription_plan="margin_invest",
        )
        session.add_all([free_user, paid_user])
        await session.commit()
        await session.refresh(free_user)
        await session.refresh(paid_user)
        free_id = free_user.id
        paid_id = paid_user.id

    app = FastAPI()

    async def override_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    # Test endpoint gated by require_plan
    @app.get("/premium")
    async def premium_endpoint(
        _=Depends(require_plan("margin_invest")),
    ):
        return {"access": "granted"}

    yield app, free_id, paid_id
    await engine.dispose()


class TestRequirePlan:
    @pytest.mark.asyncio
    async def test_free_user_denied(self, setup):
        app, free_id, _ = setup
        # Override get_current_user_id to return free user
        app.dependency_overrides[get_current_user_id] = lambda: free_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/premium")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_paid_user_allowed(self, setup):
        app, _, paid_id = setup
        app.dependency_overrides[get_current_user_id] = lambda: paid_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/premium")
        assert resp.status_code == 200
        assert resp.json() == {"access": "granted"}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_deps.py -v`
Expected: FAIL — `margin_api.deps` does not exist.

**Step 3: Implement deps.py**

Create `api/src/margin_api/deps.py`:

```python
"""FastAPI dependency helpers for auth and plan enforcement."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User
from margin_api.db.session import get_db


def get_current_user_id() -> int:
    """Placeholder: returns the current user's ID.

    In production this will extract the user ID from the JWT/session.
    Override in tests or replace with real auth logic.
    """
    raise HTTPException(status_code=401, detail="Not authenticated")


def require_plan(plan: str) -> Callable:
    """Return a FastAPI dependency that verifies the user's subscription plan."""

    async def _check(
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
    ) -> int:
        stmt = select(User.subscription_plan).where(User.id == user_id)
        result = await db.execute(stmt)
        current_plan = result.scalar_one_or_none()
        if current_plan != plan:
            raise HTTPException(
                status_code=403,
                detail=f"Upgrade to {plan} plan required",
            )
        return user_id

    return _check
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_deps.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add api/src/margin_api/deps.py api/tests/test_deps.py
git commit -m "feat: add require_plan dependency for subscription gating"
```

---

### Task 7: Create billing service (Stripe integration)

**Files:**
- Create: `api/src/margin_api/services/billing.py`
- Test: `api/tests/test_billing_service.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_billing_service.py`:

```python
"""Tests for BillingService — Stripe Checkout, portal, webhooks."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.services.billing import BillingService


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def user(db):
    u = User(email="a@b.com", name="A", provider="google")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
def service():
    return BillingService(
        stripe_secret_key="sk_test_fake",
        stripe_price_id="price_test_123",
        stripe_webhook_secret="whsec_fake",
    )


class TestCreateCheckoutSession:
    @pytest.mark.asyncio
    async def test_creates_checkout_and_sets_customer(self, db, user, service):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session_123"

        mock_customer = MagicMock()
        mock_customer.id = "cus_new_123"

        with patch.object(service, "_stripe") as mock_stripe:
            mock_stripe.v1.customers.create.return_value = mock_customer
            mock_stripe.v1.checkout.sessions.create.return_value = mock_session

            url = await service.create_checkout_session(
                db,
                user_id=user.id,
                success_url="http://localhost:3000/settings?subscription=active",
                cancel_url="http://localhost:3000/settings",
            )

        assert url == "https://checkout.stripe.com/session_123"
        await db.refresh(user)
        assert user.stripe_customer_id == "cus_new_123"

    @pytest.mark.asyncio
    async def test_reuses_existing_customer(self, db, user, service):
        user.stripe_customer_id = "cus_existing"
        await db.commit()

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session_456"

        with patch.object(service, "_stripe") as mock_stripe:
            mock_stripe.v1.checkout.sessions.create.return_value = mock_session

            url = await service.create_checkout_session(
                db,
                user_id=user.id,
                success_url="http://localhost:3000/settings",
                cancel_url="http://localhost:3000/settings",
            )

        # Should NOT create a new customer
        mock_stripe.v1.customers.create.assert_not_called()
        assert url == "https://checkout.stripe.com/session_456"


class TestHandleSubscriptionCreated:
    @pytest.mark.asyncio
    async def test_sets_plan_and_subscription_id(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="active",
        )

        await db.refresh(user)
        assert user.subscription_plan == "margin_invest"
        assert user.stripe_subscription_id == "sub_abc"


class TestHandleSubscriptionDeleted:
    @pytest.mark.asyncio
    async def test_downgrades_to_free(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        user.subscription_plan = "margin_invest"
        user.stripe_subscription_id = "sub_abc"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="canceled",
        )

        await db.refresh(user)
        assert user.subscription_plan == "free"
        assert user.stripe_subscription_id is None


class TestHandleSubscriptionPastDue:
    @pytest.mark.asyncio
    async def test_past_due_downgrades(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        user.subscription_plan = "margin_invest"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="past_due",
        )

        await db.refresh(user)
        assert user.subscription_plan == "free"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_billing_service.py -v`
Expected: FAIL — `margin_api.services.billing` does not exist.

**Step 3: Implement BillingService**

Create `api/src/margin_api/services/billing.py`:

```python
"""Billing service — wraps Stripe SDK for subscription management."""

from __future__ import annotations

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User

# Statuses that grant access to the paid plan
_ACTIVE_STATUSES = {"active", "trialing"}


class BillingService:
    """Manages Stripe Checkout, Customer Portal, and subscription state."""

    def __init__(
        self,
        stripe_secret_key: str,
        stripe_price_id: str,
        stripe_webhook_secret: str,
    ) -> None:
        self._stripe = stripe.StripeClient(api_key=stripe_secret_key)
        self._price_id = stripe_price_id
        self._webhook_secret = stripe_webhook_secret

    async def create_checkout_session(
        self,
        session: AsyncSession,
        user_id: int,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout Session for the Margin Invest subscription.

        Returns the checkout URL.
        """
        user = await self._get_user(session, user_id)

        # Create Stripe customer if needed
        if not user.stripe_customer_id:
            customer = self._stripe.v1.customers.create(
                params={
                    "email": user.email,
                    "name": user.name,
                    "metadata": {"user_id": str(user.id)},
                }
            )
            user.stripe_customer_id = customer.id
            await session.commit()

        checkout = self._stripe.v1.checkout.sessions.create(
            params={
                "customer": user.stripe_customer_id,
                "mode": "subscription",
                "line_items": [{"price": self._price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
        )
        return checkout.url

    async def create_portal_session(
        self,
        session: AsyncSession,
        user_id: int,
        return_url: str,
    ) -> str:
        """Create a Stripe Customer Portal session. Returns the portal URL."""
        user = await self._get_user(session, user_id)
        if not user.stripe_customer_id:
            raise ValueError("User has no Stripe customer ID")

        portal = self._stripe.v1.billing_portal.sessions.create(
            params={
                "customer": user.stripe_customer_id,
                "return_url": return_url,
            }
        )
        return portal.url

    def construct_webhook_event(self, payload: bytes, signature: str) -> stripe.Event:
        """Verify and construct a Stripe webhook event."""
        return stripe.Webhook.construct_event(
            payload.decode("utf-8"),
            signature,
            self._webhook_secret,
        )

    async def handle_subscription_change(
        self,
        session: AsyncSession,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        status: str,
    ) -> None:
        """Update user's subscription plan based on Stripe subscription status."""
        stmt = select(User).where(User.stripe_customer_id == stripe_customer_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return

        if status in _ACTIVE_STATUSES:
            user.subscription_plan = "margin_invest"
            user.stripe_subscription_id = stripe_subscription_id
        else:
            user.subscription_plan = "free"
            user.stripe_subscription_id = None

        await session.commit()

    async def _get_user(self, session: AsyncSession, user_id: int) -> User:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"User {user_id} not found")
        return user
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_billing_service.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add api/src/margin_api/services/billing.py api/tests/test_billing_service.py
git commit -m "feat: add BillingService with Stripe Checkout, portal, and subscription handling"
```

---

### Task 8: Create billing routes

**Files:**
- Create: `api/src/margin_api/routes/billing.py`
- Modify: `api/src/margin_api/routes/__init__.py`
- Modify: `api/src/margin_api/app.py`
- Test: `api/tests/test_billing_routes.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_billing_routes.py`:

```python
"""Tests for billing API routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id

_TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest_asyncio.fixture()
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        user = User(email="a@b.com", name="A", provider="google")
        session.add(user)
        await session.commit()
        await session.refresh(user)
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
            stripe_price_id="price_test_123",
            stripe_webhook_secret="whsec_fake",
        )

    from margin_api.config import get_settings
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    yield app, user_id
    await engine.dispose()


class TestCheckout:
    @pytest.mark.asyncio
    async def test_checkout_returns_url(self, setup):
        app, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("margin_api.services.billing.stripe.StripeClient") as MockClient:
                mock_stripe = MockClient.return_value
                mock_customer = MagicMock()
                mock_customer.id = "cus_123"
                mock_stripe.v1.customers.create.return_value = mock_customer
                mock_session = MagicMock()
                mock_session.url = "https://checkout.stripe.com/s/123"
                mock_stripe.v1.checkout.sessions.create.return_value = mock_session

                resp = await client.post("/api/v1/billing/checkout")

        assert resp.status_code == 200
        assert resp.json()["checkout_url"] == "https://checkout.stripe.com/s/123"


class TestBillingStatus:
    @pytest.mark.asyncio
    async def test_status_returns_free_by_default(self, setup):
        app, _ = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/billing/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["subscription_plan"] == "free"
        assert data["is_active"] is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_billing_routes.py -v`
Expected: FAIL — no `/api/v1/billing` routes registered.

**Step 3: Implement billing routes**

Create `api/src/margin_api/routes/billing.py`:

```python
"""Billing API routes — Stripe Checkout, portal, webhooks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import SignatureVerificationError

from margin_api.config import get_settings
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.schemas.billing import BillingStatusResponse, CheckoutResponse, PortalResponse
from margin_api.services.billing import BillingService

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


def _get_billing_service() -> BillingService:
    settings = get_settings()
    return BillingService(
        stripe_secret_key=settings.stripe_secret_key,
        stripe_price_id=settings.stripe_price_id,
        stripe_webhook_secret=settings.stripe_webhook_secret,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    billing: BillingService = Depends(_get_billing_service),
) -> CheckoutResponse:
    """Create a Stripe Checkout Session for the Margin Invest subscription."""
    settings = get_settings()
    origin = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    url = await billing.create_checkout_session(
        db,
        user_id=user_id,
        success_url=f"{origin}/settings?subscription=active",
        cancel_url=f"{origin}/settings",
    )
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    billing: BillingService = Depends(_get_billing_service),
) -> PortalResponse:
    """Create a Stripe Customer Portal session for subscription management."""
    settings = get_settings()
    origin = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    try:
        url = await billing.create_portal_session(
            db, user_id=user_id, return_url=f"{origin}/settings"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PortalResponse(portal_url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    billing: BillingService = Depends(_get_billing_service),
) -> dict:
    """Receive and process Stripe webhook events."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        event = billing.construct_webhook_event(payload, signature)
    except (ValueError, SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event.type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        subscription = event.data.object
        await billing.handle_subscription_change(
            db,
            stripe_customer_id=subscription.customer,
            stripe_subscription_id=subscription.id,
            status=subscription.status,
        )

    return {"received": True}


@router.get("/status", response_model=BillingStatusResponse)
async def billing_status(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> BillingStatusResponse:
    """Return the current subscription plan and status."""
    from sqlalchemy import select
    from margin_api.db.models import User

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return BillingStatusResponse(
        subscription_plan=user.subscription_plan,
        stripe_subscription_id=user.stripe_subscription_id,
        is_active=user.subscription_plan == "margin_invest",
    )
```

Update `api/src/margin_api/routes/__init__.py` — add billing router import:

```python
from margin_api.routes.billing import router as billing_router
```

Add `"billing_router"` to `__all__`.

Update `api/src/margin_api/app.py` — add after the auth_router import:

```python
from margin_api.routes.billing import router as billing_router
```

Add `app.include_router(billing_router)` after the auth_router inclusion.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_billing_routes.py -v`
Expected: PASS (2 tests)

**Step 5: Run all tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass.

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/billing.py api/src/margin_api/routes/__init__.py api/src/margin_api/app.py api/tests/test_billing_routes.py
git commit -m "feat: add billing routes — checkout, portal, webhook, status"
```

---

### Task 9: Create API key management routes

**Files:**
- Create: `api/src/margin_api/routes/keys.py`
- Modify: `api/src/margin_api/routes/__init__.py`
- Modify: `api/src/margin_api/app.py`
- Test: `api/tests/test_key_routes.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_key_routes.py`:

```python
"""Tests for API key management routes."""

from __future__ import annotations

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id

_TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest_asyncio.fixture()
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        paid_user = User(
            email="paid@test.com",
            name="Paid",
            provider="google",
            subscription_plan="margin_invest",
        )
        free_user = User(email="free@test.com", name="Free", provider="google")
        session.add_all([paid_user, free_user])
        await session.commit()
        await session.refresh(paid_user)
        await session.refresh(free_user)
        paid_id = paid_user.id
        free_id = free_user.id

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
            stripe_price_id="price_test_123",
            stripe_webhook_secret="whsec_fake",
        )

    from margin_api.config import get_settings
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings

    yield app, paid_id, free_id
    await engine.dispose()


class TestPlanGating:
    @pytest.mark.asyncio
    async def test_free_user_cannot_list_keys(self, setup):
        app, _, free_id = setup
        app.dependency_overrides[get_current_user_id] = lambda: free_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/keys/")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_paid_user_can_list_keys(self, setup):
        app, paid_id, _ = setup
        app.dependency_overrides[get_current_user_id] = lambda: paid_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/keys/")
        assert resp.status_code == 200
        assert resp.json()["keys"] == []


class TestSaveKey:
    @pytest.mark.asyncio
    async def test_save_and_list_key(self, setup):
        app, paid_id, _ = setup
        app.dependency_overrides[get_current_user_id] = lambda: paid_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/keys/",
                json={"provider_name": "fmp", "api_key": "sk_live_fmp_abc123"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["provider_name"] == "fmp"
            assert "abc123" in data["masked_key"]  # Last 6 chars visible
            assert data["is_platform_managed"] is False

            # List should include it
            list_resp = await client.get("/api/v1/keys/")
            assert len(list_resp.json()["keys"]) == 1


class TestDeleteKey:
    @pytest.mark.asyncio
    async def test_delete_key(self, setup):
        app, paid_id, _ = setup
        app.dependency_overrides[get_current_user_id] = lambda: paid_id
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                "/api/v1/keys/",
                json={"provider_name": "fmp", "api_key": "sk_live_fmp_abc123"},
            )
            resp = await client.delete("/api/v1/keys/fmp")
            assert resp.status_code == 200

            list_resp = await client.get("/api/v1/keys/")
            assert len(list_resp.json()["keys"]) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_key_routes.py -v`
Expected: FAIL — no `/api/v1/keys` routes.

**Step 3: Implement key routes**

Create `api/src/margin_api/routes/keys.py`:

```python
"""API key management routes — CRUD for provider API keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id, require_plan
from margin_api.schemas.keys import ApiKeyListResponse, ApiKeyResponse, SaveKeyRequest
from margin_api.services.api_keys import ApiKeyService

router = APIRouter(prefix="/api/v1/keys", tags=["keys"])


def _get_api_key_service() -> ApiKeyService:
    settings = get_settings()
    return ApiKeyService(encryption_key=settings.api_key_encryption_key.encode())


def _mask_key(encrypted_key: str, service: ApiKeyService) -> str:
    """Decrypt a key and return a masked version showing only last 6 chars."""
    plaintext = service.decrypt(encrypted_key)
    if len(plaintext) <= 6:
        return "***"
    return f"{'*' * (len(plaintext) - 6)}{plaintext[-6:]}"


@router.get("/", response_model=ApiKeyListResponse)
async def list_keys(
    _user_id: int = Depends(require_plan("margin_invest")),
    db: AsyncSession = Depends(get_db),
    service: ApiKeyService = Depends(_get_api_key_service),
) -> ApiKeyListResponse:
    """List all active API keys for the current user (masked)."""
    keys = await service.list_active_keys(db, _user_id)
    return ApiKeyListResponse(
        keys=[
            ApiKeyResponse(
                id=k.id,
                provider_name=k.provider_name,
                masked_key=_mask_key(k.encrypted_key, service),
                is_platform_managed=k.is_platform_managed,
                created_at=k.created_at,
            )
            for k in keys
        ]
    )


@router.post("/", response_model=ApiKeyResponse, status_code=201)
async def save_key(
    body: SaveKeyRequest,
    _user_id: int = Depends(require_plan("margin_invest")),
    db: AsyncSession = Depends(get_db),
    service: ApiKeyService = Depends(_get_api_key_service),
) -> ApiKeyResponse:
    """Save (or replace) an API key for a provider."""
    key = await service.save_key(
        session=db,
        user_id=_user_id,
        provider_name=body.provider_name,
        plaintext_key=body.api_key,
        is_platform_managed=False,
    )
    return ApiKeyResponse(
        id=key.id,
        provider_name=key.provider_name,
        masked_key=_mask_key(key.encrypted_key, service),
        is_platform_managed=key.is_platform_managed,
        created_at=key.created_at,
    )


@router.delete("/{provider_name}")
async def delete_key(
    provider_name: str,
    _user_id: int = Depends(require_plan("margin_invest")),
    db: AsyncSession = Depends(get_db),
    service: ApiKeyService = Depends(_get_api_key_service),
) -> dict:
    """Revoke the active key for a provider."""
    revoked = await service.revoke_key(db, _user_id, provider_name)
    if not revoked:
        raise HTTPException(status_code=404, detail="No active key found for this provider")
    return {"revoked": True}
```

Update `api/src/margin_api/routes/__init__.py` — add import:

```python
from margin_api.routes.keys import router as keys_router
```

Add `"keys_router"` to `__all__`.

Update `api/src/margin_api/app.py` — add import and include:

```python
from margin_api.routes.keys import router as keys_router
```

Add `app.include_router(keys_router)` after the billing_router inclusion.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_key_routes.py -v`
Expected: PASS (4 tests)

**Step 5: Run all tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass.

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/keys.py api/src/margin_api/routes/__init__.py api/src/margin_api/app.py api/tests/test_key_routes.py
git commit -m "feat: add API key CRUD routes gated by subscription plan"
```

---

### Task 10: Add key rotation ARQ worker task

**Files:**
- Modify: `api/src/margin_api/worker.py`
- Test: `api/tests/test_key_rotation.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_key_rotation.py`:

```python
"""Tests for platform API key rotation worker task."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import ApiKey, ApiKeyEvent, User
from margin_api.services.api_keys import ApiKeyService
from margin_api.worker import rotate_platform_keys

_TEST_KEY = Fernet.generate_key()


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def user(db):
    u = User(email="a@b.com", name="A", provider="google", subscription_plan="margin_invest")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest.fixture
def service():
    return ApiKeyService(encryption_key=_TEST_KEY)


class TestRotatePlatformKeys:
    @pytest.mark.asyncio
    async def test_rotates_old_platform_key(self, db, user, service):
        """Keys older than 90 days get an expires_at set and a new key created."""
        old_key = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key=service.encrypt("old_fmp_key"),
            is_platform_managed=True,
            created_at=datetime.now(UTC) - timedelta(days=91),
        )
        db.add(old_key)
        await db.commit()
        await db.refresh(old_key)

        rotated = await rotate_platform_keys(session=db, service=service)
        assert rotated == 1

        await db.refresh(old_key)
        assert old_key.expires_at is not None  # Overlap window set

        # New key should exist
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.user_id == user.id,
                ApiKey.provider_name == "fmp",
                ApiKey.revoked_at.is_(None),
                ApiKey.id != old_key.id,
            )
        )
        new_key = result.scalar_one_or_none()
        assert new_key is not None
        assert new_key.is_platform_managed is True

    @pytest.mark.asyncio
    async def test_skips_recent_keys(self, db, user, service):
        """Keys less than 90 days old should NOT be rotated."""
        recent_key = ApiKey(
            user_id=user.id,
            provider_name="polygon",
            encrypted_key=service.encrypt("pg_key"),
            is_platform_managed=True,
            created_at=datetime.now(UTC) - timedelta(days=30),
        )
        db.add(recent_key)
        await db.commit()

        rotated = await rotate_platform_keys(session=db, service=service)
        assert rotated == 0

    @pytest.mark.asyncio
    async def test_skips_user_provided_keys(self, db, user, service):
        """BYOK keys should never be rotated."""
        byok = ApiKey(
            user_id=user.id,
            provider_name="fmp",
            encrypted_key=service.encrypt("user_key"),
            is_platform_managed=False,
            created_at=datetime.now(UTC) - timedelta(days=200),
        )
        db.add(byok)
        await db.commit()

        rotated = await rotate_platform_keys(session=db, service=service)
        assert rotated == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_key_rotation.py -v`
Expected: FAIL — `rotate_platform_keys` does not exist in `worker.py`.

**Step 3: Add rotation function to worker.py**

Add to `api/src/margin_api/worker.py`, after the existing imports add:

```python
from margin_api.db.models import ApiKey, ApiKeyEvent
from margin_api.services.api_keys import ApiKeyService
```

Add the following function before `class WorkerSettings`:

```python
_ROTATION_AGE_DAYS = 90
_OVERLAP_HOURS = 24


async def rotate_platform_keys(
    *,
    session: AsyncSession,
    service: ApiKeyService,
) -> int:
    """Rotate platform-managed API keys older than 90 days.

    Sets expires_at on the old key (24-hour overlap window) and creates
    a new key with the same plaintext value. Returns count of rotated keys.
    """
    cutoff = datetime.now(UTC) - timedelta(days=_ROTATION_AGE_DAYS)
    stmt = select(ApiKey).where(
        ApiKey.is_platform_managed.is_(True),
        ApiKey.revoked_at.is_(None),
        ApiKey.expires_at.is_(None),
        ApiKey.created_at < cutoff,
    )
    result = await session.execute(stmt)
    old_keys = list(result.scalars().all())

    rotated = 0
    for old_key in old_keys:
        # Set overlap window on old key
        old_key.expires_at = datetime.now(UTC) + timedelta(hours=_OVERLAP_HOURS)
        session.add(
            ApiKeyEvent(api_key_id=old_key.id, event_type="rotated")
        )

        # Create new key with same plaintext
        plaintext = service.decrypt(old_key.encrypted_key)
        new_key = ApiKey(
            user_id=old_key.user_id,
            provider_name=old_key.provider_name,
            encrypted_key=service.encrypt(plaintext),
            is_platform_managed=True,
        )
        session.add(new_key)
        rotated += 1

    if rotated:
        await session.commit()

    return rotated
```

Also add `from datetime import timedelta` to the imports at the top if not already present.

Add `rotate_platform_keys` to the ARQ `WorkerSettings.functions` list.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_key_rotation.py -v`
Expected: PASS (3 tests)

**Step 5: Run all tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass.

**Step 6: Commit**

```bash
git add api/src/margin_api/worker.py api/tests/test_key_rotation.py
git commit -m "feat: add platform API key rotation worker task (90-day cycle, 24h overlap)"
```

---

### Task 11: Create Alembic migration

**Files:**
- Generate new migration in `api/alembic/versions/`

**Step 1: Generate the migration**

```bash
cd /Users/brandon/repos/margin_invest && uv run alembic -c api/alembic.ini revision --autogenerate -m "add subscription fields and api key event table"
```

**Step 2: Review the generated migration**

Read the generated file and verify it includes:
- `stripe_customer_id`, `stripe_subscription_id`, `subscription_plan` columns added to `users` table
- Same three columns added to `credential_users` table
- `is_platform_managed`, `expires_at`, `revoked_at` columns added to `api_keys` table
- `uq_user_provider` unique constraint dropped from `api_keys`
- `api_key_events` table created

**Step 3: Run the migration**

```bash
uv run alembic -c api/alembic.ini upgrade head
```

**Step 4: Commit**

```bash
git add api/alembic/versions/
git commit -m "migration: add subscription fields, api key event table, update api keys"
```

---

### Task 12: Update frontend API keys section with subscription gating

**Files:**
- Modify: `web/src/components/settings/api-keys-section.tsx`
- Test: `web/src/components/settings/__tests__/api-keys-section.test.tsx` (create)

**Step 1: Write the failing test**

Create `web/src/components/settings/__tests__/api-keys-section.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ApiKeysSection } from "../api-keys-section"

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe("ApiKeysSection", () => {
  it("shows upgrade CTA when subscription is free", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ subscription_plan: "free", is_active: false }),
    })

    render(<ApiKeysSection />)
    expect(await screen.findByText(/upgrade/i)).toBeInTheDocument()
  })

  it("shows key management when subscription is active", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ subscription_plan: "margin_invest", is_active: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ keys: [] }),
      })

    render(<ApiKeysSection />)
    expect(await screen.findByText(/API Keys/i)).toBeInTheDocument()
    expect(screen.queryByText(/upgrade/i)).not.toBeInTheDocument()
  })

  it("renders existing keys as masked", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ subscription_plan: "margin_invest", is_active: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            keys: [
              {
                id: 1,
                provider_name: "fmp",
                masked_key: "****abc123",
                is_platform_managed: false,
                created_at: "2026-01-01T00:00:00Z",
              },
            ],
          }),
      })

    render(<ApiKeysSection />)
    expect(await screen.findByText("****abc123")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/settings/__tests__/api-keys-section.test.tsx`
Expected: FAIL — component doesn't fetch billing status.

**Step 3: Rewrite api-keys-section.tsx**

Rewrite `web/src/components/settings/api-keys-section.tsx` to:
1. Fetch billing status on mount (`GET /api/v1/billing/status`)
2. If `subscription_plan === "free"`, show upgrade CTA with link to checkout
3. If `subscription_plan === "margin_invest"`, fetch and display keys (`GET /api/v1/keys/`)
4. Wire up save/delete to `POST /api/v1/keys/` and `DELETE /api/v1/keys/{provider}`

```tsx
"use client"

import { useEffect, useState } from "react"

const providers = [
  { id: "fmp", name: "Financial Modeling Prep", description: "Fundamentals, pre-computed ratios" },
  { id: "polygon", name: "Polygon.io", description: "Superior price data" },
  { id: "finnhub", name: "Finnhub", description: "News, earnings, insider data" },
  { id: "fred", name: "FRED", description: "Macro economic indicators" },
]

interface ApiKeyData {
  id: number
  provider_name: string
  masked_key: string
  is_platform_managed: boolean
  created_at: string
}

export function ApiKeysSection() {
  const [plan, setPlan] = useState<string | null>(null)
  const [keys, setKeys] = useState<ApiKeyData[]>([])
  const [inputKeys, setInputKeys] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})

  useEffect(() => {
    fetch("/api/v1/billing/status")
      .then((r) => r.json())
      .then((data) => {
        setPlan(data.subscription_plan)
        if (data.is_active) {
          fetch("/api/v1/keys/")
            .then((r) => r.json())
            .then((d) => setKeys(d.keys))
        }
      })
  }, [])

  const handleUpgrade = async () => {
    const resp = await fetch("/api/v1/billing/checkout", { method: "POST" })
    const data = await resp.json()
    window.location.href = data.checkout_url
  }

  const handleSave = async (providerId: string) => {
    const value = inputKeys[providerId]
    if (!value) return
    setSaving((prev) => ({ ...prev, [providerId]: true }))
    const resp = await fetch("/api/v1/keys/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider_name: providerId, api_key: value }),
    })
    if (resp.ok) {
      const saved = await resp.json()
      setKeys((prev) => [
        ...prev.filter((k) => k.provider_name !== providerId),
        saved,
      ])
      setInputKeys((prev) => ({ ...prev, [providerId]: "" }))
    }
    setSaving((prev) => ({ ...prev, [providerId]: false }))
  }

  const handleDelete = async (providerId: string) => {
    await fetch(`/api/v1/keys/${providerId}`, { method: "DELETE" })
    setKeys((prev) => prev.filter((k) => k.provider_name !== providerId))
  }

  if (plan === null) return null

  if (plan === "free") {
    return (
      <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
        <h2 className="text-lg font-bold text-text-primary mb-2">API Keys</h2>
        <p className="text-sm text-text-secondary mb-4">
          Upgrade to Margin Invest to unlock premium data providers.
        </p>
        <button
          onClick={handleUpgrade}
          className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors"
        >
          Upgrade to Margin Invest
        </button>
      </section>
    )
  }

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-2">API Keys</h2>
      <p className="text-sm text-text-secondary mb-6">
        Add provider API keys to unlock premium data sources. Keys are encrypted at rest.
      </p>
      <div className="space-y-4">
        {providers.map((provider) => {
          const existingKey = keys.find((k) => k.provider_name === provider.id)
          return (
            <div
              key={provider.id}
              className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 bg-bg-primary rounded-sm border border-border-primary"
            >
              <div className="flex-1">
                <div className="text-text-primary font-medium">{provider.name}</div>
                <div className="text-xs text-text-secondary">{provider.description}</div>
                {existingKey && (
                  <div className="text-xs text-text-tertiary mt-1 font-mono">
                    {existingKey.masked_key}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                {existingKey ? (
                  <button
                    onClick={() => handleDelete(provider.id)}
                    className="px-3 py-2 text-danger text-sm font-medium hover:bg-danger/10 rounded-sm transition-colors"
                  >
                    Revoke
                  </button>
                ) : (
                  <>
                    <input
                      type="password"
                      placeholder="Enter API key"
                      value={inputKeys[provider.id] || ""}
                      onChange={(e) =>
                        setInputKeys((prev) => ({ ...prev, [provider.id]: e.target.value }))
                      }
                      className="px-3 py-2 bg-bg-elevated border border-border-primary rounded-sm text-sm text-text-primary placeholder-text-secondary focus:border-accent focus:outline-none w-48"
                    />
                    <button
                      onClick={() => handleSave(provider.id)}
                      disabled={!inputKeys[provider.id] || saving[provider.id]}
                      className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {saving[provider.id] ? "Saving..." : "Save"}
                    </button>
                  </>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/settings/__tests__/api-keys-section.test.tsx`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add web/src/components/settings/api-keys-section.tsx web/src/components/settings/__tests__/api-keys-section.test.tsx
git commit -m "feat: rewrite API keys section with subscription gating and backend integration"
```

---

### Task 13: Add billing section to settings page

**Files:**
- Create: `web/src/components/settings/billing-section.tsx`
- Modify: `web/src/app/settings/page.tsx`
- Test: `web/src/components/settings/__tests__/billing-section.test.tsx` (create)

**Step 1: Write the failing test**

Create `web/src/components/settings/__tests__/billing-section.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { BillingSection } from "../billing-section"

const mockFetch = vi.fn()
global.fetch = mockFetch

describe("BillingSection", () => {
  it("shows free plan with upgrade button", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ subscription_plan: "free", is_active: false }),
    })
    render(<BillingSection />)
    expect(await screen.findByText(/Free/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /upgrade/i })).toBeInTheDocument()
  })

  it("shows active plan with manage button", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          subscription_plan: "margin_invest",
          is_active: true,
          stripe_subscription_id: "sub_123",
        }),
    })
    render(<BillingSection />)
    expect(await screen.findByText(/Margin Invest/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /manage/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/settings/__tests__/billing-section.test.tsx`
Expected: FAIL — `billing-section` does not exist.

**Step 3: Create BillingSection component**

Create `web/src/components/settings/billing-section.tsx`:

```tsx
"use client"

import { useEffect, useState } from "react"

interface BillingStatus {
  subscription_plan: string
  stripe_subscription_id: string | null
  is_active: boolean
}

export function BillingSection() {
  const [status, setStatus] = useState<BillingStatus | null>(null)

  useEffect(() => {
    fetch("/api/v1/billing/status")
      .then((r) => r.json())
      .then(setStatus)
  }, [])

  const handleUpgrade = async () => {
    const resp = await fetch("/api/v1/billing/checkout", { method: "POST" })
    const data = await resp.json()
    window.location.href = data.checkout_url
  }

  const handleManage = async () => {
    const resp = await fetch("/api/v1/billing/portal", { method: "POST" })
    const data = await resp.json()
    window.location.href = data.portal_url
  }

  if (!status) return null

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-2">Billing</h2>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-text-primary font-medium">
            {status.is_active ? "Margin Invest" : "Free"}
          </div>
          <div className="text-sm text-text-secondary">
            {status.is_active
              ? "Premium data providers and priority scoring"
              : "Basic scoring with yfinance data"}
          </div>
        </div>
        {status.is_active ? (
          <button
            onClick={handleManage}
            className="px-4 py-2 border border-border-primary text-text-primary font-medium text-sm rounded-sm hover:bg-bg-subtle transition-colors"
          >
            Manage subscription
          </button>
        ) : (
          <button
            onClick={handleUpgrade}
            className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors"
          >
            Upgrade
          </button>
        )}
      </div>
    </section>
  )
}
```

Update `web/src/app/settings/page.tsx` — add `BillingSection` import and render it between `AccountSection` and `ApiKeysSection`:

```tsx
import { BillingSection } from "@/components/settings/billing-section"
```

```tsx
<div className="space-y-8">
  <AccountSection />
  <BillingSection />
  <ApiKeysSection />
</div>
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/settings/__tests__/billing-section.test.tsx`
Expected: PASS (2 tests)

**Step 5: Run all frontend tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All pass.

**Step 6: Commit**

```bash
git add web/src/components/settings/billing-section.tsx web/src/components/settings/__tests__/billing-section.test.tsx web/src/app/settings/page.tsx
git commit -m "feat: add billing section to settings page with Stripe portal integration"
```

---

### Task 14: Run full test suite and verify

**Step 1: Run all API tests**

```bash
uv run pytest api/tests/ -v
```

Expected: All tests pass (existing + ~30 new tests).

**Step 2: Run all frontend tests**

```bash
cd /Users/brandon/repos/margin_invest/web && npx vitest run
```

Expected: All tests pass.

**Step 3: Run engine tests (regression check)**

```bash
uv run pytest engine/tests/ -v
```

Expected: All 784 engine tests still pass (no engine changes).

**Step 4: Verify no lint issues**

```bash
uv run ruff check api/src/ api/tests/
```

**Step 5: Commit any final fixes if needed**

If any tests or lint issues found, fix and commit individually.
