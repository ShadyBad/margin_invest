# Password Reset Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add email-based password reset using Resend, reusing the existing challenge token pattern.

**Architecture:** Two new unauthenticated API endpoints (forgot-password, reset-password) backed by the existing `MfaChallengeToken` table with 60-min TTL. New `EmailService` wrapping Resend SDK. Frontend adds "Forgot password?" inline form on login card and a new `/reset-password` page.

**Tech Stack:** Resend (email), existing Argon2id hashing, existing MfaChallengeToken, Next.js 15, FastAPI

---

### Task 1: Add Resend dependency

**Files:**
- Modify: `api/pyproject.toml:6-25`

**Step 1: Add resend to dependencies**

In `api/pyproject.toml`, add `"resend>=4.0.0"` to the dependencies list after line 24 (`"bcrypt>=5.0.0"`):

```toml
    "bcrypt>=5.0.0",
    "resend>=4.0.0",
```

**Step 2: Add config settings**

In `api/src/margin_api/config.py`, add after line 50 (`api_key_encryption_key`):

```python
    # Email (Resend)
    resend_api_key: str = ""
    app_url: str = "http://localhost:3000"
```

**Step 3: Sync dependencies**

Run: `uv sync`
Expected: Resend installed successfully

**Step 4: Commit**

```bash
git add api/pyproject.toml uv.lock api/src/margin_api/config.py
git commit -m "chore: add resend dependency and email config settings"
```

---

### Task 2: Create EmailService

**Files:**
- Create: `api/src/margin_api/services/email.py`
- Create: `api/tests/test_email_service.py`

**Step 1: Write the failing test**

Create `api/tests/test_email_service.py`:

```python
"""Tests for EmailService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from margin_api.services.email import EmailService


class TestEmailService:
    def test_send_password_reset_calls_resend(self):
        """EmailService calls Resend API with correct params."""
        mock_client = MagicMock()
        service = EmailService(client=mock_client)

        service.send_password_reset(
            to_email="user@example.com",
            reset_url="https://app.test/reset-password?token=abc123",
        )

        mock_client.emails.send.assert_called_once()
        call_args = mock_client.emails.send.call_args[0][0]
        assert call_args["to"] == "user@example.com"
        assert "Reset" in call_args["subject"]
        assert "abc123" in call_args["html"]

    def test_send_password_reset_returns_false_on_error(self):
        """EmailService returns False when Resend raises."""
        mock_client = MagicMock()
        mock_client.emails.send.side_effect = Exception("API error")
        service = EmailService(client=mock_client)

        result = service.send_password_reset(
            to_email="user@example.com",
            reset_url="https://app.test/reset-password?token=abc123",
        )

        assert result is False

    def test_dev_mode_logs_url_when_no_api_key(self):
        """When no API key, logs the URL instead of sending."""
        service = EmailService(api_key="")

        # Should not raise even though there's no real client
        result = service.send_password_reset(
            to_email="user@example.com",
            reset_url="https://app.test/reset-password?token=abc123",
        )

        assert result is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_email_service.py -v`
Expected: FAIL (module not found)

**Step 3: Write the implementation**

Create `api/src/margin_api/services/email.py`:

```python
"""Email service for transactional emails via Resend."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Sends transactional emails. Uses Resend in production, logs in dev."""

    def __init__(self, *, api_key: str | None = None, client: object | None = None):
        if client is not None:
            self._client = client
            self._dev_mode = False
        elif api_key:
            import resend

            resend.api_key = api_key
            self._client = resend.Emails  # type: ignore[assignment]
            self._dev_mode = False
        else:
            self._client = None
            self._dev_mode = True

    def send_password_reset(self, to_email: str, reset_url: str) -> bool:
        """Send password reset email. Returns True on success."""
        if self._dev_mode:
            logger.info("[dev] Password reset link for %s: %s", to_email, reset_url)
            return True

        try:
            self._client.emails.send(  # type: ignore[union-attr]
                {
                    "from": "Margin Invest <noreply@margin-invest.app>",
                    "to": to_email,
                    "subject": "Reset your Margin Invest password",
                    "html": (
                        "<h2>Reset your password</h2>"
                        f'<p><a href="{reset_url}">Click here to reset your password</a></p>'
                        "<p>This link expires in 1 hour.</p>"
                        "<p>If you didn't request this, ignore this email.</p>"
                    ),
                }
            )
            return True
        except Exception:
            logger.exception("Failed to send password reset email to %s", to_email)
            return False
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_email_service.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add api/src/margin_api/services/email.py api/tests/test_email_service.py
git commit -m "feat(api): add EmailService for password reset emails via Resend"
```

---

### Task 3: Add reset_password method to AuthService

**Files:**
- Modify: `api/src/margin_api/services/auth.py:131-198`
- Create: `api/tests/test_password_reset_service.py`

**Step 1: Write the failing tests**

Create `api/tests/test_password_reset_service.py`:

```python
"""Tests for AuthService password reset methods."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import MfaChallengeToken, User
from margin_api.services.auth import AuthService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_auth = AuthService()


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        user = await _auth.register_user(
            session, "testuser", "test@example.com", "OldPassword1!"
        )

    yield factory, user.id
    await engine.dispose()


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_creates_token_with_60min_ttl(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)
            assert len(raw_token) == 64  # 32 bytes hex

            # Token should exist in DB
            tokens = (
                await session.execute(
                    select(MfaChallengeToken).where(
                        MfaChallengeToken.user_id == user_id
                    )
                )
            ).scalars().all()
            assert len(tokens) >= 1

    @pytest.mark.asyncio
    async def test_reset_password_success(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            await _auth.reset_password(session, user_id, raw_token, "NewPassword2@")

        # Verify new password works
        async with factory() as session:
            result = await _auth.verify_credentials(
                session, "test@example.com", "NewPassword2@"
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_reset_password_sets_changed_at(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            await _auth.reset_password(session, user_id, raw_token, "NewPassword2@")

        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert user.password_changed_at is not None

    @pytest.mark.asyncio
    async def test_reset_password_clears_lockout(self, db):
        factory, user_id = db
        # Lock the account with failed attempts
        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            user.failed_login_attempts = 5
            await session.commit()

        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            await _auth.reset_password(session, user_id, raw_token, "NewPassword2@")

        async with factory() as session:
            user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert user.failed_login_attempts == 0
            assert user.locked_until is None

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, db):
        factory, user_id = db
        async with factory() as session:
            with pytest.raises(LookupError, match="Invalid or expired"):
                await _auth.reset_password(session, user_id, "badtoken", "NewPassword2@")

    @pytest.mark.asyncio
    async def test_reset_password_token_single_use(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            await _auth.reset_password(session, user_id, raw_token, "NewPassword2@")

        async with factory() as session:
            with pytest.raises(LookupError, match="Invalid or expired"):
                await _auth.reset_password(session, user_id, raw_token, "AnotherPass3#")

    @pytest.mark.asyncio
    async def test_reset_password_weak_password_rejected(self, db):
        factory, user_id = db
        async with factory() as session:
            raw_token = await _auth.create_challenge_token(session, user_id, ttl_minutes=60)

        async with factory() as session:
            with pytest.raises(ValueError, match="special character"):
                await _auth.reset_password(session, user_id, raw_token, "NoSpecialChar123")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_password_reset_service.py -v`
Expected: FAIL (AttributeError: 'AuthService' has no attribute 'reset_password')

**Step 3: Add reset_password method**

In `api/src/margin_api/services/auth.py`, add after the `verify_challenge_token` method (after line 198):

```python
    async def reset_password(
        self,
        session: AsyncSession,
        user_id: int,
        raw_token: str,
        new_password: str,
    ) -> None:
        """Reset a user's password using a valid challenge token.

        Verifies the token, validates password strength, updates the hash,
        sets password_changed_at, and clears any lockout.

        Raises LookupError if token is invalid/expired/used.
        Raises ValueError if password doesn't meet requirements.
        """
        valid = await self.verify_challenge_token(session, user_id, raw_token)
        if not valid:
            raise LookupError("Invalid or expired reset token")

        _validate_password(new_password)

        stmt = select(User).where(User.id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user is None:
            raise LookupError("User not found")

        user.password_hash = _hasher.hash(new_password)
        user.password_changed_at = datetime.now(UTC)
        user.failed_login_attempts = 0
        user.locked_until = None
        await session.commit()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_password_reset_service.py -v`
Expected: 7 passed

**Step 5: Commit**

```bash
git add api/src/margin_api/services/auth.py api/tests/test_password_reset_service.py
git commit -m "feat(api): add reset_password method to AuthService"
```

---

### Task 4: Add forgot-password and reset-password API endpoints

**Files:**
- Modify: `api/src/margin_api/schemas/auth.py:255` (add schemas)
- Modify: `api/src/margin_api/routes/auth.py:19-54,84-86,319` (add imports, factory, endpoints)
- Create: `api/tests/test_password_reset_endpoints.py`

**Step 1: Add Pydantic schemas**

In `api/src/margin_api/schemas/auth.py`, add at the end of the file (after line 255):

```python


# ---------------------------------------------------------------------------
# Password reset schemas
# ---------------------------------------------------------------------------


class ForgotPasswordRequest(BaseModel):
    """Request body for initiating password reset."""

    email: str = Field(min_length=5, max_length=320)


class ForgotPasswordResponse(BaseModel):
    """Response after initiating password reset."""

    message: str


class ResetPasswordRequest(BaseModel):
    """Request body for completing password reset."""

    user_id: int
    token: str
    new_password: str = Field(min_length=12)


class ResetPasswordResponse(BaseModel):
    """Response after successful password reset."""

    message: str
```

**Step 2: Write the failing tests**

Create `api/tests/test_password_reset_endpoints.py`:

```python
"""Tests for POST /api/v1/auth/forgot-password and POST /api/v1/auth/reset-password."""

from __future__ import annotations

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
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
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_password_reset_endpoints.py -v`
Expected: FAIL (import errors or 404s)

**Step 4: Add imports and endpoints to routes**

In `api/src/margin_api/routes/auth.py`, add to the schema imports (after line 38, `SecurityStatusResponse`):

```python
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
```

Add import for EmailService (after line 53, `from margin_api.services.webauthn`):

```python
from margin_api.services.email import EmailService
```

Add email service factory (after `_get_recovery_code_service` on line 85):

```python

def _get_email_service() -> EmailService:
    settings = get_settings()
    return EmailService(api_key=settings.resend_api_key)
```

Add endpoints after the `change_password` endpoint (after line 319):

```python


# ---------------------------------------------------------------------------
# Password reset endpoints
# ---------------------------------------------------------------------------


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
    email_svc: EmailService = Depends(_get_email_service),
) -> ForgotPasswordResponse:
    """Initiate password reset. Always returns 200 to prevent email enumeration."""
    stmt = select(User).where(
        User.email == body.email,
        User.password_hash.isnot(None),
    )
    user = (await db.execute(stmt)).scalar_one_or_none()

    if user is not None:
        settings = get_settings()
        raw_token = await auth.create_challenge_token(db, user.id, ttl_minutes=60)
        reset_url = f"{settings.app_url}/reset-password?token={raw_token}&userId={user.id}"
        email_svc.send_password_reset(to_email=user.email, reset_url=reset_url)

    return ForgotPasswordResponse(
        message="If an account exists with that email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
) -> ResetPasswordResponse:
    """Complete password reset using a valid token."""
    try:
        await auth.reset_password(db, body.user_id, body.token, body.new_password)
    except LookupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ResetPasswordResponse(message="Password has been reset.")
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_password_reset_endpoints.py -v`
Expected: 5 passed

**Step 6: Run full API test suite**

Run: `uv run pytest api/tests/ -v`
Expected: All tests pass (294+ tests)

**Step 7: Commit**

```bash
git add api/src/margin_api/schemas/auth.py api/src/margin_api/routes/auth.py api/tests/test_password_reset_endpoints.py
git commit -m "feat(api): add forgot-password and reset-password endpoints"
```

---

### Task 5: Add "Forgot password?" flow to login card

**Files:**
- Modify: `web/src/components/login/login-card.tsx`
- Modify: `web/src/app/login/page.tsx`
- Modify: `web/src/components/login/__tests__/login-card.test.tsx`

**Step 1: Write failing tests**

Add to `web/src/components/login/__tests__/login-card.test.tsx`, new describe block:

```typescript
  describe("forgot password", () => {
    it("shows 'Forgot password?' link in sign-in mode when credentials visible", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      expect(screen.getByText("Forgot password?")).toBeInTheDocument()
    })

    it("does not show 'Forgot password?' in sign-up mode", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      const segmented = screen.getByTestId("segmented-control")
      await user.click(within(segmented).getByRole("button", { name: "Sign Up" }))
      await user.click(screen.getByText("Continue with email"))
      expect(screen.queryByText("Forgot password?")).not.toBeInTheDocument()
    })

    it("switches to reset request form when clicked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      await user.click(screen.getByText("Forgot password?"))
      expect(screen.getByText("Send reset link")).toBeInTheDocument()
      // Password field should be gone
      expect(screen.queryByLabelText("Password", { selector: "input" })).not.toBeInTheDocument()
    })

    it("returns to sign-in form when 'Back to sign in' clicked", async () => {
      const user = userEvent.setup()
      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      await user.click(screen.getByText("Forgot password?"))
      await user.click(screen.getByText("Back to sign in"))
      expect(screen.getByLabelText("Password", { selector: "input" })).toBeInTheDocument()
    })

    it("shows success message after submitting email", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })

      render(<LoginCard />)
      await user.click(screen.getByText("Continue with email"))
      await user.click(screen.getByText("Forgot password?"))
      await user.type(screen.getByLabelText("Email"), "test@example.com")
      await user.click(screen.getByText("Send reset link"))

      await waitFor(() => {
        expect(screen.getByText(/check your email/i)).toBeInTheDocument()
      })

      global.fetch = originalFetch
    })
  })
```

Note: `originalFetch` is already declared in the sign-up registration describe block. Move `const originalFetch = global.fetch` and `afterEach` to the top-level describe scope so both blocks can share it.

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx`
Expected: FAIL (no "Forgot password?" element found)

**Step 3: Implement forgot password UI in login-card.tsx**

Add a `forgotMode` state and the corresponding form. In `login-card.tsx`:

Add state after the existing state declarations (around line 85):

```typescript
  const [forgotMode, setForgotMode] = useState(false)
  const [resetSent, setResetSent] = useState(false)
```

Add the forgot password submit handler after `handleSignUpSubmit` (around line 163):

```typescript
  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setServerError("")
    setIsSubmitting(true)
    try {
      const res = await fetch("/api/v1/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      if (res.ok) {
        setResetSent(true)
      }
    } catch {
      setServerError("Unable to reach the server. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }
```

In the credentials form JSX, when `forgotMode` is true and mode is "signin", show a simplified email-only form instead of the full credentials form. Replace the existing `<form>` inside the collapsible with:

```tsx
          <form onSubmit={forgotMode && mode === "signin" ? handleForgotSubmit : mode === "signin" ? handleCredentialsSubmit : handleSignUpSubmit} className="flex flex-col gap-4 pb-1">
```

When `forgotMode && mode === "signin"`, render only:
- The email input (already exists)
- A "Send reset link" submit button
- A "Back to sign in" link that sets `forgotMode` to false

When `resetSent`, show a green success message: "Check your email for a reset link."

Hide the password field, confirm password, and password rules when in forgot mode.

Add a "Forgot password?" link below the password field (visible only in sign-in mode when not in forgot mode):

```tsx
{mode === "signin" && !forgotMode && (
  <button
    type="button"
    onClick={() => { setForgotMode(true); setServerError("") }}
    className="text-[13px] text-accent hover:brightness-110 transition-colors self-end -mt-2"
  >
    Forgot password?
  </button>
)}
```

Also update `resetForm` to clear forgot mode:

```typescript
  const resetForm = () => {
    setEmail("")
    setPassword("")
    setShowPassword(false)
    setConfirmPassword("")
    setConfirmPasswordError("")
    setServerError("")
    setForgotMode(false)
    setResetSent(false)
  }
```

**Step 4: Also handle `resetSuccess` search param**

In `login/page.tsx`, add `resetSuccess` to the searchParams type:

```typescript
  searchParams: Promise<{ mode?: string; error?: string; code?: string; resetSuccess?: string }>
```

Pass it to LoginCard:

```tsx
<LoginCard
  initialMode={initialMode}
  authError={params.error}
  authCode={params.code}
  resetSuccess={params.resetSuccess === "true"}
/>
```

In LoginCard, accept the new prop and display it:

```typescript
interface LoginCardProps {
  initialMode?: "signin" | "signup"
  authError?: string
  authCode?: string
  resetSuccess?: boolean
}
```

Show the success message alongside the existing `successMessage` display:

```tsx
{resetSuccess && (
  <p className="text-[13px] text-green-400 text-center mb-4">
    Password reset successfully. Sign in with your new password.
  </p>
)}
```

**Step 5: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/login/__tests__/login-card.test.tsx`
Expected: All tests pass

**Step 6: Commit**

```bash
git add web/src/components/login/login-card.tsx web/src/app/login/page.tsx web/src/components/login/__tests__/login-card.test.tsx
git commit -m "feat(web): add forgot password flow to login card"
```

---

### Task 6: Create /reset-password page

**Files:**
- Create: `web/src/app/reset-password/page.tsx`
- Create: `web/src/app/reset-password/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Create `web/src/app/reset-password/__tests__/page.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import ResetPasswordPage from "../page"

// Mock useSearchParams
const mockSearchParams = new URLSearchParams()
vi.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
  useRouter: () => ({ push: vi.fn() }),
}))

describe("ResetPasswordPage", () => {
  const originalFetch = global.fetch

  beforeEach(() => {
    mockSearchParams.delete("token")
    mockSearchParams.delete("userId")
    global.fetch = originalFetch
  })

  it("renders password and confirm password fields", () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    render(<ResetPasswordPage />)
    expect(screen.getByLabelText("New Password")).toBeInTheDocument()
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument()
  })

  it("shows password validation checklist", () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    render(<ResetPasswordPage />)
    expect(screen.getByText("At least 12 characters")).toBeInTheDocument()
  })

  it("shows error when passwords do not match", async () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    const user = userEvent.setup()
    render(<ResetPasswordPage />)

    await user.type(screen.getByLabelText("New Password"), "NewPassword2@")
    await user.type(screen.getByLabelText("Confirm Password"), "Different2@!")
    await user.click(screen.getByRole("button", { name: /reset password/i }))

    expect(screen.getByText("Passwords do not match")).toBeInTheDocument()
  })

  it("calls API and shows success on valid submission", async () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ message: "Password has been reset." }),
    })

    const user = userEvent.setup()
    render(<ResetPasswordPage />)

    await user.type(screen.getByLabelText("New Password"), "NewPassword2@")
    await user.type(screen.getByLabelText("Confirm Password"), "NewPassword2@")
    await user.click(screen.getByRole("button", { name: /reset password/i }))

    await waitFor(() => {
      expect(screen.getByText(/password reset successfully/i)).toBeInTheDocument()
    })
  })

  it("shows error on API failure", async () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: "Invalid or expired reset token" }),
    })

    const user = userEvent.setup()
    render(<ResetPasswordPage />)

    await user.type(screen.getByLabelText("New Password"), "NewPassword2@")
    await user.type(screen.getByLabelText("Confirm Password"), "NewPassword2@")
    await user.click(screen.getByRole("button", { name: /reset password/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid or expired/i)).toBeInTheDocument()
    })
  })

  it("shows error when token is missing", () => {
    // No token in search params
    render(<ResetPasswordPage />)
    expect(screen.getByText(/invalid or missing/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/app/reset-password/__tests__/page.test.tsx`
Expected: FAIL (module not found)

**Step 3: Create the reset password page**

Create `web/src/app/reset-password/page.tsx`:

```tsx
"use client"

import { Suspense, useState } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { validatePassword, isPasswordValid } from "@/lib/password-validation"

function ResetPasswordForm() {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  const userId = searchParams.get("userId")

  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const passwordRules = validatePassword(password)

  if (!token || !userId) {
    return (
      <div className="flex flex-col items-center gap-6">
        <h1 className="text-xl font-semibold text-text-primary">Invalid or missing reset link</h1>
        <Link href="/login" className="text-accent hover:brightness-110 text-[13px]">
          Back to login
        </Link>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!isPasswordValid(password)) {
      setError("Password does not meet all requirements")
      return
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match")
      return
    }

    setIsSubmitting(true)
    try {
      const res = await fetch("/api/v1/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: Number(userId),
          token,
          new_password: password,
        }),
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail ?? "Password reset failed")
        return
      }

      setSuccess(true)
    } catch {
      setError("Unable to reach the server. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="flex flex-col items-center gap-6">
        <h1 className="text-xl font-semibold text-text-primary">Password reset successfully</h1>
        <p className="text-[13px] text-text-secondary text-center">
          You can now sign in with your new password.
        </p>
        <Link
          href="/login?resetSuccess=true"
          className="h-12 flex items-center justify-center w-full rounded-xl bg-accent text-white text-[15px] font-semibold hover:brightness-110 transition-all"
        >
          Sign In
        </Link>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-text-primary text-center">Reset your password</h1>
      <p className="text-[13px] text-text-secondary text-center mb-2">
        Enter your new password below.
      </p>

      {error && <p className="text-[13px] text-red-400 text-center">{error}</p>}

      <div className="flex flex-col gap-1.5">
        <label htmlFor="new-password" className="text-[13px] font-medium text-text-secondary">
          New Password
        </label>
        <input
          id="new-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
          placeholder="Enter new password"
        />
      </div>

      <div className="flex flex-col gap-1.5 -mt-1">
        {passwordRules.map((rule) => (
          <div key={rule.label} className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full transition-colors duration-200 ${
              rule.met ? "bg-green-400" : "bg-white/20"
            }`} />
            <span className={`text-[12px] transition-colors duration-200 ${
              rule.met ? "text-green-400" : "text-text-secondary"
            }`}>
              {rule.label}
            </span>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="confirm-password" className="text-[13px] font-medium text-text-secondary">
          Confirm Password
        </label>
        <input
          id="confirm-password"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="h-12 w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 text-[15px] text-text-primary placeholder-text-secondary/50 shadow-[inset_0_1px_2px_rgba(0,0,0,0.2)] transition-all duration-200 focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none"
          placeholder="Re-enter new password"
        />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="h-12 w-full rounded-xl bg-accent text-white text-[15px] font-semibold hover:brightness-110 active:scale-[0.98] transition-all duration-150 ease-out disabled:opacity-60 disabled:cursor-not-allowed"
      >
        Reset Password
      </button>

      <Link
        href="/login"
        className="text-[13px] text-text-secondary hover:text-text-primary transition-colors text-center"
      >
        Back to login
      </Link>
    </form>
  )
}

export default function ResetPasswordPage() {
  return (
    <div className="relative min-h-screen flex items-center justify-center bg-bg-primary overflow-hidden">
      <div className="w-[calc(100%-32px)] max-w-[420px] rounded-3xl border border-white/[0.06] bg-[rgba(17,17,19,0.6)] px-8 py-10 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-[16px] backdrop-saturate-[1.2]">
        <Suspense>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/app/reset-password/__tests__/page.test.tsx`
Expected: 6 passed

**Step 5: Commit**

```bash
git add web/src/app/reset-password/
git commit -m "feat(web): add /reset-password page"
```

---

### Task 7: Final integration verification

**Step 1: Run full API test suite**

Run: `uv run pytest api/tests/ -v`
Expected: All tests pass

**Step 2: Run full web test suite**

Run: `cd web && npx vitest run`
Expected: All tests pass

**Step 3: Commit all remaining changes**

If any files were missed, stage and commit them.

**Step 4: Summary commit / squash (optional)**

All work is committed across tasks 1-6. No final commit needed unless cleanup is required.
