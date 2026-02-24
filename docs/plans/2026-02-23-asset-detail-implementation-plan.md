# Asset Detail Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the `/asset/[ticker]` page — a forensic audit report that shows full scoring transparency for any ticker, with dual-mode for passing vs eliminated stocks.

**Architecture:** Server component page that fetches score data server-side, rendering into 5 sections (Hero, Gauntlet, Pillars, Conviction, Valuation). Reuses existing panel components (`PriceLadder`, `FactorRow`) where possible; creates new page-level components for the Gauntlet and Hero. Client components handle expandable sub-factors and the "What if?" reveal.

**Tech Stack:** Next.js 16 (server components), Tailwind v4 (design tokens from globals.css), Framer Motion (expand/collapse), Recharts (sparkline already exists), Vitest + Testing Library.

**Design Doc:** `docs/plans/2026-02-23-asset-detail-ui-design.md`

---

## Task 1: Create the page route and server data fetching

**Files:**
- Create: `web/src/app/asset/[ticker]/page.tsx`
- Create: `web/src/app/asset/[ticker]/loading.tsx`
- Create: `web/src/app/asset/[ticker]/error.tsx`

**Step 1: Create loading skeleton**

```tsx
// web/src/app/asset/[ticker]/loading.tsx
export default function AssetDetailLoading() {
  return (
    <div className="min-h-screen bg-bg-primary">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-bg-subtle rounded" />
          <div className="h-40 bg-bg-subtle rounded-xl" />
          <div className="h-64 bg-bg-subtle rounded-xl" />
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Create error boundary**

```tsx
// web/src/app/asset/[ticker]/error.tsx
"use client"

export default function AssetDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center">
      <div className="text-center space-y-4">
        <h2 className="text-xl font-semibold text-text-primary">Something went wrong</h2>
        <p className="text-text-secondary text-sm">{error.message}</p>
        <button
          onClick={reset}
          className="px-4 py-2 bg-accent text-white rounded-lg text-sm hover:bg-accent-hover transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  )
}
```

**Step 3: Create the main page (server component)**

```tsx
// web/src/app/asset/[ticker]/page.tsx
import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { serverFetch } from "@/lib/api/server"
import { AppShell } from "@/components/layout/app-shell"
import { AssetDetailView } from "@/components/asset-detail/asset-detail-view"
import type { ScoreResponse, ScoreHistoryResponse } from "@/lib/api/types"

interface AssetDetailPageProps {
  params: Promise<{ ticker: string }>
}

export default async function AssetDetailPage({ params }: AssetDetailPageProps) {
  const { ticker } = await params
  const session = await auth()
  if (!session) redirect("/login")

  const upperTicker = ticker.toUpperCase()

  let scoreData: ScoreResponse | null = null
  let historyData: ScoreHistoryResponse | null = null
  let apiError: string | null = null

  try {
    const [scoreResult, historyResult] = await Promise.allSettled([
      serverFetch<ScoreResponse>(
        `/api/v1/scores/${upperTicker}?include=price_history,signal_history`
      ),
      serverFetch<ScoreHistoryResponse>(
        `/api/v1/scores/${upperTicker}/history?limit=30`
      ),
    ])

    if (scoreResult.status === "fulfilled") scoreData = scoreResult.value
    else apiError = scoreResult.reason?.message ?? "Failed to load score"

    if (historyResult.status === "fulfilled") historyData = historyResult.value
  } catch (err) {
    apiError = err instanceof Error ? err.message : "Failed to load data"
  }

  return (
    <AppShell>
      <AssetDetailView
        ticker={upperTicker}
        scoreData={scoreData}
        historyData={historyData}
        apiError={apiError}
      />
    </AppShell>
  )
}
```

**Step 4: Verify the route resolves**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next build --no-lint 2>&1 | head -30`
Expected: Build succeeds (may warn about missing `AssetDetailView` component — that's fine, we create it next)

**Step 5: Commit**

```bash
git add web/src/app/asset/
git commit -m "feat(web): add /asset/[ticker] page route with server data fetching"
```

---

## Task 2: Create the AssetDetailView container and Hero section

**Files:**
- Create: `web/src/components/asset-detail/asset-detail-view.tsx`
- Create: `web/src/components/asset-detail/hero-header.tsx`
- Create: `web/src/components/asset-detail/eliminated-hero.tsx`
- Create: `web/src/components/asset-detail/index.ts`
- Test: `web/src/components/asset-detail/__tests__/hero-header.test.tsx`

**Step 1: Write the failing test for HeroHeader**

```tsx
// web/src/components/asset-detail/__tests__/hero-header.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { HeroHeader } from "../hero-header"

const baseProps = {
  ticker: "AAPL",
  name: "Apple Inc.",
  sector: "Technology",
  growthStage: "mature",
  actualPrice: 187.42,
  priceChange: 1.23,
  priceChangePercent: 0.66,
  compositeScore: 78.3,
  universePercentile: 96,
  universeSize: 2847,
  convictionLevel: "high",
  signal: "buy",
  dataCoverage: 0.94,
  scoredAt: "2026-02-23T12:00:00Z",
  dataFreshness: "fresh" as const,
  priceSource: "live" as const,
  scoreHistory: [70, 72, 75, 78, 78.3],
}

describe("HeroHeader", () => {
  it("renders ticker and company name", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders four metric cards", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByTestId("metric-score")).toHaveTextContent("78.3")
    expect(screen.getByTestId("metric-percentile")).toHaveTextContent("Top 4%")
    expect(screen.getByTestId("metric-conviction")).toHaveTextContent("HIGH")
    expect(screen.getByTestId("metric-signal")).toHaveTextContent("BUY")
  })

  it("renders metadata ribbon", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByTestId("metadata-ribbon")).toHaveTextContent("94%")
  })

  it("renders growth stage and sector", () => {
    render(<HeroHeader {...baseProps} />)
    expect(screen.getByText(/Technology/)).toBeInTheDocument()
    expect(screen.getByText(/Mature/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/__tests__/hero-header.test.tsx`
Expected: FAIL — module not found

**Step 3: Implement HeroHeader**

```tsx
// web/src/components/asset-detail/hero-header.tsx
import { ConvictionBadge, SignalBadge } from "@/components/ui"
import { formatScoredAt } from "@/lib/format"

interface HeroHeaderProps {
  ticker: string
  name: string
  sector?: string | null
  growthStage?: string | null
  actualPrice?: number | null
  priceChange?: number | null
  priceChangePercent?: number | null
  compositeScore: number
  universePercentile: number
  universeSize?: number
  convictionLevel: string
  signal: string
  dataCoverage: number
  scoredAt?: string | null
  dataFreshness?: string | null
  priceSource?: string | null
  scoreHistory?: number[]
}

function formatGrowthStage(stage: string): string {
  return stage.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

function MiniSparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const w = 80
  const h = 24
  const pad = 2

  const points = values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (w - pad * 2)
      const y = pad + (1 - (v - min) / range) * (h - pad * 2)
      return `${x},${y}`
    })
    .join(" ")

  return (
    <svg width={w} height={h} data-testid="score-sparkline">
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        points={points}
        className="text-accent"
      />
    </svg>
  )
}

export function HeroHeader({
  ticker,
  name,
  sector,
  growthStage,
  actualPrice,
  priceChange,
  priceChangePercent,
  compositeScore,
  universePercentile,
  universeSize,
  convictionLevel,
  signal,
  dataCoverage,
  scoredAt,
  dataFreshness,
  priceSource,
  scoreHistory,
}: HeroHeaderProps) {
  const topPercent = Math.max(1, Math.round(100 - universePercentile))

  return (
    <section data-testid="hero-header" className="space-y-4">
      {/* Ticker line */}
      <div className="flex items-baseline justify-between gap-4">
        <div className="flex items-baseline gap-3 min-w-0">
          <h1 className="text-2xl font-semibold text-text-primary font-sans">{ticker}</h1>
          <span className="text-base text-text-secondary truncate">{name}</span>
        </div>
        {(sector || growthStage) && (
          <div className="flex items-center gap-2 text-sm text-text-tertiary shrink-0">
            {sector && <span>{sector}</span>}
            {sector && growthStage && <span>·</span>}
            {growthStage && <span>{formatGrowthStage(growthStage)}</span>}
          </div>
        )}
      </div>

      {/* Price line */}
      {actualPrice != null && (
        <div className="flex items-baseline gap-2">
          <span className="text-xl font-mono text-text-primary">
            ${actualPrice.toFixed(2)}
          </span>
          {priceChange != null && priceChangePercent != null && (
            <span
              className={`text-sm font-mono ${
                priceChange >= 0 ? "text-bullish" : "text-bearish"
              }`}
            >
              {priceChange >= 0 ? "+" : ""}
              {priceChange.toFixed(2)} ({priceChangePercent >= 0 ? "+" : ""}
              {priceChangePercent.toFixed(2)}%)
            </span>
          )}
        </div>
      )}

      {/* Four metric cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="terminal-card p-4 space-y-1" data-testid="metric-score">
          <span className="text-[11px] uppercase tracking-wider text-text-tertiary">Score</span>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-display text-accent leading-none">
              {compositeScore.toFixed(1)}
            </span>
            {scoreHistory && <MiniSparkline values={scoreHistory} />}
          </div>
        </div>

        <div className="terminal-card p-4 space-y-1" data-testid="metric-percentile">
          <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
            Percentile
          </span>
          <span className="text-2xl font-display text-text-primary leading-none">
            Top {topPercent}%
          </span>
          {universeSize && (
            <span className="text-[11px] text-text-tertiary block">
              of {universeSize.toLocaleString()}
            </span>
          )}
        </div>

        <div className="terminal-card p-4 space-y-1" data-testid="metric-conviction">
          <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
            Conviction
          </span>
          <span className="text-2xl font-display text-text-primary leading-none uppercase">
            {convictionLevel}
          </span>
        </div>

        <div className="terminal-card p-4 space-y-1" data-testid="metric-signal">
          <span className="text-[11px] uppercase tracking-wider text-text-tertiary">Signal</span>
          <span className="text-2xl font-display text-text-primary leading-none uppercase">
            {signal}
          </span>
        </div>
      </div>

      {/* Metadata ribbon */}
      <div
        className="flex items-center gap-3 text-[12px] text-text-tertiary font-mono"
        data-testid="metadata-ribbon"
      >
        <span>Data coverage: {Math.round(dataCoverage * 100)}%</span>
        <span>·</span>
        {scoredAt && <span>Scored: {formatScoredAt(scoredAt)}</span>}
        {scoredAt && priceSource && <span>·</span>}
        {priceSource && (
          <span>Price: {priceSource === "live" ? "Live" : "Daily close"}</span>
        )}
      </div>
    </section>
  )
}
```

**Step 4: Write the failing test for EliminatedHero**

```tsx
// Add to the same test file or create:
// web/src/components/asset-detail/__tests__/eliminated-hero.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { EliminatedHero } from "../eliminated-hero"

describe("EliminatedHero", () => {
  it("shows elimination banner with failure count", () => {
    render(
      <EliminatedHero
        ticker="TSLA"
        name="Tesla Inc."
        sector="Consumer Discretionary"
        growthStage="high_growth"
        actualPrice={241.87}
        failedCount={2}
        totalFilters={6}
        dataCoverage={0.91}
        scoredAt="2026-02-23T08:00:00Z"
      />
    )
    expect(screen.getByTestId("eliminated-banner")).toBeInTheDocument()
    expect(screen.getByText(/Failed 2 of 6/)).toBeInTheDocument()
    expect(screen.getByText("TSLA")).toBeInTheDocument()
  })
})
```

**Step 5: Implement EliminatedHero**

```tsx
// web/src/components/asset-detail/eliminated-hero.tsx
import { formatScoredAt } from "@/lib/format"

interface EliminatedHeroProps {
  ticker: string
  name: string
  sector?: string | null
  growthStage?: string | null
  actualPrice?: number | null
  failedCount: number
  totalFilters: number
  dataCoverage: number
  scoredAt?: string | null
}

function formatGrowthStage(stage: string): string {
  return stage.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

export function EliminatedHero({
  ticker,
  name,
  sector,
  growthStage,
  actualPrice,
  failedCount,
  totalFilters,
  dataCoverage,
  scoredAt,
}: EliminatedHeroProps) {
  return (
    <section data-testid="eliminated-hero" className="space-y-4">
      <div className="flex items-baseline justify-between gap-4">
        <div className="flex items-baseline gap-3 min-w-0">
          <h1 className="text-2xl font-semibold text-text-primary font-sans">{ticker}</h1>
          <span className="text-base text-text-secondary truncate">{name}</span>
        </div>
        {(sector || growthStage) && (
          <div className="flex items-center gap-2 text-sm text-text-tertiary shrink-0">
            {sector && <span>{sector}</span>}
            {sector && growthStage && <span>·</span>}
            {growthStage && <span>{formatGrowthStage(growthStage)}</span>}
          </div>
        )}
      </div>

      {actualPrice != null && (
        <span className="text-xl font-mono text-text-primary block">
          ${actualPrice.toFixed(2)}
        </span>
      )}

      <div
        className="border border-bearish/30 bg-bearish/5 rounded-xl px-5 py-4"
        data-testid="eliminated-banner"
      >
        <div className="flex items-center gap-2 mb-1">
          <span className="text-bearish font-semibold text-base">ELIMINATED</span>
        </div>
        <p className="text-text-secondary text-sm">
          Failed {failedCount} of {totalFilters} elimination filters.
          This stock did not qualify for scoring.
        </p>
      </div>

      <div className="flex items-center gap-3 text-[12px] text-text-tertiary font-mono">
        <span>Data coverage: {Math.round(dataCoverage * 100)}%</span>
        {scoredAt && (
          <>
            <span>·</span>
            <span>Last checked: {formatScoredAt(scoredAt)}</span>
          </>
        )}
      </div>
    </section>
  )
}
```

**Step 6: Create the AssetDetailView container**

```tsx
// web/src/components/asset-detail/asset-detail-view.tsx
import { HeroHeader } from "./hero-header"
import { EliminatedHero } from "./eliminated-hero"
import type { ScoreResponse, ScoreHistoryResponse } from "@/lib/api/types"

interface AssetDetailViewProps {
  ticker: string
  scoreData: ScoreResponse | null
  historyData: ScoreHistoryResponse | null
  apiError: string | null
}

export function AssetDetailView({
  ticker,
  scoreData,
  historyData,
  apiError,
}: AssetDetailViewProps) {
  // No data state
  if (apiError || !scoreData) {
    return (
      <div className="max-w-4xl mx-auto py-8">
        <div className="terminal-card p-8 text-center space-y-3">
          <h2 className="text-xl font-semibold text-text-primary">{ticker}</h2>
          <p className="text-text-secondary text-sm">
            {apiError ?? "No data available for this ticker. It may not be in our coverage universe."}
          </p>
          <a
            href="/dashboard"
            className="inline-block text-accent hover:text-accent-hover text-sm transition-colors"
          >
            Back to Dashboard
          </a>
        </div>
      </div>
    )
  }

  const allFiltersPassed = scoreData.filters_passed.every((f) => f.passed)
  const failedCount = scoreData.filters_passed.filter((f) => !f.passed).length
  const scoreHistoryValues = historyData?.scores
    ? historyData.scores.map((s) => s.composite_raw_score).reverse()
    : undefined

  return (
    <div className="max-w-4xl mx-auto py-8 space-y-8">
      {/* Navigation */}
      <a
        href="/dashboard"
        className="inline-flex items-center gap-1 text-sm text-text-tertiary hover:text-text-primary transition-colors"
      >
        <span>←</span> Back to Dashboard
      </a>

      {/* Hero — conditional on pass/fail */}
      {allFiltersPassed ? (
        <HeroHeader
          ticker={scoreData.ticker}
          name={scoreData.name}
          sector={(scoreData as any).sector ?? null}
          growthStage={scoreData.growth_stage ?? null}
          actualPrice={scoreData.actual_price}
          compositeScore={scoreData.composite_raw_score}
          universePercentile={scoreData.composite_percentile}
          convictionLevel={scoreData.conviction_level}
          signal={scoreData.signal}
          dataCoverage={scoreData.data_coverage}
          scoredAt={scoreData.scored_at ?? null}
          dataFreshness={(scoreData as any).data_freshness ?? null}
          priceSource={(scoreData as any).price_source ?? null}
          scoreHistory={scoreHistoryValues}
        />
      ) : (
        <EliminatedHero
          ticker={scoreData.ticker}
          name={scoreData.name}
          sector={(scoreData as any).sector ?? null}
          growthStage={scoreData.growth_stage ?? null}
          actualPrice={scoreData.actual_price}
          failedCount={failedCount}
          totalFilters={scoreData.filters_passed.length}
          dataCoverage={scoreData.data_coverage}
          scoredAt={scoreData.scored_at ?? null}
        />
      )}

      {/* Remaining sections will be added in subsequent tasks */}
    </div>
  )
}
```

**Step 7: Create barrel export**

```tsx
// web/src/components/asset-detail/index.ts
export { AssetDetailView } from "./asset-detail-view"
export { HeroHeader } from "./hero-header"
export { EliminatedHero } from "./eliminated-hero"
```

**Step 8: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/`
Expected: All tests PASS

**Step 9: Commit**

```bash
git add web/src/components/asset-detail/ web/src/app/asset/
git commit -m "feat(web): add Hero section for asset detail page (passing + eliminated modes)"
```

---

## Task 3: Build the Elimination Gauntlet component

**Files:**
- Create: `web/src/components/asset-detail/elimination-gauntlet.tsx`
- Create: `web/src/components/asset-detail/filter-card.tsx`
- Create: `web/src/lib/filter-metadata.ts`
- Test: `web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx` — add Gauntlet section

**Step 1: Create filter metadata (formulas + WHY THIS MATTERS descriptions)**

```tsx
// web/src/lib/filter-metadata.ts

interface FilterMeta {
  displayName: string
  technicalName: string
  formula: string | null
  whyItMatters: string
}

export const FILTER_METADATA: Record<string, FilterMeta> = {
  liquidity: {
    displayName: "Liquidity",
    technicalName: "Market Cap & Position Sizing",
    formula: null,
    whyItMatters:
      "Illiquid stocks cannot be traded efficiently. Small market caps mean wide spreads, high slippage, and difficulty exiting positions.",
  },
  beneish_m_score: {
    displayName: "Earnings Quality",
    technicalName: "Beneish M-Score",
    formula: "8-variable composite (DSRI, GMI, AQI, SGI, DEPI, SGAI, accruals, leverage)",
    whyItMatters:
      "The Beneish M-Score detects earnings manipulation. Companies with scores above -2.22 have a high probability of manipulating reported earnings.",
  },
  altman_z_score: {
    displayName: "Financial Distress",
    technicalName: "Altman Z-Score",
    formula: "6.56(WC/TA) + 3.26(RE/TA) + 6.72(EBIT/TA) + 1.05(Equity/TL)",
    whyItMatters:
      "The Altman Z-Score predicts bankruptcy probability. Scores below 1.1 indicate a company in the financial distress zone.",
  },
  current_ratio: {
    displayName: "Short-Term Liquidity",
    technicalName: "Current Ratio",
    formula: "Current Assets / Current Liabilities",
    whyItMatters:
      "A low current ratio means the company may struggle to pay short-term obligations. Thresholds are sector-adjusted to account for capital-intensive industries.",
  },
  fcf_distress: {
    displayName: "Cash Flow Health",
    technicalName: "Free Cash Flow Distress",
    formula: null,
    whyItMatters:
      "Persistent negative free cash flow means the company is burning cash. This increases dilution risk and limits capital return to shareholders.",
  },
  interest_coverage: {
    displayName: "Debt Service",
    technicalName: "Interest Coverage Ratio",
    formula: "EBIT / Interest Expense",
    whyItMatters:
      "Low interest coverage means the company barely earns enough to service its debt. This increases default risk, especially during economic downturns.",
  },
}
```

**Step 2: Write the failing test for EliminationGauntlet**

```tsx
// web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { EliminationGauntlet } from "../elimination-gauntlet"
import type { FilterResultResponse } from "@/lib/api/types"

const allPassing: FilterResultResponse[] = [
  { name: "liquidity", passed: true, value: 2890000, threshold: 200000000, detail: "Market cap $2.89T", verdict: "pass", missing_fields: null },
  { name: "beneish_m_score", passed: true, value: -2.87, threshold: -2.22, detail: "M-Score: -2.87", verdict: "pass", missing_fields: null },
  { name: "altman_z_score", passed: true, value: 5.12, threshold: 1.1, detail: "Z-Score: 5.12", verdict: "pass", missing_fields: null },
  { name: "current_ratio", passed: true, value: 0.99, threshold: 0.8, detail: "CR: 0.99 (Tech threshold)", verdict: "pass", missing_fields: null },
  { name: "fcf_distress", passed: true, value: 104300, threshold: 0, detail: "Positive FCF", verdict: "pass", missing_fields: null },
  { name: "interest_coverage", passed: true, value: 29.4, threshold: 3.0, detail: "Coverage: 29.4x", verdict: "pass", missing_fields: null },
]

const withFailures: FilterResultResponse[] = [
  { name: "liquidity", passed: true, value: 782000, threshold: 200000000, detail: "Market cap $782B", verdict: "pass", missing_fields: null },
  { name: "beneish_m_score", passed: true, value: -2.45, threshold: -2.22, detail: "", verdict: "pass", missing_fields: null },
  { name: "altman_z_score", passed: false, value: 1.6, threshold: 1.1, detail: "Below safe zone", verdict: "fail", missing_fields: null },
  { name: "current_ratio", passed: true, value: 1.2, threshold: 0.8, detail: "", verdict: "pass", missing_fields: null },
  { name: "fcf_distress", passed: false, value: -2100, threshold: 0, detail: "Negative FCF", verdict: "fail", missing_fields: null },
  { name: "interest_coverage", passed: true, value: 8.5, threshold: 3.0, detail: "", verdict: "pass", missing_fields: null },
]

describe("EliminationGauntlet", () => {
  it("shows pass count for all-passing filters", () => {
    render(<EliminationGauntlet filters={allPassing} eliminated={false} />)
    expect(screen.getByText("6 of 6 passed")).toBeInTheDocument()
  })

  it("shows all 6 filter cards", () => {
    render(<EliminationGauntlet filters={allPassing} eliminated={false} />)
    expect(screen.getAllByTestId(/^filter-card-/)).toHaveLength(6)
  })

  it("sorts failed filters to top when eliminated", () => {
    render(<EliminationGauntlet filters={withFailures} eliminated={true} />)
    const cards = screen.getAllByTestId(/^filter-card-/)
    // Failed filters should be first
    expect(cards[0]).toHaveAttribute("data-testid", "filter-card-altman_z_score")
    expect(cards[1]).toHaveAttribute("data-testid", "filter-card-fcf_distress")
  })

  it("shows WHY THIS MATTERS for failed filters", () => {
    render(<EliminationGauntlet filters={withFailures} eliminated={true} />)
    expect(screen.getByText(/predicts bankruptcy probability/)).toBeInTheDocument()
  })
})
```

**Step 3: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx`
Expected: FAIL — module not found

**Step 4: Implement FilterCard**

```tsx
// web/src/components/asset-detail/filter-card.tsx
"use client"

import { FILTER_METADATA } from "@/lib/filter-metadata"
import type { FilterResultResponse } from "@/lib/api/types"

interface FilterCardProps {
  filter: FilterResultResponse
  expanded: boolean
}

function formatValue(value: number | null, name: string): string {
  if (value == null) return "N/A"
  if (name === "liquidity") {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
    if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`
    return `$${value.toLocaleString()}`
  }
  if (name === "interest_coverage") return `${value.toFixed(1)}x`
  if (name === "fcf_distress") {
    if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
    if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(0)}M`
    return `$${value.toLocaleString()}`
  }
  return value.toFixed(2)
}

function formatThreshold(threshold: number | null, name: string): string {
  if (threshold == null) return "N/A"
  if (name === "liquidity") return `$${(threshold / 1e6).toFixed(0)}M`
  if (name === "interest_coverage") return `${threshold.toFixed(1)}x`
  if (name === "fcf_distress") return "Positive"
  return threshold.toFixed(2)
}

export function FilterCard({ filter, expanded }: FilterCardProps) {
  const meta = FILTER_METADATA[filter.name]
  const passed = filter.passed
  const isInconclusive = filter.verdict === "inconclusive"

  const borderColor = isInconclusive
    ? "border-warning/30"
    : passed
      ? "border-white/[0.06]"
      : "border-bearish/30"

  const bgColor = isInconclusive
    ? "bg-warning/5"
    : !passed
      ? "bg-bearish/5"
      : ""

  const icon = isInconclusive ? "?" : passed ? "✓" : "✕"
  const iconColor = isInconclusive
    ? "text-warning"
    : passed
      ? "text-bullish"
      : "text-bearish"

  return (
    <div
      className={`border rounded-lg ${borderColor} ${bgColor} px-4 py-3 space-y-2`}
      data-testid={`filter-card-${filter.name}`}
    >
      {/* Header row */}
      <div className="flex items-center gap-2">
        <span className={`text-base font-semibold ${iconColor}`}>{icon}</span>
        <span className="text-sm font-semibold text-text-primary">
          {meta?.displayName ?? filter.name}
        </span>
        {meta?.technicalName && (
          <span className="text-xs text-text-tertiary">({meta.technicalName})</span>
        )}
        {!passed && !isInconclusive && (
          <span className="ml-auto text-xs font-mono text-bearish bg-bearish/10 px-2 py-0.5 rounded">
            FAILED
          </span>
        )}
      </div>

      {/* Value vs threshold */}
      <div className="flex items-center gap-6 text-sm font-mono">
        <div>
          <span className="text-text-tertiary text-xs block">Value</span>
          <span className="text-text-primary">{formatValue(filter.value, filter.name)}</span>
        </div>
        <div>
          <span className="text-text-tertiary text-xs block">Threshold</span>
          <span className="text-text-primary">{formatThreshold(filter.threshold, filter.name)}</span>
        </div>
      </div>

      {/* Formula (if available) */}
      {meta?.formula && expanded && (
        <div className="text-xs text-text-tertiary font-mono">
          Formula: {meta.formula}
        </div>
      )}

      {/* Detail from API */}
      {filter.detail && (
        <p className="text-xs text-text-secondary">{filter.detail}</p>
      )}

      {/* WHY THIS MATTERS — only for failed or inconclusive, when expanded */}
      {expanded && !passed && meta?.whyItMatters && (
        <div className="border-t border-white/[0.06] pt-2 mt-2">
          <span className="text-[10px] uppercase tracking-wider text-text-tertiary font-semibold block mb-1">
            Why This Matters
          </span>
          <p className="text-xs text-text-secondary leading-relaxed">{meta.whyItMatters}</p>
        </div>
      )}
    </div>
  )
}
```

**Step 5: Implement EliminationGauntlet**

```tsx
// web/src/components/asset-detail/elimination-gauntlet.tsx
import { FilterCard } from "./filter-card"
import type { FilterResultResponse } from "@/lib/api/types"

interface EliminationGauntletProps {
  filters: FilterResultResponse[]
  eliminated: boolean
}

export function EliminationGauntlet({ filters, eliminated }: EliminationGauntletProps) {
  const passCount = filters.filter((f) => f.passed).length

  // When eliminated, sort failed filters to top
  const sortedFilters = eliminated
    ? [...filters].sort((a, b) => {
        if (a.passed === b.passed) return 0
        return a.passed ? 1 : -1
      })
    : filters

  return (
    <section data-testid="elimination-gauntlet" className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Elimination Gauntlet</h2>
          <p className="text-xs text-text-tertiary mt-0.5">
            Every scored stock must survive all six filters.
          </p>
        </div>
        <span
          className={`text-sm font-mono px-2 py-1 rounded ${
            passCount === filters.length
              ? "text-bullish bg-bullish/10"
              : "text-bearish bg-bearish/10"
          }`}
        >
          {passCount} of {filters.length} passed
        </span>
      </div>

      <div className="space-y-2">
        {sortedFilters.map((filter) => (
          <FilterCard
            key={filter.name}
            filter={filter}
            expanded={eliminated ? !filter.passed : false}
          />
        ))}
      </div>
    </section>
  )
}
```

**Step 6: Add Gauntlet to AssetDetailView**

In `asset-detail-view.tsx`, import `EliminationGauntlet` and add after the Hero:

```tsx
import { EliminationGauntlet } from "./elimination-gauntlet"

// ... inside the return, after the Hero section:
<EliminationGauntlet
  filters={scoreData.filters_passed}
  eliminated={!allFiltersPassed}
/>
```

**Step 7: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/`
Expected: All tests PASS

**Step 8: Commit**

```bash
git add web/src/components/asset-detail/ web/src/lib/filter-metadata.ts
git commit -m "feat(web): add Elimination Gauntlet section with filter cards and WHY THIS MATTERS"
```

---

## Task 4: Build the Scoring Pillars section

**Files:**
- Create: `web/src/components/asset-detail/scoring-pillars.tsx`
- Create: `web/src/components/asset-detail/pillar-card.tsx`
- Test: `web/src/components/asset-detail/__tests__/scoring-pillars.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx` — add Pillars section

**Step 1: Write the failing test**

```tsx
// web/src/components/asset-detail/__tests__/scoring-pillars.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ScoringPillars } from "../scoring-pillars"
import type { FactorBreakdownResponse } from "@/lib/api/types"

const quality: FactorBreakdownResponse = {
  factor_name: "quality",
  weight: 0.3,
  average_percentile: 72,
  sub_scores: [
    { name: "piotroski_f_score", raw_value: 7, percentile_rank: 85, detail: "Strong", weight: null },
    { name: "gross_profitability", raw_value: 0.43, percentile_rank: 78, detail: "Above avg", weight: null },
  ],
}

const value: FactorBreakdownResponse = {
  factor_name: "value",
  weight: 0.4,
  average_percentile: 81,
  sub_scores: [
    { name: "ev_fcf", raw_value: 18.5, percentile_rank: 75, detail: "Reasonable", weight: null },
  ],
}

const momentum: FactorBreakdownResponse = {
  factor_name: "momentum",
  weight: 0.3,
  average_percentile: 68,
  sub_scores: [
    { name: "price_momentum", raw_value: 0.15, percentile_rank: 70, detail: "Positive", weight: null },
  ],
}

describe("ScoringPillars", () => {
  it("renders three pillar cards", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}
        growthStage="mature"
      />
    )
    expect(screen.getByTestId("pillar-quality")).toBeInTheDocument()
    expect(screen.getByTestId("pillar-value")).toBeInTheDocument()
    expect(screen.getByTestId("pillar-momentum")).toBeInTheDocument()
  })

  it("shows growth stage weight explanation", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}
        growthStage="mature"
      />
    )
    expect(screen.getByText(/Mature/)).toBeInTheDocument()
    expect(screen.getByText(/Q:30%/)).toBeInTheDocument()
  })

  it("expands sub-factors on click", () => {
    render(
      <ScoringPillars
        quality={quality}
        value={value}
        momentum={momentum}
        growthStage="mature"
      />
    )
    fireEvent.click(screen.getByTestId("pillar-quality-toggle"))
    expect(screen.getByText("Piotroski F-Score")).toBeInTheDocument()
    expect(screen.getByText("85th")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/__tests__/scoring-pillars.test.tsx`
Expected: FAIL

**Step 3: Implement PillarCard**

```tsx
// web/src/components/asset-detail/pillar-card.tsx
"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { formatAttributeLabel } from "@/lib/format"
import { PercentileBar } from "@/components/ui"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface PillarCardProps {
  pillar: FactorBreakdownResponse
}

function getPercentileDetail(p: number): string {
  if (p >= 80) return "Strong"
  if (p >= 60) return "Above avg"
  if (p >= 40) return "Average"
  if (p >= 20) return "Below avg"
  return "Weak"
}

export function PillarCard({ pillar }: PillarCardProps) {
  const [expanded, setExpanded] = useState(false)
  const name = pillar.factor_name.charAt(0).toUpperCase() + pillar.factor_name.slice(1)
  const weightPct = Math.round(pillar.weight * 100)
  const testId = `pillar-${pillar.factor_name}`

  return (
    <div className="terminal-card overflow-hidden" data-testid={testId}>
      <div className="p-4 space-y-2">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-text-primary uppercase">{name}</span>
          <span className="text-xs font-mono text-text-tertiary">{weightPct}%</span>
        </div>

        {/* Percentile */}
        <div className="text-center py-2">
          <span className="text-3xl font-display text-text-primary leading-none">
            {Math.round(pillar.average_percentile)}
          </span>
          <span className="text-xs text-text-tertiary block mt-1">percentile</span>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 rounded-full bg-white/[0.06]">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500"
            style={{ width: `${pillar.average_percentile}%` }}
          />
        </div>

        {/* Toggle */}
        <button
          className="flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary transition-colors w-full justify-center pt-1"
          onClick={() => setExpanded(!expanded)}
          data-testid={`${testId}-toggle`}
        >
          <span>{expanded ? "▲" : "▼"}</span>
          <span>{pillar.sub_scores.length} sub-factors</span>
        </button>
      </div>

      {/* Expanded sub-factors */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/[0.06] px-4 py-3 space-y-2">
              {/* Table header */}
              <div className="grid grid-cols-[1fr_80px_60px_60px] gap-2 text-[10px] uppercase tracking-wider text-text-tertiary">
                <span>Factor</span>
                <span className="text-right">Raw</span>
                <span className="text-right">Pctile</span>
                <span className="text-right">Rating</span>
              </div>
              {pillar.sub_scores.map((sub) => (
                <div
                  key={sub.name}
                  className="grid grid-cols-[1fr_80px_60px_60px] gap-2 text-xs items-center"
                >
                  <span className="text-text-primary truncate">
                    {formatAttributeLabel(sub.name)}
                  </span>
                  <span className="text-right font-mono text-text-secondary">
                    {typeof sub.raw_value === "number"
                      ? sub.raw_value % 1 === 0
                        ? sub.raw_value
                        : sub.raw_value.toFixed(2)
                      : sub.raw_value}
                  </span>
                  <span className="text-right font-mono text-text-primary">
                    {Math.round(sub.percentile_rank)}th
                  </span>
                  <span className="text-right text-text-tertiary">
                    {sub.detail || getPercentileDetail(sub.percentile_rank)}
                  </span>
                </div>
              ))}
              <p className="text-[10px] text-text-tertiary pt-2 border-t border-white/[0.04]">
                Each sub-factor is ranked within the stock's GICS sector first (sector-neutral), then combined.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
```

**Step 4: Implement ScoringPillars**

```tsx
// web/src/components/asset-detail/scoring-pillars.tsx
import { PillarCard } from "./pillar-card"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface ScoringPillarsProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  growthStage?: string | null
}

function formatGrowthStage(stage: string): string {
  return stage.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

function getWeightLabel(q: number, v: number, m: number): string {
  return `Q:${Math.round(q * 100)}% · V:${Math.round(v * 100)}% · M:${Math.round(m * 100)}%`
}

export function ScoringPillars({
  quality,
  value,
  momentum,
  growthStage,
}: ScoringPillarsProps) {
  const weightLabel = getWeightLabel(quality.weight, value.weight, momentum.weight)

  return (
    <section data-testid="scoring-pillars" className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-text-primary">Scoring Breakdown</h2>
        <p className="text-xs text-text-tertiary mt-0.5">
          Weighted by growth stage:{" "}
          {growthStage ? formatGrowthStage(growthStage) : "Default"} ({weightLabel})
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <PillarCard pillar={quality} />
        <PillarCard pillar={value} />
        <PillarCard pillar={momentum} />
      </div>
    </section>
  )
}
```

**Step 5: Add Pillars to AssetDetailView (only for passing tickers)**

In `asset-detail-view.tsx`, import and add after Gauntlet, conditional on `allFiltersPassed`:

```tsx
import { ScoringPillars } from "./scoring-pillars"

// After EliminationGauntlet:
{allFiltersPassed && (
  <ScoringPillars
    quality={scoreData.quality}
    value={scoreData.value}
    momentum={scoreData.momentum}
    growthStage={scoreData.growth_stage}
  />
)}
```

**Step 6: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add web/src/components/asset-detail/
git commit -m "feat(web): add Scoring Pillars section with expandable sub-factors"
```

---

## Task 5: Build the Conviction Engine section

**Files:**
- Create: `web/src/components/asset-detail/conviction-engine.tsx`
- Test: `web/src/components/asset-detail/__tests__/conviction-engine.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx` — add Conviction section

**Step 1: Write the failing test**

```tsx
// web/src/components/asset-detail/__tests__/conviction-engine.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ConvictionEngine } from "../conviction-engine"

describe("ConvictionEngine", () => {
  it("renders opportunity type with description", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={4.2}
        maxPositionPct={5.0}
        timingSignal="add_on_pullback"
        capitalAllocation={{
          factor_name: "capital_allocation",
          weight: 0.5,
          average_percentile: 75,
          sub_scores: [
            { name: "moat_durability", raw_value: 0.82, percentile_rank: 82, detail: "Wide", weight: null },
            { name: "compounding_power", raw_value: 0.76, percentile_rank: 76, detail: "Strong", weight: null },
          ],
        }}
        catalyst={{
          factor_name: "catalyst",
          weight: 0.5,
          average_percentile: 52,
          sub_scores: [
            { name: "catalyst_strength", raw_value: 0.45, percentile_rank: 45, detail: "Moderate", weight: null },
          ],
        }}
      />
    )
    expect(screen.getByText("COMPOUNDER")).toBeInTheDocument()
    expect(screen.getByText(/durable competitive advantages/)).toBeInTheDocument()
    expect(screen.getByText("4.2x")).toBeInTheDocument()
    expect(screen.getByText("5.0%")).toBeInTheDocument()
  })

  it("returns null when no conviction data", () => {
    const { container } = render(
      <ConvictionEngine
        opportunityType={null}
        winningTrack={null}
        asymmetryRatio={null}
        maxPositionPct={null}
        timingSignal={null}
        capitalAllocation={null}
        catalyst={null}
      />
    )
    expect(container.firstChild).toBeNull()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/__tests__/conviction-engine.test.tsx`
Expected: FAIL

**Step 3: Implement ConvictionEngine**

```tsx
// web/src/components/asset-detail/conviction-engine.tsx
import { formatAttributeLabel } from "@/lib/format"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface ConvictionEngineProps {
  opportunityType: string | null
  winningTrack: string | null
  asymmetryRatio: number | null
  maxPositionPct: number | null
  timingSignal: string | null
  capitalAllocation: FactorBreakdownResponse | null
  catalyst: FactorBreakdownResponse | null
}

const OPPORTUNITY_DESCRIPTIONS: Record<string, string> = {
  compounder: "This stock exhibits durable competitive advantages and consistent reinvestment returns.",
  mispricing: "The market is undervaluing this stock relative to its fundamentals.",
  both: "This stock exhibits both compounding qualities and current mispricing.",
  neither: "This stock does not clearly fit either opportunity pattern.",
}

const TIMING_LABELS: Record<string, { label: string; description: string }> = {
  buy_now: { label: "BUY NOW", description: "Current price represents a good entry point." },
  add_on_pullback: { label: "ADD ON PULLBACK", description: "Wait for a 5-10% dip from current levels." },
  wait_for_catalyst: { label: "WAIT FOR CATALYST", description: "Hold until a specific catalyst materializes." },
}

function TrackBar({ label, percentile }: { label: string; percentile: number }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="text-text-secondary w-40 truncate">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-white/[0.06]">
        <div
          className="h-full rounded-full bg-accent/60 transition-all"
          style={{ width: `${percentile}%` }}
        />
      </div>
      <span className="font-mono text-text-tertiary w-10 text-right">
        {Math.round(percentile)}th
      </span>
    </div>
  )
}

export function ConvictionEngine({
  opportunityType,
  winningTrack,
  asymmetryRatio,
  maxPositionPct,
  timingSignal,
  capitalAllocation,
  catalyst,
}: ConvictionEngineProps) {
  // Don't render if no conviction data
  if (!opportunityType) return null

  const timing = timingSignal ? TIMING_LABELS[timingSignal] : null

  return (
    <section data-testid="conviction-engine" className="space-y-4">
      <h2 className="text-lg font-semibold text-text-primary">Conviction Engine</h2>

      {/* Opportunity type banner */}
      <div className="terminal-card p-4 space-y-1">
        <span className="text-base font-semibold text-accent uppercase">
          {opportunityType.toUpperCase()}
        </span>
        <p className="text-sm text-text-secondary">
          {OPPORTUNITY_DESCRIPTIONS[opportunityType] ?? ""}
        </p>
      </div>

      {/* Three metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {asymmetryRatio != null && (
          <div className="terminal-card p-4 space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
              Asymmetry Ratio
            </span>
            <span className="text-2xl font-display text-text-primary block">
              {asymmetryRatio.toFixed(1)}x
            </span>
            <span className="text-xs text-text-tertiary">
              Upside is {asymmetryRatio.toFixed(1)}x the downside
            </span>
          </div>
        )}

        {maxPositionPct != null && (
          <div className="terminal-card p-4 space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
              Max Position
            </span>
            <span className="text-2xl font-display text-text-primary block">
              {maxPositionPct.toFixed(1)}%
            </span>
            <span className="text-xs text-text-tertiary">of portfolio</span>
          </div>
        )}

        {timing && (
          <div className="terminal-card p-4 space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
              Timing
            </span>
            <span className="text-base font-semibold text-text-primary block">
              {timing.label}
            </span>
            <span className="text-xs text-text-tertiary">{timing.description}</span>
          </div>
        )}
      </div>

      {/* Conviction tracks */}
      {(capitalAllocation || catalyst) && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-text-secondary">Conviction Tracks</h3>

          {capitalAllocation && (
            <div
              className={`terminal-card p-4 space-y-2 ${
                winningTrack === "compounder" ? "border-accent/30" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-text-primary uppercase">
                  Compounder Track
                </span>
                {winningTrack === "compounder" && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent font-medium">
                    winning
                  </span>
                )}
              </div>
              <div className="space-y-1.5">
                {capitalAllocation.sub_scores.map((s) => (
                  <TrackBar
                    key={s.name}
                    label={formatAttributeLabel(s.name)}
                    percentile={s.percentile_rank}
                  />
                ))}
              </div>
            </div>
          )}

          {catalyst && (
            <div
              className={`terminal-card p-4 space-y-2 ${
                winningTrack === "mispricing" ? "border-purple-500/30" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-text-primary uppercase">
                  Mispricing Track
                </span>
                {winningTrack === "mispricing" && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 font-medium">
                    winning
                  </span>
                )}
              </div>
              <div className="space-y-1.5">
                {catalyst.sub_scores.map((s) => (
                  <TrackBar
                    key={s.name}
                    label={formatAttributeLabel(s.name)}
                    percentile={s.percentile_rank}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
```

**Step 4: Add to AssetDetailView (only for passing tickers)**

In `asset-detail-view.tsx`, import and add after ScoringPillars:

```tsx
import { ConvictionEngine } from "./conviction-engine"

// After ScoringPillars:
{allFiltersPassed && (
  <ConvictionEngine
    opportunityType={scoreData.opportunity_type ?? null}
    winningTrack={scoreData.winning_track ?? null}
    asymmetryRatio={scoreData.asymmetry_ratio ?? null}
    maxPositionPct={scoreData.max_position_pct ?? null}
    timingSignal={scoreData.timing_signal ?? null}
    capitalAllocation={scoreData.capital_allocation ?? null}
    catalyst={scoreData.catalyst ?? null}
  />
)}
```

**Step 5: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add web/src/components/asset-detail/
git commit -m "feat(web): add Conviction Engine section with opportunity type and dual tracks"
```

---

## Task 6: Build the Valuation section

**Files:**
- Create: `web/src/components/asset-detail/valuation-section.tsx`
- Test: `web/src/components/asset-detail/__tests__/valuation-section.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx` — add Valuation section

**Step 1: Write the failing test**

```tsx
// web/src/components/asset-detail/__tests__/valuation-section.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ValuationSection } from "../valuation-section"

describe("ValuationSection", () => {
  it("renders price ruler with buy, sell, intrinsic, and current", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={142}
        sellPrice={214}
        intrinsicValue={165}
        currentPrice={187.42}
        priceUpside={-0.119}
        marginOfSafety={-0.136}
        valuationMethods={{ dcf: 158.2, ev_fcf: 172.4, acquirers_multiple: 161.8, shareholder_yield: 170.5 }}
      />
    )
    expect(screen.getByTestId("price-ruler")).toBeInTheDocument()
    expect(screen.getByText("$165.00")).toBeInTheDocument()
    expect(screen.getByText("$187.42")).toBeInTheDocument()
  })

  it("shows overvalued warning when price > intrinsic", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={142}
        sellPrice={214}
        intrinsicValue={165}
        currentPrice={187.42}
        priceUpside={-0.119}
        marginOfSafety={-0.136}
        valuationMethods={{}}
      />
    )
    expect(screen.getByText(/ABOVE intrinsic value/)).toBeInTheDocument()
  })

  it("shows unavailable message when no intrinsic value", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={null}
        sellPrice={null}
        intrinsicValue={null}
        currentPrice={187.42}
        priceUpside={null}
        marginOfSafety={null}
        valuationMethods={null}
        invalidReason="Negative trailing earnings prevent reliable DCF computation."
      />
    )
    expect(screen.getByText(/Negative trailing earnings/)).toBeInTheDocument()
  })

  it("renders valuation methods table", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={142}
        sellPrice={214}
        intrinsicValue={165}
        currentPrice={187.42}
        priceUpside={-0.119}
        marginOfSafety={-0.136}
        valuationMethods={{ dcf: 158.2, ev_fcf: 172.4 }}
      />
    )
    expect(screen.getByText("DCF Model")).toBeInTheDocument()
    expect(screen.getByText("$158.20")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/__tests__/valuation-section.test.tsx`
Expected: FAIL

**Step 3: Implement ValuationSection**

This component reuses the existing `PriceLadder` from the panel if possible. If not, it includes its own inline ruler:

```tsx
// web/src/components/asset-detail/valuation-section.tsx
"use client"

import { useState } from "react"
import { getValuationAudit } from "@/lib/api/scores"
import type { ValuationAuditResponse } from "@/lib/api/types"

interface ValuationSectionProps {
  ticker: string
  buyPrice: number | null
  sellPrice: number | null
  intrinsicValue: number | null
  currentPrice: number | null
  priceUpside: number | null
  marginOfSafety: number | null
  valuationMethods: Record<string, number> | null
  invalidReason?: string | null
}

const METHOD_LABELS: Record<string, string> = {
  dcf: "DCF Model",
  ev_fcf: "EV/FCF",
  acquirers_multiple: "EV/EBIT",
  shareholder_yield: "Shareholder Yield",
}

function PriceRuler({
  buyPrice,
  sellPrice,
  intrinsicValue,
  currentPrice,
}: {
  buyPrice: number | null
  sellPrice: number | null
  intrinsicValue: number | null
  currentPrice: number | null
}) {
  const prices = [buyPrice, sellPrice, intrinsicValue, currentPrice].filter(
    (p): p is number => p != null
  )
  if (prices.length < 2) return null

  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1
  const pad = 0.1 * range
  const absMin = min - pad
  const absMax = max + pad
  const absRange = absMax - absMin

  function pct(val: number): number {
    return ((val - absMin) / absRange) * 100
  }

  return (
    <div className="relative py-8 px-4" data-testid="price-ruler">
      {/* Track */}
      <div className="relative h-1 bg-white/[0.08] rounded-full">
        {/* Buy marker */}
        {buyPrice != null && (
          <div className="absolute -top-6" style={{ left: `${pct(buyPrice)}%` }}>
            <span className="text-[10px] font-mono text-bullish block text-center transform -translate-x-1/2">
              Buy
            </span>
            <span className="text-xs font-mono text-text-secondary block text-center transform -translate-x-1/2">
              ${buyPrice.toFixed(0)}
            </span>
          </div>
        )}

        {/* Sell marker */}
        {sellPrice != null && (
          <div className="absolute -top-6" style={{ left: `${pct(sellPrice)}%` }}>
            <span className="text-[10px] font-mono text-bearish block text-center transform -translate-x-1/2">
              Sell
            </span>
            <span className="text-xs font-mono text-text-secondary block text-center transform -translate-x-1/2">
              ${sellPrice.toFixed(0)}
            </span>
          </div>
        )}

        {/* Intrinsic value marker */}
        {intrinsicValue != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-0.5 h-4 bg-accent"
            style={{ left: `${pct(intrinsicValue)}%` }}
          >
            <span className="absolute top-5 left-1/2 -translate-x-1/2 text-[10px] text-accent whitespace-nowrap">
              Intrinsic ${intrinsicValue.toFixed(2)}
            </span>
          </div>
        )}

        {/* Current price marker */}
        {currentPrice != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-text-primary border-2 border-bg-primary transform -translate-x-1/2"
            style={{ left: `${pct(currentPrice)}%` }}
          >
            <span className="absolute top-4 left-1/2 -translate-x-1/2 text-[10px] text-text-primary whitespace-nowrap font-mono">
              Current ${currentPrice.toFixed(2)}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export function ValuationSection({
  ticker,
  buyPrice,
  sellPrice,
  intrinsicValue,
  currentPrice,
  priceUpside,
  marginOfSafety,
  valuationMethods,
  invalidReason,
}: ValuationSectionProps) {
  const [showAudit, setShowAudit] = useState(false)
  const [auditData, setAuditData] = useState<ValuationAuditResponse | null>(null)
  const [auditLoading, setAuditLoading] = useState(false)

  const isOvervalued = currentPrice != null && intrinsicValue != null && currentPrice > intrinsicValue
  const entries = valuationMethods ? Object.entries(valuationMethods) : []

  async function handleAuditClick() {
    setShowAudit(!showAudit)
    if (!auditData && !auditLoading) {
      setAuditLoading(true)
      try {
        const data = await getValuationAudit(ticker)
        setAuditData(data)
      } catch {
        // Audit is optional enrichment
      } finally {
        setAuditLoading(false)
      }
    }
  }

  return (
    <section data-testid="valuation-section" className="space-y-4">
      <h2 className="text-lg font-semibold text-text-primary">Valuation</h2>

      {/* Unavailable state */}
      {intrinsicValue == null && (
        <div className="terminal-card p-4 space-y-2">
          <p className="text-sm text-text-secondary">Intrinsic value unavailable.</p>
          {invalidReason && (
            <p className="text-xs text-text-tertiary">Reason: {invalidReason}</p>
          )}
          <p className="text-xs text-text-tertiary">
            Score-based assessment is still available above.
          </p>
        </div>
      )}

      {/* Price ruler */}
      {intrinsicValue != null && (
        <div className="terminal-card p-4">
          <PriceRuler
            buyPrice={buyPrice}
            sellPrice={sellPrice}
            intrinsicValue={intrinsicValue}
            currentPrice={currentPrice}
          />

          {/* Metrics */}
          <div className="flex items-center gap-6 text-sm font-mono mt-2">
            {priceUpside != null && (
              <div>
                <span className="text-[10px] text-text-tertiary uppercase tracking-wider block">
                  Price Upside
                </span>
                <span className={priceUpside >= 0 ? "text-bullish" : "text-bearish"}>
                  {priceUpside >= 0 ? "+" : ""}
                  {(priceUpside * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {marginOfSafety != null && (
              <div>
                <span className="text-[10px] text-text-tertiary uppercase tracking-wider block">
                  Margin of Safety
                </span>
                <span className={marginOfSafety >= 0 ? "text-bullish" : "text-bearish"}>
                  {marginOfSafety >= 0 ? "+" : ""}
                  {(marginOfSafety * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          {/* Overvalued warning */}
          {isOvervalued && (
            <div className="flex items-center gap-2 mt-3 px-3 py-2 rounded bg-warning/10 border border-warning/20">
              <span className="text-warning text-sm">
                Currently trading ABOVE intrinsic value
              </span>
            </div>
          )}
        </div>
      )}

      {/* Valuation methods table */}
      {entries.length > 0 && (
        <div className="terminal-card p-4 space-y-3">
          <h3 className="text-sm font-semibold text-text-secondary">Valuation Methods</h3>
          <div className="space-y-2">
            <div className="grid grid-cols-[1fr_100px_60px] gap-2 text-[10px] uppercase tracking-wider text-text-tertiary">
              <span>Method</span>
              <span className="text-right">Implied Value</span>
              <span className="text-right">Status</span>
            </div>
            {entries.map(([key, val]) => (
              <div key={key} className="grid grid-cols-[1fr_100px_60px] gap-2 text-xs items-center">
                <span className="text-text-primary">{METHOD_LABELS[key] ?? key}</span>
                <span className="text-right font-mono text-text-primary">${val.toFixed(2)}</span>
                <span className="text-right text-bullish">Computed</span>
              </div>
            ))}
            {intrinsicValue != null && (
              <div className="grid grid-cols-[1fr_100px_60px] gap-2 text-xs items-center border-t border-white/[0.06] pt-2 mt-2">
                <span className="text-text-primary font-semibold">Blended Intrinsic Value</span>
                <span className="text-right font-mono text-text-primary font-semibold">
                  ${intrinsicValue.toFixed(2)}
                </span>
                <span />
              </div>
            )}
          </div>

          {/* Audit toggle */}
          <button
            className="text-xs text-accent hover:text-accent-hover transition-colors"
            onClick={handleAuditClick}
          >
            {showAudit ? "▲ Hide" : "▼ Full"} Valuation Audit (DCF scenarios, sensitivity analysis)
          </button>
          {showAudit && auditLoading && (
            <p className="text-xs text-text-tertiary">Loading audit data...</p>
          )}
          {showAudit && auditData && (
            <pre className="text-[10px] font-mono text-text-tertiary bg-white/[0.02] rounded p-3 overflow-x-auto max-h-64">
              {JSON.stringify(auditData, null, 2)}
            </pre>
          )}
        </div>
      )}
    </section>
  )
}
```

**Step 4: Add to AssetDetailView (only for passing tickers)**

In `asset-detail-view.tsx`, import and add after ConvictionEngine:

```tsx
import { ValuationSection } from "./valuation-section"

// After ConvictionEngine:
{allFiltersPassed && (
  <ValuationSection
    ticker={scoreData.ticker}
    buyPrice={scoreData.buy_price}
    sellPrice={scoreData.sell_price}
    intrinsicValue={scoreData.margin_invest_value}
    currentPrice={scoreData.actual_price}
    priceUpside={scoreData.price_upside ?? null}
    marginOfSafety={scoreData.margin_of_safety ?? null}
    valuationMethods={scoreData.valuation_methods ?? null}
    invalidReason={scoreData.price_target_invalid_reason ?? null}
  />
)}
```

**Step 5: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add web/src/components/asset-detail/
git commit -m "feat(web): add Valuation section with price ruler and methods table"
```

---

## Task 7: Build the "What If It Had Passed?" tiered reveal

**Files:**
- Create: `web/src/components/asset-detail/hypothetical-scores.tsx`
- Test: `web/src/components/asset-detail/__tests__/hypothetical-scores.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx` — add to failed-ticker view

**Step 1: Write the failing test**

```tsx
// web/src/components/asset-detail/__tests__/hypothetical-scores.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { HypotheticalScores } from "../hypothetical-scores"

const props = {
  ticker: "TSLA",
  compositeScore: 61.4,
  compositePercentile: 38,
  convictionLevel: "none",
  quality: {
    factor_name: "quality",
    weight: 0.3,
    average_percentile: 54,
    sub_scores: [],
  },
  value: {
    factor_name: "value",
    weight: 0.25,
    average_percentile: 42,
    sub_scores: [],
  },
  momentum: {
    factor_name: "momentum",
    weight: 0.35,
    average_percentile: 78,
    sub_scores: [],
  },
  growthStage: "high_growth" as const,
}

describe("HypotheticalScores", () => {
  it("is collapsed by default", () => {
    render(<HypotheticalScores {...props} />)
    expect(screen.queryByTestId("hypothetical-content")).not.toBeInTheDocument()
    expect(screen.getByText(/What if TSLA had passed/)).toBeInTheDocument()
  })

  it("expands on click", () => {
    render(<HypotheticalScores {...props} />)
    fireEvent.click(screen.getByTestId("hypothetical-toggle"))
    expect(screen.getByTestId("hypothetical-content")).toBeInTheDocument()
    expect(screen.getByText("HYPOTHETICAL SCORES")).toBeInTheDocument()
  })

  it("shows narrative conclusion about low score", () => {
    render(<HypotheticalScores {...props} />)
    fireEvent.click(screen.getByTestId("hypothetical-toggle"))
    expect(screen.getByText(/38th percentile/)).toBeInTheDocument()
    expect(screen.getByText(/below the threshold/)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/__tests__/hypothetical-scores.test.tsx`
Expected: FAIL

**Step 3: Implement HypotheticalScores**

```tsx
// web/src/components/asset-detail/hypothetical-scores.tsx
"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { PillarCard } from "./pillar-card"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface HypotheticalScoresProps {
  ticker: string
  compositeScore: number
  compositePercentile: number
  convictionLevel: string
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  growthStage?: string | null
}

const CONVICTION_MINIMUM = 65.0

export function HypotheticalScores({
  ticker,
  compositeScore,
  compositePercentile,
  convictionLevel,
  quality,
  value,
  momentum,
  growthStage,
}: HypotheticalScoresProps) {
  const [expanded, setExpanded] = useState(false)
  const wouldQualify = compositeScore >= CONVICTION_MINIMUM

  const narrative = wouldQualify
    ? `Even if it had passed filters, ${ticker} would rank in the ${Math.round(compositePercentile)}th percentile of the scored universe. However, the elimination filters exist to remove fundamental risk regardless of scoring potential.`
    : `Even if it had passed filters, ${ticker} would rank in the ${Math.round(compositePercentile)}th percentile of the scored universe — below the threshold for any conviction level (minimum: ${CONVICTION_MINIMUM}).`

  return (
    <section data-testid="hypothetical-scores">
      <button
        className="w-full terminal-card px-4 py-3 text-left flex items-center gap-2 hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(!expanded)}
        data-testid="hypothetical-toggle"
      >
        <span className="text-sm text-text-tertiary">{expanded ? "▲" : "▼"}</span>
        <span className="text-sm text-text-secondary">
          What if {ticker} had passed all filters?
        </span>
        <span className="text-xs text-text-tertiary ml-auto">See partial scores</span>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
            data-testid="hypothetical-content"
          >
            <div className="mt-3 space-y-4">
              {/* Warning banner */}
              <div className="border border-warning/30 bg-warning/5 rounded-lg px-4 py-3">
                <span className="text-sm font-semibold text-warning block">
                  HYPOTHETICAL SCORES
                </span>
                <p className="text-xs text-text-secondary mt-1">
                  These scores are informational only. {ticker} did not survive elimination
                  and is NOT a scored recommendation.
                </p>
              </div>

              {/* Summary */}
              <div className="flex items-center gap-4 text-sm">
                <div>
                  <span className="text-text-tertiary text-xs block">Composite Score</span>
                  <span className="text-text-primary font-mono">{compositeScore.toFixed(1)}</span>
                </div>
                <div>
                  <span className="text-text-tertiary text-xs block">Conviction</span>
                  <span className="text-text-primary uppercase">{convictionLevel}</span>
                </div>
                <div>
                  <span className="text-text-tertiary text-xs block">Signal</span>
                  <span className="text-text-tertiary">N/A</span>
                </div>
              </div>

              {/* Pillar cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <PillarCard pillar={quality} />
                <PillarCard pillar={value} />
                <PillarCard pillar={momentum} />
              </div>

              {/* Narrative conclusion */}
              <p className="text-xs text-text-secondary leading-relaxed border-t border-white/[0.06] pt-3">
                {narrative}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}
```

**Step 4: Add to AssetDetailView (only for failed tickers)**

In `asset-detail-view.tsx`, import and add after EliminationGauntlet for failed tickers:

```tsx
import { HypotheticalScores } from "./hypothetical-scores"

// After EliminationGauntlet, when !allFiltersPassed:
{!allFiltersPassed && (
  <HypotheticalScores
    ticker={scoreData.ticker}
    compositeScore={scoreData.composite_raw_score}
    compositePercentile={scoreData.composite_percentile}
    convictionLevel={scoreData.conviction_level}
    quality={scoreData.quality}
    value={scoreData.value}
    momentum={scoreData.momentum}
    growthStage={scoreData.growth_stage}
  />
)}
```

**Step 5: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add web/src/components/asset-detail/
git commit -m "feat(web): add 'What if it had passed?' hypothetical scores for eliminated tickers"
```

---

## Task 8: Wire up navigation — global search and dashboard links

**Files:**
- Modify: `web/src/components/nav/navbar.tsx` — add search bar
- Create: `web/src/components/nav/ticker-search.tsx`
- Modify: `web/src/components/dashboard/stock-card.tsx` — add link to `/asset/{ticker}`
- Test: `web/src/components/nav/__tests__/ticker-search.test.tsx`

**Step 1: Write the failing test for TickerSearch**

```tsx
// web/src/components/nav/__tests__/ticker-search.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { TickerSearch } from "../ticker-search"

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

describe("TickerSearch", () => {
  it("renders search input", () => {
    render(<TickerSearch />)
    expect(screen.getByPlaceholderText(/Search any ticker/i)).toBeInTheDocument()
  })

  it("navigates to /asset/{ticker} on submit", () => {
    const pushMock = vi.fn()
    vi.mocked(vi.importActual("next/navigation")).useRouter = () => ({ push: pushMock })

    render(<TickerSearch />)
    const input = screen.getByPlaceholderText(/Search any ticker/i)
    fireEvent.change(input, { target: { value: "TSLA" } })
    fireEvent.submit(input.closest("form")!)

    // The component should call router.push("/asset/TSLA")
    // Exact assertion depends on implementation
  })
})
```

**Step 2: Implement TickerSearch**

```tsx
// web/src/components/nav/ticker-search.tsx
"use client"

import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"

export function TickerSearch() {
  const [query, setQuery] = useState("")
  const router = useRouter()

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      const ticker = query.trim().toUpperCase()
      if (ticker) {
        router.push(`/asset/${ticker}`)
        setQuery("")
      }
    },
    [query, router]
  )

  return (
    <form onSubmit={handleSubmit} className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search any ticker..."
        className="w-32 sm:w-40 h-8 px-3 text-xs bg-white/[0.04] border border-white/[0.08] rounded-lg text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent/40 transition-colors"
      />
    </form>
  )
}
```

**Step 3: Add TickerSearch to Navbar**

In `navbar.tsx`, import `TickerSearch` and add it before the CTA / user dropdown section. The exact placement depends on the existing layout — insert it into the nav items area.

**Step 4: Add link from StockCard to Asset Detail**

In `stock-card.tsx`, add a "View full report" link or make the ticker header link to `/asset/{ticker}`. This should be a subtle addition — a small link that doesn't disrupt the existing card expand behavior.

```tsx
// In the stock card header area, add:
<a
  href={`/asset/${pick.ticker}`}
  className="text-xs text-text-tertiary hover:text-accent transition-colors"
  onClick={(e) => e.stopPropagation()}
>
  Full report →
</a>
```

**Step 5: Run tests**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/nav/ src/components/asset-detail/`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add web/src/components/nav/ web/src/components/dashboard/stock-card.tsx
git commit -m "feat(web): add global ticker search and dashboard link to asset detail page"
```

---

## Task 9: Update barrel exports and final integration test

**Files:**
- Modify: `web/src/components/asset-detail/index.ts` — ensure all components exported
- Create: `web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx`

**Step 1: Update barrel export**

```tsx
// web/src/components/asset-detail/index.ts
export { AssetDetailView } from "./asset-detail-view"
export { HeroHeader } from "./hero-header"
export { EliminatedHero } from "./eliminated-hero"
export { EliminationGauntlet } from "./elimination-gauntlet"
export { FilterCard } from "./filter-card"
export { ScoringPillars } from "./scoring-pillars"
export { PillarCard } from "./pillar-card"
export { ConvictionEngine } from "./conviction-engine"
export { ValuationSection } from "./valuation-section"
export { HypotheticalScores } from "./hypothetical-scores"
```

**Step 2: Write integration test**

```tsx
// web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { AssetDetailView } from "../asset-detail-view"
import type { ScoreResponse } from "@/lib/api/types"

function makeScoreResponse(overrides: Partial<ScoreResponse> = {}): ScoreResponse {
  return {
    ticker: "AAPL",
    name: "Apple Inc.",
    score: 78.3,
    universe_percentile: 96,
    composite_percentile: 96,
    composite_raw_score: 78.3,
    conviction_level: "high",
    signal: "buy",
    quality: { factor_name: "quality", weight: 0.3, average_percentile: 72, sub_scores: [] },
    value: { factor_name: "value", weight: 0.4, average_percentile: 81, sub_scores: [] },
    momentum: { factor_name: "momentum", weight: 0.3, average_percentile: 68, sub_scores: [] },
    filters_passed: [
      { name: "liquidity", passed: true, value: 2890000, threshold: 200000000, detail: "", verdict: "pass", missing_fields: null },
      { name: "beneish_m_score", passed: true, value: -2.87, threshold: -2.22, detail: "", verdict: "pass", missing_fields: null },
      { name: "altman_z_score", passed: true, value: 5.12, threshold: 1.1, detail: "", verdict: "pass", missing_fields: null },
      { name: "current_ratio", passed: true, value: 0.99, threshold: 0.8, detail: "", verdict: "pass", missing_fields: null },
      { name: "fcf_distress", passed: true, value: 104300, threshold: 0, detail: "", verdict: "pass", missing_fields: null },
      { name: "interest_coverage", passed: true, value: 29.4, threshold: 3.0, detail: "", verdict: "pass", missing_fields: null },
    ],
    data_coverage: 0.94,
    growth_stage: "mature",
    scored_at: "2026-02-23T12:00:00Z",
    margin_invest_value: 165,
    buy_price: 142,
    sell_price: 214,
    actual_price: 187.42,
    price_upside: -0.119,
    margin_of_safety: -0.136,
    valuation_methods: { dcf: 158.2, ev_fcf: 172.4 },
    opportunity_type: "compounder",
    winning_track: "compounder",
    asymmetry_ratio: 4.2,
    max_position_pct: 5.0,
    timing_signal: "add_on_pullback",
    capital_allocation: null,
    catalyst: null,
    price_target_invalid_reason: null,
    ...overrides,
  } as ScoreResponse
}

describe("AssetDetailView", () => {
  it("renders all sections for a passing ticker", () => {
    render(
      <AssetDetailView
        ticker="AAPL"
        scoreData={makeScoreResponse()}
        historyData={null}
        apiError={null}
      />
    )
    expect(screen.getByTestId("hero-header")).toBeInTheDocument()
    expect(screen.getByTestId("elimination-gauntlet")).toBeInTheDocument()
    expect(screen.getByTestId("scoring-pillars")).toBeInTheDocument()
    expect(screen.getByTestId("conviction-engine")).toBeInTheDocument()
    expect(screen.getByTestId("valuation-section")).toBeInTheDocument()
  })

  it("renders eliminated view for a failing ticker", () => {
    const data = makeScoreResponse({
      filters_passed: [
        { name: "liquidity", passed: true, value: 782000, threshold: 200000000, detail: "", verdict: "pass", missing_fields: null },
        { name: "beneish_m_score", passed: true, value: -2.45, threshold: -2.22, detail: "", verdict: "pass", missing_fields: null },
        { name: "altman_z_score", passed: false, value: 1.6, threshold: 1.1, detail: "", verdict: "fail", missing_fields: null },
        { name: "current_ratio", passed: true, value: 1.2, threshold: 0.8, detail: "", verdict: "pass", missing_fields: null },
        { name: "fcf_distress", passed: false, value: -2100, threshold: 0, detail: "", verdict: "fail", missing_fields: null },
        { name: "interest_coverage", passed: true, value: 8.5, threshold: 3.0, detail: "", verdict: "pass", missing_fields: null },
      ],
    })
    render(
      <AssetDetailView
        ticker="TSLA"
        scoreData={data}
        historyData={null}
        apiError={null}
      />
    )
    expect(screen.getByTestId("eliminated-hero")).toBeInTheDocument()
    expect(screen.getByTestId("elimination-gauntlet")).toBeInTheDocument()
    expect(screen.queryByTestId("scoring-pillars")).not.toBeInTheDocument()
    expect(screen.queryByTestId("conviction-engine")).not.toBeInTheDocument()
    expect(screen.getByTestId("hypothetical-scores")).toBeInTheDocument()
  })

  it("shows error state when no data", () => {
    render(
      <AssetDetailView
        ticker="XYZA"
        scoreData={null}
        historyData={null}
        apiError="Not found"
      />
    )
    expect(screen.getByText("XYZA")).toBeInTheDocument()
    expect(screen.getByText("Not found")).toBeInTheDocument()
  })
})
```

**Step 3: Run full test suite**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/asset-detail/`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add web/src/components/asset-detail/
git commit -m "test(web): add integration tests for asset detail view (passing, eliminated, error states)"
```

---

## Summary

| Task | Component | Files Created | Tests |
|------|-----------|---------------|-------|
| 1 | Page route + server fetch | 3 | Build verification |
| 2 | Hero Header (passing + eliminated) | 5 | 2 test suites |
| 3 | Elimination Gauntlet + Filter Cards | 3 + 1 lib | 1 test suite |
| 4 | Scoring Pillars + Pillar Card | 2 | 1 test suite |
| 5 | Conviction Engine | 1 | 1 test suite |
| 6 | Valuation Section + Price Ruler | 1 | 1 test suite |
| 7 | Hypothetical Scores (tiered reveal) | 1 | 1 test suite |
| 8 | Global search + dashboard links | 2 | 1 test suite |
| 9 | Barrel exports + integration tests | 1 | 1 integration suite |

**Total: ~17 new files, 9 commits, 9 test suites**
