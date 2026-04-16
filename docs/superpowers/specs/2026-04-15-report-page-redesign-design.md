# Forensic Report Page Redesign — Technical Specification

**Date**: 2026-04-15
**Version**: 1.0
**Status**: Draft
**Design System**: Digital Horologist (see `2026-04-14-digital-horologist-redesign-design.md`)

## Summary

Redesign the asset detail report page (`/asset/[ticker]`) to embody the Digital Horologist aesthetic while eliminating redundancy and enforcing information hierarchy. The page consolidates 22 components into 14, cuts ~1,100 LOC, and restructures around the principle: **verdict first, evidence second, depth on demand**.

### Page Flow

```
Instrument Header (full-width)
  └─ Ticker, score, tier, signal, timestamp, watchlist, determinism

Vital Signs Strip (full-width)
  └─ Current price, target price, MOS, composite percentile, filters passed

Factor Profile + Elimination Gauntlet (2-column, equal width)
  ├─ Left: Radar chart + 5 factor bars with sector benchmarks
  └─ Right: 6 filters, collapsed, expand for diagnostics

Scoring Pillars (full-width, 3-column)
  └─ Quality | Value | Momentum — percentile, weight, sub-factors

Conviction Engine (full-width)
  └─ Opportunity type + 3 metrics (asymmetry, position size, timing)

Valuation Evidence (full-width)
  └─ Price ruler + methods table + audit drawer

Institutional Positioning + Model Validation (2-column)
  ├─ Left: Holders, trend chart, top holders table
  └─ Right: ML audit + backtest combined
```

---

## 1. Instrument Header

**Replaces**: ScoreHeader, HeroHeader, DeterminismBadge, breadcrumb metadata, EliminatedHero

Full-width strip — the face of the chronograph. One glance tells you the verdict.

**Layout** (3-zone horizontal):
- **Left**: Ticker in Newsreader `headline-md` + company name in Inter Tight `body-md` `on-surface-variant` + sector chip (`label-sm`, `surface-container` bg, `rounded-sm`) + growth stage chip
- **Center**: Composite score in Space Grotesk, 56px, tier-colored + tier badge (`label-sm`, tier-colored bg at 12% opacity) + signal label
- **Right**: Scored timestamp in `label-sm` `text-tertiary` + DeterminismBadge (inline icon + tooltip) + WatchlistButton (star toggle)

**Styling**:
- Background: `surface-container-low`
- No border — tonal separation from page `surface` base
- No dividers between zones — spacing handles separation
- Breadcrumb nav above the header: simple "Explore / AAPL" in `label-sm` `text-tertiary`

**Eliminated state**: Score renders at 40% opacity. Tier shows "ELIMINATED" in `bearish` color. Signal field shows primary elimination reason.

---

## 2. Vital Signs Strip

**Replaces**: PriceContext, ConsistencyBadge, key stats from HeroHeader

5 metrics in a horizontal row — same visual language as the landing page hero stats.

| Current Price | Target Price | Margin of Safety | Composite Percentile | Filters Passed |
|---|---|---|---|---|
| $174.50 | $210.00 | +20.3% | 84th | 6/6 |

**Per metric**:
- Large number: Space Grotesk `mono-data` scale, `on-surface`
- Small label: Space Grotesk `label-sm`, `on-surface-variant`

**Color coding**:
- MOS: `bullish` if positive, `bearish` if negative
- Filters: `bullish` if 6/6, `warning` if partial, `bearish` if critical failures
- ConsistencyBadge: appears as small alert icon next to affected metric if data anomaly detected

**Styling**:
- Background: `surface` (base level) — tonal step down from header
- No card container — bare metrics on base surface
- Responsive: 2x3 grid on mobile, 5-column on desktop

**Eliminated state**: Target price and MOS show "\u2014" (em dash). Percentile dimmed.

---

## 3. Factor Profile (left card of 2-column section)

**Replaces**: FactorPanel, FactorRadar

Single consolidated factor visualization.

**Top — Radar chart**:
- Recharts RadarChart, 5 axes (Quality, Value, Momentum, Sentiment, Growth)
- Three overlapping polygons: stock (filled `primary-container` at 30% opacity), sector median P50 (dashed line `surface-variant`), sector top P90 (dotted line `on-surface-variant` at 40%)
- Axis labels in Space Grotesk `label-sm`
- Grid lines: `surface-variant` at 10% opacity
- No area fill on the P50/P90 reference lines

**Bottom — Factor bars**:
- 5 horizontal bars (one per factor)
- Each bar: factor name (`label-sm`), horizontal track (`surface-container-lowest`), filled portion (`primary-container`), percentile number (Space Grotesk `label-md`)
- SectorMicroBar markers (P50/P90 tick marks) integrated into each bar track
- Bars use `rounded-sm` — no pills

**Card styling**:
- `surface-container-low` background, ghost border
- `label-sm` header: "FACTOR PROFILE"
- Responsive: on mobile, this card stacks above the elimination card

---

## 4. Elimination Gauntlet (right card of 2-column section)

**Replaces**: EliminationGauntlet, FilterCard, FailedComparison, SectorNeutralBanner

**Header**: "ELIMINATION GAUNTLET" `label-sm` + pass count badge ("6/6 PASSED" in `primary-muted` or "4/6" in `warning`)

**Filter rows** (6 rows, collapsed by default):
- Each row: filter name (`body-md` `on-surface`), pass/fail icon (checkmark `primary-muted` or X `bearish`), right-aligned
- Click to expand: diagnostics table (metric name, stock value, threshold, result), formula in `label-sm` Space Grotesk
- **Failed filters**: auto-expanded when the stock is eliminated. Champion comparison bars render inline inside the expanded state — showing the stock's value vs sector champion as horizontal bars (`bearish` vs `primary-muted`)

**Footer note**: "Sector-neutral ranking applied" in `label-sm` `text-tertiary` — replaces SectorNeutralBanner

**Card styling**:
- `surface-container-low` background, ghost border
- Expand/collapse: smooth height transition (CSS grid 0fr→1fr or framer-motion)
- Responsive: stacks below Factor Profile on mobile

---

## 5. Scoring Pillars

**Restyled**: ScoringPillars, PillarCard (existing structure is sound)

3 equal-width cards in a row — Quality, Value, Momentum.

**Each card**:
- `label-sm` header: "QUALITY" / "VALUE" / "MOMENTUM"
- Large percentile: Space Grotesk `mono-data`, tier-colored
- Weight badge: `label-sm` `text-tertiary` (e.g., "40% WEIGHT")
- Sub-factor table: collapsed by default, expand on click
  - Each sub-factor row: name (`body-md`), percentile (Space Grotesk `label-md`), SectorMicroBar inline
  - Alternating `surface` / `surface-container-lowest` rows

**Card styling**:
- `surface-container-low` background, ghost border
- Responsive: stack on mobile

---

## 6. Conviction Engine

**Simplified from**: ConvictionEngine (232 lines → estimated ~120 lines)

One card, two zones.

**Top zone — Opportunity Classification**:
- Type label: Newsreader `headline-md` (e.g., "COMPOUNDER" or "DEEP VALUE MISPRICING")
- One-line rationale: Inter Tight `body-md`, `on-surface-variant`

**Bottom zone — 3-metric strip**:

| Asymmetry | Max Position (Kelly) | Timing Signal |
|---|---|---|
| 2.4x | 4.2% | Accumulate |

- Space Grotesk `mono-data` for numbers, `label-sm` for labels
- Asymmetry color-coded by magnitude (higher = more `bullish`)
- Timing signal uses renamed vocabulary (strong/stable/emerging/weak)

**Removed**: Compounder/mispricing track bars (redundant with factor bars), smart money alignment (covered by Institutional section)

**Card styling**: `surface-container-low` background, ghost border

**Eliminated state**: Entire section hidden.

---

## 7. Valuation Evidence

**Restyled**: ValuationSection (285 lines)

One card, two parts.

**Top — Price Ruler**:
- Existing SVG ruler showing price positions on a linear scale
- Restyled: `surface-container-low` background, Space Grotesk price labels, `primary-muted` for target markers, `bearish` for downside markers
- No border around ruler — sits directly on card surface

**Bottom — Methods Table**:
- Columns: Method | Estimate | Weight | vs Current
- Alternating surface tier rows (same pattern as landing comparison table)
- "vs Current" column: `bullish`/`bearish` percentage
- All numbers in Space Grotesk

**Audit drawer**: "VIEW AUDIT TRAIL" link at bottom in `label-sm` `primary-muted`. Expands inline to show DCF assumptions, discount rate, terminal growth rate. Progressive disclosure.

**Card styling**: `surface-container-low` background, ghost border

**Eliminated state**: Entire section hidden.

---

## 8. Institutional Positioning (left card of 2-column section)

**Restyled**: InstitutionalPositioning (393 lines)

**Summary strip**: 3 inline metrics — Total Holders, Curated Holders, Net Accumulation (with directional arrow icon)

**Holder trend chart**:
- Recharts AreaChart — quarter-over-quarter holder count
- Lines: 1.5px `primary-muted`, NO area fill (DESIGN.md chart rules)
- Grid lines: `surface-variant` at 10% opacity
- Axis labels: Space Grotesk `label-sm`

**Top holders table**:
- Compact rows, Space Grotesk for AUM figures
- Collapsed to top 5 with "Show all" expand link
- Alternating surface tier rows

**Gated content**: Users without tier access see blurred preview with upgrade prompt — not empty state

**Card styling**: `surface-container-low` background, ghost border

**Eliminated state**: Entire section hidden.

---

## 9. Model Validation (right card of 2-column section)

**Replaces**: MLAuditPanel + BacktestTeaser merged into one card

**Top half — ML Status**:
- Qualified/Not Qualified badge (`label-sm`, `primary-muted` bg or `text-tertiary` bg)
- If qualified: alpha estimate (Space Grotesk `mono-data`), confidence interval, override gates as pass/fail indicators
- If not qualified: "No qualified model — rules-only scoring" in `text-tertiary`

**Bottom half — Backtest Evidence**:
- 3 inline metrics: Model Return, Benchmark Return, Excess Return
- Space Grotesk `mono-data`, `bullish`/`bearish` color coding
- Max drawdown improvement as a single stat below

**Card styling**: `surface-container-low` background, ghost border

**Eliminated state**: Entire section hidden.

---

## 10. Eliminated State Behavior

When a stock fails filters, the report adapts rather than rendering a separate component tree:

1. **Instrument Header**: Score at 40% opacity, "ELIMINATED" tier in `bearish`, elimination reason as signal
2. **Vital Signs**: Target/MOS show "\u2014", percentile dimmed
3. **Factor Profile**: Renders normally but with `surface-container-lowest` dimmed background + inline banner: "Hypothetical — this candidate was eliminated before scoring" in `label-sm` `text-tertiary`
4. **Elimination Gauntlet**: Failed filters auto-expanded with champion comparison bars visible
5. **Scoring Pillars**: Same dimmed treatment as Factor Profile
6. **Sections 6-9**: Hidden entirely (no conviction, valuation, institutional, or model data for eliminated stocks)
7. **Bottom CTA**: "View another candidate" link to `/explore`

---

## 11. Component Map

### Deleted (12 components)
| Component | Reason |
|-----------|--------|
| `hero-header.tsx` | Absorbed into Instrument Header + Vital Signs |
| `score-header.tsx` | Absorbed into Instrument Header |
| `price-context.tsx` | Absorbed into Vital Signs |
| `factor-panel.tsx` | Merged into Factor Profile |
| `factor-radar.tsx` | Merged into Factor Profile |
| `eliminated-hero.tsx` | Replaced by conditional rendering |
| `hypothetical-scores.tsx` | Replaced by conditional dimming |
| `failed-comparison.tsx` | Moved inline into filter expansion |
| `backtest-teaser.tsx` | Merged into Model Validation |
| `determinism-badge.tsx` | Absorbed into Instrument Header |
| `consistency-badge.tsx` | Absorbed into Vital Signs |
| `sector-neutral-banner.tsx` | Absorbed as inline note in Gauntlet |

### Created (4 components)
| Component | Purpose |
|-----------|---------|
| `instrument-header.tsx` | Full-width verdict strip |
| `vital-signs.tsx` | 5-metric horizontal strip |
| `factor-profile.tsx` | Consolidated radar + bars |
| `model-validation.tsx` | Merged ML audit + backtest |

### Restyled (8 components)
| Component | Changes |
|-----------|---------|
| `asset-detail-view.tsx` | Rewrite — new layout orchestrator |
| `elimination-gauntlet.tsx` | Absorb FailedComparison + SectorNeutralBanner, restyle |
| `filter-card.tsx` | Ghost borders, Space Grotesk, tonal layering |
| `scoring-pillars.tsx` | 3-column cards, restyle |
| `pillar-card.tsx` | Progressive disclosure, SectorMicroBar inline |
| `conviction-engine.tsx` | Simplify — classification + 3 metrics only |
| `valuation-section.tsx` | Tonal rows, audit drawer |
| `institutional-positioning.tsx` | Chart rules, compact tables |

### Kept unchanged
- `sector-micro-bar.tsx`
- `watchlist-button.tsx` (moved into Instrument Header)

### Total: 22 components → 14 components (~3,300 LOC → ~2,200 LOC)

---

## 12. Styling Rules (inherited from Digital Horologist)

All sections follow the design system established in `2026-04-14-digital-horologist-redesign-design.md`:

- **Typography**: Newsreader (display/headlines), Space Grotesk (data/labels), Inter Tight (body/UI)
- **Surfaces**: Tonal layering via 6-tier surface hierarchy. No 1px borders for section separation.
- **Borders**: Ghost borders only (`outline-variant` at 15% opacity) on cards
- **Radii**: Max 0.75rem. Buttons 0.375rem. No pills.
- **Charts**: Lines 1.5px, no area fills, grid lines at 10% opacity, Space Grotesk axes
- **Elevation**: Tonal, not shadows. Ambient shadow only on floating elements.
- **Motion**: GSAP `power2.out` / `expo.out`. No `back.out` bounce. `prefers-reduced-motion` respected.
- **Colors**: `primary-muted` (#4a9e7e) for visible accent text. `primary` (#80d8b2) for glows only.

---

## 13. Data Flow

No API changes required. The page already fetches:

**Server-side** (page.tsx):
- `GET /api/v1/scores/{TICKER}?include=price_history,signal_history` → ScoreResponse
- `GET /api/v1/scores/{TICKER}/history?limit=30` → ScoreHistoryResponse

**Client-side** (lazy):
- `getBacktestTeaser(ticker)` → BacktestTeaserResponse
- `getHoldings(ticker)` → HoldingsResponse
- `getHoldingsHistory(ticker)` → HoldingsHistoryResponse (gated)
- `getValuationAudit(ticker)` → ValuationAuditResponse (on demand)

All data sources remain unchanged. The redesign is purely presentational.

---

## 14. Out of Scope

- New API endpoints or data fields
- Mobile-native layouts beyond responsive stacking
- Print/PDF export of reports
- Comparison mode (side-by-side candidates)
- Dashboard page changes
