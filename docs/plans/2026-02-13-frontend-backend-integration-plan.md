# Frontend-Backend Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect the Next.js dashboard to the FastAPI backend so real scored data flows end-to-end using Server Components.

**Architecture:** Dashboard becomes an async Server Component fetching from FastAPI via a private `serverFetch()` layer. StockCard stays a Client Component with lazy detail loading through a Next.js API route proxy. Frontend types are aligned to match backend Pydantic schemas.

**Tech Stack:** Next.js 15 (App Router, Server Components), FastAPI, SQLAlchemy async, PostgreSQL/TimescaleDB, NextAuth v5, Vitest

---

## Type Alignment Reference

The frontend TypeScript types and backend Pydantic schemas have diverged. This plan aligns them. Key mismatches:

| Field | Frontend (current) | Backend (Pydantic) | Resolution |
|-------|-------------------|-------------------|------------|
| Score detail structure | `factor_breakdown: Record<string, ...>` | `quality`, `value`, `momentum` as separate fields | Update frontend to match backend |
| Sub-score percentile | `percentile: number` | `percentile_rank: float` | Update frontend to `percentile_rank` |
| Sub-score weight | `weight: number` | not present | Remove from frontend |
| Filter detail | `reason?: string` | `detail: str`, `value`, `threshold`, `verdict` | Update frontend to match |
| Score name | `name: string` | not present | Add to backend |
| Score timestamp | `scored_at: string` | not present | Add to backend |

---

### Task 1: Start Infrastructure

**Files:**
- Reference: `docker-compose.yml`
- Reference: `api/alembic.ini`
- Reference: `api/src/margin_api/cli.py`

**Step 1: Start database and Redis**

Run:
```bash
docker compose up -d db redis
```
Expected: Both services healthy. Verify with:
```bash
docker compose ps
```
Expected: `db` and `redis` show "healthy" status.

**Step 2: Run Alembic migrations**

Run:
```bash
cd /Users/brandon/repos/margin_invest && uv run alembic -c api/alembic.ini upgrade head
```
Expected: Tables created in `margin_invest` database.

**Step 3: Seed financial data**

Run:
```bash
uv run python -m margin_api.cli seed
```
Expected: Financial data for ~50 S&P 500 tickers inserted into `financial_data` table.

**Step 4: Run scoring pipeline**

Run:
```bash
uv run python -m margin_api.cli score
```
Expected: Scores computed and inserted into `scores` table.

**Step 5: Start FastAPI and verify**

Run:
```bash
uv run uvicorn margin_api.app:app --reload --port 8000 &
sleep 3
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/api/v1/dashboard | python3 -m json.tool
```
Expected: Health returns `{"status": "ok", ...}`. Dashboard returns JSON with `picks` and `watchlist` arrays.

**Step 6: Stop the dev server** (we'll restart it later for full E2E)

---

### Task 2: Add `name` and `scored_at` to Backend ScoreResponse

The frontend needs `name` (company name) and `scored_at` (timestamp) in score detail. The backend doesn't include them yet.

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py:42-54`
- Modify: `api/src/margin_api/routes/scores.py:20-76`
- Test: `api/tests/` (existing tests)

**Step 1: Write the failing test**

Create: `api/tests/test_score_response_fields.py`

```python
"""Test that ScoreResponse includes name and scored_at fields."""

import pytest
from margin_api.schemas.scores import ScoreResponse, FactorBreakdownResponse


def test_score_response_includes_name():
    resp = ScoreResponse(
        ticker="AAPL",
        name="Apple Inc.",
        composite_percentile=92.0,
        conviction_level="exceptional",
        signal="buy",
        quality=FactorBreakdownResponse(
            factor_name="quality", weight=0.35, sub_scores=[], average_percentile=88.0,
        ),
        value=FactorBreakdownResponse(
            factor_name="value", weight=0.30, sub_scores=[], average_percentile=72.0,
        ),
        momentum=FactorBreakdownResponse(
            factor_name="momentum", weight=0.35, sub_scores=[], average_percentile=95.0,
        ),
        filters_passed=[],
        data_coverage=0.95,
        scored_at="2026-02-12T08:00:00Z",
    )
    assert resp.name == "Apple Inc."
    assert resp.scored_at == "2026-02-12T08:00:00Z"


def test_score_response_name_defaults_to_empty():
    resp = ScoreResponse(
        ticker="AAPL",
        composite_percentile=92.0,
        conviction_level="exceptional",
        signal="buy",
        quality=FactorBreakdownResponse(
            factor_name="quality", weight=0.35, sub_scores=[], average_percentile=88.0,
        ),
        value=FactorBreakdownResponse(
            factor_name="value", weight=0.30, sub_scores=[], average_percentile=72.0,
        ),
        momentum=FactorBreakdownResponse(
            factor_name="momentum", weight=0.35, sub_scores=[], average_percentile=95.0,
        ),
        filters_passed=[],
        data_coverage=0.95,
    )
    assert resp.name == ""
    assert resp.scored_at is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_score_response_fields.py -v`
Expected: FAIL — `name` and `scored_at` are not accepted by `ScoreResponse`.

**Step 3: Add fields to ScoreResponse schema**

Modify `api/src/margin_api/schemas/scores.py:42-54` — add `name` and `scored_at`:

```python
class ScoreResponse(BaseModel):
    """Full scoring result for a single ticker."""

    ticker: str
    name: str = ""
    composite_percentile: float
    conviction_level: str  # "exceptional", "high", "watchlist", "none"
    signal: str  # "buy", "watch", "no_action", etc.
    quality: FactorBreakdownResponse
    value: FactorBreakdownResponse
    momentum: FactorBreakdownResponse
    filters_passed: list[FilterResultResponse]
    data_coverage: float
    growth_stage: str | None = None
    scored_at: str | None = None
```

**Step 4: Update `_score_response_from_row` to populate new fields**

Modify `api/src/margin_api/routes/scores.py` — in the `_score_response_from_row` function:

In the `if detail:` branch (around line 31), add name and scored_at before `return ScoreResponse(**detail)`:

```python
    if detail:
        detail.setdefault("conviction_level", score.conviction_level)
        detail.setdefault("signal", score.signal)
        detail.setdefault("name", row.asset_name if hasattr(row, "asset_name") else "")
        detail.setdefault("scored_at", score.scored_at.isoformat() if score.scored_at else None)
        # ... rest of existing code ...
```

In the fallback branch (around line 50), add `name` and `scored_at` to the `ScoreResponse()` constructor:

```python
    return ScoreResponse(
        ticker=ticker,
        name=row.asset_name if hasattr(row, "asset_name") else "",
        composite_percentile=score.composite_percentile,
        # ... existing fields ...
        scored_at=score.scored_at.isoformat() if score.scored_at else None,
    )
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest api/tests/test_score_response_fields.py -v`
Expected: PASS

**Step 6: Run existing API tests to check for regressions**

Run: `uv run pytest api/tests/ -v`
Expected: All existing tests pass.

**Step 7: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/src/margin_api/routes/scores.py api/tests/test_score_response_fields.py
git commit -m "feat(api): add name and scored_at fields to ScoreResponse"
```

---

### Task 3: Create Server-Side Fetch Layer

**Files:**
- Create: `web/src/lib/api/server.ts`
- Test: `web/src/lib/api/__tests__/server.test.ts`

**Step 1: Write the failing test**

Create: `web/src/lib/api/__tests__/server.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

// Mock next-auth before importing serverFetch
const mockAuth = vi.fn()
vi.mock("@/lib/auth", () => ({
  auth: () => mockAuth(),
}))

// Mock global fetch
const mockFetch = vi.fn()
vi.stubGlobal("fetch", mockFetch)

// Import after mocks
const { serverFetch } = await import("../server")

describe("serverFetch", () => {
  beforeEach(() => {
    vi.stubEnv("API_URL", "http://localhost:8000")
    mockAuth.mockReset()
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("fetches from API_URL with the given path", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: "ok" }),
    })

    await serverFetch("/health")

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/health",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      }),
    )
  })

  it("returns parsed JSON on success", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ picks: [], watchlist: [] }),
    })

    const result = await serverFetch("/api/v1/dashboard")
    expect(result).toEqual({ picks: [], watchlist: [] })
  })

  it("throws ApiError on non-2xx response", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      text: () => Promise.resolve("server error"),
    })

    await expect(serverFetch("/api/v1/dashboard")).rejects.toThrow("server error")
  })

  it("injects X-User-Id header when session exists", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    })

    await serverFetch("/api/v1/dashboard")

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-User-Id": "user-123",
        }),
      }),
    )
  })

  it("uses cache: no-store by default", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    })

    await serverFetch("/api/v1/dashboard")

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ cache: "no-store" }),
    )
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/lib/api/__tests__/server.test.ts`
Expected: FAIL — module `../server` does not exist.

**Step 3: Write the implementation**

Create: `web/src/lib/api/server.ts`

```typescript
import { auth } from "@/lib/auth"
import { ApiError } from "./client"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function serverFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  }

  // Inject user ID from session if available
  try {
    const session = await auth()
    if (session?.userId) {
      headers["X-User-Id"] = session.userId as string
    }
  } catch {
    // Auth not available — continue without user context
  }

  const response = await fetch(url, {
    ...options,
    headers,
    cache: options.cache ?? "no-store",
  })

  if (!response.ok) {
    const message = await response.text().catch(() => undefined)
    throw new ApiError(response.status, response.statusText, message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/lib/api/__tests__/server.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/lib/api/server.ts web/src/lib/api/__tests__/server.test.ts
git commit -m "feat(web): add server-side fetch layer for Server Components"
```

---

### Task 4: Align Frontend Types with Backend Schemas

The frontend `ScoreResponse` uses `factor_breakdown: Record<string, ...>` but the backend sends `quality`, `value`, `momentum` as separate fields. Sub-scores use `percentile_rank` (not `percentile`). Filters use `detail`/`verdict` (not `reason`).

**Files:**
- Modify: `web/src/lib/api/types.ts`

**Step 1: Update types to match backend**

Replace the relevant interfaces in `web/src/lib/api/types.ts`:

```typescript
export interface FilterResultResponse {
  name: string
  passed: boolean
  value: number | null
  threshold: number | null
  detail: string
  verdict: string  // "pass" or "fail"
}

export interface FactorScoreResponse {
  name: string
  raw_value: number
  percentile_rank: number
  detail: string
}

export interface FactorBreakdownResponse {
  factor_name: string
  weight: number
  sub_scores: FactorScoreResponse[]
  average_percentile: number
}

export interface ScoreResponse {
  ticker: string
  name: string
  composite_percentile: number
  conviction_level: string
  signal: string
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  filters_passed: FilterResultResponse[]
  data_coverage: number
  growth_stage?: string
  scored_at?: string
}
```

Remove `quality_percentile`, `value_percentile`, `momentum_percentile`, `factor_breakdown` from `ScoreResponse`. Remove `reason` from `FilterResultResponse`. Change `percentile` to `percentile_rank` and remove `weight` from `FactorScoreResponse`.

Note: `PickSummary`, `WatchlistItem`, `DashboardResponse` stay unchanged — they already match the backend.

**Step 2: Verify TypeScript catches the breakage**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit 2>&1 | head -40`
Expected: Type errors in `asset-detail.tsx`, `factor-breakdown.tsx`, `filter-list.tsx`, `stock-card.tsx`, and test files. This confirms we need to update those files next.

**Step 3: Commit types only (components fixed in next tasks)**

```bash
git add web/src/lib/api/types.ts
git commit -m "refactor(web): align ScoreResponse types with backend Pydantic schemas"
```

---

### Task 5: Update Dashboard Components for New Types

**Files:**
- Modify: `web/src/components/dashboard/asset-detail.tsx`
- Modify: `web/src/components/dashboard/factor-breakdown.tsx`
- Modify: `web/src/components/dashboard/filter-list.tsx`
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Modify: `web/src/lib/api/index.ts`

**Step 1: Update FactorBreakdown to accept separate factors**

Modify `web/src/components/dashboard/factor-breakdown.tsx`:

Change the props interface and component to accept `quality`, `value`, `momentum` directly:

```typescript
import { PercentileBar } from "@/components/ui"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface FactorBreakdownProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  className?: string
}

interface FactorSectionProps {
  factor: FactorBreakdownResponse
}

function FactorSection({ factor }: FactorSectionProps) {
  return (
    <div data-testid={`factor-section-${factor.factor_name.toLowerCase()}`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-text-primary capitalize">
          {factor.factor_name}
        </h4>
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-secondary">
            Weight: {(factor.weight * 100).toFixed(0)}%
          </span>
          <span className="text-sm font-mono font-bold text-gold">
            {factor.average_percentile.toFixed(0)}
          </span>
        </div>
      </div>
      <div className="space-y-1.5">
        {factor.sub_scores.map((sub) => (
          <PercentileBar
            key={sub.name}
            value={sub.percentile_rank}
            label={sub.name}
            showValue
          />
        ))}
      </div>
    </div>
  )
}

export function FactorBreakdown({ quality, value, momentum, className = "" }: FactorBreakdownProps) {
  const factors = [quality, value, momentum]

  return (
    <div className={`space-y-4 ${className}`} data-testid="factor-breakdown">
      <h3 className="text-base font-semibold text-text-primary">
        Factor Breakdown
      </h3>
      <div className="space-y-5">
        {factors.map((factor) => (
          <FactorSection key={factor.factor_name} factor={factor} />
        ))}
      </div>
    </div>
  )
}
```

**Step 2: Update FilterList to use `detail` instead of `reason`**

Modify `web/src/components/dashboard/filter-list.tsx` — change `filter.reason` to `filter.detail`:

```typescript
import type { FilterResultResponse } from "@/lib/api/types"

interface FilterListProps {
  filters: FilterResultResponse[]
  className?: string
}

function FilterItem({ filter }: { filter: FilterResultResponse }) {
  return (
    <li
      className="flex items-start gap-2 text-sm"
      data-testid={`filter-${filter.name}`}
    >
      <span
        className={`shrink-0 mt-0.5 ${filter.passed ? "text-bullish" : "text-bearish"}`}
        aria-label={filter.passed ? "passed" : "failed"}
      >
        {filter.passed ? "\u2713" : "\u2717"}
      </span>
      <span className="text-text-primary">{filter.name}</span>
      {filter.detail && (
        <span className="text-text-secondary ml-auto text-xs">
          {filter.detail}
        </span>
      )}
    </li>
  )
}

export function FilterList({ filters, className = "" }: FilterListProps) {
  return (
    <div className={className} data-testid="filter-list">
      <h3 className="text-base font-semibold text-text-primary mb-3">
        Elimination Filters
      </h3>
      <ul className="space-y-2">
        {filters.map((filter) => (
          <FilterItem key={filter.name} filter={filter} />
        ))}
      </ul>
    </div>
  )
}
```

**Step 3: Update AssetDetail to use new ScoreResponse shape**

Modify `web/src/components/dashboard/asset-detail.tsx` — change `score.factor_breakdown` to separate fields:

```typescript
import { ConvictionBadge, SignalBadge } from "@/components/ui"
import { FactorBreakdown } from "./factor-breakdown"
import { FilterList } from "./filter-list"
import type { ScoreResponse } from "@/lib/api/types"

interface AssetDetailProps {
  score: ScoreResponse
  className?: string
}

function formatScoredAt(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export function AssetDetail({ score, className = "" }: AssetDetailProps) {
  return (
    <div
      className={`border-t border-border pt-6 mt-4 ${className}`}
      data-testid={`asset-detail-${score.ticker}`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <h3 className="text-xl font-bold text-text-primary">{score.ticker}</h3>
        <span className="text-sm text-text-secondary">{score.name}</span>
        <span className="text-lg font-bold text-gold ml-auto">
          {score.composite_percentile.toFixed(0)}
        </span>
        <ConvictionBadge level={score.conviction_level} />
        <SignalBadge signal={score.signal} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left column: Factor Breakdown */}
        <FactorBreakdown
          quality={score.quality}
          value={score.value}
          momentum={score.momentum}
        />

        {/* Right column: Filters + Metadata */}
        <div className="space-y-6">
          {score.filters_passed.length > 0 && (
            <FilterList filters={score.filters_passed} />
          )}

          {/* Metadata */}
          <div data-testid="asset-metadata">
            <h3 className="text-base font-semibold text-text-primary mb-3">
              Metadata
            </h3>
            <dl className="space-y-2 text-sm">
              {score.growth_stage && (
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Growth Stage</dt>
                  <dd className="text-text-primary capitalize">
                    {score.growth_stage}
                  </dd>
                </div>
              )}
              {score.data_coverage !== undefined && (
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Data Coverage</dt>
                  <dd className="text-text-primary">
                    {(score.data_coverage * 100).toFixed(0)}%
                  </dd>
                </div>
              )}
              {score.scored_at && (
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Scored At</dt>
                  <dd className="text-text-primary">
                    {formatScoredAt(score.scored_at)}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}
```

**Step 4: Update StockCard** — the `getScore` call returns the new shape. StockCard itself only uses `PickSummary` props (unchanged) and passes `ScoreResponse` to `AssetDetail`. No changes needed to StockCard since `AssetDetail` was updated above. But remove the unused `quality_percentile` etc from the type import if needed.

Verify: `StockCard` imports `ScoreResponse` and passes it to `AssetDetail` — both now use the updated type. No code change needed in `stock-card.tsx`.

**Step 5: Verify TypeScript compiles**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit 2>&1 | head -20`
Expected: Only test file errors remain (test mocks use old shapes — fixed in Task 10).

**Step 6: Commit**

```bash
git add web/src/components/dashboard/asset-detail.tsx web/src/components/dashboard/factor-breakdown.tsx web/src/components/dashboard/filter-list.tsx
git commit -m "refactor(web): update dashboard components for backend-aligned types"
```

---

### Task 6: Create Dashboard Loading and Error Files

**Files:**
- Create: `web/src/app/dashboard/loading.tsx`
- Create: `web/src/app/dashboard/error.tsx`

**Step 1: Create loading.tsx**

Create: `web/src/app/dashboard/loading.tsx`

```typescript
import { AppShell } from "@/components/layout"
import { SkeletonCard } from "@/components/ui"

export default function DashboardLoading() {
  return (
    <AppShell>
      <div className="mb-8">
        <div className="h-8 w-40 bg-border rounded animate-pulse" />
        <div className="h-4 w-56 bg-border rounded animate-pulse mt-2" />
      </div>
      <div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        data-testid="loading-skeleton"
      >
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </AppShell>
  )
}
```

**Step 2: Create error.tsx**

Create: `web/src/app/dashboard/error.tsx`

```typescript
"use client"

import { useRouter } from "next/navigation"
import { AppShell } from "@/components/layout"

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const router = useRouter()

  return (
    <AppShell>
      <div className="flex flex-col items-center justify-center py-20">
        <div className="bg-bearish/10 border border-bearish/30 rounded-xl p-6 max-w-md text-center">
          <h2 className="text-lg font-semibold text-bearish mb-2">
            Failed to load dashboard
          </h2>
          <p className="text-sm text-text-secondary mb-4">
            {error.message || "An unexpected error occurred."}
          </p>
          <button
            onClick={() => {
              reset()
              router.refresh()
            }}
            className="px-4 py-2 bg-gold text-bg-primary rounded-lg text-sm font-medium hover:bg-gold/90 transition-colors"
          >
            Try again
          </button>
        </div>
      </div>
    </AppShell>
  )
}
```

**Step 3: Commit**

```bash
git add web/src/app/dashboard/loading.tsx web/src/app/dashboard/error.tsx
git commit -m "feat(web): add Suspense loading skeleton and error boundary for dashboard"
```

---

### Task 7: Rewrite Dashboard Page as Server Component

**Files:**
- Modify: `web/src/app/dashboard/page.tsx`

**Step 1: Rewrite the page**

Replace the entire contents of `web/src/app/dashboard/page.tsx`:

```typescript
import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"
import { PicksGrid, WatchlistTable } from "@/components/dashboard"
import { serverFetch } from "@/lib/api/server"
import type { DashboardResponse } from "@/lib/api/types"

function formatLastUpdated(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export default async function DashboardPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  const data = await serverFetch<DashboardResponse>("/api/v1/dashboard")

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
        {data.last_updated && (
          <p className="text-sm text-text-secondary mt-1">
            Last updated: {formatLastUpdated(data.last_updated)}
          </p>
        )}
      </div>

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Top Picks
        </h2>
        <PicksGrid picks={data.picks} />
      </section>

      {data.watchlist.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Watchlist
          </h2>
          <WatchlistTable items={data.watchlist} />
        </section>
      )}
    </AppShell>
  )
}
```

Key changes from the original:
- Removed `"use client"`, `useState`, `useEffect`
- Async function that awaits `serverFetch` and `auth()` server-side
- No loading/error state management — handled by `loading.tsx` and `error.tsx`
- `redirect("/login")` if no session (defense-in-depth alongside middleware)

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit 2>&1 | head -20`
Expected: Page compiles. Remaining errors should only be in test files.

**Step 3: Commit**

```bash
git add web/src/app/dashboard/page.tsx
git commit -m "refactor(web): rewrite dashboard page as async Server Component"
```

---

### Task 8: Create API Route Proxy for Score Detail

StockCard (Client Component) needs to fetch score detail from the browser. This proxy route keeps the API URL server-side.

**Files:**
- Create: `web/src/app/api/v1/scores/[ticker]/route.ts`
- Test: `web/src/app/api/v1/scores/[ticker]/__tests__/route.test.ts`

**Step 1: Write the failing test**

Create: `web/src/app/api/v1/scores/[ticker]/__tests__/route.test.ts`

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const mockAuth = vi.fn()
vi.mock("@/lib/auth", () => ({
  auth: () => mockAuth(),
}))

const mockFetch = vi.fn()
vi.stubGlobal("fetch", mockFetch)

const { GET } = await import("../route")

function mockNextRequest(url: string) {
  return new Request(url)
}

describe("GET /api/v1/scores/[ticker]", () => {
  beforeEach(() => {
    vi.stubEnv("API_URL", "http://localhost:8000")
    mockAuth.mockReset()
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("returns 401 when not authenticated", async () => {
    mockAuth.mockResolvedValue(null)

    const response = await GET(
      mockNextRequest("http://localhost:3000/api/v1/scores/AAPL"),
      { params: Promise.resolve({ ticker: "AAPL" }) },
    )

    expect(response.status).toBe(401)
    const body = await response.json()
    expect(body.error).toBe("Unauthorized")
  })

  it("proxies request to FastAPI when authenticated", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ ticker: "AAPL", composite_percentile: 92 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    const response = await GET(
      mockNextRequest("http://localhost:3000/api/v1/scores/AAPL"),
      { params: Promise.resolve({ ticker: "AAPL" }) },
    )

    expect(response.status).toBe(200)
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/scores/AAPL",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      }),
    )
  })

  it("returns 502 when upstream fails", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockFetch.mockRejectedValue(new Error("Connection refused"))

    const response = await GET(
      mockNextRequest("http://localhost:3000/api/v1/scores/AAPL"),
      { params: Promise.resolve({ ticker: "AAPL" }) },
    )

    expect(response.status).toBe(502)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/app/api/v1/scores/\\[ticker\\]/__tests__/route.test.ts`
Expected: FAIL — module `../route` does not exist.

**Step 3: Write the implementation**

Create: `web/src/app/api/v1/scores/[ticker]/route.ts`

```typescript
import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ ticker: string }> },
) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { ticker } = await params

  try {
    const response = await fetch(`${API_URL}/api/v1/scores/${ticker}`, {
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
      },
      cache: "no-store",
    })

    if (!response.ok) {
      const text = await response.text().catch(() => "Upstream error")
      return NextResponse.json(
        { error: text },
        { status: response.status },
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error(`Failed to proxy score for ${ticker}:`, error)
    return NextResponse.json(
      { error: "Failed to fetch score data" },
      { status: 502 },
    )
  }
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/app/api/v1/scores/\\[ticker\\]/__tests__/route.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add "web/src/app/api/v1/scores/[ticker]/route.ts" "web/src/app/api/v1/scores/[ticker]/__tests__/route.test.ts"
git commit -m "feat(web): add API route proxy for score detail fetches"
```

---

### Task 9: Update Client Base URL

Change `apiFetch` to use relative URLs so browser-side fetches hit Next.js API routes (which proxy to FastAPI) instead of calling FastAPI directly.

**Files:**
- Modify: `web/src/lib/api/client.ts:12`

**Step 1: Change BASE_URL**

In `web/src/lib/api/client.ts`, change line 12 from:
```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```
to:
```typescript
const BASE_URL = ''
```

This makes `apiFetch('/api/v1/scores/AAPL')` resolve to `/api/v1/scores/AAPL` relative to the Next.js origin, hitting the proxy route from Task 8.

**Step 2: Export `serverFetch` from the API index**

Modify `web/src/lib/api/index.ts` — add the server-side fetch export:

```typescript
export { serverFetch } from './server'
```

**Step 3: Verify TypeScript compiles**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit 2>&1 | head -20`
Expected: Clean compile (test files may still have errors — fixed next task).

**Step 4: Commit**

```bash
git add web/src/lib/api/client.ts web/src/lib/api/index.ts
git commit -m "refactor(web): change API client base URL to relative for proxy routing"
```

---

### Task 10: Update Dashboard Tests

The existing test at `web/src/app/dashboard/__tests__/page.test.tsx` tests a Client Component with `useEffect`. The page is now a Server Component. Server Components can't be rendered directly with `render()` in Vitest — they need a different approach.

**Files:**
- Modify: `web/src/app/dashboard/__tests__/page.test.tsx`

**Step 1: Rewrite the test file**

The page is now an async Server Component. We test it by calling it as an async function and rendering the returned JSX. Mock `auth()`, `serverFetch()`, and `redirect()`.

Replace the entire contents of `web/src/app/dashboard/__tests__/page.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

// Mock auth
const mockAuth = vi.fn()
vi.mock("@/lib/auth", () => ({
  auth: () => mockAuth(),
}))

// Mock redirect
const mockRedirect = vi.fn()
vi.mock("next/navigation", () => ({
  redirect: (path: string) => {
    mockRedirect(path)
    throw new Error(`NEXT_REDIRECT: ${path}`)
  },
  usePathname: () => "/dashboard",
}))

// Mock serverFetch
const mockServerFetch = vi.fn()
vi.mock("@/lib/api/server", () => ({
  serverFetch: (...args: unknown[]) => mockServerFetch(...args),
}))

// Mock next-auth/react for child components that may use it
vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { user: { name: "Test User" } },
    status: "authenticated",
  }),
  signOut: vi.fn(),
}))

import type { DashboardResponse } from "@/lib/api/types"

const mockDashboardData: DashboardResponse = {
  picks: [
    {
      ticker: "AAPL",
      name: "Apple Inc.",
      composite_percentile: 92,
      conviction_level: "exceptional",
      signal: "buy",
      quality_percentile: 88,
      value_percentile: 72,
      momentum_percentile: 95,
    },
    {
      ticker: "MSFT",
      name: "Microsoft Corporation",
      composite_percentile: 85,
      conviction_level: "high",
      signal: "buy",
      quality_percentile: 90,
      value_percentile: 65,
      momentum_percentile: 80,
    },
  ],
  watchlist: [
    {
      ticker: "GOOG",
      name: "Alphabet Inc.",
      composite_percentile: 68,
      conviction_level: "watchlist",
    },
    {
      ticker: "AMZN",
      name: "Amazon.com Inc.",
      composite_percentile: 62,
      conviction_level: "watchlist",
    },
  ],
  last_updated: "2026-02-12T10:30:00Z",
  total_scored: 500,
}

describe("Dashboard Page (Server Component)", () => {
  beforeEach(() => {
    mockAuth.mockReset()
    mockServerFetch.mockReset()
    mockRedirect.mockReset()
  })

  it("redirects to /login when not authenticated", async () => {
    mockAuth.mockResolvedValue(null)

    const DashboardPage = (await import("../page")).default

    await expect(DashboardPage()).rejects.toThrow("NEXT_REDIRECT: /login")
    expect(mockRedirect).toHaveBeenCalledWith("/login")
  })

  it("renders picks and watchlist when authenticated", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument()
    expect(screen.getByTestId("picks-grid")).toBeInTheDocument()
    expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    expect(screen.getByTestId("stock-card-MSFT")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("sorts picks by composite_percentile descending", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    const grid = screen.getByTestId("picks-grid")
    const cards = grid.children
    expect(cards[0]).toHaveAttribute("data-testid", "stock-card-AAPL")
    expect(cards[1]).toHaveAttribute("data-testid", "stock-card-MSFT")
  })

  it("renders watchlist section", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByTestId("watchlist-table")).toBeInTheDocument()
    expect(screen.getByTestId("watchlist-row-GOOG")).toBeInTheDocument()
    expect(screen.getByTestId("watchlist-row-AMZN")).toBeInTheDocument()
  })

  it("displays last updated timestamp", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByText(/Last updated:/)).toBeInTheDocument()
  })

  it("shows empty state when no picks", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue({
      ...mockDashboardData,
      picks: [],
      watchlist: [],
    })

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByText("No picks yet")).toBeInTheDocument()
  })

  it("calls serverFetch with /api/v1/dashboard", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    await DashboardPage()

    expect(mockServerFetch).toHaveBeenCalledWith("/api/v1/dashboard")
  })
})
```

**Step 2: Run the tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/app/dashboard/__tests__/page.test.tsx`
Expected: PASS

**Step 3: Run all web tests to check for regressions**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All tests pass. If any component tests fail due to the type changes (particularly tests using the old `ScoreResponse` mock with `factor_breakdown`), update those mock objects to use the new shape:

Old mock shape:
```typescript
factor_breakdown: { quality: { ... }, value: { ... }, momentum: { ... } }
```

New mock shape:
```typescript
quality: { factor_name: "quality", weight: 0.4, average_percentile: 88, sub_scores: [...] },
value: { factor_name: "value", weight: 0.3, average_percentile: 72, sub_scores: [...] },
momentum: { factor_name: "momentum", weight: 0.3, average_percentile: 95, sub_scores: [...] },
```

And sub-scores change from `{ percentile: 92, weight: 0.5 }` to `{ percentile_rank: 92, detail: "" }`.

And filters change from `{ reason: "Price > $5" }` to `{ detail: "Price > $5", value: null, threshold: null, verdict: "pass" }`.

**Step 4: Commit**

```bash
git add web/src/app/dashboard/__tests__/page.test.tsx
git commit -m "test(web): update dashboard tests for Server Component architecture"
```

---

### Task 11: Environment Setup and End-to-End Verification

**Files:**
- Create: `web/.env.local` (git-ignored)

**Step 1: Create `.env.local` for the web app**

Create `web/.env.local`:

```
API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
AUTH_SECRET=dev-secret-change-me-in-production
NEXTAUTH_URL=http://localhost:3000
```

Generate a proper AUTH_SECRET:
```bash
openssl rand -base64 32
```
Use the output as the `AUTH_SECRET` value.

**Step 2: Start all services**

```bash
# Terminal 1: Database + Redis
docker compose up -d db redis

# Terminal 2: FastAPI backend
uv run uvicorn margin_api.app:app --reload --port 8000

# Terminal 3: Next.js frontend
cd web && npm run dev
```

**Step 3: Verify end-to-end data flow**

1. Open `http://localhost:3000/dashboard` in a browser
2. Should redirect to `/login` (auth required)
3. Log in via OAuth (Google/GitHub) or credentials
4. Dashboard should render with real picks and watchlist from the database
5. Click a stock card — should expand and show score detail fetched via the proxy route
6. Check browser Network tab — requests go to `/api/v1/scores/AAPL` (Next.js), not `localhost:8000`

**Step 4: Debugging if data doesn't appear**

If dashboard shows empty state ("No picks yet"):
```bash
# Check if scores exist in the database
curl -s http://localhost:8000/api/v1/dashboard | python3 -m json.tool
```

If the curl returns empty picks: the scoring pipeline didn't produce high-conviction results. Check:
```bash
# List all scores regardless of conviction
curl -s "http://localhost:8000/api/v1/scores?page_size=5" | python3 -m json.tool
```

If the curl works but the dashboard doesn't render:
- Check Next.js server logs for `serverFetch` errors
- Verify `API_URL` is set in `web/.env.local`
- Verify the FastAPI server is running on port 8000

If score detail doesn't load on card click:
- Check browser console for 401 errors (session issue)
- Check browser Network tab — the request should go to `/api/v1/scores/{ticker}`
- Verify the proxy route file exists at `web/src/app/api/v1/scores/[ticker]/route.ts`

**Step 5: Final test run**

```bash
# API tests
uv run pytest api/tests/ -v

# Web tests
cd web && npx vitest run
```

Expected: All tests pass.

**Step 6: Commit any remaining fixes**

```bash
git add -A
git commit -m "chore: finalize frontend-backend integration"
```
