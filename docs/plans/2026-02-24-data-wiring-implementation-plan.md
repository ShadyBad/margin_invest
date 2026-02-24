# Data Wiring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace all hardcoded/mock data in frontend with real API calls.

**Architecture:** Fix TS types to match API schemas, add fetch functions, transform API responses to component prop shapes, wire elimination percentage from existing dashboard data.

**Tech Stack:** Next.js 15, TypeScript, Vitest, FastAPI (no API changes needed)

---

### Task 1: Fix BacktestTeaser type + component + wire to API

**Files:**
- Modify: `web/src/lib/api/types.ts` (fix BacktestTeaserResponse)
- Modify: `web/src/components/asset-detail/backtest-teaser.tsx` (change startYear→startDate)
- Modify: `web/src/components/asset-detail/__tests__/backtest-teaser.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx` (wire API call)
- Modify: `web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx`

**Step 1: Fix BacktestTeaserResponse type**

In `web/src/lib/api/types.ts`, replace:
```typescript
export interface BacktestTeaserResponse {
  model_return: number
  benchmark_return: number
  max_drawdown: number
  benchmark_max_drawdown: number
  start_year: number
}
```
With:
```typescript
export interface BacktestTeaserResponse {
  ticker: string | null
  model_return: number
  benchmark_return: number
  max_drawdown: number
  benchmark_max_drawdown: number
  start_date: string
  end_date: string
}
```

**Step 2: Update backtest-teaser.tsx props**

Change the interface and component to accept `startDate: string` instead of `startYear: number`. Extract year internally:
```typescript
interface BacktestTeaserProps {
  modelReturn: number
  benchmarkReturn: number
  maxDrawdown: number
  benchmarkMaxDrawdown: number
  startDate: string        // ISO date string, e.g. "2006-01-01"
}
```
Inside component: `const startYear = new Date(startDate).getFullYear()`

**Step 3: Update backtest-teaser tests**

Change all test renders from `startYear={2006}` to `startDate="2006-01-01"`. Same assertions work (still checks for "2006" text).

**Step 4: Wire API call in asset-detail-view.tsx**

Make asset-detail-view.tsx a client component that fetches teaser data:
- Add `BacktestTeaser` state + useEffect to fetch `getBacktestTeaser(ticker)`
- On success: render `<BacktestTeaser>` with API data mapped to props
- On failure: don't render teaser (hide gracefully)
- Remove the hardcoded `<BacktestTeaser>` with static numbers

The component is already `"use client"` implicitly (no directive but uses client components). Add the state:
```typescript
const [teaserData, setTeaserData] = useState<BacktestTeaserResponse | null>(null)

useEffect(() => {
  getBacktestTeaser(ticker).then(setTeaserData).catch(() => {})
}, [ticker])
```

Then conditionally render:
```typescript
{teaserData && (
  <BacktestTeaser
    modelReturn={teaserData.model_return}
    benchmarkReturn={teaserData.benchmark_return}
    maxDrawdown={teaserData.max_drawdown}
    benchmarkMaxDrawdown={teaserData.benchmark_max_drawdown}
    startDate={teaserData.start_date}
  />
)}
```

**Step 5: Update asset-detail-view tests**

Mock `getBacktestTeaser` in the test file. The existing tests that check for `backtest-teaser` testid need to wait for async render.

**Step 6: Run tests**

```bash
cd web && npx vitest run src/components/asset-detail/
```

**Step 7: Commit**

```bash
git add web/src/lib/api/types.ts web/src/components/asset-detail/backtest-teaser.tsx web/src/components/asset-detail/__tests__/backtest-teaser.test.tsx web/src/components/asset-detail/asset-detail-view.tsx web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx
git commit -m "fix(web): wire backtest teaser to API, fix type mismatch

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Wire EliminationVignette to real data

**Files:**
- Modify: `web/src/components/landing/homepage-client.tsx`
- Modify: `web/src/components/landing/types.ts` (no change needed — already has total_scored + eligible_count)

**Step 1: Pass eliminatedPct to EliminationVignette**

In `web/src/components/landing/homepage-client.tsx`, compute and pass the prop:

```typescript
const eliminatedPct = data && data.total_scored > 0
  ? Math.round(((data.total_scored - data.eligible_count) / data.total_scored) * 100)
  : undefined

// Then in JSX:
<EliminationVignette eliminatedPct={eliminatedPct} />
```

Note: `total_scored` and `eligible_count` are currently set to the same value in `page.tsx:39` (`eligible_count: data.total_scored`). This means eliminatedPct will be 0%. We also need to fix `page.tsx` to use the correct field. Looking at `DashboardResponse`, it has `total_scored` (number of scored stocks). We need a count of stocks that passed filters. The dashboard picks already have filter data — `picks.length` is the survivors. So:

In `web/src/app/page.tsx`, fix the homepage data:
```typescript
eligible_count: data.picks.length,  // stocks that passed filters (not total_scored)
```

**Step 2: Run landing tests (if any exist)**

```bash
cd web && npx vitest run src/components/landing/
```

**Step 3: Commit**

```bash
git add web/src/components/landing/homepage-client.tsx web/src/app/page.tsx
git commit -m "feat(web): wire elimination vignette to real universe data

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Wire backtest page to replay API + shadow portfolio

**Files:**
- Modify: `web/src/lib/api/types.ts` (add FullBacktestResponse + sub-types + ShadowPortfolioResponse)
- Modify: `web/src/lib/api/backtest.ts` (add getDefaultBacktest, runReplay, getShadowPortfolio)
- Modify: `web/src/lib/api/index.ts` (export new functions + types)
- Modify: `web/src/app/backtesting/page.tsx` (replace mock data with API calls)
- Modify: `web/src/app/backtesting/__tests__/page.test.tsx` (mock new API functions)

**Step 1: Add API response types to types.ts**

Add after the existing `BacktestTeaserResponse`:

```typescript
export interface RegimeSegmentResponse {
  regime: string
  num_months: number
  total_return: number
  benchmark_return: number
  max_drawdown: number
}

export interface AuditRecordResponse {
  rebalance_date: string
  universe_size: number
  eliminated_count: number
  survivor_count: number
  selected_count: number
  top_holdings: Record<string, unknown>[]
  notable_events: string[]
  factor_coverage: number
  regime: string
}

export interface FactorTimelineResponse {
  as_of_date: string
  available: string[]
  missing: string[]
  coverage_ratio: number
}

export interface FailurePeriodResponse {
  rebalance_date: string
  portfolio_return: number
  benchmark_return: number
  relative_underperformance: number
  holdings: Record<string, unknown>[]
  regime: string
  regime_context: string
}

export interface ReplayConfigResponse {
  start_date: string
  end_date: string | null
  rebalance_frequency: string
  conviction_threshold: number
  weighting: string
  sector_exclusions: string[]
  transaction_cost_bps: number
}

export interface FullBacktestResponse {
  config: ReplayConfigResponse
  metrics: BacktestMetrics
  regime_segments: RegimeSegmentResponse[]
  audit_log: AuditRecordResponse[]
  factor_timeline: FactorTimelineResponse[]
  failure_audit: FailurePeriodResponse[]
  equity_curve: { date: string; portfolio_value: number; benchmark_value: number }[]
  walk_forward_note: string
  honesty_disclosure: string
}

export interface ShadowSnapshotResponse {
  as_of_date: string
  portfolio_value: number
  total_return: number | null
  num_positions: number
  positions: Record<string, unknown>[] | null
}

export interface ShadowPortfolioResponse {
  start_date: string
  snapshots: ShadowSnapshotResponse[]
  total_return: number
  max_drawdown: number
  num_days: number
  cannot_be_backdated: boolean
}
```

**Step 2: Add API functions to backtest.ts**

```typescript
export async function getDefaultBacktest(): Promise<FullBacktestResponse> {
  return apiFetch<FullBacktestResponse>("/api/v1/backtest/default")
}

export async function runReplay(config: {
  start_date?: string
  end_date?: string | null
  rebalance_frequency?: string
  conviction_threshold?: number
  weighting?: string
  sector_exclusions?: string[]
  transaction_cost_bps?: number
}): Promise<FullBacktestResponse> {
  return apiFetch<FullBacktestResponse>("/api/v1/backtest/replay", {
    method: "POST",
    body: JSON.stringify(config),
  })
}

export async function getShadowPortfolio(): Promise<ShadowPortfolioResponse> {
  return apiFetch<ShadowPortfolioResponse>("/api/v1/backtest/shadow-portfolio")
}
```

**Step 3: Update index.ts exports**

Add `getDefaultBacktest`, `runReplay`, `getShadowPortfolio` to function exports.
Add `FullBacktestResponse`, `ShadowPortfolioResponse`, `RegimeSegmentResponse`, etc. to type exports.

**Step 4: Rewrite backtesting page.tsx**

Key changes:
- Remove ALL `MOCK_*` constants (~90 lines)
- Add state for `replayData` (FullBacktestResponse | null) and `shadowData` (ShadowPortfolioResponse | null)
- Fetch `getDefaultBacktest()` + `getShadowPortfolio()` alongside existing fetches
- Add transform functions to map API shapes → component prop shapes:

```typescript
function toRegimePerformance(segments: RegimeSegmentResponse[]): RegimePerformance[] {
  const labels: Record<string, string> = { bull: "Bull Market", bear: "Bear Market", sideways: "Sideways", crisis: "Crisis" }
  return segments.map(s => ({
    regime: s.regime as "bull" | "bear" | "sideways" | "crisis",
    label: labels[s.regime] ?? s.regime,
    modelReturn: s.total_return / Math.max(s.num_months, 1) * 12, // annualize
    benchmarkReturn: s.benchmark_return / Math.max(s.num_months, 1) * 12,
    months: s.num_months,
    excessReturn: (s.total_return - s.benchmark_return) / Math.max(s.num_months, 1) * 12,
  }))
}

function toEquityCurvePoints(curve: { date: string; portfolio_value: number; benchmark_value: number }[]): EquityCurvePoint[] {
  let peak = 0
  return curve.map(p => {
    peak = Math.max(peak, p.portfolio_value)
    const drawdown = peak > 0 ? (p.portfolio_value - peak) / peak : 0
    return { date: p.date, portfolioValue: p.portfolio_value, benchmarkValue: p.benchmark_value, drawdown }
  })
}

function toFactorEntries(timeline: FactorTimelineResponse[]): FactorAvailabilityEntry[] {
  return timeline.map(t => ({ date: t.as_of_date, factors: t.available }))
}

function toAuditEntries(log: AuditRecordResponse[]) {
  return log.map(a => ({
    date: a.rebalance_date,
    action: "rebalance",
    universeSize: a.universe_size,
    selectedCount: a.selected_count,
    factorCoverage: a.factor_coverage,
    regime: a.regime,
    turnover: 0, // not provided by API
  }))
}

function toStats(m: BacktestMetrics) {
  return {
    cagr: m.cagr, excessCagr: m.excess_cagr, sharpe: m.sharpe_ratio,
    sortino: m.sortino_ratio, maxDrawdown: m.max_drawdown, winRate: m.win_rate,
    informationRatio: m.information_ratio, totalReturn: m.total_return,
    benchmarkReturn: m.benchmark_total_return, numMonths: m.num_months,
    avgTurnover: m.avg_turnover,
  }
}

function toFailurePeriods(failures: FailurePeriodResponse[]) {
  return failures.map(f => ({
    startDate: f.rebalance_date, endDate: f.rebalance_date,
    returnPct: f.portfolio_return, benchmarkReturnPct: f.benchmark_return,
    regime: f.regime, maxDrawdown: Math.abs(f.portfolio_return),
    recoveryMonths: null as number | null,
  }))
}
```

Wire components to transformed data, fall back to empty arrays when API returns nothing.

**Step 5: Update page tests**

Add mocks for `getDefaultBacktest` and `getShadowPortfolio`. The mock data should match the new response shapes. Existing test assertions should still work since component testids haven't changed.

**Step 6: Run tests**

```bash
cd web && npx vitest run src/app/backtesting/
cd web && npx vitest run src/components/backtesting/
```

**Step 7: Commit**

```bash
git commit -m "feat(web): wire backtest page to replay API, remove mock data

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
