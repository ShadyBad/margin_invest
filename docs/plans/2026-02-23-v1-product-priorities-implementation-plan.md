# V1 Product Priorities Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the V1 product priorities from the strategic design document — enriching the Glass Box explainability, zero-results scenario handling, backtest proof framing, and data reliability signals.

**Architecture:** All changes are frontend-only (web/ package). Tasks modify the asset detail page (filter cards, hero headers, gauntlet), dashboard (empty/low-results states, regime indicator), landing page (proof section reframing), and metadata ribbon (freshness color-coding). No backend or engine changes.

**Tech Stack:** Next.js 16, React 19, Tailwind v4, Vitest + @testing-library/react

---

### Task 1: Add Elimination Rate Context to Passing Ticker Hero

When a stock passes all filters, show how selective the gauntlet is. Add a one-line context note below the elimination gauntlet header: "X% of the scored universe was eliminated before scoring."

This requires the `DashboardResponse.total_scored` and `universe.size` to compute elimination rate, but the asset detail page doesn't fetch dashboard data. Instead, pass the universe size from `ScoreResponse` (already available as `universeSize` prop) and compute a static approximation. The real elimination rate requires a new API field — for now, show the universe size as context.

**Files:**
- Modify: `web/src/components/asset-detail/elimination-gauntlet.tsx`
- Test: `web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx` (extend)

**Step 1: Write the failing test**

Add to `web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx`:

```tsx
  it("shows universe context when universeSize provided", () => {
    const filters = [
      { name: "liquidity", passed: true, value: 2.89e12, threshold: 2e8, detail: "", verdict: "passed" },
      { name: "beneish_m_score", passed: true, value: -2.87, threshold: -1.78, detail: "", verdict: "passed" },
      { name: "altman_z_score", passed: true, value: 5.12, threshold: 1.1, detail: "", verdict: "passed" },
      { name: "current_ratio", passed: true, value: 0.99, threshold: 0.8, detail: "", verdict: "passed" },
      { name: "fcf_distress", passed: true, value: 1.04e11, threshold: 0, detail: "", verdict: "passed" },
      { name: "interest_coverage", passed: true, value: 29.4, threshold: 3.0, detail: "", verdict: "passed" },
    ]
    render(<EliminationGauntlet filters={filters} eliminated={false} universeSize={2847} scoredCount={847} />)
    expect(screen.getByText(/70% of the universe/i)).toBeInTheDocument()
  })
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx`
Expected: FAIL — `universeSize` prop doesn't exist

**Step 3: Add optional universeSize and scoredCount props**

In `web/src/components/asset-detail/elimination-gauntlet.tsx`, update the interface and add the context line:

```tsx
import { FilterCard } from "./filter-card"
import type { FilterResultResponse } from "@/lib/api/types"

interface EliminationGauntletProps {
  filters: FilterResultResponse[]
  eliminated: boolean
  universeSize?: number
  scoredCount?: number
}

export function EliminationGauntlet({ filters, eliminated, universeSize, scoredCount }: EliminationGauntletProps) {
  const passCount = filters.filter((f) => f.passed).length

  // When eliminated, sort failed filters to top
  const sortedFilters = eliminated
    ? [...filters].sort((a, b) => {
        if (a.passed === b.passed) return 0
        return a.passed ? 1 : -1
      })
    : filters

  const eliminatedPct =
    universeSize && scoredCount && universeSize > scoredCount
      ? Math.round(((universeSize - scoredCount) / universeSize) * 100)
      : null

  return (
    <section data-testid="elimination-gauntlet" className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Elimination Gauntlet</h2>
          <p className="text-xs text-text-tertiary mt-0.5">
            Every scored stock must survive all six filters.
          </p>
          {eliminatedPct != null && (
            <p className="text-xs text-text-tertiary mt-0.5">
              {eliminatedPct}% of the universe was eliminated before scoring.
            </p>
          )}
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

**Step 4: Wire the props in asset-detail-view.tsx**

In `web/src/components/asset-detail/asset-detail-view.tsx`, pass `universeSize` to the gauntlet. The `ScoreResponse` doesn't directly have `universe_size`, but the hero header already receives it from the page. Add it to `AssetDetailViewProps` and thread it through:

At line 11-16, update the interface:
```tsx
interface AssetDetailViewProps {
  ticker: string
  scoreData: ScoreResponse | null
  historyData: ScoreHistoryResponse | null
  apiError: string | null
  universeSize?: number
  totalScored?: number
}
```

At line 18, destructure the new props:
```tsx
export function AssetDetailView({ ticker, scoreData, historyData, apiError, universeSize, totalScored }: AssetDetailViewProps) {
```

At line 79-82, pass them to the gauntlet:
```tsx
      <EliminationGauntlet
        filters={scoreData.filters_passed}
        eliminated={!allFiltersPassed}
        universeSize={universeSize}
        scoredCount={totalScored}
      />
```

**Step 5: Run test to verify it passes**

Run: `npx vitest run web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx`
Expected: All PASS

**Step 6: Commit**

```bash
git add web/src/components/asset-detail/elimination-gauntlet.tsx web/src/components/asset-detail/asset-detail-view.tsx web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx
git commit -m "feat(web): add elimination rate context to gauntlet header"
```

---

### Task 2: Add Sector Survivor CTA on Eliminated Tickers

When a ticker is eliminated, the page is a dead end. Add a CTA at the bottom of eliminated ticker pages: "N stocks in [sector] survived the gauntlet." This converts curiosity into engagement.

**Files:**
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx:120-131`
- Test: `web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx` (create)

**Step 1: Write the failing test**

Create `web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AssetDetailView } from "../asset-detail-view"

// Mock all sub-components to isolate the view logic
vi.mock("../hero-header", () => ({ HeroHeader: () => <div data-testid="hero-header" /> }))
vi.mock("../eliminated-hero", () => ({ EliminatedHero: () => <div data-testid="eliminated-hero" /> }))
vi.mock("../elimination-gauntlet", () => ({ EliminationGauntlet: () => <div data-testid="gauntlet" /> }))
vi.mock("../scoring-pillars", () => ({ ScoringPillars: () => <div data-testid="pillars" /> }))
vi.mock("../conviction-engine", () => ({ ConvictionEngine: () => <div data-testid="conviction" /> }))
vi.mock("../valuation-section", () => ({ ValuationSection: () => <div data-testid="valuation" /> }))
vi.mock("../hypothetical-scores", () => ({ HypotheticalScores: () => <div data-testid="hypothetical" /> }))

const eliminatedScore = {
  ticker: "TSLA",
  name: "Tesla Inc.",
  score: 61.4,
  universe_percentile: 38,
  composite_percentile: 38,
  composite_raw_score: 61.4,
  conviction_level: "none",
  signal: "n/a",
  quality: { factor_name: "quality", weight: 0.3, sub_scores: [], average_percentile: 54 },
  value: { factor_name: "value", weight: 0.25, sub_scores: [], average_percentile: 42 },
  momentum: { factor_name: "momentum", weight: 0.35, sub_scores: [], average_percentile: 78 },
  filters_passed: [
    { name: "liquidity", passed: true, value: 8e11, threshold: 2e8, detail: "", verdict: "passed" },
    { name: "altman_z_score", passed: false, value: 1.6, threshold: 1.1, detail: "", verdict: "failed" },
    { name: "beneish_m_score", passed: true, value: -2.5, threshold: -1.78, detail: "", verdict: "passed" },
    { name: "current_ratio", passed: true, value: 1.5, threshold: 0.8, detail: "", verdict: "passed" },
    { name: "fcf_distress", passed: false, value: -2.1e9, threshold: 0, detail: "", verdict: "failed" },
    { name: "interest_coverage", passed: true, value: 15, threshold: 3, detail: "", verdict: "passed" },
  ],
  data_coverage: 0.91,
  growth_stage: "high_growth",
  margin_invest_value: null,
  buy_price: null,
  sell_price: null,
  actual_price: 241.87,
  price_upside: null,
  margin_of_safety: null,
  valuation_methods: null,
}

describe("AssetDetailView", () => {
  it("renders sector survivor CTA when eliminated and sector provided", () => {
    render(
      <AssetDetailView
        ticker="TSLA"
        scoreData={eliminatedScore as any}
        historyData={null}
        apiError={null}
        sectorSurvivorCount={5}
        sectorName="Consumer Discretionary"
      />
    )
    expect(screen.getByText(/5 stocks in Consumer Discretionary/i)).toBeInTheDocument()
    expect(screen.getByText(/survived the gauntlet/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx`
Expected: FAIL — props don't exist

**Step 3: Add sector survivor CTA**

In `web/src/components/asset-detail/asset-detail-view.tsx`:

Add new optional props to the interface:
```tsx
interface AssetDetailViewProps {
  ticker: string
  scoreData: ScoreResponse | null
  historyData: ScoreHistoryResponse | null
  apiError: string | null
  universeSize?: number
  totalScored?: number
  sectorSurvivorCount?: number
  sectorName?: string
}
```

After the HypotheticalScores section (after line 131), add:

```tsx
      {!allFiltersPassed && sectorSurvivorCount != null && sectorSurvivorCount > 0 && sectorName && (
        <div className="terminal-card p-4 text-center">
          <p className="text-sm text-text-secondary">
            {sectorSurvivorCount} stock{sectorSurvivorCount !== 1 ? "s" : ""} in {sectorName} survived the gauntlet.
          </p>
          <Link
            href={`/dashboard?sector=${encodeURIComponent(sectorName)}`}
            className="text-sm text-accent hover:text-accent-hover mt-2 inline-block"
          >
            View survivors &rarr;
          </Link>
        </div>
      )}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/asset-detail-view.tsx web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx
git commit -m "feat(web): add sector survivor CTA on eliminated ticker pages"
```

---

### Task 3: Enrich Dashboard Empty State with Elimination Stats

The current empty state says "It found nothing worth your capital right now." Enrich it with quantitative context from the dashboard response: total scored, universe size, and a framing sentence.

**Files:**
- Modify: `web/src/components/dashboard/picks-grid.tsx:17-34`
- Test: `web/src/components/dashboard/__tests__/picks-grid.test.tsx`

**Step 1: Write the failing test**

Add to `web/src/components/dashboard/__tests__/picks-grid.test.tsx`:

```tsx
  it("shows elimination stats when universe data provided and no picks", () => {
    render(<PicksGrid picks={[]} totalScored={847} universeSize={2847} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
    expect(screen.getByText(/847/)).toBeInTheDocument()
    expect(screen.getByText(/2,847/)).toBeInTheDocument()
  })
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/dashboard/__tests__/picks-grid.test.tsx`
Expected: FAIL — `totalScored` prop doesn't exist

**Step 3: Add universe context to empty state**

In `web/src/components/dashboard/picks-grid.tsx`:

Update the interface and empty state:

```tsx
interface PicksGridProps {
  picks: PickSummary[]
  className?: string
  totalScored?: number
  universeSize?: number
}

export function PicksGrid({ picks, className = "", totalScored, universeSize }: PicksGridProps) {
  const sorted = [...picks].sort(
    (a, b) => b.composite_percentile - a.composite_percentile,
  )

  if (sorted.length === 0) {
    const hasStats = totalScored != null && universeSize != null && universeSize > 0
    return (
      <EmptyState
        title="The system is working"
        description={
          hasStats
            ? `${totalScored.toLocaleString()} of ${universeSize.toLocaleString()} equities were scored. None met the conviction threshold. When high-conviction opportunities emerge, they'll appear here.`
            : "It found nothing worth your capital right now. When high-conviction opportunities emerge, they'll appear here."
        }
        className={className}
      />
    )
  }

  // ... rest unchanged
```

**Step 4: Wire the props in dashboard/page.tsx**

In `web/src/app/dashboard/page.tsx`, pass the stats to PicksGrid (around line 81):

```tsx
        <PicksGrid
          picks={data?.picks ?? []}
          totalScored={data?.total_scored}
          universeSize={data?.universe?.size}
        />
```

**Step 5: Run test to verify it passes**

Run: `npx vitest run web/src/components/dashboard/__tests__/picks-grid.test.tsx`
Expected: All PASS

**Step 6: Commit**

```bash
git add web/src/components/dashboard/picks-grid.tsx web/src/app/dashboard/page.tsx web/src/components/dashboard/__tests__/picks-grid.test.tsx
git commit -m "feat(web): enrich dashboard empty state with universe elimination stats"
```

---

### Task 4: Add Market Regime Label to Dashboard Header

Display a "Market Regime" label in the dashboard header based on how many picks the system produced. Categories: Normal (6+ picks), Concentrated (2-5 picks), Overheated (0-1 picks).

**Files:**
- Create: `web/src/components/dashboard/market-regime-label.tsx`
- Modify: `web/src/app/dashboard/page.tsx:45-60`
- Test: `web/src/components/dashboard/__tests__/market-regime-label.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/dashboard/__tests__/market-regime-label.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MarketRegimeLabel } from "../market-regime-label"

describe("MarketRegimeLabel", () => {
  it("shows Overheated when 0 picks", () => {
    render(<MarketRegimeLabel pickCount={0} />)
    expect(screen.getByText(/Overheated/i)).toBeInTheDocument()
  })

  it("shows Concentrated when 3 picks", () => {
    render(<MarketRegimeLabel pickCount={3} />)
    expect(screen.getByText(/Concentrated/i)).toBeInTheDocument()
  })

  it("shows Normal when 8 picks", () => {
    render(<MarketRegimeLabel pickCount={8} />)
    expect(screen.getByText(/Normal/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/dashboard/__tests__/market-regime-label.test.tsx`
Expected: FAIL — module doesn't exist

**Step 3: Create the market regime label component**

Create `web/src/components/dashboard/market-regime-label.tsx`:

```tsx
interface MarketRegimeLabelProps {
  pickCount: number
}

function getRegime(count: number): { label: string; color: string } {
  if (count <= 1) return { label: "Overheated", color: "text-bearish bg-bearish/10 border-bearish/20" }
  if (count <= 5) return { label: "Concentrated", color: "text-warning bg-warning/10 border-warning/20" }
  return { label: "Normal", color: "text-text-tertiary bg-white/[0.03] border-white/[0.06]" }
}

export function MarketRegimeLabel({ pickCount }: MarketRegimeLabelProps) {
  const regime = getRegime(pickCount)
  return (
    <span
      className={`text-xs font-mono px-2 py-0.5 rounded border ${regime.color}`}
      data-testid="market-regime"
    >
      {regime.label}
    </span>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/dashboard/__tests__/market-regime-label.test.tsx`
Expected: PASS

**Step 5: Wire into dashboard page**

In `web/src/app/dashboard/page.tsx`:

Add the import:
```tsx
import { PicksGrid, WatchlistPicksList, IngestionBanner, PortfolioConviction, MarketRegimeLabel } from "@/components/dashboard"
```

Note: Check if `MarketRegimeLabel` needs to be added to the dashboard barrel export (`web/src/components/dashboard/index.ts` or similar). If no barrel file exists, import directly from the component file.

Add after the "Last updated" line (around line 52), inside the header `<div>`:

```tsx
          {data?.picks != null && (
            <MarketRegimeLabel pickCount={data.picks.length} />
          )}
```

**Step 6: Commit**

```bash
git add web/src/components/dashboard/market-regime-label.tsx web/src/app/dashboard/page.tsx web/src/components/dashboard/__tests__/market-regime-label.test.tsx
git commit -m "feat(web): add market regime label to dashboard header"
```

---

### Task 5: Reframe Proof Section — Replace Backtest Placeholder with Live Tracking

The proof section currently shows "Walk-forward backtest since 2015" but no backtest exists yet. Replace the placeholder with honest framing: methodology commitment + "live tracking since launch."

**Files:**
- Modify: `web/src/components/landing/proof-section.tsx:80-88`
- Test: `web/src/components/landing/__tests__/proof-section.test.tsx`

**Step 1: Write the failing test**

Add to `web/src/components/landing/__tests__/proof-section.test.tsx`:

```tsx
  it("renders live tracking framing instead of backtest numbers", () => {
    render(<ProofSection candidates={[]} />)
    expect(screen.getByText(/every signal recorded/i)).toBeInTheDocument()
    expect(screen.getByText(/live tracking/i)).toBeInTheDocument()
  })
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/proof-section.test.tsx`
Expected: FAIL — text doesn't match

**Step 3: Update the proof section disclaimer ribbon**

In `web/src/components/landing/proof-section.tsx`, replace lines 80-88:

```tsx
        <div className="text-center mb-8 space-y-2">
          <p className="text-sm font-mono text-text-primary">
            Every signal recorded · Sector-neutral · Live tracking from day one
          </p>
          <p className="text-[10px] text-text-tertiary max-w-md mx-auto">
            Past performance does not guarantee future results. Walk-forward backtesting with
            point-in-time data and transaction costs is in development. Full methodology on
            the backtesting page.
          </p>
        </div>
```

**Step 4: Update existing test that checks old text**

In `web/src/components/landing/__tests__/proof-section.test.tsx`, find the test that checks for "since 2015" and update it to match the new copy. Replace:

```tsx
  it("renders backtesting performance summary", () => {
    render(<ProofSection candidates={[]} />)
    expect(screen.getByText(/since 2015/i)).toBeInTheDocument()
    expect(screen.getByText(/past performance/i)).toBeInTheDocument()
  })
```

With:

```tsx
  it("renders backtesting performance summary", () => {
    render(<ProofSection candidates={[]} />)
    expect(screen.getByText(/every signal recorded/i)).toBeInTheDocument()
    expect(screen.getByText(/past performance/i)).toBeInTheDocument()
  })
```

**Step 5: Run all proof section tests to verify**

Run: `npx vitest run web/src/components/landing/__tests__/proof-section.test.tsx`
Expected: All PASS

**Step 6: Commit**

```bash
git add web/src/components/landing/proof-section.tsx web/src/components/landing/__tests__/proof-section.test.tsx
git commit -m "feat(web): reframe proof section with live tracking instead of backtest placeholder"
```

---

### Task 6: Add Freshness Color-Coding to Metadata Ribbon

Color-code the metadata ribbon freshness indicators. Green = <1 hour since scored. Yellow = <24 hours. Amber = >24 hours.

**Files:**
- Modify: `web/src/components/asset-detail/hero-header.tsx:172-184`
- Test: `web/src/components/asset-detail/__tests__/hero-header.test.tsx`

**Step 1: Write the failing test**

Add to `web/src/components/asset-detail/__tests__/hero-header.test.tsx`:

```tsx
  it("applies freshness color class to scored-at metadata", () => {
    const recentDate = new Date(Date.now() - 30 * 60 * 1000).toISOString() // 30 min ago
    render(<HeroHeader {...baseProps} scoredAt={recentDate} />)
    const ribbon = screen.getByTestId("metadata-ribbon")
    expect(ribbon.querySelector("[data-freshness]")).toHaveClass("text-bullish")
  })

  it("applies stale color when scored >24h ago", () => {
    const oldDate = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString() // 25h ago
    render(<HeroHeader {...baseProps} scoredAt={oldDate} />)
    const ribbon = screen.getByTestId("metadata-ribbon")
    expect(ribbon.querySelector("[data-freshness]")).toHaveClass("text-warning")
  })
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/asset-detail/__tests__/hero-header.test.tsx`
Expected: FAIL — no `data-freshness` element exists

**Step 3: Add freshness color helper and apply to metadata ribbon**

In `web/src/components/asset-detail/hero-header.tsx`:

Add a helper function before the `HeroHeader` component (after `MiniSparkline`):

```tsx
function getFreshnessColor(scoredAt: string | null | undefined): string {
  if (!scoredAt) return "text-text-tertiary"
  const ageMs = Date.now() - new Date(scoredAt).getTime()
  const oneHour = 60 * 60 * 1000
  const oneDay = 24 * oneHour
  if (ageMs < oneHour) return "text-bullish"
  if (ageMs < oneDay) return "text-text-tertiary"
  return "text-warning"
}
```

In the metadata ribbon (lines 173-184), replace the scored-at span:

```tsx
        <span data-freshness className={getFreshnessColor(scoredAt)}>
          Scored: {scoredAt ? formatScoredAt(scoredAt) : "N/A"}
        </span>
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/asset-detail/__tests__/hero-header.test.tsx`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/hero-header.tsx web/src/components/asset-detail/__tests__/hero-header.test.tsx
git commit -m "feat(web): add freshness color-coding to hero metadata ribbon"
```

---

### Task 7: Add Low-Results Contextual Messaging to Dashboard

When only 2-3 picks exist, the dashboard should contextualize scarcity. Add a banner above the picks grid that says "Only N stocks survived all filters and scored above the conviction threshold."

**Files:**
- Modify: `web/src/app/dashboard/page.tsx:77-82`
- Test: (inline — test via the existing dashboard integration patterns)

**Step 1: Add the low-results banner in dashboard page**

In `web/src/app/dashboard/page.tsx`, replace the "Top Picks" section (lines 77-82):

```tsx
      <section className="mb-10">
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Top Picks
        </h2>
        {(data?.picks?.length ?? 0) > 0 && (data?.picks?.length ?? 0) <= 5 && data?.total_scored && (
          <p className="text-xs text-text-tertiary mb-4">
            Only {data.picks.length} stock{data.picks.length !== 1 ? "s" : ""} survived
            all filters and scored above the conviction threshold.{" "}
            {data.total_scored} stocks were evaluated.
          </p>
        )}
        <PicksGrid
          picks={data?.picks ?? []}
          totalScored={data?.total_scored}
          universeSize={data?.universe?.size}
        />
      </section>
```

**Step 2: Commit**

```bash
git add web/src/app/dashboard/page.tsx
git commit -m "feat(web): add low-results contextual messaging to dashboard"
```

---

### Task 8: Add Filing Period Attribution to Filter Cards

Show which SEC filing period each filter's data comes from. The `FilterResultResponse.detail` field already contains filing context when available from the API. Add a dedicated filing period display when the detail mentions a filing date.

Since the API already sends `detail` which often includes the filing context, and the filter card already renders `filter.detail`, this task adds a distinct `data_period` field to the filter metadata and renders it.

**Files:**
- Modify: `web/src/lib/filter-metadata.ts`
- Modify: `web/src/components/asset-detail/filter-card.tsx:60-91`
- Test: `web/src/components/asset-detail/__tests__/filter-card.test.tsx`

**Step 1: Write the failing test**

Add to `web/src/components/asset-detail/__tests__/filter-card.test.tsx`:

```tsx
  it("shows filing period when filter has detail containing period info", () => {
    const filter = {
      name: "altman_z_score",
      passed: true,
      value: 5.12,
      threshold: 1.1,
      detail: "Based on Q3 2025 10-Q filed Oct 2025",
      verdict: "passed",
    }
    render(<FilterCard filter={filter} expanded={true} />)
    expect(screen.getByText(/Q3 2025 10-Q/)).toBeInTheDocument()
  })
```

**Step 2: Run test to verify it fails or passes**

Run: `npx vitest run web/src/components/asset-detail/__tests__/filter-card.test.tsx`

Note: This test may already pass because `filter.detail` is already rendered at line 108-110. If it passes, the filter card already handles this. If not, the `detail` field rendering needs adjustment.

If the test passes as-is, this task is a no-op and we can skip implementation — the existing `filter.detail` rendering already surfaces filing period data when the API provides it. Commit only the test.

**Step 3: Commit**

```bash
git add web/src/components/asset-detail/__tests__/filter-card.test.tsx
git commit -m "test(web): verify filter card displays filing period from detail field"
```

---

## Task Dependency Map

```
Task 1 (elimination rate)     — independent
Task 2 (sector survivor CTA)  — independent (touches same file as Task 1; if parallel, merge carefully)
Task 3 (dashboard empty state) — independent
Task 4 (market regime label)   — independent
Task 5 (proof section reframe) — independent
Task 6 (freshness colors)      — independent
Task 7 (low-results message)   — independent (touches dashboard/page.tsx like Task 3; if parallel, merge)
Task 8 (filing period)         — independent
```

Tasks 1 & 2 both modify `asset-detail-view.tsx` — run sequentially or merge interface changes.
Tasks 3, 4 & 7 all modify `dashboard/page.tsx` — run sequentially or merge.
All other tasks are fully independent.

## Test Commands

```bash
# Individual task verification
npx vitest run web/src/components/asset-detail/__tests__/elimination-gauntlet.test.tsx
npx vitest run web/src/components/asset-detail/__tests__/asset-detail-view.test.tsx
npx vitest run web/src/components/dashboard/__tests__/picks-grid.test.tsx
npx vitest run web/src/components/dashboard/__tests__/market-regime-label.test.tsx
npx vitest run web/src/components/landing/__tests__/proof-section.test.tsx
npx vitest run web/src/components/asset-detail/__tests__/hero-header.test.tsx
npx vitest run web/src/components/asset-detail/__tests__/filter-card.test.tsx

# Full suite
npx vitest run web/src/
```
