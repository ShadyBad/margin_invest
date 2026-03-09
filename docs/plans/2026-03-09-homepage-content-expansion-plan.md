# Homepage Content Expansion — Implementation Plan

**Goal:** Add three new data-driven sections to the landing page between Evidence and Pricing.
**Architecture:** 4 tasks. Tasks 1-3 create the sections (parallel, different files). Task 4 wires them into the page.
**Tech:** Next.js 16, React 19, Tailwind v4, GSAP ScrollTrigger (viewport-enter fade), Vitest

**Design doc:** `docs/plans/2026-03-09-homepage-content-expansion-design.md`

---

### Task 1: How The Engine Works Section

**Files:**
- Create: `web/src/components/landing/how-it-works-section.tsx`
- Create: `web/src/components/landing/__tests__/how-it-works-section.test.tsx`

**Step 1: Write test**

The test verifies the component renders 4 pipeline steps with live data, and falls back gracefully when data is null.

```tsx
// web/src/components/landing/__tests__/how-it-works-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), set: vi.fn(), to: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { HowItWorksSection } from "../how-it-works-section"
import type { HomepageData } from "../types"

const mockData: HomepageData = {
  candidates: [],
  allPicks: [],
  last_updated: "2026-03-09T00:00:00Z",
  universe_size: 3056,
  eligible_count: 842,
  total_scored: 842,
  total_universe: 3056,
  surviving_count: 12,
}

describe("HowItWorksSection", () => {
  it("renders 4 pipeline steps with live counts", () => {
    render(<HowItWorksSection data={mockData} />)
    expect(screen.getByText("3,056")).toBeInTheDocument()
    expect(screen.getByText("842")).toBeInTheDocument()
    expect(screen.getByText("12")).toBeInTheDocument()
    expect(screen.getByText(/SCAN/)).toBeInTheDocument()
    expect(screen.getByText(/ELIMINATE/)).toBeInTheDocument()
    expect(screen.getByText(/SCORE/)).toBeInTheDocument()
    expect(screen.getByText(/SURFACE/)).toBeInTheDocument()
  })

  it("renders dashes when data is null", () => {
    render(<HowItWorksSection data={null} />)
    const dashes = screen.getAllByText("—")
    expect(dashes.length).toBeGreaterThanOrEqual(4)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/how-it-works-section.test.tsx`
Expected: FAIL — module not found.

**Step 3: Implement the component**

```tsx
// web/src/components/landing/how-it-works-section.tsx
"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "./types"

interface HowItWorksSectionProps {
  data: HomepageData | null
}

const STEPS = [
  {
    number: "01",
    label: "SCAN",
    dataKey: "total_universe" as const,
    description: "Every US-listed equity, daily",
  },
  {
    number: "02",
    label: "ELIMINATE",
    dataKey: "eligible_count" as const,
    description: "6 forensic filters. Beneish, Altman, liquidity, more.",
  },
  {
    number: "03",
    label: "SCORE",
    dataKey: "total_scored" as const,
    description: "5-factor composite. Sector-neutral percentile ranks.",
  },
  {
    number: "04",
    label: "SURFACE",
    dataKey: "surviving_count" as const,
    description: "Only the strongest survive all gates.",
  },
]

export function HowItWorksSection({ data }: HowItWorksSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = sectionRef.current
      if (!el) return

      const cards = el.querySelectorAll("[data-step-card]")
      gsap.set(cards, { opacity: 0, y: 20 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          gsap.to(cards, {
            opacity: 1,
            y: 0,
            duration: 0.5,
            stagger: 0.1,
            ease: "power2.out",
          })
        },
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [])

  return (
    <section ref={sectionRef} className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-text-tertiary mb-8 text-center flex items-center justify-center gap-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent/50" />
          HOW THE ENGINE WORKS
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {STEPS.map((step, i) => (
            <div
              key={step.label}
              data-step-card
              className="bg-bg-elevated border border-border-subtle rounded-xl p-5 relative"
            >
              {i < STEPS.length - 1 && (
                <div className="hidden lg:block absolute top-1/2 -right-2.5 text-text-tertiary text-xs">
                  &rarr;
                </div>
              )}
              <div className="font-mono text-xs text-accent/60 mb-2">
                {step.number}
              </div>
              <div className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary mb-3">
                {step.label}
              </div>
              <div className="font-display text-3xl text-text-primary mb-2">
                {data ? data[step.dataKey].toLocaleString() : "—"}
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/landing/__tests__/how-it-works-section.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/how-it-works-section.tsx web/src/components/landing/__tests__/how-it-works-section.test.tsx
git commit -m "feat(web): add How The Engine Works section with live pipeline data"
```

---

### Task 2: What Survives (Results Showcase) Section

**Files:**
- Create: `web/src/components/landing/results-showcase-section.tsx`
- Create: `web/src/components/landing/__tests__/results-showcase-section.test.tsx`

**Step 1: Write test**

```tsx
// web/src/components/landing/__tests__/results-showcase-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), set: vi.fn(), to: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { ResultsShowcaseSection } from "../results-showcase-section"
import type { HomepageData, CandidateCard } from "../types"

function makeCandidate(overrides: Partial<CandidateCard>): CandidateCard {
  return {
    ticker: "AAPL",
    name: "Apple Inc.",
    sector: "Technology",
    actual_price: 185.0,
    buy_price: 150.0,
    margin_of_safety: 0.23,
    score: 82,
    composite_percentile: 82,
    composite_tier: "exceptional",
    quality_percentile: 88,
    value_percentile: 72,
    momentum_percentile: 65,
    sentiment_percentile: 70,
    growth_percentile: 60,
    scored_at: "2026-03-09T12:00:00Z",
    filters_passed: 6,
    filters_total: 6,
    ...overrides,
  }
}

const mockData: HomepageData = {
  candidates: [
    makeCandidate({ ticker: "AAPL", name: "Apple Inc.", score: 82 }),
    makeCandidate({ ticker: "MSFT", name: "Microsoft Corp.", score: 78 }),
    makeCandidate({ ticker: "JNJ", name: "Johnson & Johnson", score: 75 }),
  ],
  allPicks: [],
  last_updated: "2026-03-09T12:00:00Z",
  universe_size: 3056,
  eligible_count: 842,
  total_scored: 842,
  total_universe: 3056,
  surviving_count: 12,
}

describe("ResultsShowcaseSection", () => {
  it("renders top 3 candidate cards with tickers and scores", () => {
    render(<ResultsShowcaseSection data={mockData} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("MSFT")).toBeInTheDocument()
    expect(screen.getByText("JNJ")).toBeInTheDocument()
  })

  it("renders cycle stats line", () => {
    render(<ResultsShowcaseSection data={mockData} />)
    expect(screen.getByText(/842 stocks scored/)).toBeInTheDocument()
    expect(screen.getByText(/12 survived/)).toBeInTheDocument()
  })

  it("renders empty state when data is null", () => {
    render(<ResultsShowcaseSection data={null} />)
    expect(screen.getByText(/Scoring data loads/i)).toBeInTheDocument()
  })

  it("renders empty state when no candidates", () => {
    render(
      <ResultsShowcaseSection
        data={{ ...mockData, candidates: [] }}
      />
    )
    expect(screen.getByText(/Scoring in progress/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/results-showcase-section.test.tsx`
Expected: FAIL

**Step 3: Implement**

```tsx
// web/src/components/landing/results-showcase-section.tsx
"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "./types"

interface ResultsShowcaseSectionProps {
  data: HomepageData | null
}

function FactorBar({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[10px] text-text-tertiary w-20 shrink-0 uppercase tracking-wider">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${Math.min(100, Math.max(0, value))}%`,
            background:
              value >= 70
                ? "var(--color-accent)"
                : value >= 40
                  ? "var(--color-text-tertiary)"
                  : "var(--color-warning)",
          }}
        />
      </div>
      <span className="font-mono text-[10px] text-text-secondary w-6 text-right">
        {Math.round(value)}
      </span>
    </div>
  )
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime()
  const hours = Math.floor(diff / 3600000)
  if (hours < 1) return "just now"
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function ResultsShowcaseSection({
  data,
}: ResultsShowcaseSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = sectionRef.current
      if (!el) return

      const panel = el.querySelector("[data-results-panel]")
      if (!panel) return

      gsap.set(panel, { opacity: 0, y: 24 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          gsap.to(panel, {
            opacity: 1,
            y: 0,
            duration: 0.6,
            ease: "power2.out",
          })
        },
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [])

  const top3 = data?.candidates.slice(0, 3) ?? []
  const hasData = data && top3.length > 0

  return (
    <section ref={sectionRef} className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        <div
          data-results-panel
          className="border border-border-subtle rounded-xl overflow-hidden"
          style={{ background: "var(--color-bg-elevated)" }}
        >
          {/* Terminal header */}
          <div
            className="px-6 py-3 border-b border-border-subtle"
            style={{ background: "var(--color-bg-subtle)" }}
          >
            <span className="font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary">
              Current Cycle Results
            </span>
          </div>

          {hasData ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-border-subtle">
                {top3.map((c) => (
                  <div key={c.ticker} className="p-6">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="text-lg font-bold text-text-primary">
                          {c.ticker}
                        </div>
                        <div className="text-xs text-text-secondary line-clamp-1">
                          {c.name}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-display text-3xl text-accent leading-none">
                          {Math.round(c.score)}
                        </div>
                        <div className="font-mono text-[9px] text-text-tertiary uppercase tracking-wider mt-1">
                          composite
                        </div>
                      </div>
                    </div>

                    <div className="space-y-1.5 mb-3">
                      <FactorBar value={c.quality_percentile} label="Quality" />
                      <FactorBar value={c.value_percentile} label="Value" />
                      <FactorBar
                        value={c.momentum_percentile}
                        label="Momentum"
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
                        {c.sector}
                      </span>
                      <span className="text-[10px] font-mono text-text-tertiary">
                        {timeAgo(c.scored_at)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Stats line */}
              <div className="px-6 py-3 border-t border-border-subtle text-center">
                <p className="text-xs font-mono text-text-tertiary">
                  {data.total_scored.toLocaleString()} stocks scored &middot;{" "}
                  {(
                    data.total_universe - data.eligible_count
                  ).toLocaleString()}{" "}
                  eliminated &middot; {data.surviving_count} survived &middot;
                  Last cycle:{" "}
                  {timeAgo(data.last_updated)}
                </p>
              </div>
            </>
          ) : (
            <div className="p-12 text-center">
              <p className="text-sm text-text-secondary">
                {data
                  ? "Scoring in progress — results appear after each cycle."
                  : "Scoring data loads after the engine completes a cycle."}
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/landing/__tests__/results-showcase-section.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/results-showcase-section.tsx web/src/components/landing/__tests__/results-showcase-section.test.tsx
git commit -m "feat(web): add results showcase section with live candidate data"
```

---

### Task 3: Three Pillars (Feature Deep-Dives) Section

**Files:**
- Create: `web/src/components/landing/pillars-section.tsx`
- Create: `web/src/components/landing/__tests__/pillars-section.test.tsx`

**Step 1: Write test**

```tsx
// web/src/components/landing/__tests__/pillars-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), set: vi.fn(), to: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { PillarsSection } from "../pillars-section"
import type { HomepageData, CandidateCard } from "../types"

function makeCandidate(overrides: Partial<CandidateCard>): CandidateCard {
  return {
    ticker: "AAPL",
    name: "Apple Inc.",
    sector: "Technology",
    actual_price: 185.0,
    buy_price: 150.0,
    margin_of_safety: 0.23,
    score: 82,
    composite_percentile: 82,
    composite_tier: "exceptional",
    quality_percentile: 88,
    value_percentile: 72,
    momentum_percentile: 65,
    sentiment_percentile: 70,
    growth_percentile: 60,
    scored_at: "2026-03-09T12:00:00Z",
    filters_passed: 6,
    filters_total: 6,
    ...overrides,
  }
}

const mockData: HomepageData = {
  candidates: [makeCandidate({})],
  allPicks: [
    makeCandidate({ sector: "Technology" }),
    makeCandidate({ sector: "Technology", ticker: "MSFT" }),
    makeCandidate({ sector: "Healthcare", ticker: "JNJ" }),
    makeCandidate({ sector: "Financials", ticker: "JPM" }),
  ],
  last_updated: "2026-03-09T12:00:00Z",
  universe_size: 3056,
  eligible_count: 842,
  total_scored: 842,
  total_universe: 3056,
  surviving_count: 12,
}

describe("PillarsSection", () => {
  it("renders 3 pillar headings", () => {
    render(<PillarsSection data={mockData} />)
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
    expect(screen.getByText("Multi-Factor Scoring")).toBeInTheDocument()
    expect(screen.getByText("Sector-Neutral Ranking")).toBeInTheDocument()
  })

  it("shows elimination rate with live data", () => {
    render(<PillarsSection data={mockData} />)
    expect(screen.getByText(/842/)).toBeInTheDocument()
    expect(screen.getByText(/3,056/)).toBeInTheDocument()
  })

  it("shows factor breakdown for top candidate", () => {
    render(<PillarsSection data={mockData} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText(/Quality/)).toBeInTheDocument()
  })

  it("shows sector distribution from allPicks", () => {
    render(<PillarsSection data={mockData} />)
    expect(screen.getByText(/Technology/)).toBeInTheDocument()
    expect(screen.getByText(/Healthcare/)).toBeInTheDocument()
  })

  it("renders gracefully when data is null", () => {
    render(<PillarsSection data={null} />)
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/pillars-section.test.tsx`
Expected: FAIL

**Step 3: Implement**

```tsx
// web/src/components/landing/pillars-section.tsx
"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "./types"

interface PillarsSectionProps {
  data: HomepageData | null
}

const FILTER_NAMES = [
  "Beneish M-Score",
  "Altman Z-Score",
  "Penny stock exclusion",
  "Delisting detection",
  "Liquidity threshold",
  "Data sufficiency",
]

const FACTORS = [
  { key: "quality_percentile" as const, label: "Quality" },
  { key: "value_percentile" as const, label: "Value" },
  { key: "momentum_percentile" as const, label: "Momentum" },
  { key: "sentiment_percentile" as const, label: "Sentiment" },
  { key: "growth_percentile" as const, label: "Growth" },
]

function FactorBar({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[10px] text-text-tertiary w-16 shrink-0 uppercase tracking-wider">
        {label}
      </span>
      <div className="flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${Math.min(100, Math.max(0, value))}%`,
            background:
              value >= 70
                ? "var(--color-accent)"
                : value >= 40
                  ? "var(--color-text-tertiary)"
                  : "var(--color-warning)",
          }}
        />
      </div>
      <span className="font-mono text-[10px] text-text-secondary w-6 text-right">
        {Math.round(value)}
      </span>
    </div>
  )
}

function getSectorCounts(
  data: HomepageData
): { sector: string; count: number }[] {
  const map = new Map<string, number>()
  for (const pick of data.allPicks) {
    const s = pick.sector || "Unknown"
    map.set(s, (map.get(s) ?? 0) + 1)
  }
  return Array.from(map.entries())
    .map(([sector, count]) => ({ sector, count }))
    .sort((a, b) => b.count - a.count)
}

export function PillarsSection({ data }: PillarsSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false
    const triggers: { kill: () => void }[] = []

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = sectionRef.current
      if (!el) return

      const pillars = el.querySelectorAll("[data-pillar]")
      pillars.forEach((pillar, i) => {
        gsap.set(pillar, { opacity: 0, y: 24 })
        triggers.push(
          ScrollTrigger.create({
            trigger: pillar,
            start: "top 85%",
            once: true,
            onEnter: () => {
              gsap.to(pillar, {
                opacity: 1,
                y: 0,
                duration: 0.5,
                delay: i * 0.1,
                ease: "power2.out",
              })
            },
          })
        )
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      triggers.forEach((t) => t.kill())
    }
  }, [])

  const topCandidate = data?.candidates[0] ?? null
  const eliminationRate = data
    ? (
        ((data.total_universe - data.eligible_count) / data.total_universe) *
        100
      ).toFixed(1)
    : null
  const sectorCounts = data ? getSectorCounts(data) : []
  const maxSectorCount = sectorCounts[0]?.count ?? 1

  return (
    <section ref={sectionRef} className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-text-tertiary mb-10 text-center flex items-center justify-center gap-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent/50" />
          THREE PILLARS
        </div>

        <div className="space-y-6">
          {/* Pillar 1: Elimination Filters */}
          <div
            data-pillar
            className="bg-bg-elevated border border-border-subtle rounded-xl p-6 md:p-8"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-xl font-semibold text-text-primary mb-3">
                  Elimination Filters
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed mb-4">
                  Before a stock is scored, it must survive six forensic screens.
                  Earnings manipulation, bankruptcy risk, liquidity traps — if any
                  flag triggers, the stock is removed from consideration entirely.
                </p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                  {FILTER_NAMES.map((name) => (
                    <div
                      key={name}
                      className="flex items-center gap-1.5 text-xs text-text-secondary"
                    >
                      <span className="text-accent text-sm">&#10003;</span>
                      {name}
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex flex-col justify-center">
                {data ? (
                  <div className="bg-bg-primary/50 border border-border-subtle rounded-lg p-5 text-center">
                    <div className="font-mono text-xs text-text-tertiary uppercase tracking-wider mb-2">
                      Current elimination rate
                    </div>
                    <div className="font-display text-4xl text-text-primary mb-1">
                      {eliminationRate}%
                    </div>
                    <div className="text-xs text-text-secondary">
                      {data.eligible_count.toLocaleString()} of{" "}
                      {data.total_universe.toLocaleString()} passed all filters
                    </div>
                    {topCandidate && (
                      <div className="mt-3 pt-3 border-t border-border-subtle text-xs text-text-tertiary font-mono">
                        {topCandidate.ticker}: {topCandidate.filters_passed}/
                        {topCandidate.filters_total} filters passed
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-bg-primary/50 border border-border-subtle rounded-lg p-5 text-center">
                    <div className="text-sm text-text-secondary">
                      Elimination stats load after scoring cycle
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Pillar 2: Multi-Factor Scoring */}
          <div
            data-pillar
            className="bg-bg-elevated border border-border-subtle rounded-xl p-6 md:p-8"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="md:order-2">
                <h3 className="text-xl font-semibold text-text-primary mb-3">
                  Multi-Factor Scoring
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed mb-4">
                  Every surviving stock is scored across five factors: Quality,
                  Value, Momentum, Sentiment, and Growth. Each factor uses
                  sector-neutral percentile ranks — comparing apples to apples,
                  banks to banks.
                </p>
                <p className="text-sm text-text-secondary leading-relaxed">
                  The composite score is a weighted blend. No human
                  adjustments. No override button. Same inputs, same outputs.
                </p>
              </div>
              <div className="md:order-1 flex flex-col justify-center">
                {topCandidate ? (
                  <div className="bg-bg-primary/50 border border-border-subtle rounded-lg p-5">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <div className="text-lg font-bold text-text-primary">
                          {topCandidate.ticker}
                        </div>
                        <div className="text-xs text-text-secondary">
                          {topCandidate.name}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-display text-2xl text-accent leading-none">
                          {Math.round(topCandidate.score)}
                        </div>
                        <div className="font-mono text-[9px] text-text-tertiary uppercase tracking-wider mt-0.5">
                          composite
                        </div>
                      </div>
                    </div>
                    <div className="space-y-2">
                      {FACTORS.map((f) => (
                        <FactorBar
                          key={f.key}
                          value={topCandidate[f.key]}
                          label={f.label}
                        />
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="bg-bg-primary/50 border border-border-subtle rounded-lg p-5 text-center">
                    <div className="text-sm text-text-secondary">
                      Factor breakdown loads after scoring cycle
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Pillar 3: Sector-Neutral Ranking */}
          <div
            data-pillar
            className="bg-bg-elevated border border-border-subtle rounded-xl p-6 md:p-8"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-xl font-semibold text-text-primary mb-3">
                  Sector-Neutral Ranking
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed mb-4">
                  A bank with 15% ROIC is excellent — among banks. A tech company
                  with 15% ROIC is below average — among tech. We rank within
                  GICS sector first, then combine. No false comparisons.
                </p>
                <p className="text-sm text-text-secondary leading-relaxed">
                  The result: quality surfaces in every sector, not just the
                  usual suspects.
                </p>
              </div>
              <div className="flex flex-col justify-center">
                {sectorCounts.length > 0 ? (
                  <div className="bg-bg-primary/50 border border-border-subtle rounded-lg p-5">
                    <div className="font-mono text-xs text-text-tertiary uppercase tracking-wider mb-3">
                      Survivors by sector
                    </div>
                    <div className="space-y-2">
                      {sectorCounts.slice(0, 6).map((s) => (
                        <div key={s.sector} className="flex items-center gap-2">
                          <span className="font-mono text-[10px] text-text-secondary w-24 shrink-0 truncate">
                            {s.sector}
                          </span>
                          <div className="flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full bg-accent/60"
                              style={{
                                width: `${(s.count / maxSectorCount) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="font-mono text-[10px] text-text-tertiary w-4 text-right">
                            {s.count}
                          </span>
                        </div>
                      ))}
                    </div>
                    {sectorCounts.length > 6 && (
                      <div className="text-[10px] text-text-tertiary font-mono mt-2">
                        +{sectorCounts.length - 6} more sectors
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-bg-primary/50 border border-border-subtle rounded-lg p-5 text-center">
                    <div className="text-sm text-text-secondary">
                      Sector distribution loads after scoring cycle
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/landing/__tests__/pillars-section.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/pillars-section.tsx web/src/components/landing/__tests__/pillars-section.test.tsx
git commit -m "feat(web): add three pillars feature section with live data"
```

---

### Task 4: Wire Sections into Homepage

**Files:**
- Modify: `web/src/components/landing/homepage-client.tsx`

**Step 1: Add imports and insert sections between Evidence and Pricing**

```tsx
// web/src/components/landing/homepage-client.tsx
"use client"

import { HeroSection } from "./hero-section"
import { AuthorityStrip } from "./authority-strip"
import { EvidenceSection } from "./evidence-section"
import { HowItWorksSection } from "./how-it-works-section"
import { ResultsShowcaseSection } from "./results-showcase-section"
import { PillarsSection } from "./pillars-section"
import { PricingSection } from "./pricing-section"
import { FaqSection } from "./faq-section"
import { FooterSection } from "./footer-section"
import { ScrollCanvas } from "./scroll-canvas"
import type { HomepageData } from "./types"

interface HomepageClientProps {
  data: HomepageData | null
}

export function HomepageClient({ data }: HomepageClientProps) {
  return (
    <ScrollCanvas>
      <HeroSection data={data} />
      <AuthorityStrip />
      <EvidenceSection candidates={data?.allPicks ?? []} />
      <HowItWorksSection data={data} />
      <ResultsShowcaseSection data={data} />
      <PillarsSection data={data} />
      <PricingSection totalUniverse={data?.total_universe} />
      <FaqSection />
      <FooterSection />
    </ScrollCanvas>
  )
}
```

**Step 2: Run all tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -30`
Expected: All tests pass.

**Step 3: Run lint**

Run: `cd web && npx eslint --fix .`
Expected: Clean.

**Step 4: Commit**

```bash
git add web/src/components/landing/homepage-client.tsx
git commit -m "feat(web): wire new sections into homepage between evidence and pricing"
```

---

## Task Order

| Priority | Task | Effort | Dependencies |
|----------|------|--------|--------------|
| 1 | How The Engine Works section | Small | None |
| 2 | Results Showcase section | Medium | None |
| 3 | Three Pillars section | Medium | None |
| 4 | Wire into homepage | Small | Tasks 1-3 |

Tasks 1, 2, 3 can run in parallel. Task 4 after all three.

## Criteria

- Three new sections render between Evidence and Pricing
- All numbers are live from HomepageData (no hardcoded dynamic values)
- Graceful fallback when data is null (dashes or empty state message)
- Viewport-enter fade animations match existing section pattern
- `cd web && npx vitest run` passes
- `cd web && npx eslint --fix .` clean
