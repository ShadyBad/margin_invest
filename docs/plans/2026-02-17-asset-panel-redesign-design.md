# Asset Panel Redesign — Executive Dashboard Slide-Over

**Date:** 2026-02-17
**Status:** Approved
**Scope:** Replace current inline asset-detail expansion with a premium slide-over panel

---

## Problem

The current asset detail view expands inline below the stock card grid. It is card-heavy, visually repetitive, and reads like a data dump rather than an executive financial dashboard. The visual language does not carry through the dark glassmorphic identity established by the login page.

## Goal

When a candidate card is clicked, a slide-over panel emerges from the right presenting a premium executive financial performance dashboard. The panel must:

- Improve visual hierarchy with clear information priority
- Increase data density without clutter
- Introduce the composite score trend as the hero visualization (not price)
- Match the dark fintech branding of the login screen
- Feel modern, premium, and interactive
- Show AI-generated insights as structured cards (strengths/risks/commentary)

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Navigation model | Slide-over panel (right, 70vw) | Keeps card grid visible for context. Bloomberg/institutional pattern. |
| Hero chart data | Composite score over time | Score trend is Margin's unique value prop. Price charts are commodity. |
| Panel internal layout | Split dashboard (60/40 two-column) | Higher data density. Institutional dashboard feel. |
| AI insight format | Structured cards (strengths/risks/commentary) | More scannable than a text block. Color-coded by sentiment. |
| Bottom section | Score history table | Shows score evolution over time. Sortable, clean typography. |

---

## 1. High-Level UX Strategy

When a user clicks a stock card, a slide-over panel (70vw, min 900px, max 1200px) emerges from the right with a backdrop dimming the card grid. The panel is the asset's executive dossier — a 2-column financial dashboard.

**Information hierarchy (top to bottom, left to right):**

1. **What is this?** — Executive Header (sticky) — ticker, name, score, conviction, signal
2. **How is it performing?** — Hero Chart (left column) — composite score trend
3. **Why does it score this way?** — Factor Breakdown (left) + KPI Sidebar (right)
4. **What should I know?** — AI Insight Cards (right) — strengths, risks, commentary
5. **What's the valuation story?** — Valuation Breakdown (right)
6. **What changed?** — Score History Table (full-width bottom)

**Panel structure:**
- Left column: 60% — primary visualizations (chart, factors)
- Right column: 40% — supporting data (KPIs, insights, valuation, filters)
- Sticky header: always visible with key metrics
- Scrollable body: both columns scroll together

---

## 2. Executive Summary Header (Sticky)

Full-width horizontal bar, 72px height, fixed to panel top. Background `#0D0F12` with `border-b border-white/[0.06]`.

**Left cluster (identity):**
- Close button — X icon, 40x40 hit target
- Ticker — Inter Tight Semibold, 20px, white
- Company name — Inter Tight Regular, 13px, muted gray
- Conviction badge — existing component

**Center cluster (score + signal):**
- Composite score — Instrument Serif, 32px, accent `#1A7A5A`
- Score delta — Geist Mono, 13px, green/red. Format: `+3 triangle-up`
- Signal pill — existing ActionPill component

**Right cluster (controls):**
- Time range selector — pill toggle: 1M | 3M | 6M | 1Y | ALL. Active: accent bg. Inactive: transparent.
- View toggle — icon button for Data/Thesis switch

**Behavior:**
- Subtle box-shadow appears on scroll (intensity increases over first 8px)
- Score delta count-up animation on panel open
- Time range dispatches to hero chart

---

## 3. Hero Performance Chart (Left Column)

Full left-column width, 320px height, 24px padding. No card wrapper — lives directly on panel background.

**Chart type:** Recharts ComposedChart with smooth monotone area + line for composite score.

**Primary series — Composite Score:**
- Area gradient: `rgba(26, 122, 90, 0.25)` top to `rgba(26, 122, 90, 0)` bottom
- Line: `#1A7A5A`, 2px, monotoneX curve
- Data points: hidden, appear on hover as 6px circles

**Benchmark overlay (toggleable):**
- Dashed line, `rgba(255, 255, 255, 0.2)`, 1px
- Toggle in header (chart-compare icon)
- Green/red tint fill between score and benchmark when active

**Axes:**
- X: Geist Mono 11px, date labels auto-thinned by range
- Y: Hidden. Range always 0-100. Floating Y label on hover.
- Grid: horizontal only, `rgba(255, 255, 255, 0.04)`, lines at 25/50/75

**Tooltip (Custom Crosshair):**
- Glassmorphic card: `bg-[rgba(17,17,19,0.8)]`, `backdrop-blur-[8px]`, rounded-lg
- Contents: Date, Score (Instrument Serif 20px), Delta, Signal

**Animations:**
- Line draws left-to-right, 800ms ease-out on open
- Range change: crossfade 400ms, area fill fades in after line (200ms delay)
- Reduced motion: instant render

**Score Context Strip (below chart, 40px):**
- "Top 3% of universe" — accent, 13px
- "Scored weekly" — tertiary, 13px
- "2h ago" with green dot — tertiary, 13px

---

## 4. Factor Breakdown (Left Column, Below Chart)

Replaces current flat percentile bars with expressive, scannable factor rows.

**Section header:** "Factor Breakdown" — Inter Tight Semibold, 16px. Right: opportunity type badge.

**Each Factor Row (80px tall):**

- **Line 1:** Factor name (Inter Tight Medium 14px) | Weight % (Geist Mono 12px, tertiary) | Score (Instrument Serif 24px, percentile-colored)
- **Line 2:** Full-width progress bar (4px, rounded, 5-tier color) | Interpretation text (12px, tertiary)
- **Line 3:** Sub-score chips (Geist Mono 11px, `bg-white/[0.04]`, rounded-md)

Rows separated by `border-b border-white/[0.06]`. Sorted by weight descending. Compounder: Quality, Value, Momentum, Capital Allocation, Catalyst. Mispricing: Value, Quality, Momentum, Catalyst.

Hover: row background `rgba(255,255,255,0.03)`, 200ms.

---

## 5. Right Column

### 5A: KPI Grid (Top)

Six metrics in a 2x3 grid. No borders, vertical alignment only.

**Each cell (48px tall):**
- Label: Inter Tight 11px, uppercase, tracking-wide, tertiary
- Value: Geist Mono 20px, white
- Context: Inter Tight 11px, percentile-colored

**KPIs:** Sharpe Ratio, Max Drawdown, Volatility, Avg Profit Margin, Allocation Weight, Margin of Safety.

Hover: background pulse + micro-tooltip with calculation detail (300ms hover delay). Pro-gated.

### 5B: AI Insight Cards

Three cards stacked with 12px gap. Each has a 4px left accent border and tinted background.

**Card 1 — Strengths:**
- Border: `#1A7A5A`, bg: `rgba(26, 122, 90, 0.04)`
- Header: shield-check icon + "Strengths" in accent
- Body: 2-4 bullet points, 13px

**Card 2 — Risk Flags:**
- Border: `#C74B50`, bg: `rgba(199, 75, 80, 0.04)`
- Header: alert-triangle icon + "Risk Flags" in bearish
- Body: 2-4 bullet points

**Card 3 — Commentary:**
- Border: `rgba(255, 255, 255, 0.15)`, bg: `rgba(255, 255, 255, 0.02)`
- Header: sparkles icon + "Analysis" in secondary
- Body: 2-3 sentence narrative

**Below cards:** Confidence bar — label left, percentage right, 3px animated fill. Pro-gated.

### 5C: Valuation Breakdown

**Intrinsic value callout:**
- "Intrinsic Value: $28.50" — Geist Mono 16px
- "Current: $21.00 - Margin of Safety: 26%" — 12px, accent for MoS

**Method bars (4x):**
- DCF, EV/FCF, EV/EBIT, Shareholder Yield
- Label left (12px), value right (Geist Mono 12px), 3px proportional bar

### 5D: Elimination Filters

Header: "Filters" + pass count pill (e.g., "2/3").

Each row (32px): status icon (check/X) + name (13px) + detail (Geist Mono 11px, right-aligned). Failed rows get `rgba(199, 75, 80, 0.04)` background. Click to expand threshold detail.

---

## 6. Score History Table (Full-Width Bottom)

Spans full panel width below both columns. Header: "Score History" + row count.

**Columns:**

| Column | Font | Size | Notes |
|--------|------|------|-------|
| Date | Geist Mono | 12px | MMM DD, YYYY |
| Score | Instrument Serif | 16px | Percentile-colored |
| Delta | Geist Mono | 12px | Green up-arrow / red down-arrow |
| Signal | SignalBadge | compact | Existing component |
| Conviction | Inter Tight | 12px | Text only, percentile-colored |
| Key Change | Inter Tight | 12px | Largest factor move or "Stable" |

**Styling:**
- No outer borders, no cell borders
- Header: tertiary, 11px, uppercase, tracking-wide, bottom border
- Rows: 44px height, `border-b border-white/[0.03]`
- Hover: `rgba(255,255,255,0.03)`, 150ms
- Sortable columns with chevron indicator
- Default sort: date descending
- 20+ rows: "Show all" / "Last 10" toggle pill

---

## 7. Design System (Panel-Specific)

### Colors

```
Panel Backgrounds:
  panel-bg:              #0B0D10
  panel-elevated:        #0D0F12
  panel-surface:         #111318
  panel-subtle:          rgba(255, 255, 255, 0.03)

Text:
  panel-text:            #E8E6E3
  panel-secondary:       #9A9590
  panel-tertiary:        #5C5955

Accent:
  accent:                #1A7A5A
  accent-glow:           rgba(26, 122, 90, 0.15)
  bearish:               #C74B50
  bearish-glow:          rgba(199, 75, 80, 0.04)
  warning:               #B8860B

Borders:
  panel-border:          rgba(255, 255, 255, 0.06)
  panel-border-subtle:   rgba(255, 255, 255, 0.03)
```

### Typography

| Context | Family | Weight | Size/Line-Height |
|---------|--------|--------|------------------|
| Header ticker | Inter Tight | Semibold | 20/24 |
| Header score | Instrument Serif | Regular | 32/36 |
| Score delta | Geist Mono | Regular | 13/16 |
| Chart axis | Geist Mono | Regular | 11/14 |
| Chart tooltip value | Instrument Serif | Regular | 20/24 |
| Factor name | Inter Tight | Medium | 14/18 |
| Factor score | Instrument Serif | Regular | 24/28 |
| Sub-scores | Geist Mono | Regular | 11/14 |
| Interpretation | Inter Tight | Regular | 12/16 |
| KPI label | Inter Tight | Regular | 11/14, uppercase, tracking 0.05em |
| KPI value | Geist Mono | Regular | 20/24 |
| Insight header | Inter Tight | Medium | 13/16 |
| Insight body | Inter Tight | Regular | 13/18 |
| Table header | Inter Tight | Regular | 11/14, uppercase, tracking 0.05em |
| Table cell | Geist Mono | Regular | 12/16 |

### Spacing

8px grid. Section gap: 24px. Inner padding: 24px horizontal, 16px vertical. Card gap: 12px. KPI grid: 16px horizontal, 20px vertical.

### Glassmorphic Surfaces

Chart tooltip and header-on-scroll only:
```
backdrop-filter: blur(8px)
background: rgba(17, 17, 19, 0.8)
border: 1px solid rgba(255, 255, 255, 0.06)
border-radius: 12px
```

---

## 8. Interaction & Animation

### Panel Open Sequence (5 stages)

| Stage | Delay | Element | Animation | Duration |
|-------|-------|---------|-----------|----------|
| 0 | 0ms | Backdrop | opacity 0 to 0.5 | 300ms ease-out |
| 1 | 0ms | Panel | translateX(100%) to 0 | 400ms cubic-bezier(0.22,1,0.36,1) |
| 2 | 200ms | Header content | fade + slideY(8px to 0), 30ms stagger | 300ms each |
| 2 | 200ms | Score | count-up from 0 | 600ms ease-out |
| 3 | 350ms | Chart line | draw left-to-right | 800ms ease-out |
| 3 | 350ms | Factor rows | fade + slideY(6px), 40ms stagger | 250ms each |
| 4 | 400ms | KPI cells | fade, 30ms stagger (2x3 LTR, TTB) | 200ms each |
| 4 | 400ms | Insight cards | fade + slideY, 60ms stagger | 250ms each |

**Panel close:** Panel slides right 300ms, backdrop fades 200ms, content opacity 0 at 150ms.

**Reduced motion:** All stages instant render. Opacity transitions 150ms only.

### Chart Interactions

- Time range change: data crossfade 400ms, line redraws if range expanded
- Crosshair: direct DOM positioning (no animation delay), tooltip 100ms fade
- Benchmark toggle: dashed line draws 500ms, fill between fades 200ms

### Micro-Interactions

- KPI hover: value scale 1.02, 150ms. Tooltip after 300ms delay.
- Factor row hover: background 200ms
- Insight card hover: accent border 4px to 6px, background brightens
- Table row hover: background 150ms
- Filter row click: height expand with AnimatePresence
- Header shadow: interpolates 0 to 1 over first 16px scroll

### Loading States

- Panel skeleton: pulsing rectangles matching layout structure
- Chart: single pulsing rectangle, 320px
- KPI: six small rectangles, 50ms stagger
- Insights: three card rectangles

---

## 9. Component Architecture

### Component Tree

```
<AssetPanel>                          -- Portal, open/close state
  <PanelBackdrop />                   -- Click-to-close overlay
  <PanelContainer>                    -- Slide animation, scroll, sticky header
    <ExecutiveHeader />               -- Sticky, full-width
      <CloseButton />
      <AssetIdentity />               -- Ticker, name, conviction badge
      <ScoreDisplay />                -- Animated score, delta, signal pill
      <TimeRangeSelector />           -- 1M/3M/6M/1Y/ALL pills
    <PanelBody>                       -- 2-column grid
      <LeftColumn>
        <ScoreChart />                -- Recharts hero chart
          <ChartTooltip />            -- Glassmorphic crosshair
          <ScoreContext />            -- "Top 3% . Scored weekly . 2h ago"
        <FactorBreakdown />           -- Redesigned factor list
          <FactorRow />[]
            <PercentileBar />         -- Existing, reused
            <SubScoreChips />
      <RightColumn>
        <KpiGrid />
          <KpiCell />[]
        <InsightPanel />              -- Pro-gated
          <InsightCard />             -- x3 (strengths, risks, commentary)
          <ConfidenceBar />           -- Existing, reused
        <ValuationBreakdown />
        <FilterList />
          <FilterRow />[]
    <ScoreHistoryTable />             -- Full-width bottom
```

### Key Props

```typescript
interface AssetPanelProps {
  isOpen: boolean
  onClose: () => void
  ticker: string
  scoredResult: ScoredResult
  priceHistory?: PricePoint[]
}

interface ExecutiveHeaderProps {
  ticker: string
  companyName: string
  compositeScore: number
  scoreDelta: number
  conviction: ConvictionLevel
  signal: Signal
  opportunityType: 'compounder' | 'mispricing'
  timeRange: TimeRange
  onTimeRangeChange: (range: TimeRange) => void
  onClose: () => void
}

type TimeRange = '1M' | '3M' | '6M' | '1Y' | 'ALL'

interface ScoreChartProps {
  data: ScoreDataPoint[]
  timeRange: TimeRange
  showBenchmark: boolean
  benchmarkData?: ScoreDataPoint[]
}

interface FactorBreakdownProps {
  factors: FactorScore[]
  winningTrack: 'compounder' | 'mispricing'
}

interface FactorRowProps {
  name: string
  weight: number
  score: number
  interpretation: string
  subScores: { label: string; value: number }[]
}

interface KpiGridProps {
  sharpeRatio: number | null
  maxDrawdown: number | null
  volatility: number | null
  avgProfitMargin: number | null
  allocationWeight: number | null
  marginOfSafety: number | null
}

interface InsightPanelProps {
  strengths: string[]
  risks: string[]
  commentary: string
  confidence: number
}

interface ValuationBreakdownProps {
  intrinsicValue: number
  currentPrice: number
  marginOfSafety: number
  methods: { name: string; value: number }[]
}

interface ScoreHistoryTableProps {
  history: ScoreHistoryRow[]
  defaultSort?: 'date' | 'score'
}

interface ScoreHistoryRow {
  date: string
  score: number
  delta: number
  signal: Signal
  conviction: ConvictionLevel
  keyChange: string
}
```

### State Management

No global state library. Panel-local state only:
- `timeRange` — useState in AssetPanel, passed to header and chart
- `showBenchmark` — useState, toggled from header
- `expandedFilters` — useState<Set<string>> in FilterList
- `tableSortKey` / `tableSortDir` — useState in ScoreHistoryTable
- Score history data fetched on panel open via useEffect

### Reused Components

- PercentileBar, ConvictionBadge, SignalBadge, ActionPill, ProGate, AnimatedScore, ConfidenceBar

### New Components (17 total)

| Component | Complexity |
|-----------|-----------|
| AssetPanel | High |
| PanelBackdrop | Low |
| PanelContainer | Medium |
| ExecutiveHeader | Medium |
| TimeRangeSelector | Low |
| ScoreChart | High |
| ChartTooltip | Medium |
| ScoreContext | Low |
| FactorRow | Medium |
| SubScoreChips | Low |
| KpiGrid | Medium |
| KpiCell | Low |
| InsightPanel | Medium |
| InsightCard | Low |
| ValuationBreakdown | Medium |
| FilterRow | Low |
| ScoreHistoryTable | Medium |

---

## 10. Tech Stack

- **React 19** + **Next.js 15** (existing)
- **Recharts 3.7** (existing) for hero chart
- **Framer Motion 12** (existing) for panel/content animations
- **Tailwind CSS 4** (existing) with panel-specific token overrides
- **React Portal** for panel mounting (outside main layout DOM)
- No new dependencies required

---

## 11. Constraints

- Dark mode only (panel is always dark regardless of system theme)
- Desktop-first (mobile: panel becomes full-screen overlay)
- No card spam — sections defined by spacing and borders, not card wrappers
- No default chart styling — all Recharts defaults overridden
- Hierarchy and readability over data exhaustiveness
- Same inputs must produce same outputs (deterministic rendering)
