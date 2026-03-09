# Homepage Content Expansion — Design

**Date:** 2026-03-09
**Status:** Approved

## Problem

After Phase 3 craft layer work (pricing scroll-pinning removal, authority strip elevation, border radius unification), the homepage feels sparse. The page jumps from Evidence (proof panel) directly to Pricing (buy now) with no narrative bridge. There is no "how it works" explanation, no live results showcase, and no feature deep-dives.

## Solution

Add three new sections between Evidence and Pricing, all wired to live data from the existing `HomepageData` fetch (no new API endpoints).

### New Page Flow

```
Hero → Authority Strip → Evidence → How Engine Works → What Survives → Three Pillars → Pricing → FAQ → Footer
```

Narrative arc: credibility → process → proof → depth → conversion → objections.

## Section Designs

### A. How The Engine Works

A 4-step horizontal pipeline visualization showing the live scoring funnel:

| Step | Label | Data Source | Description |
|------|-------|-------------|-------------|
| 1 | SCAN | `total_universe` | "Every US-listed equity, daily" |
| 2 | ELIMINATE | `eligible_count` | "6 forensic filters. Beneish, Altman, liquidity, more." |
| 3 | SCORE | `total_scored` | "5-factor composite. Sector-neutral percentile ranks." |
| 4 | SURFACE | `surviving_count` | "Only the strongest survive all gates." |

Each step rendered as a terminal-card column with step number, monospace label, live count (large number), and one-line description. Connecting arrows or flow indicators between steps. Desktop: horizontal 4-column grid. Mobile: vertical stack.

Visual: terminal aesthetic — `bg-bg-elevated`, `border-border-subtle`, monospace labels, accent status dots. Section header: "HOW THE ENGINE WORKS" in monospace.

### B. What Survives (Results Showcase)

Display top 3 candidates from `HomepageData.candidates` as compact proof cards. Each card shows:
- Ticker (large) + company name
- Composite score (large display number)
- 3 factor bars: Quality, Value, Momentum (using existing `PercentileBar` or simplified version)
- Sector tag
- Scored-at timestamp (relative, e.g. "2h ago")

Below the cards: a summary stat line using live data:
"{total_scored} stocks scored · {total_universe - eligible_count} eliminated · {surviving_count} survived · Last cycle: {last_updated}"

Visual: 3-column grid inside a terminal panel (matching evidence section pattern — `bg-bg-elevated`, `border-border-subtle`, monospace header "CURRENT CYCLE RESULTS"). Viewport-enter fade with stagger.

Data: `HomepageData.candidates` (first 3), plus `total_scored`, `total_universe`, `eligible_count`, `surviving_count`, `last_updated`.

### C. Three Pillars (Feature Deep-Dives)

Three feature blocks in a vertical stack, each with explanatory text and a live data visualization:

**Pillar 1: Elimination Filters**
- Text: headline + description of the 6 filters
- Live visual: funnel ratio — "{eligible_count} of {total_universe} passed ({elimination_rate}% eliminated)"
- List the 6 filter names with checkmark icons
- Example: pick `candidates[0]` and show "{ticker}: {filters_passed}/{filters_total} filters passed"

**Pillar 2: Multi-Factor Scoring**
- Text: headline + description of 5-factor composite
- Live visual: pick `candidates[0]` and render its 5 factor percentile bars (Quality, Value, Momentum, Sentiment, Growth) with the composite score
- Shows what a real forensic breakdown looks like

**Pillar 3: Sector-Neutral Ranking**
- Text: headline + description of why sector-neutral matters
- Live visual: sector distribution from `allPicks` — count survivors per GICS sector, render as compact horizontal bars or tag counts
- Proves the system surfaces stocks across all sectors, not just tech

Visual: each pillar is a terminal-card with monospace header. Alternating layout on desktop (text left / visual right, then flip). Mobile: stacked. Section header: "THREE PILLARS" in monospace.

## Data Flow

All data comes from the existing `HomepageData` interface and server fetch in `page.tsx`. The `HomepageClient` component already receives this data and passes it to child sections. The new sections receive the same `data` prop.

```
page.tsx (server) → serverFetch("/api/v1/homepage") → HomepageClient → new sections
```

No new API endpoints. No new data types. The `HomepageData` interface already has all required fields. The `CandidateCard` type already has all factor percentiles, sector, filters_passed, filters_total, and scored_at.

## Components

New files to create:
- `web/src/components/landing/how-it-works-section.tsx`
- `web/src/components/landing/results-showcase-section.tsx`
- `web/src/components/landing/pillars-section.tsx`

Modified files:
- `web/src/components/landing/homepage-client.tsx` — add 3 new sections between Evidence and Pricing, pass `data` prop

## Animation

All three sections use the same viewport-enter fade pattern as FAQ and pricing: GSAP ScrollTrigger with `once: true`, `start: "top 85%"`, fade from `opacity: 0, y: 20` with stagger where applicable.

## Success Criteria

- Three new sections render with live data from HomepageData
- All numbers update when scoring data changes (no hardcoded values for dynamic data)
- Graceful fallback when data is null (show section structure with dashes or "—" for missing values)
- Page narrative flows: credibility → process → proof → depth → conversion
- Existing tests pass
- New sections have basic render tests
- `cd web && npx vitest run` passes
- `cd web && npx eslint --fix .` clean
