# Scoring History Bug Fix Design

## Problem

The Score Tracking chart renders blank for every candidate. The chart container appears but no data points, lines, or axes are displayed. This occurs consistently across all candidates on both local and deployed (Railway) environments.

## Prior Fixes (Already Committed)

Two bugs were identified and fixed in earlier commits:

1. **Invalid Date** (`a4a3107`): `formatDate()` in `score-history-table.tsx` split on `"-"` expecting `YYYY-MM-DD` but API returns full ISO datetimes. Fixed by extracting date portion with `split("T")[0]`.

2. **Missing Proxy Route** (`62fc5a2`): `web/src/app/api/v1/scores/[ticker]/history/route.ts` didn't exist. Client-side fetch got a 404, silently caught by `.catch(() => {})`, fell back to single synthetic entry. Fixed by creating the proxy route.

Both fixes are on `main` but the chart is still blank in both environments.

## Remaining Root Cause

The fundamental issue is **silent error swallowing**. Line 86 of `asset-panel.tsx`:

```typescript
.catch(() => {
  // Silently fail — synthetic fallback will be used
})
```

Every failure mode (auth error, server down, timeout, rate limit, upstream 500, malformed response) produces the same blank chart with zero diagnostic information. The chart component checks `data.length < 2` and shows an empty state message, making it impossible to distinguish between "no data exists" and "fetch failed."

Additionally:
- No loading indicator while history is being fetched
- No error state to inform the user something went wrong
- No retry mechanism

## Fix: Defensive Overhaul

### 1. Explicit State Machine in AssetPanel

Replace the implicit null/data binary with explicit status tracking:

```typescript
const [historyStatus, setHistoryStatus] = useState<'idle' | 'loading' | 'loaded' | 'error'>('idle')
```

The fetch effect transitions: `idle → loading → loaded | error`. On ticker change, reset to `loading` and clear stale data. On error, log the actual error to console for debugging.

### 2. Status-Aware Chart Components

**ScoreChart** receives a `status` prop and renders four states:
- `loading` → Animated skeleton placeholder (pulse bars matching chart dimensions)
- `error` → "Unable to load score history" + retry button
- `loaded` + `data.length < 2` → "Score tracking begins after the next scoring run"
- `loaded` + `data.length >= 2` → Actual Recharts chart (unchanged)

**ScoreHistoryTable** receives a `status` prop with matching states:
- `loading` → Skeleton rows
- `error` → Error message row
- `loaded` + empty → "No historical data available"
- `loaded` + data → Current table rendering

**PriceTargetChart** already conditionally renders on `historyData.points.length > 0` — no change needed.

### 3. Retry Mechanism

The `AssetPanel` exposes a `retryHistory` callback that re-triggers the fetch. This is passed to `ScoreChart` as `onRetry` and rendered as a button in the error state.

### 4. Test Coverage

**`asset-panel.test.tsx`:**
- Calls `getScoreHistory` when panel opens
- Passes `status='loading'` to ScoreChart initially
- Passes `status='loaded'` + data after fetch succeeds
- Passes `status='error'` when fetch fails
- Retry callback triggers re-fetch

**`score-chart.test.tsx`:**
- Loading → renders skeleton (`score-chart-loading`)
- Error → renders error message + retry button (`score-chart-error`)
- Empty → renders existing empty state (`score-chart-empty`)
- Loaded → renders chart (`score-chart`)

**`score-history-table.test.tsx`:**
- Status-based rendering for each state

**Manual verification:**
- Start FastAPI → curl history endpoint → confirm JSON with data
- Start Next.js → open asset panel → confirm chart renders
- Kill FastAPI → reopen panel → confirm error state (not blank)
- Check browser console for diagnostic logs

## Files Changed

- `web/src/components/dashboard/panel/asset-panel.tsx` (state machine, error logging, retry)
- `web/src/components/dashboard/panel/score-chart.tsx` (status prop, loading/error states)
- `web/src/components/dashboard/panel/score-history-table.tsx` (status prop, loading/error states)
- `web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx` (fetch lifecycle tests)
- `web/src/components/dashboard/panel/__tests__/score-chart.test.tsx` (status state tests)
- `web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx` (status state tests)
