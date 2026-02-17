# Candidate Detail View Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the expanded stock card detail view into an institutional-grade analysis experience with animated entry, hero chart, Pro-gated metrics, and CSS ambient effects.

**Architecture:** Enhanced inline expand — card stays in-place but interior becomes a 12-column grid with staggered Framer Motion entry. New utility layers (compute metrics, compose summary) feed new UI components (institutional metrics, AI summary, pro gate). All ambient effects are CSS/SVG only — no Three.js on dashboard.

**Tech Stack:** Next.js 15, React, Tailwind CSS 4, Recharts, Framer Motion, Vitest + Testing Library

**Test command:** `cd web && npx vitest run` (all tests) or `cd web && npx vitest run src/path/to/test.ts` (single file)

**Design doc:** `docs/plans/2026-02-17-candidate-detail-redesign-design.md`

---

## Task 1: useSubscriptionTier Hook

**Files:**
- Create: `web/src/lib/hooks/use-subscription-tier.ts`
- Test: `web/src/lib/hooks/__tests__/use-subscription-tier.test.ts`

**Step 1: Write the failing test**

```ts
// web/src/lib/hooks/__tests__/use-subscription-tier.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useSubscriptionTier } from "../use-subscription-tier"

const mockFetch = vi.fn()
global.fetch = mockFetch

describe("useSubscriptionTier", () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it("returns 'free' when billing status is inactive", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ subscription_plan: "free", is_active: false }),
    })
    const { result } = renderHook(() => useSubscriptionTier())
    expect(result.current.tier).toBe("free") // default before fetch
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.tier).toBe("free")
  })

  it("returns 'pro' when billing status is active", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ subscription_plan: "margin_invest", is_active: true }),
    })
    const { result } = renderHook(() => useSubscriptionTier())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.tier).toBe("pro")
  })

  it("returns 'free' on fetch error", async () => {
    mockFetch.mockRejectedValueOnce(new Error("network"))
    const { result } = renderHook(() => useSubscriptionTier())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.tier).toBe("free")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/lib/hooks/__tests__/use-subscription-tier.test.ts`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```ts
// web/src/lib/hooks/use-subscription-tier.ts
"use client"

import { useEffect, useState } from "react"

export type SubscriptionTier = "free" | "pro"

interface SubscriptionTierResult {
  tier: SubscriptionTier
  loading: boolean
}

export function useSubscriptionTier(): SubscriptionTierResult {
  const [tier, setTier] = useState<SubscriptionTier>("free")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/v1/billing/status")
      .then((r) => r.json())
      .then((data) => {
        setTier(data.is_active ? "pro" : "free")
      })
      .catch(() => {
        setTier("free")
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  return { tier, loading }
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/lib/hooks/__tests__/use-subscription-tier.test.ts`
Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add web/src/lib/hooks/use-subscription-tier.ts web/src/lib/hooks/__tests__/use-subscription-tier.test.ts
git commit -m "feat(web): add useSubscriptionTier hook for Pro gating"
```

---

## Task 2: ProGate Wrapper Component

**Files:**
- Create: `web/src/components/dashboard/pro-gate.tsx`
- Test: `web/src/components/dashboard/__tests__/pro-gate.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/__tests__/pro-gate.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ProGate } from "../pro-gate"

// Mock the hook
vi.mock("@/lib/hooks/use-subscription-tier", () => ({
  useSubscriptionTier: vi.fn(),
}))

import { useSubscriptionTier } from "@/lib/hooks/use-subscription-tier"
const mockHook = vi.mocked(useSubscriptionTier)

describe("ProGate", () => {
  it("renders children unblurred for pro users", () => {
    mockHook.mockReturnValue({ tier: "pro", loading: false })
    render(
      <ProGate>
        <div data-testid="content">Secret data</div>
      </ProGate>
    )
    expect(screen.getByTestId("content")).toBeVisible()
    expect(screen.queryByText(/unlock/i)).not.toBeInTheDocument()
  })

  it("renders children with blur overlay for free users", () => {
    mockHook.mockReturnValue({ tier: "free", loading: false })
    render(
      <ProGate>
        <div data-testid="content">Secret data</div>
      </ProGate>
    )
    const container = screen.getByTestId("pro-gate-overlay")
    expect(container).toBeInTheDocument()
    expect(container.className).toContain("blur")
  })

  it("shows lock icon and CTA for free users", () => {
    mockHook.mockReturnValue({ tier: "free", loading: false })
    render(
      <ProGate>
        <div>Secret data</div>
      </ProGate>
    )
    expect(screen.getByText(/unlock institutional-grade analytics/i)).toBeInTheDocument()
    expect(screen.getByText(/pro insight/i)).toBeInTheDocument()
  })

  it("renders children unblurred while loading", () => {
    mockHook.mockReturnValue({ tier: "free", loading: true })
    render(
      <ProGate>
        <div data-testid="content">Secret data</div>
      </ProGate>
    )
    // Don't show blur while loading to avoid flash
    expect(screen.queryByTestId("pro-gate-overlay")).not.toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/pro-gate.test.tsx`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```tsx
// web/src/components/dashboard/pro-gate.tsx
"use client"

import { useSubscriptionTier } from "@/lib/hooks/use-subscription-tier"

interface ProGateProps {
  children: React.ReactNode
  className?: string
}

export function ProGate({ children, className = "" }: ProGateProps) {
  const { tier, loading } = useSubscriptionTier()

  if (loading || tier === "pro") {
    return <div className={className}>{children}</div>
  }

  return (
    <div className={`relative ${className}`}>
      <div
        data-testid="pro-gate-overlay"
        className="blur-[6px] select-none pointer-events-none"
        aria-hidden="true"
      >
        {children}
      </div>
      <div className="mt-3 flex items-center gap-3 bg-accent/[0.04] border border-accent/10 rounded-sm py-3 px-5">
        <svg
          className="w-3.5 h-3.5 text-accent/40 shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
          />
        </svg>
        <span className="text-sm text-text-secondary">
          Unlock institutional-grade analytics
        </span>
        <span className="text-xs font-medium bg-accent/10 text-accent px-2 py-0.5 rounded-sm">
          Pro Insight
        </span>
        <a
          href="/settings"
          className="ml-auto text-accent/60 hover:text-accent transition-colors"
          aria-label="Upgrade to Pro"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </a>
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/pro-gate.test.tsx`
Expected: 4 tests PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/pro-gate.tsx web/src/components/dashboard/__tests__/pro-gate.test.tsx
git commit -m "feat(web): add ProGate blur overlay component for conversion gating"
```

---

## Task 3: computeInstitutionalMetrics Utility

**Files:**
- Create: `web/src/lib/compute-institutional-metrics.ts`
- Test: `web/src/lib/__tests__/compute-institutional-metrics.test.ts`

**Step 1: Write the failing test**

```ts
// web/src/lib/__tests__/compute-institutional-metrics.test.ts
import { describe, it, expect } from "vitest"
import {
  computeSharpeRatio,
  computeMaxDrawdown,
  computeVolatility,
  computeInstitutionalMetrics,
} from "../compute-institutional-metrics"
import type { PriceBar, ScoreResponse } from "@/lib/api/types"

function makeBars(closes: number[]): PriceBar[] {
  return closes.map((close, i) => ({
    date: `2026-01-${String(i + 1).padStart(2, "0")}`,
    open: close,
    high: close * 1.01,
    low: close * 0.99,
    close,
    volume: 1000000,
    adj_close: close,
  }))
}

describe("computeSharpeRatio", () => {
  it("returns positive Sharpe for upward trending prices", () => {
    // 10 days of consistent 1% daily returns
    const closes = [100, 101, 102.01, 103.03, 104.06, 105.1, 106.15, 107.21, 108.28, 109.37]
    const result = computeSharpeRatio(makeBars(closes))
    expect(result).toBeGreaterThan(0)
  })

  it("returns null for insufficient data", () => {
    expect(computeSharpeRatio(makeBars([100, 101]))).toBeNull()
  })
})

describe("computeMaxDrawdown", () => {
  it("computes drawdown correctly for peak-to-trough", () => {
    // Peak at 200, trough at 150 = -25%
    const closes = [100, 150, 200, 180, 150, 160]
    const result = computeMaxDrawdown(makeBars(closes))
    expect(result).toBeCloseTo(-0.25, 2)
  })

  it("returns 0 for monotonically increasing prices", () => {
    const closes = [100, 110, 120, 130, 140]
    expect(computeMaxDrawdown(makeBars(closes))).toBe(0)
  })
})

describe("computeVolatility", () => {
  it("returns annualized volatility as a percentage", () => {
    const closes = [100, 102, 98, 103, 97, 105, 99, 104, 96, 101]
    const result = computeVolatility(makeBars(closes))
    expect(result).toBeGreaterThan(0)
    expect(result).toBeLessThan(200) // sanity: not unreasonably high
  })

  it("returns null for insufficient data", () => {
    expect(computeVolatility(makeBars([100]))).toBeNull()
  })
})

describe("computeInstitutionalMetrics", () => {
  it("returns all metrics from a score with price history", () => {
    const closes = Array.from({ length: 60 }, (_, i) => 100 + i * 0.5 + Math.sin(i) * 2)
    const score = {
      price_history: makeBars(closes),
      max_position_pct: 4.2,
      growth_stage: "mature",
    } as unknown as ScoreResponse

    const result = computeInstitutionalMetrics(score)
    expect(result).not.toBeNull()
    expect(result!.sharpeRatio).toBeDefined()
    expect(result!.maxDrawdown).toBeDefined()
    expect(result!.volatility).toBeDefined()
    expect(result!.riskClassification).toBe("Moderate")
    expect(result!.allocationWeight).toBe(4.2)
  })

  it("returns null when no price history", () => {
    const score = { price_history: null } as unknown as ScoreResponse
    expect(computeInstitutionalMetrics(score)).toBeNull()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/lib/__tests__/compute-institutional-metrics.test.ts`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```ts
// web/src/lib/compute-institutional-metrics.ts
import type { PriceBar, ScoreResponse } from "@/lib/api/types"

export interface InstitutionalMetrics {
  sharpeRatio: number | null
  maxDrawdown: number
  volatility: number | null
  avgProfitMargin: number | null
  riskClassification: string
  allocationWeight: number | null
}

const RISK_FREE_RATE = 0.05 // ~5% annualized
const TRADING_DAYS_PER_YEAR = 252
const MIN_BARS_FOR_STATS = 5

function dailyReturns(bars: PriceBar[]): number[] {
  const returns: number[] = []
  for (let i = 1; i < bars.length; i++) {
    if (bars[i - 1].close > 0) {
      returns.push((bars[i].close - bars[i - 1].close) / bars[i - 1].close)
    }
  }
  return returns
}

function mean(values: number[]): number {
  return values.reduce((sum, v) => sum + v, 0) / values.length
}

function stddev(values: number[]): number {
  const m = mean(values)
  const variance = values.reduce((sum, v) => sum + (v - m) ** 2, 0) / (values.length - 1)
  return Math.sqrt(variance)
}

export function computeSharpeRatio(bars: PriceBar[]): number | null {
  const returns = dailyReturns(bars)
  if (returns.length < MIN_BARS_FOR_STATS) return null

  const avgDailyReturn = mean(returns)
  const dailyStd = stddev(returns)
  if (dailyStd === 0) return null

  const dailyRiskFree = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
  const sharpe = ((avgDailyReturn - dailyRiskFree) / dailyStd) * Math.sqrt(TRADING_DAYS_PER_YEAR)
  return Math.round(sharpe * 100) / 100
}

export function computeMaxDrawdown(bars: PriceBar[]): number {
  let peak = -Infinity
  let maxDd = 0
  for (const bar of bars) {
    if (bar.close > peak) peak = bar.close
    const dd = (bar.close - peak) / peak
    if (dd < maxDd) maxDd = dd
  }
  return Math.round(maxDd * 10000) / 10000
}

export function computeVolatility(bars: PriceBar[]): number | null {
  const returns = dailyReturns(bars)
  if (returns.length < MIN_BARS_FOR_STATS) return null

  const annualized = stddev(returns) * Math.sqrt(TRADING_DAYS_PER_YEAR) * 100
  return Math.round(annualized * 10) / 10
}

function classifyRisk(volatility: number | null, growthStage?: string): string {
  if (volatility == null) return "Unknown"
  if (volatility > 40) return "Aggressive"
  if (volatility > 25) return "Moderate-High"
  if (volatility > 15) return "Moderate"
  return "Conservative"
}

export function computeInstitutionalMetrics(score: ScoreResponse): InstitutionalMetrics | null {
  if (!score.price_history || score.price_history.length === 0) return null

  const sorted = [...score.price_history].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )

  const volatility = computeVolatility(sorted)

  return {
    sharpeRatio: computeSharpeRatio(sorted),
    maxDrawdown: computeMaxDrawdown(sorted),
    volatility,
    avgProfitMargin: null, // Derived from factor sub-scores in a future iteration
    riskClassification: classifyRisk(volatility, score.growth_stage),
    allocationWeight: score.max_position_pct ?? null,
  }
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/lib/__tests__/compute-institutional-metrics.test.ts`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/lib/compute-institutional-metrics.ts web/src/lib/__tests__/compute-institutional-metrics.test.ts
git commit -m "feat(web): add computeInstitutionalMetrics utility (Sharpe, drawdown, volatility)"
```

---

## Task 4: composeAiSummary Utility

**Files:**
- Create: `web/src/lib/compose-ai-summary.ts`
- Test: `web/src/lib/__tests__/compose-ai-summary.test.ts`

**Step 1: Write the failing test**

```ts
// web/src/lib/__tests__/compose-ai-summary.test.ts
import { describe, it, expect } from "vitest"
import { composeAiSummary } from "../compose-ai-summary"
import type { FactorBreakdownResponse, ScoreResponse } from "@/lib/api/types"

function makeFactor(name: string, percentile: number): FactorBreakdownResponse {
  return {
    factor_name: name,
    weight: 0.33,
    sub_scores: [],
    average_percentile: percentile,
  }
}

describe("composeAiSummary", () => {
  it("produces a summary string for a high-scoring stock", () => {
    const score = {
      ticker: "AAPL",
      name: "Apple Inc.",
      quality: makeFactor("quality", 88),
      value: makeFactor("value", 72),
      momentum: makeFactor("momentum", 65),
      score: 85,
    } as unknown as ScoreResponse

    const result = composeAiSummary(score)
    expect(result.summary.length).toBeGreaterThan(20)
    expect(result.summary).toContain("AAPL")
    expect(result.confidence).toBeGreaterThan(0)
    expect(result.confidence).toBeLessThanOrEqual(100)
  })

  it("produces lower confidence for mixed signals", () => {
    const highScore = {
      ticker: "GOOD",
      name: "Good Co",
      quality: makeFactor("quality", 90),
      value: makeFactor("value", 85),
      momentum: makeFactor("momentum", 80),
      score: 90,
    } as unknown as ScoreResponse

    const mixedScore = {
      ticker: "MIX",
      name: "Mixed Co",
      quality: makeFactor("quality", 90),
      value: makeFactor("value", 30),
      momentum: makeFactor("momentum", 20),
      score: 50,
    } as unknown as ScoreResponse

    const highResult = composeAiSummary(highScore)
    const mixedResult = composeAiSummary(mixedScore)
    expect(highResult.confidence).toBeGreaterThan(mixedResult.confidence)
  })

  it("mentions winning track when present", () => {
    const score = {
      ticker: "CMP",
      name: "Compounder Co",
      quality: makeFactor("quality", 85),
      value: makeFactor("value", 75),
      momentum: makeFactor("momentum", 60),
      winning_track: "compounder",
      score: 80,
    } as unknown as ScoreResponse

    const result = composeAiSummary(score)
    expect(result.summary.toLowerCase()).toContain("compounder")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/lib/__tests__/compose-ai-summary.test.ts`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```ts
// web/src/lib/compose-ai-summary.ts
import type { ScoreResponse } from "@/lib/api/types"
import { getFactorInterpretation } from "@/lib/score-interpretation"

export interface AiSummaryResult {
  summary: string
  confidence: number
}

function factorStrength(percentile: number): string {
  if (percentile >= 80) return "strong"
  if (percentile >= 60) return "above-average"
  if (percentile >= 40) return "moderate"
  return "weak"
}

export function composeAiSummary(score: ScoreResponse): AiSummaryResult {
  const factors = [
    { name: "quality", p: score.quality.average_percentile },
    { name: "value", p: score.value.average_percentile },
    { name: "momentum", p: score.momentum.average_percentile },
  ]

  const sorted = [...factors].sort((a, b) => b.p - a.p)
  const strongest = sorted[0]
  const weakest = sorted[sorted.length - 1]

  // Build summary
  const parts: string[] = []

  if (score.winning_track) {
    const track = score.winning_track === "compounder" ? "compounder" : "mispricing"
    parts.push(
      `${score.ticker} scores as a ${track} candidate with ${factorStrength(strongest.p)} ${strongest.name}.`,
    )
  } else {
    parts.push(
      `${score.ticker} demonstrates ${factorStrength(strongest.p)} ${strongest.name} characteristics.`,
    )
  }

  if (weakest.p < 50) {
    parts.push(`${weakest.name.charAt(0).toUpperCase() + weakest.name.slice(1)} is a relative weak point at the ${Math.round(weakest.p)}th percentile.`)
  } else {
    parts.push(`All core factors rank above median, indicating broad strength.`)
  }

  // Confidence = composite score weighted by factor agreement
  const avg = factors.reduce((s, f) => s + f.p, 0) / factors.length
  const spread = Math.max(...factors.map((f) => f.p)) - Math.min(...factors.map((f) => f.p))
  // High avg + low spread = high confidence
  const confidence = Math.round(Math.min(100, Math.max(0, avg * 0.7 + (100 - spread) * 0.3)))

  return {
    summary: parts.join(" "),
    confidence,
  }
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/lib/__tests__/compose-ai-summary.test.ts`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/lib/compose-ai-summary.ts web/src/lib/__tests__/compose-ai-summary.test.ts
git commit -m "feat(web): add composeAiSummary utility for AI performance interpretation"
```

---

## Task 5: InstitutionalMetrics Component

**Files:**
- Create: `web/src/components/dashboard/institutional-metrics.tsx`
- Test: `web/src/components/dashboard/__tests__/institutional-metrics.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/__tests__/institutional-metrics.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { InstitutionalMetrics } from "../institutional-metrics"
import type { InstitutionalMetrics as Metrics } from "@/lib/compute-institutional-metrics"

// Mock ProGate to passthrough for testing
vi.mock("../pro-gate", () => ({
  ProGate: ({ children }: { children: React.ReactNode }) => <div data-testid="pro-gate">{children}</div>,
}))

const metrics: Metrics = {
  sharpeRatio: 1.84,
  maxDrawdown: -0.124,
  volatility: 18.2,
  avgProfitMargin: null,
  riskClassification: "Moderate",
  allocationWeight: 4.2,
}

describe("InstitutionalMetrics", () => {
  it("renders all metric cells", () => {
    render(<InstitutionalMetrics metrics={metrics} />)
    expect(screen.getByText("1.84")).toBeInTheDocument()
    expect(screen.getByText("-12.4%")).toBeInTheDocument()
    expect(screen.getByText("18.2%")).toBeInTheDocument()
    expect(screen.getByText("Moderate")).toBeInTheDocument()
    expect(screen.getByText("4.2%")).toBeInTheDocument()
  })

  it("renders metric labels in uppercase", () => {
    render(<InstitutionalMetrics metrics={metrics} />)
    expect(screen.getByText("SHARPE RATIO")).toBeInTheDocument()
    expect(screen.getByText("MAX DRAWDOWN")).toBeInTheDocument()
    expect(screen.getByText("VOLATILITY")).toBeInTheDocument()
  })

  it("wraps in ProGate", () => {
    render(<InstitutionalMetrics metrics={metrics} />)
    expect(screen.getByTestId("pro-gate")).toBeInTheDocument()
  })

  it("renders nothing when metrics is null", () => {
    const { container } = render(<InstitutionalMetrics metrics={null} />)
    expect(container.firstChild).toBeNull()
  })

  it("shows N/A for null avgProfitMargin", () => {
    render(<InstitutionalMetrics metrics={metrics} />)
    expect(screen.getByText("N/A")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/institutional-metrics.test.tsx`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```tsx
// web/src/components/dashboard/institutional-metrics.tsx
"use client"

import { ProGate } from "./pro-gate"
import type { InstitutionalMetrics as Metrics } from "@/lib/compute-institutional-metrics"

interface MetricCellProps {
  label: string
  value: string
  context?: string
}

function MetricCell({ label, value, context }: MetricCellProps) {
  return (
    <div className="bg-bg-subtle/50 border border-border-primary/30 rounded-sm p-5 transition-all duration-200 hover:bg-bg-subtle/80 hover:shadow-sm">
      <div className="text-xs font-medium tracking-widest uppercase text-text-tertiary">
        {label}
      </div>
      <div className="text-2xl font-mono font-bold text-text-primary mt-2">
        {value}
      </div>
      {context && (
        <div className="text-xs text-text-secondary mt-3">{context}</div>
      )}
    </div>
  )
}

interface InstitutionalMetricsProps {
  metrics: Metrics | null
  className?: string
}

export function InstitutionalMetrics({ metrics, className = "" }: InstitutionalMetricsProps) {
  if (!metrics) return null

  return (
    <ProGate className={className}>
      <div
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
        data-testid="institutional-metrics"
      >
        <MetricCell
          label="SHARPE RATIO"
          value={metrics.sharpeRatio != null ? metrics.sharpeRatio.toFixed(2) : "N/A"}
        />
        <MetricCell
          label="MAX DRAWDOWN"
          value={`${(metrics.maxDrawdown * 100).toFixed(1)}%`}
        />
        <MetricCell
          label="VOLATILITY"
          value={metrics.volatility != null ? `${metrics.volatility.toFixed(1)}%` : "N/A"}
        />
        <MetricCell
          label="AVG PROFIT MARGIN"
          value={metrics.avgProfitMargin != null ? `${metrics.avgProfitMargin.toFixed(1)}%` : "N/A"}
        />
        <MetricCell
          label="RISK CLASSIFICATION"
          value={metrics.riskClassification}
        />
        <MetricCell
          label="ALLOCATION WEIGHT"
          value={metrics.allocationWeight != null ? `${metrics.allocationWeight.toFixed(1)}%` : "N/A"}
          context="of portfolio"
        />
      </div>
    </ProGate>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/institutional-metrics.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/institutional-metrics.tsx web/src/components/dashboard/__tests__/institutional-metrics.test.tsx
git commit -m "feat(web): add InstitutionalMetrics 3x2 grid component with Pro gating"
```

---

## Task 6: AiSummary Component

**Files:**
- Create: `web/src/components/dashboard/ai-summary.tsx`
- Test: `web/src/components/dashboard/__tests__/ai-summary.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/__tests__/ai-summary.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AiSummary } from "../ai-summary"

vi.mock("../pro-gate", () => ({
  ProGate: ({ children }: { children: React.ReactNode }) => <div data-testid="pro-gate">{children}</div>,
}))

describe("AiSummary", () => {
  it("renders summary text and confidence bar", () => {
    render(
      <AiSummary summary="AAPL demonstrates strong quality." confidence={78} />
    )
    expect(screen.getByText("AAPL demonstrates strong quality.")).toBeInTheDocument()
    expect(screen.getByText("78")).toBeInTheDocument()
    expect(screen.getByText("AI ANALYSIS")).toBeInTheDocument()
  })

  it("renders confidence bar with correct width style", () => {
    render(<AiSummary summary="Test" confidence={65} />)
    const bar = screen.getByTestId("confidence-bar-fill")
    expect(bar.style.width).toBe("65%")
  })

  it("wraps in ProGate", () => {
    render(<AiSummary summary="Test" confidence={50} />)
    expect(screen.getByTestId("pro-gate")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/ai-summary.test.tsx`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```tsx
// web/src/components/dashboard/ai-summary.tsx
"use client"

import { ProGate } from "./pro-gate"

interface AiSummaryProps {
  summary: string
  confidence: number
  className?: string
}

export function AiSummary({ summary, confidence, className = "" }: AiSummaryProps) {
  return (
    <ProGate className={className}>
      <div
        className="bg-bg-subtle/50 border border-border-primary/30 rounded-sm p-5"
        data-testid="ai-summary"
      >
        <div className="text-xs font-semibold tracking-wide uppercase text-text-tertiary mb-3">
          AI ANALYSIS
        </div>
        <p className="text-sm text-text-secondary leading-relaxed mb-4">
          {summary}
        </p>
        <div className="flex items-center gap-3">
          <span className="text-xs text-text-tertiary uppercase tracking-wide">Confidence</span>
          <div className="flex-1 h-2 bg-bg-primary rounded-full overflow-hidden">
            <div
              data-testid="confidence-bar-fill"
              className="h-full bg-accent rounded-full transition-[width] duration-[600ms] ease-[cubic-bezier(0.22,1,0.36,1)]"
              style={{ width: `${Math.max(0, Math.min(100, confidence))}%` }}
            />
          </div>
          <span className="text-xs font-mono text-text-primary w-8 text-right">
            {Math.round(confidence)}
          </span>
        </div>
      </div>
    </ProGate>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/ai-summary.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/ai-summary.tsx web/src/components/dashboard/__tests__/ai-summary.test.tsx
git commit -m "feat(web): add AiSummary component with confidence bar and Pro gating"
```

---

## Task 7: CustomCrosshair Tooltip Component

**Files:**
- Create: `web/src/components/dashboard/custom-crosshair.tsx`
- Test: `web/src/components/dashboard/__tests__/custom-crosshair.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/__tests__/custom-crosshair.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { CustomCrosshair } from "../custom-crosshair"

describe("CustomCrosshair", () => {
  it("renders nothing when not active", () => {
    const { container } = render(<CustomCrosshair active={false} payload={[]} label="" />)
    expect(container.firstChild).toBeNull()
  })

  it("renders date, close, volume when active with payload", () => {
    const payload = [
      { dataKey: "close", value: 182.5, color: "#1C7A5A" },
      { dataKey: "volume", value: 45000000, color: "#888" },
    ]
    render(<CustomCrosshair active={true} payload={payload} label="02-14" />)
    expect(screen.getByText("02-14")).toBeInTheDocument()
    expect(screen.getByText("$182.50")).toBeInTheDocument()
    expect(screen.getByText("45.0M")).toBeInTheDocument()
  })

  it("formats volume in millions", () => {
    const payload = [
      { dataKey: "close", value: 100, color: "#1C7A5A" },
      { dataKey: "volume", value: 1234567, color: "#888" },
    ]
    render(<CustomCrosshair active={true} payload={payload} label="01-01" />)
    expect(screen.getByText("1.2M")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/custom-crosshair.test.tsx`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```tsx
// web/src/components/dashboard/custom-crosshair.tsx
interface PayloadItem {
  dataKey: string
  value: number
  color: string
}

interface CustomCrosshairProps {
  active: boolean
  payload: PayloadItem[]
  label: string
}

function formatVolume(vol: number): string {
  if (vol >= 1_000_000_000) return `${(vol / 1_000_000_000).toFixed(1)}B`
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(1)}K`
  return vol.toString()
}

export function CustomCrosshair({ active, payload, label }: CustomCrosshairProps) {
  if (!active || !payload || payload.length === 0) return null

  const close = payload.find((p) => p.dataKey === "close")
  const volume = payload.find((p) => p.dataKey === "volume")

  return (
    <div className="bg-bg-elevated border border-border-primary shadow-modal rounded-sm px-3 py-2 text-xs">
      <div className="font-mono text-text-tertiary mb-1">{label}</div>
      {close && (
        <div className="flex justify-between gap-4">
          <span className="text-text-secondary">Close</span>
          <span className="font-mono font-bold text-text-primary">
            ${close.value.toFixed(2)}
          </span>
        </div>
      )}
      {volume && (
        <div className="flex justify-between gap-4">
          <span className="text-text-secondary">Volume</span>
          <span className="font-mono text-text-primary">
            {formatVolume(volume.value)}
          </span>
        </div>
      )}
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/custom-crosshair.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/custom-crosshair.tsx web/src/components/dashboard/__tests__/custom-crosshair.test.tsx
git commit -m "feat(web): add CustomCrosshair tooltip for precision chart hover"
```

---

## Task 8: Price Chart Upgrade

**Files:**
- Modify: `web/src/components/dashboard/price-chart.tsx`

This is a visual-heavy component. The upgrade replaces the chart internals while keeping the same props interface.

**Step 1: Rewrite price-chart.tsx**

Replace the full content of `web/src/components/dashboard/price-chart.tsx` with:

```tsx
"use client"

import { useState } from "react"
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  CartesianGrid,
} from "recharts"
import { CustomCrosshair } from "./custom-crosshair"
import type { PriceBar } from "@/lib/api/types"

interface PriceChartProps {
  bars: PriceBar[] | null | undefined
  buyPrice?: number | null
  sellPrice?: number | null
  className?: string
}

type TimeRange = "1M" | "3M" | "6M" | "1Y"

const RANGE_DAYS: Record<TimeRange, number> = {
  "1M": 22,
  "3M": 66,
  "6M": 132,
  "1Y": 252,
}

export function PriceChart({
  bars,
  buyPrice,
  sellPrice,
  className = "",
}: PriceChartProps) {
  const [range, setRange] = useState<TimeRange>("3M")

  if (!bars || bars.length === 0) {
    return (
      <div
        className={`h-[320px] flex items-center justify-center bg-bg-secondary rounded-sm ${className}`}
        data-testid="price-chart-empty"
      >
        <span className="text-sm text-text-tertiary">
          No price data available
        </span>
      </div>
    )
  }

  const sorted = [...bars].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )
  const sliced = sorted.slice(-RANGE_DAYS[range])

  const data = sliced.map((bar) => ({
    date: bar.date.slice(5),
    close: bar.close,
    volume: bar.volume,
    open: bar.open,
    high: bar.high,
    low: bar.low,
  }))

  return (
    <div
      className={`relative border border-border-primary/50 rounded-sm animate-chart-glow ${className}`}
      data-testid="price-chart"
    >
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <h4 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary">
          Price History
        </h4>
        <div className="flex gap-1.5">
          {(["1M", "3M", "6M", "1Y"] as TimeRange[]).map((r) => (
            <button
              key={r}
              onClick={(e) => {
                e.stopPropagation()
                setRange(r)
              }}
              className={`px-2 py-0.5 text-xs font-mono tracking-wide rounded-sm transition-colors ${
                range === r
                  ? "bg-accent text-bg-primary shadow-sm"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 16 }}>
          <defs>
            <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.2} />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="opacity-10" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fontFamily: "var(--font-geist-mono)" }}
            interval="preserveStartEnd"
            className="text-text-tertiary"
          />
          <YAxis
            yAxisId="price"
            domain={["auto", "auto"]}
            tick={{ fontSize: 10, fontFamily: "var(--font-geist-mono)" }}
            className="text-text-tertiary"
            width={60}
            tickFormatter={(v: number) => `$${v}`}
          />
          <Tooltip
            content={({ active, payload, label }) => (
              <CustomCrosshair
                active={!!active}
                payload={(payload ?? []).map((p) => ({
                  dataKey: String(p.dataKey),
                  value: Number(p.value),
                  color: String(p.color ?? ""),
                }))}
                label={String(label)}
              />
            )}
            cursor={{ stroke: "var(--text-tertiary)", strokeDasharray: "4 2", strokeWidth: 1 }}
          />
          <YAxis yAxisId="volume" orientation="right" hide />
          <Bar
            dataKey="volume"
            fill="currentColor"
            className="text-text-tertiary"
            opacity={0.08}
            yAxisId="volume"
          />
          <Area
            type="monotone"
            dataKey="close"
            fill="url(#priceGradient)"
            stroke="none"
            yAxisId="price"
            animationDuration={800}
            animationEasing="ease-out"
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="currentColor"
            strokeWidth={2}
            dot={false}
            className="text-accent"
            yAxisId="price"
            animationDuration={800}
            animationEasing="ease-out"
          />
          {buyPrice != null && sellPrice != null && (
            <ReferenceArea
              y1={buyPrice}
              y2={sellPrice}
              yAxisId="price"
              fill="var(--accent)"
              fillOpacity={0.04}
            />
          )}
          {buyPrice != null && (
            <ReferenceLine
              y={buyPrice}
              yAxisId="price"
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-bullish"
              label={{
                value: "Buy",
                position: "right",
                fontSize: 10,
                fontFamily: "var(--font-geist-mono)",
              }}
            />
          )}
          {sellPrice != null && (
            <ReferenceLine
              y={sellPrice}
              yAxisId="price"
              stroke="currentColor"
              strokeDasharray="4 2"
              className="text-warning"
              label={{
                value: "Sell",
                position: "right",
                fontSize: 10,
                fontFamily: "var(--font-geist-mono)",
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
```

**Step 2: Add CSS keyframe for chart glow**

Add to `web/src/app/globals.css` inside the existing styles (not inside `@theme`):

```css
@keyframes chart-glow {
  0% { box-shadow: 0 0 40px 0 color-mix(in srgb, var(--accent) 8%, transparent); }
  100% { box-shadow: 0 0 0 0 transparent; }
}

.animate-chart-glow {
  animation: chart-glow 1.5s ease-out 0.9s 1 both;
}
```

**Step 3: Run existing tests to verify no regressions**

Run: `cd web && npx vitest run`
Expected: All existing tests PASS (price chart has no dedicated tests — it's tested indirectly through stock-card)

**Step 4: Commit**

```bash
git add web/src/components/dashboard/price-chart.tsx web/src/app/globals.css
git commit -m "feat(web): upgrade price chart with gradient underfill, crosshair tooltip, animated draw"
```

---

## Task 9: Factor Breakdown Typography & Spacing Upgrade

**Files:**
- Modify: `web/src/components/dashboard/factor-breakdown.tsx`

**Step 1: Apply typography and spacing changes**

In `web/src/components/dashboard/factor-breakdown.tsx`, update `FactorSection`:

Replace the entire `FactorSection` function body with:

```tsx
function FactorSection({ factor }: FactorSectionProps) {
  return (
    <div
      className="pb-6 border-b border-border-primary/30 last:border-b-0 last:pb-0"
      data-testid={`factor-section-${factor.factor_name.toLowerCase()}`}
    >
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-text-primary">
          {factor.factor_name.charAt(0).toUpperCase() + factor.factor_name.slice(1).replace("_", " ")}
        </h4>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-text-tertiary">
            {(factor.weight * 100).toFixed(0)}%
          </span>
          <span className="text-lg font-mono font-bold text-accent">
            {factor.average_percentile.toFixed(0)}
          </span>
        </div>
      </div>
      <p className="text-xs text-text-tertiary leading-relaxed mb-3">
        {getFactorInterpretation(factor.factor_name, factor.average_percentile)}
      </p>
      <div className="space-y-2.5">
        {factor.sub_scores.map((sub) => (
          <PercentileBar
            key={sub.name}
            value={sub.percentile_rank}
            label={formatAttributeLabel(sub.name)}
            showValue
          />
        ))}
      </div>
    </div>
  )
}
```

Update the section heading in `FactorBreakdown`:

Replace:
```tsx
<h3 className="text-base font-semibold text-text-primary">
```

With:
```tsx
<h3 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary">
```

Update spacing:
```tsx
<div className="space-y-5">
```
(changed from `space-y-4` in outer, `space-y-5` stays)

**Step 2: Run tests**

Run: `cd web && npx vitest run`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add web/src/components/dashboard/factor-breakdown.tsx
git commit -m "feat(web): upgrade factor breakdown typography, spacing, and dividers"
```

---

## Task 10: Right Column Upgrades (Filter, Valuation, Signal, Metadata)

**Files:**
- Modify: `web/src/components/dashboard/filter-list.tsx`
- Modify: `web/src/components/dashboard/valuation-breakdown.tsx`
- Modify: `web/src/components/dashboard/signal-timeline.tsx`

**Step 1: Update filter-list.tsx**

Replace the section heading:
```tsx
<h3 className="text-base font-semibold text-text-primary mb-3">
```
With:
```tsx
<h3 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary mb-3">
```

Update `FilterItem` to add mono "passed" label:

Replace:
```tsx
{filter.detail && (
  <span className="text-text-secondary ml-auto text-xs">
    {filter.detail}
  </span>
)}
```

With:
```tsx
<span className="text-xs font-mono text-text-tertiary ml-auto">
  {filter.passed ? "passed" : "failed"}
</span>
```

**Step 2: Update valuation-breakdown.tsx**

Replace all heading instances of:
```tsx
<h4 className="text-sm font-semibold text-text-primary mb-3">
```
With:
```tsx
<h4 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary mb-3">
```

In the bar chart entries, replace:
```tsx
<span className="text-xs text-text-secondary w-28 shrink-0">
```
With:
```tsx
<span className="text-xs text-text-secondary w-32 shrink-0">
```

Replace bar height:
```tsx
<div className="flex-1 h-4 bg-bg-secondary rounded-sm overflow-hidden">
```
With:
```tsx
<div className="flex-1 h-5 bg-bg-secondary rounded-sm overflow-hidden">
```

Add `font-mono` to the dollar values:
```tsx
<span className="text-xs text-text-primary font-mono font-medium w-16 text-right">
```

In the consensus/price/MoS section, add `font-mono` to values:
```tsx
<span className="text-text-primary font-mono font-semibold">${intrinsicValue.toFixed(2)}</span>
```
```tsx
<span className="text-text-primary font-mono">${actualPrice.toFixed(2)}</span>
```
```tsx
<span className={`font-mono ${marginOfSafety > 0 ? "text-bullish font-semibold" : "text-bearish"}`}>
```

**Step 3: Update signal-timeline.tsx**

Replace heading:
```tsx
<h4 className="text-sm font-semibold text-text-primary mb-3">Signal History</h4>
```
With:
```tsx
<h4 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary mb-3">SIGNAL HISTORY</h4>
```

Update signal names to `font-semibold`:
```tsx
<span className={`uppercase text-xs font-semibold ${signalColor[t.previous_signal] ?? ""}`}>
```
```tsx
<span className={`uppercase text-xs font-semibold ${signalColor[t.new_signal] ?? ""}`}>
```

Make arrow quieter:
```tsx
<span className="text-text-tertiary/40">&rarr;</span>
```

Add `font-mono` to price:
```tsx
<span className="text-text-secondary font-mono ml-auto">
```

**Step 4: Run tests**

Run: `cd web && npx vitest run`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/filter-list.tsx web/src/components/dashboard/valuation-breakdown.tsx web/src/components/dashboard/signal-timeline.tsx
git commit -m "feat(web): upgrade right column typography — filters, valuation, signals"
```

---

## Task 11: Asset Detail Rewrite (Layout + Animation Orchestration)

**Files:**
- Modify: `web/src/components/dashboard/asset-detail.tsx`

This is the central composition task. It rewires the layout to the 12-column grid, adds Framer Motion staggered entry, and integrates the new components.

**Step 1: Rewrite asset-detail.tsx**

Replace the full content with:

```tsx
"use client"

import { useState, useMemo } from "react"
import { motion, useReducedMotion } from "framer-motion"
import { ConvictionBadge } from "@/components/ui"
import { ActionPill } from "@/components/ui"
import { formatAttributeLabel, formatScoredAt } from "@/lib/format"
import { computeInstitutionalMetrics } from "@/lib/compute-institutional-metrics"
import { composeAiSummary } from "@/lib/compose-ai-summary"
import { FactorBreakdown } from "./factor-breakdown"
import { FilterList } from "./filter-list"
import { PriceChart } from "./price-chart"
import { ValuationBreakdown } from "./valuation-breakdown"
import { SignalTimeline } from "./signal-timeline"
import { InstitutionalMetrics } from "./institutional-metrics"
import { AiSummary } from "./ai-summary"
import type { ScoreResponse } from "@/lib/api/types"

interface AssetDetailProps {
  score: ScoreResponse
  className?: string
}

const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
}

export function AssetDetail({ score, className = "" }: AssetDetailProps) {
  const [showData, setShowData] = useState(false)
  const hasV2 = score.opportunity_type != null
  const prefersReduced = useReducedMotion()

  const institutionalMetrics = useMemo(
    () => computeInstitutionalMetrics(score),
    [score],
  )

  const aiSummary = useMemo(() => composeAiSummary(score), [score])

  const transition = prefersReduced
    ? { duration: 0 }
    : { duration: 0.4, ease: "easeOut" }

  function stagger(delay: number) {
    return prefersReduced ? {} : { delay }
  }

  return (
    <div
      className={`border-t border-border-primary pt-8 mt-4 ${className}`}
      data-testid={`asset-detail-${score.ticker}`}
    >
      {/* Header */}
      <motion.div
        className="flex items-center gap-3 mb-8"
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={{ ...transition, ...stagger(0) }}
      >
        <h3 className="text-2xl font-bold tracking-tight text-text-primary">
          {score.ticker}
        </h3>
        <span className="text-sm font-normal text-text-tertiary">
          {score.name}
        </span>
        <span className="text-3xl font-mono font-bold text-accent ml-auto">
          {(score.score || score.composite_percentile).toFixed(0)}
        </span>
        <ConvictionBadge level={score.conviction_level} />
        <ActionPill
          signal={score.signal}
          buyPrice={score.buy_price}
          sellPrice={score.sell_price}
          actualPrice={score.actual_price}
        />
        {hasV2 && (
          <>
            {score.winning_track && (
              <span
                className={`text-xs px-2 py-0.5 rounded font-medium ${
                  score.winning_track === "compounder"
                    ? "bg-accent/10 text-accent"
                    : "bg-purple-500/10 text-purple-400"
                }`}
              >
                {score.winning_track === "compounder" ? "Compounder" : "Mispricing"} Track
              </span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation()
                setShowData(!showData)
              }}
              className="text-xs text-accent hover:text-accent/80 underline ml-2"
              data-testid="thesis-data-toggle"
            >
              {showData ? "Show Thesis" : "Show Data"}
            </button>
          </>
        )}
      </motion.div>

      {/* V2 Metrics Row */}
      {hasV2 && score.asymmetry_ratio != null && (
        <motion.div
          className="flex items-center gap-4 mb-6 text-sm"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          transition={{ ...transition, ...stagger(0.05) }}
        >
          <span className="text-text-secondary">
            Asymmetry:{" "}
            <span className="text-text-primary font-mono font-bold">
              {score.asymmetry_ratio.toFixed(1)}x
            </span>
          </span>
          {score.max_position_pct != null && (
            <span className="text-text-secondary">
              Max position:{" "}
              <span className="text-text-primary font-mono font-medium">
                {score.max_position_pct.toFixed(0)}%
              </span>
            </span>
          )}
          {score.timing_signal && (
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                score.timing_signal === "buy_now"
                  ? "bg-bullish/10 text-bullish"
                  : score.timing_signal === "add_on_pullback"
                    ? "bg-accent/10 text-accent"
                    : "bg-text-secondary/10 text-text-secondary"
              }`}
            >
              {score.timing_signal === "buy_now"
                ? "Buy now"
                : score.timing_signal === "add_on_pullback"
                  ? "Add on pullback"
                  : "Wait for catalyst"}
            </span>
          )}
        </motion.div>
      )}

      {/* Hero Price Chart */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={{ ...transition, ...stagger(0.1) }}
      >
        <PriceChart
          bars={score.price_history ?? undefined}
          buyPrice={score.buy_price}
          sellPrice={score.sell_price}
          className="mb-8"
        />
      </motion.div>

      {/* Institutional Metrics (Pro-gated) */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={{ ...transition, ...stagger(0.5) }}
      >
        <InstitutionalMetrics metrics={institutionalMetrics} className="mb-8" />
      </motion.div>

      {/* AI Summary (Pro-gated) */}
      <motion.div
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={{ ...transition, ...stagger(0.7) }}
      >
        <AiSummary
          summary={aiSummary.summary}
          confidence={aiSummary.confidence}
          className="mb-8"
        />
      </motion.div>

      {/* Two-column layout: Factors | Right column */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-12 gap-8"
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        transition={{ ...transition, ...stagger(0.8) }}
      >
        {/* Left column: Factor Breakdown (7 cols) */}
        <div className="md:col-span-7">
          <FactorBreakdown
            quality={score.quality}
            value={score.value}
            momentum={score.momentum}
            capitalAllocation={score.capital_allocation}
            catalyst={score.catalyst}
            winningTrack={score.winning_track}
            showAllFactors={showData}
          />
        </div>

        {/* Right column (5 cols) */}
        <div className="md:col-span-5 space-y-0">
          {score.filters_passed.length > 0 && (
            <div className="pb-5 mb-5 border-b border-border-primary/20">
              <FilterList filters={score.filters_passed} />
            </div>
          )}

          <div className="pb-5 mb-5 border-b border-border-primary/20">
            <ValuationBreakdown
              methods={score.valuation_methods}
              intrinsicValue={score.intrinsic_value}
              actualPrice={score.actual_price}
              marginOfSafety={score.margin_of_safety}
              invalidReason={score.price_target_invalid_reason}
            />
          </div>

          {/* Metadata */}
          <div className="pb-5 mb-5 border-b border-border-primary/20" data-testid="asset-metadata">
            <h3 className="text-xs font-semibold tracking-wide uppercase text-text-tertiary mb-3">
              Metadata
            </h3>
            <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              {score.growth_stage && (
                <>
                  <dt className="text-xs text-text-tertiary uppercase tracking-wide">
                    Growth Stage
                  </dt>
                  <dd className="text-sm font-mono text-text-primary text-right">
                    {formatAttributeLabel(score.growth_stage)}
                  </dd>
                </>
              )}
              {score.data_coverage !== undefined && (
                <>
                  <dt className="text-xs text-text-tertiary uppercase tracking-wide">
                    Data Coverage
                  </dt>
                  <dd className="text-sm font-mono text-text-primary text-right">
                    {(score.data_coverage * 100).toFixed(0)}%
                  </dd>
                </>
              )}
              {score.scored_at && (
                <>
                  <dt className="text-xs text-text-tertiary uppercase tracking-wide">
                    Scored At
                  </dt>
                  <dd className="text-sm font-mono text-text-primary text-right">
                    {formatScoredAt(score.scored_at)}
                  </dd>
                </>
              )}
            </div>
          </div>

          <SignalTimeline transitions={score.signal_history ?? undefined} />
        </div>
      </motion.div>
    </div>
  )
}
```

**Step 2: Update barrel export**

Check `web/src/components/dashboard/index.ts` — add exports for new components if barrel exists. If it doesn't export AssetDetail specifically, skip this step.

**Step 3: Run tests**

Run: `cd web && npx vitest run`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add web/src/components/dashboard/asset-detail.tsx
git commit -m "feat(web): rewrite asset-detail with 12-col grid, staggered animation, institutional metrics"
```

---

## Task 12: Stock Card Expanded State + CSS Ambient

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Modify: `web/src/app/globals.css`

**Step 1: Update stock-card.tsx expanded styles**

In the card's className, update the expanded-state classes. Find the className string on the outer `<div>` and update the `expanded` conditional:

Replace:
```tsx
${expanded ? "col-span-full" : ""}
```

With:
```tsx
${expanded ? "col-span-full p-8 shadow-[0_4px_24px_rgba(0,0,0,0.15)] border-accent/15" : "p-6"}
```

Ensure the non-expanded state keeps `p-6` by adding it to the else branch.

**Step 2: Add dark-mode ambient gradient**

In `web/src/app/globals.css`, add:

```css
.dark .asset-detail-ambient {
  background: radial-gradient(ellipse at 50% 0%, color-mix(in srgb, var(--accent) 2%, transparent) 0%, transparent 60%);
}
```

Then in `asset-detail.tsx`, add `asset-detail-ambient` to the root div's className (after `border-t`):

```tsx
className={`border-t border-border-primary pt-8 mt-4 asset-detail-ambient ${className}`}
```

**Step 3: Run tests**

Run: `cd web && npx vitest run`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx web/src/app/globals.css web/src/components/dashboard/asset-detail.tsx
git commit -m "feat(web): add expanded card depth, ambient gradient, and CSS chart glow"
```

---

## Task 13: Update Dashboard Barrel Export

**Files:**
- Modify: `web/src/components/dashboard/index.ts`

**Step 1: Add new component exports**

Read the current barrel file and add exports for the new components:

```ts
export { InstitutionalMetrics } from "./institutional-metrics"
export { AiSummary } from "./ai-summary"
export { ProGate } from "./pro-gate"
export { CustomCrosshair } from "./custom-crosshair"
```

**Step 2: Run full test suite**

Run: `cd web && npx vitest run`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add web/src/components/dashboard/index.ts
git commit -m "feat(web): export new dashboard components from barrel"
```

---

## Task 14: Final Verification

**Step 1: Run full test suite**

Run: `cd web && npx vitest run`
Expected: All tests PASS, no regressions

**Step 2: Build check**

Run: `cd web && npx next build`
Expected: Build succeeds with no type errors

**Step 3: Visual verification**

Run: `cd web && npx next dev`
Navigate to dashboard, click a stock card, verify:
- Staggered animation plays
- Chart has gradient underfill and crosshair tooltip
- Institutional metrics grid renders (blurred if free user)
- AI summary renders (blurred if free user)
- Factor breakdown has dividers and upgraded typography
- Right column has section dividers and mono values
- Card shadow deepens on expand
- Chart glow pulse fires once

**Step 4: Final commit (if any visual tweaks needed)**

```bash
git add -A
git commit -m "fix(web): visual polish for candidate detail redesign"
```
