# Premium Design Phase 4 — Factor Signature, Hero, Dashboard Hierarchy

## Overview

Three high-leverage design changes to elevate perceived quality from "competent developer build" to "premium financial platform." All changes are derived from the product's own logic — the five-factor model, the elimination funnel, and the "Discipline. Engineered." brand identity.

**Branch:** `feat/premium-design-phase4`

## 1. Factor Signature — Signature Visual Element

### What It Is

A reusable SVG component that visualizes a stock's five-factor profile as a spectrograph-style measurement readout. Five horizontal tracks, each with a precision marker dot at the percentile position. A thin connecting polyline between the dots creates each stock's unique "signature shape."

### Visual Specification

```
QUALITY   ──────────────────────────────●  95
VALUE     ──────────────────●              68
MOMENTUM  ─────────────────────────●       84
SENTIMENT ────────────────────────●        79
GROWTH    ──────────────────────────●      88
```

- **Tracks**: Thin horizontal lines (`stroke: rgba(237,233,227,0.06)`) spanning the full width
- **Fill bars**: Subtle colored rectangles from left edge to the marker position, using factor-specific colors at ~12% opacity
- **Marker dots**: Solid circles (radius 3-4px) at the exact percentile position, using factor-specific colors:
  - Quality: `#10B981` (percentile-exceptional)
  - Value: `#3BA5D0` (value pillar color)
  - Momentum: `#1A7A5A` (accent)
  - Sentiment: `#C9A84C` (gold-highlight)
  - Growth: `#22C55E` (bullish)
- **Connecting line**: `rgba(237,233,227,0.12)`, 1-1.5px, connects all 5 dots in order
- **Factor labels**: Left-aligned, mono font, 8-9px, `rgba(237,233,227,0.35)`
- **Percentile values**: Right-aligned, mono font, 9-10px, `rgba(237,233,227,0.5)`

### Size Variants

| Variant | Dimensions | Labels | Values | Fill Bars | Use Case |
|---------|-----------|--------|--------|-----------|----------|
| Full | ~340×160 | Full words (QUALITY, VALUE...) | Yes | Yes | Hero card, asset detail |
| Compact | ~260×110 | Abbreviations (Q, V, M, S, G) | Yes | Yes | Dashboard tier-1 card |
| Mini | ~160×50 | None | None | Yes | Dashboard tier-2 cards |
| Inline | ~80×10 | None | None | Dots only | Dashboard tier-3 rows |

### Component Interface

```tsx
interface FactorSignatureProps {
  factors: {
    quality: number | null   // 0-100 percentile, null = no data
    value: number | null
    momentum: number | null
    sentiment: number | null
    growth: number | null
  }
  variant: 'full' | 'compact' | 'mini' | 'inline'
  className?: string
}
```

**Null handling:** When a factor value is `null`, render the track line but omit the marker dot and fill bar. The connecting polyline skips null factors (connects only non-null dots). In the `inline` variant, null factors render as a dimmed ring (`opacity: 0.15`) instead of a filled dot. This matches `PickSummary` from the API, where `sentiment_percentile` and `growth_percentile` can be `null`.

### Animation (Entrance Only)

On mount, dots appear sequentially (80ms stagger) from top to bottom, with fill bars drawing in from the left. Connecting line traces after the last dot appears. Total entrance: ~600ms. Uses GSAP (already a dependency). Respects `prefers-reduced-motion`.

**Animation library note:** The FactorSignature internal animations use GSAP. Card-level entrance animations in the dashboard `TieredPicksList` should use Framer Motion (consistent with the existing dashboard patterns in `picks-grid.tsx`). The two libraries coexist without conflict — GSAP handles SVG internals, Framer Motion handles React component mounting.

### File Location

`web/src/components/visualizations/factor-signature.tsx`

This is a new shared location (not under `landing/` or `dashboard/`) because it's used across both surfaces.

## 2. Hero Section — Instrument Panel

### What Changes

Replace the current `SystemReportCard` (right column of hero) with an expanded **Instrument Panel** containing the Factor Signature at full size. The left column (headline, subtext, search) stays the same.

### Current vs. New

| Aspect | Current | New |
|--------|---------|-----|
| Right column | `SystemReportCard` — flat card with 5 progress bars | Instrument Panel — ticker/score header + Factor Signature (full variant) |
| Card glow | `box-shadow: 0 0 40px rgba(26,122,90,0.08)` | Same, with accent border `border-color: rgba(26,122,90,0.2)` |
| Card header | "SYSTEM REPORT" mono label + status dot | "Live Score — AAPL" mono label + status dot + relative timestamp |
| Score display | Score number + "Composite Score" label | Score number (larger, tier-colored) + ticker + company name + sector (omit if null) + tier badge |
| Factor display | 5 `FactorBars` (progress bars) | Factor Signature (full variant) |
| Dead zone | ~300px empty below search | Eliminated — taller card + reduced `min-height` from `90svh` to `auto` with `min-height: 80svh` |

### Layout Adjustments

- Hero `min-height`: Reduce from `90svh` to `80svh` (keeps the hero feeling substantial while eliminating the dead zone)
- Grid split: Keep `55%/45%` — works well
- Right column card: `max-w-md` (currently `max-w-sm`) to accommodate the wider Factor Signature
- Bottom fade gradient: Keep

### Files Modified

- `web/src/components/landing/sections/hero-section.tsx` — layout adjustments, update import from `SystemReportCard` to `InstrumentPanel`
- `web/src/components/landing/sections/system-report-card.tsx` — **rename file** to `instrument-panel.tsx`, rewrite component as `InstrumentPanel` using Factor Signature. Export name changes from `SystemReportCard` to `InstrumentPanel`.
- `web/src/components/landing/visualizations/factor-bars.tsx` — no changes, remains in current location (still used by other components)

## 3. Dashboard — Tiered Visual Hierarchy

### What Changes

Replace the current uniform `picks-grid` (6 identical `stock-card` components in a 3-column grid) with a tiered layout where visual weight mirrors conviction rank.

### Tier Structure

**Tier 1 — Hero Card (Pick #1)**
- Full width of main content area
- Two-column internal layout: score/ticker/tier (left) + Factor Signature compact variant (right)
- Accent border: `border-color: rgba(26,122,90,0.2)`
- Subtle glow: `box-shadow: 0 0 30px rgba(26,122,90,0.06)`
- Rank badge: `#1` in accent-colored pill
- Score: 42px mono, tier-colored
- Includes: company name, sector (omit if null), price, "Full report →" link

**Tier 2 — Medium Cards (Picks #2-3)**
- Two-column grid (`grid-cols-2`)
- Each card: score/ticker header + Factor Signature mini variant
- Standard border: `border-color: rgba(237,233,227,0.06)`
- No glow
- Rank badge: `#2`, `#3` in muted text
- Score: 28px mono, tier-colored

**Tier 3 — Compact Rows (Picks #4+)**
- Single-line rows, stacked vertically with 2px gap
- Each row: score (20px) | ticker | company name | inline factor dots | tier badge
- Minimal border: `border-color: rgba(237,233,227,0.04)`
- Inline factor dots: 5 colored circles in a row (Factor Signature inline variant), dot opacity proportional to percentile (≥80 = full, 60-79 = 0.7, 40-59 = 0.5, <40 = 0.3)

### Tier Determination Logic

```tsx
function getTier(index: number): 'hero' | 'medium' | 'compact' {
  if (index === 0) return 'hero'
  if (index <= 2) return 'medium'
  return 'compact'
}
```

**Layout by pick count:**
- **0 picks**: Render existing `EmptyState` component (no picks available message)
- **1 pick**: Hero card only (full width)
- **2 picks**: Hero card + 1 medium card (single column, not grid)
- **3 picks**: Hero card + 2 medium cards (2-column grid)
- **4+ picks**: Hero card + 2 medium cards + compact rows for the rest

The hero card always exists if there's at least 1 pick. With 2-3 picks, tier-2 medium cards are used (not compact) to avoid a visually lopsided layout.

### Component Architecture

```
TieredPicksList (new)
├── PickHeroCard (tier-1) — uses FactorSignature compact
├── PickMediumCard (tier-2) — uses FactorSignature mini
└── PickCompactRow (tier-3) — uses FactorSignature inline
```

Dashboard pick cards consume `PickSummary` from `@/lib/api/types` (not `CandidateCard`, which is the landing page type). The existing `StockCard` component is not modified — it's still used on the watchlist page.

### Files Modified

- `web/src/components/dashboard/picks-grid.tsx` — replace with `TieredPicksList` or refactor to use tiered rendering
- New: `web/src/components/dashboard/pick-hero-card.tsx`
- New: `web/src/components/dashboard/pick-medium-card.tsx`
- New: `web/src/components/dashboard/pick-compact-row.tsx`

### Market Context Sidebar

No changes. The right sidebar with Universe/Scored/Surviving/Sector Breakdown stays as-is.

## Design Tokens Used

All designs use existing tokens from `globals.css`. Factor-specific colors reuse existing semantic tokens (listed below). This is an intentional coupling — if factor identity colors need to diverge from their semantic counterparts in the future, add `--color-factor-*` aliases at that time.

| Token | Usage |
|-------|-------|
| `--color-bg-primary` (#0C1A13) | Page background |
| `--color-bg-elevated` (#12221A) | Card backgrounds |
| `--color-border-subtle` (rgba 0.06) | Standard card borders |
| `--color-accent` (#1A7A5A) | Tier-1 card border, rank badges |
| `--color-text-primary` (#EDE9E3) | Headings, ticker names |
| `--color-text-secondary` (#A39E96) | Body text |
| `--color-text-tertiary` (#6B6660) | Labels, timestamps |
| `--color-value` (#3BA5D0) | Value factor color |
| `--color-gold-highlight` (#C9A84C) | Sentiment factor color |
| `--color-bullish` (#22C55E) | Growth factor, bullish signals |
| `--color-percentile-exceptional` (#10B981) | Quality factor, strong scores |

## Testing Strategy

- Unit tests for `FactorSignature` component: renders correct number of tracks, dots positioned correctly, handles edge cases (all 0s, all 100s, missing data)
- Unit tests for tier determination logic
- Unit tests for each pick card variant
- Visual regression: screenshot tests comparing rendered output (optional, low priority)
- Existing dashboard and homepage tests must continue passing

## Implementation Order

1. **FactorSignature component** — the shared primitive. Build + test in isolation.
2. **Hero Instrument Panel** — integrate FactorSignature into the homepage hero card.
3. **Dashboard Tiered Layout** — build the three pick card variants + TieredPicksList.

Each step is independently deployable and testable.

## Out of Scope (Future Cycles)

- Landing page section variety (heading → grid monotony)
- Footer redesign
- Empty state improvements ("Target: N/A", "Score data unavailable")
- Component polish (status indicators, badges)
- Secondary page design
- Animation/motion system overhaul
