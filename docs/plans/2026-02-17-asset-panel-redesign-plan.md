# Asset Panel Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the inline asset-detail expansion with a premium 70vw slide-over panel featuring a split dashboard layout, composite score hero chart, structured AI insight cards, and institutional KPI grid.

**Architecture:** A React Portal-based slide-over panel triggered from StockCard click. The panel uses a 60/40 two-column layout with a sticky executive header. All state is local (no global store). Existing Recharts + Framer Motion stack. Dark-only panel with absolute color values.

**Tech Stack:** React 19, Next.js 15, Recharts 3.7, Framer Motion 12, Tailwind CSS 4, Vitest + React Testing Library.

---

## Task 1: Panel Shell — PanelBackdrop

**Files:**
- Create: `web/src/components/dashboard/panel/panel-backdrop.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/panel-backdrop.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/panel-backdrop.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { PanelBackdrop } from "../panel-backdrop"

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion")
  return {
    ...actual,
    motion: {
      ...actual.motion,
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    },
  }
})

describe("PanelBackdrop", () => {
  it("calls onClose when clicked", () => {
    const onClose = vi.fn()
    render(<PanelBackdrop onClose={onClose} />)
    fireEvent.click(screen.getByTestId("panel-backdrop"))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it("renders with correct aria attributes", () => {
    render(<PanelBackdrop onClose={vi.fn()} />)
    const el = screen.getByTestId("panel-backdrop")
    expect(el).toHaveAttribute("aria-hidden", "true")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/panel-backdrop.test.tsx`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```tsx
// web/src/components/dashboard/panel/panel-backdrop.tsx
"use client"

import { motion } from "framer-motion"

interface PanelBackdropProps {
  onClose: () => void
}

export function PanelBackdrop({ onClose }: PanelBackdropProps) {
  return (
    <motion.div
      data-testid="panel-backdrop"
      className="fixed inset-0 z-40 bg-black/50"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      onClick={onClose}
      aria-hidden="true"
    />
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/panel-backdrop.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/
git commit -m "feat(web): add PanelBackdrop component for asset slide-over"
```

---

## Task 2: Panel Shell — TimeRangeSelector

**Files:**
- Create: `web/src/components/dashboard/panel/time-range-selector.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/time-range-selector.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/time-range-selector.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { TimeRangeSelector } from "../time-range-selector"

describe("TimeRangeSelector", () => {
  it("renders all range options", () => {
    render(<TimeRangeSelector value="3M" onChange={vi.fn()} />)
    expect(screen.getByText("1M")).toBeInTheDocument()
    expect(screen.getByText("3M")).toBeInTheDocument()
    expect(screen.getByText("6M")).toBeInTheDocument()
    expect(screen.getByText("1Y")).toBeInTheDocument()
    expect(screen.getByText("ALL")).toBeInTheDocument()
  })

  it("highlights the active range", () => {
    render(<TimeRangeSelector value="6M" onChange={vi.fn()} />)
    const active = screen.getByText("6M")
    expect(active.className).toContain("bg-")
  })

  it("calls onChange with new range", () => {
    const onChange = vi.fn()
    render(<TimeRangeSelector value="3M" onChange={onChange} />)
    fireEvent.click(screen.getByText("1Y"))
    expect(onChange).toHaveBeenCalledWith("1Y")
  })

  it("does not propagate click to parent", () => {
    const parentClick = vi.fn()
    const onChange = vi.fn()
    render(
      <div onClick={parentClick}>
        <TimeRangeSelector value="3M" onChange={onChange} />
      </div>
    )
    fireEvent.click(screen.getByText("1Y"))
    expect(parentClick).not.toHaveBeenCalled()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/time-range-selector.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

```tsx
// web/src/components/dashboard/panel/time-range-selector.tsx
"use client"

export type TimeRange = "1M" | "3M" | "6M" | "1Y" | "ALL"

const RANGES: TimeRange[] = ["1M", "3M", "6M", "1Y", "ALL"]

interface TimeRangeSelectorProps {
  value: TimeRange
  onChange: (range: TimeRange) => void
}

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="flex gap-1" data-testid="time-range-selector">
      {RANGES.map((r) => (
        <button
          key={r}
          onClick={(e) => {
            e.stopPropagation()
            onChange(r)
          }}
          className={`px-2.5 py-1 text-xs font-mono tracking-wide rounded transition-colors ${
            value === r
              ? "bg-[#1A7A5A] text-white"
              : "text-[#5C5955] hover:text-[#9A9590]"
          }`}
        >
          {r}
        </button>
      ))}
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/time-range-selector.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/time-range-selector.tsx web/src/components/dashboard/panel/__tests__/time-range-selector.test.tsx
git commit -m "feat(web): add TimeRangeSelector pill toggle component"
```

---

## Task 3: Panel Shell — ExecutiveHeader

**Files:**
- Create: `web/src/components/dashboard/panel/executive-header.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/executive-header.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/executive-header.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ExecutiveHeader } from "../executive-header"

vi.mock("@/components/ui", () => ({
  ConvictionBadge: ({ level }: { level: string }) => <span data-testid="conviction-badge">{level}</span>,
  ActionPill: () => <span data-testid="action-pill" />,
  AnimatedScore: ({ value }: { value: number }) => <span data-testid="animated-score">{value}</span>,
}))

vi.mock("../time-range-selector", () => ({
  TimeRangeSelector: ({ value, onChange }: any) => (
    <div data-testid="time-range-selector" onClick={() => onChange("1Y")}>{value}</div>
  ),
}))

const baseProps = {
  ticker: "AAPL",
  companyName: "Apple Inc.",
  compositeScore: 92,
  scoreDelta: 3,
  conviction: "exceptional",
  signal: "buy",
  opportunityType: "compounder" as const,
  timeRange: "3M" as const,
  onTimeRangeChange: vi.fn(),
  onClose: vi.fn(),
}

describe("ExecutiveHeader", () => {
  it("renders ticker and company name", () => {
    render(<ExecutiveHeader {...baseProps} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders score and positive delta", () => {
    render(<ExecutiveHeader {...baseProps} />)
    expect(screen.getByTestId("animated-score")).toHaveTextContent("92")
    expect(screen.getByTestId("score-delta")).toHaveTextContent("+3")
  })

  it("renders negative delta in bearish style", () => {
    render(<ExecutiveHeader {...baseProps} scoreDelta={-5} />)
    const delta = screen.getByTestId("score-delta")
    expect(delta).toHaveTextContent("-5")
  })

  it("calls onClose when close button is clicked", () => {
    render(<ExecutiveHeader {...baseProps} />)
    fireEvent.click(screen.getByTestId("panel-close-btn"))
    expect(baseProps.onClose).toHaveBeenCalledOnce()
  })

  it("passes timeRange to TimeRangeSelector", () => {
    render(<ExecutiveHeader {...baseProps} />)
    expect(screen.getByTestId("time-range-selector")).toHaveTextContent("3M")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/executive-header.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

```tsx
// web/src/components/dashboard/panel/executive-header.tsx
"use client"

import { ConvictionBadge, ActionPill, AnimatedScore } from "@/components/ui"
import { TimeRangeSelector, type TimeRange } from "./time-range-selector"

interface ExecutiveHeaderProps {
  ticker: string
  companyName: string
  compositeScore: number
  scoreDelta: number
  conviction: string
  signal: string
  opportunityType: "compounder" | "mispricing"
  timeRange: TimeRange
  onTimeRangeChange: (range: TimeRange) => void
  onClose: () => void
}

export function ExecutiveHeader({
  ticker,
  companyName,
  compositeScore,
  scoreDelta,
  conviction,
  signal,
  opportunityType,
  timeRange,
  onTimeRangeChange,
  onClose,
}: ExecutiveHeaderProps) {
  return (
    <div
      className="sticky top-0 z-10 flex items-center gap-4 h-[72px] px-6 bg-[#0D0F12] border-b border-white/[0.06]"
      data-testid="executive-header"
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="w-10 h-10 flex items-center justify-center rounded-lg text-[#9A9590] hover:text-[#E8E6E3] hover:bg-white/[0.04] transition-colors"
        data-testid="panel-close-btn"
        aria-label="Close panel"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M4 4l8 8M12 4l-8 8" />
        </svg>
      </button>

      {/* Identity */}
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-xl font-semibold text-[#E8E6E3] font-sans shrink-0">{ticker}</span>
        <span className="text-[13px] text-[#5C5955] truncate">{companyName}</span>
        <ConvictionBadge level={conviction} />
      </div>

      {/* Score + Delta + Signal */}
      <div className="flex items-center gap-3 ml-auto">
        <AnimatedScore
          value={compositeScore}
          className="text-[32px] font-display text-[#1A7A5A] leading-none tracking-[-0.04em]"
        />
        <span
          data-testid="score-delta"
          className={`text-[13px] font-mono ${scoreDelta >= 0 ? "text-[#1A7A5A]" : "text-[#C74B50]"}`}
        >
          {scoreDelta >= 0 ? `+${scoreDelta}` : scoreDelta}
          {scoreDelta > 0 ? " \u25B2" : scoreDelta < 0 ? " \u25BC" : ""}
        </span>
        <ActionPill
          signal={signal}
          buyPrice={null}
          sellPrice={null}
          actualPrice={null}
        />
      </div>

      {/* Time range */}
      <TimeRangeSelector value={timeRange} onChange={onTimeRangeChange} />
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/executive-header.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/executive-header.tsx web/src/components/dashboard/panel/__tests__/executive-header.test.tsx
git commit -m "feat(web): add ExecutiveHeader sticky bar for asset panel"
```

---

## Task 4: Left Column — ScoreChart (Hero)

**Files:**
- Create: `web/src/components/dashboard/panel/score-chart.tsx`
- Create: `web/src/components/dashboard/panel/chart-tooltip.tsx`
- Create: `web/src/components/dashboard/panel/score-context.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/score-chart.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/score-chart.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ScoreChart } from "../score-chart"

// Mock recharts — it doesn't render in jsdom
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  ComposedChart: ({ children }: any) => <div data-testid="composed-chart">{children}</div>,
  Area: () => <div data-testid="area" />,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
}))

const mockData = [
  { date: "2026-01-01", score: 80, signal: "buy" },
  { date: "2026-01-08", score: 82, signal: "buy" },
  { date: "2026-01-15", score: 85, signal: "buy" },
  { date: "2026-01-22", score: 87, signal: "buy" },
]

describe("ScoreChart", () => {
  it("renders chart when data is provided", () => {
    render(<ScoreChart data={mockData} timeRange="3M" showBenchmark={false} />)
    expect(screen.getByTestId("score-chart")).toBeInTheDocument()
    expect(screen.getByTestId("composed-chart")).toBeInTheDocument()
  })

  it("renders empty state when no data", () => {
    render(<ScoreChart data={[]} timeRange="3M" showBenchmark={false} />)
    expect(screen.getByTestId("score-chart-empty")).toBeInTheDocument()
    expect(screen.getByText("Insufficient scoring history")).toBeInTheDocument()
  })

  it("renders score context strip", () => {
    render(
      <ScoreChart
        data={mockData}
        timeRange="3M"
        showBenchmark={false}
        universeRank="Top 3%"
        scoringFrequency="Scored weekly"
        lastScored="2h ago"
      />
    )
    expect(screen.getByText("Top 3%")).toBeInTheDocument()
    expect(screen.getByText("Scored weekly")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/score-chart.test.tsx`
Expected: FAIL

**Step 3: Write implementations**

```tsx
// web/src/components/dashboard/panel/chart-tooltip.tsx
"use client"

export interface ChartTooltipData {
  date: string
  score: number
  delta?: number
  signal?: string
}

interface ChartTooltipProps {
  active?: boolean
  payload?: any[]
  label?: string
}

export function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null

  const data = payload[0]?.payload
  if (!data) return null

  return (
    <div className="bg-[rgba(17,17,19,0.8)] backdrop-blur-[8px] border border-white/[0.06] rounded-lg px-3 py-2 shadow-lg">
      <p className="text-[11px] font-mono text-[#5C5955]">{label}</p>
      <p className="text-[20px] font-display text-[#1A7A5A] leading-tight">{Math.round(data.score)}</p>
      {data.signal && (
        <p className="text-[11px] font-mono text-[#9A9590] uppercase">{data.signal}</p>
      )}
    </div>
  )
}
```

```tsx
// web/src/components/dashboard/panel/score-context.tsx
interface ScoreContextProps {
  universeRank?: string
  scoringFrequency?: string
  lastScored?: string
}

export function ScoreContext({ universeRank, scoringFrequency, lastScored }: ScoreContextProps) {
  return (
    <div className="flex items-center gap-4 h-10 px-6 text-[13px]" data-testid="score-context">
      {universeRank && <span className="text-[#1A7A5A]">{universeRank}</span>}
      {scoringFrequency && <span className="text-[#5C5955]">{scoringFrequency}</span>}
      {lastScored && (
        <span className="text-[#5C5955] flex items-center gap-1.5">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#1A7A5A]" />
          {lastScored}
        </span>
      )}
    </div>
  )
}
```

```tsx
// web/src/components/dashboard/panel/score-chart.tsx
"use client"

import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts"
import { ChartTooltip } from "./chart-tooltip"
import { ScoreContext } from "./score-context"
import type { TimeRange } from "./time-range-selector"

export interface ScoreDataPoint {
  date: string
  score: number
  signal?: string
}

interface ScoreChartProps {
  data: ScoreDataPoint[]
  timeRange: TimeRange
  showBenchmark: boolean
  benchmarkData?: ScoreDataPoint[]
  universeRank?: string
  scoringFrequency?: string
  lastScored?: string
}

const RANGE_DAYS: Record<TimeRange, number | null> = {
  "1M": 30,
  "3M": 90,
  "6M": 180,
  "1Y": 365,
  "ALL": null,
}

export function ScoreChart({
  data,
  timeRange,
  showBenchmark,
  benchmarkData,
  universeRank,
  scoringFrequency,
  lastScored,
}: ScoreChartProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="h-[320px] flex items-center justify-center"
        data-testid="score-chart-empty"
      >
        <span className="text-[13px] text-[#5C5955]">Insufficient scoring history</span>
      </div>
    )
  }

  const sorted = [...data].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )
  const rangeDays = RANGE_DAYS[timeRange]
  const sliced = rangeDays ? sorted.slice(-rangeDays) : sorted

  const chartData = sliced.map((d) => ({
    ...d,
    dateLabel: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
  }))

  return (
    <div data-testid="score-chart" className="p-6 pb-0">
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1A7A5A" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#1A7A5A" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            horizontal
            vertical={false}
            stroke="rgba(255,255,255,0.04)"
            strokeDasharray=""
          />
          <XAxis
            dataKey="dateLabel"
            tick={{ fontSize: 11, fontFamily: "var(--font-geist-mono)", fill: "#5C5955" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis domain={[0, 100]} hide />
          <Tooltip
            content={<ChartTooltip />}
            cursor={{ stroke: "rgba(255,255,255,0.15)", strokeDasharray: "4 2", strokeWidth: 1 }}
          />
          <Area
            type="monotone"
            dataKey="score"
            fill="url(#scoreGradient)"
            stroke="none"
            animationDuration={800}
            animationEasing="ease-out"
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#1A7A5A"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: "#fff", stroke: "#1A7A5A", strokeWidth: 2 }}
            animationDuration={800}
            animationEasing="ease-out"
          />
          {showBenchmark && benchmarkData && (
            <Line
              type="monotone"
              data={benchmarkData}
              dataKey="score"
              stroke="rgba(255,255,255,0.2)"
              strokeWidth={1}
              strokeDasharray="4 2"
              dot={false}
              animationDuration={500}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      <ScoreContext
        universeRank={universeRank}
        scoringFrequency={scoringFrequency}
        lastScored={lastScored}
      />
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/score-chart.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/score-chart.tsx web/src/components/dashboard/panel/chart-tooltip.tsx web/src/components/dashboard/panel/score-context.tsx web/src/components/dashboard/panel/__tests__/score-chart.test.tsx
git commit -m "feat(web): add ScoreChart hero visualization with tooltip and context strip"
```

---

## Task 5: Left Column — Redesigned FactorRow + SubScoreChips

**Files:**
- Create: `web/src/components/dashboard/panel/factor-row.tsx`
- Create: `web/src/components/dashboard/panel/sub-score-chips.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/factor-row.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/factor-row.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FactorRow } from "../factor-row"

describe("FactorRow", () => {
  const baseProps = {
    name: "Quality",
    weight: 35,
    score: 65,
    interpretation: "Middle of the pack. Room for improvement.",
    subScores: [
      { label: "Gross Prof", value: 62 },
      { label: "ROIC", value: 85 },
      { label: "Accrual", value: 23 },
      { label: "Piotr", value: 85 },
    ],
  }

  it("renders factor name and weight", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("35%")).toBeInTheDocument()
  })

  it("renders score with percentile-appropriate color", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByTestId("factor-score")).toHaveTextContent("65")
  })

  it("renders interpretation text", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByText("Middle of the pack. Room for improvement.")).toBeInTheDocument()
  })

  it("renders sub-score chips", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByText("Gross Prof: 62")).toBeInTheDocument()
    expect(screen.getByText("ROIC: 85")).toBeInTheDocument()
    expect(screen.getByText("Accrual: 23")).toBeInTheDocument()
    expect(screen.getByText("Piotr: 85")).toBeInTheDocument()
  })

  it("renders progress bar", () => {
    render(<FactorRow {...baseProps} />)
    expect(screen.getByTestId("factor-progress-bar")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/factor-row.test.tsx`
Expected: FAIL

**Step 3: Write implementations**

```tsx
// web/src/components/dashboard/panel/sub-score-chips.tsx
interface SubScore {
  label: string
  value: number
}

interface SubScoreChipsProps {
  subScores: SubScore[]
}

export function SubScoreChips({ subScores }: SubScoreChipsProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {subScores.map((sub) => (
        <span
          key={sub.label}
          className="text-[11px] font-mono text-[#9A9590] bg-white/[0.04] rounded-md px-2 py-0.5"
        >
          {sub.label}: {Math.round(sub.value)}
        </span>
      ))}
    </div>
  )
}
```

```tsx
// web/src/components/dashboard/panel/factor-row.tsx
import { SubScoreChips } from "./sub-score-chips"

function getPercentileColor(score: number): string {
  if (score >= 80) return "#10B981"  // exceptional
  if (score >= 60) return "#1C7A5A"  // strong
  if (score >= 40) return "#6B7280"  // average
  if (score >= 20) return "#D97706"  // below
  return "#DC2626"                    // weak
}

interface FactorRowProps {
  name: string
  weight: number
  score: number
  interpretation: string
  subScores: { label: string; value: number }[]
}

export function FactorRow({ name, weight, score, interpretation, subScores }: FactorRowProps) {
  const color = getPercentileColor(score)

  return (
    <div
      className="py-4 border-b border-white/[0.06] last:border-b-0 hover:bg-white/[0.03] transition-colors duration-200 px-6"
      data-testid={`factor-row-${name.toLowerCase()}`}
    >
      {/* Line 1: Name, Weight, Score */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[14px] font-medium text-[#E8E6E3]">{name}</span>
        <div className="flex items-center gap-3">
          <span className="text-[12px] font-mono text-[#5C5955]">{weight}%</span>
          <span
            className="text-[24px] font-display leading-none"
            style={{ color }}
            data-testid="factor-score"
          >
            {Math.round(score)}
          </span>
        </div>
      </div>

      {/* Line 2: Progress bar + interpretation */}
      <div className="flex items-center gap-3 mb-2">
        <div className="flex-1 h-1 rounded-full bg-white/[0.06]" data-testid="factor-progress-bar">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${score}%`, backgroundColor: color }}
          />
        </div>
        <span className="text-[12px] text-[#5C5955] shrink-0 max-w-[200px] truncate">
          {interpretation}
        </span>
      </div>

      {/* Line 3: Sub-score chips */}
      <SubScoreChips subScores={subScores} />
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/factor-row.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/factor-row.tsx web/src/components/dashboard/panel/sub-score-chips.tsx web/src/components/dashboard/panel/__tests__/factor-row.test.tsx
git commit -m "feat(web): add FactorRow and SubScoreChips for panel factor breakdown"
```

---

## Task 6: Left Column — PanelFactorBreakdown (Wrapper)

**Files:**
- Create: `web/src/components/dashboard/panel/panel-factor-breakdown.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/panel-factor-breakdown.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/panel-factor-breakdown.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PanelFactorBreakdown } from "../panel-factor-breakdown"
import type { FactorBreakdownResponse } from "@/lib/api/types"

const mockFactor = (name: string, weight: number, avg: number): FactorBreakdownResponse => ({
  factor_name: name,
  weight,
  average_percentile: avg,
  sub_scores: [
    { name: "metric_a", raw_value: 0.5, percentile_rank: avg - 5, detail: "" },
    { name: "metric_b", raw_value: 0.7, percentile_rank: avg + 5, detail: "" },
  ],
})

describe("PanelFactorBreakdown", () => {
  it("renders section header with opportunity type", () => {
    render(
      <PanelFactorBreakdown
        quality={mockFactor("quality", 0.35, 65)}
        value={mockFactor("value", 0.30, 98)}
        momentum={mockFactor("momentum", 0.20, 93)}
        winningTrack="compounder"
      />
    )
    expect(screen.getByText("Factor Breakdown")).toBeInTheDocument()
    expect(screen.getByText("Compounder")).toBeInTheDocument()
  })

  it("renders factor rows sorted by weight descending", () => {
    render(
      <PanelFactorBreakdown
        quality={mockFactor("quality", 0.35, 65)}
        value={mockFactor("value", 0.30, 98)}
        momentum={mockFactor("momentum", 0.20, 93)}
        winningTrack="compounder"
      />
    )
    const rows = screen.getAllByTestId(/^factor-row-/)
    expect(rows).toHaveLength(3)
  })

  it("passes correct weight percentages to FactorRow", () => {
    render(
      <PanelFactorBreakdown
        quality={mockFactor("quality", 0.35, 65)}
        value={mockFactor("value", 0.30, 98)}
        momentum={mockFactor("momentum", 0.20, 93)}
        winningTrack={null}
      />
    )
    expect(screen.getByText("35%")).toBeInTheDocument()
    expect(screen.getByText("30%")).toBeInTheDocument()
    expect(screen.getByText("20%")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/panel-factor-breakdown.test.tsx`
Expected: FAIL

**Step 3: Write implementation**

```tsx
// web/src/components/dashboard/panel/panel-factor-breakdown.tsx
import { FactorRow } from "./factor-row"
import { getFactorInterpretation } from "@/lib/score-interpretation"
import { formatAttributeLabel } from "@/lib/format"
import type { FactorBreakdownResponse } from "@/lib/api/types"

interface PanelFactorBreakdownProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  capitalAllocation?: FactorBreakdownResponse | null
  catalyst?: FactorBreakdownResponse | null
  winningTrack?: string | null
}

export function PanelFactorBreakdown({
  quality,
  value,
  momentum,
  capitalAllocation,
  catalyst,
  winningTrack,
}: PanelFactorBreakdownProps) {
  let factors: FactorBreakdownResponse[] = [quality, value, momentum]
  if (capitalAllocation) factors.push(capitalAllocation)
  if (catalyst) factors.push(catalyst)

  // Sort by weight descending
  factors = [...factors].sort((a, b) => b.weight - a.weight)

  const trackLabel = winningTrack === "compounder"
    ? "Compounder"
    : winningTrack === "mispricing"
      ? "Mispricing"
      : null

  return (
    <div data-testid="panel-factor-breakdown">
      <div className="flex items-center justify-between px-6 py-3">
        <h3 className="text-[16px] font-semibold text-[#E8E6E3]">Factor Breakdown</h3>
        {trackLabel && (
          <span
            className={`text-xs px-2 py-0.5 rounded font-medium ${
              winningTrack === "compounder"
                ? "bg-[#1A7A5A]/10 text-[#1A7A5A]"
                : "bg-purple-500/10 text-purple-400"
            }`}
          >
            {trackLabel}
          </span>
        )}
      </div>
      <div>
        {factors.map((factor) => (
          <FactorRow
            key={factor.factor_name}
            name={factor.factor_name.charAt(0).toUpperCase() + factor.factor_name.slice(1).replace("_", " ")}
            weight={Math.round(factor.weight * 100)}
            score={factor.average_percentile}
            interpretation={getFactorInterpretation(factor.factor_name, factor.average_percentile)}
            subScores={factor.sub_scores.map((s) => ({
              label: formatAttributeLabel(s.name),
              value: s.percentile_rank,
            }))}
          />
        ))}
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/panel-factor-breakdown.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/panel-factor-breakdown.tsx web/src/components/dashboard/panel/__tests__/panel-factor-breakdown.test.tsx
git commit -m "feat(web): add PanelFactorBreakdown wrapper with sorted factor rows"
```

---

## Task 7: Right Column — KpiCell + KpiGrid

**Files:**
- Create: `web/src/components/dashboard/panel/kpi-cell.tsx`
- Create: `web/src/components/dashboard/panel/kpi-grid.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/kpi-grid.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/kpi-grid.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { KpiGrid } from "../kpi-grid"

describe("KpiGrid", () => {
  const baseProps = {
    sharpeRatio: 1.42,
    maxDrawdown: -0.15,
    volatility: 22.5,
    avgProfitMargin: null,
    allocationWeight: 5,
    marginOfSafety: 26,
  }

  it("renders all 6 KPI cells", () => {
    render(<KpiGrid {...baseProps} />)
    expect(screen.getByText("SHARPE RATIO")).toBeInTheDocument()
    expect(screen.getByText("MAX DRAWDOWN")).toBeInTheDocument()
    expect(screen.getByText("VOLATILITY")).toBeInTheDocument()
    expect(screen.getByText("AVG PROFIT MARGIN")).toBeInTheDocument()
    expect(screen.getByText("ALLOCATION")).toBeInTheDocument()
    expect(screen.getByText("MARGIN OF SAFETY")).toBeInTheDocument()
  })

  it("renders numeric values correctly", () => {
    render(<KpiGrid {...baseProps} />)
    expect(screen.getByText("1.42")).toBeInTheDocument()
    expect(screen.getByText("-15.0%")).toBeInTheDocument()
    expect(screen.getByText("22.5%")).toBeInTheDocument()
  })

  it("renders null values as dashes", () => {
    render(<KpiGrid {...baseProps} />)
    // avgProfitMargin is null
    expect(screen.getByTestId("kpi-avg-profit-margin-value")).toHaveTextContent("\u2014")
  })

  it("renders margin of safety as percentage", () => {
    render(<KpiGrid {...baseProps} />)
    expect(screen.getByText("26%")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/kpi-grid.test.tsx`
Expected: FAIL

**Step 3: Write implementations**

```tsx
// web/src/components/dashboard/panel/kpi-cell.tsx
interface KpiCellProps {
  label: string
  value: string
  context?: string
  testId?: string
}

export function KpiCell({ label, value, context, testId }: KpiCellProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-sans uppercase tracking-[0.05em] text-[#5C5955]">
        {label}
      </span>
      <span className="text-[20px] font-mono text-[#E8E6E3] leading-tight" data-testid={testId}>
        {value}
      </span>
      {context && (
        <span className="text-[11px] text-[#1A7A5A]">{context}</span>
      )}
    </div>
  )
}
```

```tsx
// web/src/components/dashboard/panel/kpi-grid.tsx
import { KpiCell } from "./kpi-cell"

interface KpiGridProps {
  sharpeRatio: number | null
  maxDrawdown: number | null
  volatility: number | null
  avgProfitMargin: number | null
  allocationWeight: number | null
  marginOfSafety: number | null
}

function fmt(v: number | null, suffix: string = "", decimals: number = 1): string {
  if (v == null) return "\u2014"
  if (suffix === "%") return `${v.toFixed(decimals)}%`
  return `${v.toFixed(decimals === 0 ? 0 : 2)}${suffix}`
}

export function KpiGrid({
  sharpeRatio,
  maxDrawdown,
  volatility,
  avgProfitMargin,
  allocationWeight,
  marginOfSafety,
}: KpiGridProps) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-5" data-testid="kpi-grid">
      <KpiCell
        label="SHARPE RATIO"
        value={sharpeRatio != null ? sharpeRatio.toFixed(2) : "\u2014"}
        testId="kpi-sharpe-ratio-value"
      />
      <KpiCell
        label="MAX DRAWDOWN"
        value={maxDrawdown != null ? `${(maxDrawdown * 100).toFixed(1)}%` : "\u2014"}
        testId="kpi-max-drawdown-value"
      />
      <KpiCell
        label="VOLATILITY"
        value={volatility != null ? `${volatility.toFixed(1)}%` : "\u2014"}
        testId="kpi-volatility-value"
      />
      <KpiCell
        label="AVG PROFIT MARGIN"
        value={avgProfitMargin != null ? `${avgProfitMargin.toFixed(1)}%` : "\u2014"}
        testId="kpi-avg-profit-margin-value"
      />
      <KpiCell
        label="ALLOCATION"
        value={allocationWeight != null ? `${Math.round(allocationWeight)}%` : "\u2014"}
        testId="kpi-allocation-value"
      />
      <KpiCell
        label="MARGIN OF SAFETY"
        value={marginOfSafety != null ? `${Math.round(marginOfSafety)}%` : "\u2014"}
        testId="kpi-margin-of-safety-value"
      />
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/kpi-grid.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/kpi-cell.tsx web/src/components/dashboard/panel/kpi-grid.tsx web/src/components/dashboard/panel/__tests__/kpi-grid.test.tsx
git commit -m "feat(web): add KpiGrid and KpiCell for institutional metrics"
```

---

## Task 8: Right Column — InsightCard + InsightPanel

**Files:**
- Create: `web/src/components/dashboard/panel/insight-card.tsx`
- Create: `web/src/components/dashboard/panel/insight-panel.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/insight-panel.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/insight-panel.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { InsightPanel } from "../insight-panel"

describe("InsightPanel", () => {
  const baseProps = {
    strengths: ["Exceptional value — top 2% on FCF yield", "Strong momentum"],
    risks: ["Liquidity filter failed", "Insufficient Beneish M-Score data"],
    commentary: "TISNF presents a compelling value opportunity with exceptional momentum.",
    confidence: 78,
  }

  it("renders strengths card with items", () => {
    render(<InsightPanel {...baseProps} />)
    expect(screen.getByText("Strengths")).toBeInTheDocument()
    expect(screen.getByText("Exceptional value — top 2% on FCF yield")).toBeInTheDocument()
    expect(screen.getByText("Strong momentum")).toBeInTheDocument()
  })

  it("renders risk flags card", () => {
    render(<InsightPanel {...baseProps} />)
    expect(screen.getByText("Risk Flags")).toBeInTheDocument()
    expect(screen.getByText("Liquidity filter failed")).toBeInTheDocument()
  })

  it("renders commentary card", () => {
    render(<InsightPanel {...baseProps} />)
    expect(screen.getByText("Analysis")).toBeInTheDocument()
    expect(screen.getByText(baseProps.commentary)).toBeInTheDocument()
  })

  it("renders confidence bar with percentage", () => {
    render(<InsightPanel {...baseProps} />)
    expect(screen.getByText("AI Confidence")).toBeInTheDocument()
    expect(screen.getByText("78%")).toBeInTheDocument()
  })

  it("renders empty strengths gracefully", () => {
    render(<InsightPanel {...baseProps} strengths={[]} />)
    expect(screen.getByText("Strengths")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/insight-panel.test.tsx`
Expected: FAIL

**Step 3: Write implementations**

```tsx
// web/src/components/dashboard/panel/insight-card.tsx
interface InsightCardProps {
  variant: "strengths" | "risks" | "commentary"
  title: string
  items?: string[]
  text?: string
}

const VARIANT_STYLES = {
  strengths: {
    border: "border-l-[#1A7A5A]",
    bg: "bg-[rgba(26,122,90,0.04)]",
    title: "text-[#1A7A5A]",
    icon: "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  },
  risks: {
    border: "border-l-[#C74B50]",
    bg: "bg-[rgba(199,75,80,0.04)]",
    title: "text-[#C74B50]",
    icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z",
  },
  commentary: {
    border: "border-l-white/15",
    bg: "bg-white/[0.02]",
    title: "text-[#9A9590]",
    icon: "M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z",
  },
}

export function InsightCard({ variant, title, items, text }: InsightCardProps) {
  const styles = VARIANT_STYLES[variant]

  return (
    <div
      className={`border-l-4 ${styles.border} ${styles.bg} rounded-r-lg p-4 hover:border-l-[6px] transition-all duration-200`}
      data-testid={`insight-card-${variant}`}
    >
      <div className={`flex items-center gap-2 mb-2 ${styles.title}`}>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d={styles.icon} />
        </svg>
        <span className="text-[13px] font-medium">{title}</span>
      </div>
      {items && items.length > 0 && (
        <ul className="space-y-1">
          {items.map((item, i) => (
            <li key={i} className="text-[13px] text-[#9A9590] leading-relaxed flex gap-2">
              <span className="text-[#5C5955] shrink-0">&bull;</span>
              {item}
            </li>
          ))}
        </ul>
      )}
      {text && (
        <p className="text-[13px] text-[#9A9590] leading-relaxed">{text}</p>
      )}
    </div>
  )
}
```

```tsx
// web/src/components/dashboard/panel/insight-panel.tsx
import { InsightCard } from "./insight-card"

interface InsightPanelProps {
  strengths: string[]
  risks: string[]
  commentary: string
  confidence: number
}

export function InsightPanel({ strengths, risks, commentary, confidence }: InsightPanelProps) {
  return (
    <div className="space-y-3" data-testid="insight-panel">
      <InsightCard variant="strengths" title="Strengths" items={strengths} />
      <InsightCard variant="risks" title="Risk Flags" items={risks} />
      <InsightCard variant="commentary" title="Analysis" text={commentary} />

      {/* Confidence bar */}
      <div className="flex items-center gap-3 pt-1">
        <span className="text-[11px] text-[#5C5955]">AI Confidence</span>
        <div className="flex-1 h-[3px] rounded-full bg-white/[0.06]">
          <div
            className="h-full rounded-full bg-[#1A7A5A] transition-all duration-700 ease-out"
            style={{ width: `${confidence}%` }}
          />
        </div>
        <span className="text-[13px] font-mono text-[#1A7A5A]">{confidence}%</span>
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/insight-panel.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/insight-card.tsx web/src/components/dashboard/panel/insight-panel.tsx web/src/components/dashboard/panel/__tests__/insight-panel.test.tsx
git commit -m "feat(web): add InsightCard and InsightPanel with strengths/risks/commentary"
```

---

## Task 9: Right Column — Panel ValuationBreakdown

**Files:**
- Create: `web/src/components/dashboard/panel/panel-valuation.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/panel-valuation.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/panel-valuation.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PanelValuation } from "../panel-valuation"

describe("PanelValuation", () => {
  const baseProps = {
    intrinsicValue: 28.5,
    currentPrice: 21.0,
    marginOfSafety: 0.26,
    methods: { dcf: 32.1, ev_fcf: 24.8, acquirers_multiple: 28.9, shareholder_yield: 27.2 },
  }

  it("renders intrinsic value", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("$28.50")).toBeInTheDocument()
  })

  it("renders current price and margin of safety", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("Current: $21.00")).toBeInTheDocument()
    expect(screen.getByText("26%")).toBeInTheDocument()
  })

  it("renders all valuation method bars", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("DCF Model")).toBeInTheDocument()
    expect(screen.getByText("EV/FCF")).toBeInTheDocument()
    expect(screen.getByText("EV/EBIT")).toBeInTheDocument()
    expect(screen.getByText("Shareholder Yield")).toBeInTheDocument()
  })

  it("renders empty state when no methods", () => {
    render(<PanelValuation {...baseProps} methods={{}} />)
    expect(screen.getByText("No valuation data")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/panel-valuation.test.tsx`
Expected: FAIL

**Step 3: Write implementation**

```tsx
// web/src/components/dashboard/panel/panel-valuation.tsx
const METHOD_LABELS: Record<string, string> = {
  dcf: "DCF Model",
  ev_fcf: "EV/FCF",
  acquirers_multiple: "EV/EBIT",
  shareholder_yield: "Shareholder Yield",
}

interface PanelValuationProps {
  intrinsicValue: number | null
  currentPrice: number | null
  marginOfSafety: number | null
  methods: Record<string, number> | null
}

export function PanelValuation({
  intrinsicValue,
  currentPrice,
  marginOfSafety,
  methods,
}: PanelValuationProps) {
  const entries = methods ? Object.entries(methods) : []

  if (entries.length === 0) {
    return (
      <div data-testid="panel-valuation">
        <h3 className="text-[14px] font-semibold text-[#E8E6E3] mb-3">Valuation</h3>
        <p className="text-[13px] text-[#5C5955]">No valuation data</p>
      </div>
    )
  }

  const maxValue = Math.max(...entries.map(([, v]) => v))

  return (
    <div data-testid="panel-valuation">
      <h3 className="text-[14px] font-semibold text-[#E8E6E3] mb-3">Valuation</h3>

      {/* Intrinsic value callout */}
      {intrinsicValue != null && (
        <div className="mb-4">
          <div className="flex items-baseline gap-2">
            <span className="text-[12px] text-[#9A9590]">Intrinsic Value:</span>
            <span className="text-[16px] font-mono text-[#E8E6E3]">${intrinsicValue.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2 mt-1 text-[12px]">
            {currentPrice != null && (
              <span className="text-[#9A9590]">Current: ${currentPrice.toFixed(2)}</span>
            )}
            {currentPrice != null && marginOfSafety != null && (
              <span className="text-[#5C5955]">&middot;</span>
            )}
            {marginOfSafety != null && (
              <span className="text-[12px]">
                <span className="text-[#9A9590]">MoS: </span>
                <span className={marginOfSafety > 0 ? "text-[#1A7A5A] font-mono font-medium" : "text-[#C74B50] font-mono"}>
                  {Math.round(marginOfSafety * 100)}%
                </span>
              </span>
            )}
          </div>
        </div>
      )}

      {/* Method bars */}
      <div className="space-y-2.5">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-[12px] text-[#9A9590] w-[120px] shrink-0">
              {METHOD_LABELS[key] ?? key}
            </span>
            <div className="flex-1 h-[3px] rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full bg-[#1A7A5A]/40"
                style={{ width: `${(value / maxValue) * 100}%` }}
              />
            </div>
            <span className="text-[12px] font-mono text-[#E8E6E3] w-16 text-right">${value.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/panel-valuation.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/panel-valuation.tsx web/src/components/dashboard/panel/__tests__/panel-valuation.test.tsx
git commit -m "feat(web): add PanelValuation with intrinsic value callout and method bars"
```

---

## Task 10: Right Column — PanelFilterList

**Files:**
- Create: `web/src/components/dashboard/panel/panel-filter-list.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/panel-filter-list.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/panel-filter-list.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { PanelFilterList } from "../panel-filter-list"
import type { FilterResultResponse } from "@/lib/api/types"

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion")
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    motion: {
      ...actual.motion,
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    },
  }
})

const mockFilters: FilterResultResponse[] = [
  { name: "liquidity", passed: false, value: 5376, threshold: 300000, detail: "market_cap=$5,376", verdict: "FAIL" },
  { name: "beneish_m_score", passed: true, value: null, threshold: null, detail: "Insufficient data", verdict: "PASS" },
  { name: "altman_z_score", passed: true, value: 6.48, threshold: 1.1, detail: "Z=6.4817", verdict: "PASS" },
]

describe("PanelFilterList", () => {
  it("renders filter header with pass count", () => {
    render(<PanelFilterList filters={mockFilters} />)
    expect(screen.getByText("Filters")).toBeInTheDocument()
    expect(screen.getByText("2/3")).toBeInTheDocument()
  })

  it("renders all filter rows", () => {
    render(<PanelFilterList filters={mockFilters} />)
    expect(screen.getByText("Liquidity")).toBeInTheDocument()
    expect(screen.getByText("Beneish M Score")).toBeInTheDocument()
    expect(screen.getByText("Altman Z Score")).toBeInTheDocument()
  })

  it("marks failed filters with red background", () => {
    render(<PanelFilterList filters={mockFilters} />)
    const row = screen.getByTestId("panel-filter-liquidity")
    expect(row.className).toContain("bg-")
  })

  it("expands filter detail on click", () => {
    render(<PanelFilterList filters={mockFilters} />)
    fireEvent.click(screen.getByTestId("panel-filter-liquidity"))
    expect(screen.getByText("market_cap=$5,376")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/panel-filter-list.test.tsx`
Expected: FAIL

**Step 3: Write implementation**

```tsx
// web/src/components/dashboard/panel/panel-filter-list.tsx
"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { formatAttributeLabel } from "@/lib/format"
import type { FilterResultResponse } from "@/lib/api/types"

interface PanelFilterListProps {
  filters: FilterResultResponse[]
}

export function PanelFilterList({ filters }: PanelFilterListProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const passCount = filters.filter((f) => f.passed).length

  function toggle(name: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <div data-testid="panel-filter-list">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[14px] font-semibold text-[#E8E6E3]">Filters</h3>
        <span className="text-[12px] font-mono text-[#9A9590] bg-white/[0.04] px-2 py-0.5 rounded">
          {passCount}/{filters.length}
        </span>
      </div>
      <div className="space-y-0.5">
        {filters.map((filter) => {
          const isExpanded = expanded.has(filter.name)
          return (
            <div key={filter.name}>
              <div
                className={`flex items-center gap-2 h-8 px-2 rounded cursor-pointer transition-colors duration-150 hover:bg-white/[0.03] ${
                  !filter.passed ? "bg-[rgba(199,75,80,0.04)]" : ""
                }`}
                data-testid={`panel-filter-${filter.name}`}
                onClick={() => toggle(filter.name)}
              >
                <span className={`text-[14px] shrink-0 ${filter.passed ? "text-[#1A7A5A]" : "text-[#C74B50]"}`}>
                  {filter.passed ? "\u2713" : "\u2717"}
                </span>
                <span className="text-[13px] text-[#E8E6E3]">{formatAttributeLabel(filter.name)}</span>
                <span className="text-[11px] font-mono text-[#5C5955] ml-auto">
                  {filter.passed ? "PASS" : "FAIL"}
                </span>
              </div>
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="text-[11px] font-mono text-[#5C5955] px-2 pb-2 pl-7">
                      {filter.detail}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/panel-filter-list.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/panel-filter-list.tsx web/src/components/dashboard/panel/__tests__/panel-filter-list.test.tsx
git commit -m "feat(web): add PanelFilterList with collapsible detail rows"
```

---

## Task 11: Bottom — ScoreHistoryTable

**Files:**
- Create: `web/src/components/dashboard/panel/score-history-table.tsx`
- Test: `web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ScoreHistoryTable } from "../score-history-table"

vi.mock("@/components/ui", () => ({
  SignalBadge: ({ signal }: { signal: string }) => <span data-testid="signal-badge">{signal}</span>,
}))

const mockHistory = [
  { date: "2026-02-16", score: 87, delta: 3, signal: "buy", conviction: "exceptional", keyChange: "Value \u2191 94\u219298" },
  { date: "2026-02-09", score: 84, delta: -1, signal: "buy", conviction: "high", keyChange: "Momentum \u2193 96\u219293" },
  { date: "2026-02-02", score: 85, delta: 5, signal: "buy", conviction: "high", keyChange: "Quality \u2191 58\u219265" },
]

describe("ScoreHistoryTable", () => {
  it("renders table with correct number of rows", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    expect(screen.getByTestId("score-history-table")).toBeInTheDocument()
    expect(screen.getByText("3 runs")).toBeInTheDocument()
    expect(screen.getAllByRole("row")).toHaveLength(4) // 1 header + 3 data
  })

  it("renders score values", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    expect(screen.getByText("87")).toBeInTheDocument()
    expect(screen.getByText("84")).toBeInTheDocument()
    expect(screen.getByText("85")).toBeInTheDocument()
  })

  it("renders positive delta with green styling", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    const deltas = screen.getAllByTestId("score-delta")
    expect(deltas[0]).toHaveTextContent("+3")
  })

  it("renders negative delta with red styling", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    const deltas = screen.getAllByTestId("score-delta")
    expect(deltas[1]).toHaveTextContent("-1")
  })

  it("sorts by date descending by default", () => {
    render(<ScoreHistoryTable history={mockHistory} />)
    const rows = screen.getAllByRole("row")
    // First data row should be most recent
    expect(rows[1]).toHaveTextContent("Feb 16, 2026")
  })

  it("renders empty state", () => {
    render(<ScoreHistoryTable history={[]} />)
    expect(screen.getByText("No scoring history yet")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx`
Expected: FAIL

**Step 3: Write implementation**

```tsx
// web/src/components/dashboard/panel/score-history-table.tsx
"use client"

import { useState, useMemo } from "react"
import { SignalBadge } from "@/components/ui"

export interface ScoreHistoryRow {
  date: string
  score: number
  delta: number
  signal: string
  conviction: string
  keyChange: string
}

interface ScoreHistoryTableProps {
  history: ScoreHistoryRow[]
}

function getPercentileColor(score: number): string {
  if (score >= 80) return "#10B981"
  if (score >= 60) return "#1C7A5A"
  if (score >= 40) return "#6B7280"
  if (score >= 20) return "#D97706"
  return "#DC2626"
}

type SortKey = "date" | "score"

export function ScoreHistoryTable({ history }: ScoreHistoryTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("date")
  const [sortAsc, setSortAsc] = useState(false) // desc by default

  const sorted = useMemo(() => {
    const copy = [...history]
    copy.sort((a, b) => {
      let cmp: number
      if (sortKey === "date") {
        cmp = new Date(a.date).getTime() - new Date(b.date).getTime()
      } else {
        cmp = a.score - b.score
      }
      return sortAsc ? cmp : -cmp
    })
    return copy
  }, [history, sortKey, sortAsc])

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(false)
    }
  }

  if (history.length === 0) {
    return (
      <div className="px-6 py-8 text-center" data-testid="score-history-table">
        <p className="text-[13px] text-[#5C5955]">No scoring history yet</p>
      </div>
    )
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  }

  const chevron = sortAsc ? " \u25B2" : " \u25BC"

  return (
    <div className="px-6 pt-4 pb-6" data-testid="score-history-table">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[16px] font-semibold text-[#E8E6E3]">Score History</h3>
        <span className="text-[12px] text-[#5C5955]">{history.length} runs</span>
      </div>
      <table className="w-full">
        <thead>
          <tr className="border-b border-white/[0.06]">
            <th
              className="text-left text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2 cursor-pointer select-none"
              onClick={() => handleSort("date")}
            >
              Date{sortKey === "date" ? chevron : ""}
            </th>
            <th
              className="text-right text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2 cursor-pointer select-none"
              onClick={() => handleSort("score")}
            >
              Score{sortKey === "score" ? chevron : ""}
            </th>
            <th className="text-right text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2">Delta</th>
            <th className="text-center text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2">Signal</th>
            <th className="text-left text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2">Conviction</th>
            <th className="text-left text-[11px] font-normal uppercase tracking-[0.05em] text-[#5C5955] pb-2">Key Change</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr
              key={row.date + i}
              className="border-b border-white/[0.03] h-[44px] hover:bg-white/[0.03] transition-colors duration-150"
            >
              <td className="text-[12px] font-mono text-[#9A9590]">{formatDate(row.date)}</td>
              <td className="text-right">
                <span
                  className="text-[16px] font-display"
                  style={{ color: getPercentileColor(row.score) }}
                >
                  {Math.round(row.score)}
                </span>
              </td>
              <td className="text-right">
                <span
                  data-testid="score-delta"
                  className={`text-[12px] font-mono ${
                    row.delta > 0 ? "text-[#1A7A5A]" : row.delta < 0 ? "text-[#C74B50]" : "text-[#5C5955]"
                  }`}
                >
                  {row.delta > 0 ? `+${row.delta}` : row.delta === 0 ? "\u2014" : row.delta}
                  {row.delta > 0 ? " \u25B2" : row.delta < 0 ? " \u25BC" : ""}
                </span>
              </td>
              <td className="text-center">
                <SignalBadge signal={row.signal} />
              </td>
              <td className="text-[12px]" style={{ color: getPercentileColor(row.score) }}>
                {row.conviction}
              </td>
              <td className="text-[12px] text-[#5C5955]">{row.keyChange}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/score-history-table.tsx web/src/components/dashboard/panel/__tests__/score-history-table.test.tsx
git commit -m "feat(web): add ScoreHistoryTable with sortable columns"
```

---

## Task 12: Orchestrator — AssetPanel

This is the main component that composes everything together. It manages panel open/close, data wiring, and the animation orchestration.

**Files:**
- Create: `web/src/components/dashboard/panel/asset-panel.tsx`
- Create: `web/src/components/dashboard/panel/index.ts`
- Test: `web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { AssetPanel } from "../asset-panel"
import type { ScoreResponse } from "@/lib/api/types"

// Mock all child components to isolate orchestration logic
vi.mock("../panel-backdrop", () => ({
  PanelBackdrop: ({ onClose }: any) => <div data-testid="panel-backdrop" onClick={onClose} />,
}))
vi.mock("../executive-header", () => ({
  ExecutiveHeader: (props: any) => <div data-testid="executive-header">{props.ticker}</div>,
}))
vi.mock("../score-chart", () => ({
  ScoreChart: () => <div data-testid="score-chart" />,
}))
vi.mock("../panel-factor-breakdown", () => ({
  PanelFactorBreakdown: () => <div data-testid="panel-factor-breakdown" />,
}))
vi.mock("../kpi-grid", () => ({
  KpiGrid: () => <div data-testid="kpi-grid" />,
}))
vi.mock("../insight-panel", () => ({
  InsightPanel: () => <div data-testid="insight-panel" />,
}))
vi.mock("../panel-valuation", () => ({
  PanelValuation: () => <div data-testid="panel-valuation" />,
}))
vi.mock("../panel-filter-list", () => ({
  PanelFilterList: () => <div data-testid="panel-filter-list" />,
}))
vi.mock("../score-history-table", () => ({
  ScoreHistoryTable: () => <div data-testid="score-history-table" />,
}))
vi.mock("../../pro-gate", () => ({
  ProGate: ({ children }: any) => <div data-testid="pro-gate">{children}</div>,
}))

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion")
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    motion: {
      ...actual.motion,
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    },
  }
})

const mockScore: ScoreResponse = {
  ticker: "AAPL",
  name: "Apple Inc.",
  score: 92,
  universe_percentile: 95,
  composite_percentile: 95,
  composite_raw_score: 88,
  conviction_level: "exceptional",
  signal: "buy",
  quality: { factor_name: "quality", weight: 0.35, average_percentile: 90, sub_scores: [] },
  value: { factor_name: "value", weight: 0.30, average_percentile: 85, sub_scores: [] },
  momentum: { factor_name: "momentum", weight: 0.20, average_percentile: 88, sub_scores: [] },
  filters_passed: [],
  data_coverage: 0.95,
  intrinsic_value: 180,
  buy_price: 140,
  sell_price: 200,
  actual_price: 150,
  price_upside: 0.2,
  margin_of_safety: 0.17,
  valuation_methods: { dcf: 190, ev_fcf: 170 },
}

describe("AssetPanel", () => {
  it("renders nothing when isOpen is false", () => {
    render(<AssetPanel isOpen={false} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} />)
    expect(screen.queryByTestId("asset-panel")).not.toBeInTheDocument()
  })

  it("renders all sections when open", () => {
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} />)
    expect(screen.getByTestId("asset-panel")).toBeInTheDocument()
    expect(screen.getByTestId("panel-backdrop")).toBeInTheDocument()
    expect(screen.getByTestId("executive-header")).toBeInTheDocument()
    expect(screen.getByTestId("score-chart")).toBeInTheDocument()
    expect(screen.getByTestId("panel-factor-breakdown")).toBeInTheDocument()
    expect(screen.getByTestId("kpi-grid")).toBeInTheDocument()
    expect(screen.getByTestId("insight-panel")).toBeInTheDocument()
    expect(screen.getByTestId("panel-valuation")).toBeInTheDocument()
    expect(screen.getByTestId("panel-filter-list")).toBeInTheDocument()
    expect(screen.getByTestId("score-history-table")).toBeInTheDocument()
  })

  it("calls onClose when backdrop clicked", () => {
    const onClose = vi.fn()
    render(<AssetPanel isOpen={true} onClose={onClose} ticker="AAPL" scoredResult={mockScore} />)
    fireEvent.click(screen.getByTestId("panel-backdrop"))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it("passes ticker to ExecutiveHeader", () => {
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} />)
    expect(screen.getByTestId("executive-header")).toHaveTextContent("AAPL")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx`
Expected: FAIL

**Step 3: Write implementation**

```tsx
// web/src/components/dashboard/panel/asset-panel.tsx
"use client"

import { useState, useMemo } from "react"
import { createPortal } from "react-dom"
import { AnimatePresence, motion } from "framer-motion"
import { PanelBackdrop } from "./panel-backdrop"
import { ExecutiveHeader } from "./executive-header"
import { ScoreChart } from "./score-chart"
import { PanelFactorBreakdown } from "./panel-factor-breakdown"
import { KpiGrid } from "./kpi-grid"
import { InsightPanel } from "./insight-panel"
import { PanelValuation } from "./panel-valuation"
import { PanelFilterList } from "./panel-filter-list"
import { ScoreHistoryTable } from "./score-history-table"
import { ProGate } from "../pro-gate"
import { computeInstitutionalMetrics } from "@/lib/compute-institutional-metrics"
import { composeAiSummary } from "@/lib/compose-ai-summary"
import type { TimeRange } from "./time-range-selector"
import type { ScoreResponse } from "@/lib/api/types"

interface AssetPanelProps {
  isOpen: boolean
  onClose: () => void
  ticker: string
  scoredResult: ScoreResponse
}

const PANEL_EASE = [0.22, 1, 0.36, 1] as const

function computeInsights(score: ScoreResponse) {
  const strengths: string[] = []
  const risks: string[] = []

  const factors = [
    { name: "quality", p: score.quality.average_percentile },
    { name: "value", p: score.value.average_percentile },
    { name: "momentum", p: score.momentum.average_percentile },
  ]

  for (const f of factors) {
    if (f.p >= 80) {
      strengths.push(`Exceptional ${f.name} \u2014 top ${100 - Math.round(f.p)}% on key metrics`)
    } else if (f.p >= 60) {
      strengths.push(`Strong ${f.name} with ${Math.round(f.p)}th percentile ranking`)
    }
    if (f.p < 40) {
      risks.push(`Weak ${f.name} at ${Math.round(f.p)}th percentile`)
    }
  }

  for (const filter of score.filters_passed) {
    if (!filter.passed) {
      risks.push(`${filter.name.replace(/_/g, " ")} filter failed`)
    }
  }

  if (strengths.length === 0) strengths.push("Balanced factor profile across all dimensions")
  if (risks.length === 0) risks.push("No significant risk flags identified")

  return { strengths, risks }
}

export function AssetPanel({ isOpen, onClose, ticker, scoredResult }: AssetPanelProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>("3M")

  const metrics = useMemo(
    () => computeInstitutionalMetrics(scoredResult),
    [scoredResult],
  )

  const aiSummary = useMemo(() => composeAiSummary(scoredResult), [scoredResult])
  const insights = useMemo(() => computeInsights(scoredResult), [scoredResult])

  // Score history — for now, single entry from current score.
  // TODO: Fetch actual history from API when endpoint exists.
  const scoreHistory = useMemo(() => [{
    date: scoredResult.scored_at ?? new Date().toISOString(),
    score: scoredResult.score,
    delta: 0,
    signal: scoredResult.signal,
    conviction: scoredResult.conviction_level,
    keyChange: "Current",
  }], [scoredResult])

  // Score chart data — currently single point. Will expand with history API.
  const scoreChartData = useMemo(() => [{
    date: scoredResult.scored_at ?? new Date().toISOString(),
    score: scoredResult.score,
    signal: scoredResult.signal,
  }], [scoredResult])

  const universeRank = scoredResult.universe_percentile >= 90
    ? `Top ${100 - Math.round(scoredResult.universe_percentile)}% of universe`
    : `${Math.round(scoredResult.universe_percentile)}th percentile`

  if (typeof window === "undefined") return null

  const content = (
    <AnimatePresence>
      {isOpen && (
        <div data-testid="asset-panel" className="fixed inset-0 z-50">
          <PanelBackdrop onClose={onClose} />
          <motion.div
            className="fixed top-0 right-0 bottom-0 w-[70vw] min-w-[900px] max-w-[1200px] bg-[#0B0D10] shadow-[0_0_80px_rgba(0,0,0,0.6)] overflow-y-auto z-50"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.4, ease: PANEL_EASE }}
          >
            <ExecutiveHeader
              ticker={ticker}
              companyName={scoredResult.name}
              compositeScore={scoredResult.score}
              scoreDelta={0}
              conviction={scoredResult.conviction_level}
              signal={scoredResult.signal}
              opportunityType={(scoredResult.winning_track as "compounder" | "mispricing") ?? "compounder"}
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
              onClose={onClose}
            />

            {/* 2-column body */}
            <div className="grid grid-cols-[1fr_0.67fr]">
              {/* Left column — 60% */}
              <div className="border-r border-white/[0.06]">
                <ScoreChart
                  data={scoreChartData}
                  timeRange={timeRange}
                  showBenchmark={false}
                  universeRank={universeRank}
                  scoringFrequency="Scored weekly"
                  lastScored={scoredResult.scored_at ? "Recent" : undefined}
                />
                <PanelFactorBreakdown
                  quality={scoredResult.quality}
                  value={scoredResult.value}
                  momentum={scoredResult.momentum}
                  capitalAllocation={scoredResult.capital_allocation}
                  catalyst={scoredResult.catalyst}
                  winningTrack={scoredResult.winning_track}
                />
              </div>

              {/* Right column — 40% */}
              <div className="p-6 space-y-6">
                <ProGate>
                  <KpiGrid
                    sharpeRatio={metrics?.sharpeRatio ?? null}
                    maxDrawdown={metrics?.maxDrawdown ?? null}
                    volatility={metrics?.volatility ?? null}
                    avgProfitMargin={metrics?.avgProfitMargin ?? null}
                    allocationWeight={metrics?.allocationWeight ?? null}
                    marginOfSafety={scoredResult.margin_of_safety != null ? Math.round(scoredResult.margin_of_safety * 100) : null}
                  />
                </ProGate>

                <ProGate>
                  <InsightPanel
                    strengths={insights.strengths}
                    risks={insights.risks}
                    commentary={aiSummary.summary}
                    confidence={aiSummary.confidence}
                  />
                </ProGate>

                <PanelValuation
                  intrinsicValue={scoredResult.intrinsic_value}
                  currentPrice={scoredResult.actual_price}
                  marginOfSafety={scoredResult.margin_of_safety}
                  methods={scoredResult.valuation_methods}
                />

                <PanelFilterList filters={scoredResult.filters_passed} />
              </div>
            </div>

            {/* Full-width bottom */}
            <div className="border-t border-white/[0.06]">
              <ScoreHistoryTable history={scoreHistory} />
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )

  return createPortal(content, document.body)
}
```

```tsx
// web/src/components/dashboard/panel/index.ts
export { AssetPanel } from "./asset-panel"
export type { TimeRange } from "./time-range-selector"
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/
git commit -m "feat(web): add AssetPanel orchestrator composing all panel sections"
```

---

## Task 13: Integration — Wire AssetPanel into StockCard

Replace the inline `AssetDetail` expansion with the new slide-over `AssetPanel`.

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Modify: `web/src/components/dashboard/index.ts`
- Test: Update `web/src/components/dashboard/__tests__/stock-card.test.tsx`

**Step 1: Update the StockCard test**

Add a test for the new panel behavior:

```tsx
// Add to existing stock-card.test.tsx
import { AssetPanel } from "../panel"

vi.mock("../panel", () => ({
  AssetPanel: ({ isOpen, ticker }: any) =>
    isOpen ? <div data-testid={`asset-panel-${ticker}`} /> : null,
}))

it("opens AssetPanel on click instead of inline detail", async () => {
  const { user } = render(<StockCard pick={basePick} />)
  await user.click(screen.getByTestId("stock-card-AAPL"))
  expect(screen.getByTestId("asset-panel-AAPL")).toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/__tests__/stock-card.test.tsx`
Expected: FAIL — still renders inline AssetDetail

**Step 3: Modify StockCard**

In `web/src/components/dashboard/stock-card.tsx`:

1. Replace `import { AssetDetail }` with `import { AssetPanel } from "./panel"`
2. Remove the inline `AssetDetail` rendering at the bottom of the component
3. Instead, render `<AssetPanel>` with `isOpen={expanded}` and `onClose={() => setExpanded(false)}`
4. Remove `expanded` CSS classes that make the card span full width (`col-span-full`)
5. Keep the data fetching logic — pass `scoreData` to `AssetPanel` as `scoredResult`

Key changes in the JSX:
- Remove the `col-span-full` and expanded-specific classes from the card div
- Remove the three conditional blocks at the bottom (loading, error, AssetDetail)
- Add `<AssetPanel isOpen={expanded && !!scoreData} onClose={() => setExpanded(false)} ticker={pick.ticker} scoredResult={scoreData!} />` after the card div (outside the card, since it portals anyway)

**Step 4: Run tests to verify they pass**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/__tests__/stock-card.test.tsx`
Expected: PASS

**Step 5: Run all dashboard tests**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/dashboard/`
Expected: All PASS. Some tests may need mock updates for the removed `AssetDetail` import.

**Step 6: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx web/src/components/dashboard/__tests__/stock-card.test.tsx web/src/components/dashboard/index.ts
git commit -m "feat(web): wire AssetPanel slide-over into StockCard, replace inline detail"
```

---

## Task 14: Visual QA — Run Dev Server and Verify

**Step 1: Start the dev server**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next dev`

**Step 2: Navigate to dashboard**

Open `http://localhost:3000/dashboard` in browser. Verify:
- Stock cards render normally (no expanded state changes)
- Clicking a card opens the slide-over panel from the right
- Panel shows executive header with ticker, score, signal
- Panel has two-column layout with chart on left, KPIs on right
- Backdrop dims the card grid
- Clicking backdrop or X closes the panel
- Time range selector is interactive
- Factor breakdown shows redesigned rows with sub-score chips
- KPI grid shows institutional metrics (may show dashes if no price history)
- Insight cards show strengths/risks/commentary
- Valuation section shows method bars
- Filters section shows pass/fail with expandable detail
- Score history table renders at bottom

**Step 3: Check dark-only styling**

Verify the panel uses absolute dark colors regardless of system theme. Toggle system light/dark mode — the panel should always be dark.

**Step 4: Check animations**

- Panel slide-in should be smooth (400ms)
- Content should stagger-fade
- Reduced motion: verify content appears instantly

**Step 5: Fix any visual issues found**

Address any spacing, color, or layout issues discovered during QA.

**Step 6: Commit fixes**

```bash
git add -u
git commit -m "fix(web): visual QA fixes for asset panel"
```

---

## Task 15: Update Barrel Exports

**Files:**
- Modify: `web/src/components/dashboard/index.ts`

**Step 1: Add panel export**

Add to `web/src/components/dashboard/index.ts`:

```tsx
export { AssetPanel } from "./panel"
```

**Step 2: Verify build**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next build`
Expected: Build succeeds with no errors.

**Step 3: Run full test suite**

Run: `cd /Users/brandon/repos/margin_invest/web && npx vitest run`
Expected: All tests pass.

**Step 4: Commit**

```bash
git add web/src/components/dashboard/index.ts
git commit -m "feat(web): export AssetPanel from dashboard barrel"
```

---

## Summary

| Task | Component(s) | Complexity |
|------|-------------|------------|
| 1 | PanelBackdrop | Low |
| 2 | TimeRangeSelector | Low |
| 3 | ExecutiveHeader | Medium |
| 4 | ScoreChart + ChartTooltip + ScoreContext | High |
| 5 | FactorRow + SubScoreChips | Medium |
| 6 | PanelFactorBreakdown | Medium |
| 7 | KpiCell + KpiGrid | Medium |
| 8 | InsightCard + InsightPanel | Medium |
| 9 | PanelValuation | Medium |
| 10 | PanelFilterList | Medium |
| 11 | ScoreHistoryTable | Medium |
| 12 | AssetPanel (orchestrator) | High |
| 13 | StockCard integration | Medium |
| 14 | Visual QA | Manual |
| 15 | Barrel exports + build verify | Low |

Tasks 1-11 are independent and can be parallelized. Task 12 depends on 1-11. Task 13 depends on 12. Tasks 14-15 are sequential.
