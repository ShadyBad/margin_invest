# Growth vs Value Tilt Chart Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the hardcoded "Growth vs Value Tilt" proof-section chart with a vertical bar chart showing real candidate counts per tilt category (Value / Blend / Growth).

**Architecture:** Pure frontend change. Extract a `classifyTilt()` utility, thread candidate data from `page.tsx` through `HomepageClient` → `ProofSection` → `ProofTiltChart`, rewrite the chart as a vertical bar chart with count labels and legend.

**Tech Stack:** TypeScript, React, recharts, vitest, @testing-library/react

**Design doc:** `docs/plans/2026-02-20-growth-value-tilt-chart-design.md`

---

### Task 1: Create classifyTilt utility with tests

**Files:**
- Create: `web/src/components/landing/classify-tilt.ts`
- Create: `web/src/components/landing/__tests__/classify-tilt.test.ts`

**Step 1: Write the failing tests**

Create `web/src/components/landing/__tests__/classify-tilt.test.ts`:

```ts
import { describe, it, expect } from "vitest"
import { classifyTilt, type TiltCounts } from "../classify-tilt"
import type { CandidateCard } from "../types"

function makeCandidate(
  overrides: Partial<CandidateCard> & { growth_percentile: number; value_percentile: number }
): CandidateCard {
  return {
    ticker: "TEST",
    name: "Test Co",
    sector: "Technology",
    actual_price: 100,
    buy_price: 80,
    margin_of_safety: 0.2,
    composite_percentile: 75,
    conviction_level: "high",
    quality_percentile: 70,
    momentum_percentile: 60,
    sentiment_percentile: 50,
    scored_at: "2026-01-01T00:00:00Z",
    filters_passed: 8,
    filters_total: 8,
    ...overrides,
  }
}

describe("classifyTilt", () => {
  it("returns zero counts for empty array", () => {
    expect(classifyTilt([])).toEqual({ Value: 0, Blend: 0, Growth: 0 })
  })

  it("classifies growth-leaning candidate (diff > 10)", () => {
    const candidates = [makeCandidate({ growth_percentile: 80, value_percentile: 50 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 0, Growth: 1 })
  })

  it("classifies value-leaning candidate (diff < -10)", () => {
    const candidates = [makeCandidate({ growth_percentile: 40, value_percentile: 70 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 1, Blend: 0, Growth: 0 })
  })

  it("classifies blend candidate (diff within threshold)", () => {
    const candidates = [makeCandidate({ growth_percentile: 55, value_percentile: 50 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 1, Growth: 0 })
  })

  it("boundary: diff exactly 10 is Blend", () => {
    const candidates = [makeCandidate({ growth_percentile: 60, value_percentile: 50 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 1, Growth: 0 })
  })

  it("boundary: diff exactly -10 is Blend", () => {
    const candidates = [makeCandidate({ growth_percentile: 50, value_percentile: 60 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 1, Growth: 0 })
  })

  it("boundary: diff 11 is Growth", () => {
    const candidates = [makeCandidate({ growth_percentile: 61, value_percentile: 50 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 0, Blend: 0, Growth: 1 })
  })

  it("boundary: diff -11 is Value", () => {
    const candidates = [makeCandidate({ growth_percentile: 50, value_percentile: 61 })]
    expect(classifyTilt(candidates)).toEqual({ Value: 1, Blend: 0, Growth: 0 })
  })

  it("counts multiple candidates across categories", () => {
    const candidates = [
      makeCandidate({ ticker: "A", growth_percentile: 80, value_percentile: 30 }), // Growth
      makeCandidate({ ticker: "B", growth_percentile: 20, value_percentile: 70 }), // Value
      makeCandidate({ ticker: "C", growth_percentile: 50, value_percentile: 55 }), // Blend
      makeCandidate({ ticker: "D", growth_percentile: 90, value_percentile: 40 }), // Growth
      makeCandidate({ ticker: "E", growth_percentile: 30, value_percentile: 80 }), // Value
    ]
    expect(classifyTilt(candidates)).toEqual({ Value: 2, Blend: 1, Growth: 2 })
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/landing/__tests__/classify-tilt.test.ts`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

Create `web/src/components/landing/classify-tilt.ts`:

```ts
import type { CandidateCard } from "./types"

export interface TiltCounts {
  Value: number
  Blend: number
  Growth: number
}

const TILT_THRESHOLD = 10

export function classifyTilt(candidates: CandidateCard[]): TiltCounts {
  const counts: TiltCounts = { Value: 0, Blend: 0, Growth: 0 }
  for (const c of candidates) {
    const diff = c.growth_percentile - c.value_percentile
    if (diff > TILT_THRESHOLD) {
      counts.Growth++
    } else if (diff < -TILT_THRESHOLD) {
      counts.Value++
    } else {
      counts.Blend++
    }
  }
  return counts
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/classify-tilt.test.ts`
Expected: 9 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/classify-tilt.ts web/src/components/landing/__tests__/classify-tilt.test.ts
git commit -m "feat(web): add classifyTilt utility with tests"
```

---

### Task 2: Thread candidate data through component tree

**Files:**
- Modify: `web/src/app/page.tsx:33` — stop slicing picks to 5 for HomepageData
- Modify: `web/src/components/landing/types.ts` — add `allPicks` field to `HomepageData`
- Modify: `web/src/components/landing/homepage-client.tsx:30` — pass allPicks to ProofSection
- Modify: `web/src/components/landing/proof-section.tsx:65-92` — accept and forward candidates prop

**Step 1: Add allPicks to HomepageData type**

In `web/src/components/landing/types.ts`, add a field to `HomepageData`:

```ts
export interface HomepageData {
  candidates: CandidateCard[]
  allPicks: CandidateCard[]    // ← add this line
  last_updated: string
  universe_size: number
  eligible_count: number
  total_scored: number
}
```

**Step 2: Populate allPicks in page.tsx**

In `web/src/app/page.tsx`, change `getHomepageData()` to pass all picks:

Replace:
```ts
    return {
      candidates: data.picks.slice(0, 5).map(toCandidateCard),
      last_updated: data.last_updated,
      universe_size: data.universe?.size ?? 0,
      eligible_count: data.total_scored,
      total_scored: data.total_scored,
    }
```

With:
```ts
    const allCards = data.picks.map(toCandidateCard)
    return {
      candidates: allCards.slice(0, 5),
      allPicks: allCards,
      last_updated: data.last_updated,
      universe_size: data.universe?.size ?? 0,
      eligible_count: data.total_scored,
      total_scored: data.total_scored,
    }
```

**Step 3: Pass allPicks through HomepageClient to ProofSection**

In `web/src/components/landing/homepage-client.tsx`, change:

```tsx
      <ProofSection />
```

To:

```tsx
      <ProofSection candidates={data?.allPicks ?? []} />
```

**Step 4: Accept candidates prop in ProofSection**

In `web/src/components/landing/proof-section.tsx`, change `ProofSection`:

Add prop type and forward to ProofTiltChart:

```tsx
interface ProofSectionProps {
  candidates?: CandidateCard[]
}
```

Change the function signature:
```tsx
export function ProofSection({ candidates = [] }: ProofSectionProps) {
```

Add import:
```tsx
import type { CandidateCard } from "./types"
```

Change the ProofTiltChart usage:
```tsx
          <ProofCard title="Growth vs Value Tilt">
            <ProofTiltChart candidates={candidates} />
          </ProofCard>
```

**Step 5: Run existing tests to make sure nothing breaks**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-section.test.tsx`
Expected: Tests may need updating since ProofSection now expects an optional prop. The existing tests render `<ProofSection />` with no props — this should still work because `candidates` defaults to `[]`.

**Step 6: Commit**

```bash
git add web/src/app/page.tsx web/src/components/landing/types.ts web/src/components/landing/homepage-client.tsx web/src/components/landing/proof-section.tsx
git commit -m "feat(web): thread allPicks through to ProofTiltChart"
```

---

### Task 3: Rewrite ProofTiltChart component

**Files:**
- Modify: `web/src/components/landing/proof-tilt-chart.tsx` — complete rewrite

**Step 1: Rewrite the component**

Replace the entire contents of `web/src/components/landing/proof-tilt-chart.tsx`:

```tsx
"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts"
import { classifyTilt } from "./classify-tilt"
import type { CandidateCard } from "./types"

interface ProofTiltChartProps {
  candidates: CandidateCard[]
}

const BAR_COLORS = [
  "color-mix(in srgb, var(--color-accent), transparent 60%)", // Value — 40% opacity
  "color-mix(in srgb, var(--color-accent), transparent 40%)", // Blend — 60% opacity
  "var(--color-accent)",                                       // Growth — 100% opacity
]

const CATEGORIES = ["Value", "Blend", "Growth"] as const

export function ProofTiltChart({ candidates }: ProofTiltChartProps) {
  const counts = classifyTilt(candidates)
  const maxCount = Math.max(counts.Value, counts.Blend, counts.Growth, 1)

  if (candidates.length === 0) {
    return (
      <div>
        <div className="h-[120px] flex items-center justify-center">
          <p className="text-xs text-text-tertiary">No candidates scored yet</p>
        </div>
        <p className="text-[10px] text-text-tertiary mt-3 text-center">
          Candidates by dominant factor · Value ← Blend → Growth
        </p>
      </div>
    )
  }

  const data = CATEGORIES.map((name) => ({ name, count: counts[name] }))

  return (
    <div>
      <div className="h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barCategoryGap="20%">
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: "var(--color-text-tertiary)" }}
            />
            <YAxis hide domain={[0, maxCount + 1]} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={28} minPointSize={2}>
              {data.map((_, i) => (
                <Cell key={CATEGORIES[i]} fill={BAR_COLORS[i]} />
              ))}
              <LabelList
                dataKey="count"
                position="top"
                style={{ fontSize: 11, fill: "var(--color-text-tertiary)" }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-text-tertiary mt-3 text-center">
        Candidates by dominant factor · Value ← Blend → Growth
      </p>
    </div>
  )
}
```

**Step 2: Verify the app compiles**

Run: `cd web && npx next build 2>&1 | head -30`
Expected: Build succeeds (or at least no TypeScript errors related to this file)

**Step 3: Commit**

```bash
git add web/src/components/landing/proof-tilt-chart.tsx
git commit -m "feat(web): rewrite ProofTiltChart with real data, counts, and legend"
```

---

### Task 4: Update existing tests and add chart component tests

**Files:**
- Modify: `web/src/components/landing/__tests__/proof-section.test.tsx` — update for new prop
- Create: `web/src/components/landing/__tests__/proof-tilt-chart.test.tsx`

**Step 1: Write ProofTiltChart component tests**

Create `web/src/components/landing/__tests__/proof-tilt-chart.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: ({ children }: any) => <div>{children}</div>,
  XAxis: () => null,
  YAxis: () => null,
  Cell: () => null,
  LabelList: ({ dataKey }: any) => <span data-testid={`label-${dataKey}`} />,
}))

import { ProofTiltChart } from "../proof-tilt-chart"
import type { CandidateCard } from "../types"

function makeCandidate(
  overrides: Partial<CandidateCard> & { growth_percentile: number; value_percentile: number }
): CandidateCard {
  return {
    ticker: "TEST",
    name: "Test Co",
    sector: "Technology",
    actual_price: 100,
    buy_price: 80,
    margin_of_safety: 0.2,
    composite_percentile: 75,
    conviction_level: "high",
    quality_percentile: 70,
    momentum_percentile: 60,
    sentiment_percentile: 50,
    scored_at: "2026-01-01T00:00:00Z",
    filters_passed: 8,
    filters_total: 8,
    ...overrides,
  }
}

describe("ProofTiltChart", () => {
  it("renders empty state when no candidates", () => {
    render(<ProofTiltChart candidates={[]} />)
    expect(screen.getByText("No candidates scored yet")).toBeInTheDocument()
  })

  it("renders legend text", () => {
    render(<ProofTiltChart candidates={[]} />)
    expect(
      screen.getByText(/Candidates by dominant factor/)
    ).toBeInTheDocument()
  })

  it("renders bar chart when candidates provided", () => {
    const candidates = [
      makeCandidate({ growth_percentile: 80, value_percentile: 30 }),
    ]
    render(<ProofTiltChart candidates={candidates} />)
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument()
  })

  it("does not render bar chart in empty state", () => {
    render(<ProofTiltChart candidates={[]} />)
    expect(screen.queryByTestId("bar-chart")).not.toBeInTheDocument()
  })
})
```

**Step 2: Run new tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-tilt-chart.test.tsx`
Expected: 4 tests PASS

**Step 3: Update existing proof-section test**

In `web/src/components/landing/__tests__/proof-section.test.tsx`, the existing tests render `<ProofSection />` with no props. Since `candidates` defaults to `[]`, these should still pass. Verify:

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-section.test.tsx`
Expected: All existing tests PASS

If the "renders factor bar labels" test fails because the "Growth" text now conflicts with the tilt chart label "Growth", update the test assertion to be more specific (e.g. check within a specific container, or use `getAllByText`).

**Step 4: Run all landing tests**

Run: `cd web && npx vitest run src/components/landing/`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/__tests__/proof-tilt-chart.test.tsx web/src/components/landing/__tests__/proof-section.test.tsx
git commit -m "test(web): add ProofTiltChart tests and update proof-section tests"
```

---

### Task 5: Final verification

**Step 1: Run full web test suite**

Run: `cd web && npx vitest run`
Expected: All tests pass

**Step 2: Build check**

Run: `cd web && npx next build 2>&1 | tail -20`
Expected: Build succeeds with no errors

**Step 3: Commit any remaining fixes if needed**

If any tests failed and required fixes, commit those fixes here.
