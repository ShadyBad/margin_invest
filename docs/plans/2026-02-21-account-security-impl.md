# Account Security Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify the user model, redesign the Security section with provider linking, enforce MFA with a 72-hour grace period, and implement recovery codes.

**Architecture:** Merge `users` + `credential_users` into one `users` table with nullable credential fields. Add `linked_providers` and `recovery_codes` tables. New `@require_mfa` middleware gates sensitive endpoints. Frontend Security section renders five provider states, password management, and MFA lifecycle.

**Tech Stack:** SQLAlchemy 2.0 + Alembic (async), FastAPI, Argon2id + bcrypt, pyotp, Next.js 15 + NextAuth v5, TypeScript, Tailwind CSS

**Design doc:** `docs/plans/2026-02-21-account-security-design.md`

---

## Phase 1: Unified User Model (Database)

### Task 1: Create Alembic migration for unified users table

**Files:**
- Create: `api/alembic/versions/xxxx_unify_user_tables.py` (Alembic will generate the filename)
- Reference: `api/src/margin_api/db/models.py`

**Step 1: Generate empty migration**

Run: `cd /Users/brandon/repos/margin_invest && uv run alembic -c api/alembic.ini revision -m "unify user tables"`
Expected: New file created in `api/alembic/versions/`

**Step 2: Write the upgrade function**

The migration must:

1. Create `linked_providers` table:
   ```python
   op.create_table(
       "linked_providers",
       sa.Column("id", sa.Integer, primary_key=True),
       sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
       sa.Column("provider", sa.String(50), nullable=False),
       sa.Column("oauth_id", sa.String(255), nullable=False),
       sa.Column("provider_email", sa.String(320), nullable=True),
       sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
   )
   op.create_unique_constraint("uq_linked_providers_provider_oauth_id", "linked_providers", ["provider", "oauth_id"])
   op.create_unique_constraint("uq_linked_providers_user_id_provider", "linked_providers", ["user_id", "provider"])
   ```

2. Create `recovery_codes` table:
   ```python
   op.create_table(
       "recovery_codes",
       sa.Column("id", sa.Integer, primary_key=True),
       sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
       sa.Column("code_hash", sa.Text, nullable=False),
       sa.Column("used", sa.Boolean, default=False, nullable=False),
       sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
       sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
   )
   ```

3. Add nullable credential columns to existing `users` table:
   ```python
   op.add_column("users", sa.Column("password_hash", sa.Text, nullable=True))
   op.add_column("users", sa.Column("mfa_enabled", sa.Boolean, server_default="false", nullable=False))
   op.add_column("users", sa.Column("mfa_grace_deadline", sa.DateTime(timezone=True), nullable=True))
   op.add_column("users", sa.Column("failed_login_attempts", sa.Integer, server_default="0", nullable=False))
   op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
   op.add_column("users", sa.Column("last_totp_counter", sa.Integer, nullable=True))
   op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
   op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
   ```

4. Make existing `users` columns nullable where needed:
   ```python
   # oauth_id, name, provider were NOT NULL — make nullable for credential users
   op.alter_column("users", "oauth_id", existing_type=sa.String(255), nullable=True)
   op.alter_column("users", "name", existing_type=sa.String(255), nullable=True)
   op.alter_column("users", "provider", existing_type=sa.String(50), nullable=True)
   ```

5. Migrate data from `credential_users` into `users`:
   ```python
   # Insert credential users into unified users table
   op.execute("""
       INSERT INTO users (email, name, password_hash, mfa_enabled, failed_login_attempts,
           locked_until, last_totp_counter, password_changed_at, avatar_url,
           stripe_customer_id, stripe_subscription_id, subscription_plan,
           subscription_status, current_period_end, created_at, updated_at,
           mfa_grace_deadline)
       SELECT email, username, password_hash, mfa_enabled, failed_login_attempts,
           locked_until, last_totp_counter, password_changed_at, avatar_url,
           stripe_customer_id, stripe_subscription_id, subscription_plan,
           subscription_status, current_period_end, created_at, updated_at,
           CASE WHEN mfa_enabled = false
                THEN NOW() + INTERVAL '72 hours'
                ELSE NULL END
       FROM credential_users
   """)
   ```

6. Create `linked_providers` rows for existing OAuth users:
   ```python
   op.execute("""
       INSERT INTO linked_providers (user_id, provider, oauth_id, provider_email, linked_at)
       SELECT id, provider, oauth_id, email, created_at
       FROM users
       WHERE oauth_id IS NOT NULL AND provider IS NOT NULL
   """)
   ```

7. Repoint FK references from `credential_users` to `users`:
   ```python
   # For totp_secrets, webauthn_credentials, mfa_challenge_tokens:
   # Add new user_id column pointing to users, migrate data, drop old column
   # This requires mapping old credential_users.id -> new users.id by email match
   for table in ["totp_secrets", "webauthn_credentials", "mfa_challenge_tokens"]:
       op.add_column(table, sa.Column("new_user_id", sa.Integer, nullable=True))
       op.execute(f"""
           UPDATE {table} SET new_user_id = (
               SELECT u.id FROM users u
               JOIN credential_users cu ON cu.email = u.email
               WHERE cu.id = {table}.user_id
           )
       """)
       op.drop_constraint(f"{table}_user_id_fkey", table, type_="foreignkey")
       op.drop_column(table, "user_id")
       op.alter_column(table, "new_user_id", new_column_name="user_id", nullable=False)
       op.create_foreign_key(
           f"{table}_user_id_fkey", table, "users", ["user_id"], ["id"], ondelete="CASCADE"
       )
   ```

8. Drop `credential_users` table:
   ```python
   op.drop_table("credential_users")
   ```

**Step 3: Write the downgrade function**

The downgrade should recreate `credential_users`, move data back, repoint FKs, remove added columns, and drop `linked_providers` and `recovery_codes`. This is the reverse of the upgrade.

**Step 4: Run the migration against test database**

Run: `uv run alembic -c api/alembic.ini upgrade head`
Expected: Migration completes without error

**Step 5: Commit**

```bash
git add api/alembic/versions/*_unify_user_tables.py
git commit -m "feat(db): add migration to unify user and credential_users tables"
```

---

### Task 2: Update SQLAlchemy models to match unified schema

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Test: `api/tests/test_models.py` (if exists, or verify with existing tests)

**Step 1: Write a test that the unified User model has all required columns**

Create or add to `api/tests/db/test_unified_user_model.py`:

```python
"""Tests for unified User model."""
import pytest
from sqlalchemy import inspect

from margin_api.db.models import User, LinkedProvider, RecoveryCode


def test_user_has_credential_columns():
    """Unified User model has nullable credential fields."""
    mapper = inspect(User)
    columns = {c.key for c in mapper.columns}
    assert "password_hash" in columns
    assert "mfa_enabled" in columns
    assert "mfa_grace_deadline" in columns
    assert "failed_login_attempts" in columns
    assert "locked_until" in columns
    assert "last_totp_counter" in columns
    assert "password_changed_at" in columns


def test_user_has_oauth_columns():
    """Unified User model retains OAuth fields as nullable."""
    mapper = inspect(User)
    columns = {c.key: c for c in mapper.columns}
    assert columns["oauth_id"].nullable is True
    assert columns["name"].nullable is True


def test_linked_provider_model_exists():
    """LinkedProvider model is defined with correct table name."""
    assert LinkedProvider.__tablename__ == "linked_providers"
    mapper = inspect(LinkedProvider)
    columns = {c.key for c in mapper.columns}
    assert "user_id" in columns
    assert "provider" in columns
    assert "oauth_id" in columns


def test_recovery_code_model_exists():
    """RecoveryCode model is defined with correct table name."""
    assert RecoveryCode.__tablename__ == "recovery_codes"
    mapper = inspect(RecoveryCode)
    columns = {c.key for c in mapper.columns}
    assert "user_id" in columns
    assert "code_hash" in columns
    assert "used" in columns
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/db/test_unified_user_model.py -v`
Expected: FAIL — `LinkedProvider` and `RecoveryCode` don't exist, `User` missing credential columns

**Step 3: Update the User model**

In `api/src/margin_api/db/models.py`, replace the current `User` class (lines ~140–162) with the unified version. Add nullable credential fields. Make `oauth_id`, `name`, `provider` nullable. Add relationships for `linked_providers`, `recovery_codes`, `totp_secrets`, `webauthn_credentials`, `challenge_tokens`.

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # OAuth fields (nullable — absent for credential-only users)
    oauth_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)

    # Credential fields (nullable — absent for OAuth-only users)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    mfa_grace_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_totp_counter: Mapped[int | None] = mapped_column(nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Billing
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    subscription_plan: Mapped[str] = mapped_column(String(20), default="analyst")
    subscription_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Avatars
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    oauth_avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    linked_providers: Mapped[list["LinkedProvider"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")
    totp_secrets: Mapped[list["TotpSecret"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    webauthn_credentials: Mapped[list["WebAuthnCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    challenge_tokens: Mapped[list["MfaChallengeToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    recovery_codes: Mapped[list["RecoveryCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    @property
    def auth_methods(self) -> list[str]:
        methods = []
        if self.has_password:
            methods.append("credentials")
        if self.linked_providers:
            methods.extend(lp.provider for lp in self.linked_providers)
        return methods
```

**Step 4: Add LinkedProvider model**

```python
class LinkedProvider(Base):
    __tablename__ = "linked_providers"
    __table_args__ = (
        UniqueConstraint("provider", "oauth_id", name="uq_linked_providers_provider_oauth_id"),
        UniqueConstraint("user_id", "provider", name="uq_linked_providers_user_id_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(50))
    oauth_id: Mapped[str] = mapped_column(String(255))
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped["User"] = relationship(back_populates="linked_providers")
```

**Step 5: Add RecoveryCode model**

```python
class RecoveryCode(Base):
    __tablename__ = "recovery_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    code_hash: Mapped[str] = mapped_column(Text)
    used: Mapped[bool] = mapped_column(default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped["User"] = relationship(back_populates="recovery_codes")
```

**Step 6: Remove CredentialUser class**

Delete the `CredentialUser` class entirely. Update `TotpSecret`, `WebAuthnCredential`, and `MfaChallengeToken` to FK to `User` instead of `CredentialUser`. Remove the old `provider` column from `User` (providers are now in `linked_providers`).

**Step 7: Update all imports**

Search the codebase for `CredentialUser` imports and replace with `User`. Key files:
- `api/src/margin_api/routes/auth.py`
- `api/src/margin_api/services/auth.py`
- `api/src/margin_api/services/totp.py`
- `api/src/margin_api/services/webauthn.py`
- `api/src/margin_api/routes/dashboard.py` (if it queries users)
- All test files that reference `CredentialUser`

**Step 8: Run test to verify it passes**

Run: `uv run pytest api/tests/db/test_unified_user_model.py -v`
Expected: PASS

**Step 9: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/db/test_unified_user_model.py
git commit -m "feat(db): unify User and CredentialUser into single model"
```

---

### Task 3: Update AuthService for unified User model

**Files:**
- Modify: `api/src/margin_api/services/auth.py`
- Modify: `api/tests/` — all auth service tests
- Reference: `api/src/margin_api/db/models.py`

**Step 1: Update existing auth service tests to use User instead of CredentialUser**

Find all tests in `api/tests/` that create `CredentialUser` fixtures and change them to `User` with `password_hash` set. The key queries change from `select(CredentialUser).where(CredentialUser.username == ...)` to `select(User).where(User.email == ...)`.

**Step 2: Write a test for the new `register_user` that sets `mfa_grace_deadline`**

```python
async def test_register_user_sets_mfa_grace_deadline(db_session):
    """New credential users get a 72-hour MFA grace deadline."""
    service = AuthService()
    user = await service.register_user(db_session, "test@example.com", "test@example.com", "ValidPass123!")
    assert user.mfa_grace_deadline is not None
    expected = user.created_at + timedelta(hours=72)
    assert abs((user.mfa_grace_deadline - expected).total_seconds()) < 5
```

**Step 3: Run test to verify it fails**

Run: `uv run pytest api/tests/ -k "test_register_user_sets_mfa_grace_deadline" -v`
Expected: FAIL

**Step 4: Update `AuthService.register_user`**

Change the method to:
- Query `User` instead of `CredentialUser`
- Check uniqueness on `email` only (drop separate `username` check — `username` column no longer exists)
- Set `mfa_grace_deadline = datetime.now(UTC) + timedelta(hours=72)` on creation

```python
async def register_user(
    self, session: AsyncSession, username: str, email: str, password: str
) -> User:
    _validate_password(password)

    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    user = User(
        email=email,
        name=username,
        password_hash=_hasher.hash(password),
        mfa_grace_deadline=datetime.now(UTC) + timedelta(hours=72),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
```

**Step 5: Update `AuthService.verify_credentials`**

Change to query by `User.email` where `User.password_hash IS NOT NULL`. The rest of the lockout/rehash logic stays the same but references `User` columns.

**Step 6: Update `AuthService.change_password` and `verify_challenge_token`**

Same pattern: replace `CredentialUser` with `User` in all queries.

**Step 7: Run all auth service tests**

Run: `uv run pytest api/tests/ -k "auth" -v`
Expected: PASS (all existing tests updated + new grace deadline test)

**Step 8: Commit**

```bash
git add api/src/margin_api/services/auth.py api/tests/
git commit -m "feat(auth): update AuthService for unified User model"
```

---

### Task 4: Update TotpService for unified User model

**Files:**
- Modify: `api/src/margin_api/services/totp.py`
- Modify: related tests

**Step 1: Replace all `CredentialUser` references with `User`**

In `totp.py`, the `confirm_totp` method queries `CredentialUser` to set `mfa_enabled = True`. Change to query `User`.

**Step 2: Run existing TOTP tests**

Run: `uv run pytest api/tests/ -k "totp" -v`
Expected: PASS after model swap

**Step 3: Commit**

```bash
git add api/src/margin_api/services/totp.py api/tests/
git commit -m "refactor(auth): update TotpService for unified User model"
```

---

### Task 5: Update auth routes for unified User model

**Files:**
- Modify: `api/src/margin_api/routes/auth.py`
- Modify: `api/src/margin_api/schemas/auth.py`
- Modify: related test files

**Step 1: Update all route handlers**

Replace `CredentialUser` imports/queries with `User` across all route handlers in `auth.py`. The `/oauth-sync` endpoint needs the most change: instead of upserting into the old `users` table, it now upserts into the unified `users` table AND creates/updates a `linked_providers` row.

Update `/oauth-sync`:
```python
@router.post("/oauth-sync", response_model=OAuthSyncResponse)
async def oauth_sync(request: OAuthSyncRequest, session: AsyncSession = Depends(get_session)):
    # Find by email first (may already exist as credential user)
    result = await session.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=request.email,
            name=request.name,
            oauth_avatar_url=request.avatar_url,
        )
        session.add(user)
        await session.flush()

    # Upsert linked provider
    lp_result = await session.execute(
        select(LinkedProvider).where(
            LinkedProvider.user_id == user.id,
            LinkedProvider.provider == request.provider,
        )
    )
    lp = lp_result.scalar_one_or_none()
    if lp is None:
        lp = LinkedProvider(
            user_id=user.id,
            provider=request.provider,
            oauth_id=request.oauth_id,
            provider_email=request.email,
        )
        session.add(lp)

    if request.avatar_url:
        user.oauth_avatar_url = request.avatar_url
    if request.name and not user.name:
        user.name = request.name

    await session.commit()
    await session.refresh(user)
    return OAuthSyncResponse(id=user.id, subscription_plan=user.subscription_plan)
```

Note: `OAuthSyncRequest` needs a new field `oauth_id: str` to populate `linked_providers.oauth_id`.

**Step 2: Update schemas**

Add `oauth_id` to `OAuthSyncRequest`:
```python
class OAuthSyncRequest(BaseModel):
    email: str = Field(max_length=320)
    name: str = Field(max_length=255)
    provider: str = Field(max_length=50)
    oauth_id: str = Field(max_length=255)
    avatar_url: str | None = None
```

**Step 3: Update `/session-check/{user_id}`**

Change to query `User` instead of `CredentialUser`.

**Step 4: Run all auth route tests**

Run: `uv run pytest api/tests/ -k "auth" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/auth.py api/src/margin_api/schemas/auth.py api/tests/
git commit -m "feat(auth): update auth routes and schemas for unified User model"
```

---

### Task 6: Fix all remaining CredentialUser references across the codebase

**Files:**
- Search: entire `api/` directory for `CredentialUser` or `credential_users`

**Step 1: Search for remaining references**

Run: `grep -r "CredentialUser\|credential_users" api/src/ api/tests/ --include="*.py" -l`

Fix every file found. Common locations:
- `api/src/margin_api/routes/dashboard.py`
- `api/src/margin_api/services/billing.py`
- `api/src/margin_api/services/storage.py`
- Various test fixtures and factories

**Step 2: Run full API test suite**

Run: `uv run pytest api/tests/ -v`
Expected: All 294+ tests PASS (some may need fixture updates)

**Step 3: Commit**

```bash
git add api/
git commit -m "refactor(api): remove all CredentialUser references"
```

---

## Phase 2: Recovery Code Service

### Task 7: Create RecoveryCodeService

**Files:**
- Create: `api/src/margin_api/services/recovery_codes.py`
- Create: `api/tests/services/test_recovery_codes.py`
- Reference: `api/src/margin_api/db/models.py` (RecoveryCode model)

**Step 1: Write failing tests**

```python
"""Tests for RecoveryCodeService."""
import pytest
from margin_api.services.recovery_codes import RecoveryCodeService


@pytest.fixture
def service():
    return RecoveryCodeService()


class TestGenerateCodes:
    async def test_generates_eight_codes(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        assert len(codes) == 8

    async def test_codes_match_format(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        import re
        for code in codes:
            assert re.match(r"^[a-z0-9]{4}-[a-z0-9]{4}$", code)

    async def test_no_ambiguous_characters(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        ambiguous = set("0oO1lI")
        for code in codes:
            assert not ambiguous.intersection(code.replace("-", ""))

    async def test_codes_stored_hashed(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        from sqlalchemy import select
        from margin_api.db.models import RecoveryCode
        result = await db_session.execute(
            select(RecoveryCode).where(RecoveryCode.user_id == credential_user.id)
        )
        stored = result.scalars().all()
        assert len(stored) == 8
        # Stored hashes should NOT match plaintext codes
        for rc in stored:
            assert rc.code_hash not in codes

    async def test_regenerate_deletes_old_codes(self, service, db_session, credential_user):
        first = await service.generate_codes(db_session, credential_user.id)
        second = await service.generate_codes(db_session, credential_user.id)
        assert set(first) != set(second)
        from sqlalchemy import select, func
        from margin_api.db.models import RecoveryCode
        result = await db_session.execute(
            select(func.count()).where(RecoveryCode.user_id == credential_user.id)
        )
        assert result.scalar() == 8  # Only second batch


class TestVerifyCode:
    async def test_valid_code_returns_true(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        result = await service.verify_code(db_session, credential_user.id, codes[0])
        assert result is True

    async def test_code_marked_used_after_verification(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        await service.verify_code(db_session, credential_user.id, codes[0])
        result = await service.verify_code(db_session, credential_user.id, codes[0])
        assert result is False

    async def test_code_works_without_hyphen(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        no_hyphen = codes[0].replace("-", "")
        result = await service.verify_code(db_session, credential_user.id, no_hyphen)
        assert result is True

    async def test_invalid_code_returns_false(self, service, db_session, credential_user):
        await service.generate_codes(db_session, credential_user.id)
        result = await service.verify_code(db_session, credential_user.id, "xxxx-xxxx")
        assert result is False


class TestRemainingCount:
    async def test_returns_count_of_unused_codes(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        assert await service.remaining_count(db_session, credential_user.id) == 8
        await service.verify_code(db_session, credential_user.id, codes[0])
        assert await service.remaining_count(db_session, credential_user.id) == 7
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/services/test_recovery_codes.py -v`
Expected: FAIL — module does not exist

**Step 3: Implement RecoveryCodeService**

```python
"""Recovery code generation, storage, and verification."""
import secrets
import string
from datetime import UTC, datetime

import bcrypt
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import RecoveryCode

# Exclude ambiguous characters: 0, O, o, 1, l, I
_ALPHABET = "".join(c for c in string.ascii_lowercase + string.digits if c not in "0o1l")


class RecoveryCodeService:
    def _generate_raw_code(self) -> str:
        """Generate one 8-character code in xxxx-xxxx format."""
        chars = "".join(secrets.choice(_ALPHABET) for _ in range(8))
        return f"{chars[:4]}-{chars[4:]}"

    def _hash_code(self, code: str) -> str:
        """Hash a recovery code with bcrypt."""
        normalized = code.replace("-", "")
        return bcrypt.hashpw(normalized.encode(), bcrypt.gensalt()).decode()

    def _check_code(self, code: str, hashed: str) -> bool:
        """Verify a recovery code against its bcrypt hash."""
        normalized = code.replace("-", "")
        return bcrypt.checkpw(normalized.encode(), hashed.encode())

    async def generate_codes(self, session: AsyncSession, user_id: int) -> list[str]:
        """Generate 8 new recovery codes, replacing any existing ones."""
        # Delete existing codes
        await session.execute(
            delete(RecoveryCode).where(RecoveryCode.user_id == user_id)
        )

        codes: list[str] = []
        for _ in range(8):
            raw = self._generate_raw_code()
            codes.append(raw)
            session.add(RecoveryCode(
                user_id=user_id,
                code_hash=self._hash_code(raw),
            ))

        await session.commit()
        return codes

    async def verify_code(self, session: AsyncSession, user_id: int, code: str) -> bool:
        """Verify a recovery code. Marks it as used if valid."""
        result = await session.execute(
            select(RecoveryCode).where(
                RecoveryCode.user_id == user_id,
                RecoveryCode.used == False,  # noqa: E712
            )
        )
        unused = result.scalars().all()

        for rc in unused:
            if self._check_code(code, rc.code_hash):
                rc.used = True
                rc.used_at = datetime.now(UTC)
                await session.commit()
                return True
        return False

    async def remaining_count(self, session: AsyncSession, user_id: int) -> int:
        """Return count of unused recovery codes."""
        result = await session.execute(
            select(func.count()).select_from(RecoveryCode).where(
                RecoveryCode.user_id == user_id,
                RecoveryCode.used == False,  # noqa: E712
            )
        )
        return result.scalar() or 0
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/services/test_recovery_codes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/recovery_codes.py api/tests/services/test_recovery_codes.py
git commit -m "feat(auth): add RecoveryCodeService with generation, verification, and counting"
```

---

## Phase 3: MFA Enforcement Middleware

### Task 8: Create @require_mfa decorator

**Files:**
- Create: `api/src/margin_api/middleware/mfa_enforcement.py`
- Create: `api/tests/middleware/test_mfa_enforcement.py`

**Step 1: Write failing tests**

```python
"""Tests for MFA enforcement middleware."""
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from margin_api.middleware.mfa_enforcement import check_mfa_requirement


class TestCheckMfaRequirement:
    async def test_oauth_only_user_passes(self):
        """OAuth-only users (no password) are never blocked."""
        user = MagicMock(password_hash=None, mfa_enabled=False, mfa_grace_deadline=None)
        # Should not raise
        await check_mfa_requirement(user)

    async def test_credential_user_mfa_enabled_passes(self):
        """Credential user with MFA enabled passes."""
        user = MagicMock(password_hash="hash", mfa_enabled=True, mfa_grace_deadline=None)
        await check_mfa_requirement(user)

    async def test_credential_user_within_grace_period_passes(self):
        """Credential user without MFA but within grace period passes."""
        user = MagicMock(
            password_hash="hash",
            mfa_enabled=False,
            mfa_grace_deadline=datetime.now(UTC) + timedelta(hours=24),
        )
        await check_mfa_requirement(user)

    async def test_credential_user_past_grace_period_blocked(self):
        """Credential user without MFA past grace period is blocked."""
        user = MagicMock(
            password_hash="hash",
            mfa_enabled=False,
            mfa_grace_deadline=datetime.now(UTC) - timedelta(hours=1),
        )
        with pytest.raises(HTTPException) as exc_info:
            await check_mfa_requirement(user)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"] == "mfa_required"

    async def test_credential_user_no_grace_deadline_blocked(self):
        """Credential user with no grace deadline and no MFA is blocked."""
        user = MagicMock(
            password_hash="hash",
            mfa_enabled=False,
            mfa_grace_deadline=None,
        )
        with pytest.raises(HTTPException) as exc_info:
            await check_mfa_requirement(user)
        assert exc_info.value.status_code == 403
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/middleware/test_mfa_enforcement.py -v`
Expected: FAIL — module does not exist

**Step 3: Implement the middleware**

```python
"""MFA enforcement for sensitive endpoints."""
from datetime import UTC, datetime

from fastapi import HTTPException

from margin_api.db.models import User


async def check_mfa_requirement(user: User) -> None:
    """Raise 403 if the user has a password but has not set up MFA and grace period expired.

    Rules:
    1. No password (OAuth-only) -> pass
    2. Password + mfa_enabled -> pass
    3. Password + !mfa_enabled + grace_deadline in future -> pass
    4. Password + !mfa_enabled + grace_deadline expired or null -> block
    """
    if not user.has_password:
        return

    if user.mfa_enabled:
        return

    if user.mfa_grace_deadline and user.mfa_grace_deadline > datetime.now(UTC):
        return

    raise HTTPException(
        status_code=403,
        detail={
            "error": "mfa_required",
            "message": "Multi-factor authentication must be enabled to perform this action.",
        },
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/middleware/test_mfa_enforcement.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/middleware/mfa_enforcement.py api/tests/middleware/test_mfa_enforcement.py
git commit -m "feat(auth): add MFA enforcement check for sensitive endpoints"
```

---

### Task 9: Apply @require_mfa to sensitive endpoints

**Files:**
- Modify: `api/src/margin_api/routes/auth.py` (change-password)
- Modify: `api/src/margin_api/routes/keys.py` (API key management)
- Modify: `api/src/margin_api/routes/billing.py` (billing changes)
- Modify: Any other routes handling sensitive actions

**Step 1: Write integration tests**

Test that a credential user past their grace period gets 403 on sensitive endpoints. Test that OAuth users and MFA-enabled users get 200.

**Step 2: Add the check as a FastAPI dependency**

Create a reusable dependency:

```python
# In api/src/margin_api/middleware/mfa_enforcement.py, add:
from fastapi import Depends
from margin_api.db.session import get_session

async def require_mfa(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> User:
    """FastAPI dependency that loads user and checks MFA requirement."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await check_mfa_requirement(user)
    return user
```

Add `Depends(require_mfa)` to each sensitive route handler.

**Step 3: Run affected route tests**

Run: `uv run pytest api/tests/ -k "keys or billing or change_password" -v`
Expected: PASS

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/ api/src/margin_api/middleware/ api/tests/
git commit -m "feat(auth): apply MFA enforcement to sensitive endpoints"
```

---

## Phase 4: New Auth Endpoints

### Task 10: Add recovery code endpoints

**Files:**
- Modify: `api/src/margin_api/routes/auth.py`
- Modify: `api/src/margin_api/schemas/auth.py`
- Create: `api/tests/routes/test_recovery_code_routes.py`

**Step 1: Write failing route tests**

```python
"""Tests for recovery code routes."""

class TestVerifyRecoveryCode:
    async def test_valid_code_returns_mfa_token(self, client, user_with_mfa):
        """POST /auth/mfa/verify-recovery with valid code returns mfa_token."""
        resp = await client.post("/api/v1/auth/mfa/verify-recovery", json={
            "user_id": user_with_mfa.id,
            "code": user_with_mfa.recovery_codes[0],
            "challenge_token": user_with_mfa.challenge_token,
        })
        assert resp.status_code == 200
        assert resp.json()["mfa_token"] is not None

    async def test_invalid_code_returns_401(self, client, user_with_mfa):
        resp = await client.post("/api/v1/auth/mfa/verify-recovery", json={
            "user_id": user_with_mfa.id,
            "code": "xxxx-xxxx",
            "challenge_token": user_with_mfa.challenge_token,
        })
        assert resp.status_code == 401


class TestRegenerateRecoveryCodes:
    async def test_returns_eight_new_codes(self, authed_client, user_with_mfa):
        """POST /auth/mfa/regenerate-recovery-codes returns 8 new codes."""
        resp = await authed_client.post("/api/v1/auth/mfa/regenerate-recovery-codes", json={
            "current_password": "ValidPass123!",
        })
        assert resp.status_code == 200
        assert len(resp.json()["codes"]) == 8

    async def test_requires_valid_password(self, authed_client, user_with_mfa):
        resp = await authed_client.post("/api/v1/auth/mfa/regenerate-recovery-codes", json={
            "current_password": "WrongPassword123!",
        })
        assert resp.status_code == 403
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/routes/test_recovery_code_routes.py -v`
Expected: FAIL

**Step 3: Add schemas**

```python
class VerifyRecoveryCodeRequest(BaseModel):
    user_id: int
    code: str = Field(min_length=8, max_length=9)  # with or without hyphen
    challenge_token: str

class RegenerateRecoveryCodesRequest(BaseModel):
    current_password: str

class RegenerateRecoveryCodesResponse(BaseModel):
    codes: list[str]
```

**Step 4: Add route handlers**

```python
@router.post("/mfa/verify-recovery", response_model=MfaVerifyResponse)
async def verify_recovery_code(
    request: VerifyRecoveryCodeRequest,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(_get_auth_service),
    recovery_service: RecoveryCodeService = Depends(_get_recovery_service),
):
    valid_challenge = await auth_service.verify_challenge_token(
        session, request.user_id, request.challenge_token
    )
    if not valid_challenge:
        raise HTTPException(status_code=401, detail="Invalid or expired challenge token")

    verified = await recovery_service.verify_code(session, request.user_id, request.code)
    if not verified:
        raise HTTPException(status_code=401, detail="Invalid recovery code")

    mfa_token = secrets.token_hex(32)
    return MfaVerifyResponse(verified=True, mfa_token=mfa_token)


@router.post("/mfa/regenerate-recovery-codes", response_model=RegenerateRecoveryCodesResponse)
async def regenerate_recovery_codes(
    request: RegenerateRecoveryCodesRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(_get_auth_service),
    recovery_service: RecoveryCodeService = Depends(_get_recovery_service),
):
    user = await session.get(User, user_id)
    if not user or not user.has_password:
        raise HTTPException(status_code=404)
    try:
        _hasher.verify(user.password_hash, request.current_password)
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid password")

    codes = await recovery_service.generate_codes(session, user_id)
    return RegenerateRecoveryCodesResponse(codes=codes)
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest api/tests/routes/test_recovery_code_routes.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/auth.py api/src/margin_api/schemas/auth.py api/tests/routes/test_recovery_code_routes.py
git commit -m "feat(auth): add recovery code verify and regenerate endpoints"
```

---

### Task 11: Add MFA disable endpoint

**Files:**
- Modify: `api/src/margin_api/routes/auth.py`
- Modify: `api/src/margin_api/schemas/auth.py`
- Create: `api/tests/routes/test_mfa_disable_route.py`

**Step 1: Write failing tests**

```python
class TestDisableMfa:
    async def test_requires_password_and_totp(self, authed_client, user_with_mfa):
        """POST /auth/mfa/disable requires both password and TOTP code."""
        resp = await authed_client.post("/api/v1/auth/mfa/disable", json={
            "current_password": "ValidPass123!",
            "totp_code": "123456",  # valid TOTP from fixture
        })
        assert resp.status_code == 200
        assert resp.json()["mfa_disabled"] is True

    async def test_wrong_password_rejected(self, authed_client, user_with_mfa):
        resp = await authed_client.post("/api/v1/auth/mfa/disable", json={
            "current_password": "WrongPass123!",
            "totp_code": "123456",
        })
        assert resp.status_code == 403

    async def test_sets_new_grace_deadline(self, authed_client, user_with_mfa, db_session):
        """After disabling, a 72h grace period starts."""
        await authed_client.post("/api/v1/auth/mfa/disable", json={
            "current_password": "ValidPass123!",
            "totp_code": "123456",
        })
        await db_session.refresh(user_with_mfa)
        assert user_with_mfa.mfa_enabled is False
        assert user_with_mfa.mfa_grace_deadline is not None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/routes/test_mfa_disable_route.py -v`
Expected: FAIL

**Step 3: Add schema and route**

```python
class DisableMfaRequest(BaseModel):
    current_password: str
    totp_code: str = Field(min_length=6, max_length=6)

class DisableMfaResponse(BaseModel):
    mfa_disabled: bool
```

Route handler: verify password, verify TOTP code, then delete `totp_secrets` + `recovery_codes`, set `mfa_enabled = False`, set `mfa_grace_deadline = now() + 72h`.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/routes/test_mfa_disable_route.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/auth.py api/src/margin_api/schemas/auth.py api/tests/routes/
git commit -m "feat(auth): add MFA disable endpoint with password + TOTP verification"
```

---

### Task 12: Add provider linking endpoints

**Files:**
- Modify: `api/src/margin_api/routes/auth.py`
- Modify: `api/src/margin_api/schemas/auth.py`
- Create: `api/tests/routes/test_provider_linking_routes.py`

**Step 1: Write failing tests**

Cover:
- `POST /auth/link-provider` — links OAuth provider to existing user, returns 200
- `POST /auth/link-provider` — duplicate `(provider, oauth_id)` returns 409
- `DELETE /auth/unlink-provider/{provider}` — removes linked provider
- `DELETE /auth/unlink-provider/{provider}` — blocked if only auth method (no password)
- `POST /auth/set-password` — OAuth user sets a password, triggers MFA grace deadline
- `POST /auth/remove-password` — removes password, clears MFA state

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/routes/test_provider_linking_routes.py -v`

**Step 3: Add schemas**

```python
class LinkProviderRequest(BaseModel):
    provider: str = Field(max_length=50)
    oauth_id: str = Field(max_length=255)
    provider_email: str | None = None

class LinkProviderResponse(BaseModel):
    linked: bool
    provider: str

class SetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=12)

class RemovePasswordRequest(BaseModel):
    current_password: str
```

**Step 4: Implement route handlers**

Key logic for each:

`POST /auth/link-provider`:
- Lookup user by `get_current_user_id`
- Check `UNIQUE(provider, oauth_id)` — catch `IntegrityError` → 409
- Insert `LinkedProvider` row

`DELETE /auth/unlink-provider/{provider}`:
- Lookup user, count remaining auth methods
- If only method (no password, only this provider) → 403 with message
- If has password but no MFA and grace expired → 403 with message
- Otherwise delete the `linked_providers` row

`POST /auth/set-password`:
- Validate password rules
- Set `password_hash`, `mfa_grace_deadline = now() + 72h`

`POST /auth/remove-password`:
- Verify current password
- Check user has at least one linked provider
- Null out `password_hash`, `mfa_enabled`, delete `totp_secrets`, `recovery_codes`, clear `mfa_grace_deadline`

**Step 5: Run tests to verify they pass**

Run: `uv run pytest api/tests/routes/test_provider_linking_routes.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/auth.py api/src/margin_api/schemas/auth.py api/tests/routes/
git commit -m "feat(auth): add provider linking, set-password, and remove-password endpoints"
```

---

### Task 13: Add user security status endpoint

**Files:**
- Modify: `api/src/margin_api/routes/auth.py`
- Modify: `api/src/margin_api/schemas/auth.py`

**Step 1: Write failing test**

```python
async def test_security_status_returns_full_state(self, authed_client, user_with_mfa):
    """GET /auth/security-status returns auth methods, MFA state, providers."""
    resp = await authed_client.get("/api/v1/auth/security-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "has_password" in data
    assert "mfa_enabled" in data
    assert "linked_providers" in data
    assert "mfa_grace_deadline" in data
    assert "recovery_codes_remaining" in data
```

**Step 2: Implement the endpoint**

```python
class SecurityStatusResponse(BaseModel):
    has_password: bool
    mfa_enabled: bool
    mfa_method: str | None  # "totp", "webauthn", None
    mfa_grace_deadline: datetime | None
    recovery_codes_remaining: int
    linked_providers: list[ProviderInfo]

class ProviderInfo(BaseModel):
    provider: str
    provider_email: str | None
    linked_at: datetime

@router.get("/security-status", response_model=SecurityStatusResponse)
async def security_status(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    recovery_service: RecoveryCodeService = Depends(_get_recovery_service),
):
    user = await session.get(User, user_id, options=[selectinload(User.linked_providers)])
    if not user:
        raise HTTPException(status_code=404)

    mfa_method = None
    if user.mfa_enabled:
        # Check which method is active
        totp = await session.execute(
            select(TotpSecret).where(TotpSecret.user_id == user_id, TotpSecret.confirmed == True)
        )
        if totp.scalar_one_or_none():
            mfa_method = "totp"
        else:
            webauthn = await session.execute(
                select(WebAuthnCredential).where(WebAuthnCredential.user_id == user_id)
            )
            if webauthn.scalar_one_or_none():
                mfa_method = "webauthn"

    remaining = await recovery_service.remaining_count(session, user_id)

    return SecurityStatusResponse(
        has_password=user.has_password,
        mfa_enabled=user.mfa_enabled,
        mfa_method=mfa_method,
        mfa_grace_deadline=user.mfa_grace_deadline,
        recovery_codes_remaining=remaining,
        linked_providers=[
            ProviderInfo(
                provider=lp.provider,
                provider_email=lp.provider_email,
                linked_at=lp.linked_at,
            )
            for lp in user.linked_providers
        ],
    )
```

**Step 3: Run test, verify it passes**

Run: `uv run pytest api/tests/ -k "security_status" -v`
Expected: PASS

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/auth.py api/src/margin_api/schemas/auth.py api/tests/
git commit -m "feat(auth): add GET /security-status endpoint for account page"
```

---

### Task 14: Integrate recovery codes into TOTP confirmation flow

**Files:**
- Modify: `api/src/margin_api/routes/auth.py` — the `/mfa/confirm-totp` handler
- Modify: `api/src/margin_api/schemas/auth.py`

**Step 1: Write failing test**

```python
async def test_confirm_totp_returns_recovery_codes(self, client, user_with_totp_setup):
    """POST /mfa/confirm-totp returns 8 recovery codes on success."""
    resp = await client.post("/api/v1/auth/mfa/confirm-totp", json={
        "secret_id": user_with_totp_setup.secret_id,
        "code": user_with_totp_setup.valid_code,
    })
    assert resp.status_code == 200
    assert len(resp.json()["recovery_codes"]) == 8
```

**Step 2: Update the `/mfa/confirm-totp` handler**

After confirming TOTP, generate recovery codes and return them in the response. Update `ConfirmTotpResponse` schema to include `recovery_codes: list[str]`.

**Step 3: Run tests**

Run: `uv run pytest api/tests/ -k "confirm_totp" -v`
Expected: PASS

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/auth.py api/src/margin_api/schemas/auth.py api/tests/
git commit -m "feat(auth): return recovery codes on TOTP confirmation"
```

---

## Phase 5: Frontend — NextAuth + Session Updates

### Task 15: Update NextAuth configuration for unified model

**Files:**
- Modify: `web/src/lib/auth.ts`
- Reference: New `/auth/security-status` and `/auth/oauth-sync` endpoints

**Step 1: Update the OAuth sync call**

In the `signIn` callback for OAuth accounts, the `POST /api/v1/auth/oauth-sync` call now needs to include `oauth_id` from the provider account. Update the fetch body:

```typescript
const body = {
  email: user.email,
  name: user.name,
  provider: account.provider,
  oauth_id: account.providerAccountId,  // NEW — required for linked_providers
  avatar_url: user.image,
};
```

**Step 2: Update the JWT callback**

Add `linkedProviders` and `hasPassword` to the token. On first sign-in, fetch from `/auth/security-status` to populate:

```typescript
token.hasPassword = securityStatus.has_password;
token.mfaEnabled = securityStatus.mfa_enabled;
token.mfaGraceDeadline = securityStatus.mfa_grace_deadline;
token.linkedProviders = securityStatus.linked_providers.map(lp => lp.provider);
```

**Step 3: Update the session callback**

Expose new fields to the client:

```typescript
session.hasPassword = token.hasPassword;
session.mfaEnabled = token.mfaEnabled;
session.mfaGraceDeadline = token.mfaGraceDeadline;
session.linkedProviders = token.linkedProviders;
```

**Step 4: Update TypeScript types**

Extend the NextAuth session and JWT types in `web/src/lib/types.ts` or `web/src/types/next-auth.d.ts`:

```typescript
declare module "next-auth" {
  interface Session {
    userId: number;
    authMethod: "oauth" | "credentials";
    oauthProvider?: string;
    mfaVerified: boolean;
    hasPassword: boolean;
    mfaEnabled: boolean;
    mfaGraceDeadline: string | null;
    linkedProviders: string[];
    avatarUrl?: string;
    oauthAvatarUrl?: string;
  }
}
```

**Step 5: Run frontend tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npm test`
Expected: Existing tests pass (may need fixture updates for new session shape)

**Step 6: Commit**

```bash
git add web/src/lib/auth.ts web/src/types/ web/src/lib/types.ts
git commit -m "feat(web): update NextAuth config for unified user model and security status"
```

---

## Phase 6: Frontend — Security Section Rewrite

### Task 16: Create provider icon components

**Files:**
- Create: `web/src/components/account/provider-icons.tsx`
- Test: `web/src/components/account/__tests__/provider-icons.test.tsx`

**Step 1: Write component tests**

```typescript
import { render, screen } from "@testing-library/react";
import { ProviderIcons } from "../provider-icons";

describe("ProviderIcons", () => {
  it("shows Google as connected when user signed in with Google", () => {
    render(<ProviderIcons linkedProviders={["google"]} />);
    expect(screen.getByLabelText("Google — Connected")).toBeInTheDocument();
  });

  it("shows GitHub as not connected with Connect button", () => {
    render(<ProviderIcons linkedProviders={["google"]} />);
    expect(screen.getByLabelText("GitHub — Not connected")).toBeInTheDocument();
    expect(screen.getByLabelText("Connect GitHub account")).toBeInTheDocument();
  });

  it("shows Apple, Amazon, Facebook as coming soon", () => {
    render(<ProviderIcons linkedProviders={[]} />);
    expect(screen.getByLabelText("Apple — Coming soon")).toBeInTheDocument();
    expect(screen.getByLabelText("Amazon — Coming soon")).toBeInTheDocument();
    expect(screen.getByLabelText("Facebook — Coming soon")).toBeInTheDocument();
  });

  it("disables coming soon icons", () => {
    render(<ProviderIcons linkedProviders={[]} />);
    const apple = screen.getByLabelText("Apple — Coming soon");
    expect(apple).toHaveAttribute("aria-disabled", "true");
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/account/__tests__/provider-icons.test.tsx`

**Step 3: Implement the component**

Five provider entries: Google, GitHub (available), Apple, Amazon, Facebook (coming soon). Each rendered as an icon + label + optional button. Use SVG icons or provider logo images. Greyed-out icons use `opacity-40` and `cursor-not-allowed`. Connected icons get solid border + green "Connected" label. Available icons get dashed border + "Connect" button.

**Step 4: Run tests to verify they pass**

**Step 5: Commit**

```bash
git add web/src/components/account/provider-icons.tsx web/src/components/account/__tests__/
git commit -m "feat(web): add ProviderIcons component with connected/available/coming-soon states"
```

---

### Task 17: Create MFA status component

**Files:**
- Create: `web/src/components/account/mfa-status.tsx`
- Test: `web/src/components/account/__tests__/mfa-status.test.tsx`

**Step 1: Write component tests**

Cover all 5 MFA states from the design:
- State 1: OAuth-only, no password → "Managed by {Provider}"
- State 2: Has password, MFA not enabled → yellow dot + "Set Up MFA" button + grace period banner
- State 3: Has password, MFA enabled (TOTP) → green dot + "Regenerate" + "Remove MFA"
- State 5: Both OAuth and password, MFA not enabled → same as State 2

**Step 2: Run tests, verify fail**

**Step 3: Implement component**

Use `session.hasPassword`, `session.mfaEnabled`, `session.mfaGraceDeadline`, `session.linkedProviders` from the session to determine which state to render. Include the exact copy from the design doc. Status dots: 8px circles (`w-2 h-2 rounded-full`), green `bg-emerald-500`, yellow `bg-amber-500`. Grace period banner: amber left border, `role="alert"`.

**Step 4: Run tests, verify pass**

**Step 5: Commit**

```bash
git add web/src/components/account/mfa-status.tsx web/src/components/account/__tests__/
git commit -m "feat(web): add MfaStatus component with 5 states and grace period banner"
```

---

### Task 18: Create password management component

**Files:**
- Create: `web/src/components/account/password-section.tsx`
- Test: `web/src/components/account/__tests__/password-section.test.tsx`

**Step 1: Write component tests**

Cover:
- State A: No password → "Set Password" button, inline form on click
- State B: Has password → "Change Password" button, shows last changed time
- "Remove Password" button visible only when user has linked providers

**Step 2: Implement component**

Reuse the existing change-password form logic from the current `security-section.tsx`. Add the new "Set Password" form (new password + confirm) and "Remove Password" flow (password confirmation modal).

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add web/src/components/account/password-section.tsx web/src/components/account/__tests__/
git commit -m "feat(web): add PasswordSection with set/change/remove password flows"
```

---

### Task 19: Rewrite SecuritySection to compose new components

**Files:**
- Modify: `web/src/components/account/security-section.tsx`
- Test: `web/src/components/account/__tests__/security-section.test.tsx`

**Step 1: Write integration tests for the full section**

Cover AC-1 through AC-5 from the design doc: OAuth-only user, GitHub OAuth user, credential user without MFA, credential user with MFA, user with both.

**Step 2: Rewrite security-section.tsx**

Replace the current implementation with a composition of:
- `ProviderIcons` (Task 16)
- OAuth info copy block (conditional on `linkedProviders.length > 0 && !hasPassword`)
- `PasswordSection` (Task 18)
- `MfaStatus` (Task 17)

Layout: card with `space-y-6`, subsection headings in `text-sm font-medium text-text-secondary uppercase tracking-wide`, dividers between subsections.

**Step 3: Run all security section tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/account/__tests__/`

**Step 4: Commit**

```bash
git add web/src/components/account/security-section.tsx web/src/components/account/__tests__/
git commit -m "feat(web): rewrite SecuritySection with provider icons, password, and MFA subsections"
```

---

## Phase 7: Frontend — MFA Setup + Recovery Codes

### Task 20: Add recovery code display to MFA setup flow

**Files:**
- Modify: `web/src/app/mfa/setup/page.tsx`
- Create: `web/src/components/mfa/recovery-codes-display.tsx`
- Test: `web/src/components/mfa/__tests__/recovery-codes-display.test.tsx`

**Step 1: Write component tests for RecoveryCodesDisplay**

```typescript
describe("RecoveryCodesDisplay", () => {
  it("renders 8 codes in monospace", () => {
    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={jest.fn()} />);
    expect(screen.getAllByTestId("recovery-code")).toHaveLength(8);
  });

  it("disables Continue until checkbox is checked", () => {
    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={jest.fn()} />);
    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled();
  });

  it("enables Continue after checking the checkbox", async () => {
    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={jest.fn()} />);
    await userEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByRole("button", { name: /continue/i })).toBeEnabled();
  });

  it("copies codes to clipboard", async () => {
    render(<RecoveryCodesDisplay codes={mockCodes} onContinue={jest.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /copy/i }));
    // Assert clipboard was called
  });
});
```

**Step 2: Implement RecoveryCodesDisplay**

A standalone component that receives `codes: string[]` and `onContinue: () => void`. Shows heading, educational copy, monospace code grid, copy button, download button, checkbox, and Continue button.

**Step 3: Update MFA setup page**

After TOTP confirmation succeeds, the API now returns `recovery_codes` in the response. Add a new step `"recovery"` to the setup flow. After TOTP verify, transition to `"recovery"` step showing `RecoveryCodesDisplay`. On Continue, redirect to `/account` (not `/login` as it does today).

**Step 4: Run tests**

**Step 5: Commit**

```bash
git add web/src/app/mfa/setup/page.tsx web/src/components/mfa/
git commit -m "feat(web): add recovery codes display to MFA setup flow"
```

---

### Task 21: Add recovery code input to MFA verify page

**Files:**
- Modify: `web/src/app/mfa/verify/page.tsx`

**Step 1: Write test**

```typescript
it("shows recovery code input when 'Use a recovery code' is clicked", async () => {
  render(<MfaVerifyPage />);
  await userEvent.click(screen.getByText(/use a recovery code/i));
  expect(screen.getByLabelText("Recovery code")).toBeInTheDocument();
});
```

**Step 2: Add recovery code flow**

Below the TOTP input, add a link: "Lost your authenticator? Use a recovery code". On click, show a single input (label: "Recovery code", placeholder: "xxxx-xxxx") and "Verify" button. On submit, `POST /api/v1/auth/mfa/verify-recovery`. On success, complete sign-in the same way as TOTP verification.

Below the recovery code input, add: "Lost your recovery codes too? Contact support" linking to `/support?subject=MFA+recovery`.

**Step 3: Run tests**

**Step 4: Commit**

```bash
git add web/src/app/mfa/verify/page.tsx web/src/app/mfa/__tests__/
git commit -m "feat(web): add recovery code input to MFA verify page"
```

---

## Phase 8: Frontend — MFA Enforcement Banners

### Task 22: Create MFA enforcement banner component

**Files:**
- Create: `web/src/components/banners/mfa-enforcement-banner.tsx`
- Test: `web/src/components/banners/__tests__/mfa-enforcement-banner.test.tsx`

**Step 1: Write tests**

Cover:
- Phase 1 (0–24h): dismissible banner with "Set up now" link
- Phase 2 (24–72h): non-dismissible amber banner with countdown
- Not shown for OAuth-only users
- Not shown for users with MFA enabled

**Step 2: Implement component**

Read `session.hasPassword`, `session.mfaEnabled`, `session.mfaGraceDeadline`. Calculate which phase based on time remaining. Render appropriate banner variant. Phase 1 banner has dismiss button (state stored in `sessionStorage`). Phase 2 banner has no dismiss. Both have "Set up now" link to `/mfa/setup`.

**Step 3: Run tests**

**Step 4: Commit**

```bash
git add web/src/components/banners/
git commit -m "feat(web): add MFA enforcement banner with 3-phase timeline"
```

---

### Task 23: Add MFA enforcement banner to app layout

**Files:**
- Modify: `web/src/app/layout.tsx` or `web/src/components/app-shell.tsx` (whichever wraps all pages)

**Step 1: Import and render MfaEnforcementBanner**

Add the banner component inside the `AppShell` layout, above the main content area. It self-determines visibility based on session state.

**Step 2: Write test**

Verify the banner appears in the layout for a credential user without MFA.

**Step 3: Run tests**

**Step 4: Commit**

```bash
git add web/src/app/layout.tsx web/src/components/app-shell.tsx
git commit -m "feat(web): integrate MFA enforcement banner into app layout"
```

---

### Task 24: Add MFA-required blocking modal

**Files:**
- Create: `web/src/components/modals/mfa-required-modal.tsx`
- Modify: `web/src/lib/api-client.ts` — intercept 403 `mfa_required` responses

**Step 1: Write tests**

```typescript
describe("MFA required modal", () => {
  it("appears when API returns mfa_required error", () => { ... });
  it("has Set Up MFA button linking to /mfa/setup", () => { ... });
  it("has Go back link that dismisses the modal", () => { ... });
});
```

**Step 2: Implement modal**

A dialog component shown when the API client receives a 403 with `error: "mfa_required"`. Copy from design doc: "Multi-factor authentication is required to {action}. Set up MFA to continue."

**Step 3: Update API client**

In the fetch wrapper, add a response interceptor that checks for 403 + `mfa_required` and triggers the modal via a global state (React context or zustand store).

**Step 4: Run tests**

**Step 5: Commit**

```bash
git add web/src/components/modals/ web/src/lib/api-client.ts
git commit -m "feat(web): add MFA-required blocking modal with API response interceptor"
```

---

## Phase 9: Full Integration Test

### Task 25: Run complete test suites

**Step 1: Run engine tests (should be unaffected)**

Run: `uv run pytest engine/tests/ -v`
Expected: 784+ tests PASS

**Step 2: Run API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All tests PASS (existing + new)

**Step 3: Run frontend tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npm test`
Expected: All tests PASS

**Step 4: Manual smoke test**

- Start services: `docker compose up -d && uv run uvicorn margin_api.app:create_app --factory --reload`
- Start frontend: `cd web && npm run dev`
- Test OAuth login → verify Security section shows provider states correctly
- Test credential login → verify MFA enforcement flow
- Test recovery code generation and redemption

**Step 5: Commit any fixes from smoke testing**

```bash
git add -A && git commit -m "fix: address issues found in integration testing"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1–6 | Unified user model (migration, models, services, routes) |
| 2 | 7 | Recovery code service |
| 3 | 8–9 | MFA enforcement middleware |
| 4 | 10–14 | New auth endpoints (recovery, disable MFA, provider linking, status) |
| 5 | 15 | NextAuth + session updates |
| 6 | 16–19 | Security section frontend components |
| 7 | 20–21 | MFA setup + verify with recovery codes |
| 8 | 22–24 | MFA enforcement banners + blocking modal |
| 9 | 25 | Full integration test |

**Total: 25 tasks across 9 phases.**

Dependencies: Phase 1 → Phase 2/3/4 (all depend on unified model) → Phase 5 (depends on new endpoints) → Phase 6/7/8 (depend on session shape) → Phase 9 (integration).

Within phases, tasks are sequential. Across phases 2/3/4, tasks can run in parallel once Phase 1 is complete. Phases 6/7/8 can partially parallelize once Phase 5 is done.
