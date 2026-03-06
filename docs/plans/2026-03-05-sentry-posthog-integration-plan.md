# Sentry + PostHog Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Sentry error tracking and PostHog analytics to both the Next.js frontend and FastAPI backend, with zero regressions to the existing ~5,500 test suite.

**Architecture:** Two independent SDK installs (Sentry + PostHog) across two deployment targets (Vercel for Next.js, Railway for FastAPI/ARQ). Both SDKs guard on env vars — no-op when not set, so local dev and tests are unaffected. PostHog identifies users by database ID with email alias.

**Tech Stack:** @sentry/nextjs, sentry-sdk[fastapi], posthog-js, posthog (Python)

**Design doc:** `docs/plans/2026-03-05-sentry-posthog-integration-design.md`

---

### Task 1: Install @sentry/nextjs and create client config

**Files:**
- Create: `web/sentry.client.config.ts`

**Step 1: Install the package**

Run: `cd /Users/brandon/repos/margin_invest/web && npm install @sentry/nextjs`

**Step 2: Create `web/sentry.client.config.ts`**

```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 1.0,
});
```

**Step 3: Run web tests to verify no regressions**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All ~1285 tests pass. Sentry init is guarded by DSN env var (undefined in test env = no-op).

**Step 4: Commit**

```bash
git add web/sentry.client.config.ts web/package.json web/package-lock.json
git commit -m "feat(web): add @sentry/nextjs with client config"
```

---

### Task 2: Create server and edge Sentry configs

**Files:**
- Create: `web/sentry.server.config.ts`
- Create: `web/sentry.edge.config.ts`

**Step 1: Create `web/sentry.server.config.ts`**

```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
  tracesSampleRate: 0.1,
});
```

**Step 2: Create `web/sentry.edge.config.ts`**

```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
  tracesSampleRate: 0.1,
});
```

**Step 3: Commit**

```bash
git add web/sentry.server.config.ts web/sentry.edge.config.ts
git commit -m "feat(web): add Sentry server and edge configs"
```

---

### Task 3: Create instrumentation.ts for Next.js server-side hooks

**Files:**
- Create: `web/src/instrumentation.ts`

**Step 1: Create `web/src/instrumentation.ts`**

Next.js 16 uses this file for server-side instrumentation. Sentry v8+ requires it.

```typescript
import * as Sentry from "@sentry/nextjs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("../sentry.server.config");
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("../sentry.edge.config");
  }
}

export const onRequestError = Sentry.captureRequestError;
```

**Step 2: Run web tests to verify no regressions**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All tests pass.

**Step 3: Commit**

```bash
git add web/src/instrumentation.ts
git commit -m "feat(web): add Sentry instrumentation hook for server/edge"
```

---

### Task 4: Create global-error.tsx root error boundary

**Files:**
- Create: `web/src/app/global-error.tsx`

**Step 1: Create `web/src/app/global-error.tsx`**

This is the root error boundary for the app router. It catches unhandled errors including hydration failures. Must be a client component. Must render its own `<html>` and `<body>` tags (Next.js requirement for global-error).

```tsx
"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <div style={{ padding: "2rem", fontFamily: "system-ui, sans-serif" }}>
          <h2>Something went wrong</h2>
          <p>An unexpected error occurred. The issue has been reported.</p>
          <button
            onClick={() => reset()}
            style={{
              marginTop: "1rem",
              padding: "0.5rem 1rem",
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
```

**Step 2: Run web tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All tests pass.

**Step 3: Commit**

```bash
git add web/src/app/global-error.tsx
git commit -m "feat(web): add global-error boundary with Sentry capture"
```

---

### Task 5: Wrap next.config.ts with withSentryConfig and update CSP

**Files:**
- Modify: `web/next.config.ts`

**Step 1: Modify `web/next.config.ts`**

Add `@sentry/nextjs` import, update CSP directives to include Sentry and PostHog domains (doing both now since we're already editing CSP), wrap export with `withSentryConfig`.

The full file should become:

```typescript
import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const cspDirectives = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://app.termly.io https://browser.sentry-cdn.com https://us.i.posthog.com",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://lh3.googleusercontent.com https://avatars.githubusercontent.com https://app.termly.io",
  "font-src 'self'",
  "connect-src 'self' https://api.stripe.com wss: https://app.termly.io https://vitals.termly.io https://*.ingest.sentry.io https://us.i.posthog.com",
  "frame-src https://js.stripe.com https://hooks.stripe.com https://app.termly.io",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
];

const csp = cspDirectives.join("; ");

const nextConfig: NextConfig = {
  transpilePackages: ["three"],
  async headers() {
    return [
      {
        source: "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-DNS-Prefetch-Control", value: "off" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
          { key: "Content-Security-Policy-Report-Only", value: csp },
        ],
      },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  widenClientFileUpload: true,
  hideSourceMaps: true,
  silent: !process.env.SENTRY_AUTH_TOKEN,
});
```

Note: `silent: !process.env.SENTRY_AUTH_TOKEN` suppresses source map upload warnings in local dev where the token isn't set.

**Step 2: Run web tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All tests pass.

**Step 3: Verify build succeeds**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next build`
Expected: Build completes. Source map upload will be skipped (no SENTRY_AUTH_TOKEN locally) but build should succeed.

**Step 4: Lint**

Run: `cd /Users/brandon/repos/margin_invest/web && npx eslint --fix .`
Expected: Clean.

**Step 5: Commit**

```bash
git add web/next.config.ts
git commit -m "feat(web): wrap next.config with withSentryConfig, add Sentry+PostHog to CSP"
```

---

### Task 6: Add Sentry to FastAPI backend

**Files:**
- Modify: `api/src/margin_api/app.py`

**Step 1: Install package**

Run: `cd /Users/brandon/repos/margin_invest && uv add sentry-sdk[fastapi] --package margin-api`

**Step 2: Modify `api/src/margin_api/app.py`**

Add Sentry initialization at the top of `create_app()`, before any middleware or route registration. Add `sentry_sdk.capture_exception(exc)` to the existing unhandled exception handler.

Add these imports at the top of the file:

```python
import os
import sentry_sdk
```

Add this block at the beginning of `create_app()`, right after `settings = get_settings()` (before the localhost check):

```python
    # Sentry error tracking
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
```

Note: We do NOT explicitly list integrations. The `sentry-sdk[fastapi]` extra installs FastAPI/Starlette/SQLAlchemy/asyncpg integrations, and Sentry v2+ auto-discovers them.

Add `sentry_sdk.capture_exception(exc)` to the existing `unhandled_exception_handler`, before the `return JSONResponse(...)`:

```python
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error("[%s] Unhandled exception: %s", request_id, exc, exc_info=True)
        sentry_sdk.capture_exception(exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
                request_id=request_id,
                status_code=500,
            ).model_dump(),
        )
```

**Step 3: Run API tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py -x -q`
Expected: All ~1587 tests pass. SENTRY_DSN is not set in test env, so `sentry_sdk.init()` is not called.

**Step 4: Lint**

Run: `cd /Users/brandon/repos/margin_invest && uv run ruff check --fix . && uv run ruff format .`
Expected: Clean.

**Step 5: Commit**

```bash
git add api/pyproject.toml api/src/margin_api/app.py uv.lock
git commit -m "feat(api): add Sentry error tracking to FastAPI app"
```

---

### Task 7: Add Sentry to ARQ worker

**Files:**
- Modify: `api/src/margin_api/workers.py`

**Step 1: Add imports at the top of `workers.py`**

Add to the existing imports section (near the other stdlib imports):

```python
import os
import sentry_sdk
```

Note: `os` may already be imported — check first, only add if missing.

**Step 2: Add Sentry init to `WorkerSettings.on_startup`**

Add this block at the very beginning of `on_startup` (line ~2893), before any other logic:

```python
        # Sentry error tracking
        sentry_dsn = os.environ.get("SENTRY_DSN")
        if sentry_dsn:
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
                traces_sample_rate=0.1,
                send_default_pii=False,
            )
            logger.info("[worker] Sentry initialized")
```

**Step 3: Run API tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py -x -q`
Expected: All tests pass.

**Step 4: Commit**

```bash
git add api/src/margin_api/workers.py
git commit -m "feat(worker): add Sentry error tracking to ARQ worker startup"
```

---

### Task 8: Install posthog-js and create PostHog provider

**Files:**
- Create: `web/src/lib/posthog/provider.tsx`

**Step 1: Install the package**

Run: `cd /Users/brandon/repos/margin_invest/web && npm install posthog-js`

**Step 2: Create `web/src/lib/posthog/provider.tsx`**

```tsx
"use client";

import posthog from "posthog-js";
import { PostHogProvider as PHProvider } from "posthog-js/react";
import { useEffect } from "react";

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
      capture_pageview: false,
      capture_pageleave: true,
    });
  }, []);

  return <PHProvider client={posthog}>{children}</PHProvider>;
}
```

**Step 3: Commit**

```bash
git add web/src/lib/posthog/provider.tsx web/package.json web/package-lock.json
git commit -m "feat(web): add PostHog provider with posthog-js"
```

---

### Task 9: Create PostHog pageview tracker

**Files:**
- Create: `web/src/lib/posthog/pageview.tsx`

**Step 1: Create `web/src/lib/posthog/pageview.tsx`**

This component tracks SPA page views using Next.js router events. It fires `posthog.capture('$pageview')` on every route change.

```tsx
"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import posthog from "posthog-js";

export function PostHogPageview() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (pathname) {
      let url = window.origin + pathname;
      if (searchParams?.toString()) {
        url = url + "?" + searchParams.toString();
      }
      posthog.capture("$pageview", { $current_url: url });
    }
  }, [pathname, searchParams]);

  return null;
}
```

**Step 2: Commit**

```bash
git add web/src/lib/posthog/pageview.tsx
git commit -m "feat(web): add PostHog SPA pageview tracker"
```

---

### Task 10: Create PostHog user identification component

**Files:**
- Create: `web/src/lib/posthog/identify.tsx`

**Step 1: Create `web/src/lib/posthog/identify.tsx`**

Reads the NextAuth session and calls `posthog.identify()` when authenticated, `posthog.reset()` on logout. Uses database userId as distinct_id with email as alias.

```tsx
"use client";

import { useSession } from "next-auth/react";
import { useEffect } from "react";
import posthog from "posthog-js";

export function PostHogIdentify() {
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status === "authenticated" && session?.userId) {
      posthog.identify(session.userId, {
        email: session.user?.email,
      });
      if (session.user?.email) {
        posthog.alias(session.user.email);
      }
    } else if (status === "unauthenticated") {
      posthog.reset();
    }
  }, [session, status]);

  return null;
}
```

**Step 2: Commit**

```bash
git add web/src/lib/posthog/identify.tsx
git commit -m "feat(web): add PostHog user identification with email alias"
```

---

### Task 11: Wire PostHog into root layout

**Files:**
- Modify: `web/src/app/layout.tsx`

**Step 1: Modify `web/src/app/layout.tsx`**

Add PostHog provider inside SessionProvider, wrapping the content. Add PostHogPageview and PostHogIdentify as children. Wrap PostHogPageview in `<Suspense>` (required because it uses `useSearchParams()`).

The full file should become:

```tsx
import type { Metadata } from "next";
import Script from "next/script";
import { Suspense } from "react";
import { Inter_Tight, Geist_Mono, Instrument_Serif } from "next/font/google";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { SessionProvider } from "@/components/providers/session-provider";
import { PostHogProvider } from "@/lib/posthog/provider";
import { PostHogPageview } from "@/lib/posthog/pageview";
import { PostHogIdentify } from "@/lib/posthog/identify";
import { ConditionalFooter } from "@/components/layout/conditional-footer";
import { MfaRequiredModal } from "@/components/modals/mfa-required-modal";
import { AnalysisDisclaimerModal } from "@/components/modals/analysis-disclaimer-modal";
import "./globals.css";

const interTight = Inter_Tight({
  variable: "--font-inter-tight",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: ["400"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "Margin Invest",
  description:
    "Deterministic investment analysis — quantitative scoring without human bias",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${interTight.variable} ${geistMono.variable} ${instrumentSerif.variable} antialiased text-text-primary`}
      >
        {process.env.NEXT_PUBLIC_TERMLY_WEBSITE_UUID && (
          <Script
            src={`https://app.termly.io/resource-blocker/${process.env.NEXT_PUBLIC_TERMLY_WEBSITE_UUID}?autoBlock=on`}
            strategy="beforeInteractive"
          />
        )}
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <SessionProvider>
            <PostHogProvider>
              <Suspense fallback={null}>
                <PostHogPageview />
              </Suspense>
              <PostHogIdentify />
              <div className="min-h-screen" style={{ backgroundColor: '#0A0F0D' }}>
                {children}
                <ConditionalFooter />
                <MfaRequiredModal />
                <AnalysisDisclaimerModal />
              </div>
            </PostHogProvider>
          </SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

**Step 2: Run web tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All tests pass. PostHog won't initialize in test env (no NEXT_PUBLIC_POSTHOG_KEY).

**Step 3: Lint**

Run: `cd /Users/brandon/repos/margin_invest/web && npx eslint --fix .`
Expected: Clean.

**Step 4: Commit**

```bash
git add web/src/app/layout.tsx
git commit -m "feat(web): wire PostHog provider, pageview, and identify into root layout"
```

---

### Task 12: Add PostHog server-side client to FastAPI

**Files:**
- Create: `api/src/margin_api/services/analytics.py`
- Modify: `api/src/margin_api/app.py`

**Step 1: Install package**

Run: `cd /Users/brandon/repos/margin_invest && uv add posthog --package margin-api`

**Step 2: Create `api/src/margin_api/services/analytics.py`**

Thin wrapper. No-ops if env vars not set.

```python
"""PostHog server-side analytics client."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Lazily initialize the PostHog client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("POSTHOG_API_KEY")
    host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")

    if not api_key:
        return None

    from posthog import Posthog

    _client = Posthog(api_key, host=host)
    logger.info("[analytics] PostHog initialized (host=%s)", host)
    return _client


def track_event(distinct_id: str, event: str, properties: dict | None = None) -> None:
    """Track a server-side event. No-ops if PostHog is not configured."""
    client = _get_client()
    if client is None:
        return
    client.capture(distinct_id, event, properties=properties or {})


def shutdown() -> None:
    """Flush pending events and shut down the client."""
    global _client
    if _client is not None:
        _client.shutdown()
        _client = None
        logger.info("[analytics] PostHog shut down")
```

**Step 3: Add shutdown hook to `api/src/margin_api/app.py`**

Add this import near the top:

```python
from margin_api.services import analytics
```

Add this shutdown event inside `create_app()`, after all routes are registered (before `return app`):

```python
    @app.on_event("shutdown")
    async def shutdown_analytics():
        analytics.shutdown()
```

**Step 4: Write a quick test for the analytics module**

Create `api/tests/services/test_analytics.py`:

```python
"""Tests for PostHog analytics wrapper."""

from unittest.mock import MagicMock, patch

from margin_api.services.analytics import shutdown, track_event


def test_track_event_noop_without_env_var():
    """track_event is a no-op when POSTHOG_API_KEY is not set."""
    with patch.dict("os.environ", {}, clear=True):
        # Should not raise
        track_event("user-1", "test_event", {"key": "value"})


def test_shutdown_noop_without_client():
    """shutdown is safe to call even if client was never initialized."""
    shutdown()  # Should not raise
```

**Step 5: Run tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/services/test_analytics.py -v`
Expected: 2 tests pass.

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py -x -q`
Expected: All tests pass.

**Step 6: Lint**

Run: `cd /Users/brandon/repos/margin_invest && uv run ruff check --fix . && uv run ruff format .`
Expected: Clean.

**Step 7: Commit**

```bash
git add api/src/margin_api/services/analytics.py api/tests/services/test_analytics.py api/src/margin_api/app.py api/pyproject.toml uv.lock
git commit -m "feat(api): add PostHog server-side analytics client with shutdown hook"
```

---

### Task 13: Final verification — full test suite + lint + build

**Files:** None (verification only)

**Step 1: Run all Python tests**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest engine/tests/ -v -q`
Expected: All ~2621 engine tests pass.

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py -q`
Expected: All ~1587 API tests pass.

**Step 2: Run all web tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All ~1285 tests pass.

**Step 3: Lint everything**

Run: `cd /Users/brandon/repos/margin_invest && uv run ruff check --fix . && uv run ruff format .`
Run: `cd /Users/brandon/repos/margin_invest/web && npx eslint --fix .`
Expected: Both clean.

**Step 4: Build**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next build`
Expected: Build succeeds. Source map upload skipped (no SENTRY_AUTH_TOKEN locally).

**Step 5: Verify no secrets in committed files**

Run: `cd /Users/brandon/repos/margin_invest && git diff main --stat`
Verify: No `.env` files, no DSN strings, no API keys in diff. All secrets reference env vars only.

---

## Environment Variable Checklist (Manual Setup)

After all code is merged, set these in deployment environments:

**Vercel (web):**
- `NEXT_PUBLIC_SENTRY_DSN` — from Sentry Next.js project settings
- `NEXT_PUBLIC_SENTRY_ENVIRONMENT` — `production`
- `SENTRY_AUTH_TOKEN` — from Sentry org auth tokens (build-time)
- `SENTRY_ORG` — your Sentry org slug
- `SENTRY_PROJECT` — your Sentry project slug
- `NEXT_PUBLIC_POSTHOG_KEY` — from PostHog project settings
- `NEXT_PUBLIC_POSTHOG_HOST` — `https://us.i.posthog.com`

**Railway (API + Worker):**
- `SENTRY_DSN` — from Sentry Python/FastAPI project settings
- `SENTRY_ENVIRONMENT` — `production`
- `POSTHOG_API_KEY` — same key as frontend
- `POSTHOG_HOST` — `https://us.i.posthog.com`

**Local dev (`.env.local` in web/, `.env` in repo root):**
- Optional — both SDKs no-op when keys are not set
