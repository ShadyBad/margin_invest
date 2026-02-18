# Institutional Homepage 10/10 Rebuild — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Full rebuild of the homepage from 6 to 9 sections with live rotating candidate cards, GSAP-only animations, Recharts proof charts, and institutional micro-density metadata.

**Architecture:** Delete all existing `web/src/components/landing/` files. Rebuild each section as a standalone component. GSAP for all animations (no Framer Motion on homepage). Server-side data fetch with static fallback pool. Two small API schema changes to add sentiment/growth percentiles.

**Tech Stack:** Next.js 15, GSAP + ScrollTrigger, Recharts, Tailwind CSS 4, Vitest + Testing Library

**Design Doc:** `docs/plans/2026-02-18-institutional-homepage-design.md`

**Test command (web):** `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run web/src/components/landing/`
**Test command (API):** `cd /Users/brandon/repos/margin_invest && uv run pytest api/tests/test_dashboard.py -v`
**Full test (web):** `cd /Users/brandon/repos/margin_invest && npx --prefix web vitest run`

**GSAP mock for all tests:**
```typescript
vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
    utils: { toArray: vi.fn((x: any) => (Array.isArray(x) ? x : [x])) },
  },
}))

vi.mock("gsap/ScrollTrigger", () => ({
  default: {
    create: vi.fn(),
    getAll: () => [],
    refresh: vi.fn(),
  },
}))
```

**Recharts mock for tests:**
```typescript
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Line: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  Cell: () => null,
}))
```

---

## Task 1: API — Add sentiment_percentile and growth_percentile to PickSummary

**Files:**
- Modify: `api/src/margin_api/schemas/dashboard.py` (line 10-38)
- Modify: `api/src/margin_api/routes/dashboard.py` (line 25-71, `_pick_summary_from_row`)
- Modify: `web/src/lib/api/types.ts` (line 100-128, `PickSummary` interface)
- Test: `api/tests/test_schemas.py`

**Step 1: Add fields to Python PickSummary schema**

In `api/src/margin_api/schemas/dashboard.py`, add after `momentum_percentile` (line 22):
```python
    sentiment_percentile: float | None = None
    growth_percentile: float | None = None
```

**Step 2: Extract from score_detail in route builder**

In `api/src/margin_api/routes/dashboard.py`, add to `_pick_summary_from_row` after `momentum_percentile` assignment (around line 39). The score_detail JSONB stores the full CompositeScore. The engine currently has 3 factors (quality, value, momentum) — sentiment and growth are future factors. Extract if present, else None:

```python
    # Extract optional factor percentiles from score_detail JSONB
    detail = s.score_detail or {}
    sentiment_pct = None
    growth_pct = None
    for factor_key in ("sentiment", "growth"):
        factor_data = detail.get(factor_key)
        if isinstance(factor_data, dict):
            sub_scores = factor_data.get("sub_scores", [])
            if sub_scores:
                total = sum(ss.get("percentile_rank", 0) for ss in sub_scores)
                sentiment_pct if factor_key == "sentiment" else None  # noqa
                if factor_key == "sentiment":
                    sentiment_pct = round(total / len(sub_scores), 1)
                else:
                    growth_pct = round(total / len(sub_scores), 1)
```

Then add to the PickSummary constructor call:
```python
        sentiment_percentile=sentiment_pct,
        growth_percentile=growth_pct,
```

**Step 3: Add to TypeScript PickSummary interface**

In `web/src/lib/api/types.ts`, add after `momentum_percentile` (line 110):
```typescript
  sentiment_percentile?: number | null
  growth_percentile?: number | null
```

**Step 4: Run API tests**

Run: `uv run pytest api/tests/test_dashboard.py api/tests/test_schemas.py -v`
Expected: All pass (new fields are optional with defaults)

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/dashboard.py api/src/margin_api/routes/dashboard.py web/src/lib/api/types.ts
git commit -m "feat(api): add sentiment_percentile and growth_percentile to PickSummary"
```

---

## Task 2: Delete old landing components and tests

**Files:**
- Delete: All files in `web/src/components/landing/` (17 files)
- Delete: All files in `web/src/components/landing/__tests__/` (13 files)

**Step 1: Remove all landing component files**

Delete the entire `web/src/components/landing/` directory. Every component will be rebuilt.

```bash
rm -rf web/src/components/landing/
mkdir -p web/src/components/landing/__tests__
```

**Step 2: Create empty barrel export**

Create `web/src/components/landing/index.ts`:
```typescript
// Landing page components — rebuilt for institutional homepage
```

**Step 3: Verify the app doesn't crash on import resolution**

The page.tsx imports will be broken — that's expected. We'll rebuild each component.

**Step 4: Commit**

```bash
git add -A web/src/components/landing/
git commit -m "chore(web): delete old landing components for institutional rebuild"
```

---

## Task 3: Static fallback data + shared types

**Files:**
- Create: `web/src/components/landing/candidate-data.ts`
- Create: `web/src/components/landing/types.ts`
- Test: `web/src/components/landing/__tests__/candidate-data.test.ts`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/candidate-data.test.ts`:
```typescript
import { describe, it, expect } from "vitest"
import { FALLBACK_CANDIDATES, type CandidateCard } from "../candidate-data"

describe("FALLBACK_CANDIDATES", () => {
  it("contains 3-5 candidates", () => {
    expect(FALLBACK_CANDIDATES.length).toBeGreaterThanOrEqual(3)
    expect(FALLBACK_CANDIDATES.length).toBeLessThanOrEqual(5)
  })

  it("every candidate has required fields", () => {
    for (const c of FALLBACK_CANDIDATES) {
      expect(c.ticker).toBeTruthy()
      expect(c.name).toBeTruthy()
      expect(c.sector).toBeTruthy()
      expect(c.actual_price).toBeGreaterThan(0)
      expect(c.buy_price).toBeGreaterThan(0)
      expect(c.composite_percentile).toBeGreaterThanOrEqual(0)
      expect(c.composite_percentile).toBeLessThanOrEqual(100)
      expect(c.quality_percentile).toBeGreaterThanOrEqual(0)
      expect(c.value_percentile).toBeGreaterThanOrEqual(0)
      expect(c.momentum_percentile).toBeGreaterThanOrEqual(0)
    }
  })

  it("every candidate has margin_of_safety between 0 and 1", () => {
    for (const c of FALLBACK_CANDIDATES) {
      expect(c.margin_of_safety).toBeGreaterThan(0)
      expect(c.margin_of_safety).toBeLessThan(1)
    }
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx --prefix web vitest run web/src/components/landing/__tests__/candidate-data.test.ts`
Expected: FAIL — module not found

**Step 3: Create shared types file**

Create `web/src/components/landing/types.ts`:
```typescript
export interface CandidateCard {
  ticker: string
  name: string
  sector: string
  actual_price: number
  buy_price: number
  margin_of_safety: number
  composite_percentile: number
  conviction_level: string
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  sentiment_percentile: number
  growth_percentile: number
  scored_at: string
  filters_passed: number
  filters_total: number
}

export interface HomepageData {
  candidates: CandidateCard[]
  last_updated: string
  universe_size: number
  eligible_count: number
  total_scored: number
}
```

**Step 4: Create candidate-data.ts with static fallback pool**

Create `web/src/components/landing/candidate-data.ts`:
```typescript
import type { CandidateCard } from "./types"

export type { CandidateCard }

export const FALLBACK_CANDIDATES: CandidateCard[] = [
  {
    ticker: "AAPL",
    name: "Apple Inc.",
    sector: "Technology",
    actual_price: 173.22,
    buy_price: 214.90,
    margin_of_safety: 0.194,
    composite_percentile: 83,
    conviction_level: "high",
    quality_percentile: 85,
    value_percentile: 62,
    momentum_percentile: 71,
    sentiment_percentile: 68,
    growth_percentile: 74,
    scored_at: new Date().toISOString(),
    filters_passed: 8,
    filters_total: 8,
  },
  {
    ticker: "MSFT",
    name: "Microsoft Corp.",
    sector: "Technology",
    actual_price: 378.91,
    buy_price: 445.00,
    margin_of_safety: 0.149,
    composite_percentile: 79,
    conviction_level: "high",
    quality_percentile: 91,
    value_percentile: 55,
    momentum_percentile: 68,
    sentiment_percentile: 72,
    growth_percentile: 81,
    scored_at: new Date().toISOString(),
    filters_passed: 8,
    filters_total: 8,
  },
  {
    ticker: "JNJ",
    name: "Johnson & Johnson",
    sector: "Healthcare",
    actual_price: 152.44,
    buy_price: 188.30,
    margin_of_safety: 0.190,
    composite_percentile: 76,
    conviction_level: "high",
    quality_percentile: 78,
    value_percentile: 82,
    momentum_percentile: 59,
    sentiment_percentile: 61,
    growth_percentile: 55,
    scored_at: new Date().toISOString(),
    filters_passed: 8,
    filters_total: 8,
  },
  {
    ticker: "COST",
    name: "Costco Wholesale",
    sector: "Consumer Staples",
    actual_price: 591.20,
    buy_price: 710.00,
    margin_of_safety: 0.167,
    composite_percentile: 81,
    conviction_level: "high",
    quality_percentile: 88,
    value_percentile: 48,
    momentum_percentile: 77,
    sentiment_percentile: 75,
    growth_percentile: 70,
    scored_at: new Date().toISOString(),
    filters_passed: 8,
    filters_total: 8,
  },
  {
    ticker: "V",
    name: "Visa Inc.",
    sector: "Financials",
    actual_price: 279.55,
    buy_price: 338.20,
    margin_of_safety: 0.173,
    composite_percentile: 78,
    conviction_level: "high",
    quality_percentile: 82,
    value_percentile: 64,
    momentum_percentile: 73,
    sentiment_percentile: 69,
    growth_percentile: 76,
    scored_at: new Date().toISOString(),
    filters_passed: 8,
    filters_total: 8,
  },
]

export const ENGINE_VERSION = "v1.3.2"
export const FACTOR_MODEL_VERSION = "v2.1"
export const DEFAULT_UNIVERSE_SIZE = 1842
export const DEFAULT_ELIGIBLE_COUNT = 143
```

**Step 5: Run test**

Run: `npx --prefix web vitest run web/src/components/landing/__tests__/candidate-data.test.ts`
Expected: PASS

**Step 6: Commit**

```bash
git add web/src/components/landing/types.ts web/src/components/landing/candidate-data.ts web/src/components/landing/__tests__/candidate-data.test.ts
git commit -m "feat(web): add landing page types and static fallback candidate pool"
```

---

## Task 4: Micro-metadata component

**Files:**
- Create: `web/src/components/landing/micro-metadata.tsx`
- Test: `web/src/components/landing/__tests__/micro-metadata.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/micro-metadata.test.tsx`:
```typescript
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MicroMetadata } from "../micro-metadata"

describe("MicroMetadata", () => {
  it("renders text content", () => {
    render(<MicroMetadata text="Engine v1.3.2" />)
    expect(screen.getByText("Engine v1.3.2")).toBeInTheDocument()
  })

  it("applies mono font and tertiary styling", () => {
    render(<MicroMetadata text="Test" />)
    const el = screen.getByText("Test")
    expect(el.className).toContain("font-mono")
    expect(el.className).toContain("text-text-tertiary")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx --prefix web vitest run web/src/components/landing/__tests__/micro-metadata.test.tsx`
Expected: FAIL

**Step 3: Implement**

Create `web/src/components/landing/micro-metadata.tsx`:
```typescript
interface MicroMetadataProps {
  text: string
  className?: string
}

export function MicroMetadata({ text, className = "" }: MicroMetadataProps) {
  return (
    <span
      className={`font-mono text-[10px] uppercase tracking-widest text-text-tertiary ${className}`}
    >
      {text}
    </span>
  )
}
```

**Step 4: Run test**

Run: `npx --prefix web vitest run web/src/components/landing/__tests__/micro-metadata.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/micro-metadata.tsx web/src/components/landing/__tests__/micro-metadata.test.tsx
git commit -m "feat(web): add MicroMetadata component for institutional density"
```

---

## Task 5: Hero Candidate Card (with rotation)

**Files:**
- Create: `web/src/components/landing/hero-candidate-card.tsx`
- Test: `web/src/components/landing/__tests__/hero-candidate-card.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/hero-candidate-card.test.tsx`:
```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, act } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))

vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { HeroCandidateCard } from "../hero-candidate-card"
import { FALLBACK_CANDIDATES } from "../candidate-data"

describe("HeroCandidateCard", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("renders first candidate ticker and name", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders header with Live Engine Output", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText(/live engine output/i)).toBeInTheDocument()
  })

  it("renders conviction score as largest visual element", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText("83")).toBeInTheDocument()
  })

  it("renders 5 factor bars", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText("Valuation")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
    expect(screen.getByText("Sentiment")).toBeInTheDocument()
    expect(screen.getByText("Growth")).toBeInTheDocument()
  })

  it("renders margin of safety", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText("19.4%")).toBeInTheDocument()
  })

  it("renders universe metadata", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} universeSize={1842} eligibleCount={143} />)
    expect(screen.getByText(/1,842/)).toBeInTheDocument()
    expect(screen.getByText(/143/)).toBeInTheDocument()
  })

  it("renders Engine version in header", () => {
    render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
    expect(screen.getByText(/v1\.3\.2/)).toBeInTheDocument()
  })

  it("does not auto-rotate on mobile (disabled by default when single candidate)", () => {
    render(<HeroCandidateCard candidates={[FALLBACK_CANDIDATES[0]]} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx --prefix web vitest run web/src/components/landing/__tests__/hero-candidate-card.test.tsx`
Expected: FAIL

**Step 3: Implement hero-candidate-card.tsx**

Create `web/src/components/landing/hero-candidate-card.tsx`:
```typescript
"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import type { CandidateCard } from "./types"
import { MicroMetadata } from "./micro-metadata"
import { ENGINE_VERSION } from "./candidate-data"

const ROTATION_INTERVAL = 7000
const FADE_OUT_MS = 150
const FADE_IN_MS = 200

interface HeroCandidateCardProps {
  candidates: CandidateCard[]
  universeSize?: number
  eligibleCount?: number
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  const h = d.getHours().toString().padStart(2, "0")
  const m = d.getMinutes().toString().padStart(2, "0")
  return `${h}:${m} EST`
}

function formatMoS(value: number | null): string {
  if (value == null) return "\u2014"
  return `${(value * 100).toFixed(1)}%`
}

function formatPrice(value: number | null): string {
  if (value == null) return "\u2014"
  return `$${value.toFixed(2)}`
}

function FactorBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-tertiary w-20 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all duration-700"
          style={{ width: `${value}%`, transitionTimingFunction: "cubic-bezier(0.4, 0, 0.2, 1)" }}
        />
      </div>
      <span className="font-mono text-xs text-text-secondary w-8 text-right">{Math.round(value)}</span>
    </div>
  )
}

export function HeroCandidateCard({ candidates, universeSize, eligibleCount }: HeroCandidateCardProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [visible, setVisible] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const touchStartX = useRef(0)

  const data = candidates[currentIndex] ?? candidates[0]
  const canRotate = candidates.length > 1

  const advance = useCallback((direction: 1 | -1 = 1) => {
    setVisible(false)
    setTimeout(() => {
      setCurrentIndex((prev) => {
        const next = prev + direction
        if (next >= candidates.length) return 0
        if (next < 0) return candidates.length - 1
        return next
      })
      setVisible(true)
    }, FADE_OUT_MS)
  }, [candidates.length])

  // Auto-rotation (desktop only)
  useEffect(() => {
    if (!canRotate) return
    // Disable on touch devices
    const isTouchDevice = "ontouchstart" in window
    if (isTouchDevice) return

    intervalRef.current = setInterval(() => advance(1), ROTATION_INTERVAL)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [canRotate, advance])

  // Swipe support (mobile)
  function handleTouchStart(e: React.TouchEvent) {
    touchStartX.current = e.touches[0].clientX
  }

  function handleTouchEnd(e: React.TouchEvent) {
    if (!canRotate) return
    const diff = e.changedTouches[0].clientX - touchStartX.current
    if (Math.abs(diff) > 50) {
      advance(diff < 0 ? 1 : -1)
    }
  }

  if (!data) return null

  return (
    <div
      className="w-full max-w-sm"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Header */}
      <div className="flex items-baseline justify-between mb-3 px-1">
        <MicroMetadata text="Live Engine Output — Today" />
        <MicroMetadata text={`Updated ${formatTimestamp(data.scored_at)} · Engine ${ENGINE_VERSION}`} />
      </div>

      {/* Card */}
      <div
        className="terminal-card p-6 md:p-8 border border-accent/20"
        style={{
          opacity: visible ? 1 : 0,
          transition: `opacity ${visible ? FADE_IN_MS : FADE_OUT_MS}ms cubic-bezier(0.4, 0, 0.2, 1)`,
        }}
      >
        {/* Ticker + Sector */}
        <div className="flex items-baseline justify-between mb-5">
          <div>
            <span className="font-mono text-lg font-semibold text-text-primary">{data.ticker}</span>
            <span className="ml-2 text-xs text-text-secondary">{data.name}</span>
          </div>
          <span className="text-[10px] uppercase tracking-widest text-text-tertiary px-2 py-0.5 rounded border border-border-subtle">
            {data.sector}
          </span>
        </div>

        {/* Prices */}
        <div className="grid grid-cols-2 gap-4 mb-5">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">Current</p>
            <p className="font-mono text-xl text-text-primary">{formatPrice(data.actual_price)}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">Target</p>
            <p className="font-mono text-xl text-accent">{formatPrice(data.buy_price)}</p>
          </div>
        </div>

        {/* Margin of Safety */}
        <div className="mb-5">
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">Margin of Safety</p>
          <p className="font-mono text-lg text-accent">{formatMoS(data.margin_of_safety)}</p>
        </div>

        {/* Conviction Score — largest element */}
        <div className="mb-6 text-center py-4 border-y border-border-subtle">
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-2">Conviction Score</p>
          <p className="font-mono text-5xl font-bold text-text-primary">{data.composite_percentile}</p>
        </div>

        {/* 5 Factor bars */}
        <div className="space-y-2.5 mb-5">
          <FactorBar label="Valuation" value={data.value_percentile} />
          <FactorBar label="Quality" value={data.quality_percentile} />
          <FactorBar label="Momentum" value={data.momentum_percentile} />
          <FactorBar label="Sentiment" value={data.sentiment_percentile} />
          <FactorBar label="Growth" value={data.growth_percentile} />
        </div>

        {/* Bottom metadata */}
        <div className="flex items-center justify-between pt-3 border-t border-border-subtle">
          <MicroMetadata text={`Universe: ${universeSize?.toLocaleString() ?? "—"}`} />
          <MicroMetadata text={`Eligible: ${eligibleCount?.toLocaleString() ?? "—"}`} />
          <MicroMetadata text={`Filters: ${data.filters_passed}/${data.filters_total}`} />
        </div>
      </div>

      {/* Dot indicators (mobile swipe) */}
      {canRotate && (
        <div className="flex justify-center gap-2 mt-3 md:hidden">
          {candidates.map((_, i) => (
            <div
              key={i}
              className={`w-1.5 h-1.5 rounded-full transition-colors duration-200 ${
                i === currentIndex ? "bg-accent" : "bg-text-tertiary/30"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

**Step 4: Run test**

Run: `npx --prefix web vitest run web/src/components/landing/__tests__/hero-candidate-card.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/hero-candidate-card.tsx web/src/components/landing/__tests__/hero-candidate-card.test.tsx
git commit -m "feat(web): add HeroCandidateCard with rotation and swipe"
```

---

## Task 6: Hero Section

**Files:**
- Create: `web/src/components/landing/hero-section.tsx`
- Test: `web/src/components/landing/__tests__/hero-section.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/hero-section.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))

vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { HeroSection } from "../hero-section"
import type { HomepageData } from "../types"

describe("HeroSection", () => {
  it("renders headline words", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("Conviction.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()
  })

  it("renders subheadline", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText(/deterministic capital allocation/i)).toBeInTheDocument()
  })

  it("renders primary CTA to dashboard", () => {
    render(<HeroSection data={null} />)
    const link = screen.getByRole("link", { name: /open the dashboard/i })
    expect(link).toHaveAttribute("href", "/dashboard")
  })

  it("renders secondary CTA to methodology", () => {
    render(<HeroSection data={null} />)
    const link = screen.getByRole("link", { name: /see the methodology/i })
    expect(link).toHaveAttribute("href", "/methodology")
  })

  it("shows fallback candidate card when no API data", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })
})
```

**Step 2: Run test — expect FAIL**

Run: `npx --prefix web vitest run web/src/components/landing/__tests__/hero-section.test.tsx`

**Step 3: Implement**

Create `web/src/components/landing/hero-section.tsx`:
```typescript
"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import { HeroCandidateCard } from "./hero-candidate-card"
import { FALLBACK_CANDIDATES, DEFAULT_UNIVERSE_SIZE, DEFAULT_ELIGIBLE_COUNT } from "./candidate-data"
import type { HomepageData } from "./types"

interface HeroSectionProps {
  data: HomepageData | null
}

export function HeroSection({ data }: HeroSectionProps) {
  const sectionRef = useRef<HTMLDivElement>(null)
  const headlineRef = useRef<HTMLHeadingElement>(null)
  const subtextRef = useRef<HTMLParagraphElement>(null)
  const ctaRef = useRef<HTMLDivElement>(null)

  const candidates = data?.candidates?.length ? data.candidates : FALLBACK_CANDIDATES
  const universeSize = data?.universe_size ?? DEFAULT_UNIVERSE_SIZE
  const eligibleCount = data?.eligible_count ?? DEFAULT_ELIGIBLE_COUNT

  useEffect(() => {
    let gsap: any

    async function animate() {
      try {
        gsap = (await import("gsap")).default
        const elements = [headlineRef.current, subtextRef.current, ctaRef.current].filter(Boolean)

        gsap.set(elements, { opacity: 0, y: 20 })
        elements.forEach((el: any, i: number) => {
          gsap.to(el, {
            opacity: 1,
            y: 0,
            duration: 0.5,
            delay: i * 0.15,
            ease: "power2.out",
          })
        })
      } catch {
        // GSAP not available — show content immediately
        const elements = [headlineRef.current, subtextRef.current, ctaRef.current]
        elements.forEach((el) => {
          if (el) el.style.opacity = "1"
        })
      }
    }

    animate()
  }, [])

  return (
    <section
      ref={sectionRef}
      id="hero"
      className="min-h-screen flex items-center justify-center px-6 bg-bg-primary"
    >
      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-[55%_45%] gap-12 lg:gap-16 items-center">
        {/* Left: headline + CTAs */}
        <div>
          <h1
            ref={headlineRef}
            className="font-display text-5xl md:text-7xl lg:text-[80px] leading-[0.95] tracking-[-0.04em] text-text-primary mb-6"
          >
            <span className="inline-block mr-4">Conviction.</span>
            <span className="inline-block">Engineered.</span>
          </h1>

          <p
            ref={subtextRef}
            className="text-lg text-text-secondary max-w-[480px] mb-10 leading-relaxed"
          >
            A deterministic capital allocation system that replaces narrative with structure.
          </p>

          <div ref={ctaRef} className="flex items-center gap-6">
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center h-12 px-8 rounded-lg bg-accent text-white text-sm font-medium tracking-wide transition-colors duration-200 hover:bg-accent-hover"
            >
              Open the Dashboard
            </Link>
            <Link
              href="/methodology"
              className="text-sm font-medium text-text-secondary underline underline-offset-4 decoration-border-primary hover:text-text-primary transition-colors duration-200"
            >
              See the Methodology
            </Link>
          </div>
        </div>

        {/* Right: rotating candidate card */}
        <div className="flex justify-center lg:justify-end">
          <HeroCandidateCard
            candidates={candidates}
            universeSize={universeSize}
            eligibleCount={eligibleCount}
          />
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test**

Run: `npx --prefix web vitest run web/src/components/landing/__tests__/hero-section.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/hero-section.tsx web/src/components/landing/__tests__/hero-section.test.tsx
git commit -m "feat(web): add HeroSection with GSAP entrance and rotating card"
```

---

## Task 7: Problem Section

**Files:**
- Create: `web/src/components/landing/problem-section.tsx`
- Test: `web/src/components/landing/__tests__/problem-section.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/problem-section.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { ProblemSection } from "../problem-section"

describe("ProblemSection", () => {
  it("renders headline", () => {
    render(<ProblemSection />)
    expect(screen.getByText(/most investors react/i)).toBeInTheDocument()
  })

  it("renders all 4 bullet points", () => {
    render(<ProblemSection />)
    expect(screen.getByText(/no filtering discipline/i)).toBeInTheDocument()
    expect(screen.getByText(/no factor weighting memory/i)).toBeInTheDocument()
    expect(screen.getByText(/no sector normalization/i)).toBeInTheDocument()
    expect(screen.getByText(/no portfolio-level correlation awareness/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement**

Create `web/src/components/landing/problem-section.tsx`:
```typescript
"use client"

import { useEffect, useRef } from "react"

const bullets = [
  "No filtering discipline",
  "No factor weighting memory",
  "No sector normalization",
  "No portfolio-level correlation awareness",
]

export function ProblemSection() {
  const headlineRef = useRef<HTMLHeadingElement>(null)
  const listRef = useRef<HTMLUListElement>(null)

  useEffect(() => {
    async function animate() {
      try {
        const gsap = (await import("gsap")).default
        const ScrollTrigger = (await import("gsap/ScrollTrigger")).default
        gsap.registerPlugin(ScrollTrigger)

        if (headlineRef.current) {
          gsap.fromTo(
            headlineRef.current,
            { opacity: 0, y: 20 },
            {
              opacity: 1,
              y: 0,
              duration: 0.3,
              ease: "power2.out",
              scrollTrigger: { trigger: headlineRef.current, start: "top 80%" },
            },
          )
        }

        if (listRef.current) {
          const items = listRef.current.querySelectorAll("li")
          items.forEach((item, i) => {
            gsap.fromTo(
              item,
              { opacity: 0, y: 15 },
              {
                opacity: 1,
                y: 0,
                duration: 0.3,
                delay: i * 0.1,
                ease: "power2.out",
                scrollTrigger: { trigger: item, start: "top 85%" },
              },
            )
          })
        }
      } catch {
        // Graceful degradation
      }
    }
    animate()
  }, [])

  return (
    <section id="problem" className="pt-[120px] pb-20 px-6 border-b border-border-subtle">
      <div className="max-w-3xl mx-auto">
        <h2 ref={headlineRef} className="font-display text-4xl md:text-[36px] text-text-primary mb-12 text-center">
          Most investors react. Few operate with structure.
        </h2>

        <ul ref={listRef} className="space-y-6">
          {bullets.map((bullet) => (
            <li key={bullet} className="text-base text-text-secondary flex items-start gap-3">
              <span className="text-text-tertiary shrink-0">&mdash;</span>
              {bullet}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
git add web/src/components/landing/problem-section.tsx web/src/components/landing/__tests__/problem-section.test.tsx
git commit -m "feat(web): add ProblemSection with GSAP scroll reveals"
```

---

## Task 8: Pipeline Chips (Standalone Section)

**Files:**
- Create: `web/src/components/landing/pipeline-chips.tsx`
- Test: `web/src/components/landing/__tests__/pipeline-chips.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/pipeline-chips.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { PipelineChips } from "../pipeline-chips"

describe("PipelineChips", () => {
  it("renders all 6 pipeline stages", () => {
    render(<PipelineChips activeStage={0} />)
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("FILTER")).toBeInTheDocument()
    expect(screen.getByText("FACTOR MODEL")).toBeInTheDocument()
    expect(screen.getByText("NORMALIZE")).toBeInTheDocument()
    expect(screen.getByText("SCORE")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()
  })

  it("renders Factor Model version metadata", () => {
    render(<PipelineChips activeStage={0} />)
    expect(screen.getByText(/factor model v2\.1/i)).toBeInTheDocument()
  })

  it("marks stages as active up to activeStage", () => {
    render(<PipelineChips activeStage={3} />)
    const stages = screen.getAllByTestId("pipeline-stage")
    // First 4 stages (0-3) should have active styling
    expect(stages[0]).toHaveAttribute("data-active", "true")
    expect(stages[3]).toHaveAttribute("data-active", "true")
    expect(stages[4]).toHaveAttribute("data-active", "false")
  })
})
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement**

Create `web/src/components/landing/pipeline-chips.tsx`:
```typescript
"use client"

import { MicroMetadata } from "./micro-metadata"
import { FACTOR_MODEL_VERSION } from "./candidate-data"

const STAGES = ["DATA", "FILTER", "FACTOR MODEL", "NORMALIZE", "SCORE", "PORTFOLIO"]

interface PipelineChipsProps {
  activeStage: number
}

export function PipelineChips({ activeStage }: PipelineChipsProps) {
  return (
    <section id="pipeline" className="py-8">
      <div className="w-full overflow-x-auto">
        <div className="flex items-center justify-center gap-1 md:gap-2 min-w-[600px] px-4">
          {STAGES.map((stage, i) => {
            const isActive = i <= activeStage
            return (
              <div key={stage} className="flex items-center">
                <div
                  data-testid="pipeline-stage"
                  data-active={isActive ? "true" : "false"}
                  className={`relative px-3 py-2 font-mono text-[10px] md:text-xs tracking-[0.15em] transition-all duration-250 ${
                    isActive ? "text-accent" : "text-text-tertiary"
                  }`}
                >
                  {stage}
                  {/* Underline bar */}
                  <div
                    className={`absolute bottom-0 left-0 right-0 h-0.5 transition-all duration-250 ${
                      isActive
                        ? "bg-accent shadow-[0_0_8px_rgba(26,122,90,0.3)]"
                        : "bg-transparent"
                    }`}
                  />
                </div>
                {i < STAGES.length - 1 && (
                  <span
                    className={`mx-1 text-xs transition-colors duration-250 ${
                      i < activeStage ? "text-accent/50" : "text-text-tertiary/30"
                    }`}
                  >
                    &rarr;
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </div>
      <div className="text-center mt-3">
        <MicroMetadata text={`Factor Model ${FACTOR_MODEL_VERSION}`} />
      </div>
    </section>
  )
}
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
git add web/src/components/landing/pipeline-chips.tsx web/src/components/landing/__tests__/pipeline-chips.test.tsx
git commit -m "feat(web): add standalone PipelineChips section with underline highlighting"
```

---

## Task 9: Engine Card + Engine Section (Counter-Scroll)

**Files:**
- Create: `web/src/components/landing/engine-card.tsx`
- Create: `web/src/components/landing/engine-section.tsx`
- Test: `web/src/components/landing/__tests__/engine-section.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/engine-section.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { EngineSection } from "../engine-section"

describe("EngineSection", () => {
  it("renders top row card titles", () => {
    render(<EngineSection onStageChange={() => {}} />)
    expect(screen.getAllByText("Raw Market Signal").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Elimination Filters").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Liquidity Thresholding").length).toBeGreaterThanOrEqual(1)
  })

  it("renders bottom row card titles", () => {
    render(<EngineSection onStageChange={() => {}} />)
    expect(screen.getAllByText("Multi-Factor Ranking").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Conviction Score Synthesis").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Portfolio Correlation Mapping").length).toBeGreaterThanOrEqual(1)
  })
})
```

**Step 2: Run test — expect FAIL**

**Step 3: Create engine-card.tsx**

Create `web/src/components/landing/engine-card.tsx`:
```typescript
interface EngineCardProps {
  title: string
  subtitle: string
  description: string
}

export function EngineCard({ title, subtitle, description }: EngineCardProps) {
  return (
    <div className="w-[320px] flex-shrink-0 terminal-card p-6 md:p-8 transition-opacity duration-200">
      <p className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-3">{subtitle}</p>
      <h3 className="font-display text-2xl md:text-3xl leading-tight text-text-primary mb-3">{title}</h3>
      <p className="text-sm text-text-secondary leading-relaxed">{description}</p>
    </div>
  )
}
```

**Step 4: Create engine-section.tsx**

Create `web/src/components/landing/engine-section.tsx`:
```typescript
"use client"

import { useRef, useEffect } from "react"
import { EngineCard } from "./engine-card"

const topRowCards = [
  { title: "Raw Market Signal", subtitle: "Input", description: "Earnings transcripts, SEC filings, price targets, institutional flows — hundreds of data points per ticker, gathered and normalized." },
  { title: "Data Integrity + Normalization", subtitle: "Input", description: "Standardize across reporting periods, currencies, and accounting methods. Clean data is the foundation of deterministic scoring." },
  { title: "Elimination Filters", subtitle: "Gating", description: "Penny stocks, delistings, insufficient data — fail-fast filters eliminate noise before scoring begins. Only investable assets proceed." },
  { title: "Survivorship Bias Control", subtitle: "Gating", description: "Delisted and acquired companies remain in historical datasets. No retroactive cleaning of failures from the record." },
  { title: "Liquidity Thresholding", subtitle: "Gating", description: "Minimum volume and market cap requirements ensure every scored asset is actually tradeable at institutional scale." },
]

const bottomRowCards = [
  { title: "Multi-Factor Ranking", subtitle: "Scoring", description: "Five factors — valuation, quality, momentum, growth, sentiment — each scored independently against sector peers." },
  { title: "Percentile Normalization", subtitle: "Scoring", description: "Raw scores converted to percentile ranks (0-100) within GICS sector. Cross-factor comparison becomes meaningful." },
  { title: "Conviction Score Synthesis", subtitle: "Output", description: "Weighted combination of factor percentiles produces a single composite conviction score. Growth stage adjusts weights automatically." },
  { title: "Sector-Neutral Construction", subtitle: "Output", description: "Rank within sector first, then combine. A 60th-percentile bank is compared to banks, not tech stocks." },
  { title: "Portfolio Correlation Mapping", subtitle: "Output", description: "Identify correlated positions across your portfolio. Diversification measured, not assumed." },
]

interface EngineSectionProps {
  onStageChange: (stage: number) => void
}

export function EngineSection({ onStageChange }: EngineSectionProps) {
  const sectionRef = useRef<HTMLDivElement>(null)
  const topRowRef = useRef<HTMLDivElement>(null)
  const bottomRowRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let ScrollTriggerModule: any

    async function initGSAP() {
      try {
        const gsapModule = (await import("gsap")).default
        ScrollTriggerModule = (await import("gsap/ScrollTrigger")).default
        gsapModule.registerPlugin(ScrollTriggerModule)

        if (!sectionRef.current || !topRowRef.current || !bottomRowRef.current) return

        // Top row scrolls left
        gsapModule.to(topRowRef.current, {
          x: "-30%",
          ease: "none",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top bottom",
            end: "bottom top",
            scrub: 1,
          },
        })

        // Bottom row scrolls right
        gsapModule.to(bottomRowRef.current, {
          x: "30%",
          ease: "none",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top bottom",
            end: "bottom top",
            scrub: 1,
          },
        })

        // Pipeline stage highlighting — complete by 75-80%
        ScrollTriggerModule.create({
          trigger: sectionRef.current,
          start: "top center",
          end: "75% center",
          onUpdate: (self: any) => {
            const stage = Math.min(5, Math.floor(self.progress * 7.5))
            onStageChange(stage)
          },
        })
      } catch {
        // Graceful degradation
      }
    }

    initGSAP()

    return () => {
      if (ScrollTriggerModule) {
        ScrollTriggerModule.getAll?.().forEach((t: any) => t.kill())
      }
    }
  }, [onStageChange])

  return (
    <section ref={sectionRef} id="engine" className="relative py-24 overflow-hidden">
      {/* Desktop: counter-scrolling card rows */}
      <div className="hidden md:block space-y-8">
        {/* Connection lines hint */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-0 right-0 h-px bg-accent/[0.08] border-dashed" />
        </div>

        <div
          ref={topRowRef}
          className="flex gap-6 pl-[10%]"
          style={{ transform: "translateX(30%)" }}
        >
          {topRowCards.map((card) => (
            <EngineCard key={card.title} {...card} />
          ))}
        </div>

        <div
          ref={bottomRowRef}
          className="flex gap-6 pl-[10%]"
          style={{ transform: "translateX(-30%)" }}
        >
          {bottomRowCards.map((card) => (
            <EngineCard key={card.title} {...card} />
          ))}
        </div>
      </div>

      {/* Mobile: vertical interleaved stack */}
      <div className="md:hidden flex flex-col items-center gap-4 px-6 max-w-[360px] mx-auto">
        {topRowCards.map((card, i) => (
          <div key={card.title} className="w-full space-y-4">
            <EngineCard {...card} />
            {bottomRowCards[i] && <EngineCard {...bottomRowCards[i]} />}
          </div>
        ))}
      </div>
    </section>
  )
}
```

**Step 5: Run test — expect PASS**

**Step 6: Commit**

```bash
git add web/src/components/landing/engine-card.tsx web/src/components/landing/engine-section.tsx web/src/components/landing/__tests__/engine-section.test.tsx
git commit -m "feat(web): add EngineSection with GSAP counter-scroll and stage callback"
```

---

## Task 10: Proof Section with Recharts

**Files:**
- Create: `web/src/components/landing/proof-section.tsx`
- Create: `web/src/components/landing/proof-factor-bars.tsx`
- Create: `web/src/components/landing/proof-tilt-chart.tsx`
- Create: `web/src/components/landing/proof-heatmap.tsx`
- Create: `web/src/components/landing/proof-historical-chart.tsx`
- Test: `web/src/components/landing/__tests__/proof-section.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/proof-section.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Line: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  Cell: () => null,
}))

import { ProofSection } from "../proof-section"

describe("ProofSection", () => {
  it("renders headline", () => {
    render(<ProofSection />)
    expect(screen.getByText(/structure creates measurable advantage/i)).toBeInTheDocument()
  })

  it("renders all 4 proof card titles", () => {
    render(<ProofSection />)
    expect(screen.getByText("Factor Transparency")).toBeInTheDocument()
    expect(screen.getByText("Growth vs Value Tilt")).toBeInTheDocument()
    expect(screen.getByText("Correlation Heatmap")).toBeInTheDocument()
    expect(screen.getByText("Historical Application")).toBeInTheDocument()
  })

  it("renders sector-neutral metadata", () => {
    render(<ProofSection />)
    expect(screen.getByText(/sector-neutral by design/i)).toBeInTheDocument()
  })

  it("renders factor bar labels", () => {
    render(<ProofSection />)
    expect(screen.getByText("Valuation")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
    expect(screen.getByText("Sentiment")).toBeInTheDocument()
    expect(screen.getByText("Growth")).toBeInTheDocument()
  })
})
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement sub-components**

Create `web/src/components/landing/proof-factor-bars.tsx`:
```typescript
const FACTORS = [
  { label: "Valuation", value: 62 },
  { label: "Quality", value: 85 },
  { label: "Momentum", value: 71 },
  { label: "Sentiment", value: 68 },
  { label: "Growth", value: 74 },
]

export function ProofFactorBars() {
  return (
    <div className="space-y-3">
      {FACTORS.map(({ label, value }) => (
        <div key={label} className="flex items-center gap-3">
          <span className="text-xs text-text-tertiary w-20">{label}</span>
          <div className="flex-1 h-2 bg-bg-subtle rounded-full overflow-hidden relative">
            {/* Grid guides */}
            {[25, 50, 75].map((mark) => (
              <div key={mark} className="absolute top-0 bottom-0 w-px bg-border-subtle" style={{ left: `${mark}%` }} />
            ))}
            <div
              className="h-full bg-accent rounded-full relative z-10"
              style={{ width: `${value}%` }}
            />
          </div>
          <span className="font-mono text-xs text-text-primary w-8 text-right">{value}</span>
        </div>
      ))}
    </div>
  )
}
```

Create `web/src/components/landing/proof-tilt-chart.tsx`:
```typescript
"use client"

import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from "recharts"

const data = [
  { name: "Growth", weight: 35 },
  { name: "Value", weight: 25 },
]

export function ProofTiltChart() {
  return (
    <div className="h-24">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 20 }}>
          <XAxis type="number" domain={[0, 50]} hide />
          <YAxis
            type="category"
            dataKey="name"
            width={60}
            tick={{ fontSize: 11, fill: "var(--color-text-tertiary)" }}
            axisLine={false}
            tickLine={false}
          />
          <Bar dataKey="weight" radius={[0, 4, 4, 0]} barSize={16}>
            {data.map((_, i) => (
              <Cell key={i} fill={i === 0 ? "var(--color-accent)" : "color-mix(in srgb, var(--color-accent), transparent 40%)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-text-tertiary mt-2">
        Factor weights adapt by growth stage.
      </p>
    </div>
  )
}
```

Create `web/src/components/landing/proof-heatmap.tsx`:
```typescript
const SIZE = 5
const LABELS = ["AAPL", "MSFT", "JNJ", "COST", "V"]
const HEATMAP_DATA: number[][] = [
  [1.0, 0.72, 0.15, 0.28, 0.45],
  [0.72, 1.0, 0.08, 0.31, 0.52],
  [0.15, 0.08, 1.0, 0.41, 0.12],
  [0.28, 0.31, 0.41, 1.0, 0.22],
  [0.45, 0.52, 0.12, 0.22, 1.0],
]

// Key cells to annotate (row, col)
const ANNOTATED: [number, number][] = [[0, 1], [2, 3], [1, 4]]

function cellColor(value: number): string {
  if (value >= 0.6) return "var(--color-accent)"
  if (value >= 0.3) return "var(--color-text-tertiary)"
  return "var(--color-danger)"
}

export function ProofHeatmap() {
  return (
    <div>
      {/* Column labels */}
      <div className="grid gap-px ml-8" style={{ gridTemplateColumns: `repeat(${SIZE}, 1fr)` }}>
        {LABELS.map((l) => (
          <span key={l} className="text-[9px] text-text-tertiary text-center font-mono">{l}</span>
        ))}
      </div>

      {/* Grid */}
      <div className="flex">
        {/* Row labels */}
        <div className="flex flex-col justify-around w-8 shrink-0">
          {LABELS.map((l) => (
            <span key={l} className="text-[9px] text-text-tertiary font-mono">{l}</span>
          ))}
        </div>

        <div
          className="flex-1 grid gap-px"
          style={{ gridTemplateColumns: `repeat(${SIZE}, 1fr)` }}
        >
          {HEATMAP_DATA.flatMap((row, r) =>
            row.map((value, c) => {
              const isAnnotated = ANNOTATED.some(([ar, ac]) => ar === r && ac === c)
              return (
                <div
                  key={`${r}-${c}`}
                  className="aspect-square flex items-center justify-center border border-border-subtle/50 relative"
                  style={{ backgroundColor: `color-mix(in srgb, ${cellColor(value)}, transparent 70%)` }}
                >
                  {isAnnotated && (
                    <span className="font-mono text-[9px] text-text-primary">{value.toFixed(2)}</span>
                  )}
                </div>
              )
            }),
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between mt-3 text-[9px] text-text-tertiary">
        <div className="flex items-center gap-1">
          <div className="w-3 h-2 rounded-sm" style={{ backgroundColor: "var(--color-danger)" }} />
          <span>-1.0</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-2 rounded-sm" style={{ backgroundColor: "var(--color-text-tertiary)" }} />
          <span>0.0</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-2 rounded-sm" style={{ backgroundColor: "var(--color-accent)" }} />
          <span>+1.0</span>
        </div>
      </div>
    </div>
  )
}
```

Create `web/src/components/landing/proof-historical-chart.tsx`:
```typescript
"use client"

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"

const data = [
  { month: "Jan", portfolio: 2.1, benchmark: 1.4 },
  { month: "Feb", portfolio: 3.8, benchmark: 2.1 },
  { month: "Mar", portfolio: 1.2, benchmark: -0.3 },
  { month: "Apr", portfolio: 5.4, benchmark: 3.2 },
  { month: "May", portfolio: 7.1, benchmark: 4.8 },
  { month: "Jun", portfolio: 6.3, benchmark: 5.1 },
  { month: "Jul", portfolio: 9.2, benchmark: 6.4 },
  { month: "Aug", portfolio: 8.5, benchmark: 5.9 },
  { month: "Sep", portfolio: 11.3, benchmark: 7.2 },
  { month: "Oct", portfolio: 10.1, benchmark: 6.8 },
  { month: "Nov", portfolio: 13.5, benchmark: 8.4 },
  { month: "Dec", portfolio: 15.2, benchmark: 9.1 },
]

export function ProofHistoricalChart() {
  return (
    <div>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
            <CartesianGrid
              strokeDasharray="4 4"
              stroke="var(--color-border-subtle)"
              strokeOpacity={0.5}
            />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 9, fill: "var(--color-text-tertiary)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 9, fill: "var(--color-text-tertiary)" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `${v}%`}
            />
            <ReferenceLine y={0} stroke="var(--color-text-tertiary)" strokeDasharray="2 2" strokeOpacity={0.5} />
            <Line
              type="monotone"
              dataKey="portfolio"
              stroke="var(--color-accent)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="benchmark"
              stroke="var(--color-text-tertiary)"
              strokeWidth={1}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center gap-4 mt-2 text-[9px] text-text-tertiary">
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5 bg-accent" />
          <span>Portfolio</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-0.5 bg-text-tertiary" />
          <span>Benchmark</span>
        </div>
      </div>
      <p className="text-[10px] text-text-tertiary mt-2 italic">
        Past performance is not indicative of future results.
      </p>
    </div>
  )
}
```

**Step 4: Create proof-section.tsx**

Create `web/src/components/landing/proof-section.tsx`:
```typescript
"use client"

import { useEffect, useRef } from "react"
import { MicroMetadata } from "./micro-metadata"
import { ProofFactorBars } from "./proof-factor-bars"
import { ProofTiltChart } from "./proof-tilt-chart"
import { ProofHeatmap } from "./proof-heatmap"
import { ProofHistoricalChart } from "./proof-historical-chart"

function ProofCard({ title, children }: { title: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    async function animate() {
      try {
        const gsap = (await import("gsap")).default
        const ScrollTrigger = (await import("gsap/ScrollTrigger")).default
        gsap.registerPlugin(ScrollTrigger)

        if (ref.current) {
          gsap.fromTo(
            ref.current,
            { opacity: 0, y: 20 },
            {
              opacity: 1,
              y: 0,
              duration: 0.3,
              ease: "power2.out",
              scrollTrigger: { trigger: ref.current, start: "top 85%" },
            },
          )
        }
      } catch {}
    }
    animate()
  }, [])

  return (
    <div ref={ref} className="terminal-card p-6">
      <p className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">{title}</p>
      {children}
    </div>
  )
}

export function ProofSection() {
  return (
    <section id="proof" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="font-display text-4xl md:text-[36px] text-text-primary mb-3">
            Structure creates measurable advantage.
          </h2>
          <MicroMetadata text="Sector-neutral by design" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ProofCard title="Factor Transparency">
            <ProofFactorBars />
          </ProofCard>

          <ProofCard title="Growth vs Value Tilt">
            <ProofTiltChart />
          </ProofCard>

          <ProofCard title="Correlation Heatmap">
            <ProofHeatmap />
          </ProofCard>

          <ProofCard title="Historical Application">
            <ProofHistoricalChart />
          </ProofCard>
        </div>
      </div>
    </section>
  )
}
```

**Step 5: Run test — expect PASS**

**Step 6: Commit**

```bash
git add web/src/components/landing/proof-section.tsx web/src/components/landing/proof-factor-bars.tsx web/src/components/landing/proof-tilt-chart.tsx web/src/components/landing/proof-heatmap.tsx web/src/components/landing/proof-historical-chart.tsx web/src/components/landing/__tests__/proof-section.test.tsx
git commit -m "feat(web): add ProofSection with Recharts charts and CSS factor bars"
```

---

## Task 11: Positioning Section

**Files:**
- Create: `web/src/components/landing/positioning-section.tsx`
- Test: `web/src/components/landing/__tests__/positioning-section.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/positioning-section.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { PositioningSection } from "../positioning-section"

describe("PositioningSection", () => {
  it("renders headline", () => {
    render(<PositioningSection />)
    expect(screen.getByText(/disciplined capital allocators/i)).toBeInTheDocument()
  })

  it("renders Not for items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Narrative traders")).toBeInTheDocument()
    expect(screen.getByText("Signal chasers")).toBeInTheDocument()
    expect(screen.getByText("Emotion-driven decisions")).toBeInTheDocument()
  })

  it("renders For items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Long-horizon allocators")).toBeInTheDocument()
    expect(screen.getByText("Portfolio operators")).toBeInTheDocument()
    expect(screen.getByText("Structured decision-makers")).toBeInTheDocument()
  })
})
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement**

Create `web/src/components/landing/positioning-section.tsx`:
```typescript
"use client"

import { useEffect, useRef } from "react"

const notFor = ["Narrative traders", "Signal chasers", "Emotion-driven decisions"]
const forItems = ["Long-horizon allocators", "Portfolio operators", "Structured decision-makers"]

export function PositioningSection() {
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    async function animate() {
      try {
        const gsap = (await import("gsap")).default
        const ScrollTrigger = (await import("gsap/ScrollTrigger")).default
        gsap.registerPlugin(ScrollTrigger)

        if (contentRef.current) {
          gsap.fromTo(
            contentRef.current,
            { opacity: 0 },
            {
              opacity: 1,
              duration: 0.3,
              ease: "power2.out",
              scrollTrigger: { trigger: contentRef.current, start: "top 80%" },
            },
          )
        }
      } catch {}
    }
    animate()
  }, [])

  return (
    <section id="positioning" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <h2 className="font-display text-4xl md:text-[36px] text-text-primary mb-16 text-center">
          Built for disciplined capital allocators.
        </h2>

        <div ref={contentRef} className="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-16">
          <div className="md:border-r md:border-border-subtle md:pr-12">
            <p className="text-xs uppercase tracking-[0.2em] text-text-tertiary mb-6">Not for</p>
            <ul className="space-y-3">
              {notFor.map((item) => (
                <li key={item} className="text-sm text-text-tertiary">{item}</li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-accent mb-6">For</p>
            <ul className="space-y-3">
              {forItems.map((item) => (
                <li key={item} className="text-sm text-accent">{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
git add web/src/components/landing/positioning-section.tsx web/src/components/landing/__tests__/positioning-section.test.tsx
git commit -m "feat(web): add PositioningSection with for/not-for micro-columns"
```

---

## Task 12: Pricing Section

**Files:**
- Create: `web/src/components/landing/pricing-section.tsx`
- Create: `web/src/components/landing/pricing-tier-card.tsx`
- Test: `web/src/components/landing/__tests__/pricing-section.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/pricing-section.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { PricingSection } from "../pricing-section"

describe("PricingSection", () => {
  it("renders pre-headline", () => {
    render(<PricingSection />)
    expect(screen.getByText(/system scales with your responsibility/i)).toBeInTheDocument()
  })

  it("renders all 3 tiers", () => {
    render(<PricingSection />)
    expect(screen.getByText("Analyst")).toBeInTheDocument()
    expect(screen.getByText("Portfolio")).toBeInTheDocument()
    expect(screen.getByText("Institutional")).toBeInTheDocument()
  })

  it("renders Most Popular tag on Portfolio", () => {
    render(<PricingSection />)
    expect(screen.getByText("Most Popular")).toBeInTheDocument()
  })

  it("renders prices", () => {
    render(<PricingSection />)
    expect(screen.getByText("Free")).toBeInTheDocument()
    expect(screen.getByText("$29")).toBeInTheDocument()
    expect(screen.getByText("$79")).toBeInTheDocument()
  })
})
```

**Step 2: Run test — expect FAIL**

**Step 3: Create pricing-tier-card.tsx**

Create `web/src/components/landing/pricing-tier-card.tsx`:
```typescript
import Link from "next/link"

interface Tier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  highlighted: boolean
}

export function PricingTierCard({ tier }: { tier: Tier }) {
  return (
    <div className={tier.highlighted ? "-mt-2" : ""}>
      <div
        className={`terminal-card p-6 md:p-8 flex flex-col h-full ${
          tier.highlighted ? "border-accent/30" : ""
        }`}
        style={tier.highlighted ? { borderColor: "color-mix(in srgb, var(--color-accent), transparent 70%)" } : {}}
      >
        <div className="flex items-center gap-2 mb-3">
          <p className="text-xs uppercase tracking-[0.2em] text-text-tertiary">{tier.name}</p>
          {tier.highlighted && (
            <span className="text-[10px] text-accent bg-accent/10 px-2 py-0.5 rounded">Most Popular</span>
          )}
        </div>

        <div className="flex items-baseline gap-1 mb-2">
          <span className="font-display text-4xl text-text-primary">{tier.price}</span>
          {tier.period && <span className="text-sm text-text-tertiary">{tier.period}</span>}
        </div>

        <p className="text-sm text-text-secondary mb-6">{tier.description}</p>

        <ul className="space-y-2 mb-8 flex-1">
          {tier.features.map((f) => (
            <li key={f} className="text-sm text-text-secondary flex items-start gap-2">
              <span className="text-accent mt-0.5">&#x2713;</span>
              {f}
            </li>
          ))}
        </ul>

        <Link
          href="/onboarding"
          className={`inline-flex items-center justify-center h-11 rounded-lg text-sm font-medium transition-colors duration-200 ${
            tier.highlighted
              ? "bg-accent text-white hover:bg-accent-hover"
              : "border border-border-primary text-text-primary hover:bg-bg-subtle"
          }`}
        >
          {tier.highlighted ? "Start trial" : tier.price === "Free" ? "Start free" : "Get started"}
        </Link>
      </div>
    </div>
  )
}
```

**Step 4: Create pricing-section.tsx**

Create `web/src/components/landing/pricing-section.tsx`:
```typescript
"use client"

import { PricingTierCard } from "./pricing-tier-card"

const tiers = [
  {
    name: "Analyst",
    price: "Free",
    period: "",
    description: "Evaluate the engine with real positions.",
    features: [
      "3 ticker analyses per month",
      "Composite score + conviction level",
      "Top-level factor breakdown",
      "5-ticker watchlist",
    ],
    highlighted: false,
  },
  {
    name: "Portfolio",
    price: "$29",
    period: "/mo",
    description: "Full scoring for active portfolio management.",
    features: [
      "Unlimited ticker analysis",
      "Full 6-factor breakdown",
      "90-day score history",
      "25-ticker watchlist",
      "Conviction change alerts",
    ],
    highlighted: true,
  },
  {
    name: "Institutional",
    price: "$79",
    period: "/mo",
    description: "Portfolio-level conviction infrastructure.",
    features: [
      "Everything in Portfolio",
      "Unlimited score history",
      "Portfolio correlation analysis",
      "Sector rotation signals",
      "API access",
    ],
    highlighted: false,
  },
]

export function PricingSection() {
  return (
    <section id="pricing" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <p className="text-sm uppercase tracking-[0.15em] text-text-tertiary text-center mb-16">
          The system scales with your responsibility.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {tiers.map((tier) => (
            <PricingTierCard key={tier.name} tier={tier} />
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 5: Run test — expect PASS**

**Step 6: Commit**

```bash
git add web/src/components/landing/pricing-section.tsx web/src/components/landing/pricing-tier-card.tsx web/src/components/landing/__tests__/pricing-section.test.tsx
git commit -m "feat(web): add PricingSection with institutional flat cards and Most Popular tag"
```

---

## Task 13: Institutional Infrastructure Section (NEW)

**Files:**
- Create: `web/src/components/landing/infrastructure-section.tsx`
- Test: `web/src/components/landing/__tests__/infrastructure-section.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/infrastructure-section.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn(), set: vi.fn(), fromTo: vi.fn() },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))

import { InfrastructureSection } from "../infrastructure-section"

describe("InfrastructureSection", () => {
  it("renders headline", () => {
    render(<InfrastructureSection />)
    expect(screen.getByText(/institutional-grade infrastructure/i)).toBeInTheDocument()
  })

  it("renders subtext", () => {
    render(<InfrastructureSection />)
    expect(screen.getByText(/verified public data/i)).toBeInTheDocument()
  })

  it("renders all 5 bullet items", () => {
    render(<InfrastructureSection />)
    expect(screen.getByText(/sec filings/i)).toBeInTheDocument()
    expect(screen.getByText(/market data feeds/i)).toBeInTheDocument()
    expect(screen.getByText(/encrypted api key storage/i)).toBeInTheDocument()
    expect(screen.getByText(/deterministic.*scoring/i)).toBeInTheDocument()
    expect(screen.getByText(/no hidden heuristics/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement**

Create `web/src/components/landing/infrastructure-section.tsx`:
```typescript
"use client"

import { useEffect, useRef } from "react"

const items = [
  "SEC Filings + Earnings Transcripts",
  "Market Data Feeds (Daily Refresh)",
  "Encrypted API Key Storage",
  "Deterministic, Audit-Friendly Scoring",
  "No Hidden Heuristics",
]

export function InfrastructureSection() {
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    async function animate() {
      try {
        const gsap = (await import("gsap")).default
        const ScrollTrigger = (await import("gsap/ScrollTrigger")).default
        gsap.registerPlugin(ScrollTrigger)

        if (gridRef.current) {
          const children = gridRef.current.children
          Array.from(children).forEach((child, i) => {
            gsap.fromTo(
              child,
              { opacity: 0, y: 15 },
              {
                opacity: 1,
                y: 0,
                duration: 0.3,
                delay: i * 0.08,
                ease: "power2.out",
                scrollTrigger: { trigger: child, start: "top 85%" },
              },
            )
          })
        }
      } catch {}
    }
    animate()
  }, [])

  return (
    <section id="infrastructure" className="py-[100px] px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="font-display text-4xl md:text-[36px] text-text-primary mb-4 text-center">
          Institutional-Grade Infrastructure
        </h2>
        <p className="text-text-secondary text-center mb-16 max-w-2xl mx-auto">
          Built on verified public data and deterministic scoring architecture.
        </p>

        <div ref={gridRef} className="grid grid-cols-1 md:grid-cols-3 gap-y-6 gap-x-12">
          {items.map((item) => (
            <div key={item} className="flex items-start gap-3 py-4 border-b border-border-subtle">
              <span className="text-text-tertiary shrink-0">&mdash;</span>
              <span className="text-sm text-text-secondary">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
git add web/src/components/landing/infrastructure-section.tsx web/src/components/landing/__tests__/infrastructure-section.test.tsx
git commit -m "feat(web): add InfrastructureSection with bullet blocks and dividers"
```

---

## Task 14: Footer Section

**Files:**
- Create: `web/src/components/landing/footer-section.tsx`
- Test: `web/src/components/landing/__tests__/footer-section.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/footer-section.test.tsx`:
```typescript
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FooterSection } from "../footer-section"

describe("FooterSection", () => {
  it("renders all navigation links", () => {
    render(<FooterSection />)
    expect(screen.getByText("Support")).toBeInTheDocument()
    expect(screen.getByText("Methodology")).toBeInTheDocument()
    expect(screen.getByText("Security")).toBeInTheDocument()
    expect(screen.getByText("Legal")).toBeInTheDocument()
    expect(screen.getByText("Status")).toBeInTheDocument()
    expect(screen.getByText("API")).toBeInTheDocument()
    expect(screen.getByText("Contact")).toBeInTheDocument()
  })

  it("renders engine version", () => {
    render(<FooterSection />)
    expect(screen.getByText(/engine v1\.3\.2/i)).toBeInTheDocument()
  })

  it("renders copyright year", () => {
    render(<FooterSection />)
    expect(screen.getByText(/2026 margin invest/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement**

Create `web/src/components/landing/footer-section.tsx`:
```typescript
import Link from "next/link"
import { ENGINE_VERSION } from "./candidate-data"

const links = [
  { href: "/support", label: "Support" },
  { href: "/methodology", label: "Methodology" },
  { href: "/security", label: "Security" },
  { href: "/legal", label: "Legal" },
  { href: "/status", label: "Status" },
  { href: "/api", label: "API" },
  { href: "/support", label: "Contact" },
]

export function FooterSection() {
  return (
    <footer id="footer" className="border-t border-border-subtle py-12">
      <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center md:items-start justify-between gap-6">
        <nav className="flex flex-col md:flex-row flex-wrap gap-x-8 gap-y-3" aria-label="Footer">
          {links.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-200"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="text-right">
          <p className="font-mono text-xs text-text-tertiary">Engine {ENGINE_VERSION}</p>
          <p className="font-mono text-xs text-text-tertiary mt-1">
            &copy; {new Date().getFullYear()} Margin Invest
          </p>
        </div>
      </div>
    </footer>
  )
}
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
git add web/src/components/landing/footer-section.tsx web/src/components/landing/__tests__/footer-section.test.tsx
git commit -m "feat(web): add FooterSection with version and copyright"
```

---

## Task 15: Section Indicator (updated for 9 sections)

**Files:**
- Create: `web/src/components/landing/section-indicator.tsx`
- Test: `web/src/components/landing/__tests__/section-indicator.test.tsx`

**Step 1: Write the test**

Create `web/src/components/landing/__tests__/section-indicator.test.tsx`:
```typescript
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SectionIndicator } from "../section-indicator"

describe("SectionIndicator", () => {
  it("renders navigation dots for all major sections", () => {
    render(<SectionIndicator />)
    const nav = screen.getByRole("navigation", { name: /page sections/i })
    expect(nav).toBeInTheDocument()
    // 9 sections = 9 dots
    const buttons = nav.querySelectorAll("button")
    expect(buttons.length).toBe(9)
  })
})
```

**Step 2: Run test — expect FAIL**

**Step 3: Implement**

Create `web/src/components/landing/section-indicator.tsx`:
```typescript
"use client"

import { useEffect, useRef, useState } from "react"

const SECTIONS = [
  { id: "hero", label: "Hero" },
  { id: "problem", label: "Problem" },
  { id: "pipeline", label: "Pipeline" },
  { id: "engine", label: "Engine" },
  { id: "proof", label: "Proof" },
  { id: "positioning", label: "Positioning" },
  { id: "pricing", label: "Pricing" },
  { id: "infrastructure", label: "Infrastructure" },
  { id: "footer", label: "Footer" },
]

export function SectionIndicator() {
  const [activeIndex, setActiveIndex] = useState(0)
  const observerRef = useRef<IntersectionObserver | null>(null)

  useEffect(() => {
    const elements = SECTIONS.map(({ id }) => document.getElementById(id)).filter(Boolean) as HTMLElement[]
    if (elements.length === 0) return

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const index = SECTIONS.findIndex((s) => s.id === entry.target.id)
            if (index !== -1) setActiveIndex(index)
          }
        }
      },
      { threshold: 0.3 },
    )

    for (const el of elements) observerRef.current.observe(el)
    return () => observerRef.current?.disconnect()
  }, [])

  function handleNavigate(index: number) {
    const id = SECTIONS[index]?.id
    if (id) document.getElementById(id)?.scrollIntoView({ behavior: "smooth" })
  }

  return (
    <nav
      aria-label="Page sections"
      className="fixed right-6 top-1/2 -translate-y-1/2 z-50 hidden lg:flex flex-col gap-2"
    >
      {SECTIONS.map((section, i) => (
        <button
          key={section.id}
          aria-label={section.label}
          aria-current={i === activeIndex ? "step" : undefined}
          onClick={() => handleNavigate(i)}
          className={`w-1.5 h-1.5 rounded-full transition-all duration-200 ${
            i === activeIndex
              ? "bg-accent scale-150"
              : "bg-text-tertiary opacity-30 hover:opacity-60"
          }`}
        />
      ))}
    </nav>
  )
}
```

**Step 4: Run test — expect PASS**

**Step 5: Commit**

```bash
git add web/src/components/landing/section-indicator.tsx web/src/components/landing/__tests__/section-indicator.test.tsx
git commit -m "feat(web): add SectionIndicator for 9-section homepage"
```

---

## Task 16: Barrel exports

**Files:**
- Modify: `web/src/components/landing/index.ts`

**Step 1: Update index.ts**

Write `web/src/components/landing/index.ts`:
```typescript
export { HeroSection } from "./hero-section"
export { HeroCandidateCard } from "./hero-candidate-card"
export { ProblemSection } from "./problem-section"
export { PipelineChips } from "./pipeline-chips"
export { EngineSection } from "./engine-section"
export { EngineCard } from "./engine-card"
export { ProofSection } from "./proof-section"
export { PositioningSection } from "./positioning-section"
export { PricingSection } from "./pricing-section"
export { InfrastructureSection } from "./infrastructure-section"
export { FooterSection } from "./footer-section"
export { SectionIndicator } from "./section-indicator"
export { MicroMetadata } from "./micro-metadata"
```

**Step 2: Commit**

```bash
git add web/src/components/landing/index.ts
git commit -m "chore(web): update barrel exports for rebuilt landing components"
```

---

## Task 17: Assemble page.tsx (9-section homepage)

**Files:**
- Modify: `web/src/app/page.tsx`
- Test: `web/src/components/landing/__tests__/page-assembly.test.tsx`

**Step 1: Write the page assembly test**

Create `web/src/components/landing/__tests__/page-assembly.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/api/server", () => ({
  serverFetch: vi.fn().mockResolvedValue({ picks: [], last_updated: "", total_scored: 0, universe: null, watchlist: [], warnings: [] }),
}))
vi.mock("@/lib/auth", () => ({
  auth: vi.fn().mockResolvedValue(null),
}))
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}))
vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  LineChart: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div>{children}</div>,
  Line: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ReferenceLine: () => null,
  Cell: () => null,
}))

import Page from "../../../app/page"

describe("Landing page assembly", () => {
  it("renders all 9 sections", async () => {
    const jsx = await Page()
    render(jsx)

    // Hero
    expect(screen.getByText("Conviction.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()

    // Problem
    expect(screen.getByText(/most investors react/i)).toBeInTheDocument()

    // Pipeline
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()

    // Engine cards
    expect(screen.getAllByText("Raw Market Signal").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Portfolio Correlation Mapping").length).toBeGreaterThanOrEqual(1)

    // Proof
    expect(screen.getByText(/structure creates measurable advantage/i)).toBeInTheDocument()

    // Positioning
    expect(screen.getByText(/disciplined capital allocators/i)).toBeInTheDocument()

    // Pricing
    expect(screen.getByText("Analyst")).toBeInTheDocument()
    expect(screen.getByText("Institutional")).toBeInTheDocument()

    // Infrastructure (NEW)
    expect(screen.getByText(/institutional-grade infrastructure/i)).toBeInTheDocument()

    // Footer
    expect(screen.getByText(/engine v1\.3\.2/i)).toBeInTheDocument()
  })

  it("renders the navbar", async () => {
    const jsx = await Page()
    render(jsx)
    const nav = screen.getByRole("navigation", { name: "Main navigation" })
    expect(nav).toBeInTheDocument()
  })
})
```

**Step 2: Rewrite page.tsx**

Write `web/src/app/page.tsx`:
```typescript
import { Navbar } from "@/components/nav/navbar"
import { serverFetch } from "@/lib/api/server"
import { HomepageClient } from "@/components/landing/homepage-client"
import type { DashboardResponse } from "@/lib/api/types"
import type { HomepageData, CandidateCard } from "@/components/landing/types"

function toCandidateCard(pick: DashboardResponse["picks"][0]): CandidateCard {
  return {
    ticker: pick.ticker,
    name: pick.name,
    sector: pick.sector ?? "Unknown",
    actual_price: pick.actual_price ?? 0,
    buy_price: pick.buy_price ?? 0,
    margin_of_safety: pick.margin_of_safety ?? 0,
    composite_percentile: pick.composite_percentile,
    conviction_level: pick.conviction_level,
    quality_percentile: pick.quality_percentile,
    value_percentile: pick.value_percentile,
    momentum_percentile: pick.momentum_percentile,
    sentiment_percentile: pick.sentiment_percentile ?? 0,
    growth_percentile: pick.growth_percentile ?? 0,
    scored_at: pick.scored_at ?? new Date().toISOString(),
    filters_passed: 8,
    filters_total: 8,
  }
}

async function getHomepageData(): Promise<HomepageData | null> {
  try {
    const data = await serverFetch<DashboardResponse>("/api/v1/dashboard")
    return {
      candidates: data.picks.slice(0, 5).map(toCandidateCard),
      last_updated: data.last_updated,
      universe_size: data.universe?.size ?? 0,
      eligible_count: data.total_scored,
      total_scored: data.total_scored,
    }
  } catch {
    return null
  }
}

export default async function Home() {
  const data = await getHomepageData()

  return (
    <main>
      <Navbar />
      <HomepageClient data={data} />
    </main>
  )
}
```

**Step 3: Create HomepageClient wrapper**

Create `web/src/components/landing/homepage-client.tsx`:
```typescript
"use client"

import { useState, useCallback } from "react"
import { HeroSection } from "./hero-section"
import { ProblemSection } from "./problem-section"
import { PipelineChips } from "./pipeline-chips"
import { EngineSection } from "./engine-section"
import { ProofSection } from "./proof-section"
import { PositioningSection } from "./positioning-section"
import { PricingSection } from "./pricing-section"
import { InfrastructureSection } from "./infrastructure-section"
import { FooterSection } from "./footer-section"
import { SectionIndicator } from "./section-indicator"
import type { HomepageData } from "./types"

interface HomepageClientProps {
  data: HomepageData | null
}

export function HomepageClient({ data }: HomepageClientProps) {
  const [activeStage, setActiveStage] = useState(0)
  const handleStageChange = useCallback((stage: number) => setActiveStage(stage), [])

  return (
    <div className="relative z-10">
      <HeroSection data={data} />
      <ProblemSection />
      <div className="sticky top-0 z-20 bg-bg-primary/95 backdrop-blur-sm">
        <PipelineChips activeStage={activeStage} />
      </div>
      <EngineSection onStageChange={handleStageChange} />
      <ProofSection />
      <PositioningSection />
      <PricingSection />
      <InfrastructureSection />
      <FooterSection />
      <SectionIndicator />
    </div>
  )
}
```

**Step 4: Run test**

Run: `npx --prefix web vitest run web/src/components/landing/__tests__/page-assembly.test.tsx`
Expected: PASS

**Step 5: Run ALL landing tests**

Run: `npx --prefix web vitest run web/src/components/landing/`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add web/src/app/page.tsx web/src/components/landing/homepage-client.tsx web/src/components/landing/__tests__/page-assembly.test.tsx web/src/components/landing/index.ts
git commit -m "feat(web): assemble 9-section institutional homepage with HomepageClient"
```

---

## Task 18: Full test suite verification

**Step 1: Run all web tests**

Run: `npx --prefix web vitest run`
Expected: All pass. If any old tests reference deleted components, update or remove them.

**Step 2: Run API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass (294+ tests)

**Step 3: Fix any failures**

Address individually. Common issues:
- Old imports referencing deleted `framer-motion` wrappers — update to GSAP mocks
- Old test files referencing `HeroCandidatePanel` instead of `HeroCandidateCard`
- Snapshot tests that need updating

**Step 4: Commit fixes if any**

```bash
git add -A
git commit -m "fix(web): resolve test failures from homepage rebuild"
```

---

## Task 19: Visual smoke test

**Step 1: Start the dev server**

Run: `npx --prefix web next dev`

**Step 2: Verify in browser**

Open `http://localhost:3000` and check:
- [ ] Hero loads with rotating candidate card (7s cycle)
- [ ] Problem section has generous spacing
- [ ] Pipeline chips stick and highlight on scroll
- [ ] Engine cards counter-scroll (top left, bottom right)
- [ ] Pipeline complete by 75-80% scroll of engine section
- [ ] Proof section shows all 4 Recharts/CSS charts
- [ ] Positioning has vertical divider between columns
- [ ] Pricing has flat cards, "Most Popular" tag on Portfolio
- [ ] Infrastructure section is full-width with bullet blocks
- [ ] Footer has left links + right version/copyright
- [ ] Section indicator dots work (desktop only)
- [ ] Mobile: rotation disabled, swipe works, pipeline wraps

**Step 3: Take screenshots for verification**

Use browser dev tools to capture desktop and mobile views.

**Step 4: Commit any visual fixes**

```bash
git add -A
git commit -m "fix(web): visual polish from homepage smoke test"
```
