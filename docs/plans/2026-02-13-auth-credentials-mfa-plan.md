# Auth Credentials + MFA Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Microsoft/Facebook OAuth with a CredentialsProvider (username/password) and enforce mandatory TOTP + WebAuthn MFA for all credentials-based users.

**Architecture:** Auth.js CredentialsProvider calls FastAPI backend for password verification (Argon2id) and MFA status. The `signIn` callback gates login — no session is created until MFA is completed. New API endpoints handle registration, TOTP enrollment/verification, and WebAuthn registration/authentication. New frontend pages handle registration, MFA setup, and MFA verification.

**Tech Stack:** Auth.js v5 (CredentialsProvider), FastAPI, SQLAlchemy (async), Argon2id (argon2-cffi), pyotp + cryptography (TOTP), py_webauthn (WebAuthn server), @simplewebauthn/browser (WebAuthn client), otpauth + qrcode.react (TOTP QR).

---

### Task 1: Add Python Auth Dependencies

**Files:**
- Modify: `api/pyproject.toml`

**Step 1: Add auth dependencies to api/pyproject.toml**

Add to the `dependencies` list in `api/pyproject.toml`:

```toml
dependencies = [
    "margin-engine",
    "fastapi>=0.115",
    "uvicorn>=0.34",
    "pydantic-settings>=2.12.0",
    "sqlalchemy>=2.0.46",
    "argon2-cffi>=23.1.0",
    "pyotp>=2.9.0",
    "cryptography>=44.0.0",
    "py_webauthn>=2.5.0",
]
```

**Step 2: Sync dependencies**

Run: `uv sync`
Expected: All packages install successfully.

**Step 3: Commit**

```bash
git add api/pyproject.toml uv.lock
git commit -m "chore: add auth dependencies (argon2, pyotp, py_webauthn)"
```

---

### Task 2: Add Auth Database Models

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Modify: `api/src/margin_api/db/__init__.py`
- Create: `api/tests/test_auth_models.py`

**Step 1: Write the failing test**

Create `api/tests/test_auth_models.py`:

```python
"""Tests for auth-related database models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import (
    CredentialUser,
    MfaChallengeToken,
    TotpSecret,
    WebAuthnCredential,
)


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_credential_user_creation(async_session: AsyncSession):
    user = CredentialUser(
        username="alice",
        email="alice@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        mfa_enabled=False,
    )
    async_session.add(user)
    await async_session.commit()

    result = await async_session.execute(select(CredentialUser).where(CredentialUser.username == "alice"))
    fetched = result.scalar_one()
    assert fetched.email == "alice@example.com"
    assert fetched.mfa_enabled is False
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_credential_user_username_unique(async_session: AsyncSession):
    user1 = CredentialUser(username="alice", email="a1@example.com", password_hash="hash1")
    user2 = CredentialUser(username="alice", email="a2@example.com", password_hash="hash2")
    async_session.add(user1)
    await async_session.commit()
    async_session.add(user2)
    with pytest.raises(Exception):
        await async_session.commit()


@pytest.mark.asyncio
async def test_totp_secret_creation(async_session: AsyncSession):
    user = CredentialUser(username="bob", email="bob@example.com", password_hash="hash")
    async_session.add(user)
    await async_session.commit()

    secret = TotpSecret(
        user_id=user.id,
        encrypted_secret="fernet-encrypted-base32-secret",
        confirmed=False,
    )
    async_session.add(secret)
    await async_session.commit()

    result = await async_session.execute(select(TotpSecret).where(TotpSecret.user_id == user.id))
    fetched = result.scalar_one()
    assert fetched.confirmed is False
    assert fetched.encrypted_secret == "fernet-encrypted-base32-secret"


@pytest.mark.asyncio
async def test_webauthn_credential_creation(async_session: AsyncSession):
    user = CredentialUser(username="carol", email="carol@example.com", password_hash="hash")
    async_session.add(user)
    await async_session.commit()

    cred = WebAuthnCredential(
        user_id=user.id,
        credential_id="base64url-credential-id",
        public_key="base64url-public-key",
        sign_count=0,
    )
    async_session.add(cred)
    await async_session.commit()

    result = await async_session.execute(
        select(WebAuthnCredential).where(WebAuthnCredential.user_id == user.id)
    )
    fetched = result.scalar_one()
    assert fetched.sign_count == 0
    assert fetched.credential_id == "base64url-credential-id"


@pytest.mark.asyncio
async def test_mfa_challenge_token_creation(async_session: AsyncSession):
    user = CredentialUser(username="dave", email="dave@example.com", password_hash="hash")
    async_session.add(user)
    await async_session.commit()

    token = MfaChallengeToken(
        user_id=user.id,
        token_hash="sha256-hash-of-token",
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        used=False,
    )
    async_session.add(token)
    await async_session.commit()

    result = await async_session.execute(
        select(MfaChallengeToken).where(MfaChallengeToken.user_id == user.id)
    )
    fetched = result.scalar_one()
    assert fetched.used is False
    assert fetched.token_hash == "sha256-hash-of-token"


@pytest.mark.asyncio
async def test_credential_user_relationships(async_session: AsyncSession):
    user = CredentialUser(username="eve", email="eve@example.com", password_hash="hash")
    async_session.add(user)
    await async_session.commit()

    totp = TotpSecret(user_id=user.id, encrypted_secret="secret", confirmed=True)
    webauthn = WebAuthnCredential(
        user_id=user.id, credential_id="cred", public_key="key", sign_count=0
    )
    async_session.add_all([totp, webauthn])
    await async_session.commit()

    await async_session.refresh(user, ["totp_secrets", "webauthn_credentials"])
    assert len(user.totp_secrets) == 1
    assert len(user.webauthn_credentials) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_auth_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'CredentialUser'`

**Step 3: Write the models**

Add to `api/src/margin_api/db/models.py` (after the existing `ApiKey` class):

```python
class CredentialUser(Base):
    __tablename__ = "credential_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)
    last_totp_counter: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    totp_secrets: Mapped[list[TotpSecret]] = relationship(back_populates="user")
    webauthn_credentials: Mapped[list[WebAuthnCredential]] = relationship(back_populates="user")
    challenge_tokens: Mapped[list[MfaChallengeToken]] = relationship(back_populates="user")


class TotpSecret(Base):
    __tablename__ = "totp_secrets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("credential_users.id"), index=True)
    encrypted_secret: Mapped[str] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    user: Mapped[CredentialUser] = relationship(back_populates="totp_secrets")


class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("credential_users.id"), index=True)
    credential_id: Mapped[str] = mapped_column(Text, unique=True)
    public_key: Mapped[str] = mapped_column(Text)
    sign_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    user: Mapped[CredentialUser] = relationship(back_populates="webauthn_credentials")


class MfaChallengeToken(Base):
    __tablename__ = "mfa_challenge_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("credential_users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime]
    used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    user: Mapped[CredentialUser] = relationship(back_populates="challenge_tokens")
```

**Step 4: Update `api/src/margin_api/db/__init__.py`**

Add the new model imports:

```python
from margin_api.db.models import (
    ApiKey, Asset, CredentialUser, MfaChallengeToken, Recommendation,
    Score, TotpSecret, User, WebAuthnCredential,
)

__all__ = [
    "ApiKey",
    "Asset",
    "Base",
    "CredentialUser",
    "MfaChallengeToken",
    "Recommendation",
    "Score",
    "TotpSecret",
    "User",
    "WebAuthnCredential",
    "get_db",
    "get_engine",
    "get_session_factory",
]
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest api/tests/test_auth_models.py -v`
Expected: All 6 tests PASS.

**Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/src/margin_api/db/__init__.py api/tests/test_auth_models.py
git commit -m "feat(api): add auth database models (CredentialUser, TOTP, WebAuthn, MFA tokens)"
```

---

### Task 3: Add Auth Service Layer

**Files:**
- Create: `api/src/margin_api/services/__init__.py`
- Create: `api/src/margin_api/services/auth.py`
- Create: `api/tests/test_auth_service.py`

**Step 1: Create services package**

Create empty `api/src/margin_api/services/__init__.py`:

```python
"""Service layer for business logic."""
```

**Step 2: Write the failing tests**

Create `api/tests/test_auth_service.py`:

```python
"""Tests for auth service layer."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import CredentialUser, MfaChallengeToken, TotpSecret
from margin_api.services.auth import AuthService


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def auth_service():
    return AuthService(mfa_encryption_key=b"test-key-must-be-32-bytes-long!!")


# --- Registration ---

@pytest.mark.asyncio
async def test_register_user_success(async_session: AsyncSession, auth_service: AuthService):
    user = await auth_service.register_user(
        async_session, username="alice", email="alice@example.com", password="StrongP@ss1!"
    )
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.password_hash.startswith("$argon2id$")
    assert user.mfa_enabled is False


@pytest.mark.asyncio
async def test_register_duplicate_username(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a1@x.com", "StrongP@ss1!")
    with pytest.raises(ValueError, match="Username already taken"):
        await auth_service.register_user(async_session, "alice", "a2@x.com", "StrongP@ss1!")


@pytest.mark.asyncio
async def test_register_duplicate_email(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "same@x.com", "StrongP@ss1!")
    with pytest.raises(ValueError, match="Email already registered"):
        await auth_service.register_user(async_session, "bob", "same@x.com", "StrongP@ss1!")


@pytest.mark.asyncio
async def test_register_weak_password(async_session: AsyncSession, auth_service: AuthService):
    with pytest.raises(ValueError, match="Password must be"):
        await auth_service.register_user(async_session, "alice", "a@x.com", "short")


# --- Credential verification ---

@pytest.mark.asyncio
async def test_verify_credentials_success(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    result = await auth_service.verify_credentials(async_session, "alice", "StrongP@ss1!")
    assert result is not None
    assert result["username"] == "alice"
    assert result["mfa_status"] == "not_configured"


@pytest.mark.asyncio
async def test_verify_credentials_wrong_password(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    result = await auth_service.verify_credentials(async_session, "alice", "wrong")
    assert result is None


@pytest.mark.asyncio
async def test_verify_credentials_nonexistent_user(async_session: AsyncSession, auth_service: AuthService):
    result = await auth_service.verify_credentials(async_session, "nobody", "pass")
    assert result is None


@pytest.mark.asyncio
async def test_verify_credentials_locked_account(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    # Simulate lockout
    user_result = await async_session.execute(
        select(CredentialUser).where(CredentialUser.username == "alice")
    )
    user = user_result.scalar_one()
    user.failed_login_attempts = 5
    user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
    await async_session.commit()

    result = await auth_service.verify_credentials(async_session, "alice", "StrongP@ss1!")
    assert result is None


@pytest.mark.asyncio
async def test_failed_attempts_increment(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    for _ in range(4):
        await auth_service.verify_credentials(async_session, "alice", "wrong")
    user_result = await async_session.execute(
        select(CredentialUser).where(CredentialUser.username == "alice")
    )
    user = user_result.scalar_one()
    assert user.failed_login_attempts == 4


@pytest.mark.asyncio
async def test_lockout_after_5_failures(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    for _ in range(5):
        await auth_service.verify_credentials(async_session, "alice", "wrong")
    user_result = await async_session.execute(
        select(CredentialUser).where(CredentialUser.username == "alice")
    )
    user = user_result.scalar_one()
    assert user.locked_until is not None
    assert user.failed_login_attempts == 5


@pytest.mark.asyncio
async def test_successful_login_resets_attempts(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    for _ in range(3):
        await auth_service.verify_credentials(async_session, "alice", "wrong")
    result = await auth_service.verify_credentials(async_session, "alice", "StrongP@ss1!")
    assert result is not None
    user_result = await async_session.execute(
        select(CredentialUser).where(CredentialUser.username == "alice")
    )
    user = user_result.scalar_one()
    assert user.failed_login_attempts == 0


# --- Challenge tokens ---

@pytest.mark.asyncio
async def test_create_challenge_token(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    user_result = await async_session.execute(
        select(CredentialUser).where(CredentialUser.username == "alice")
    )
    user = user_result.scalar_one()
    raw_token = await auth_service.create_challenge_token(async_session, user.id)
    assert isinstance(raw_token, str)
    assert len(raw_token) == 64  # 32 bytes hex


@pytest.mark.asyncio
async def test_verify_challenge_token_valid(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    user_result = await async_session.execute(
        select(CredentialUser).where(CredentialUser.username == "alice")
    )
    user = user_result.scalar_one()
    raw_token = await auth_service.create_challenge_token(async_session, user.id)
    result = await auth_service.verify_challenge_token(async_session, user.id, raw_token)
    assert result is True


@pytest.mark.asyncio
async def test_verify_challenge_token_single_use(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    user_result = await async_session.execute(
        select(CredentialUser).where(CredentialUser.username == "alice")
    )
    user = user_result.scalar_one()
    raw_token = await auth_service.create_challenge_token(async_session, user.id)
    await auth_service.verify_challenge_token(async_session, user.id, raw_token)
    result = await auth_service.verify_challenge_token(async_session, user.id, raw_token)
    assert result is False


@pytest.mark.asyncio
async def test_verify_challenge_token_expired(async_session: AsyncSession, auth_service: AuthService):
    await auth_service.register_user(async_session, "alice", "a@x.com", "StrongP@ss1!")
    user_result = await async_session.execute(
        select(CredentialUser).where(CredentialUser.username == "alice")
    )
    user = user_result.scalar_one()
    raw_token = await auth_service.create_challenge_token(async_session, user.id, ttl_minutes=0)
    result = await auth_service.verify_challenge_token(async_session, user.id, raw_token)
    assert result is False
```

**Step 3: Run test to verify it fails**

Run: `uv run pytest api/tests/test_auth_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'AuthService'`

**Step 4: Implement AuthService**

Create `api/src/margin_api/services/auth.py`:

```python
"""Authentication service — password hashing, verification, challenge tokens."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import CredentialUser, MfaChallengeToken

# Argon2id with OWASP-recommended parameters
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{12,}$"
)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class AuthService:
    """Handles user registration, credential verification, and challenge tokens."""

    def __init__(self, mfa_encryption_key: bytes | None = None):
        self._mfa_key = mfa_encryption_key

    async def register_user(
        self,
        session: AsyncSession,
        username: str,
        email: str,
        password: str,
    ) -> CredentialUser:
        """Register a new credential user. Raises ValueError on validation failure."""
        if not _PASSWORD_PATTERN.match(password):
            raise ValueError(
                "Password must be at least 12 characters with uppercase, lowercase, "
                "digit, and special character"
            )

        # Check uniqueness before insert for better error messages
        existing = await session.execute(
            select(CredentialUser).where(CredentialUser.username == username)
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Username already taken")

        existing_email = await session.execute(
            select(CredentialUser).where(CredentialUser.email == email)
        )
        if existing_email.scalar_one_or_none() is not None:
            raise ValueError("Email already registered")

        password_hash = _ph.hash(password)
        user = CredentialUser(
            username=username,
            email=email,
            password_hash=password_hash,
            mfa_enabled=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def verify_credentials(
        self,
        session: AsyncSession,
        username: str,
        password: str,
    ) -> dict | None:
        """Verify username/password. Returns user info + MFA status, or None."""
        result = await session.execute(
            select(CredentialUser).where(CredentialUser.username == username)
        )
        user = result.scalar_one_or_none()
        if user is None:
            # Constant-time: hash the password anyway to prevent timing attacks
            _ph.hash(password)
            return None

        # Check lockout
        if user.locked_until and user.locked_until > datetime.now(UTC):
            return None

        # Verify password
        try:
            _ph.verify(user.password_hash, password)
        except VerifyMismatchError:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_MINUTES)
            await session.commit()
            return None

        # Success: reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        await session.commit()

        mfa_status = "configured" if user.mfa_enabled else "not_configured"
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "mfa_status": mfa_status,
        }

    async def create_challenge_token(
        self,
        session: AsyncSession,
        user_id: int,
        ttl_minutes: int = 5,
    ) -> str:
        """Create a short-lived challenge token proving password was verified."""
        raw_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        challenge = MfaChallengeToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
            used=False,
        )
        session.add(challenge)
        await session.commit()
        return raw_token

    async def verify_challenge_token(
        self,
        session: AsyncSession,
        user_id: int,
        raw_token: str,
    ) -> bool:
        """Verify and consume a challenge token. Single-use."""
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        result = await session.execute(
            select(MfaChallengeToken).where(
                MfaChallengeToken.user_id == user_id,
                MfaChallengeToken.token_hash == token_hash,
                MfaChallengeToken.used == False,  # noqa: E712
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return False

        if token.expires_at < datetime.now(UTC):
            token.used = True
            await session.commit()
            return False

        token.used = True
        await session.commit()
        return True
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest api/tests/test_auth_service.py -v`
Expected: All 16 tests PASS.

**Step 6: Commit**

```bash
git add api/src/margin_api/services/ api/tests/test_auth_service.py
git commit -m "feat(api): add AuthService with registration, verification, and challenge tokens"
```

---

### Task 4: Add TOTP Service

**Files:**
- Create: `api/src/margin_api/services/totp.py`
- Create: `api/tests/test_totp_service.py`

**Step 1: Write the failing tests**

Create `api/tests/test_totp_service.py`:

```python
"""Tests for TOTP MFA service."""

from __future__ import annotations

import pyotp
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import CredentialUser, TotpSecret
from margin_api.services.totp import TotpService


@pytest.fixture
def fernet_key():
    return Fernet.generate_key()


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def test_user(async_session: AsyncSession):
    user = CredentialUser(username="alice", email="alice@x.com", password_hash="hash")
    async_session.add(user)
    await async_session.commit()
    return user


@pytest.fixture
def totp_service(fernet_key):
    return TotpService(encryption_key=fernet_key)


@pytest.mark.asyncio
async def test_setup_totp_returns_uri(async_session, test_user, totp_service):
    result = await totp_service.setup_totp(async_session, test_user.id, test_user.email)
    assert "otpauth://totp/" in result["provisioning_uri"]
    assert "Margin%20Invest" in result["provisioning_uri"] or "Margin+Invest" in result["provisioning_uri"]
    assert isinstance(result["secret_id"], int)


@pytest.mark.asyncio
async def test_setup_totp_stores_encrypted_secret(async_session, test_user, totp_service, fernet_key):
    result = await totp_service.setup_totp(async_session, test_user.id, test_user.email)
    db_result = await async_session.execute(
        select(TotpSecret).where(TotpSecret.id == result["secret_id"])
    )
    secret_row = db_result.scalar_one()
    assert secret_row.confirmed is False
    # Verify it's encrypted (not plain base32)
    fernet = Fernet(fernet_key)
    decrypted = fernet.decrypt(secret_row.encrypted_secret.encode()).decode()
    assert len(decrypted) == 32  # base32 encoded 20-byte secret


@pytest.mark.asyncio
async def test_confirm_totp_with_valid_code(async_session, test_user, totp_service, fernet_key):
    result = await totp_service.setup_totp(async_session, test_user.id, test_user.email)
    # Decrypt secret to generate a valid code
    db_result = await async_session.execute(
        select(TotpSecret).where(TotpSecret.id == result["secret_id"])
    )
    secret_row = db_result.scalar_one()
    fernet = Fernet(fernet_key)
    raw_secret = fernet.decrypt(secret_row.encrypted_secret.encode()).decode()
    valid_code = pyotp.TOTP(raw_secret).now()

    confirmed = await totp_service.confirm_totp(async_session, result["secret_id"], valid_code)
    assert confirmed is True

    await async_session.refresh(secret_row)
    assert secret_row.confirmed is True

    await async_session.refresh(test_user)
    assert test_user.mfa_enabled is True


@pytest.mark.asyncio
async def test_confirm_totp_with_invalid_code(async_session, test_user, totp_service):
    result = await totp_service.setup_totp(async_session, test_user.id, test_user.email)
    confirmed = await totp_service.confirm_totp(async_session, result["secret_id"], "000000")
    assert confirmed is False


@pytest.mark.asyncio
async def test_verify_totp_valid_code(async_session, test_user, totp_service, fernet_key):
    # Setup and confirm
    result = await totp_service.setup_totp(async_session, test_user.id, test_user.email)
    db_result = await async_session.execute(
        select(TotpSecret).where(TotpSecret.id == result["secret_id"])
    )
    secret_row = db_result.scalar_one()
    fernet = Fernet(fernet_key)
    raw_secret = fernet.decrypt(secret_row.encrypted_secret.encode()).decode()
    valid_code = pyotp.TOTP(raw_secret).now()
    await totp_service.confirm_totp(async_session, result["secret_id"], valid_code)

    # Now verify
    verified = await totp_service.verify_totp(async_session, test_user.id, valid_code)
    assert verified is True


@pytest.mark.asyncio
async def test_verify_totp_invalid_code(async_session, test_user, totp_service, fernet_key):
    result = await totp_service.setup_totp(async_session, test_user.id, test_user.email)
    db_result = await async_session.execute(
        select(TotpSecret).where(TotpSecret.id == result["secret_id"])
    )
    secret_row = db_result.scalar_one()
    fernet = Fernet(fernet_key)
    raw_secret = fernet.decrypt(secret_row.encrypted_secret.encode()).decode()
    valid_code = pyotp.TOTP(raw_secret).now()
    await totp_service.confirm_totp(async_session, result["secret_id"], valid_code)

    verified = await totp_service.verify_totp(async_session, test_user.id, "999999")
    assert verified is False


@pytest.mark.asyncio
async def test_verify_totp_no_confirmed_secret(async_session, test_user, totp_service):
    verified = await totp_service.verify_totp(async_session, test_user.id, "123456")
    assert verified is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_totp_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'TotpService'`

**Step 3: Implement TotpService**

Create `api/src/margin_api/services/totp.py`:

```python
"""TOTP MFA service — setup, confirmation, and verification."""

from __future__ import annotations

import pyotp
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import CredentialUser, TotpSecret


class TotpService:
    """Handles TOTP secret generation, encryption, and verification."""

    def __init__(self, encryption_key: bytes):
        self._fernet = Fernet(encryption_key)

    async def setup_totp(
        self,
        session: AsyncSession,
        user_id: int,
        user_email: str,
    ) -> dict:
        """Generate a new TOTP secret and return provisioning URI for QR code."""
        raw_secret = pyotp.random_base32()
        encrypted = self._fernet.encrypt(raw_secret.encode()).decode()

        totp_secret = TotpSecret(
            user_id=user_id,
            encrypted_secret=encrypted,
            confirmed=False,
        )
        session.add(totp_secret)
        await session.commit()
        await session.refresh(totp_secret)

        totp = pyotp.TOTP(raw_secret)
        uri = totp.provisioning_uri(name=user_email, issuer_name="Margin Invest")

        return {
            "provisioning_uri": uri,
            "secret_id": totp_secret.id,
        }

    async def confirm_totp(
        self,
        session: AsyncSession,
        secret_id: int,
        code: str,
    ) -> bool:
        """Confirm TOTP setup by validating the first code from the user."""
        result = await session.execute(
            select(TotpSecret).where(TotpSecret.id == secret_id, TotpSecret.confirmed == False)  # noqa: E712
        )
        secret_row = result.scalar_one_or_none()
        if secret_row is None:
            return False

        raw_secret = self._fernet.decrypt(secret_row.encrypted_secret.encode()).decode()
        totp = pyotp.TOTP(raw_secret)

        if totp.verify(code, valid_window=1):
            secret_row.confirmed = True
            # Enable MFA on the user
            user_result = await session.execute(
                select(CredentialUser).where(CredentialUser.id == secret_row.user_id)
            )
            user = user_result.scalar_one()
            user.mfa_enabled = True
            await session.commit()
            return True

        return False

    async def verify_totp(
        self,
        session: AsyncSession,
        user_id: int,
        code: str,
    ) -> bool:
        """Verify a TOTP code during login."""
        result = await session.execute(
            select(TotpSecret).where(
                TotpSecret.user_id == user_id,
                TotpSecret.confirmed == True,  # noqa: E712
            )
        )
        secret_row = result.scalar_one_or_none()
        if secret_row is None:
            return False

        raw_secret = self._fernet.decrypt(secret_row.encrypted_secret.encode()).decode()
        totp = pyotp.TOTP(raw_secret)
        return totp.verify(code, valid_window=1)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_totp_service.py -v`
Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add api/src/margin_api/services/totp.py api/tests/test_totp_service.py
git commit -m "feat(api): add TotpService with setup, confirmation, and verification"
```

---

### Task 5: Add WebAuthn Service

**Files:**
- Create: `api/src/margin_api/services/webauthn.py`
- Create: `api/tests/test_webauthn_service.py`

**Step 1: Write the failing tests**

Create `api/tests/test_webauthn_service.py`:

```python
"""Tests for WebAuthn MFA service."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import CredentialUser, WebAuthnCredential
from margin_api.services.webauthn import WebAuthnService


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def test_user(async_session: AsyncSession):
    user = CredentialUser(username="alice", email="alice@x.com", password_hash="hash")
    async_session.add(user)
    await async_session.commit()
    return user


@pytest.fixture
def webauthn_service():
    return WebAuthnService(
        rp_id="localhost",
        rp_name="Margin Invest",
        rp_origin="http://localhost:3000",
    )


@pytest.mark.asyncio
async def test_generate_registration_options(async_session, test_user, webauthn_service):
    options = await webauthn_service.generate_registration_options(
        async_session, test_user.id, test_user.username, test_user.email
    )
    assert "challenge" in options
    assert options["rp"]["name"] == "Margin Invest"
    assert options["user"]["name"] == "alice"


@pytest.mark.asyncio
async def test_generate_registration_options_excludes_existing(async_session, test_user, webauthn_service):
    # Add an existing credential
    cred = WebAuthnCredential(
        user_id=test_user.id,
        credential_id="existing-cred-id",
        public_key="existing-key",
        sign_count=0,
    )
    async_session.add(cred)
    await async_session.commit()

    options = await webauthn_service.generate_registration_options(
        async_session, test_user.id, test_user.username, test_user.email
    )
    exclude_ids = [c["id"] for c in options.get("excludeCredentials", [])]
    assert "existing-cred-id" in exclude_ids


@pytest.mark.asyncio
async def test_generate_authentication_options(async_session, test_user, webauthn_service):
    cred = WebAuthnCredential(
        user_id=test_user.id,
        credential_id="cred-id-1",
        public_key="key-1",
        sign_count=0,
    )
    async_session.add(cred)
    await async_session.commit()

    options = await webauthn_service.generate_authentication_options(
        async_session, test_user.id
    )
    assert "challenge" in options
    allow_ids = [c["id"] for c in options.get("allowCredentials", [])]
    assert "cred-id-1" in allow_ids


@pytest.mark.asyncio
async def test_generate_authentication_options_no_credentials(async_session, test_user, webauthn_service):
    options = await webauthn_service.generate_authentication_options(
        async_session, test_user.id
    )
    assert options.get("allowCredentials", []) == []
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_webauthn_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'WebAuthnService'`

**Step 3: Implement WebAuthnService**

Create `api/src/margin_api/services/webauthn.py`:

```python
"""WebAuthn MFA service — registration and authentication option generation."""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from margin_api.db.models import CredentialUser, WebAuthnCredential


class WebAuthnService:
    """Handles WebAuthn registration and authentication flows."""

    def __init__(self, rp_id: str, rp_name: str, rp_origin: str):
        self._rp_id = rp_id
        self._rp_name = rp_name
        self._rp_origin = rp_origin

    async def generate_registration_options(
        self,
        session: AsyncSession,
        user_id: int,
        username: str,
        email: str,
    ) -> dict:
        """Generate WebAuthn registration options."""
        # Get existing credentials to exclude
        result = await session.execute(
            select(WebAuthnCredential).where(WebAuthnCredential.user_id == user_id)
        )
        existing = result.scalars().all()
        exclude_credentials = [
            {"id": c.credential_id, "type": "public-key"} for c in existing
        ]

        challenge = secrets.token_urlsafe(32)

        return {
            "challenge": challenge,
            "rp": {"name": self._rp_name, "id": self._rp_id},
            "user": {
                "id": str(user_id),
                "name": username,
                "displayName": email,
            },
            "pubKeyCredParams": [
                {"alg": -7, "type": "public-key"},   # ES256
                {"alg": -257, "type": "public-key"},  # RS256
            ],
            "timeout": 60000,
            "authenticatorSelection": {
                "residentKey": "required",
                "userVerification": "preferred",
            },
            "excludeCredentials": exclude_credentials,
            "attestation": "none",
        }

    async def generate_authentication_options(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> dict:
        """Generate WebAuthn authentication options."""
        result = await session.execute(
            select(WebAuthnCredential).where(WebAuthnCredential.user_id == user_id)
        )
        credentials = result.scalars().all()
        allow_credentials = [
            {"id": c.credential_id, "type": "public-key"} for c in credentials
        ]

        challenge = secrets.token_urlsafe(32)

        return {
            "challenge": challenge,
            "timeout": 60000,
            "rpId": self._rp_id,
            "allowCredentials": allow_credentials,
            "userVerification": "preferred",
        }

    async def store_credential(
        self,
        session: AsyncSession,
        user_id: int,
        credential_id: str,
        public_key: str,
    ) -> WebAuthnCredential:
        """Store a verified WebAuthn credential."""
        cred = WebAuthnCredential(
            user_id=user_id,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=0,
        )
        session.add(cred)

        # Enable MFA on user
        user_result = await session.execute(
            select(CredentialUser).where(CredentialUser.id == user_id)
        )
        user = user_result.scalar_one()
        user.mfa_enabled = True
        await session.commit()
        await session.refresh(cred)
        return cred
```

Note: Full WebAuthn attestation/assertion verification with `py_webauthn` requires real browser interaction. The service generates options and stores credentials; the route layer calls `webauthn.verify_registration_response()` and `webauthn.verify_authentication_response()` from the `py_webauthn` library with the actual browser response. Integration tests for that verification require end-to-end browser testing.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_webauthn_service.py -v`
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add api/src/margin_api/services/webauthn.py api/tests/test_webauthn_service.py
git commit -m "feat(api): add WebAuthnService with registration and authentication options"
```

---

### Task 6: Add Auth API Routes

**Files:**
- Create: `api/src/margin_api/schemas/auth.py`
- Create: `api/src/margin_api/routes/auth.py`
- Modify: `api/src/margin_api/routes/__init__.py`
- Modify: `api/src/margin_api/app.py`
- Modify: `api/src/margin_api/config.py`
- Create: `api/tests/test_auth_routes.py`

**Step 1: Add settings for MFA**

Add to `api/src/margin_api/config.py` in the `Settings` class:

```python
    # MFA
    mfa_encryption_key: str = ""  # Fernet key for TOTP secret encryption
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "Margin Invest"
    webauthn_rp_origin: str = "http://localhost:3000"
```

**Step 2: Create auth schemas**

Create `api/src/margin_api/schemas/auth.py`:

```python
"""Auth API request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12)


class RegisterResponse(BaseModel):
    id: int
    username: str
    email: str


class VerifyCredentialsRequest(BaseModel):
    username: str
    password: str


class VerifyCredentialsResponse(BaseModel):
    id: int
    username: str
    email: str
    mfa_status: str
    challenge_token: str


class SetupTotpResponse(BaseModel):
    provisioning_uri: str
    secret_id: int


class ConfirmTotpRequest(BaseModel):
    secret_id: int
    code: str = Field(min_length=6, max_length=6)


class VerifyTotpRequest(BaseModel):
    user_id: int
    code: str = Field(min_length=6, max_length=6)
    challenge_token: str


class MfaVerifyResponse(BaseModel):
    verified: bool
    mfa_token: str | None = None


class WebAuthnOptionsResponse(BaseModel):
    options: dict
```

**Step 3: Create auth routes**

Create `api/src/margin_api/routes/auth.py`:

```python
"""Authentication routes — registration, login, MFA."""

from __future__ import annotations

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.session import get_db
from margin_api.schemas.auth import (
    ConfirmTotpRequest,
    MfaVerifyResponse,
    RegisterRequest,
    RegisterResponse,
    SetupTotpResponse,
    VerifyCredentialsRequest,
    VerifyCredentialsResponse,
    VerifyTotpRequest,
    WebAuthnOptionsResponse,
)
from margin_api.services.auth import AuthService
from margin_api.services.totp import TotpService
from margin_api.services.webauthn import WebAuthnService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _get_auth_service() -> AuthService:
    return AuthService()


def _get_totp_service() -> TotpService:
    settings = get_settings()
    return TotpService(encryption_key=settings.mfa_encryption_key.encode())


def _get_webauthn_service() -> WebAuthnService:
    settings = get_settings()
    return WebAuthnService(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        rp_origin=settings.webauthn_rp_origin,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(_get_auth_service),
):
    try:
        user = await auth_service.register_user(db, body.username, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return RegisterResponse(id=user.id, username=user.username, email=user.email)


@router.post("/verify-credentials", response_model=VerifyCredentialsResponse)
async def verify_credentials(
    body: VerifyCredentialsRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(_get_auth_service),
):
    result = await auth_service.verify_credentials(db, body.username, body.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    challenge_token = await auth_service.create_challenge_token(db, result["id"])
    return VerifyCredentialsResponse(
        id=result["id"],
        username=result["username"],
        email=result["email"],
        mfa_status=result["mfa_status"],
        challenge_token=challenge_token,
    )


@router.post("/mfa/setup-totp", response_model=SetupTotpResponse)
async def setup_totp(
    user_id: int,
    challenge_token: str,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(_get_auth_service),
    totp_service: TotpService = Depends(_get_totp_service),
):
    if not await auth_service.verify_challenge_token(db, user_id, challenge_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")
    from sqlalchemy import select
    from margin_api.db.models import CredentialUser
    result = await db.execute(select(CredentialUser).where(CredentialUser.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    setup_result = await totp_service.setup_totp(db, user_id, user.email)
    return SetupTotpResponse(**setup_result)


@router.post("/mfa/confirm-totp", response_model=MfaVerifyResponse)
async def confirm_totp(
    body: ConfirmTotpRequest,
    db: AsyncSession = Depends(get_db),
    totp_service: TotpService = Depends(_get_totp_service),
):
    confirmed = await totp_service.confirm_totp(db, body.secret_id, body.code)
    return MfaVerifyResponse(verified=confirmed)


@router.post("/mfa/verify-totp", response_model=MfaVerifyResponse)
async def verify_totp(
    body: VerifyTotpRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(_get_auth_service),
    totp_service: TotpService = Depends(_get_totp_service),
):
    if not await auth_service.verify_challenge_token(db, body.user_id, body.challenge_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")
    verified = await totp_service.verify_totp(db, body.user_id, body.code)
    mfa_token = None
    if verified:
        mfa_token = await auth_service.create_challenge_token(db, body.user_id, ttl_minutes=2)
    return MfaVerifyResponse(verified=verified, mfa_token=mfa_token)


@router.post("/mfa/register-webauthn", response_model=WebAuthnOptionsResponse)
async def register_webauthn(
    user_id: int,
    challenge_token: str,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(_get_auth_service),
    webauthn_service: WebAuthnService = Depends(_get_webauthn_service),
):
    if not await auth_service.verify_challenge_token(db, user_id, challenge_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")
    from sqlalchemy import select
    from margin_api.db.models import CredentialUser
    result = await db.execute(select(CredentialUser).where(CredentialUser.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    options = await webauthn_service.generate_registration_options(
        db, user_id, user.username, user.email
    )
    return WebAuthnOptionsResponse(options=options)


@router.post("/mfa/authenticate-webauthn", response_model=WebAuthnOptionsResponse)
async def authenticate_webauthn(
    user_id: int,
    challenge_token: str,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(_get_auth_service),
    webauthn_service: WebAuthnService = Depends(_get_webauthn_service),
):
    if not await auth_service.verify_challenge_token(db, user_id, challenge_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token")
    options = await webauthn_service.generate_authentication_options(db, user_id)
    return WebAuthnOptionsResponse(options=options)
```

**Step 4: Register auth routes**

Add to `api/src/margin_api/routes/__init__.py`:

```python
from margin_api.routes.auth import router as auth_router
```

Add `"auth_router"` to `__all__`.

Add to `api/src/margin_api/app.py` in `create_app()`:

```python
from margin_api.routes.auth import router as auth_router
# ... in create_app():
app.include_router(auth_router)
```

**Step 5: Write route tests**

Create `api/tests/test_auth_routes.py`:

```python
"""Tests for auth API routes."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.session import get_db
from margin_api.app import create_app


@pytest.fixture
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
    yield app
    await engine.dispose()


@pytest.fixture
async def client(app_and_db):
    transport = ASGITransport(app=app_and_db)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "StrongP@ss1!xx",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "short",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "alice", "email": "a1@x.com", "password": "StrongP@ss1!xx",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "username": "alice", "email": "a2@x.com", "password": "StrongP@ss1!xx",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_credentials_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "alice", "email": "a@x.com", "password": "StrongP@ss1!xx",
    })
    resp = await client.post("/api/v1/auth/verify-credentials", json={
        "username": "alice", "password": "StrongP@ss1!xx",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["mfa_status"] == "not_configured"
    assert "challenge_token" in data


@pytest.mark.asyncio
async def test_verify_credentials_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "alice", "email": "a@x.com", "password": "StrongP@ss1!xx",
    })
    resp = await client.post("/api/v1/auth/verify-credentials", json={
        "username": "alice", "password": "wrong",
    })
    assert resp.status_code == 401
```

**Step 6: Run tests**

Run: `uv run pytest api/tests/test_auth_routes.py -v`
Expected: All 5 tests PASS.

Note: The `setup-totp` and `verify-totp` route tests require a valid `MFA_ENCRYPTION_KEY` env var. Set `MARGIN_MFA_ENCRYPTION_KEY` to a Fernet key in the test environment, or mock the settings. These are covered more thoroughly in the service-layer tests.

**Step 7: Commit**

```bash
git add api/src/margin_api/schemas/auth.py api/src/margin_api/routes/auth.py \
    api/src/margin_api/routes/__init__.py api/src/margin_api/app.py \
    api/src/margin_api/config.py api/tests/test_auth_routes.py
git commit -m "feat(api): add auth routes for registration, verification, and MFA"
```

---

### Task 7: Add Web Auth Dependencies

**Files:**
- Modify: `web/package.json`

**Step 1: Install new dependencies**

Run from `web/`:

```bash
npm install @simplewebauthn/browser qrcode.react
npm install --save-dev @types/qrcode.react
```

**Step 2: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "chore(web): add simplewebauthn and qrcode.react dependencies"
```

---

### Task 8: Reconfigure Auth.js

**Files:**
- Modify: `web/src/lib/auth.ts`
- Modify: `web/src/lib/__tests__/auth.test.ts`

**Step 1: Update the auth.test.ts test**

Replace `web/src/lib/__tests__/auth.test.ts` with:

```typescript
import { describe, it, expect, vi } from "vitest"

const { mockNextAuth } = vi.hoisted(() => {
  const mockAuth = vi.fn()
  const mockHandlers = { GET: vi.fn(), POST: vi.fn() }
  const mockSignIn = vi.fn()
  const mockSignOut = vi.fn()
  const mockNextAuth = vi.fn(() => ({
    handlers: mockHandlers,
    auth: mockAuth,
    signIn: mockSignIn,
    signOut: mockSignOut,
  }))
  return { mockAuth, mockHandlers, mockSignIn, mockSignOut, mockNextAuth }
})

vi.mock("next-auth", () => ({ default: mockNextAuth }))
vi.mock("next-auth/providers/google", () => ({ default: vi.fn(() => ({ id: "google" })) }))
vi.mock("next-auth/providers/github", () => ({ default: vi.fn(() => ({ id: "github" })) }))
vi.mock("next-auth/providers/credentials", () => ({
  default: vi.fn((config) => ({ id: "credentials", ...config })),
}))

import { handlers, auth, signIn, signOut } from "@/lib/auth"

describe("Auth configuration", () => {
  it("exports handlers, auth, signIn, and signOut", () => {
    expect(handlers).toBeDefined()
    expect(auth).toBeDefined()
    expect(signIn).toBeDefined()
    expect(signOut).toBeDefined()
  })

  it("configures exactly 3 providers (Google, GitHub, Credentials)", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown>
    expect(config.providers).toHaveLength(3)
  })

  it("does NOT include Microsoft or Facebook providers", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown>
    const providers = config.providers as { id?: string }[]
    const ids = providers.map((p) => p.id).filter(Boolean)
    expect(ids).not.toContain("microsoft-entra-id")
    expect(ids).not.toContain("facebook")
  })

  it("configures JWT session strategy", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown>
    expect(config.session).toEqual({ strategy: "jwt" })
  })

  it("configures custom sign-in page", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown>
    expect((config.pages as Record<string, string>).signIn).toBe("/login")
  })

  it("configures signIn, jwt, and session callbacks", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown>
    const callbacks = config.callbacks as Record<string, unknown>
    expect(callbacks.signIn).toBeTypeOf("function")
    expect(callbacks.jwt).toBeTypeOf("function")
    expect(callbacks.session).toBeTypeOf("function")
  })

  it("configures custom error page", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown>
    expect((config.pages as Record<string, string>).error).toBe("/auth/error")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm run test:run -- src/lib/__tests__/auth.test.ts`
Expected: FAIL — tests expect 3 providers but find 4, no `signIn`/`jwt`/`session` callbacks.

**Step 3: Update auth.ts**

Replace `web/src/lib/auth.ts` with:

```typescript
import NextAuth, { CredentialsSignin } from "next-auth"
import Google from "next-auth/providers/google"
import GitHub from "next-auth/providers/github"
import Credentials from "next-auth/providers/credentials"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

class MfaRequired extends CredentialsSignin {
  code = "mfa_required"
}

class MfaNotConfigured extends CredentialsSignin {
  code = "mfa_not_configured"
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    GitHub({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    }),
    Credentials({
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
        mfaToken: { label: "MFA Token", type: "text" },
      },
      async authorize(credentials) {
        const { username, password, mfaToken } = credentials as {
          username: string
          password: string
          mfaToken?: string
        }

        const resp = await fetch(`${API_URL}/api/v1/auth/verify-credentials`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        })

        if (!resp.ok) return null

        const data = await resp.json()

        // Return user with MFA metadata for the signIn callback
        return {
          id: String(data.id),
          name: data.username,
          email: data.email,
          mfaStatus: data.mfa_status,
          challengeToken: data.challenge_token,
          mfaToken: mfaToken || null,
        }
      },
    }),
  ],
  pages: {
    signIn: "/login",
    error: "/auth/error",
  },
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async signIn({ user, account }) {
      // OAuth providers: allow immediately
      if (account?.provider !== "credentials") {
        return true
      }

      const u = user as typeof user & {
        mfaStatus?: string
        mfaToken?: string
      }

      // Credentials: check MFA status
      if (u.mfaStatus === "not_configured") {
        return `/mfa/setup?userId=${user.id}`
      }

      if (u.mfaStatus === "configured" && !u.mfaToken) {
        return `/mfa/verify?userId=${user.id}`
      }

      // MFA token provided: validate it
      if (u.mfaToken) {
        return true
      }

      return false
    },

    async jwt({ token, user, account }) {
      if (user) {
        token.userId = user.id
        token.authMethod = account?.provider === "credentials" ? "credentials" : "oauth"
        const u = user as typeof user & { mfaToken?: string }
        token.mfaVerified = token.authMethod === "oauth" || !!u.mfaToken
      }
      return token
    },

    async session({ session, token }) {
      session.user.id = token.userId as string
      ;(session as Record<string, unknown>).authMethod = token.authMethod
      ;(session as Record<string, unknown>).mfaVerified = token.mfaVerified
      return session
    },
  },
})
```

**Step 4: Run test to verify it passes**

Run: `cd web && npm run test:run -- src/lib/__tests__/auth.test.ts`
Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add web/src/lib/auth.ts web/src/lib/__tests__/auth.test.ts
git commit -m "feat(web): reconfigure Auth.js — remove Microsoft/Facebook, add Credentials with MFA callbacks"
```

---

### Task 9: Update Login Page

**Files:**
- Modify: `web/src/app/login/login-buttons.tsx`
- Modify: `web/src/app/login/page.tsx`
- Modify: `web/src/app/login/__tests__/login-buttons.test.tsx`
- Modify: `web/src/app/login/__tests__/page.test.tsx`

**Step 1: Update login-buttons test**

Replace `web/src/app/login/__tests__/login-buttons.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { LoginButtons } from "../login-buttons"

const { mockSignIn } = vi.hoisted(() => ({ mockSignIn: vi.fn() }))
vi.mock("next-auth/react", () => ({ signIn: mockSignIn }))

describe("LoginButtons", () => {
  beforeEach(() => { mockSignIn.mockClear() })

  it("renders Google and GitHub OAuth buttons", () => {
    render(<LoginButtons />)
    expect(screen.getByText("Sign in with Google")).toBeInTheDocument()
    expect(screen.getByText("Sign in with GitHub")).toBeInTheDocument()
  })

  it("does NOT render Microsoft or Facebook buttons", () => {
    render(<LoginButtons />)
    expect(screen.queryByText(/Microsoft/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Facebook/)).not.toBeInTheDocument()
  })

  it("renders username and password input fields", () => {
    render(<LoginButtons />)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it("renders a credentials sign-in button", () => {
    render(<LoginButtons />)
    expect(screen.getByRole("button", { name: /sign in$/i })).toBeInTheDocument()
  })

  it("calls signIn with google when Google button clicked", async () => {
    const user = userEvent.setup()
    render(<LoginButtons />)
    await user.click(screen.getByText("Sign in with Google"))
    expect(mockSignIn).toHaveBeenCalledWith("google", { callbackUrl: "/dashboard" })
  })

  it("calls signIn with credentials when form submitted", async () => {
    const user = userEvent.setup()
    render(<LoginButtons />)
    await user.type(screen.getByLabelText(/username/i), "alice")
    await user.type(screen.getByLabelText(/password/i), "mypassword")
    await user.click(screen.getByRole("button", { name: /sign in$/i }))
    expect(mockSignIn).toHaveBeenCalledWith("credentials", {
      username: "alice",
      password: "mypassword",
      callbackUrl: "/dashboard",
    })
  })

  it("renders a link to create an account", () => {
    render(<LoginButtons />)
    expect(screen.getByText(/create one/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm run test:run -- src/app/login/__tests__/login-buttons.test.tsx`
Expected: FAIL — tests expect no Microsoft/Facebook, expect username/password fields.

**Step 3: Update login-buttons.tsx**

Replace `web/src/app/login/login-buttons.tsx`:

```typescript
"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import Link from "next/link"

const oauthProviders = [
  { id: "google", name: "Google" },
  { id: "github", name: "GitHub" },
]

export function LoginButtons() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  const handleCredentialsSignIn = (e: React.FormEvent) => {
    e.preventDefault()
    signIn("credentials", {
      username,
      password,
      callbackUrl: "/dashboard",
    })
  }

  return (
    <div className="flex flex-col gap-6 w-full max-w-sm">
      {/* OAuth providers */}
      <div className="flex flex-col gap-3">
        {oauthProviders.map((provider) => (
          <button
            key={provider.id}
            onClick={() => signIn(provider.id, { callbackUrl: "/dashboard" })}
            className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] hover:border-[#D4A843] transition-colors"
          >
            Sign in with {provider.name}
          </button>
        ))}
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-[#1E2740]" />
        <span className="text-sm text-[#8A8473]">or continue with</span>
        <div className="flex-1 h-px bg-[#1E2740]" />
      </div>

      {/* Credentials form */}
      <form onSubmit={handleCredentialsSignIn} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-sm text-[#8A8473]">Username</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] focus:border-[#D4A843] outline-none transition-colors"
            required
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-[#8A8473]">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] focus:border-[#D4A843] outline-none transition-colors"
            required
          />
        </label>
        <button
          type="submit"
          className="w-full px-4 py-3 rounded-lg bg-[#D4A843] text-[#0A0F1C] font-medium hover:bg-[#E8B84D] transition-colors"
        >
          Sign In
        </button>
      </form>

      <p className="text-sm text-[#8A8473] text-center">
        Don&apos;t have an account?{" "}
        <Link href="/register" className="text-[#D4A843] hover:underline">
          Create one
        </Link>
      </p>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npm run test:run -- src/app/login/__tests__/login-buttons.test.tsx`
Expected: All 7 tests PASS.

**Step 5: Update page.test.tsx**

The existing `page.test.tsx` should still pass since `LoginPage` just renders a heading + `LoginButtons`. Verify:

Run: `cd web && npm run test:run -- src/app/login/__tests__/page.test.tsx`
Expected: All 2 tests PASS.

**Step 6: Commit**

```bash
git add web/src/app/login/login-buttons.tsx web/src/app/login/__tests__/login-buttons.test.tsx
git commit -m "feat(web): update login page — remove Microsoft/Facebook, add credentials form"
```

---

### Task 10: Add Registration Page

**Files:**
- Create: `web/src/app/register/page.tsx`
- Create: `web/src/app/register/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Create `web/src/app/register/__tests__/page.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import RegisterPage from "../page"

// Mock fetch and next/navigation
const mockPush = vi.fn()
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }))

global.fetch = vi.fn()

describe("Register Page", () => {
  it("renders the registration heading", () => {
    render(<RegisterPage />)
    expect(screen.getByRole("heading", { name: /create.*account/i })).toBeInTheDocument()
  })

  it("renders username, email, and password fields", () => {
    render(<RegisterPage />)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it("renders a create account button", () => {
    render(<RegisterPage />)
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument()
  })

  it("renders a link to sign in", () => {
    render(<RegisterPage />)
    expect(screen.getByText(/sign in/i)).toBeInTheDocument()
  })

  it("shows error on failed registration", async () => {
    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: "Username already taken" }),
    })
    const user = userEvent.setup()
    render(<RegisterPage />)
    await user.type(screen.getByLabelText(/username/i), "alice")
    await user.type(screen.getByLabelText(/email/i), "a@x.com")
    await user.type(screen.getByLabelText(/password/i), "StrongP@ss1!xx")
    await user.click(screen.getByRole("button", { name: /create account/i }))
    expect(await screen.findByText(/already taken/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm run test:run -- src/app/register/__tests__/page.test.tsx`
Expected: FAIL — file not found.

**Step 3: Implement register page**

Create `web/src/app/register/page.tsx`:

```typescript
"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export default function RegisterPage() {
  const router = useRouter()
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    const resp = await fetch(`${API_URL}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    })

    if (!resp.ok) {
      const data = await resp.json()
      setError(data.detail || "Registration failed")
      return
    }

    router.push("/login")
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-8 p-8 w-full max-w-sm">
        <h1 className="text-3xl font-bold text-[#E8E4DD]">Create an Account</h1>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3 w-full">
          <label className="flex flex-col gap-1">
            <span className="text-sm text-[#8A8473]">Username</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] focus:border-[#D4A843] outline-none transition-colors"
              required
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm text-[#8A8473]">Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] focus:border-[#D4A843] outline-none transition-colors"
              required
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm text-[#8A8473]">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] focus:border-[#D4A843] outline-none transition-colors"
              required
              minLength={12}
            />
          </label>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            className="w-full px-4 py-3 rounded-lg bg-[#D4A843] text-[#0A0F1C] font-medium hover:bg-[#E8B84D] transition-colors"
          >
            Create Account
          </button>
        </form>

        <p className="text-sm text-[#8A8473]">
          Already have an account?{" "}
          <Link href="/login" className="text-[#D4A843] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npm run test:run -- src/app/register/__tests__/page.test.tsx`
Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add web/src/app/register/
git commit -m "feat(web): add registration page with form validation and error display"
```

---

### Task 11: Add MFA Setup Page

**Files:**
- Create: `web/src/app/mfa/setup/page.tsx`
- Create: `web/src/app/mfa/setup/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Create `web/src/app/mfa/setup/__tests__/page.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import MfaSetupPage from "../page"

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams("userId=1"),
}))

vi.mock("qrcode.react", () => ({
  QRCodeSVG: ({ value }: { value: string }) => (
    <svg data-testid="qr-code" data-value={value} />
  ),
}))

global.fetch = vi.fn()

describe("MFA Setup Page", () => {
  it("renders the MFA setup heading", () => {
    render(<MfaSetupPage />)
    expect(screen.getByRole("heading", { name: /set up.*mfa/i })).toBeInTheDocument()
  })

  it("renders TOTP and WebAuthn setup options", () => {
    render(<MfaSetupPage />)
    expect(screen.getByText(/authenticator app/i)).toBeInTheDocument()
    expect(screen.getByText(/security key/i)).toBeInTheDocument()
  })

  it("renders a verification code input", () => {
    render(<MfaSetupPage />)
    expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm run test:run -- src/app/mfa/setup/__tests__/page.test.tsx`
Expected: FAIL — file not found.

**Step 3: Implement MFA setup page**

Create `web/src/app/mfa/setup/page.tsx`:

```typescript
"use client"

import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { QRCodeSVG } from "qrcode.react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export default function MfaSetupPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const userId = searchParams.get("userId")

  const [provisioningUri, setProvisioningUri] = useState("")
  const [secretId, setSecretId] = useState<number | null>(null)
  const [code, setCode] = useState("")
  const [error, setError] = useState("")
  const [step, setStep] = useState<"choose" | "totp" | "webauthn">("choose")

  const handleSetupTotp = async () => {
    const resp = await fetch(
      `${API_URL}/api/v1/auth/mfa/setup-totp?user_id=${userId}&challenge_token=pending`,
      { method: "POST" }
    )
    if (!resp.ok) {
      setError("Failed to generate TOTP secret")
      return
    }
    const data = await resp.json()
    setProvisioningUri(data.provisioning_uri)
    setSecretId(data.secret_id)
    setStep("totp")
  }

  const handleConfirmTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    const resp = await fetch(`${API_URL}/api/v1/auth/mfa/confirm-totp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ secret_id: secretId, code }),
    })
    const data = await resp.json()
    if (data.verified) {
      router.push("/login")
    } else {
      setError("Invalid code. Please try again.")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-8 p-8 w-full max-w-md">
        <h1 className="text-3xl font-bold text-[#E8E4DD]">Set Up MFA</h1>
        <p className="text-[#8A8473] text-center">
          Multi-factor authentication is required for password-based accounts.
        </p>

        {step === "choose" && (
          <div className="flex flex-col gap-4 w-full">
            <button
              onClick={handleSetupTotp}
              className="w-full px-4 py-4 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] hover:border-[#D4A843] transition-colors text-left"
            >
              <div className="font-medium">Authenticator App</div>
              <div className="text-sm text-[#8A8473]">
                Use Google Authenticator, Authy, or 1Password
              </div>
            </button>
            <button
              onClick={() => setStep("webauthn")}
              className="w-full px-4 py-4 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] hover:border-[#D4A843] transition-colors text-left"
            >
              <div className="font-medium">Security Key</div>
              <div className="text-sm text-[#8A8473]">
                Use a YubiKey, fingerprint, or passkey
              </div>
            </button>
          </div>
        )}

        {step === "totp" && (
          <div className="flex flex-col items-center gap-6 w-full">
            {provisioningUri && (
              <div className="bg-white p-4 rounded-lg">
                <QRCodeSVG value={provisioningUri} size={200} />
              </div>
            )}
            <p className="text-sm text-[#8A8473] text-center">
              Scan the QR code with your authenticator app, then enter the code below.
            </p>
            <form onSubmit={handleConfirmTotp} className="flex flex-col gap-3 w-full">
              <label className="flex flex-col gap-1">
                <span className="text-sm text-[#8A8473]">Verification Code</span>
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] focus:border-[#D4A843] outline-none transition-colors text-center text-2xl tracking-widest"
                  maxLength={6}
                  pattern="[0-9]{6}"
                  required
                />
              </label>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <button
                type="submit"
                className="w-full px-4 py-3 rounded-lg bg-[#D4A843] text-[#0A0F1C] font-medium hover:bg-[#E8B84D] transition-colors"
              >
                Verify & Enable
              </button>
            </form>
          </div>
        )}

        {step === "webauthn" && (
          <div className="flex flex-col items-center gap-4 w-full">
            <p className="text-[#8A8473] text-center">
              Click below to register your security key or passkey.
            </p>
            <button
              className="w-full px-4 py-3 rounded-lg bg-[#D4A843] text-[#0A0F1C] font-medium hover:bg-[#E8B84D] transition-colors"
            >
              Register Security Key
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npm run test:run -- src/app/mfa/setup/__tests__/page.test.tsx`
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add web/src/app/mfa/setup/
git commit -m "feat(web): add MFA setup page with TOTP QR code and WebAuthn option"
```

---

### Task 12: Add MFA Verify Page

**Files:**
- Create: `web/src/app/mfa/verify/page.tsx`
- Create: `web/src/app/mfa/verify/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Create `web/src/app/mfa/verify/__tests__/page.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import MfaVerifyPage from "../page"

const { mockSignIn } = vi.hoisted(() => ({ mockSignIn: vi.fn() }))
vi.mock("next-auth/react", () => ({ signIn: mockSignIn }))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams("userId=1"),
}))

describe("MFA Verify Page", () => {
  it("renders the verification heading", () => {
    render(<MfaVerifyPage />)
    expect(screen.getByRole("heading", { name: /verify.*identity/i })).toBeInTheDocument()
  })

  it("renders TOTP code input", () => {
    render(<MfaVerifyPage />)
    expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
  })

  it("renders a verify button", () => {
    render(<MfaVerifyPage />)
    expect(screen.getByRole("button", { name: /verify/i })).toBeInTheDocument()
  })

  it("renders a security key option", () => {
    render(<MfaVerifyPage />)
    expect(screen.getByText(/security key/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm run test:run -- src/app/mfa/verify/__tests__/page.test.tsx`
Expected: FAIL — file not found.

**Step 3: Implement MFA verify page**

Create `web/src/app/mfa/verify/page.tsx`:

```typescript
"use client"

import { useState } from "react"
import { useSearchParams } from "next/navigation"
import { signIn } from "next-auth/react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export default function MfaVerifyPage() {
  const searchParams = useSearchParams()
  const userId = searchParams.get("userId")

  const [code, setCode] = useState("")
  const [error, setError] = useState("")
  const [method, setMethod] = useState<"totp" | "webauthn">("totp")

  const handleVerifyTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    const resp = await fetch(`${API_URL}/api/v1/auth/mfa/verify-totp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: Number(userId),
        code,
        challenge_token: sessionStorage.getItem("challengeToken") || "",
      }),
    })

    const data = await resp.json()
    if (data.verified && data.mfa_token) {
      // Second-pass signIn with the MFA token
      signIn("credentials", {
        username: sessionStorage.getItem("username") || "",
        password: sessionStorage.getItem("password") || "",
        mfaToken: data.mfa_token,
        callbackUrl: "/dashboard",
      })
    } else {
      setError("Invalid code. Please try again.")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-8 p-8 w-full max-w-sm">
        <h1 className="text-3xl font-bold text-[#E8E4DD]">Verify Your Identity</h1>
        <p className="text-[#8A8473] text-center">
          Enter your authentication code to continue.
        </p>

        {/* Method tabs */}
        <div className="flex gap-2 w-full">
          <button
            onClick={() => setMethod("totp")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              method === "totp"
                ? "bg-[#D4A843] text-[#0A0F1C]"
                : "bg-[#141B2D] text-[#8A8473] border border-[#1E2740]"
            }`}
          >
            Authenticator
          </button>
          <button
            onClick={() => setMethod("webauthn")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              method === "webauthn"
                ? "bg-[#D4A843] text-[#0A0F1C]"
                : "bg-[#141B2D] text-[#8A8473] border border-[#1E2740]"
            }`}
          >
            Security Key
          </button>
        </div>

        {method === "totp" && (
          <form onSubmit={handleVerifyTotp} className="flex flex-col gap-3 w-full">
            <label className="flex flex-col gap-1">
              <span className="text-sm text-[#8A8473]">Verification Code</span>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full px-4 py-3 rounded-lg bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] focus:border-[#D4A843] outline-none transition-colors text-center text-2xl tracking-widest"
                maxLength={6}
                pattern="[0-9]{6}"
                required
              />
            </label>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <button
              type="submit"
              className="w-full px-4 py-3 rounded-lg bg-[#D4A843] text-[#0A0F1C] font-medium hover:bg-[#E8B84D] transition-colors"
            >
              Verify
            </button>
          </form>
        )}

        {method === "webauthn" && (
          <div className="flex flex-col items-center gap-4 w-full">
            <p className="text-[#8A8473] text-center">
              Insert your security key and tap the button below.
            </p>
            <button
              className="w-full px-4 py-3 rounded-lg bg-[#D4A843] text-[#0A0F1C] font-medium hover:bg-[#E8B84D] transition-colors"
            >
              Authenticate with Security Key
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npm run test:run -- src/app/mfa/verify/__tests__/page.test.tsx`
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add web/src/app/mfa/verify/
git commit -m "feat(web): add MFA verification page with TOTP and WebAuthn options"
```

---

### Task 13: Add Auth Error Page

**Files:**
- Create: `web/src/app/auth/error/page.tsx`
- Create: `web/src/app/auth/error/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Create `web/src/app/auth/error/__tests__/page.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import AuthErrorPage from "../page"

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("error=CredentialsSignin&code=invalid_credentials"),
}))

describe("Auth Error Page", () => {
  it("renders an error heading", () => {
    render(<AuthErrorPage />)
    expect(screen.getByRole("heading", { name: /authentication error/i })).toBeInTheDocument()
  })

  it("renders a try again link", () => {
    render(<AuthErrorPage />)
    expect(screen.getByText(/try again/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm run test:run -- src/app/auth/error/__tests__/page.test.tsx`
Expected: FAIL — file not found.

**Step 3: Implement error page**

Create `web/src/app/auth/error/page.tsx`:

```typescript
"use client"

import { useSearchParams } from "next/navigation"
import Link from "next/link"

const errorMessages: Record<string, Record<string, string>> = {
  CredentialsSignin: {
    invalid_credentials: "Invalid username or password.",
    account_locked: "Your account has been locked due to too many failed attempts. Please try again in 15 minutes.",
    mfa_required: "Multi-factor authentication is required.",
    mfa_not_configured: "You must set up MFA before signing in.",
    default: "Invalid username or password.",
  },
  AccessDenied: { default: "You do not have permission to sign in." },
  Configuration: { default: "Server configuration error. Please contact support." },
  Default: { default: "An error occurred during sign in." },
}

export default function AuthErrorPage() {
  const searchParams = useSearchParams()
  const error = searchParams.get("error") || "Default"
  const code = searchParams.get("code") || "default"

  const category = errorMessages[error] || errorMessages.Default
  const message = category[code] || category.default || errorMessages.Default.default

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-6 p-8 max-w-sm text-center">
        <h1 className="text-3xl font-bold text-[#E8E4DD]">Authentication Error</h1>
        <p className="text-[#8A8473]">{message}</p>
        <Link
          href="/login"
          className="px-6 py-3 rounded-lg bg-[#D4A843] text-[#0A0F1C] font-medium hover:bg-[#E8B84D] transition-colors"
        >
          Try again
        </Link>
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npm run test:run -- src/app/auth/error/__tests__/page.test.tsx`
Expected: All 2 tests PASS.

**Step 5: Commit**

```bash
git add web/src/app/auth/error/
git commit -m "feat(web): add custom auth error page with error code mapping"
```

---

### Task 14: Update Protected Route Middleware

**Files:**
- Modify: `web/src/proxy.ts`

**Step 1: Update proxy.ts to include MFA routes as public**

Replace `web/src/proxy.ts`:

```typescript
export { auth as proxy } from "@/lib/auth"

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/settings/:path*",
    "/backtesting/:path*",
  ],
}
```

No change needed — `/mfa/*`, `/register`, and `/auth/error` are not in the matcher, so they're already public. Verify the file is correct.

**Step 2: Commit (skip if no changes)**

---

### Task 15: Run Full Test Suite

**Step 1: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All tests PASS (existing 176 + new ~30 auth tests).

**Step 2: Run all web tests**

Run: `cd web && npm run test:run`
Expected: All tests PASS (existing 91 + new ~25 auth tests, minus removed Microsoft/Facebook tests).

**Step 3: Fix any failures**

If any test fails, fix the issue and re-run. Common issues:
- Old tests referencing Microsoft/Facebook providers — remove those assertions
- Import path issues — verify all paths match the project structure

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test suite issues after auth reconfiguration"
```

---

### Task 16: Update Account Settings for MFA Management

**Files:**
- Modify: `web/src/components/settings/account-section.tsx`
- Create: `web/src/components/settings/__tests__/account-section.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/settings/__tests__/account-section.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AccountSection } from "../account-section"

const mockUseSession = vi.fn()
vi.mock("next-auth/react", () => ({
  useSession: () => mockUseSession(),
}))

describe("AccountSection", () => {
  it("shows MFA section for credentials users", () => {
    mockUseSession.mockReturnValue({
      data: {
        user: { name: "Alice", email: "alice@x.com" },
        authMethod: "credentials",
        mfaVerified: true,
      },
    })
    render(<AccountSection />)
    expect(screen.getByText(/multi-factor authentication/i)).toBeInTheDocument()
  })

  it("does not show MFA section for OAuth users", () => {
    mockUseSession.mockReturnValue({
      data: {
        user: { name: "Alice", email: "alice@x.com", image: "https://example.com/pic.jpg" },
        authMethod: "oauth",
        mfaVerified: true,
      },
    })
    render(<AccountSection />)
    expect(screen.queryByText(/multi-factor authentication/i)).not.toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npm run test:run -- src/components/settings/__tests__/account-section.test.tsx`
Expected: FAIL — no MFA section rendered.

**Step 3: Update account-section.tsx**

Replace `web/src/components/settings/account-section.tsx`:

```typescript
"use client"

import { useSession } from "next-auth/react"

export function AccountSection() {
  const { data: session } = useSession()
  const authMethod = (session as Record<string, unknown> | null)?.authMethod as string | undefined

  return (
    <section className="bg-bg-secondary border border-border rounded-xl p-6">
      <h2 className="text-lg font-bold text-text-primary mb-4">Account</h2>
      {session?.user ? (
        <div className="space-y-6">
          <div className="flex items-center gap-4">
            {session.user.image && (
              <img
                src={session.user.image}
                alt=""
                className="w-12 h-12 rounded-full border border-border"
              />
            )}
            <div>
              <div className="text-text-primary font-medium">
                {session.user.name || "User"}
              </div>
              <div className="text-sm text-text-secondary">
                {session.user.email}
              </div>
            </div>
          </div>

          {authMethod === "credentials" && (
            <div className="border-t border-border pt-4">
              <h3 className="text-md font-medium text-text-primary mb-2">
                Multi-Factor Authentication
              </h3>
              <p className="text-sm text-text-secondary">
                MFA is enabled for your account. You can manage your authentication methods below.
              </p>
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

**Step 4: Run test to verify it passes**

Run: `cd web && npm run test:run -- src/components/settings/__tests__/account-section.test.tsx`
Expected: All 2 tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/settings/account-section.tsx \
    web/src/components/settings/__tests__/account-section.test.tsx
git commit -m "feat(web): add MFA management section to account settings for credentials users"
```

---

### Task 17: Clean Up Environment Variables

**Files:**
- Modify: `web/.env.local.example`

**Step 1: Update .env.local.example**

Remove Microsoft and Facebook variables, keep Google and GitHub:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
AUTH_SECRET=your-auth-secret-here

# OAuth Providers
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# API MFA Config (for backend)
MARGIN_MFA_ENCRYPTION_KEY=your-fernet-key-here
```

**Step 2: Commit**

```bash
git add web/.env.local.example
git commit -m "chore(web): clean up env vars — remove Microsoft/Facebook, add MFA config"
```

---

### Task 18: Final Verification

**Step 1: Run complete API test suite**

Run: `uv run pytest api/tests/ -v --tb=short`
Expected: All tests PASS.

**Step 2: Run complete web test suite**

Run: `cd web && npm run test:run`
Expected: All tests PASS.

**Step 3: Verify no regressions in engine tests**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: All 784 tests PASS.

**Step 4: Lint check**

Run: `uv run ruff check api/`
Expected: No lint errors.

**Step 5: Commit any final fixes and verify clean state**

```bash
git status
git log --oneline -20
```
