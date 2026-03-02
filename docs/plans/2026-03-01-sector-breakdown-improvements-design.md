# Sector Breakdown Chart Improvements

**Date:** 2026-03-01
**Status:** Approved

## Problem

The ProofSectorChart component on the landing page has three issues:

1. **Data Completeness** — Only Exceptional and High tier candidates appear. Medium tier is excluded because the homepage builds `allPicks` from `data.picks` only, and the API's picks query filters to `conviction_level IN ('exceptional', 'high')`. Medium-tier candidates exist in `data.watchlist` but are never passed to the chart.

2. **Dark Mode Hover** — When a bar is hovered in dark mode, Recharts applies a default white overlay that breaks theme consistency. There is no custom hover styling in the component.

3. **Layout Imbalance** — Sector Breakdown sits next to Correlation Heatmap (which is visually dense). Historical Chart sits alone in the last row. The heatmap is cramped at 50% width.

## Solution

### 1. Data Completeness

**File:** `web/src/app/page.tsx`

Merge `data.picks` and `data.watchlist` when building `allPicks`. Convert `WatchlistItem` to `CandidateCard` shape with sensible defaults for fields that only exist on `PickSummary`:

```typescript
function watchlistToCandidateCard(item: WatchlistItem): CandidateCard {
  return {
    ticker: item.ticker,
    name: item.name,
    sector: item.sector ?? "Unknown",
    composite_tier: item.composite_tier,
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
    filters_passed: 0,
    filters_total: 0,
  }
}
```

Then in `getHomepageData()`:

```typescript
const pickCards = data.picks.map(toCandidateCard)
const watchlistCards = (data.watchlist ?? []).map(watchlistToCandidateCard)
const allCards = [...pickCards, ...watchlistCards]
```

No API changes needed. The picks/watchlist separation is correct business logic.

### 2. Dark Mode Hover

**File:** `web/src/components/landing/proof-sector-chart.tsx`

- Add a `useIsDark()` hook (same pattern as existing `useIsNarrow()`) using `matchMedia("(prefers-color-scheme: dark)")`.
- Set `cursor={false}` on `<Tooltip>` to disable Recharts' default white overlay.
- When dark mode is active, pass `activeBar` prop to each `<Bar>` with a brightened fill:
  - Exceptional: `#24A070` (brightened from `#1A7A5A`)
  - High: `color-mix(in srgb, #24A070, transparent 40%)`
  - Medium: `color-mix(in srgb, #E0BC5A, transparent 40%)`
- When light mode is active, omit `activeBar` so Recharts uses its defaults.

### 3. Layout Rebalancing

**File:** `web/src/components/landing/proof-section.tsx`

Reorder the five ProofCard children:

```
Row 1: Factor Transparency  | System Selectivity
Row 2: Sector Breakdown      | Historical Application
Row 3: Correlation Heatmap   (full-width, md:col-span-2)
```

Implementation:
- Swap the JSX order of Sector Breakdown and Correlation Heatmap cards (positions 3 and 4).
- Wrap the Heatmap ProofCard in a div with `md:col-span-2` (or apply directly to the card).
- No other sizing changes — cards already use 100% width via ResponsiveContainer.

### 4. Tests

- `proof-sector-chart.test.tsx`: Add test case with medium-tier candidates verifying they render.
- Verify card order if any proof-section tests assert ordering.
- Add a unit test for the `watchlistToCandidateCard` conversion.

## Out of Scope

- No API route changes.
- No changes to CorrelationGrid internals.
- No mobile layout changes (single-column stacking stays as-is).
- No changes to light mode hover behavior.

## Files Changed

| File | Change |
|------|--------|
| `web/src/app/page.tsx` | Merge watchlist into allPicks |
| `web/src/components/landing/proof-sector-chart.tsx` | Dark mode hover fix |
| `web/src/components/landing/proof-section.tsx` | Card reorder + col-span |
| `web/src/components/landing/__tests__/proof-sector-chart.test.tsx` | Medium tier test |
