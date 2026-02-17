# Candidate Detail View Redesign

**Date:** 2026-02-17
**Approach:** Institutional Expansion (enhanced inline expand)
**Constraint:** No font family changes. Inter Tight + Geist Mono only.

## Overview

Transform the dashboard candidate detail view (expanded stock card) into a high-end hedge fund terminal experience with conversion-optimized Pro gating and CSS-driven ambient effects. The card remains an inline expansion but the interior is restructured with a 12-column grid, dramatic spacing, staggered entry animation, and institutional-grade metrics.

## Layout Blueprint

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER BAR (12 cols)                                       │
│  Ticker(700,2xl) · Name(400) · Score(700,3xl,mono) ·       │
│  ConvictionBadge · ActionPill · Track · [Toggle]            │
├─────────────────────────────────────────────────────────────┤
│  V2 METRICS ROW (12 cols)                                   │
│  Asymmetry · Max Position · Timing Signal · MoS             │
├─────────────────────────────────────────────────────────────┤
│  HERO PRICE CHART (12 cols, h-[320px])                     │
│  Gradient underfill · Animated line draw · Crosshair hover │
│  Benchmark toggle (vs SPY) · Range selector (1M/3M/6M/1Y) │
├───────────────┬───────────────┬─────────────────────────────┤
│  INSTITUTIONAL METRICS (12 cols, 3-col grid)  [PRO-GATED]  │
│  Sharpe Ratio │  Max Drawdown │  Volatility                │
│  Avg Profit   │  Risk Class   │  Allocation Weight         │
│  Margin       │               │                             │
├───────────────┴───────────────┴─────────────────────────────┤
│  UPGRADE CTA (free users only)                              │
│  "Unlock institutional-grade analytics" · Pro Insight badge │
├─────────────────────────────────────────────────────────────┤
│  AI PERFORMANCE SUMMARY (12 cols) [PRO-GATED]              │
│  Composed factor interpretation · Confidence score bar      │
├────────────────────────────┬────────────────────────────────┤
│  LEFT (7 cols)             │  RIGHT (5 cols)                │
│  Factor Breakdown          │  Elimination Filters           │
│  · Quality w/ sub-scores   │  Valuation Methods             │
│  · Value w/ sub-scores     │  Metadata                      │
│  · Momentum w/ sub-scores  │  Signal History                │
│  · Cap Alloc / Catalyst    │                                │
└────────────────────────────┴────────────────────────────────┘
```

Section spacing: 32px between major sections. Card padding: 32px when expanded.

## Entry Animation Sequence

All animations use `ease-out`, `duration: 0.4s` unless specified. `useReducedMotion` disables all.

| Time | Element | Animation |
|------|---------|-----------|
| 0ms | Border-top + header | Fade in |
| 100ms | Chart container | Appears, line begins SVG stroke-dashoffset draw (800ms) |
| 300ms | Chart gradient underfill | Fade in beneath line |
| 500ms | Institutional metrics | Each cell fades in, translateY 8→0, 75ms stagger L→R |
| 700ms | AI summary | Fade in (or gated placeholder) |
| 800ms | Factor + metadata columns | Fade in together |
| 900ms | Chart ambient glow | Single box-shadow pulse (1.5s) |

## Hero Performance Graph

Recharts `ComposedChart` upgraded:

- **Height**: 240px → 320px
- **Line**: 2px stroke, `type="monotone"` bezier curves
- **Gradient underfill**: SVG `<linearGradient>` from `accent/20` at line to `transparent` at x-axis, rendered as `<Area>` behind `<Line>`
- **Animated line draw**: CSS `stroke-dasharray` + `stroke-dashoffset` animation, 800ms ease-out
- **Custom crosshair tooltip**: vertical dashed line + horizontal reference + floating card with Date, Close, Volume, Day Change in `font-mono`
- **Benchmark toggle**: "vs SPY" button next to range selector. Overlays second line, normalizes both to % change. Data from `/api/v1/prices/benchmark?ticker=SPY&range=1Y`
- **Reference lines**: buy/sell targets with pill badge labels. Shaded `<ReferenceArea>` between buy and sell at `accent/0.04`
- **Volume bars**: opacity 0.15 → 0.08
- **Range selector**: add `font-mono tracking-wide`, active state gets `shadow-sm`
- **Axis ticks**: `fontFamily: var(--font-geist-mono)`

## Institutional Metrics Stack

New section between chart and factor breakdown. 3x2 grid on md+, stacks on mobile.

**Per metric cell:**
- Container: `bg-bg-subtle/50 border border-border-primary/30 rounded-sm p-5`
- Label: `text-xs font-medium tracking-widest uppercase text-text-tertiary`
- Value: `text-2xl font-mono font-bold text-text-primary`
- Context: `text-xs text-text-secondary` (sector comparison or trend)
- Hover: `bg-bg-subtle/80` + `shadow-sm`

**Metrics:** Sharpe Ratio, Max Drawdown, Volatility, Avg Profit Margin, Risk Classification, Allocation Weight.

**Data source:** Client-side computation from existing `price_history` and factor sub-scores via `computeInstitutionalMetrics()`. Sector comparisons are placeholder initially.

## Pro Gating

**Gated sections:** Institutional metrics (6 cells), AI performance summary, confidence score.

**Free sections (always visible):** Price chart, factor breakdown, filters, valuation, metadata, signals.

**Blur treatment:**
- Value + context line: `filter: blur(6px)`, `select-none pointer-events-none`
- Lock icon: 12px, `text-text-tertiary/60`, inline after label
- Cell background: `bg-bg-subtle/30` (more transparent)
- `aria-hidden="true"` on blurred content

**Upgrade CTA (free users only):**
- Full-width row below metrics grid
- `bg-accent/[0.04] border border-accent/10 rounded-sm py-3 px-5`
- Lock icon + "Unlock institutional-grade analytics" + "Pro Insight" badge + arrow
- Hover: `bg-accent/[0.06]`
- Links to Stripe checkout or `/settings` billing

## AI Performance Summary

- Full-width card below metrics, above factor columns
- 2-3 sentence composed interpretation from `getFactorInterpretation()` across all factors
- Confidence score: reuses `PercentileBar` component, `h-2 rounded-full`, value right-aligned in `font-mono`
- Pro-gated with same blur treatment

## Typography Hierarchy

No font family changes. Authority through weight, scale, spacing, and mono usage.

| Element | Classes |
|---------|---------|
| Ticker | `text-2xl font-bold tracking-tight` |
| Company name | `text-sm font-normal text-text-tertiary` |
| Composite score | `text-3xl font-mono font-bold text-accent` |
| Section headings | `text-xs font-semibold tracking-wide uppercase text-text-tertiary` |
| Metric labels | `text-xs font-medium tracking-widest uppercase text-text-tertiary` |
| Metric values | `text-2xl font-mono font-bold text-text-primary` |
| Metric context | `text-xs text-text-secondary` |
| Factor percentile | `text-lg font-mono font-bold text-accent` |
| Factor weight | `text-xs font-mono text-text-tertiary` |
| Sub-score labels | `text-xs text-text-secondary tracking-wide` |
| Metadata labels | `text-xs text-text-tertiary uppercase tracking-wide` |
| Metadata values | `text-sm font-mono text-text-primary` |
| Chart axis ticks | `fontSize: 10, fontFamily: var(--font-geist-mono)` |

**Spacing:** 32px section gaps, 20px within-section gaps, 10px between sub-score bars, 8px label-to-value.

## CSS Ambient System

No Three.js. All GPU-composited CSS effects.

1. **Chart glow**: `@keyframes chartPulse` — `box-shadow: 0 0 40px 0 accent/0.08` → transparent. 1.5s, once.
2. **Expanded card depth**: shadow deepens to `0 4px 24px rgba(0,0,0,0.15)`, border transitions to `accent/15`. 500ms ease-out.
3. **Section gradient** (dark mode only): `radial-gradient(ellipse at 50% 0%, accent/0.02, transparent 60%)` on card interior.
4. **Metric cell hover**: `bg-bg-subtle/80` + `shadow-sm`, 200ms transition.
5. **Percentile bar enhancement**: gradient fill `accent/80` → `accent`. Exceptional (90+) scores get faint `box-shadow: 0 0 8px accent/0.15`.

## Factor Breakdown Upgrades

- Dividers between factors: `border-b border-border-primary/30 pb-6` except last
- Each factor staggers in with 100ms delay
- Interpretation text: `leading-relaxed mb-3`
- Sub-score spacing: `space-y-2.5`

## Right Column Upgrades

- **Reorder**: Filters → Valuation → Metadata → Signals (valuation moves up)
- Section dividers: `border-b border-border-primary/20 pb-5 mb-5`
- Filters: colored checkmarks (`text-bullish`), right-aligned "passed" in `font-mono`
- Valuation: wider label column (w-32), taller bars (h-5), `font-mono` values
- Metadata: `grid grid-cols-[auto_1fr]` layout, `font-mono` values
- Signals: `font-semibold` signal names, `font-mono` prices, quieter arrow

## New Files

| File | Purpose |
|------|---------|
| `components/dashboard/institutional-metrics.tsx` | 3x2 metric grid with Pro blur gating |
| `components/dashboard/ai-summary.tsx` | Composed factor interpretation + confidence bar |
| `components/dashboard/pro-gate.tsx` | Reusable blur overlay + lock icon + CTA |
| `components/dashboard/custom-crosshair.tsx` | Chart tooltip with crosshair lines |
| `lib/compute-institutional-metrics.ts` | Derives Sharpe, drawdown, volatility from price_history |
| `lib/compose-ai-summary.ts` | Combines factor interpretations into summary |
| `lib/hooks/use-subscription-tier.ts` | Returns `"free" | "pro"` from billing status |

## Modified Files

| File | Scope |
|------|-------|
| `asset-detail.tsx` | Major rewrite — new grid layout, animation, Pro gating |
| `price-chart.tsx` | Major rewrite — gradient, line draw, crosshair, benchmark |
| `stock-card.tsx` | Minor — expanded shadow/border/padding |
| `factor-breakdown.tsx` | Moderate — dividers, typography, spacing, stagger |
| `valuation-breakdown.tsx` | Moderate — typography, bar height, mono values |
| `signal-timeline.tsx` | Minor — typography, mono prices |
| `filter-list.tsx` | Minor — grid layout, checkmark colors |

## Unchanged

- Font imports (`layout.tsx`)
- Color tokens (`tokens.ts`, `globals.css`)
- Card collapsed state
- Picks grid layout
- API endpoints and engine code
- Three.js (not used on dashboard)
- Mobile responsive behavior (grid collapses to 1 col)

## Performance Budget

- Zero new JS libraries
- `computeInstitutionalMetrics` memoized via `useMemo`
- Chart animation: CSS `stroke-dashoffset` (GPU-composited)
- Blur gating: CSS `backdrop-filter` (GPU-composited)
- Framer Motion: 6-8 elements, `opacity` + `translateY` only
- Target: 0 layout shifts, 0 reflows, 60fps
