# Account Page & Billing Integration Design

**Date:** 2026-02-17
**Status:** Approved

## Summary

Build a production-ready `/account` page that consolidates identity, security, and billing management. Replace the current `/settings` page's account and billing sections. Integrate Stripe subscriptions with three tiers (Scout, Operator, Allocator) using Stripe Customer Portal for self-serve management.

## Decisions

### Auth Provider: NextAuth v5 (Keep Existing)

- Already implemented with Google, GitHub, and credentials+Argon2id
- Custom TOTP + WebAuthn MFA built and working for credentials users
- JWT session strategy with `userId`, `authMethod`, `mfaVerified` in token
- `userId` maps to `stripe_customer_id` via DB — no adapter needed
- Route protection via `auth()` server-side check works today
- No migration risk or vendor lock-in
- Free (self-hosted)
- OAuth users rely on provider MFA; credentials users have mandatory TOTP/WebAuthn

### Page Split

- `/account` — identity, auth method, password, MFA, billing
- `/settings` — product preferences (placeholder for now, future use)
- API Keys section removed entirely (universe-level keys handled on backend later)

### Billing UX: Stripe Customer Portal

- Plan status displayed inline on `/account`
- "Manage Subscription" opens Stripe's hosted Customer Portal
- Portal handles plan changes, cancellation, payment method updates, invoices
- No custom PCI-compliant card input needed

## Plan Tiers

| Plan | Price | Stripe Config Key |
|------|-------|-------------------|
| Scout | Free | N/A |
| Operator | $29/mo | `STRIPE_OPERATOR_PRICE_ID` |
| Allocator | $79/mo | `STRIPE_ALLOCATOR_PRICE_ID` |

## Routing & Access

| Route | Auth Required | Behavior |
|-------|---------------|----------|
| `/account` | Yes | Redirect to `/login` if no session |
| `/settings` | Yes | Placeholder — "Product preferences coming soon" |

- No auth loops — login page does not redirect authenticated users
- No re-auth prompts for logged-in users
- Backend billing routes update return URLs from `/settings` to `/account`

## `/account` Page Layout

Three stacked card sections:

```
┌─ Profile ────────────────────────────────┐
│ Avatar (upload/remove) · Name · Email    │
│ Auth method badge (Google / GitHub /     │
│   Facebook / X / Amazon / Email+Password)│
└──────────────────────────────────────────┘

┌─ Security ───────────────────────────────┐
│ [credentials only]                       │
│   Change Password (inline form)          │
│   MFA status + manage link               │
│ [oauth only]                             │
│   "Secured by {Provider}" note           │
└──────────────────────────────────────────┘

┌─ Plan & Billing ─────────────────────────┐
│ Plan badge: Scout / Operator / Allocator │
│ Status pill: active / trialing /         │
│   past_due / canceled                    │
│ Renewal date or access-until date        │
│ [Upgrade] → Stripe Checkout              │
│ [Manage Subscription] → Stripe Portal    │
└──────────────────────────────────────────┘
```

## Backend Changes

### New Endpoint: `POST /api/v1/auth/change-password`

- Input: `current_password`, `new_password`
- Validates current password against Argon2id hash
- Enforces password strength (min 8 chars)
- Updates `CredentialUser.password_hash`
- Sets `password_changed_at` timestamp
- Resets `failed_login_attempts` to 0
- Returns success or error

### New Column: `CredentialUser.password_changed_at`

- `DateTime(timezone=True)`, nullable, default null
- Alembic migration required
- JWT callback: if `password_changed_at > token.iat`, force re-auth (invalidates other sessions)

### Billing Model Updates

Both `User` and `CredentialUser` models:

- `subscription_plan` — values change from `"free"/"margin_invest"` to `"scout"` (default), `"operator"`, `"allocator"`
- New column: `subscription_status` — `"active"`, `"trialing"`, `"past_due"`, `"canceled"`, or null
- New column: `current_period_end` — `DateTime(timezone=True)`, nullable

Alembic migration: rename existing plan values (`"free"` → `"scout"`, `"margin_invest"` → `"operator"`), add new columns.

### Billing Service Updates

- Accept multiple price IDs instead of single `stripe_price_id`
- Config: `STRIPE_OPERATOR_PRICE_ID`, `STRIPE_ALLOCATOR_PRICE_ID`
- `create_checkout_session` takes a `plan` parameter (`"operator"` or `"allocator"`)
- `handle_subscription_change` extracts price ID from Stripe subscription to map to plan name
- Stores `status` + `current_period_end` from Stripe subscription object
- Return URLs change from `/settings` to `/account`

### `BillingStatusResponse` Expansion

```python
class BillingStatusResponse(BaseModel):
    plan: str                          # "scout" | "operator" | "allocator"
    status: str | None                 # "active" | "trialing" | "past_due" | "canceled"
    current_period_end: datetime | None
    is_active: bool                    # status in ("active", "trialing")
```

### New Frontend Proxy Routes

- `POST /api/v1/billing/checkout` — proxy with auth headers
- `POST /api/v1/billing/portal` — proxy with auth headers

Existing: `GET /api/v1/billing/status` (already proxied).

## Frontend Components

### New Files

```
web/src/app/account/page.tsx                  (server component, auth-gated)
web/src/components/account/profile-section.tsx (migrated from settings/account-section)
web/src/components/account/security-section.tsx
web/src/components/account/billing-section.tsx (refactored from settings/billing-section)
```

### Deleted Files

```
web/src/components/settings/account-section.tsx
web/src/components/settings/billing-section.tsx
web/src/components/settings/api-keys-section.tsx
```

### `ProfileSection`

- Migrated avatar upload/remove logic from existing `AccountSection`
- Auth method badge: reads `session.authMethod`, displays provider name
- OAuth: "Signed in with {Provider}" pill
- Credentials: "Email & Password" pill
- Extensible — any new provider string gets capitalized label + fallback icon

### `SecuritySection`

Credentials users:
- **Change Password** — inline form: current password, new password, confirm. Calls `POST /api/v1/auth/change-password`. Success message notes other sessions were signed out.
- **MFA** — shows status (always enabled for credentials). "Manage MFA" links to `/mfa/setup`. Placeholder for future inline management and recovery codes.

OAuth users:
- "Your account is secured by {Provider}. Password and MFA are managed through your {Provider} account."

### `BillingSection`

- Plan badge with tier styling: Scout (muted), Operator (accent), Allocator (gold)
- Status pill: active (green), trialing (blue), past_due (warning), canceled (red)
- Renewal date: "Renews {date}" or "Access until {date}" if canceled
- Scout users: upgrade cards for Operator ($29/mo) and Allocator ($79/mo) → Stripe Checkout
- Paid users: "Manage Subscription" → Stripe Customer Portal
- Placeholder: "Billing history" link pointing to Portal invoice section

### `/settings` Page (Gutted)

- Remove all section imports
- Show: "Product preferences coming soon" placeholder card
- Route stays alive for future use

### Navigation

- "Account" → `/account` (already in dropdown, unchanged)
- Remove "Settings" from dropdown (page is now placeholder)

## Security Edge Cases

### Session Invalidation on Password Change

- `password_changed_at` stored on `CredentialUser`
- JWT callback: on token refresh, if `authMethod === "credentials"` and `password_changed_at > token.iat`, return empty token (forces re-auth)
- Current session gets fresh token immediately after change

### MFA Recovery

- Recovery codes are a future addition (placeholder in Security section)
- MFA is mandatory for credentials users — no disable option exposed
- MFA management links to existing `/mfa/setup` page

### Stripe Race Conditions

- Webhooks are the single source of truth for subscription state
- `handle_subscription_change` updates `plan`, `status`, `current_period_end` atomically
- If webhook arrives before checkout redirect: user sees updated plan on next load
- `past_due`: user retains plan name, `is_active` returns false, UI shows warning + "Update payment method" CTA → Portal

### Entitlement Gating

- Server-side: `require_plan()` FastAPI dependency checks DB
- No client-side trust for feature gating
- Frontend fetches billing status client-side via `useEffect` for display only
- All data access gated on the API layer

### Checkout with Multiple Plans

- Frontend sends `plan: "operator" | "allocator"` to checkout endpoint
- Backend maps plan → Stripe Price ID via config
- Upgrade between paid tiers: handled by Stripe Customer Portal (automatic proration)
