# Scoring History Bug Fix Design

## Problem

The Scoring History section in the AssetPanel shows:
1. **"Invalid Date"** for all entries
2. **Only one score entry** despite multiple scoring runs existing in the database

## Root Causes

### Invalid Date

`score-history-table.tsx` `formatDate()` splits on `"-"` expecting `YYYY-MM-DD`:

```typescript
const [y, m, d] = iso.split("-").map(Number)
```

But the API returns full ISO datetimes like `2026-02-16T10:30:45+00:00`. The third segment `"16T10:30:45+00:00"` parses to `NaN`, producing `Invalid Date`.

### Only One Score

The `AssetPanel` fetches history client-side via `getScoreHistory()` → `apiFetch("/api/v1/scores/{ticker}/history")`. This hits the Next.js server, not the FastAPI backend directly.

Existing Next.js API proxy routes:
- `web/src/app/api/v1/scores/[ticker]/route.ts`
- `web/src/app/api/v1/scores/[ticker]/metrics/route.ts`

**Missing:** `web/src/app/api/v1/scores/[ticker]/history/route.ts`

The 404 is silently caught (`.catch(() => {})`), and the component falls back to a single synthetic entry from the current `scoredResult`.

## Fix

### 1. Add Missing Proxy Route

Create `web/src/app/api/v1/scores/[ticker]/history/route.ts` following the same pattern as `[ticker]/route.ts`: auth check, forward to `API_URL/api/v1/scores/{ticker}/history`, pass query params.

### 2. Fix `formatDate()` in `score-history-table.tsx`

Extract the date portion before splitting:

```typescript
const dateOnly = iso.split("T")[0]
const [y, m, d] = dateOnly.split("-").map(Number)
```

### 3. Update Tests

- Add test for `formatDate` with full ISO datetime input
- Add test for the new proxy route

## Files Changed

- `web/src/app/api/v1/scores/[ticker]/history/route.ts` (new)
- `web/src/components/dashboard/panel/score-history-table.tsx` (fix formatDate)
- `web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx` (add ISO datetime test)
