# Stripe Activation Design

**Date:** 2026-02-23
**Status:** Approved
**Type:** Verification & Activation (not greenfield)

## Overview

The Stripe billing integration already exists in the codebase. This effort audits the existing code for correctness, fixes any gaps, and activates it with real credentials.

## Deliverables

1. **Code audit** — Review every file in the billing chain, identify bugs or gaps, fix them
2. **Env var instructions** — Exact steps to set keys locally and in Railway production
3. **Live test** — Walk through a Stripe test-mode checkout to confirm the full flow

## Out of Scope

No new features: no pricing page, trial periods, usage-based billing, or feature gating.

## Audit Chain

Files reviewed in data-flow order:

### Backend (request path)
1. `api/src/margin_api/config.py` — Stripe config vars
2. `api/src/margin_api/schemas/billing.py` — Request/response models
3. `api/src/margin_api/services/billing.py` — Core Stripe API calls
4. `api/src/margin_api/routes/billing.py` — Route handlers + auth
5. `api/src/margin_api/db/models.py` — User subscription fields

### Frontend (UI path)
6. `web/src/app/api/v1/billing/checkout/route.ts` — Next.js proxy route
7. `web/src/app/api/v1/billing/portal/route.ts` — Portal proxy route
8. `web/src/app/api/v1/billing/status/route.ts` — Status proxy route
9. `web/src/components/account/billing-section.tsx` — Billing UI

### Tests
10. `api/tests/test_billing_service.py` — Verify test coverage

## Live Test Plan

1. Set local env vars with Stripe test keys
2. Start local services (Postgres, Redis, API, Next.js)
3. Test checkout with Stripe test card `4242 4242 4242 4242`
4. Verify webhook updates subscription status in database
5. Test Customer Portal access
6. Provide production env var instructions for Railway
