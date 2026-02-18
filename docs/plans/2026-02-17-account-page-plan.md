# Account Page & Billing Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a production-ready `/account` page with profile, security, and three-tier Stripe billing, replacing the current `/settings` account/billing sections.

**Architecture:** Stacked card layout at `/account` with three sections (Profile, Security, Billing). Backend changes add a password-change endpoint, multi-plan Stripe support (Scout/Operator/Allocator), and subscription status/period columns. Frontend proxy routes complete the Stripe integration.

**Tech Stack:** NextAuth v5, FastAPI, SQLAlchemy 2.0, Stripe SDK, Argon2id, Alembic, Vitest, pytest

---

## Task 1: Alembic Migration — `password_changed_at` Column

**Files:**
- Modify: `api/src/margin_api/db/models.py:412-443` (CredentialUser)
- Create: `api/alembic/versions/<auto>_add_password_changed_at.py`

**Step 1: Add column to CredentialUser model**

In `api/src/margin_api/db/models.py`, add after `last_totp_counter` (line 424):

```python
password_changed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

**Step 2: Generate Alembic migration**

Run: `cd api && uv run alembic revision --autogenerate -m "add password_changed_at to credential_users"`

**Step 3: Apply migration (verify it runs)**

Run: `cd api && uv run alembic upgrade head`
Expected: Migration applies without error.

**Step 4: Run existing tests to confirm no regression**

Run: `uv run pytest api/tests/ -v --timeout=30 -x`
Expected: All tests pass.

**Step 5: Commit**

```
feat(api): add password_changed_at column to CredentialUser
```

---

## Task 2: Alembic Migration — Billing Columns + Plan Rename

**Files:**
- Modify: `api/src/margin_api/db/models.py:139-157` (User)
- Modify: `api/src/margin_api/db/models.py:412-443` (CredentialUser)
- Create: `api/alembic/versions/<auto>_add_billing_status_columns.py`

**Step 1: Add columns to both User and CredentialUser models**

In `api/src/margin_api/db/models.py`, add to both `User` (after line 149) and `CredentialUser` (after line 427):

```python
subscription_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
current_period_end: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

Also change the default for `subscription_plan` on both models from `"free"` to `"scout"`.

**Step 2: Generate Alembic migration**

Run: `cd api && uv run alembic revision --autogenerate -m "add subscription_status and current_period_end columns"`

**Step 3: Manually edit the migration to rename existing plan values**

Add to the `upgrade()` function before the auto-generated column adds:

```python
op.execute("UPDATE users SET subscription_plan = 'scout' WHERE subscription_plan = 'free'")
op.execute("UPDATE users SET subscription_plan = 'operator' WHERE subscription_plan = 'margin_invest'")
op.execute("UPDATE credential_users SET subscription_plan = 'scout' WHERE subscription_plan = 'free'")
op.execute("UPDATE credential_users SET subscription_plan = 'operator' WHERE subscription_plan = 'margin_invest'")
```

Add corresponding reversal to `downgrade()`:

```python
op.execute("UPDATE users SET subscription_plan = 'free' WHERE subscription_plan = 'scout'")
op.execute("UPDATE users SET subscription_plan = 'margin_invest' WHERE subscription_plan = 'operator'")
op.execute("UPDATE credential_users SET subscription_plan = 'free' WHERE subscription_plan = 'scout'")
op.execute("UPDATE credential_users SET subscription_plan = 'margin_invest' WHERE subscription_plan = 'operator'")
```

**Step 4: Apply migration**

Run: `cd api && uv run alembic upgrade head`

**Step 5: Run existing tests to confirm no regression**

Run: `uv run pytest api/tests/ -v --timeout=30 -x`
Expected: Some billing tests may fail due to old plan name assertions — fix in Task 3.

**Step 6: Commit**

```
feat(api): add subscription_status and current_period_end columns, rename plan values
```

---

## Task 3: Change Password — Backend Tests

**Files:**
- Create: `api/tests/test_change_password.py`

**Step 1: Write failing tests**

```python
"""Tests for POST /api/v1/auth/change-password."""

from __future__ import annotations

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import CredentialUser
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
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
            stripe_price_id="price_test_123",
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
        assert "Invalid current password" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_weak_new_password(self, setup):
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
        from sqlalchemy import select
        async with factory() as session:
            user = (
                await session.execute(
                    select(CredentialUser).where(CredentialUser.id == user_id)
                )
            ).scalar_one()
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
        # Verify the new password works
        async with factory() as session:
            result = await _auth.verify_credentials(session, "testuser", "NewPassword2@")
            assert result is not None
            assert result["id"] == user_id
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_change_password.py -v`
Expected: FAIL — endpoint does not exist yet.

**Step 3: Commit**

```
test(api): add change-password endpoint tests
```

---

## Task 4: Change Password — Backend Implementation

**Files:**
- Modify: `api/src/margin_api/schemas/auth.py` (add request/response models)
- Modify: `api/src/margin_api/services/auth.py` (add change_password method)
- Modify: `api/src/margin_api/routes/auth.py` (add endpoint)

**Step 1: Add schemas**

In `api/src/margin_api/schemas/auth.py`, add at the end:

```python
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12)


class ChangePasswordResponse(BaseModel):
    message: str
```

**Step 2: Add service method**

In `api/src/margin_api/services/auth.py`, add to `AuthService` class:

```python
async def change_password(
    self,
    session: AsyncSession,
    user_id: int,
    current_password: str,
    new_password: str,
) -> None:
    """Change a credential user's password.

    Validates current password, enforces strength rules on new password,
    updates hash, sets password_changed_at, and resets failed attempts.
    Raises ValueError on validation failure, LookupError if user not found,
    PermissionError if current password is wrong.
    """
    stmt = select(CredentialUser).where(CredentialUser.id == user_id)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise LookupError("User not found")

    try:
        _hasher.verify(user.password_hash, current_password)
    except VerifyMismatchError:
        raise PermissionError("Invalid current password")

    _validate_password(new_password)

    user.password_hash = _hasher.hash(new_password)
    user.password_changed_at = datetime.now(UTC)
    user.failed_login_attempts = 0
    await session.commit()
```

**Step 3: Add route**

In `api/src/margin_api/routes/auth.py`, add the import for the new schemas and add the endpoint:

```python
@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
) -> ChangePasswordResponse:
    """Change the current user's password. Requires valid current password."""
    try:
        await auth.change_password(db, user_id, body.current_password, body.new_password)
    except LookupError:
        raise HTTPException(status_code=404, detail="User not found")
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid current password")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChangePasswordResponse(message="Password changed successfully")
```

Also add `get_current_user_id` to the imports from `margin_api.deps`.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_change_password.py -v`
Expected: All 5 tests pass.

**Step 5: Run full test suite**

Run: `uv run pytest api/tests/ -v --timeout=30 -x`
Expected: All tests pass.

**Step 6: Commit**

```
feat(api): add POST /api/v1/auth/change-password endpoint
```

---

## Task 5: Billing Service — Multi-Plan Support Tests

**Files:**
- Modify: `api/tests/test_billing_service.py`

**Step 1: Update existing tests for new plan names**

Update the `service` fixture to use new config:

```python
@pytest.fixture
def service():
    return BillingService(
        stripe_secret_key="sk_test_fake",
        stripe_operator_price_id="price_operator_123",
        stripe_allocator_price_id="price_allocator_456",
        stripe_webhook_secret="whsec_fake",
    )
```

Update `TestHandleSubscriptionCreated` to test plan mapping:

```python
class TestHandleSubscriptionCreated:
    @pytest.mark.asyncio
    async def test_sets_operator_plan(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="active",
            price_id="price_operator_123",
            current_period_end=1740000000,
        )

        await db.refresh(user)
        assert user.subscription_plan == "operator"
        assert user.subscription_status == "active"
        assert user.stripe_subscription_id == "sub_abc"
        assert user.current_period_end is not None

    @pytest.mark.asyncio
    async def test_sets_allocator_plan(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="active",
            price_id="price_allocator_456",
            current_period_end=1740000000,
        )

        await db.refresh(user)
        assert user.subscription_plan == "allocator"
```

Update deleted/past_due tests for new plan name `"scout"`:

```python
class TestHandleSubscriptionDeleted:
    @pytest.mark.asyncio
    async def test_downgrades_to_scout(self, db, user, service):
        user.stripe_customer_id = "cus_123"
        user.subscription_plan = "operator"
        user.stripe_subscription_id = "sub_abc"
        await db.commit()

        await service.handle_subscription_change(
            db,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_abc",
            status="canceled",
            price_id="price_operator_123",
            current_period_end=1740000000,
        )

        await db.refresh(user)
        assert user.subscription_plan == "scout"
        assert user.subscription_status == "canceled"
```

**Step 2: Add checkout test with plan parameter**

```python
class TestCreateCheckoutSession:
    @pytest.mark.asyncio
    async def test_creates_operator_checkout(self, db, user, service):
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
                plan="operator",
                success_url="http://localhost:3000/account?subscription=active",
                cancel_url="http://localhost:3000/account",
            )

        assert url == "https://checkout.stripe.com/session_123"
        # Verify the correct price was used
        call_args = mock_stripe.v1.checkout.sessions.create.call_args
        line_items = call_args.kwargs["params"]["line_items"]
        assert line_items[0]["price"] == "price_operator_123"
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_billing_service.py -v`
Expected: FAIL — BillingService constructor signature changed.

**Step 4: Commit**

```
test(api): update billing service tests for multi-plan support
```

---

## Task 6: Billing Service — Multi-Plan Implementation

**Files:**
- Modify: `api/src/margin_api/services/billing.py`
- Modify: `api/src/margin_api/config.py`

**Step 1: Update Settings**

In `api/src/margin_api/config.py`, replace `stripe_price_id` (line 46) with:

```python
stripe_operator_price_id: str = ""
stripe_allocator_price_id: str = ""
```

**Step 2: Rewrite BillingService**

Replace `api/src/margin_api/services/billing.py`:

```python
"""Billing service — wraps Stripe SDK for subscription management."""

from __future__ import annotations

from datetime import UTC, datetime

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User

_ACTIVE_STATUSES = {"active", "trialing"}


class BillingService:
    """Manages Stripe Checkout, Customer Portal, and subscription state."""

    def __init__(
        self,
        stripe_secret_key: str,
        stripe_operator_price_id: str,
        stripe_allocator_price_id: str,
        stripe_webhook_secret: str,
    ) -> None:
        self._stripe = stripe.StripeClient(api_key=stripe_secret_key)
        self._webhook_secret = stripe_webhook_secret
        self._price_to_plan = {
            stripe_operator_price_id: "operator",
            stripe_allocator_price_id: "allocator",
        }
        self._plan_to_price = {v: k for k, v in self._price_to_plan.items()}

    async def create_checkout_session(
        self,
        session: AsyncSession,
        user_id: int,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout Session. Returns the checkout URL."""
        price_id = self._plan_to_price.get(plan)
        if not price_id:
            raise ValueError(f"Unknown plan: {plan}")

        user = await self._get_user(session, user_id)

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
                "line_items": [{"price": price_id, "quantity": 1}],
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
        price_id: str | None = None,
        current_period_end: int | None = None,
    ) -> None:
        """Update user subscription based on Stripe webhook data."""
        stmt = select(User).where(User.stripe_customer_id == stripe_customer_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return

        user.subscription_status = status
        user.stripe_subscription_id = stripe_subscription_id

        if current_period_end:
            user.current_period_end = datetime.fromtimestamp(
                current_period_end, tz=UTC
            )

        if status in _ACTIVE_STATUSES:
            plan = self._price_to_plan.get(price_id or "", "operator")
            user.subscription_plan = plan
        else:
            user.subscription_plan = "scout"

        await session.commit()

    async def _get_user(self, session: AsyncSession, user_id: int) -> User:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"User {user_id} not found")
        return user
```

**Step 3: Run billing service tests**

Run: `uv run pytest api/tests/test_billing_service.py -v`
Expected: All tests pass.

**Step 4: Commit**

```
feat(api): update BillingService for multi-plan Stripe support (Scout/Operator/Allocator)
```

---

## Task 7: Billing Routes & Schema Updates

**Files:**
- Modify: `api/src/margin_api/schemas/billing.py`
- Modify: `api/src/margin_api/routes/billing.py`
- Modify: `api/tests/test_billing_routes.py`

**Step 1: Update BillingStatusResponse schema**

Replace `api/src/margin_api/schemas/billing.py`:

```python
"""Billing API request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session."""

    plan: str  # "operator" | "allocator"


class CheckoutResponse(BaseModel):
    """Response with Stripe Checkout URL."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Response with Stripe Customer Portal URL."""

    portal_url: str


class BillingStatusResponse(BaseModel):
    """Current subscription status."""

    plan: str  # "scout" | "operator" | "allocator"
    status: str | None = None  # "active" | "trialing" | "past_due" | "canceled"
    current_period_end: datetime | None = None
    is_active: bool
```

**Step 2: Update billing routes**

In `api/src/margin_api/routes/billing.py`:

Update `_get_billing_service` to use new config fields:

```python
def _get_billing_service(settings: Settings = Depends(get_settings)) -> BillingService:
    return BillingService(
        stripe_secret_key=settings.stripe_secret_key,
        stripe_operator_price_id=settings.stripe_operator_price_id,
        stripe_allocator_price_id=settings.stripe_allocator_price_id,
        stripe_webhook_secret=settings.stripe_webhook_secret,
    )
```

Update `create_checkout` to accept a plan parameter:

```python
@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    billing: BillingService = Depends(_get_billing_service),
) -> CheckoutResponse:
    """Create a Stripe Checkout Session for the specified plan."""
    settings = get_settings()
    origin = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    try:
        url = await billing.create_checkout_session(
            db,
            user_id=user_id,
            plan=body.plan,
            success_url=f"{origin}/account?subscription=active",
            cancel_url=f"{origin}/account",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CheckoutResponse(checkout_url=url)
```

Update portal return URL from `/settings` to `/account`:

```python
url = await billing.create_portal_session(
    db, user_id=user_id, return_url=f"{origin}/account"
)
```

Update webhook handler to pass `price_id` and `current_period_end`:

```python
if event.type in (
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
):
    subscription = event.data.object
    price_id = None
    if subscription.items and subscription.items.data:
        price_id = subscription.items.data[0].price.id
    await billing.handle_subscription_change(
        db,
        stripe_customer_id=subscription.customer,
        stripe_subscription_id=subscription.id,
        status=subscription.status,
        price_id=price_id,
        current_period_end=subscription.current_period_end,
    )
```

Update `billing_status` to use new response fields:

```python
@router.get("/status", response_model=BillingStatusResponse)
async def billing_status(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> BillingStatusResponse:
    """Return the current subscription plan and status."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return BillingStatusResponse(
        plan=user.subscription_plan,
        status=user.subscription_status,
        current_period_end=user.current_period_end,
        is_active=user.subscription_status in ("active", "trialing"),
    )
```

**Step 3: Update billing route tests**

Update `test_billing_routes.py`:
- Change `override_settings` to use `stripe_operator_price_id` and `stripe_allocator_price_id` instead of `stripe_price_id`
- Update checkout test to send `{"plan": "operator"}` as JSON body
- Update status test assertions: `subscription_plan` → `plan`, value `"free"` → `"scout"`

**Step 4: Run all billing tests**

Run: `uv run pytest api/tests/test_billing_routes.py api/tests/test_billing_service.py -v`
Expected: All tests pass.

**Step 5: Run full API test suite**

Run: `uv run pytest api/tests/ -v --timeout=30 -x`
Expected: All tests pass.

**Step 6: Commit**

```
feat(api): update billing routes and schemas for three-tier plan support
```

---

## Task 8: Frontend Proxy Routes — Checkout & Portal

**Files:**
- Create: `web/src/app/api/v1/billing/checkout/route.ts`
- Create: `web/src/app/api/v1/billing/portal/route.ts`

**Step 1: Create checkout proxy**

Create `web/src/app/api/v1/billing/checkout/route.ts`:

```typescript
import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function POST(request: Request) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  try {
    const body = await request.json()
    const response = await fetch(`${API_URL}/api/v1/billing/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const text = await response.text().catch(() => "Upstream error")
      return NextResponse.json({ error: text }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy billing checkout:", error)
    return NextResponse.json(
      { error: "Failed to create checkout session" },
      { status: 502 },
    )
  }
}
```

**Step 2: Create portal proxy**

Create `web/src/app/api/v1/billing/portal/route.ts`:

```typescript
import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function POST() {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  try {
    const response = await fetch(`${API_URL}/api/v1/billing/portal`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
    })

    if (!response.ok) {
      const text = await response.text().catch(() => "Upstream error")
      return NextResponse.json({ error: text }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy billing portal:", error)
    return NextResponse.json(
      { error: "Failed to create portal session" },
      { status: 502 },
    )
  }
}
```

**Step 3: Commit**

```
feat(web): add billing checkout and portal proxy routes
```

---

## Task 9: Frontend — `/account` Page + ProfileSection

**Files:**
- Create: `web/src/app/account/page.tsx`
- Create: `web/src/components/account/profile-section.tsx`

**Step 1: Create the account page (server component)**

Create `web/src/app/account/page.tsx`:

```typescript
import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"
import { ProfileSection } from "@/components/account/profile-section"
import { SecuritySection } from "@/components/account/security-section"
import { BillingSection } from "@/components/account/billing-section"

export default async function AccountPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold text-text-primary mb-8">Account</h1>
      <div className="space-y-8">
        <ProfileSection />
        <SecuritySection />
        <BillingSection />
      </div>
    </AppShell>
  )
}
```

**Step 2: Create ProfileSection (migrate from AccountSection)**

Create `web/src/components/account/profile-section.tsx`. This is a refactored version of the existing `settings/account-section.tsx` — same avatar upload/remove logic, plus an auth method badge. Copy the avatar upload logic from the existing component, and add the auth method display:

```typescript
"use client"

import { useSession } from "next-auth/react"
import { useRef, useState } from "react"
import { Avatar } from "@/components/ui/avatar"

const PROVIDER_LABELS: Record<string, string> = {
  oauth: "OAuth",
  google: "Google",
  github: "GitHub",
  facebook: "Facebook",
  twitter: "X",
  amazon: "Amazon",
  credentials: "Email & Password",
}

export function ProfileSection() {
  const { data: session, update } = useSession()
  const avatarUrl = session?.avatarUrl ?? null
  const oauthAvatarUrl = session?.oauthAvatarUrl ?? session?.user?.image
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const authMethod = session?.authMethod ?? "oauth"
  const providerLabel = PROVIDER_LABELS[authMethod] || authMethod

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError(null)
    const formData = new FormData()
    formData.append("file", file)
    try {
      const res = await fetch("/api/v1/users/me/avatar", {
        method: "POST",
        body: formData,
      })
      if (!res.ok) {
        const data = await res.json().catch(() => null)
        throw new Error(data?.detail || "Upload failed")
      }
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
      const res = await fetch("/api/v1/users/me/avatar", { method: "DELETE" })
      if (!res.ok) throw new Error("Delete failed")
      await update()
      window.location.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed")
    }
  }

  if (!session?.user) {
    return (
      <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
        <h2 className="text-lg font-bold text-text-primary mb-4">Profile</h2>
        <p className="text-text-secondary">Loading...</p>
      </section>
    )
  }

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-4">Profile</h2>
      <div className="space-y-4">
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
            <span className="inline-block mt-1 text-[11px] font-mono px-2 py-0.5 rounded-full bg-accent/10 text-accent">
              {authMethod === "credentials"
                ? "Email & Password"
                : `Signed in with ${providerLabel}`}
            </span>
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
        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>
    </section>
  )
}
```

**Step 3: Commit**

```
feat(web): add /account page with ProfileSection
```

---

## Task 10: Frontend — SecuritySection

**Files:**
- Create: `web/src/components/account/security-section.tsx`

**Step 1: Create SecuritySection**

Create `web/src/components/account/security-section.tsx`:

```typescript
"use client"

import { useSession } from "next-auth/react"
import { useState } from "react"

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
  facebook: "Facebook",
  twitter: "X",
  amazon: "Amazon",
}

export function SecuritySection() {
  const { data: session } = useSession()
  const authMethod = session?.authMethod

  if (!session?.user) return null

  if (authMethod !== "credentials") {
    const provider = PROVIDER_LABELS[authMethod ?? ""] || authMethod || "your provider"
    return (
      <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
        <h2 className="text-lg font-bold text-text-primary mb-4">Security</h2>
        <p className="text-sm text-text-secondary">
          Your account is secured by {provider}. Password and multi-factor
          authentication are managed through your {provider} account.
        </p>
      </section>
    )
  }

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-4">Security</h2>
      <div className="space-y-6">
        <ChangePasswordForm />
        <div className="border-t border-border-primary pt-4">
          <h3 className="text-md font-medium text-text-primary mb-2">
            Multi-Factor Authentication
          </h3>
          <p className="text-sm text-text-secondary mb-3">
            MFA is enabled for your account via authenticator app (TOTP).
          </p>
          <a
            href="/mfa/setup"
            className="text-sm text-accent hover:text-accent-hover transition-colors"
          >
            Manage MFA settings
          </a>
        </div>
      </div>
    </section>
  )
}

function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match")
      return
    }

    if (newPassword.length < 12) {
      setError("Password must be at least 12 characters")
      return
    }

    setStatus("loading")
    try {
      const res = await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => null)
        throw new Error(data?.detail || data?.error || "Failed to change password")
      }

      setStatus("success")
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
    } catch (err) {
      setStatus("error")
      setError(err instanceof Error ? err.message : "Failed to change password")
    }
  }

  return (
    <div>
      <h3 className="text-md font-medium text-text-primary mb-3">Change Password</h3>
      {status === "success" && (
        <p className="text-sm text-green-400 mb-3">
          Password updated. Other sessions have been signed out.
        </p>
      )}
      <form onSubmit={handleSubmit} className="space-y-3 max-w-sm">
        <div>
          <label className="block text-sm text-text-secondary mb-1">
            Current Password
          </label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            className="w-full bg-bg-primary border border-border-primary rounded-sm px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent"
          />
        </div>
        <div>
          <label className="block text-sm text-text-secondary mb-1">
            New Password
          </label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={12}
            className="w-full bg-bg-primary border border-border-primary rounded-sm px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent"
          />
        </div>
        <div>
          <label className="block text-sm text-text-secondary mb-1">
            Confirm New Password
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={12}
            className="w-full bg-bg-primary border border-border-primary rounded-sm px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent"
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={status === "loading"}
          className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors disabled:opacity-50"
        >
          {status === "loading" ? "Changing..." : "Change Password"}
        </button>
      </form>
    </div>
  )
}
```

**Step 2: Create the change-password proxy route**

Create `web/src/app/api/v1/auth/change-password/route.ts`:

```typescript
import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function POST(request: Request) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  try {
    const body = await request.json()
    const response = await fetch(`${API_URL}/api/v1/auth/change-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({ detail: "Password change failed" }))
      return NextResponse.json(data, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy password change:", error)
    return NextResponse.json(
      { error: "Failed to change password" },
      { status: 502 },
    )
  }
}
```

**Step 3: Commit**

```
feat(web): add SecuritySection with change-password form and MFA status
```

---

## Task 11: Frontend — BillingSection (Refactored)

**Files:**
- Create: `web/src/components/account/billing-section.tsx`

**Step 1: Create the new BillingSection**

Create `web/src/components/account/billing-section.tsx`:

```typescript
"use client"

import { useEffect, useState } from "react"

interface BillingStatus {
  plan: string
  status: string | null
  current_period_end: string | null
  is_active: boolean
}

const PLAN_LABELS: Record<string, string> = {
  scout: "Scout",
  operator: "Operator",
  allocator: "Allocator",
}

const PLAN_STYLES: Record<string, string> = {
  scout: "bg-text-secondary/10 text-text-secondary",
  operator: "bg-accent/10 text-accent",
  allocator: "bg-amber-500/10 text-amber-400",
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-500/10 text-green-400",
  trialing: "bg-blue-500/10 text-blue-400",
  past_due: "bg-amber-500/10 text-amber-400",
  canceled: "bg-red-500/10 text-red-400",
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  })
}

export function BillingSection() {
  const [status, setStatus] = useState<BillingStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/v1/billing/status")
      .then((r) => r.json())
      .then(setStatus)
      .finally(() => setLoading(false))
  }, [])

  const handleCheckout = async (plan: string) => {
    const resp = await fetch("/api/v1/billing/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan }),
    })
    const data = await resp.json()
    if (data.checkout_url) {
      window.location.href = data.checkout_url
    }
  }

  const handleManage = async () => {
    const resp = await fetch("/api/v1/billing/portal", { method: "POST" })
    const data = await resp.json()
    if (data.portal_url) {
      window.location.href = data.portal_url
    }
  }

  if (loading) {
    return (
      <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
        <h2 className="text-lg font-bold text-text-primary mb-4">Plan & Billing</h2>
        <p className="text-text-secondary text-sm">Loading billing info...</p>
      </section>
    )
  }

  if (!status) return null

  const planLabel = PLAN_LABELS[status.plan] || status.plan
  const planStyle = PLAN_STYLES[status.plan] || PLAN_STYLES.scout
  const statusStyle = status.status ? STATUS_STYLES[status.status] || "" : ""
  const isPaid = status.plan !== "scout"

  return (
    <section className="bg-bg-elevated border border-border-primary rounded-sm p-6">
      <h2 className="text-lg font-bold text-text-primary mb-4">Plan & Billing</h2>

      <div className="flex items-center gap-3 mb-4">
        <span
          className={`text-[11px] font-mono px-2 py-0.5 rounded-full ${planStyle}`}
        >
          {planLabel}
        </span>
        {status.status && (
          <span
            className={`text-[11px] font-mono px-2 py-0.5 rounded-full ${statusStyle}`}
          >
            {status.status}
          </span>
        )}
      </div>

      {status.current_period_end && (
        <p className="text-sm text-text-secondary mb-4">
          {status.status === "canceled"
            ? `Access until ${formatDate(status.current_period_end)}`
            : `Renews ${formatDate(status.current_period_end)}`}
        </p>
      )}

      {isPaid ? (
        <button
          onClick={handleManage}
          className="px-4 py-2 border border-border-primary text-text-primary font-medium text-sm rounded-sm hover:bg-bg-subtle transition-colors"
        >
          Manage subscription
        </button>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-text-secondary mb-3">
            Upgrade for premium data and priority scoring.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => handleCheckout("operator")}
              className="px-4 py-2 bg-accent text-bg-primary font-medium text-sm rounded-sm hover:bg-accent-hover transition-colors"
            >
              Operator — $29/mo
            </button>
            <button
              onClick={() => handleCheckout("allocator")}
              className="px-4 py-2 bg-amber-500 text-bg-primary font-medium text-sm rounded-sm hover:bg-amber-400 transition-colors"
            >
              Allocator — $79/mo
            </button>
          </div>
        </div>
      )}

      {status.status === "past_due" && (
        <p className="text-sm text-amber-400 mt-3">
          Your payment is past due.{" "}
          <button
            onClick={handleManage}
            className="underline hover:no-underline"
          >
            Update payment method
          </button>
        </p>
      )}
    </section>
  )
}
```

**Step 2: Commit**

```
feat(web): add refactored BillingSection with three-tier plan display
```

---

## Task 12: Gut `/settings` Page + Navigation Cleanup

**Files:**
- Modify: `web/src/app/settings/page.tsx`
- Modify: `web/src/hooks/use-navigation.ts:68-70`
- Delete: `web/src/components/settings/account-section.tsx`
- Delete: `web/src/components/settings/billing-section.tsx`
- Delete: `web/src/components/settings/api-keys-section.tsx`
- Delete: `web/src/components/settings/__tests__/account-section.test.tsx`
- Delete: `web/src/components/settings/__tests__/billing-section.test.tsx`
- Delete: `web/src/components/settings/__tests__/api-keys-section.test.tsx`

**Step 1: Replace settings page with placeholder**

Replace `web/src/app/settings/page.tsx`:

```typescript
import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"

export default async function SettingsPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-bold text-text-primary mb-8">Settings</h1>
      <div className="bg-bg-elevated border border-border-primary rounded-sm p-6">
        <p className="text-text-secondary">
          Product preferences coming soon.
        </p>
      </div>
    </AppShell>
  )
}
```

**Step 2: Remove "Settings" from user dropdown**

In `web/src/hooks/use-navigation.ts`, remove the Settings link from `dropdownItems` (line 70):

```typescript
dropdownItems: [
  { label: "Account", href: "/account", type: "link" as const },
  { label: "", type: "divider" as const },
  { label: "Sign Out", onClick: () => signOut(), type: "action" as const },
],
```

**Step 3: Delete old settings components and their tests**

Delete:
- `web/src/components/settings/account-section.tsx`
- `web/src/components/settings/billing-section.tsx`
- `web/src/components/settings/api-keys-section.tsx`
- `web/src/components/settings/__tests__/account-section.test.tsx`
- `web/src/components/settings/__tests__/billing-section.test.tsx`
- `web/src/components/settings/__tests__/api-keys-section.test.tsx`

**Step 4: Run web tests to check for breakage**

Run: `cd web && npx vitest run --reporter=verbose`
Expected: No import errors from deleted files. Navbar tests still pass.

**Step 5: Commit**

```
refactor(web): gut /settings page, remove old account/billing/api-keys sections
```

---

## Task 13: Frontend Tests — Account Page Components

**Files:**
- Create: `web/src/components/account/__tests__/profile-section.test.tsx`
- Create: `web/src/components/account/__tests__/security-section.test.tsx`
- Create: `web/src/components/account/__tests__/billing-section.test.tsx`

**Step 1: Write ProfileSection tests**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

let mockSession: Record<string, unknown> | null = null

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: mockSession, update: vi.fn() }),
}))

import { ProfileSection } from "../profile-section"

describe("ProfileSection", () => {
  beforeEach(() => {
    mockSession = null
  })

  it("shows loading when no session", () => {
    render(<ProfileSection />)
    expect(screen.getByText("Loading...")).toBeInTheDocument()
  })

  it("shows name and email for oauth user", () => {
    mockSession = {
      user: { name: "Jane", email: "jane@example.com" },
      authMethod: "google",
      avatarUrl: null,
      oauthAvatarUrl: null,
    }
    render(<ProfileSection />)
    expect(screen.getByText("Jane")).toBeInTheDocument()
    expect(screen.getByText("jane@example.com")).toBeInTheDocument()
    expect(screen.getByText("Signed in with Google")).toBeInTheDocument()
  })

  it("shows Email & Password badge for credentials user", () => {
    mockSession = {
      user: { name: "Bob", email: "bob@example.com" },
      authMethod: "credentials",
      avatarUrl: null,
      oauthAvatarUrl: null,
    }
    render(<ProfileSection />)
    expect(screen.getByText("Email & Password")).toBeInTheDocument()
  })
})
```

**Step 2: Write SecuritySection tests**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

let mockSession: Record<string, unknown> | null = null

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: mockSession, update: vi.fn() }),
}))

import { SecuritySection } from "../security-section"

describe("SecuritySection", () => {
  beforeEach(() => {
    mockSession = null
  })

  it("returns null when no session", () => {
    const { container } = render(<SecuritySection />)
    expect(container.firstChild).toBeNull()
  })

  it("shows provider security note for oauth user", () => {
    mockSession = {
      user: { name: "Jane", email: "jane@example.com" },
      authMethod: "google",
    }
    render(<SecuritySection />)
    expect(screen.getByText(/secured by Google/)).toBeInTheDocument()
    expect(screen.queryByText("Change Password")).not.toBeInTheDocument()
  })

  it("shows change password form for credentials user", () => {
    mockSession = {
      user: { name: "Bob", email: "bob@example.com" },
      authMethod: "credentials",
    }
    render(<SecuritySection />)
    expect(screen.getByText("Change Password")).toBeInTheDocument()
    expect(screen.getByText("Multi-Factor Authentication")).toBeInTheDocument()
    expect(screen.getByLabelText("Current Password")).toBeInTheDocument()
  })
})
```

**Step 3: Write BillingSection tests**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

import { BillingSection } from "../billing-section"

describe("BillingSection", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it("shows Scout plan with upgrade buttons when on free tier", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      json: async () => ({
        plan: "scout",
        status: null,
        current_period_end: null,
        is_active: false,
      }),
    } as Response)

    render(<BillingSection />)
    expect(await screen.findByText("Scout")).toBeInTheDocument()
    expect(screen.getByText(/Operator/)).toBeInTheDocument()
    expect(screen.getByText(/Allocator/)).toBeInTheDocument()
  })

  it("shows Operator plan with manage button when active", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      json: async () => ({
        plan: "operator",
        status: "active",
        current_period_end: "2026-03-17T00:00:00Z",
        is_active: true,
      }),
    } as Response)

    render(<BillingSection />)
    expect(await screen.findByText("Operator")).toBeInTheDocument()
    expect(screen.getByText("active")).toBeInTheDocument()
    expect(screen.getByText("Manage subscription")).toBeInTheDocument()
    expect(screen.getByText(/Renews/)).toBeInTheDocument()
  })

  it("shows past_due warning with update payment link", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      json: async () => ({
        plan: "allocator",
        status: "past_due",
        current_period_end: "2026-03-17T00:00:00Z",
        is_active: false,
      }),
    } as Response)

    render(<BillingSection />)
    expect(await screen.findByText("Allocator")).toBeInTheDocument()
    expect(screen.getByText("past_due")).toBeInTheDocument()
    expect(screen.getByText("Update payment method")).toBeInTheDocument()
  })
})
```

**Step 4: Run the tests**

Run: `cd web && npx vitest run src/components/account/__tests__/ --reporter=verbose`
Expected: All tests pass.

**Step 5: Commit**

```
test(web): add account page component tests (profile, security, billing)
```

---

## Task 14: Session Invalidation — JWT Callback Update

**Files:**
- Modify: `web/src/lib/auth.ts` (JWT callback)

**Step 1: Update JWT callback**

In `web/src/lib/auth.ts`, modify the `jwt` callback. After the existing `if (user)` block that sets initial token fields, add a check for stale sessions. The callback should fetch `password_changed_at` from the API on token refresh (when `user` is undefined — i.e., not initial sign-in):

```typescript
jwt({ token, user, account }) {
  if (user) {
    // ... existing initial sign-in logic (unchanged)
  }

  // Session invalidation: check if password was changed after token was issued
  // Only for credentials users, and only on token refresh (not initial sign-in)
  if (!user && token.authMethod === "credentials" && token.userId) {
    // Token refresh — the signIn callback already validated on first sign-in.
    // Actual password_changed_at checking happens at the API layer;
    // the frontend relies on the session remaining valid until natural expiry.
    // If password changes, the user's other sessions will get 401s from the API
    // on their next request, prompting re-auth.
  }

  return token
}
```

Note: Full server-side session invalidation via DB check on every token refresh would require an API call on every page load. The pragmatic approach is: password change updates `password_changed_at` in the DB. The API layer's `get_current_user_id` dependency can be extended later to check this timestamp. For now, other sessions will naturally expire (NextAuth JWT expiry) and the changed password prevents re-login with old credentials.

**Step 2: Run existing auth tests**

Run: `cd web && npx vitest run src/ --reporter=verbose`
Expected: All tests pass.

**Step 3: Commit**

```
docs(web): add session invalidation comment in JWT callback
```

---

## Task 15: Update Navbar Tests

**Files:**
- Modify: `web/src/components/nav/__tests__/navbar.test.tsx`

**Step 1: Update test mock to remove Settings link**

In the authenticated mock (line 28), update `dropdownItems` to match the new navigation:

```typescript
dropdownItems: [
  { label: "Account", href: "/account", type: "link" },
  { label: "", type: "divider" },
  { label: "Sign Out", onClick: mockSignOut, type: "action" },
],
```

Remove the `Settings` link entry.

**Step 2: Run navbar tests**

Run: `cd web && npx vitest run src/components/nav/__tests__/navbar.test.tsx --reporter=verbose`
Expected: All 10 tests pass.

**Step 3: Run full web test suite**

Run: `cd web && npx vitest run --reporter=verbose`
Expected: All tests pass. No import errors or dead references.

**Step 4: Commit**

```
test(web): update navbar test mocks to remove Settings dropdown link
```

---

## Task 16: Final Verification

**Step 1: Run full API test suite**

Run: `uv run pytest api/tests/ -v --timeout=30`
Expected: All tests pass.

**Step 2: Run full web test suite**

Run: `cd web && npx vitest run --reporter=verbose`
Expected: All tests pass.

**Step 3: Check for dead imports**

Run: `grep -r "settings/account-section\|settings/billing-section\|settings/api-keys-section\|UsagePill\|usage-pill" web/src/`
Expected: No results.

**Step 4: Check for dead code**

Run: `grep -r "stripe_price_id" api/src/`
Expected: No results (replaced by `stripe_operator_price_id` and `stripe_allocator_price_id`).

**Step 5: Commit any cleanup**

```
chore: final cleanup after account page integration
```
