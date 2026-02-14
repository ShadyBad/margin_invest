# Frontend-Backend Integration Design

Date: 2026-02-13
Status: Approved
Scope: Connect the Next.js frontend to the FastAPI backend with real data flowing end-to-end, starting with the dashboard.

## Context

The frontend currently has a well-structured API client (`lib/api/client.ts`) and component hierarchy, but no real data flows through the system. The backend has database models, scoring endpoints, and a seed/score CLI pipeline. This design connects them using Next.js 15 Server Components for the initial data load, with thin API route proxies for interactive client-side fetches.

## Architecture

### Data Flow

```
Initial page load (Server Component):
  Browser request → Next.js server → auth() check → serverFetch(API_URL) → FastAPI → PostgreSQL
                                                      ↑ private env var
                                                      ↑ injects X-User-Id header

Interactive fetch (Client Component, e.g. StockCard expand):
  Browser → GET /api/v1/scores/AAPL (Next.js API route) → auth() check → fetch(API_URL) → FastAPI
```

### Server/Client Boundary

| Component | Type | Reason |
|-----------|------|--------|
| `app/dashboard/page.tsx` | Server Component | Fetches dashboard data server-side, no client JS needed |
| `app/dashboard/loading.tsx` | Server Component | Suspense fallback, renders skeleton |
| `app/dashboard/error.tsx` | Client Component | Required by Next.js for error boundaries |
| `components/dashboard/picks-grid.tsx` | Server Component | Pure render, no state |
| `components/dashboard/watchlist-table.tsx` | Server Component | Pure render, no state |
| `components/dashboard/stock-card.tsx` | Client Component | Interactive expand/collapse + lazy fetch |
| `components/dashboard/asset-detail.tsx` | Client Component | Rendered inside StockCard |

### Why Lazy Loading for Score Detail

With 15-25 picks on the dashboard, pre-fetching all detail data server-side would be wasteful. Most users expand 2-3 cards. StockCard lazy-fetches detail on click through a Next.js API route proxy.

## Changes

### 1. Infrastructure Setup

Start Docker Compose for PostgreSQL/TimescaleDB and Redis (skip the `api` service, run FastAPI locally with `uv run`):

```bash
docker compose up -d db redis
```

Run Alembic migrations:

```bash
uv run alembic -c api/alembic.ini upgrade head
```

Seed financial data and run scoring:

```bash
uv run python -m margin_api.cli seed
uv run python -m margin_api.cli score
```

Verify:

```bash
curl http://localhost:8000/api/v1/dashboard | python -m json.tool
```

### 2. Server-Side Fetch Layer

New file: `web/src/lib/api/server.ts`

- `serverFetch<T>(path, options?)` function for Server Components and API routes
- Uses private `API_URL` env var (no `NEXT_PUBLIC_` prefix, invisible to browser)
- Optionally reads NextAuth session via `auth()` and forwards `X-User-Id` header
- Throws `ApiError` on non-2xx responses
- Sets `cache: 'no-store'` by default (scores change, no stale data)

New env var in `.env.local`:

```
API_URL=http://localhost:8000
```

### 3. Dashboard Page Rewrite

Rewrite `app/dashboard/page.tsx` from Client Component to async Server Component:

- Remove `"use client"`, `useState`, `useEffect`
- Call `auth()` at top; `redirect("/login")` if no session
- Await `serverFetch<DashboardResponse>('/api/v1/dashboard')`
- Render `PicksGrid` and `WatchlistTable` with fetched data

New `app/dashboard/loading.tsx`:

- Exports the skeleton grid (6 `SkeletonCard` elements)
- Next.js shows this automatically via Suspense during server fetch

New `app/dashboard/error.tsx`:

- Client Component (Next.js requirement)
- Shows error message with "Try again" button calling `router.refresh()`

### 4. API Route Proxy for Client-Side Fetches

New file: `web/src/app/api/v1/scores/[ticker]/route.ts`

- `GET` handler that proxies to `API_URL/api/v1/scores/{ticker}`
- Calls `auth()` — returns 401 JSON if no session
- Forwards response from FastAPI

Update `lib/api/client.ts`:

- Change `BASE_URL` from `process.env.NEXT_PUBLIC_API_URL` to empty string `''`
- Client-side `apiFetch('/api/v1/scores/AAPL')` now hits Next.js at `/api/v1/scores/AAPL`, which proxies to FastAPI
- This keeps FastAPI URL private and auth enforcement server-side

### 5. Auth Integration

Existing auth infrastructure is sufficient. Changes are defense-in-depth:

- `proxy.ts` middleware already protects `/dashboard` routes (existing)
- Dashboard Server Component adds `auth()` + `redirect()` as second layer
- API route proxy adds `auth()` check as third layer for client-side fetches
- `serverFetch()` forwards `X-User-Id` header from session for backend attribution

No changes to login, register, MFA pages, or NextAuth config.

### 6. Environment Configuration

`.env.local` (web):

```
# Server-only (not exposed to browser)
API_URL=http://localhost:8000

# Browser-accessible (kept for any remaining client-side usage)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Auth
AUTH_SECRET=<generate with: openssl rand -base64 32>
NEXTAUTH_URL=http://localhost:3000

# OAuth (optional for dev — can skip if using credentials auth)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

`.env` (api, repo root):

```
MARGIN_DATABASE_URL=postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest
MARGIN_REDIS_URL=redis://localhost:6379
MARGIN_DEBUG=true
MARGIN_JWT_SECRET=dev-secret-change-me
MARGIN_MFA_ENCRYPTION_KEY=<generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
```

### 7. Error Handling

| Scenario | Handler |
|----------|---------|
| FastAPI down | `serverFetch` throws `ApiError` → `error.tsx` shows "Service unavailable" |
| No scores in DB | API returns `{ picks: [], watchlist: [] }` → `PicksGrid` shows `EmptyState` |
| Auth expired | `auth()` returns null → redirect to `/login` |
| Score detail fetch fails | `StockCard` shows inline error (existing behavior) |
| Network timeout | `serverFetch` throws → `error.tsx` with retry button |

### 8. Testing Strategy

Unit tests:
- `serverFetch()` — mock global `fetch`, verify URL, headers, error handling
- API route proxy — mock `auth()` and `fetch`, verify 401 on no session, verify proxy

Integration tests:
- Dashboard Server Component — mock `serverFetch`, verify rendered HTML contains picks
- Update existing dashboard tests to account for Server Component rendering

E2E (Playwright):
- Existing login → dashboard flow works with real backend
- Add: verify score detail loads on StockCard click

Backend verification:
- `curl` endpoints with expected response shapes
- Existing `uv run pytest api/tests/ -v`

### 9. Logging

Minimal for v1:
- `serverFetch()` logs URL and status on failure via `console.error`
- API route proxy logs proxy errors with ticker context
- No new monitoring infrastructure; rely on Vercel/Railway built-in logs

## Verification Checklist

1. `docker compose up -d db redis` starts without errors
2. `alembic upgrade head` creates tables
3. `seed` CLI populates `financial_data` table
4. `score` CLI populates `scores` table
5. `curl /api/v1/dashboard` returns JSON with picks and watchlist
6. `curl /health` returns `{"status": "ok"}`
7. Next.js dashboard page renders picks from real database
8. Clicking a StockCard expands and shows real score detail
9. Unauthenticated access redirects to `/login`
10. All tests pass (`uv run pytest -v` and `npm test`)

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `web/src/lib/api/server.ts` | Create | Server-side fetch with auth injection |
| `web/src/app/dashboard/page.tsx` | Rewrite | Client → Server Component |
| `web/src/app/dashboard/loading.tsx` | Create | Suspense loading skeleton |
| `web/src/app/dashboard/error.tsx` | Create | Error boundary with retry |
| `web/src/app/api/v1/scores/[ticker]/route.ts` | Create | Proxy for client-side score detail fetch |
| `web/src/lib/api/client.ts` | Modify | Change BASE_URL to relative |
| `web/.env.local` | Create | Server + client env vars |
| `web/src/lib/api/server.test.ts` | Create | Unit tests for serverFetch |
| `web/src/app/api/v1/scores/[ticker]/route.test.ts` | Create | Unit tests for proxy route |
