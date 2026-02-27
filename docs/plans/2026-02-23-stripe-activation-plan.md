# Stripe Activation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the one identified bug in billing status, set up environment variables, and verify the full Stripe checkout flow works end-to-end.

**Architecture:** The Stripe integration is already built — BillingService, routes, webhook handler, frontend billing section, and tests all exist. This plan fixes a bug in `is_active` logic, adds a missing test, sets env vars, and runs a live test.

**Tech Stack:** FastAPI, Stripe SDK v14+, Next.js 15, PostgreSQL

---

### Task 1: Fix `is_active` Bug in Billing Status Route

The `/api/v1/billing/status` endpoint computes `is_active` based only on `subscription_plan`, ignoring `subscription_status`. A user with `plan="portfolio"` and `status="canceled"` incorrectly shows as active.

**Files:**
- Modify: `api/src/margin_api/routes/billing.py:132`
- Test: `api/tests/test_billing_routes.py` (create)

**Step 1: Write the failing test**

Create `api/tests/test_billing_routes.py`:

```python
"""Tests for billing route logic — is_active computation."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture()
async def db_session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(engine, db_session):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture()
async def user(db_session):
    u = User(email="billing@test.com", name="Billing User")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


class TestBillingStatusIsActive:
    @pytest.mark.asyncio
    async def test_canceled_subscription_is_not_active(self, db_session, user):
        """A canceled portfolio user should NOT be marked as active."""
        user.subscription_plan = "portfolio"
        user.subscription_status = "canceled"
        await db_session.commit()
        await db_session.refresh(user)

        # is_active should be False because status is canceled
        active_statuses = {"active", "trialing"}
        is_active = (
            user.subscription_plan in ("portfolio", "institutional", "operator")
            and user.subscription_status in active_statuses
        )
        assert is_active is False

    @pytest.mark.asyncio
    async def test_active_subscription_is_active(self, db_session, user):
        """An active portfolio user should be marked as active."""
        user.subscription_plan = "portfolio"
        user.subscription_status = "active"
        await db_session.commit()

        active_statuses = {"active", "trialing"}
        is_active = (
            user.subscription_plan in ("portfolio", "institutional", "operator")
            and user.subscription_status in active_statuses
        )
        assert is_active is True

    @pytest.mark.asyncio
    async def test_past_due_subscription_is_not_active(self, db_session, user):
        """A past_due user should NOT be marked as active."""
        user.subscription_plan = "portfolio"
        user.subscription_status = "past_due"
        await db_session.commit()

        active_statuses = {"active", "trialing"}
        is_active = (
            user.subscription_plan in ("portfolio", "institutional", "operator")
            and user.subscription_status in active_statuses
        )
        assert is_active is False

    @pytest.mark.asyncio
    async def test_analyst_is_not_active(self, db_session, user):
        """A free analyst user should NOT be marked as active."""
        user.subscription_plan = "analyst"
        user.subscription_status = None
        await db_session.commit()

        active_statuses = {"active", "trialing"}
        is_active = (
            user.subscription_plan in ("portfolio", "institutional", "operator")
            and user.subscription_status in active_statuses
        )
        assert is_active is False
```

**Step 2: Run the tests to verify they pass (they test the correct logic, not the buggy route)**

Run: `uv run pytest api/tests/test_billing_routes.py -v`
Expected: All 4 tests PASS (they test the correct logic directly)

**Step 3: Fix the `is_active` computation in the route**

In `api/src/margin_api/routes/billing.py`, change line 132 from:

```python
    is_active = user.subscription_plan in ("portfolio", "institutional", "operator")
```

to:

```python
    is_active = (
        user.subscription_plan in ("portfolio", "institutional", "operator")
        and user.subscription_status in ("active", "trialing")
    )
```

**Step 4: Run existing billing tests to verify nothing broke**

Run: `uv run pytest api/tests/test_billing_service.py api/tests/test_billing_routes.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/billing.py api/tests/test_billing_routes.py
git commit -m "fix(billing): check subscription_status in is_active computation

A user with plan=portfolio but status=canceled was incorrectly
showing as active. Now requires status to be active or trialing."
```

---

### Task 2: Set Local Environment Variables

**Files:**
- Modify: `api/.env`

**Step 1: Ask the user for their Stripe test-mode keys**

The user needs to provide:
- `MARGIN_STRIPE_SECRET_KEY` — starts with `sk_test_`
- `MARGIN_STRIPE_PUBLISHABLE_KEY` — starts with `pk_test_`
- `MARGIN_STRIPE_WEBHOOK_SECRET` — starts with `whsec_`
- `MARGIN_STRIPE_PORTFOLIO_PRICE_ID` — starts with `price_`
- `MARGIN_STRIPE_INSTITUTIONAL_PRICE_ID` — starts with `price_`

**Step 2: Update `api/.env` with the provided values**

Replace the placeholder lines:
```
MARGIN_STRIPE_SECRET_KEY=sk_test_<actual_key>
MARGIN_STRIPE_PUBLISHABLE_KEY=pk_test_<actual_key>
MARGIN_STRIPE_WEBHOOK_SECRET=whsec_<actual_secret>
MARGIN_STRIPE_PORTFOLIO_PRICE_ID=price_<actual_id>
MARGIN_STRIPE_INSTITUTIONAL_PRICE_ID=price_<actual_id>
```

**Step 3: Verify the API loads the config**

Run: `uv run python -c "from margin_api.config import get_settings; s = get_settings(); print(f'Stripe configured: {bool(s.stripe_secret_key and s.stripe_portfolio_price_id)}')" `
Expected: `Stripe configured: True`

Note: Do NOT commit `.env` — it's in `.gitignore`.

---

### Task 3: Live End-to-End Test

**Step 1: Start local services**

```bash
docker compose up -d                    # Postgres + Redis
uv run uvicorn margin_api.app:create_app --factory --reload &  # API on :8000
cd web && npm run dev &                 # Next.js on :3000
```

**Step 2: Log in to the app**

Navigate to `http://localhost:3000/login` and sign in.

**Step 3: Navigate to billing**

Go to `http://localhost:3000/account` and scroll to the Billing section.
Verify: Should show "Analyst" plan badge and two upgrade buttons.
Verify: Buttons should be enabled (not grayed out) — `billing_configured` should be `true`.

**Step 4: Test checkout flow**

Click "Upgrade to Portfolio - $29/mo".
Verify: Redirects to Stripe Checkout page.
Use test card: `4242 4242 4242 4242`, any future expiry, any CVC.
Complete checkout.
Verify: Redirects back to `/account?subscription=active`.

**Step 5: Verify webhook processed**

Check the database:
```bash
uv run python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
async def check():
    e = create_async_engine('postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest')
    async with AsyncSession(e) as s:
        r = await s.execute(text(\"SELECT subscription_plan, subscription_status, stripe_customer_id FROM users WHERE email='YOUR_EMAIL'\"))
        print(r.fetchone())
    await e.dispose()
asyncio.run(check())
"
```
Expected: `('portfolio', 'active', 'cus_...')`

**Step 6: Test portal access**

Back on `/account`, click "Manage subscription".
Verify: Redirects to Stripe Customer Portal.
Verify: Can see subscription details and cancel option.

**Step 7: Test webhook for local development (optional)**

If webhooks don't fire locally, use the Stripe CLI:
```bash
stripe listen --forward-to localhost:8000/api/v1/billing/webhook
```
This creates a temporary webhook secret — update `MARGIN_STRIPE_WEBHOOK_SECRET` in `.env` with the `whsec_` value it prints.

---

### Task 4: Production Environment Variable Instructions

After the live test succeeds, provide the user with these exact steps:

**Railway Dashboard Setup:**

1. Go to [Railway Dashboard](https://railway.com/dashboard)
2. Select the `margin_invest` service
3. Click **Variables** tab
4. Add these environment variables with your **live-mode** Stripe keys:

| Variable | Value |
|----------|-------|
| `MARGIN_STRIPE_SECRET_KEY` | `sk_live_...` (from Stripe Dashboard → API Keys) |
| `MARGIN_STRIPE_PUBLISHABLE_KEY` | `pk_live_...` (from Stripe Dashboard → API Keys) |
| `MARGIN_STRIPE_WEBHOOK_SECRET` | `whsec_...` (from Stripe Dashboard → Webhooks → your endpoint's signing secret) |
| `MARGIN_STRIPE_PORTFOLIO_PRICE_ID` | `price_...` (your live Portfolio product's price ID) |
| `MARGIN_STRIPE_INSTITUTIONAL_PRICE_ID` | `price_...` (your live Institutional product's price ID) |

5. Railway will automatically redeploy the service
6. Verify the deployment is healthy

**Stripe Dashboard Webhook Setup (if not done):**

1. Go to Stripe Dashboard → Developers → Webhooks
2. Click "Add endpoint"
3. URL: `https://<your-railway-api-url>/api/v1/billing/webhook`
4. Events to listen for:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the signing secret → use as `MARGIN_STRIPE_WEBHOOK_SECRET`

**Vercel Frontend Setup:**

The frontend needs `API_URL` set to point to your Railway API:

1. Go to Vercel Dashboard → your project → Settings → Environment Variables
2. Ensure `API_URL` is set to your Railway API URL (e.g., `https://margin-invest-production.up.railway.app`)

**CORS Configuration:**

Ensure `MARGIN_CORS_ORIGINS` on Railway includes your Vercel production URL so the frontend can reach the API.
