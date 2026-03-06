# Sentry + PostHog Integration Design

**Date:** 2026-03-05
**Status:** Approved
**Approach:** Manual setup (no wizards)

## Overview

Add Sentry (error tracking) and PostHog (analytics + feature flags) to Margin Invest. Both are independent SDK installs with no code conflicts. This is the highest-impact tooling addition — the project currently has zero error visibility and zero analytics.

## Prerequisites (Manual, Before Code)

### Sentry
1. Create a Sentry account/org at sentry.io
2. Create two projects: "Next.js" (frontend) and "Python/FastAPI" (backend)
3. Note the DSN values for each
4. Generate an auth token for source map uploads

### PostHog
1. Create a PostHog account at posthog.com
2. Create a project, note the API key and host URL (likely `https://us.i.posthog.com`)

## Part 1: Sentry — Next.js Frontend

### Package
`@sentry/nextjs`

### Files to Create

**`web/sentry.client.config.ts`**
- Browser SDK init
- DSN from `NEXT_PUBLIC_SENTRY_DSN`
- `tracesSampleRate: 0.1`
- `replaysSessionSampleRate: 0`, `replaysOnErrorSampleRate: 1.0` (replay only on errors)
- Environment from `NEXT_PUBLIC_SENTRY_ENVIRONMENT`, default `"development"`

**`web/sentry.server.config.ts`**
- Server SDK init, same DSN
- `tracesSampleRate: 0.1`

**`web/sentry.edge.config.ts`**
- Edge runtime init, same DSN
- `tracesSampleRate: 0.1`

**`web/src/app/global-error.tsx`**
- Root error boundary (client component)
- Calls `Sentry.captureException(error)`
- Renders minimal error UI with reset button
- Catches hydration errors and top-level throws

**`web/src/instrumentation.ts`**
- Imports sentry server config for Next.js 16 server-side instrumentation hooks

### Files to Modify

**`web/next.config.ts`**
- Wrap export with `withSentryConfig()`
- Options: `widenClientFileUpload: true`, `hideSourceMaps: true`
- Source map upload via `SENTRY_AUTH_TOKEN`
- Add to CSP `script-src`: `https://browser.sentry-cdn.com`
- Add to CSP `connect-src`: `https://*.ingest.sentry.io`
- Keep report-only mode

## Part 2: Sentry — FastAPI Backend + ARQ Worker

### Package
`sentry-sdk[fastapi]` (added to margin-api via uv)

### API — Modify `api/src/margin_api/app.py`
- Call `sentry_sdk.init()` early in `create_app()`, before middleware/routes
- DSN from `SENTRY_DSN` env var (no init if not set — safe for local dev)
- Integrations: `FastApiIntegration`, `SqlalchemyIntegration`, `AsyncPGIntegration`
- `traces_sample_rate=0.1`, `send_default_pii=False`
- Environment from `SENTRY_ENVIRONMENT`
- Add `sentry_sdk.capture_exception(exc)` inside existing `unhandled_exception_handler` before returning 500

### Worker — Modify `api/src/margin_api/workers.py`
- Call `sentry_sdk.init()` in `WorkerSettings.on_startup`
- Same DSN and config as API, without `FastApiIntegration`
- Sentry auto-captures unhandled exceptions in async contexts — no manual job wrapping needed

## Part 3: PostHog — Next.js Frontend

### Package
`posthog-js`

### Files to Create

**`web/src/lib/posthog/provider.tsx`**
- Client component
- Initializes PostHog with `NEXT_PUBLIC_POSTHOG_KEY` and `NEXT_PUBLIC_POSTHOG_HOST`
- Config: `capture_pageview: false` (manual SPA tracking), `capture_pageleave: true`
- Wraps children in `PostHogProvider` from `posthog-js/react`

**`web/src/lib/posthog/pageview.tsx`**
- Client component
- Uses `usePathname()` + `useSearchParams()` to fire `posthog.capture('$pageview')` on route changes via `useEffect`

**`web/src/lib/posthog/identify.tsx`**
- Client component
- Reads `useSession()` from NextAuth
- When authenticated: `posthog.identify(session.userId, { email })` + `posthog.alias(email)`
- On session loss (logout): `posthog.reset()`

### Files to Modify

**`web/src/app/layout.tsx`**
- Add PostHog provider inside SessionProvider, wrapping the content div
- Add `<Suspense>`-wrapped `PostHogPageview` component
- Provider ordering: `ThemeProvider > SessionProvider > PHProvider > content`

**`web/next.config.ts`**
- Add `https://us.i.posthog.com` to CSP `script-src` and `connect-src` (same arrays already touched for Sentry)

## Part 4: PostHog — FastAPI Backend (Server-Side)

### Package
`posthog` (added to margin-api via uv)

### Files to Create

**`api/src/margin_api/services/analytics.py`**
- Thin wrapper around PostHog Python client
- Initializes with `POSTHOG_API_KEY` and `POSTHOG_HOST` env vars
- Exposes `track_event(distinct_id, event, properties)` and `shutdown()`
- No-ops gracefully if env vars not set (safe for local dev/tests)

### Files to Modify

**`api/src/margin_api/app.py`**
- Call `analytics.shutdown()` in a shutdown handler to flush pending events

### Initial Events
No events wired in this session — just the client and lifecycle. Wiring specific events (score_published, subscription_created) is deferred to avoid scope creep.

## Part 5: Verification

### Automated (must pass before merge)
1. `cd web && npx vitest run` — all ~1285 tests pass
2. `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py` — all ~1587 tests pass
3. `uv run pytest engine/tests/ -v` — all ~2621 tests pass
4. `cd web && npx eslint --fix .` — clean
5. `uv run ruff check --fix . && uv run ruff format .` — clean
6. `cd web && npx next build` — builds without errors

### Manual (post-deploy)
- Trigger test error in web app -> confirm in Sentry dashboard
- Hit broken API endpoint -> confirm exception in Sentry backend project
- Load page -> confirm `$pageview` in PostHog
- Log in -> confirm `identify` links user
- Navigate between pages -> confirm SPA pageviews tracked

## Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `NEXT_PUBLIC_SENTRY_DSN` | Vercel + `.env.local` | Frontend Sentry DSN |
| `NEXT_PUBLIC_SENTRY_ENVIRONMENT` | Vercel | `production` / `development` |
| `SENTRY_AUTH_TOKEN` | Vercel (build-time) | Source map upload |
| `SENTRY_DSN` | Railway | Backend Sentry DSN |
| `SENTRY_ENVIRONMENT` | Railway | `production` |
| `NEXT_PUBLIC_POSTHOG_KEY` | Vercel + `.env.local` | PostHog project API key |
| `NEXT_PUBLIC_POSTHOG_HOST` | Vercel + `.env.local` | `https://us.i.posthog.com` |
| `POSTHOG_API_KEY` | Railway | Server-side PostHog |
| `POSTHOG_HOST` | Railway | `https://us.i.posthog.com` |

## Decisions Made
- **Approach:** Manual setup, no wizards
- **PostHog user ID:** Database userId as distinct_id, email as alias (both)
- **CSP:** Keep report-only mode, add Sentry + PostHog domains
- **Server-side PostHog:** Included — client + lifecycle only, no events wired yet
- **Testing:** No new test files — verify existing suites don't regress
