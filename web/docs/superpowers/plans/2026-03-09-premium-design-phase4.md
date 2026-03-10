# Premium Design Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build three visual components — Factor Signature, Hero Instrument Panel, and Dashboard Tiered Layout — to elevate the product from uniform cards to a conviction-weighted visual hierarchy.

**Architecture:** A shared SVG visualization component (`FactorSignature`) with 4 size variants is consumed by both the landing page hero (replacing `SystemReportCard` with `InstrumentPanel`) and the dashboard (replacing `PicksGrid` internals with `TieredPicksList`). All colors use existing design tokens. GSAP animates SVG internals; Framer Motion animates card entrances.

**Tech Stack:** React 19, TypeScript, SVG, GSAP (SVG animation), Framer Motion (card animation), Tailwind v4, Vitest + @testing-library/react

**Spec:** `web/docs/superpowers/specs/2026-03-09-premium-design-phase4-design.md`

**Branch:** `feat/premium-design-phase4` (already created)

---

## File Structure

### New Files
| File | Responsibility |
|------|----------------|
| `src/components/visualizations/factor-signature.tsx` | Shared SVG component — 4 variants (full/compact/mini/inline), GSAP entrance animation, null-factor handling |
| `src/components/visualizations/__tests__/factor-signature.test.tsx` | Unit tests for all variants, null handling, edge cases |
| `src/components/landing/sections/instrument-panel.tsx` | Hero right-column card — replaces `SystemReportCard`, uses FactorSignature full variant |
| `src/components/landing/__tests__/instrument-panel.test.tsx` | Tests for InstrumentPanel rendering, null candidate, tier colors |
| `src/components/dashboard/pick-hero-card.tsx` | Tier-1 dashboard card — full width, FactorSignature compact |
| `src/components/dashboard/pick-medium-card.tsx` | Tier-2 dashboard card — half width, FactorSignature mini |
| `src/components/dashboard/pick-compact-row.tsx` | Tier-3 dashboard row — single line, FactorSignature inline |
| `src/components/dashboard/tiered-picks-list.tsx` | Orchestrator — sorts picks, assigns tiers, renders appropriate card |
| `src/components/dashboard/__tests__/tiered-picks-list.test.tsx` | Tests for tier logic, pick counts 0-6, empty state |
| `src/components/dashboard/__tests__/pick-hero-card.test.tsx` | Tests for hero card rendering |
| `src/components/dashboard/__tests__/pick-medium-card.test.tsx` | Tests for medium card rendering |
| `src/components/dashboard/__tests__/pick-compact-row.test.tsx` | Tests for compact row rendering |

### Modified Files
| File | Change |
|------|--------|
| `src/components/landing/sections/hero-section.tsx` | Import `InstrumentPanel` instead of `SystemReportCard`, adjust `min-height` to `80svh`, widen right column to `max-w-md` |
| `src/components/dashboard/picks-grid.tsx` | Replace internals with `TieredPicksList` (keep export name + props for backward compat) |
| `src/components/dashboard/index.ts` | Add export for `TieredPicksList` |

### Unchanged Files (referenced for context)
| File | Why |
|------|-----|
| `src/components/landing/visualizations/factor-bars.tsx` | Still used by other components, not modified |
| `src/components/dashboard/stock-card.tsx` | Still used on watchlist page, not modified |
| `src/components/landing/shared/types.ts` | `CandidateCard` interface — read-only reference |
| `src/lib/api/types.ts` | `PickSummary` interface — read-only reference |

---

## Chunk 1: Factor Signature Component

### Task 1: Factor Signature — failing tests

**Files:**
- Create: `src/components/visualizations/__tests__/factor-signature.test.tsx`

- [ ] **Step 1: Write the test file with all core test cases**

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// Mock GSAP to prevent animation side effects in tests
vi.mock("gsap", () => ({
  default: {
    set: vi.fn(),
    to: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))

import { FactorSignature } from "../factor-signature"

const FULL_FACTORS = {
  quality: 95,
  value: 68,
  momentum: 84,
  sentiment: 79,
  growth: 88,
}

const NULL_SENTIMENT = {
  quality: 95,
  value: 68,
  momentum: 84,
  sentiment: null,
  growth: 88,
}

const ALL_NULL = {
  quality: null,
  value: null,
  momentum: null,
  sentiment: null,
  growth: null,
}

describe("FactorSignature", () => {
  describe("full variant", () => {
    it("renders 5 track lines", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" />
      )
      const tracks = container.querySelectorAll("[data-track]")
      expect(tracks).toHaveLength(5)
    })

    it("renders full factor labels", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="full" />)
      expect(screen.getByText("QUALITY")).toBeInTheDocument()
      expect(screen.getByText("VALUE")).toBeInTheDocument()
      expect(screen.getByText("MOMENTUM")).toBeInTheDocument()
      expect(screen.getByText("SENTIMENT")).toBeInTheDocument()
      expect(screen.getByText("GROWTH")).toBeInTheDocument()
    })

    it("renders percentile values", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="full" />)
      expect(screen.getByText("95")).toBeInTheDocument()
      expect(screen.getByText("68")).toBeInTheDocument()
    })

    it("renders marker dots for non-null factors", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" />
      )
      const dots = container.querySelectorAll("[data-marker-dot]")
      expect(dots).toHaveLength(5)
    })

    it("renders fill bars for non-null factors", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" />
      )
      const fills = container.querySelectorAll("[data-fill-bar]")
      expect(fills).toHaveLength(5)
    })

    it("renders connecting polyline", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" />
      )
      const polyline = container.querySelector("[data-connecting-line]")
      expect(polyline).toBeInTheDocument()
    })
  })

  describe("compact variant", () => {
    it("renders abbreviated labels", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="compact" />)
      expect(screen.getByText("Q")).toBeInTheDocument()
      expect(screen.getByText("V")).toBeInTheDocument()
      expect(screen.getByText("M")).toBeInTheDocument()
      expect(screen.getByText("S")).toBeInTheDocument()
      expect(screen.getByText("G")).toBeInTheDocument()
    })
  })

  describe("mini variant", () => {
    it("does not render labels", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="mini" />)
      expect(screen.queryByText("QUALITY")).not.toBeInTheDocument()
      expect(screen.queryByText("Q")).not.toBeInTheDocument()
    })

    it("does not render percentile values", () => {
      render(<FactorSignature factors={FULL_FACTORS} variant="mini" />)
      expect(screen.queryByText("95")).not.toBeInTheDocument()
    })

    it("still renders fill bars", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="mini" />
      )
      const fills = container.querySelectorAll("[data-fill-bar]")
      expect(fills).toHaveLength(5)
    })
  })

  describe("inline variant", () => {
    it("renders only dots, no labels or values", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="inline" />
      )
      expect(screen.queryByText("QUALITY")).not.toBeInTheDocument()
      expect(screen.queryByText("95")).not.toBeInTheDocument()
      const dots = container.querySelectorAll("[data-marker-dot]")
      expect(dots).toHaveLength(5)
    })
  })

  describe("null factor handling", () => {
    it("omits marker dot for null factors", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="full" />
      )
      const dots = container.querySelectorAll("[data-marker-dot]")
      expect(dots).toHaveLength(4) // sentiment is null
    })

    it("omits fill bar for null factors", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="full" />
      )
      const fills = container.querySelectorAll("[data-fill-bar]")
      expect(fills).toHaveLength(4)
    })

    it("still renders 5 tracks even with null factors", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="full" />
      )
      const tracks = container.querySelectorAll("[data-track]")
      expect(tracks).toHaveLength(5)
    })

    it("renders polyline with only non-null dots", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="full" />
      )
      const polyline = container.querySelector("[data-connecting-line]")
      expect(polyline).toBeInTheDocument()
    })

    it("renders dimmed ring for null factors in inline variant", () => {
      const { container } = render(
        <FactorSignature factors={NULL_SENTIMENT} variant="inline" />
      )
      const nullDots = container.querySelectorAll("[data-null-dot]")
      expect(nullDots).toHaveLength(1)
    })

    it("handles all-null factors gracefully", () => {
      const { container } = render(
        <FactorSignature factors={ALL_NULL} variant="full" />
      )
      const tracks = container.querySelectorAll("[data-track]")
      expect(tracks).toHaveLength(5)
      const dots = container.querySelectorAll("[data-marker-dot]")
      expect(dots).toHaveLength(0)
      const polyline = container.querySelector("[data-connecting-line]")
      expect(polyline).not.toBeInTheDocument() // no dots to connect
    })
  })

  describe("edge cases", () => {
    it("clamps values at 0", () => {
      const factors = { quality: -5, value: 0, momentum: 0, sentiment: 0, growth: 0 }
      const { container } = render(
        <FactorSignature factors={factors} variant="full" />
      )
      // Should not throw; -5 clamped to 0
      expect(container.querySelector("svg")).toBeInTheDocument()
    })

    it("clamps values at 100", () => {
      const factors = { quality: 150, value: 100, momentum: 100, sentiment: 100, growth: 100 }
      const { container } = render(
        <FactorSignature factors={factors} variant="full" />
      )
      expect(container.querySelector("svg")).toBeInTheDocument()
    })

    it("applies custom className", () => {
      const { container } = render(
        <FactorSignature factors={FULL_FACTORS} variant="full" className="my-custom" />
      )
      expect(container.firstChild).toHaveClass("my-custom")
    })
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/visualizations/__tests__/factor-signature.test.tsx`
Expected: FAIL — `Cannot find module '../factor-signature'`

---

### Task 2: Factor Signature — implementation

**Files:**
- Create: `src/components/visualizations/factor-signature.tsx`

- [ ] **Step 1: Create the FactorSignature component**

```tsx
"use client"

import { useEffect, useRef } from "react"

interface FactorSignatureProps {
  factors: {
    quality: number | null
    value: number | null
    momentum: number | null
    sentiment: number | null
    growth: number | null
  }
  variant: "full" | "compact" | "mini" | "inline"
  className?: string
}

const FACTOR_CONFIG = [
  { key: "quality" as const, label: "QUALITY", abbrev: "Q", color: "#10B981" },
  { key: "value" as const, label: "VALUE", abbrev: "V", color: "#3BA5D0" },
  { key: "momentum" as const, label: "MOMENTUM", abbrev: "M", color: "#1A7A5A" },
  { key: "sentiment" as const, label: "SENTIMENT", abbrev: "S", color: "#C9A84C" },
  { key: "growth" as const, label: "GROWTH", abbrev: "G", color: "#22C55E" },
] as const

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/** Dimensions and visibility per variant */
const VARIANT_SPEC = {
  full:    { width: 340, height: 160, showLabels: "full",   showValues: true,  showFill: true,  trackSpacing: 32 },
  compact: { width: 260, height: 110, showLabels: "abbrev", showValues: true,  showFill: true,  trackSpacing: 22 },
  mini:    { width: 160, height: 50,  showLabels: false,    showValues: false, showFill: true,  trackSpacing: 10 },
  inline:  { width: 80,  height: 10,  showLabels: false,    showValues: false, showFill: false, trackSpacing: 0 },
} as const

export function FactorSignature({ factors, variant, className }: FactorSignatureProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const animatedRef = useRef(false)

  const spec = VARIANT_SPEC[variant]

  // Inline variant: render as a simple row of dots
  if (variant === "inline") {
    return (
      <svg
        ref={svgRef}
        viewBox={`0 0 ${spec.width} ${spec.height}`}
        className={className}
        width={spec.width}
        height={spec.height}
        role="img"
        aria-label="Factor signature"
      >
        {FACTOR_CONFIG.map((factor, i) => {
          const value = factors[factor.key]
          const cx = (i / (FACTOR_CONFIG.length - 1)) * (spec.width - 10) + 5
          const cy = spec.height / 2
          if (value === null || value === undefined) {
            return (
              <circle
                key={factor.key}
                data-null-dot
                cx={cx}
                cy={cy}
                r={3}
                fill="none"
                stroke={factor.color}
                strokeWidth={1}
                opacity={0.15}
              />
            )
          }
          const clamped = clamp(Math.round(value), 0, 100)
          const dotOpacity = clamped >= 80 ? 1 : clamped >= 60 ? 0.7 : clamped >= 40 ? 0.5 : 0.3
          return (
            <circle
              key={factor.key}
              data-marker-dot
              cx={cx}
              cy={cy}
              r={3}
              fill={factor.color}
              opacity={dotOpacity}
            />
          )
        })}
      </svg>
    )
  }

  // Track-based variants (full, compact, mini)
  const labelWidth = spec.showLabels === "full" ? 80 : spec.showLabels === "abbrev" ? 20 : 0
  const valueWidth = spec.showValues ? 30 : 0
  const trackLeft = labelWidth + (labelWidth > 0 ? 8 : 0)
  const trackRight = spec.width - valueWidth - (valueWidth > 0 ? 8 : 0)
  const trackWidth = trackRight - trackLeft
  const topPadding = variant === "mini" ? 5 : 10
  const polylinePoints: string[] = []

  useEffect(() => {
    if (animatedRef.current || !svgRef.current) return
    animatedRef.current = true

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (prefersReduced) return

    async function runAnimation() {
      const gsapModule = await import("gsap")
      const gsap = gsapModule.default
      const svg = svgRef.current
      if (!svg) return

      const dots = svg.querySelectorAll("[data-marker-dot]")
      const fills = svg.querySelectorAll("[data-fill-bar]")
      const line = svg.querySelector("[data-connecting-line]")

      gsap.set(dots, { opacity: 0, scale: 0 })
      gsap.set(fills, { scaleX: 0, transformOrigin: "left center" })
      if (line) gsap.set(line, { opacity: 0 })

      dots.forEach((dot, i) => {
        gsap.to(dot, { opacity: 1, scale: 1, duration: 0.3, delay: i * 0.08, ease: "back.out(2)" })
      })
      fills.forEach((fill, i) => {
        gsap.to(fill, { scaleX: 1, duration: 0.4, delay: i * 0.08, ease: "power2.out" })
      })
      if (line) {
        gsap.to(line, { opacity: 1, duration: 0.3, delay: dots.length * 0.08 + 0.1 })
      }
    }

    runAnimation().catch(() => {})
  }, [])

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${spec.width} ${spec.height}`}
      className={className}
      width={spec.width}
      height={spec.height}
      role="img"
      aria-label="Factor signature"
    >
      {FACTOR_CONFIG.map((factor, i) => {
        const value = factors[factor.key]
        const y = topPadding + i * spec.trackSpacing
        const isNull = value === null || value === undefined
        const clamped = isNull ? 0 : clamp(Math.round(value), 0, 100)
        const dotX = trackLeft + (clamped / 100) * trackWidth

        if (!isNull) {
          polylinePoints.push(`${dotX},${y}`)
        }

        return (
          <g key={factor.key}>
            {/* Track line */}
            <line
              data-track
              x1={trackLeft}
              y1={y}
              x2={trackRight}
              y2={y}
              stroke="rgba(237,233,227,0.06)"
              strokeWidth={1}
            />

            {/* Fill bar */}
            {!isNull && spec.showFill && (
              <rect
                data-fill-bar
                x={trackLeft}
                y={y - 4}
                width={(clamped / 100) * trackWidth}
                height={8}
                rx={1}
                fill={factor.color}
                opacity={0.12}
              />
            )}

            {/* Marker dot */}
            {!isNull && (
              <circle
                data-marker-dot
                cx={dotX}
                cy={y}
                r={variant === "mini" ? 2.5 : 3.5}
                fill={factor.color}
              />
            )}

            {/* Label */}
            {spec.showLabels && (
              <text
                x={0}
                y={y}
                dy="0.35em"
                fill="rgba(237,233,227,0.35)"
                fontSize={spec.showLabels === "full" ? 9 : 9}
                fontFamily="var(--font-geist-mono), monospace"
              >
                {spec.showLabels === "full" ? factor.label : factor.abbrev}
              </text>
            )}

            {/* Percentile value */}
            {spec.showValues && !isNull && (
              <text
                x={spec.width}
                y={y}
                dy="0.35em"
                textAnchor="end"
                fill="rgba(237,233,227,0.5)"
                fontSize={10}
                fontFamily="var(--font-geist-mono), monospace"
              >
                {clamped}
              </text>
            )}
          </g>
        )
      })}

      {/* Connecting polyline */}
      {polylinePoints.length >= 2 && (
        <polyline
          data-connecting-line
          points={polylinePoints.join(" ")}
          fill="none"
          stroke="rgba(237,233,227,0.12)"
          strokeWidth={1.5}
        />
      )}
    </svg>
  )
}
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/visualizations/__tests__/factor-signature.test.tsx`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/components/visualizations/factor-signature.tsx src/components/visualizations/__tests__/factor-signature.test.tsx
git commit -m "feat: add FactorSignature SVG component with 4 size variants"
```

---

## Chunk 2: Hero Instrument Panel

### Task 3: Instrument Panel — failing tests

**Files:**
- Create: `src/components/landing/__tests__/instrument-panel.test.tsx`

- [ ] **Step 1: Write the test file**

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    set: vi.fn(),
    to: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))

import { InstrumentPanel } from "../sections/instrument-panel"
import type { CandidateCard } from "../shared/types"

const MOCK_CANDIDATE: CandidateCard = {
  ticker: "AAPL",
  name: "Apple Inc.",
  sector: "Technology",
  actual_price: 178.5,
  buy_price: 155.0,
  margin_of_safety: 0.15,
  score: 82,
  composite_percentile: 85,
  composite_tier: "exceptional",
  quality_percentile: 95,
  value_percentile: 68,
  momentum_percentile: 84,
  sentiment_percentile: 79,
  growth_percentile: 88,
  scored_at: new Date().toISOString(),
  filters_passed: 8,
  filters_total: 8,
}

describe("InstrumentPanel", () => {
  it("renders ticker and company name", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders composite score", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText("82")).toBeInTheDocument()
  })

  it("renders Live Score header with ticker", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText(/live score/i)).toBeInTheDocument()
  })

  it("renders sector when present", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText("Technology")).toBeInTheDocument()
  })

  it("omits sector when null", () => {
    const noSector = { ...MOCK_CANDIDATE, sector: null as unknown as string }
    render(<InstrumentPanel candidate={noSector} />)
    // Score should still render
    expect(screen.getByText("82")).toBeInTheDocument()
  })

  it("renders status dot", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByTestId("status-dot")).toBeInTheDocument()
  })

  it("renders tier badge", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    expect(screen.getByText(/exceptional/i)).toBeInTheDocument()
  })

  it("renders empty state when candidate is null", () => {
    render(<InstrumentPanel candidate={null} />)
    expect(screen.getByText("—")).toBeInTheDocument()
  })

  it("renders relative timestamp", () => {
    render(<InstrumentPanel candidate={MOCK_CANDIDATE} />)
    // The scored_at is just now, so we should see "just now" or similar
    expect(screen.getByText(/scored|just now|ago/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/instrument-panel.test.tsx`
Expected: FAIL — `Cannot find module '../sections/instrument-panel'`

---

### Task 4: Instrument Panel — implementation

**Files:**
- Create: `src/components/landing/sections/instrument-panel.tsx`

- [ ] **Step 1: Create the InstrumentPanel component**

This component replaces `SystemReportCard`. It reuses the `getTierColor` and `formatRelativeTime` utilities from the original (copy them into the new file — they're small helper functions, not worth extracting to a shared module for two usages).

```tsx
import { FactorSignature } from "@/components/visualizations/factor-signature"
import type { CandidateCard } from "../shared/types"

interface InstrumentPanelProps {
  candidate: CandidateCard | null
}

function getTierColor(tier: string): string {
  switch (tier) {
    case "exceptional":
      return "var(--color-percentile-exceptional)"
    case "high":
      return "var(--color-percentile-strong)"
    case "medium":
      return "var(--color-percentile-average)"
    case "low":
    case "below":
      return "var(--color-percentile-below)"
    case "none":
    case "weak":
      return "var(--color-percentile-weak)"
    default:
      return "var(--color-text-primary)"
  }
}

function formatRelativeTime(isoString: string): string {
  const scored = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - scored.getTime()
  if (diffMs < 0) return "just now"
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function InstrumentPanel({ candidate }: InstrumentPanelProps) {
  const hasCand = candidate !== null

  return (
    <div
      data-hero-card
      className="terminal-card w-full max-w-md transition-shadow duration-300 hover:shadow-[0_0_60px_rgba(26,122,90,0.15)]"
      style={{
        boxShadow: "0 0 40px rgba(26,122,90,0.08)",
        borderColor: "rgba(26,122,90,0.2)",
      }}
    >
      {/* Header strip */}
      <div
        className="flex items-center gap-2 px-5 py-3"
        style={{ borderBottom: "1px solid var(--color-border-subtle)" }}
      >
        <span
          className="inline-block w-2 h-2 rounded-full shrink-0"
          data-testid="status-dot"
          style={{
            backgroundColor: hasCand
              ? "var(--color-bullish)"
              : "var(--color-text-tertiary)",
          }}
        />
        <span className="text-mono-label text-text-tertiary">
          {hasCand ? `Live Score — ${candidate.ticker}` : "Live Score"}
        </span>
        {hasCand && (
          <span className="text-mono-label text-text-tertiary ml-auto text-[10px]">
            {formatRelativeTime(candidate.scored_at)}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="px-5 py-5">
        {/* Score + ticker header */}
        <div className="flex items-start justify-between mb-1">
          <div>
            <span
              className="font-mono text-[42px] font-bold leading-none tracking-tight inline-block"
              style={{
                color: hasCand
                  ? getTierColor(candidate.composite_tier)
                  : "var(--color-text-tertiary)",
              }}
            >
              {hasCand ? Math.round(candidate.score) : "—"}
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-title-1 text-text-primary">
                {hasCand ? candidate.ticker : "—"}
              </span>
              <span className="text-caption text-text-secondary truncate max-w-[140px]">
                {hasCand ? candidate.name : ""}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              {hasCand && candidate.sector && (
                <span className="text-caption text-text-tertiary">
                  {candidate.sector}
                </span>
              )}
              {hasCand && (
                <span
                  className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded"
                  style={{
                    color: getTierColor(candidate.composite_tier),
                    backgroundColor: `color-mix(in srgb, ${getTierColor(candidate.composite_tier)} 12%, transparent)`,
                  }}
                >
                  {candidate.composite_tier}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Factor Signature */}
        <div className="mt-4">
          {hasCand ? (
            <FactorSignature
              factors={{
                quality: candidate.quality_percentile,
                value: candidate.value_percentile,
                momentum: candidate.momentum_percentile,
                sentiment: candidate.sentiment_percentile,
                growth: candidate.growth_percentile,
              }}
              variant="full"
            />
          ) : (
            <div className="h-[160px] flex items-center justify-center">
              <span className="text-caption text-text-tertiary">
                No data available
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/__tests__/instrument-panel.test.tsx`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/components/landing/sections/instrument-panel.tsx src/components/landing/__tests__/instrument-panel.test.tsx
git commit -m "feat: add InstrumentPanel component replacing SystemReportCard"
```

---

### Task 5: Wire InstrumentPanel into hero section

**Files:**
- Modify: `src/components/landing/sections/hero-section.tsx`
- Modify: `src/components/landing/sections/__tests__/hero-section.test.tsx`
- Delete: `src/components/landing/sections/system-report-card.tsx`
- Delete: `src/components/landing/sections/__tests__/system-report-card.test.tsx`

- [ ] **Step 1: Update the import and layout in hero-section.tsx**

In `hero-section.tsx`, make these changes:

1. Replace the `SystemReportCard` import with `InstrumentPanel`:
```tsx
// OLD:
import { SystemReportCard } from "./system-report-card"
// NEW:
import { InstrumentPanel } from "./instrument-panel"
```

2. Replace the usage in the JSX (around line 129):
```tsx
// OLD:
<SystemReportCard candidate={topCandidate} />
// NEW:
<InstrumentPanel candidate={topCandidate} />
```

3. Change `min-height` from `90svh` to `80svh` (line 76):
```tsx
// OLD:
minHeight: "90svh",
// NEW:
minHeight: "80svh",
```

- [ ] **Step 2: Update hero-section.test.tsx**

Three tests reference `SystemReportCard` behavior and the old min-height. Update them:

```tsx
// OLD (line 81-85):
it("renders SystemReportCard with top candidate", () => {
  render(<HeroSection data={mockData} />)
  expect(screen.getByText("SYSTEM REPORT")).toBeInTheDocument()
  expect(screen.getByText("AAPL")).toBeInTheDocument()
})
// NEW:
it("renders InstrumentPanel with top candidate", () => {
  render(<HeroSection data={mockData} />)
  expect(screen.getByText(/live score/i)).toBeInTheDocument()
  expect(screen.getByText("AAPL")).toBeInTheDocument()
})

// OLD (line 87-91):
it("renders SystemReportCard in placeholder mode when data is null", () => {
  render(<HeroSection data={null} />)
  expect(screen.getByText("SYSTEM REPORT")).toBeInTheDocument()
  expect(screen.getByText("No data available")).toBeInTheDocument()
})
// NEW:
it("renders InstrumentPanel in placeholder mode when data is null", () => {
  render(<HeroSection data={null} />)
  expect(screen.getByText(/live score/i)).toBeInTheDocument()
  expect(screen.getByText("No data available")).toBeInTheDocument()
})

// OLD (line 93-97):
it("uses 90svh min-height (Authority Strip peek)", () => {
  const { container } = render(<HeroSection data={mockData} />)
  const section = container.querySelector("#hero")
  expect(section).toHaveStyle({ minHeight: "90svh" })
})
// NEW:
it("uses 80svh min-height", () => {
  const { container } = render(<HeroSection data={mockData} />)
  const section = container.querySelector("#hero")
  expect(section).toHaveStyle({ minHeight: "80svh" })
})
```

- [ ] **Step 3: Delete old SystemReportCard files**

```bash
rm src/components/landing/sections/system-report-card.tsx
rm src/components/landing/sections/__tests__/system-report-card.test.tsx
```

The `SystemReportCard` is fully replaced by `InstrumentPanel`. The `FactorBars` component it consumed is still used elsewhere and is not deleted.

- [ ] **Step 4: Run landing test suite**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/landing/`
Expected: All tests PASS (hero-section tests updated, system-report-card tests removed)

- [ ] **Step 5: Commit**

```bash
git add src/components/landing/sections/hero-section.tsx src/components/landing/sections/__tests__/hero-section.test.tsx
git rm src/components/landing/sections/system-report-card.tsx src/components/landing/sections/__tests__/system-report-card.test.tsx
git commit -m "feat: wire InstrumentPanel into hero, remove SystemReportCard"
```

---

## Chunk 3: Dashboard Tiered Layout

### Task 6: Pick card components — failing tests

**Files:**
- Create: `src/components/dashboard/__tests__/pick-hero-card.test.tsx`
- Create: `src/components/dashboard/__tests__/pick-medium-card.test.tsx`
- Create: `src/components/dashboard/__tests__/pick-compact-row.test.tsx`

- [ ] **Step 1: Write test fixtures (shared mock data)**

Create test files with this shared mock at the top of each:

```tsx
import type { PickSummary } from "@/lib/api/types"

const MOCK_PICK: PickSummary = {
  score_id: 1,
  ticker: "NVDA",
  name: "NVIDIA Corporation",
  score: 91,
  universe_percentile: 98,
  composite_percentile: 95,
  composite_tier: "exceptional",
  signal: "strong",
  quality_percentile: 92,
  value_percentile: 65,
  momentum_percentile: 88,
  sentiment_percentile: 75,
  growth_percentile: 94,
  actual_price: 890.5,
  buy_price: 750.0,
  sell_price: 1050.0,
  price_upside: 0.18,
  sector: "Technology",
}
```

- [ ] **Step 2: Write pick-hero-card.test.tsx**

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { set: vi.fn(), to: vi.fn(), timeline: vi.fn(() => ({ to: vi.fn().mockReturnThis(), play: vi.fn(), kill: vi.fn() })) },
}))

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}))

import { PickHeroCard } from "../pick-hero-card"
import type { PickSummary } from "@/lib/api/types"

const MOCK_PICK: PickSummary = {
  score_id: 1, ticker: "NVDA", name: "NVIDIA Corporation", score: 91,
  universe_percentile: 98, composite_percentile: 95, composite_tier: "exceptional",
  signal: "strong", quality_percentile: 92, value_percentile: 65,
  momentum_percentile: 88, sentiment_percentile: 75, growth_percentile: 94,
  actual_price: 890.5, buy_price: 750.0, sell_price: 1050.0, price_upside: 0.18,
  sector: "Technology",
}

describe("PickHeroCard", () => {
  it("renders ticker and company name", () => {
    render(<PickHeroCard pick={MOCK_PICK} rank={1} />)
    expect(screen.getByText("NVDA")).toBeInTheDocument()
    expect(screen.getByText("NVIDIA Corporation")).toBeInTheDocument()
  })

  it("renders score with large font", () => {
    render(<PickHeroCard pick={MOCK_PICK} rank={1} />)
    expect(screen.getByText("91")).toBeInTheDocument()
  })

  it("renders rank badge", () => {
    render(<PickHeroCard pick={MOCK_PICK} rank={1} />)
    expect(screen.getByText("#1")).toBeInTheDocument()
  })

  it("renders sector", () => {
    render(<PickHeroCard pick={MOCK_PICK} rank={1} />)
    expect(screen.getByText("Technology")).toBeInTheDocument()
  })

  it("omits sector when null", () => {
    render(<PickHeroCard pick={{ ...MOCK_PICK, sector: null }} rank={1} />)
    expect(screen.queryByText("Technology")).not.toBeInTheDocument()
  })

  it("renders Full report link", () => {
    render(<PickHeroCard pick={MOCK_PICK} rank={1} />)
    const link = screen.getByText(/full report/i)
    expect(link).toBeInTheDocument()
    expect(link.closest("a")).toHaveAttribute("href", "/asset/NVDA")
  })

  it("renders price", () => {
    render(<PickHeroCard pick={MOCK_PICK} rank={1} />)
    expect(screen.getByText("$890.50")).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: Write pick-medium-card.test.tsx**

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { set: vi.fn(), to: vi.fn(), timeline: vi.fn(() => ({ to: vi.fn().mockReturnThis(), play: vi.fn(), kill: vi.fn() })) },
}))

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}))

import { PickMediumCard } from "../pick-medium-card"
import type { PickSummary } from "@/lib/api/types"

const MOCK_PICK: PickSummary = {
  score_id: 2, ticker: "MSFT", name: "Microsoft Corp", score: 78,
  universe_percentile: 88, composite_percentile: 82, composite_tier: "high",
  signal: "strong", quality_percentile: 85, value_percentile: 72,
  momentum_percentile: 70, sentiment_percentile: null, growth_percentile: 80,
  actual_price: 415.0, buy_price: 380.0, sell_price: 480.0, price_upside: 0.16,
}

describe("PickMediumCard", () => {
  it("renders ticker", () => {
    render(<PickMediumCard pick={MOCK_PICK} rank={2} />)
    expect(screen.getByText("MSFT")).toBeInTheDocument()
  })

  it("renders rank", () => {
    render(<PickMediumCard pick={MOCK_PICK} rank={2} />)
    expect(screen.getByText("#2")).toBeInTheDocument()
  })

  it("renders score", () => {
    render(<PickMediumCard pick={MOCK_PICK} rank={2} />)
    expect(screen.getByText("78")).toBeInTheDocument()
  })

  it("renders tier badge", () => {
    render(<PickMediumCard pick={MOCK_PICK} rank={2} />)
    expect(screen.getByText(/high/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Write pick-compact-row.test.tsx**

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { set: vi.fn(), to: vi.fn(), timeline: vi.fn(() => ({ to: vi.fn().mockReturnThis(), play: vi.fn(), kill: vi.fn() })) },
}))

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}))

import { PickCompactRow } from "../pick-compact-row"
import type { PickSummary } from "@/lib/api/types"

const MOCK_PICK: PickSummary = {
  score_id: 4, ticker: "GOOG", name: "Alphabet Inc.", score: 72,
  universe_percentile: 80, composite_percentile: 75, composite_tier: "high",
  signal: "stable", quality_percentile: 78, value_percentile: 60,
  momentum_percentile: 65, sentiment_percentile: 55, growth_percentile: 70,
  actual_price: 175.0, buy_price: 160.0, sell_price: 200.0, price_upside: 0.14,
}

describe("PickCompactRow", () => {
  it("renders ticker", () => {
    render(<PickCompactRow pick={MOCK_PICK} rank={4} />)
    expect(screen.getByText("GOOG")).toBeInTheDocument()
  })

  it("renders company name", () => {
    render(<PickCompactRow pick={MOCK_PICK} rank={4} />)
    expect(screen.getByText("Alphabet Inc.")).toBeInTheDocument()
  })

  it("renders score", () => {
    render(<PickCompactRow pick={MOCK_PICK} rank={4} />)
    expect(screen.getByText("72")).toBeInTheDocument()
  })

  it("renders tier badge", () => {
    render(<PickCompactRow pick={MOCK_PICK} rank={4} />)
    expect(screen.getByText(/high/i)).toBeInTheDocument()
  })

  it("renders inline factor dots", () => {
    const { container } = render(<PickCompactRow pick={MOCK_PICK} rank={4} />)
    const dots = container.querySelectorAll("[data-marker-dot]")
    expect(dots.length).toBeGreaterThanOrEqual(5)
  })
})
```

- [ ] **Step 5: Run all three test files to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/dashboard/__tests__/pick-hero-card.test.tsx src/components/dashboard/__tests__/pick-medium-card.test.tsx src/components/dashboard/__tests__/pick-compact-row.test.tsx`
Expected: FAIL — `Cannot find module` for each

---

### Task 7: Pick card components — implementation

**Files:**
- Create: `src/components/dashboard/pick-hero-card.tsx`
- Create: `src/components/dashboard/pick-medium-card.tsx`
- Create: `src/components/dashboard/pick-compact-row.tsx`

- [ ] **Step 1: Create PickHeroCard**

```tsx
"use client"

import Link from "next/link"
import { FactorSignature } from "@/components/visualizations/factor-signature"
import { ConvictionBadge } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

function getTierColor(tier: string): string {
  switch (tier) {
    case "exceptional": return "var(--color-percentile-exceptional)"
    case "high": return "var(--color-percentile-strong)"
    case "medium": return "var(--color-percentile-average)"
    case "low": case "below": return "var(--color-percentile-below)"
    default: return "var(--color-text-primary)"
  }
}

interface PickHeroCardProps {
  pick: PickSummary
  rank: number
}

export function PickHeroCard({ pick, rank }: PickHeroCardProps) {
  return (
    <div
      className="relative bg-bg-elevated rounded-xl p-6"
      style={{
        border: "1px solid rgba(26,122,90,0.2)",
        boxShadow: "0 0 30px rgba(26,122,90,0.06)",
      }}
      data-testid={`pick-hero-${pick.ticker}`}
    >
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-6 items-center">
        {/* Left: Score + Info */}
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span
              className="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-bold"
              style={{
                background: "var(--color-accent)",
                color: "var(--color-bg-primary)",
              }}
            >
              #{rank}
            </span>
            <h3 className="text-xl font-bold text-text-primary">{pick.ticker}</h3>
            <ConvictionBadge level={pick.composite_tier} />
          </div>

          <p className="text-sm text-text-secondary mb-1">{pick.name}</p>
          {pick.sector && (
            <span className="text-caption text-text-tertiary">{pick.sector}</span>
          )}

          <div className="mt-3">
            <span
              className="font-mono text-[42px] font-bold leading-none tracking-tight"
              style={{ color: getTierColor(pick.composite_tier) }}
            >
              {Math.round(pick.score)}
            </span>
          </div>

          <div className="flex items-center gap-4 mt-3 text-sm">
            {pick.actual_price != null && (
              <span className="text-text-secondary">
                Price: <span className="text-text-primary font-medium">${pick.actual_price.toFixed(2)}</span>
              </span>
            )}
            <Link
              href={`/asset/${pick.ticker}`}
              className="text-xs text-accent hover:text-accent/80 transition-colors"
            >
              Full report &rarr;
            </Link>
          </div>
        </div>

        {/* Right: Factor Signature compact */}
        <div className="flex-shrink-0">
          <FactorSignature
            factors={{
              quality: pick.quality_percentile,
              value: pick.value_percentile,
              momentum: pick.momentum_percentile,
              sentiment: pick.sentiment_percentile ?? null,
              growth: pick.growth_percentile ?? null,
            }}
            variant="compact"
          />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create PickMediumCard**

```tsx
"use client"

import Link from "next/link"
import { FactorSignature } from "@/components/visualizations/factor-signature"
import { ConvictionBadge } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

function getTierColor(tier: string): string {
  switch (tier) {
    case "exceptional": return "var(--color-percentile-exceptional)"
    case "high": return "var(--color-percentile-strong)"
    case "medium": return "var(--color-percentile-average)"
    case "low": case "below": return "var(--color-percentile-below)"
    default: return "var(--color-text-primary)"
  }
}

interface PickMediumCardProps {
  pick: PickSummary
  rank: number
}

export function PickMediumCard({ pick, rank }: PickMediumCardProps) {
  return (
    <Link
      href={`/asset/${pick.ticker}`}
      className="block bg-bg-elevated rounded-xl p-5 transition-all duration-200 hover:border-[var(--color-accent-medium)]"
      style={{ border: "1px solid rgba(237,233,227,0.06)" }}
      data-testid={`pick-medium-${pick.ticker}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-tertiary font-mono">#{rank}</span>
          <h3 className="text-lg font-bold text-text-primary">{pick.ticker}</h3>
        </div>
        <ConvictionBadge level={pick.composite_tier} />
      </div>

      <div className="mb-3">
        <span
          className="font-mono text-[28px] font-bold leading-none tracking-tight"
          style={{ color: getTierColor(pick.composite_tier) }}
        >
          {Math.round(pick.score)}
        </span>
      </div>

      <FactorSignature
        factors={{
          quality: pick.quality_percentile,
          value: pick.value_percentile,
          momentum: pick.momentum_percentile,
          sentiment: pick.sentiment_percentile ?? null,
          growth: pick.growth_percentile ?? null,
        }}
        variant="mini"
      />
    </Link>
  )
}
```

- [ ] **Step 3: Create PickCompactRow**

```tsx
"use client"

import Link from "next/link"
import { FactorSignature } from "@/components/visualizations/factor-signature"
import { ConvictionBadge } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

function getTierColor(tier: string): string {
  switch (tier) {
    case "exceptional": return "var(--color-percentile-exceptional)"
    case "high": return "var(--color-percentile-strong)"
    case "medium": return "var(--color-percentile-average)"
    case "low": case "below": return "var(--color-percentile-below)"
    default: return "var(--color-text-primary)"
  }
}

interface PickCompactRowProps {
  pick: PickSummary
  rank: number
}

export function PickCompactRow({ pick, rank }: PickCompactRowProps) {
  return (
    <Link
      href={`/asset/${pick.ticker}`}
      className="flex items-center gap-4 px-4 py-3 rounded-lg bg-bg-elevated transition-colors duration-150 hover:bg-bg-subtle"
      style={{ border: "1px solid rgba(237,233,227,0.04)" }}
      data-testid={`pick-compact-${pick.ticker}`}
    >
      <span
        className="font-mono text-[20px] font-bold w-10 text-right tabular-nums"
        style={{ color: getTierColor(pick.composite_tier) }}
      >
        {Math.round(pick.score)}
      </span>

      <span className="font-bold text-text-primary w-16">{pick.ticker}</span>

      <span className="text-sm text-text-secondary truncate flex-1 min-w-0">
        {pick.name}
      </span>

      <FactorSignature
        factors={{
          quality: pick.quality_percentile,
          value: pick.value_percentile,
          momentum: pick.momentum_percentile,
          sentiment: pick.sentiment_percentile ?? null,
          growth: pick.growth_percentile ?? null,
        }}
        variant="inline"
      />

      <ConvictionBadge level={pick.composite_tier} />
    </Link>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/dashboard/__tests__/pick-hero-card.test.tsx src/components/dashboard/__tests__/pick-medium-card.test.tsx src/components/dashboard/__tests__/pick-compact-row.test.tsx`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/components/dashboard/pick-hero-card.tsx src/components/dashboard/pick-medium-card.tsx src/components/dashboard/pick-compact-row.tsx src/components/dashboard/__tests__/pick-hero-card.test.tsx src/components/dashboard/__tests__/pick-medium-card.test.tsx src/components/dashboard/__tests__/pick-compact-row.test.tsx
git commit -m "feat: add tiered pick card components (hero, medium, compact)"
```

---

### Task 8: TieredPicksList — failing tests

**Files:**
- Create: `src/components/dashboard/__tests__/tiered-picks-list.test.tsx`

- [ ] **Step 1: Write the test file**

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { set: vi.fn(), to: vi.fn(), timeline: vi.fn(() => ({ to: vi.fn().mockReturnThis(), play: vi.fn(), kill: vi.fn() })) },
}))

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}))

// Mock EmptyState
vi.mock("@/components/ui", () => ({
  EmptyState: ({ title, description }: { title: string; description?: string }) => (
    <div><h3>{title}</h3>{description && <p>{description}</p>}</div>
  ),
  ConvictionBadge: ({ level }: { level: string }) => <span>{level}</span>,
}))

import { TieredPicksList } from "../tiered-picks-list"
import type { PickSummary } from "@/lib/api/types"

function makePick(ticker: string, score: number, overrides?: Partial<PickSummary>): PickSummary {
  return {
    score_id: Math.random(),
    ticker,
    name: `${ticker} Corp`,
    score,
    universe_percentile: score,
    composite_percentile: score,
    composite_tier: score >= 80 ? "exceptional" : score >= 60 ? "high" : "medium",
    signal: "strong",
    quality_percentile: score,
    value_percentile: score - 10,
    momentum_percentile: score - 5,
    sentiment_percentile: score - 15,
    growth_percentile: score - 3,
    actual_price: 100,
    buy_price: 90,
    sell_price: 120,
    price_upside: 0.2,
    ...overrides,
  }
}

describe("TieredPicksList", () => {
  it("renders empty state with 0 picks", () => {
    render(<TieredPicksList picks={[]} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
  })

  it("renders empty state with stats when universe data provided", () => {
    render(<TieredPicksList picks={[]} totalScored={500} universeSize={2000} />)
    expect(screen.getByText(/500/)).toBeInTheDocument()
  })

  it("renders hero card for single pick", () => {
    render(<TieredPicksList picks={[makePick("AAPL", 90)]} />)
    expect(screen.getByTestId("pick-hero-AAPL")).toBeInTheDocument()
  })

  it("renders hero + medium for 2 picks", () => {
    render(<TieredPicksList picks={[makePick("AAPL", 90), makePick("MSFT", 85)]} />)
    expect(screen.getByTestId("pick-hero-AAPL")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-MSFT")).toBeInTheDocument()
  })

  it("renders hero + 2 medium for 3 picks", () => {
    const picks = [makePick("AAPL", 90), makePick("MSFT", 85), makePick("GOOG", 80)]
    render(<TieredPicksList picks={picks} />)
    expect(screen.getByTestId("pick-hero-AAPL")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-MSFT")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-GOOG")).toBeInTheDocument()
  })

  it("renders hero + 2 medium + compact for 5 picks", () => {
    const picks = [
      makePick("AAPL", 90), makePick("MSFT", 85), makePick("GOOG", 80),
      makePick("AMZN", 75), makePick("META", 70),
    ]
    render(<TieredPicksList picks={picks} />)
    expect(screen.getByTestId("pick-hero-AAPL")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-MSFT")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-GOOG")).toBeInTheDocument()
    expect(screen.getByTestId("pick-compact-AMZN")).toBeInTheDocument()
    expect(screen.getByTestId("pick-compact-META")).toBeInTheDocument()
  })

  it("sorts picks by composite_percentile descending", () => {
    const picks = [makePick("LOW", 60), makePick("HIGH", 95)]
    render(<TieredPicksList picks={picks} />)
    // HIGH should be hero (rank 1), LOW should be medium (rank 2)
    expect(screen.getByTestId("pick-hero-HIGH")).toBeInTheDocument()
    expect(screen.getByTestId("pick-medium-LOW")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/dashboard/__tests__/tiered-picks-list.test.tsx`
Expected: FAIL — `Cannot find module '../tiered-picks-list'`

---

### Task 9: TieredPicksList — implementation

**Files:**
- Create: `src/components/dashboard/tiered-picks-list.tsx`

- [ ] **Step 1: Create the TieredPicksList component**

```tsx
"use client"

import { motion } from "framer-motion"
import { PickHeroCard } from "./pick-hero-card"
import { PickMediumCard } from "./pick-medium-card"
import { PickCompactRow } from "./pick-compact-row"
import { EmptyState } from "@/components/ui"
import type { PickSummary } from "@/lib/api/types"

const cardVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] as const },
  }),
}

function getTier(index: number): "hero" | "medium" | "compact" {
  if (index === 0) return "hero"
  if (index <= 2) return "medium"
  return "compact"
}

interface TieredPicksListProps {
  picks: PickSummary[]
  className?: string
  totalScored?: number
  universeSize?: number
}

export function TieredPicksList({ picks, className = "", totalScored, universeSize }: TieredPicksListProps) {
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
            ? `${totalScored.toLocaleString()} of ${universeSize.toLocaleString()} equities were scored. None met the scoring threshold. When high-scoring opportunities emerge, they'll appear here.`
            : "It found nothing worth your capital right now. When high-scoring opportunities emerge, they'll appear here."
        }
        className={className}
      />
    )
  }

  const heroPick = sorted[0]
  const mediumPicks = sorted.slice(1, 3)
  const compactPicks = sorted.slice(3)

  return (
    <div className={`space-y-4 ${className}`} data-testid="tiered-picks-list">
      {/* Tier 1: Hero */}
      <motion.div
        custom={0}
        initial="hidden"
        animate="visible"
        variants={cardVariants}
      >
        <PickHeroCard pick={heroPick} rank={1} />
      </motion.div>

      {/* Tier 2: Medium cards */}
      {mediumPicks.length > 0 && (
        <div className={mediumPicks.length === 1 ? "max-w-lg" : "grid grid-cols-1 md:grid-cols-2 gap-4"}>
          {mediumPicks.map((pick, i) => (
            <motion.div
              key={pick.ticker}
              custom={i + 1}
              initial="hidden"
              animate="visible"
              variants={cardVariants}
            >
              <PickMediumCard pick={pick} rank={i + 2} />
            </motion.div>
          ))}
        </div>
      )}

      {/* Tier 3: Compact rows */}
      {compactPicks.length > 0 && (
        <div className="space-y-0.5">
          {compactPicks.map((pick, i) => (
            <motion.div
              key={pick.ticker}
              custom={i + 3}
              initial="hidden"
              animate="visible"
              variants={cardVariants}
            >
              <PickCompactRow pick={pick} rank={i + 4} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/dashboard/__tests__/tiered-picks-list.test.tsx`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/components/dashboard/tiered-picks-list.tsx src/components/dashboard/__tests__/tiered-picks-list.test.tsx
git commit -m "feat: add TieredPicksList orchestrator component"
```

---

### Task 10: Wire TieredPicksList into PicksGrid

**Files:**
- Modify: `src/components/dashboard/picks-grid.tsx`
- Modify: `src/components/dashboard/index.ts`

- [ ] **Step 1: Replace PicksGrid internals with TieredPicksList**

Replace the content of `picks-grid.tsx` with a thin wrapper:

```tsx
"use client"

import { TieredPicksList } from "./tiered-picks-list"
import type { PickSummary } from "@/lib/api/types"

interface PicksGridProps {
  picks: PickSummary[]
  className?: string
  totalScored?: number
  universeSize?: number
}

export function PicksGrid({ picks, className, totalScored, universeSize }: PicksGridProps) {
  return (
    <TieredPicksList
      picks={picks}
      className={className}
      totalScored={totalScored}
      universeSize={universeSize}
    />
  )
}
```

- [ ] **Step 2: Add TieredPicksList to dashboard index**

Add this line to `src/components/dashboard/index.ts`:
```tsx
export { TieredPicksList } from "./tiered-picks-list"
```

- [ ] **Step 3: Update existing picks-grid tests**

The existing `picks-grid.test.tsx` tests for empty state behavior. Since `PicksGrid` is now a thin wrapper around `TieredPicksList`, update the mocks:

Read the current test file first. The key tests ("renders purposeful empty state", "shows elimination stats") should still pass since `TieredPicksList` preserves the same `EmptyState` behavior. The `StockCard` mock is no longer needed (now needs mocks for the new pick card components instead).

Replace `src/components/dashboard/__tests__/picks-grid.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: { set: vi.fn(), to: vi.fn(), timeline: vi.fn(() => ({ to: vi.fn().mockReturnThis(), play: vi.fn(), kill: vi.fn() })) },
}))

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}))

vi.mock("@/components/ui", () => ({
  EmptyState: ({ title, description, className }: { title: string; description?: string; className?: string }) => (
    <div className={className}><h3>{title}</h3>{description && <p>{description}</p>}</div>
  ),
  ConvictionBadge: ({ level }: { level: string }) => <span>{level}</span>,
}))

import { PicksGrid } from "../picks-grid"

describe("PicksGrid", () => {
  it("renders purposeful empty state when no picks", () => {
    render(<PicksGrid picks={[]} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
    expect(screen.getByText(/nothing worth your capital/i)).toBeInTheDocument()
  })

  it("shows elimination stats when universe data provided and no picks", () => {
    render(<PicksGrid picks={[]} totalScored={847} universeSize={2847} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
    expect(screen.getByText(/847/)).toBeInTheDocument()
    expect(screen.getByText(/2,847/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Run the full dashboard test suite**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run src/components/dashboard/__tests__/`
Expected: All tests PASS

- [ ] **Step 5: Run the full web test suite**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All ~1370+ tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/components/dashboard/picks-grid.tsx src/components/dashboard/index.ts src/components/dashboard/__tests__/picks-grid.test.tsx
git commit -m "feat: wire TieredPicksList into PicksGrid, preserve backward compat"
```

---

## Chunk 4: Final Verification & Cleanup

### Task 11: Lint + full test pass

- [ ] **Step 1: Run ESLint**

Run: `cd /Users/brandon/repos/margin_invest/web && npx eslint --fix src/components/visualizations/ src/components/dashboard/pick-hero-card.tsx src/components/dashboard/pick-medium-card.tsx src/components/dashboard/pick-compact-row.tsx src/components/dashboard/tiered-picks-list.tsx src/components/landing/sections/instrument-panel.tsx src/components/landing/sections/hero-section.tsx`
Expected: Clean (0 errors, 0 warnings) or auto-fixed

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All tests PASS

- [ ] **Step 3: Visual verification prompt**

Show the user the landing page and dashboard in the browser so they can visually approve the changes before merging. Use the development server:

Run: `cd /Users/brandon/repos/margin_invest/web && npm run dev`

Navigate to `http://localhost:3000` (landing page) and `http://localhost:3000/dashboard` (dashboard).

- [ ] **Step 4: Final commit if any lint fixes were applied**

```bash
git add -A && git commit -m "chore: lint fixes for phase 4 components"
```
