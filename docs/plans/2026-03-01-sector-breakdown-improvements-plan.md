# Sector Breakdown Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix sector breakdown chart to show all tiers (Exceptional/High/Medium), fix dark mode hover to use brightened bar colors instead of white, and rebalance dashboard layout so heatmap is full-width below paired charts.

**Architecture:** Three independent fixes in the web/ package. Data completeness fix merges watchlist into allPicks at the page level. Dark mode hover adds a `useIsDark` hook and Recharts `activeBar` prop. Layout fix reorders ProofSection children and adds col-span-2 to heatmap.

**Tech Stack:** Next.js 15, React 19, Recharts, Tailwind v4, Vitest + Testing Library

**Design doc:** `docs/plans/2026-03-01-sector-breakdown-improvements-design.md`

---

### Task 1: Merge watchlist into allPicks for data completeness

**Files:**
- Modify: `web/src/app/page.tsx:7-41`

**Step 1: Add watchlistToCandidateCard converter**

After the existing `toCandidateCard` function (line 27), add:

```typescript
function watchlistToCandidateCard(
  item: DashboardResponse["watchlist"][0],
): CandidateCard {
  return {
    ticker: item.ticker,
    name: item.name,
    sector: item.sector ?? "Unknown",
    actual_price: item.actual_price ?? 0,
    buy_price: 0,
    margin_of_safety: 0,
    score: item.composite_raw_score,
    composite_percentile: 0,
    quality_percentile: 0,
    value_percentile: 0,
    momentum_percentile: 0,
    sentiment_percentile: 0,
    growth_percentile: 0,
    scored_at: new Date().toISOString(),
    composite_tier: item.composite_tier,
    filters_passed: 0,
    filters_total: 0,
  }
}
```

**Step 2: Merge picks + watchlist in getHomepageData**

Replace lines 33-36 in `getHomepageData()`:

```typescript
// Before:
const allCards = data.picks.map(toCandidateCard)
return {
  candidates: allCards.slice(0, 5),
  allPicks: allCards,

// After:
const pickCards = data.picks.map(toCandidateCard)
const watchlistCards = (data.watchlist ?? []).map(watchlistToCandidateCard)
const allCards = [...pickCards, ...watchlistCards]
return {
  candidates: pickCards.slice(0, 5),
  allPicks: allCards,
```

Note: `candidates` (hero section top-5) stays picks-only. Only `allPicks` (passed to ProofSection for the sector chart) gets both.

**Step 3: Run the build to verify no type errors**

Run: `cd web && npx next build 2>&1 | head -30`
Expected: No TypeScript errors related to page.tsx

**Step 4: Commit**

```bash
git add web/src/app/page.tsx
git commit -m "fix(web): include medium-tier watchlist in sector breakdown data"
```

---

### Task 2: Fix dark mode hover on sector chart bars

**Files:**
- Modify: `web/src/components/landing/proof-sector-chart.tsx:1-143`

**Step 1: Add useIsDark hook**

After the existing `useIsNarrow` hook (line 56), add:

```typescript
function useIsDark(): boolean {
  const [dark, setDark] = useState(false)
  useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)")
    setDark(mql.matches)
    const handler = (e: MediaQueryListEvent) => setDark(e.matches)
    mql.addEventListener("change", handler)
    return () => mql.removeEventListener("change", handler)
  }, [])
  return dark
}
```

**Step 2: Also detect .dark class on documentElement**

The app uses a `.dark` class on `<html>` (not just prefers-color-scheme). Update the hook to check both:

```typescript
function useIsDark(): boolean {
  const [dark, setDark] = useState(false)
  useEffect(() => {
    const checkDark = () =>
      document.documentElement.classList.contains("dark") ||
      window.matchMedia("(prefers-color-scheme: dark)").matches
    setDark(checkDark())
    const observer = new MutationObserver(() => setDark(checkDark()))
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    })
    const mql = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => setDark(checkDark())
    mql.addEventListener("change", handler)
    return () => {
      observer.disconnect()
      mql.removeEventListener("change", handler)
    }
  }, [])
  return dark
}
```

**Step 3: Use isDark in the component**

In `ProofSectorChart`, after `const isNarrow = useIsNarrow()`, add:

```typescript
const isDark = useIsDark()
```

**Step 4: Disable Recharts default cursor and add activeBar**

On the `<Tooltip>` component (line 96), add `cursor={false}`:

```tsx
<Tooltip
  cursor={false}
  contentStyle={{
    background: "var(--color-bg-elevated)",
    border: "1px solid var(--color-border-subtle)",
    borderRadius: "8px",
    fontSize: "11px",
  }}
/>
```

On each `<Bar>`, add `activeBar` prop that brightens the fill in dark mode. Replace the three `<Bar>` elements:

```tsx
<Bar
  dataKey="exceptional"
  name="Exceptional"
  fill="var(--color-accent)"
  activeBar={{ fill: isDark ? "#24A070" : "var(--color-accent)" }}
  radius={[0, 4, 4, 0]}
  barSize={isNarrow ? 16 : 8}
  stackId={isNarrow ? "stack" : undefined}
/>
<Bar
  dataKey="high"
  name="High"
  fill="color-mix(in srgb, var(--color-accent), transparent 40%)"
  activeBar={{
    fill: isDark
      ? "color-mix(in srgb, #24A070, transparent 40%)"
      : "color-mix(in srgb, var(--color-accent), transparent 40%)",
  }}
  radius={[0, 4, 4, 0]}
  barSize={isNarrow ? 16 : 8}
  stackId={isNarrow ? "stack" : undefined}
/>
<Bar
  dataKey="medium"
  name="Medium"
  fill="color-mix(in srgb, var(--color-warning), transparent 40%)"
  activeBar={{
    fill: isDark
      ? "color-mix(in srgb, #E0BC5A, transparent 40%)"
      : "color-mix(in srgb, var(--color-warning), transparent 40%)",
  }}
  radius={[0, 4, 4, 0]}
  barSize={isNarrow ? 16 : 8}
  stackId={isNarrow ? "stack" : undefined}
/>
```

**Step 5: Run build to verify**

Run: `cd web && npx next build 2>&1 | head -30`
Expected: No TypeScript errors

**Step 6: Commit**

```bash
git add web/src/components/landing/proof-sector-chart.tsx
git commit -m "fix(web): use brightened bar colors for dark mode hover instead of white"
```

---

### Task 3: Rebalance ProofSection layout

**Files:**
- Modify: `web/src/components/landing/proof-section.tsx:94-110`

**Step 1: Add className prop to ProofCard**

Update the `ProofCardProps` interface (line 12) and the component (line 57):

```typescript
interface ProofCardProps {
  title: string
  className?: string
  children: ReactNode
}

function ProofCard({ title, className, children }: ProofCardProps) {
  // ...
  return (
    <div ref={cardRef} className={`terminal-card p-6 ${className ?? ""}`}>
```

**Step 2: Reorder cards and add col-span**

Replace the grid div (lines 94-110):

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
  <ProofCard title="Factor Transparency">
    <ProofFactorBars />
  </ProofCard>
  <ProofCard title="System Selectivity">
    <ProofSelectivityFunnel />
  </ProofCard>
  <ProofCard title="Sector Breakdown">
    <ProofSectorChart candidates={candidates} />
  </ProofCard>
  <ProofCard title="Historical Application">
    <ProofHistoricalChart />
  </ProofCard>
  <ProofCard title="Correlation Heatmap" className="md:col-span-2">
    <ProofHeatmap />
  </ProofCard>
</div>
```

Changes from original:
- Sector Breakdown stays at position 3
- Historical Application moves from position 5 to position 4 (pairs with Sector)
- Correlation Heatmap moves from position 4 to position 5 with `md:col-span-2`

**Step 3: Run build to verify**

Run: `cd web && npx next build 2>&1 | head -30`
Expected: No errors

**Step 4: Commit**

```bash
git add web/src/components/landing/proof-section.tsx
git commit -m "fix(web): rebalance proof section layout with full-width heatmap"
```

---

### Task 4: Add tests for medium-tier rendering and aggregation

**Files:**
- Modify: `web/src/components/landing/__tests__/proof-sector-chart.test.tsx`

**Step 1: Add test for medium-tier candidates in aggregation**

Add after the existing tests (line 87):

```typescript
it("includes medium-tier candidates in chart data", () => {
  const candidates = [
    makeCandidate({ ticker: "A", sector: "Technology", composite_tier: "exceptional" }),
    makeCandidate({ ticker: "B", sector: "Technology", composite_tier: "high" }),
    makeCandidate({ ticker: "C", sector: "Technology", composite_tier: "medium" }),
    makeCandidate({ ticker: "D", sector: "Healthcare", composite_tier: "medium" }),
  ]
  render(<ProofSectorChart candidates={candidates} />)
  expect(screen.getByTestId("sector-bar-chart")).toBeInTheDocument()
  // Chart renders with all 4 candidates across 2 sectors
  expect(screen.getByLabelText(/sector breakdown/i)).toBeInTheDocument()
})
```

**Step 2: Add test for aggregateBySector logic directly**

Export the `aggregateBySector` function from `proof-sector-chart.tsx` by changing line 27:

```typescript
export function aggregateBySector(candidates: CandidateCard[]): SectorRow[] {
```

Also export the `SectorRow` interface (line 19):

```typescript
export interface SectorRow {
```

Then add a unit test:

```typescript
import { aggregateBySector } from "../proof-sector-chart"

it("aggregateBySector counts all three tiers correctly", () => {
  const candidates = [
    makeCandidate({ sector: "Tech", composite_tier: "exceptional" }),
    makeCandidate({ sector: "Tech", composite_tier: "high" }),
    makeCandidate({ sector: "Tech", composite_tier: "medium" }),
    makeCandidate({ sector: "Tech", composite_tier: "medium" }),
    makeCandidate({ sector: "Health", composite_tier: "high" }),
  ]
  const rows = aggregateBySector(candidates)
  expect(rows).toHaveLength(2)

  const tech = rows.find((r) => r.sector === "Tech")!
  expect(tech.exceptional).toBe(1)
  expect(tech.high).toBe(1)
  expect(tech.medium).toBe(2)
  expect(tech.total).toBe(4)

  const health = rows.find((r) => r.sector === "Health")!
  expect(health.exceptional).toBe(0)
  expect(health.high).toBe(1)
  expect(health.medium).toBe(0)
  expect(health.total).toBe(1)
})

it("aggregateBySector sorts by total descending", () => {
  const candidates = [
    makeCandidate({ sector: "Small", composite_tier: "high" }),
    makeCandidate({ sector: "Big", composite_tier: "exceptional" }),
    makeCandidate({ sector: "Big", composite_tier: "high" }),
    makeCandidate({ sector: "Big", composite_tier: "medium" }),
  ]
  const rows = aggregateBySector(candidates)
  expect(rows[0].sector).toBe("Big")
  expect(rows[1].sector).toBe("Small")
})
```

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-sector-chart.test.tsx`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add web/src/components/landing/__tests__/proof-sector-chart.test.tsx web/src/components/landing/proof-sector-chart.tsx
git commit -m "test(web): add sector chart tests for medium tier and aggregation logic"
```

---

### Task 5: Run full test suite and verify

**Step 1: Run all web tests**

Run: `cd web && npx vitest run`
Expected: All ~1285 tests pass, no regressions

**Step 2: Run build**

Run: `cd web && npx next build 2>&1 | tail -20`
Expected: Clean build with no errors

**Step 3: Visual verification (optional)**

Start dev server and check:
- Sector chart shows bars for all three tiers (Exceptional, High, Medium)
- Dark mode hover brightens bars without white flash
- Layout: Row 1 (Factor | Selectivity), Row 2 (Sector | Historical), Row 3 (Heatmap full-width)
