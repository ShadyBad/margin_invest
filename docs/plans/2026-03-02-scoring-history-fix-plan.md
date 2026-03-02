# Scoring History Bug Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the Scoring History section so it displays all historical scores with valid dates instead of showing "Invalid Date" and only one entry.

**Architecture:** Two independent bugs — a missing Next.js API proxy route (causing silent 404 → single-entry fallback) and a date parser that can't handle full ISO datetimes. Both are small, isolated fixes.

**Tech Stack:** Next.js 16 (App Router), React 19, TypeScript, Vitest

---

### Task 1: Fix `formatDate` to handle full ISO datetime strings

The `formatDate` function in `score-history-table.tsx` splits the ISO string on `"-"` expecting `YYYY-MM-DD`, but the API returns `2026-02-16T10:30:45+00:00`. The `T` in the third segment causes `NaN`.

**Files:**
- Modify: `web/src/components/dashboard/panel/score-history-table.tsx:57-66`
- Modify: `web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx`

**Step 1: Add a failing test for ISO datetime input**

Add this test to the existing `describe` block in `web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx`:

```typescript
it("handles full ISO datetime strings without showing Invalid Date", () => {
  const isoHistory = [
    { date: "2026-02-16T10:30:45+00:00", score: 87, delta: 3, signal: "strong", conviction: "exceptional", keyChange: "+3.0" },
    { date: "2026-02-09T08:15:00+00:00", score: 84, delta: -1, signal: "strong", conviction: "high", keyChange: "-1.0" },
  ]
  render(<ScoreHistoryTable history={isoHistory} />)
  expect(screen.queryByText("Invalid Date")).not.toBeInTheDocument()
  expect(screen.getByText("Feb 16, 2026")).toBeInTheDocument()
  expect(screen.getByText("Feb 9, 2026")).toBeInTheDocument()
})
```

**Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/score-history-table.test.tsx`

Expected: FAIL — "Invalid Date" will be in the document.

**Step 3: Fix `formatDate` in `score-history-table.tsx`**

Change lines 57-66 from:

```typescript
function formatDate(iso: string): string {
  // Parse as local date to avoid UTC timezone shift
  const [y, m, d] = iso.split("-").map(Number)
  const date = new Date(y, m - 1, d)
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}
```

To:

```typescript
function formatDate(iso: string): string {
  // Strip time component if present, then parse as local date to avoid UTC timezone shift
  const dateOnly = iso.split("T")[0]
  const [y, m, d] = dateOnly.split("-").map(Number)
  const date = new Date(y, m - 1, d)
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}
```

**Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/score-history-table.test.tsx`

Expected: ALL PASS (6 existing + 1 new)

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/score-history-table.tsx web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx
git commit -m "fix(web): handle full ISO datetime in score history date parser"
```

---

### Task 2: Add missing Next.js API proxy route for score history

The client-side `getScoreHistory()` calls `/api/v1/scores/{ticker}/history`, but no Next.js route handler exists for this path. The request 404s silently, and the component falls back to a single synthetic entry.

**Files:**
- Create: `web/src/app/api/v1/scores/[ticker]/history/route.ts`

**Step 1: Create the proxy route**

Create `web/src/app/api/v1/scores/[ticker]/history/route.ts` following the exact pattern used by the existing `metrics/route.ts`:

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
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  const { ticker } = await params
  const { search } = new URL(_request.url)

  try {
    const response = await fetch(`${API_URL}/api/v1/scores/${ticker}/history${search}`, {
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      cache: "no-store",
    })

    if (!response.ok) {
      try {
        const body = await response.json()
        return NextResponse.json(body, { status: response.status })
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
    console.error(`Failed to proxy score history for ${ticker}:`, error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to fetch score history", status_code: 502 },
      { status: 502 },
    )
  }
}
```

Note: `search` is forwarded so the `?limit=30` query param from the asset detail page reaches the backend.

**Step 2: Commit**

```bash
git add web/src/app/api/v1/scores/\[ticker\]/history/route.ts
git commit -m "fix(web): add missing API proxy route for score history endpoint"
```

---

### Task 3: Run full web test suite and verify

**Step 1: Run all web tests**

Run: `cd web && npx vitest run`

Expected: All tests pass, no regressions.

**Step 2: Verify no lint errors**

Run: `cd web && npx eslint src/app/api/v1/scores/\[ticker\]/history/route.ts src/components/dashboard/panel/score-history-table.tsx`

Expected: No errors.
