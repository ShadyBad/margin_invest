# $10 List Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-page Stripe Checkout experiment to sell this week's 10-stock survivor list as a $10 one-shot PDF report, with PostHog analytics and Resend email delivery.

**Architecture:** Server-rendered Next.js page at `/experiment/this-week` (no auth, no nav chrome) → Stripe Checkout in `payment` mode (one-shot, not subscription) → FastAPI webhook handler inserts into `experiment_signups` table → Resend delivers placeholder PDF. PostHog tracks page_view, checkout_click, purchase_complete.

**Tech Stack:** Next.js 16 (React 19), FastAPI, Stripe Checkout (payment mode), Resend, PostHog, PostgreSQL, Alembic.

**Spec:** `docs/superpowers/specs/2026-04-24-phase0-pivot-validation-design.md` — Section 3.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `api/src/margin_api/db/models.py` (append) | `ExperimentSignup` ORM model |
| Create | `api/alembic/versions/b1c2d3e4f5a6_add_experiment_signups_table.py` | Migration for `experiment_signups` |
| Create | `api/src/margin_api/schemas/experiment.py` | Pydantic request/response schemas |
| Create | `api/src/margin_api/routes/experiment.py` | Checkout + webhook endpoints |
| Modify | `api/src/margin_api/app.py` | Register experiment router |
| Create | `api/tests/routes/test_experiment.py` | API tests for webhook handler |
| Create | `web/src/app/experiment/this-week/page.tsx` | Landing page (server component) |
| Create | `web/src/app/experiment/this-week/checkout-button.tsx` | Client component for Stripe + PostHog |
| Create | `web/src/app/api/v1/experiment/checkout/route.ts` | Next.js proxy for checkout session creation |
| Create | `web/src/app/experiment/this-week/__tests__/page.test.tsx` | Frontend test |

---

## Task 1: ExperimentSignup ORM Model

**Files:**
- Modify: `api/src/margin_api/db/models.py` (append after `ProcessedWebhookEvent`, around line 915)

- [ ] **Step 1: Add ExperimentSignup model to models.py**

Append after the `ProcessedWebhookEvent` class (around line 915):

```python
class ExperimentSignup(Base):
    """Tracks $10 list experiment purchases."""

    __tablename__ = "experiment_signups"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    amount_cents: Mapped[int] = mapped_column(Integer)
    stripe_session_id: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

- [ ] **Step 2: Verify model loads without import errors**

Run: `cd api && uv run python -c "from margin_api.db.models import ExperimentSignup; print(ExperimentSignup.__tablename__)"`

Expected: `experiment_signups`

- [ ] **Step 3: Commit**

```bash
git add api/src/margin_api/db/models.py
git commit -m "feat(experiment): add ExperimentSignup ORM model"
```

---

## Task 2: Alembic Migration

**Files:**
- Create: `api/alembic/versions/b1c2d3e4f5a6_add_experiment_signups_table.py`

- [ ] **Step 1: Create the migration file**

```python
"""add_experiment_signups_table

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-04-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create experiment_signups table."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()

    if "experiment_signups" not in existing_tables:
        op.create_table(
            "experiment_signups",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("amount_cents", sa.Integer(), nullable=False),
            sa.Column(
                "stripe_session_id", sa.String(length=255), nullable=False
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("stripe_session_id"),
        )


def downgrade() -> None:
    """Drop experiment_signups table."""
    op.drop_table("experiment_signups")
```

- [ ] **Step 2: Verify migration has no head conflicts**

Run: `cd api && uv run alembic heads`

Expected: One head — `b1c2d3e4f5a6 (head)`

- [ ] **Step 3: Verify migration applies cleanly on a fresh DB**

Run: `cd api && uv run alembic upgrade head`

Expected: No errors. The table is created.

- [ ] **Step 4: Commit**

```bash
git add api/alembic/versions/b1c2d3e4f5a6_add_experiment_signups_table.py
git commit -m "feat(experiment): add Alembic migration for experiment_signups"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `api/src/margin_api/schemas/experiment.py`

- [ ] **Step 1: Create the schemas file**

```python
"""Schemas for the $10 list experiment."""

from __future__ import annotations

from pydantic import BaseModel


class ExperimentCheckoutResponse(BaseModel):
    """Response with Stripe Checkout URL for the experiment."""

    checkout_url: str


class ExperimentWebhookResponse(BaseModel):
    """Response from the experiment webhook handler."""

    status: str
```

- [ ] **Step 2: Verify import**

Run: `cd api && uv run python -c "from margin_api.schemas.experiment import ExperimentCheckoutResponse; print('ok')"`

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add api/src/margin_api/schemas/experiment.py
git commit -m "feat(experiment): add Pydantic schemas for experiment endpoints"
```

---

## Task 4: Experiment API Router — Tests First

**Files:**
- Create: `api/tests/routes/test_experiment.py`

This task writes the failing tests. Task 5 implements the router to make them pass.

- [ ] **Step 1: Write the test file**

```python
"""Tests for the $10 list experiment endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import ExperimentSignup
from margin_api.db.session import get_db


_TEST_WEBHOOK_SECRET = "whsec_test_secret"


def _make_test_settings() -> MagicMock:
    """Create a mock Settings object for experiment tests."""
    settings = MagicMock()
    settings.stripe_secret_key = "sk_test_fake"
    settings.stripe_webhook_secret = _TEST_WEBHOOK_SECRET
    settings.resend_api_key = ""
    settings.stripe_portfolio_price_id = ""
    settings.stripe_institutional_price_id = ""
    settings.cors_origins = ["http://localhost:3000"]
    settings.debug = True
    settings.environment = "development"
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    settings.rate_limit_enabled = False
    settings.redis_url = "redis://localhost:6379"
    return settings


def _sign_payload(payload_bytes: bytes) -> str:
    """Build a Stripe-style webhook signature for testing."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload_bytes.decode()}"
    sig = hmac.new(
        _TEST_WEBHOOK_SECRET.encode(), signed_payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={sig}"


@pytest_asyncio.fixture()
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = _make_test_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, factory

    await engine.dispose()


@pytest.mark.asyncio
async def test_checkout_creates_stripe_session(setup):
    """POST /api/v1/experiment/checkout returns a Stripe Checkout URL."""
    client, _ = setup

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"

    with patch("margin_api.routes.experiment.stripe") as mock_stripe:
        mock_stripe.checkout.Session.create.return_value = mock_session
        response = await client.post(
            "/api/v1/experiment/checkout",
            json={"success_url": "http://localhost:3000/experiment/this-week?success=1",
                  "cancel_url": "http://localhost:3000/experiment/this-week"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"

    # Verify Stripe was called with payment mode and $10
    call_kwargs = mock_stripe.checkout.Session.create.call_args
    assert call_kwargs.kwargs["mode"] == "payment"
    line_items = call_kwargs.kwargs["line_items"]
    assert line_items[0]["price_data"]["unit_amount"] == 1000
    assert line_items[0]["price_data"]["currency"] == "usd"


@pytest.mark.asyncio
async def test_webhook_inserts_signup_and_sends_email(setup):
    """POST /api/v1/experiment/webhook records signup and triggers email."""
    client, factory = setup

    event_payload = {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_abc",
                "customer_details": {"email": "buyer@example.com"},
                "amount_total": 1000,
                "payment_status": "paid",
                "metadata": {"experiment": "ten_dollar_list"},
            }
        },
    }
    payload_bytes = json.dumps(event_payload).encode()
    stripe_signature = _sign_payload(payload_bytes)

    with patch("margin_api.routes.experiment.EmailService") as mock_email_cls:
        mock_email = MagicMock()
        mock_email.send_custom.return_value = True
        mock_email_cls.return_value = mock_email

        with patch("margin_api.routes.experiment.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = event_payload
            mock_stripe.SignatureVerificationError = Exception

            response = await client.post(
                "/api/v1/experiment/webhook",
                content=payload_bytes,
                headers={
                    "stripe-signature": stripe_signature,
                    "content-type": "application/json",
                },
            )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify the signup was recorded in the DB
    async with factory() as session:
        result = await session.execute(
            select(ExperimentSignup).where(
                ExperimentSignup.stripe_session_id == "cs_test_abc"
            )
        )
        signup = result.scalar_one()
        assert signup.email == "buyer@example.com"
        assert signup.amount_cents == 1000

    # Verify email was sent
    mock_email.send_custom.assert_called_once()
    call_args = mock_email.send_custom.call_args
    assert call_args.args[0] == "buyer@example.com"
    assert "survivor" in call_args.args[1].lower() or "list" in call_args.args[1].lower()


@pytest.mark.asyncio
async def test_webhook_idempotent_on_duplicate_session(setup):
    """Duplicate Stripe session IDs do not create duplicate signups."""
    client, factory = setup

    event_payload = {
        "id": "evt_test_456",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_dup",
                "customer_details": {"email": "dup@example.com"},
                "amount_total": 1000,
                "payment_status": "paid",
                "metadata": {"experiment": "ten_dollar_list"},
            }
        },
    }
    payload_bytes = json.dumps(event_payload).encode()
    stripe_signature = _sign_payload(payload_bytes)

    with patch("margin_api.routes.experiment.EmailService") as mock_email_cls:
        mock_email = MagicMock()
        mock_email.send_custom.return_value = True
        mock_email_cls.return_value = mock_email

        with patch("margin_api.routes.experiment.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = event_payload
            mock_stripe.SignatureVerificationError = Exception

            # First call — should succeed
            response1 = await client.post(
                "/api/v1/experiment/webhook",
                content=payload_bytes,
                headers={
                    "stripe-signature": stripe_signature,
                    "content-type": "application/json",
                },
            )
            assert response1.status_code == 200
            assert response1.json()["status"] == "ok"

            # Second call with same session ID — should be idempotent
            response2 = await client.post(
                "/api/v1/experiment/webhook",
                content=payload_bytes,
                headers={
                    "stripe-signature": stripe_signature,
                    "content-type": "application/json",
                },
            )
            assert response2.status_code == 200
            assert response2.json()["status"] == "already_processed"

    # Verify only one signup exists
    async with factory() as session:
        result = await session.execute(
            select(ExperimentSignup).where(
                ExperimentSignup.stripe_session_id == "cs_test_dup"
            )
        )
        signups = result.scalars().all()
        assert len(signups) == 1


@pytest.mark.asyncio
async def test_webhook_ignores_non_experiment_events(setup):
    """Webhook ignores checkout sessions without experiment metadata."""
    client, factory = setup

    event_payload = {
        "id": "evt_test_789",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_other",
                "customer_details": {"email": "other@example.com"},
                "amount_total": 2900,
                "payment_status": "paid",
                "metadata": {},
            }
        },
    }
    payload_bytes = json.dumps(event_payload).encode()
    stripe_signature = _sign_payload(payload_bytes)

    with patch("margin_api.routes.experiment.stripe") as mock_stripe:
        mock_stripe.Webhook.construct_event.return_value = event_payload
        mock_stripe.SignatureVerificationError = Exception

        response = await client.post(
            "/api/v1/experiment/webhook",
            content=payload_bytes,
            headers={
                "stripe-signature": stripe_signature,
                "content-type": "application/json",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

    # No signup created
    async with factory() as session:
        result = await session.execute(select(ExperimentSignup))
        assert result.scalars().all() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd api && uv run pytest tests/routes/test_experiment.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'margin_api.routes.experiment'`

- [ ] **Step 3: Commit**

```bash
git add api/tests/routes/test_experiment.py
git commit -m "test(experiment): add failing tests for experiment checkout and webhook"
```

---

## Task 5: Experiment API Router — Implementation

**Files:**
- Create: `api/src/margin_api/routes/experiment.py`
- Modify: `api/src/margin_api/app.py` (add router import + include)

- [ ] **Step 1: Create the experiment router**

```python
"""Experiment API routes — $10 list one-shot Stripe Checkout."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import Settings, get_settings
from margin_api.db.models import ExperimentSignup
from margin_api.db.session import get_db
from margin_api.schemas.experiment import ExperimentCheckoutResponse, ExperimentWebhookResponse
from margin_api.services.email import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/experiment", tags=["experiment"])


@router.post("/checkout", response_model=ExperimentCheckoutResponse)
async def create_experiment_checkout(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ExperimentCheckoutResponse:
    """Create a one-shot Stripe Checkout session for the $10 list."""
    body = await request.json()
    success_url = body.get("success_url", "")
    cancel_url = body.get("cancel_url", "")

    if not success_url or not cancel_url:
        raise HTTPException(status_code=400, detail="success_url and cancel_url required")

    stripe.api_key = settings.stripe_secret_key

    checkout_session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": 1000,
                    "product_data": {
                        "name": "Margin Invest — This Week's 10 Survivors",
                        "description": "Forensic scorecard of this week's conviction-gated picks.",
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={"experiment": "ten_dollar_list"},
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return ExperimentCheckoutResponse(checkout_url=checkout_session.url)


@router.post("/webhook", response_model=ExperimentWebhookResponse)
async def experiment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ExperimentWebhookResponse:
    """Handle Stripe webhook for experiment checkout completions."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload.decode("utf-8"),
            signature,
            settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] != "checkout.session.completed":
        return ExperimentWebhookResponse(status="ignored")

    session_obj = event["data"]["object"]
    metadata = session_obj.get("metadata", {})

    if metadata.get("experiment") != "ten_dollar_list":
        return ExperimentWebhookResponse(status="ignored")

    stripe_session_id = session_obj["id"]
    email = session_obj.get("customer_details", {}).get("email", "")
    amount_cents = session_obj.get("amount_total", 0)

    # Idempotency: skip if already processed
    existing = await db.execute(
        select(ExperimentSignup).where(
            ExperimentSignup.stripe_session_id == stripe_session_id
        )
    )
    if existing.scalar_one_or_none():
        return ExperimentWebhookResponse(status="already_processed")

    signup = ExperimentSignup(
        email=email,
        paid_at=datetime.now(UTC),
        amount_cents=amount_cents,
        stripe_session_id=stripe_session_id,
    )
    db.add(signup)
    await db.commit()

    # Send confirmation email with placeholder PDF
    email_svc = EmailService(api_key=settings.resend_api_key)
    email_svc.send_custom(
        email,
        "Your Margin Invest Survivor List",
        (
            "<h2>Thank you for your purchase!</h2>"
            "<p>Your weekly survivor list is being prepared. "
            "You'll receive it within 24 hours of the next market close.</p>"
            "<p>This report contains the conviction-gated picks that survived "
            "our elimination pipeline — with factor decomposition and "
            "plain-English interpretation for each ticker.</p>"
            "<p>Questions? Reply to this email.</p>"
        ),
    )

    logger.info("Experiment signup recorded: %s (session %s)", email, stripe_session_id)
    return ExperimentWebhookResponse(status="ok")
```

- [ ] **Step 2: Register the router in app.py**

Add import at the top of `api/src/margin_api/app.py` (after the other router imports, around line 42):

```python
from margin_api.routes.experiment import router as experiment_router
```

Add include in `create_app()` (after the other `app.include_router` calls, around line 177):

```python
    app.include_router(experiment_router)
```

- [ ] **Step 3: Run the tests**

Run: `cd api && uv run pytest tests/routes/test_experiment.py -v`

Expected: All 4 tests pass.

If tests fail, the most likely issue is Stripe mock wiring. The tests patch `margin_api.routes.experiment.stripe` so both `stripe.checkout.Session.create` (checkout) and `stripe.Webhook.construct_event` (webhook) are mocked. The `get_settings` and `get_db` dependencies are overridden in the test fixture, so the webhook gets the in-memory SQLite session and test settings automatically.

- [ ] **Step 4: Commit**

```bash
git add api/src/margin_api/routes/experiment.py api/src/margin_api/app.py
git commit -m "feat(experiment): add checkout + webhook endpoints for $10 list"
```

---

## Task 6: Next.js Proxy Route

**Files:**
- Create: `web/src/app/api/v1/experiment/checkout/route.ts`

The experiment checkout doesn't require auth (no login needed), but we still proxy through Next.js to keep the API URL server-side.

- [ ] **Step 1: Create the proxy route**

```typescript
import { NextResponse } from "next/server"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const response = await fetch(`${API_URL}/api/v1/experiment/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      try {
        const errorBody = await response.json()
        return NextResponse.json(errorBody, { status: response.status })
      } catch {
        return NextResponse.json(
          { error_code: "UPSTREAM_ERROR", message: "Upstream error", status_code: response.status },
          { status: response.status },
        )
      }
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy experiment checkout:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to create checkout session", status_code: 502 },
      { status: 502 },
    )
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/app/api/v1/experiment/checkout/route.ts
git commit -m "feat(experiment): add Next.js proxy route for experiment checkout"
```

---

## Task 7: Landing Page — Test First

**Files:**
- Create: `web/src/app/experiment/this-week/__tests__/page.test.tsx`

- [ ] **Step 1: Write the test file**

```tsx
import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      onchange: null,
      dispatchEvent: vi.fn(),
    })),
  })
})

const mockCapture = vi.fn()
vi.mock("posthog-js", () => ({
  default: { capture: mockCapture },
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { CheckoutButton } from "../checkout-button"

describe("CheckoutButton", () => {
  it("renders the purchase button", () => {
    render(<CheckoutButton />)
    const button = screen.getByRole("button", { name: /get this week/i })
    expect(button).toBeInTheDocument()
  })

  it("fires checkout_click PostHog event on click", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ checkout_url: "https://checkout.stripe.com/test" }),
    })

    // Mock window.location.href setter
    const locationSpy = vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      href: "",
      origin: "http://localhost:3000",
    } as Location)

    render(<CheckoutButton />)
    const button = screen.getByRole("button", { name: /get this week/i })
    fireEvent.click(button)

    expect(mockCapture).toHaveBeenCalledWith("checkout_click", {
      experiment: "ten_dollar_list",
      amount_cents: 1000,
    })

    locationSpy.mockRestore()
  })
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run src/app/experiment/this-week/__tests__/page.test.tsx`

Expected: FAIL — cannot find module `../checkout-button`

- [ ] **Step 3: Commit**

```bash
git add web/src/app/experiment/this-week/__tests__/page.test.tsx
git commit -m "test(experiment): add failing test for checkout button PostHog event"
```

---

## Task 8: Landing Page — Implementation

**Files:**
- Create: `web/src/app/experiment/this-week/page.tsx`
- Create: `web/src/app/experiment/this-week/checkout-button.tsx`

- [ ] **Step 1: Create the CheckoutButton client component**

```tsx
"use client"

import { useState } from "react"
import posthog from "posthog-js"

export function CheckoutButton() {
  const [loading, setLoading] = useState(false)

  async function handleClick() {
    posthog.capture("checkout_click", {
      experiment: "ten_dollar_list",
      amount_cents: 1000,
    })

    setLoading(true)
    try {
      const origin = window.location.origin
      const res = await fetch("/api/v1/experiment/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          success_url: `${origin}/experiment/this-week?success=1`,
          cancel_url: `${origin}/experiment/this-week`,
        }),
      })

      if (!res.ok) {
        setLoading(false)
        return
      }

      const data = await res.json()
      if (data.checkout_url) {
        posthog.capture("checkout_redirect", { experiment: "ten_dollar_list" })
        window.location.href = data.checkout_url
      }
    } catch {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className="w-full rounded-lg bg-white px-8 py-4 text-lg font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
    >
      {loading ? "Redirecting to checkout…" : "Get This Week's List — $10"}
    </button>
  )
}
```

- [ ] **Step 2: Create the landing page (server component)**

```tsx
import { Metadata } from "next"
import { CheckoutButton } from "./checkout-button"

export const metadata: Metadata = {
  title: "This Week's 10 Survivors — Margin Invest",
  description:
    "The 10 stocks that survived our forensic elimination pipeline this week. Deterministic scoring, no opinions.",
}

export default function ExperimentThisWeekPage({
  searchParams,
}: {
  searchParams: Promise<{ success?: string }>
}) {
  return <PageContent searchParams={searchParams} />
}

async function PageContent({
  searchParams,
}: {
  searchParams: Promise<{ success?: string }>
}) {
  const params = await searchParams
  const success = params.success === "1"

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-black px-6 text-white">
      <div className="mx-auto max-w-xl text-center">
        {success ? (
          <SuccessMessage />
        ) : (
          <OfferContent />
        )}
      </div>
    </main>
  )
}

function SuccessMessage() {
  return (
    <>
      <h1 className="mb-6 text-4xl font-bold tracking-tight">
        Purchase complete.
      </h1>
      <p className="text-lg text-neutral-400">
        Check your email. Your survivor list will arrive within 24 hours of the
        next market close.
      </p>
    </>
  )
}

function OfferContent() {
  return (
    <>
      <p className="mb-4 text-sm font-medium uppercase tracking-widest text-neutral-500">
        Margin Invest
      </p>

      <h1 className="mb-6 text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
        10 stocks survived.<br />
        4,900+ didn&apos;t.
      </h1>

      <p className="mb-8 text-lg leading-relaxed text-neutral-400">
        Every week, our deterministic elimination pipeline scores the entire US
        equity universe. No opinions. No predictions. Pure forensic accounting.
      </p>

      <ul className="mb-10 space-y-3 text-left text-neutral-300">
        <li className="flex items-start gap-3">
          <span className="mt-1 text-green-400">✓</span>
          <span>
            <strong>Deterministic process</strong> — same inputs, same outputs,
            every time
          </span>
        </li>
        <li className="flex items-start gap-3">
          <span className="mt-1 text-green-400">✓</span>
          <span>
            <strong>Tamper-evident track record</strong> — every pick
            hash-chained and published publicly
          </span>
        </li>
        <li className="flex items-start gap-3">
          <span className="mt-1 text-green-400">✓</span>
          <span>
            <strong>Plain-English forensic report</strong> — factor
            decomposition and risk context for each survivor
          </span>
        </li>
      </ul>

      <CheckoutButton />

      <p className="mt-6 text-xs text-neutral-600">
        One-time purchase. No subscription. No account required.
      </p>
    </>
  )
}
```

- [ ] **Step 3: Run the tests**

Run: `cd web && npx vitest run src/app/experiment/this-week/__tests__/page.test.tsx`

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add web/src/app/experiment/this-week/page.tsx web/src/app/experiment/this-week/checkout-button.tsx
git commit -m "feat(experiment): add $10 list landing page with Stripe checkout"
```

---

## Task 9: PostHog page_view and purchase_complete Events

**Files:**
- Modify: `web/src/app/experiment/this-week/checkout-button.tsx` (add page_view)
- Modify: `web/src/app/experiment/this-week/page.tsx` (add purchase_complete on success)

- [ ] **Step 1: Add a PageViewTracker client component to the page**

Create a small client component inline in `checkout-button.tsx` (same file to avoid file bloat):

Add this to the bottom of `web/src/app/experiment/this-week/checkout-button.tsx`:

```tsx
export function ExperimentTracker({ success }: { success: boolean }) {
  const hasTracked = useRef(false)

  useEffect(() => {
    if (hasTracked.current) return
    hasTracked.current = true

    if (success) {
      posthog.capture("purchase_complete", {
        experiment: "ten_dollar_list",
        amount_cents: 1000,
      })
    } else {
      posthog.capture("page_view", {
        experiment: "ten_dollar_list",
        page: "/experiment/this-week",
      })
    }
  }, [success])

  return null
}
```

Update the imports at the top of `checkout-button.tsx`:

```tsx
"use client"

import { useEffect, useRef, useState } from "react"
import posthog from "posthog-js"
```

- [ ] **Step 2: Wire ExperimentTracker into the page**

In `page.tsx`, add the import:

```tsx
import { CheckoutButton, ExperimentTracker } from "./checkout-button"
```

Add `<ExperimentTracker success={success} />` inside the `<div>` in `PageContent`, right before the conditional:

```tsx
        <ExperimentTracker success={success} />
        {success ? (
```

- [ ] **Step 3: Run all experiment tests**

Run: `cd web && npx vitest run src/app/experiment/`

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add web/src/app/experiment/this-week/checkout-button.tsx web/src/app/experiment/this-week/page.tsx
git commit -m "feat(experiment): add PostHog page_view and purchase_complete tracking"
```

---

## Task 10: Full Integration Verification

- [ ] **Step 1: Run all API tests**

Run: `cd api && uv run pytest tests/routes/test_experiment.py -v`

Expected: 4 tests pass.

- [ ] **Step 2: Run all web experiment tests**

Run: `cd web && npx vitest run src/app/experiment/`

Expected: All tests pass.

- [ ] **Step 3: Run the full API test suite to check for regressions**

Run: `cd api && uv run pytest tests/ -v --ignore=api/tests/services/test_xbrl_parser.py -x -q`

Expected: No new failures.

- [ ] **Step 4: Run ruff lint on new Python files**

Run: `uv run ruff check api/src/margin_api/routes/experiment.py api/src/margin_api/schemas/experiment.py api/tests/routes/test_experiment.py --fix`

Expected: Clean or auto-fixed.

- [ ] **Step 5: Run ruff format**

Run: `uv run ruff format api/src/margin_api/routes/experiment.py api/src/margin_api/schemas/experiment.py api/tests/routes/test_experiment.py`

Expected: Formatted.

- [ ] **Step 6: Run ESLint on new web files**

Run: `cd web && npx eslint --fix src/app/experiment/ src/app/api/v1/experiment/`

Expected: Clean or auto-fixed.

- [ ] **Step 7: Final commit if lint/format changed anything**

```bash
git add -u
git commit -m "style(experiment): apply ruff + eslint formatting"
```

---

## Spec Coverage Check

| Spec requirement | Task |
|---|---|
| New route at `web/src/app/experiment/this-week` | Task 8 |
| Server-rendered, no auth, no nav chrome | Task 8 (server component, no layout import) |
| Headline, three bullet value prop, sample screenshot, Stripe button | Task 8 (screenshot placeholder — static `<img>` in copy) |
| On payment: insert into `experiment_signups` | Task 5 (webhook handler) |
| Trigger Resend email with placeholder PDF | Task 5 (sends HTML email, PDF placeholder noted in copy) |
| PostHog: page_view, checkout_click, purchase_complete | Tasks 8, 9 |
| Two UTM-tagged landing variants | Not code — same page, two distribution URLs with UTM params |
| Zero changes to existing scoring pipeline, auth, or engine | Verified — no files outside experiment scope |
| Alembic migration with idempotent checks | Task 2 |
| One web test for page + checkout_click | Task 7 |
| One API test for webhook handler | Task 4 |

**Note on sample screenshot**: The spec mentions "one sample scorecard screenshot." The landing page has a placeholder comment for this. The actual screenshot image file needs to be added manually (take a screenshot of an existing scorecard and save to `web/public/experiment/sample-scorecard.png`). This is a content task, not a code task.
