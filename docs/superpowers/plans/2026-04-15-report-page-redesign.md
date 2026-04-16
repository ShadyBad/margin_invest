# Forensic Report Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan one task at a time. Steps use checkbox syntax for tracking.

**Goal:** Redesign the `/asset/[ticker]` report page — consolidate 22 components into 14, apply Digital Horologist design system, enforce verdict-first information hierarchy.

**Architecture:** Create 4 new components (InstrumentHeader, VitalSigns, FactorProfile, ModelValidation), restyle 8 existing components to use new design tokens, delete 12 absorbed/redundant components, rewrite the orchestrator (asset-detail-view.tsx) with new layout. No API changes — purely presentational.

**Tech Stack:** Next.js 16, React 19, Tailwind v4, Recharts, GSAP (minimal), Digital Horologist design tokens

**Spec:** `docs/superpowers/specs/2026-04-15-report-page-redesign-design.md`

---

## File Map

### Created (4)
| File | Purpose |
|------|---------|
| `web/src/components/asset-detail/instrument-header.tsx` | Full-width verdict strip: ticker, score, tier, signal, timestamp, watchlist, determinism |
| `web/src/components/asset-detail/vital-signs.tsx` | 5-metric horizontal strip: price, target, MOS, percentile, filters |
| `web/src/components/asset-detail/factor-profile.tsx` | Consolidated radar chart + 5 factor bars with sector benchmarks |
| `web/src/components/asset-detail/model-validation.tsx` | Merged ML audit + backtest evidence |

### Restyled (8)
| File | Changes |
|------|---------|
| `asset-detail-view.tsx` | Full rewrite — new layout, new section flow, conditional eliminated state |
| `elimination-gauntlet.tsx` | Restyle + absorb SectorNeutralBanner note, Digital Horologist tokens |
| `filter-card.tsx` | Ghost borders, Space Grotesk, tonal layering, champion bars inline |
| `scoring-pillars.tsx` | 3-column cards, new tokens |
| `pillar-card.tsx` | Progressive disclosure, tonal rows, SectorMicroBar inline |
| `conviction-engine.tsx` | Simplify — opportunity type + 3 metrics, remove tracks |
| `valuation-section.tsx` | Tonal rows, Space Grotesk, audit drawer |
| `institutional-positioning.tsx` | Chart rules (no area fill), compact tables, new tokens |

### Deleted (12)
| File | Reason |
|------|--------|
| `hero-header.tsx` | Absorbed into InstrumentHeader + VitalSigns |
| `score-header.tsx` | Absorbed into InstrumentHeader |
| `price-context.tsx` | Absorbed into VitalSigns |
| `factor-panel.tsx` | Merged into FactorProfile |
| `factor-radar.tsx` | Merged into FactorProfile |
| `eliminated-hero.tsx` | Replaced by conditional rendering in InstrumentHeader |
| `hypothetical-scores.tsx` | Replaced by dimmed Factor/Pillars sections |
| `failed-comparison.tsx` | Moved inline into filter-card expanded state |
| `backtest-teaser.tsx` | Merged into ModelValidation |
| `determinism-badge.tsx` | Absorbed into InstrumentHeader |
| `consistency-badge.tsx` | Absorbed into VitalSigns |
| `sector-neutral-banner.tsx` | Absorbed as inline note in EliminationGauntlet |

### Kept Unchanged
- `sector-micro-bar.tsx` — used in pillar-card and factor-profile
- `watchlist-button.tsx` — moved into InstrumentHeader (no code change, just repositioned)

---

## Task 1: Create InstrumentHeader

**Files:**
- Create: `web/src/components/asset-detail/instrument-header.tsx`

The full-width verdict strip — replaces ScoreHeader, top portion of HeroHeader, EliminatedHero, DeterminismBadge.

- [ ] **Step 1: Read the spec** section 1 (Instrument Header) from `docs/superpowers/specs/2026-04-15-report-page-redesign-design.md`

- [ ] **Step 2: Read existing components** being absorbed — `score-header.tsx`, `hero-header.tsx` (first 50 lines), `eliminated-hero.tsx`, `determinism-badge.tsx` — to understand their props and data

- [ ] **Step 3: Create instrument-header.tsx**

The component receives ScoreResponse data and renders a 3-zone horizontal layout:
- Left: Ticker (Newsreader headline-md) + company name + sector chip + growth stage chip
- Center: Score (Space Grotesk 56px, tier-colored) + tier badge + signal
- Right: Scored timestamp + determinism tooltip + watchlist button

Key implementation details:
- Use the `deriveCompositeTier()` function (copy from asset-detail-view.tsx) for tier color mapping
- Tier colors use the existing `--color-percentile-*` tokens
- `surface-container-low` background, no border (tonal separation from page)
- Breadcrumb nav rendered above: "Explore / {TICKER}" in `label-sm`
- Eliminated state: score at 40% opacity, "ELIMINATED" badge in `bearish`, signal shows elimination reason
- Import and render `WatchlistButton` in the right zone
- Determinism: small lock icon with hover tooltip "Zero human discretion — same inputs, same outputs"

Props interface:
```typescript
interface InstrumentHeaderProps {
  ticker: string
  name: string
  sector: string | null
  growthStage: string | null
  style: string | null
  score: number
  tier: string
  signal: string | null
  scoredAt: string | null
  eliminated: boolean
  eliminationReason?: string | null
  universePercentile: number
}
```

Responsive: On mobile, stack the three zones vertically (center zone first for immediate verdict).

- [ ] **Step 4: Commit**

```bash
git add web/src/components/asset-detail/instrument-header.tsx
git commit -m "feat(report): create InstrumentHeader — verdict strip"
```

---

## Task 2: Create VitalSigns

**Files:**
- Create: `web/src/components/asset-detail/vital-signs.tsx`

5-metric horizontal strip — replaces PriceContext, absorbs key stats from HeroHeader.

- [ ] **Step 1: Read the spec** section 2 (Vital Signs Strip)

- [ ] **Step 2: Read `price-context.tsx`** to get the `formatPrice()` and `formatPercent()` utilities

- [ ] **Step 3: Create vital-signs.tsx**

Props interface:
```typescript
interface VitalSignsProps {
  currentPrice: number | null
  targetPrice: number | null
  marginOfSafety: number | null
  compositePercentile: number
  filtersPassed: number
  filtersTotal: number
  eliminated: boolean
  consistencyWarnings?: string[]
}
```

Layout: 5 metrics in a `grid grid-cols-2 md:grid-cols-5 gap-6` on `surface` background.

Each metric:
- Number: `text-mono-data` with `on-surface` color
- Label: `text-label-sm` with `on-surface-variant` color

Color coding:
- MOS: `bullish` if >= 0, `bearish` if < 0
- Filters: `bullish` if all passed, `warning` if partial, `bearish` if majority failed
- ConsistencyWarnings: render a small alert icon next to the label if warnings array is non-empty, with hover tooltip listing the warnings

Eliminated state: Target price and MOS show "\u2014", percentile text dimmed to `text-tertiary`.

Utilities (inline in file):
```typescript
function formatPrice(price: number): string {
  return `$${price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : ""
  return `${sign}${(value * 100).toFixed(1)}%`
}
```

- [ ] **Step 4: Commit**

```bash
git add web/src/components/asset-detail/vital-signs.tsx
git commit -m "feat(report): create VitalSigns — 5-metric strip"
```

---

## Task 3: Create FactorProfile

**Files:**
- Create: `web/src/components/asset-detail/factor-profile.tsx`

Consolidated radar + bars — replaces FactorPanel and FactorRadar.

- [ ] **Step 1: Read existing** `factor-panel.tsx` and `factor-radar.tsx` to understand their props and Recharts usage

- [ ] **Step 2: Create factor-profile.tsx**

Props interface:
```typescript
interface FactorProfileProps {
  factors: {
    quality: number
    value: number
    momentum: number
    sentiment: number | null
    growth: number | null
  }
  sectorBenchmarks?: {
    quality: { p50: number; p90: number }
    value: { p50: number; p90: number }
    momentum: { p50: number; p90: number }
  }
  eliminated?: boolean
}
```

Top section — Recharts RadarChart:
- 5 axes (Quality, Value, Momentum, Sentiment, Growth)
- Stock polygon: filled `primary-container` at 30% opacity, stroke `primary-muted` 1.5px
- P50 reference polygon: dashed stroke `surface-variant` 1px (if benchmarks provided)
- P90 reference polygon: dotted stroke `on-surface-variant` at 40% opacity 1px (if benchmarks provided)
- PolarGrid: `surface-variant` at 10% opacity
- PolarAngleAxis labels: Space Grotesk `label-sm`
- Responsive: `<ResponsiveContainer width="100%" height={220}>`

Bottom section — 5 factor bars:
- Each bar: label (`label-sm` left), track (`surface-container-lowest` bg, `rounded-sm`, h-2), fill (`primary-container`, `rounded-sm`), percentile number (`label-md` right, Space Grotesk)
- SectorMicroBar markers (P50 tick, P90 tick) rendered as absolute-positioned 1px-wide divs on the track if benchmarks are provided

Card wrapper:
- `surface-container-low` bg, ghost border, `rounded-lg`
- `label-sm` header: "FACTOR PROFILE"
- If `eliminated`: add `opacity-60` wrapper + banner "Hypothetical — this candidate was eliminated before scoring" in `label-sm text-tertiary`

- [ ] **Step 3: Commit**

```bash
git add web/src/components/asset-detail/factor-profile.tsx
git commit -m "feat(report): create FactorProfile — consolidated radar + bars"
```

---

## Task 4: Create ModelValidation

**Files:**
- Create: `web/src/components/asset-detail/model-validation.tsx`

Merged ML audit + backtest — replaces MLAuditPanel and BacktestTeaser.

- [ ] **Step 1: Read existing** `ml-audit-panel.tsx` and `backtest-teaser.tsx` to understand props

- [ ] **Step 2: Create model-validation.tsx**

Props interface:
```typescript
interface ModelValidationProps {
  // ML audit
  mlModelQualified: boolean | null
  mlModelRankIc: number | null
  mlModelTrainedAt: string | null
  mlAlpha: number | null
  mlConfidence: number | null
  mlOverride: {
    applied: boolean
    direction: string | null
    rules_tier: string | null
    ml_tier: string | null
  } | null
  rulesTier: string | null
  compositeTier: string | null
  // Backtest
  backtestData: {
    model_return: number
    benchmark_return: number
    max_drawdown: number
    benchmark_max_drawdown: number
    start_date: string
  } | null
}
```

Top half — ML Status:
- Qualified badge: `label-sm` with `primary-muted` bg if qualified, `surface-container` bg if not
- If qualified: 3 inline metrics (Rank IC, Alpha, Confidence) in Space Grotesk `mono-data`
- Override gates: small pass/fail checklist if override data present
- If not qualified: single line "No qualified model — rules-only scoring" in `text-tertiary`

Bottom half — Backtest Evidence:
- 3 inline metrics: Model Return, Benchmark, Excess Return (computed as model - benchmark)
- Space Grotesk `mono-data`, `bullish`/`bearish` color coding
- Max drawdown improvement: one stat below
- If no backtest data: "Backtest data not available" in `text-tertiary`

Card wrapper: `surface-container-low` bg, ghost border, `label-sm` header: "MODEL VALIDATION"

- [ ] **Step 3: Commit**

```bash
git add web/src/components/asset-detail/model-validation.tsx
git commit -m "feat(report): create ModelValidation — merged ML audit + backtest"
```

---

## Task 5: Restyle EliminationGauntlet + FilterCard

**Files:**
- Modify: `web/src/components/asset-detail/elimination-gauntlet.tsx`
- Modify: `web/src/components/asset-detail/filter-card.tsx`

- [ ] **Step 1: Read current** `elimination-gauntlet.tsx` and `filter-card.tsx`

- [ ] **Step 2: Update EliminationGauntlet**

Changes:
- Replace `text-lg font-semibold text-text-primary` heading with `text-label-sm` style and inline `color: var(--color-on-surface-variant)` — reads "ELIMINATION GAUNTLET"
- Replace `text-xs text-text-tertiary` description with `text-body-md` inline color
- Pass badge: replace `text-bullish bg-bullish/10` / `text-bearish bg-bearish/10` with inline styles using `--color-primary-muted` / `--color-bearish` and 10% opacity backgrounds
- Add SectorNeutralBanner inline note at bottom: `<p className="text-label-sm mt-6" style={{ color: "var(--color-text-tertiary)" }}>Sector-neutral ranking applied</p>` — only when not eliminated
- Wrap in card: `surface-container-low` bg, ghost border, `rounded-lg`, `p-6`
- Accept new prop `sectorName` to display in the note

- [ ] **Step 3: Update FilterCard**

Changes:
- Replace `terminal-card` with inline `surface-container` bg + ghost border + `rounded-lg`
- Replace all `font-mono` with `fontFamily: var(--font-data)` inline styles
- Replace `text-text-primary`, `text-text-secondary`, `text-text-tertiary` with `on-surface`, `on-surface-variant`, `text-tertiary` inline styles
- Replace `border-white/[0.06]` dividers with spacing (`gap-3` or `mb-3`) — no-line rule
- Replace `rounded-full` on any badges with `rounded-sm`
- For failed filters: render FailedComparison data inline (stock value bar vs champion bar) at the bottom of the expanded section. Accept optional `championData` prop.
- Diagnostics table: alternating `surface` / `surface-container-lowest` rows

- [ ] **Step 4: Commit**

```bash
git add web/src/components/asset-detail/elimination-gauntlet.tsx web/src/components/asset-detail/filter-card.tsx
git commit -m "feat(report): restyle EliminationGauntlet + FilterCard — tonal, ghost borders"
```

---

## Task 6: Restyle ScoringPillars + PillarCard

**Files:**
- Modify: `web/src/components/asset-detail/scoring-pillars.tsx`
- Modify: `web/src/components/asset-detail/pillar-card.tsx`

- [ ] **Step 1: Read current** `scoring-pillars.tsx` and `pillar-card.tsx`

- [ ] **Step 2: Update ScoringPillars**

Changes:
- Replace `text-lg font-semibold text-text-primary` heading with `text-label-sm` inline styles
- Replace `text-xs text-text-tertiary` description with inline `on-surface-variant`
- Keep the `grid grid-cols-1 sm:grid-cols-3 gap-3` layout — structure is sound

- [ ] **Step 3: Update PillarCard**

Changes:
- Replace `terminal-card` with `surface-container-low` bg + ghost border + `rounded-lg`
- Pillar name: `text-label-sm` with `on-surface-variant`
- Percentile number: Space Grotesk `mono-data`, tier-colored
- Weight: `text-label-sm text-tertiary`
- Progress bar: replace `rounded-full` with `rounded-sm`, track uses `surface-container-lowest`, fill uses tier color
- Sub-factor table: collapsed by default (CSS grid 0fr→1fr transition), alternating `surface` / `surface-container-lowest` rows
- Sub-factor values: Space Grotesk for all numbers
- Replace all `font-mono` with `fontFamily: var(--font-data)`
- Replace all old color token classes with inline styles

- [ ] **Step 4: Commit**

```bash
git add web/src/components/asset-detail/scoring-pillars.tsx web/src/components/asset-detail/pillar-card.tsx
git commit -m "feat(report): restyle ScoringPillars + PillarCard — tonal, progressive disclosure"
```

---

## Task 7: Simplify ConvictionEngine

**Files:**
- Modify: `web/src/components/asset-detail/conviction-engine.tsx`

- [ ] **Step 1: Read current** `conviction-engine.tsx` (233 lines)

- [ ] **Step 2: Rewrite to simplified version**

Keep:
- Opportunity type classification (compounder/mispricing/both/neither)
- 3 metric cards (asymmetry, max position, timing signal)

Remove:
- Compounder/mispricing "track bars" (TrackBar components) — redundant with factor bars
- Smart Money Alignment section — covered by Institutional Positioning
- ML override badges — covered by Model Validation

New structure:
- One card, `surface-container-low` bg, ghost border
- Top zone: Opportunity type in Newsreader `text-headline-md` uppercase + one-line rationale in `text-body-md on-surface-variant`
- Bottom zone: 3 metrics inline (same layout as VitalSigns) — Asymmetry, Max Position (Kelly), Timing Signal
- Space Grotesk `mono-data` for numbers, `label-sm` for labels
- Asymmetry color-coded: `bullish` if > 2x, `on-surface` otherwise
- Timing signal uses renamed vocabulary

Target: ~120 lines (from 233)

- [ ] **Step 3: Commit**

```bash
git add web/src/components/asset-detail/conviction-engine.tsx
git commit -m "feat(report): simplify ConvictionEngine — type + 3 metrics only"
```

---

## Task 8: Restyle ValuationSection

**Files:**
- Modify: `web/src/components/asset-detail/valuation-section.tsx`

- [ ] **Step 1: Read current** `valuation-section.tsx` (286 lines)

- [ ] **Step 2: Apply Digital Horologist styling**

Changes:
- Card wrapper: `surface-container-low` bg, ghost border, `rounded-lg`
- Header: `text-label-sm` "VALUATION EVIDENCE"
- Price ruler SVG: update colors to use `primary-muted` for target markers, `bearish` for downside, Space Grotesk for all price labels
- Methods table: alternating `surface` / `surface-container-lowest` rows (no border lines)
- Column headers: Space Grotesk `label-sm` uppercase
- "vs Current" column: `bullish` / `bearish` percentage
- All numbers: `fontFamily: var(--font-data)`
- Audit drawer toggle: `label-sm primary-muted` text "VIEW AUDIT TRAIL", expands inline
- Remove all `terminal-card`, `font-mono`, `text-text-*`, `border-white/*` references — replace with new tokens
- Remove any `border-t` dividers — use spacing

- [ ] **Step 3: Commit**

```bash
git add web/src/components/asset-detail/valuation-section.tsx
git commit -m "feat(report): restyle ValuationSection — tonal rows, Space Grotesk"
```

---

## Task 9: Restyle InstitutionalPositioning

**Files:**
- Modify: `web/src/components/asset-detail/institutional-positioning.tsx`

- [ ] **Step 1: Read current** `institutional-positioning.tsx` (393 lines)

- [ ] **Step 2: Apply Digital Horologist styling**

Changes:
- Card wrapper: `surface-container-low` bg, ghost border, `rounded-lg`
- Header: `text-label-sm` "INSTITUTIONAL POSITIONING"
- Summary cards: 3 inline metrics (Total Holders, Curated Holders, Net Accumulation) using `mono-data` + `label-sm` layout
- Holder trend chart (Recharts AreaChart):
  - Lines: 1.5px stroke `primary-muted`
  - **Remove area fill** — set `<Area fill="none" />` or remove the `<Area>` component and use `<Line>` instead
  - Grid lines: `surface-variant` at 10% opacity
  - Axis labels: Space Grotesk `label-sm`
- Top holders table: alternating `surface` / `surface-container-lowest` rows, Space Grotesk for AUM figures, collapsed to top 5
- Gated content: blurred preview with upgrade prompt (keep existing ProGate logic)
- Replace all old token classes with inline styles
- Remove `border-*` dividers — use spacing

- [ ] **Step 3: Commit**

```bash
git add web/src/components/asset-detail/institutional-positioning.tsx
git commit -m "feat(report): restyle InstitutionalPositioning — no area fill, tonal tables"
```

---

## Task 10: Rewrite AssetDetailView (Orchestrator)

**Files:**
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx`

This is the main layout rewrite — depends on Tasks 1-9 being complete.

- [ ] **Step 1: Read the spec** page flow section and the current `asset-detail-view.tsx`

- [ ] **Step 2: Rewrite asset-detail-view.tsx**

New imports (replace old ones):
```typescript
import { InstrumentHeader } from "./instrument-header"
import { VitalSigns } from "./vital-signs"
import { FactorProfile } from "./factor-profile"
import { EliminationGauntlet } from "./elimination-gauntlet"
import { ScoringPillars } from "./scoring-pillars"
import { ConvictionEngine } from "./conviction-engine"
import { ValuationSection } from "./valuation-section"
import { InstitutionalPositioning } from "./institutional-positioning"
import { ModelValidation } from "./model-validation"
```

Remove imports: HeroHeader, EliminatedHero, HypotheticalScores, FailedComparison, ScoreHeader, PriceContext, FactorPanel, FactorRadar, ConsistencyBadge, DeterminismBadge, SectorNeutralBanner, BacktestTeaser

Keep: `deriveCompositeTier()`, `formatGrowthStage()`, `getFreshnessLabel()` utilities

New layout structure (replacing the old 60/40 grid):
```
<InstrumentHeader ... />
<VitalSigns ... />

{/* Factor Profile + Elimination — 2-column equal */}
<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
  <FactorProfile ... />
  <EliminationGauntlet ... />
</div>

{/* Scoring Pillars — full-width 3-column */}
{showScoreView && <ScoringPillars ... />}

{/* Conviction — full-width */}
{showScoreView && <ConvictionEngine ... />}

{/* Valuation — full-width */}
{showScoreView && <ValuationSection ... />}

{/* Institutional + Model Validation — 2-column */}
{showScoreView && (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
    <InstitutionalPositioning ... />
    <ModelValidation ... />
  </div>
)}

{/* Eliminated: explore link */}
{!showScoreView && (
  <div className="text-center py-8">
    <Link href="/explore" ...>View another candidate &rarr;</Link>
  </div>
)}
```

Error state: keep existing error card but update tokens (`surface-container-low` bg, ghost border, `on-surface` text, `on-surface-variant` description)

Eliminated state: `showScoreView` flag controls which sections render (same logic as current, just cleaner — Sections 5-9 hidden when eliminated)

Factor profile gets `eliminated` prop for dimming.

- [ ] **Step 3: Verify build compiles**

```bash
cd web && npx next build 2>&1 | tail -20
```

Fix any TypeScript or import errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/asset-detail/asset-detail-view.tsx
git commit -m "feat(report): rewrite orchestrator — verdict-first layout"
```

---

## Task 11: Delete Old Components + Update Exports

**Files:**
- Delete: 12 component files
- Modify: `web/src/components/asset-detail/index.ts`

- [ ] **Step 1: Delete absorbed components**

```bash
cd web/src/components/asset-detail
rm -f hero-header.tsx
rm -f score-header.tsx
rm -f price-context.tsx
rm -f factor-panel.tsx
rm -f factor-radar.tsx
rm -f eliminated-hero.tsx
rm -f hypothetical-scores.tsx
rm -f failed-comparison.tsx
rm -f backtest-teaser.tsx
rm -f determinism-badge.tsx
rm -f consistency-badge.tsx
rm -f sector-neutral-banner.tsx
```

- [ ] **Step 2: Delete associated test files**

```bash
cd web/src/components/asset-detail/__tests__
rm -f hero-header.test.tsx score-header.test.tsx price-context.test.tsx factor-panel.test.tsx factor-radar.test.tsx eliminated-hero.test.tsx hypothetical-scores.test.tsx failed-comparison.test.tsx backtest-teaser.test.tsx determinism-badge.test.tsx consistency-badge.test.tsx sector-neutral-banner.test.tsx 2>/dev/null
```

Also check for tests in other locations:
```bash
grep -rl "hero-header\|score-header\|price-context\|factor-panel\|factor-radar\|eliminated-hero\|hypothetical-scores\|failed-comparison\|backtest-teaser\|determinism-badge\|consistency-badge\|sector-neutral-banner" web/src --include="*.test.*" | xargs rm -f
```

- [ ] **Step 3: Update barrel exports**

Replace `web/src/components/asset-detail/index.ts`:

```typescript
export { AssetDetailView } from "./asset-detail-view"
export { InstrumentHeader } from "./instrument-header"
export { VitalSigns } from "./vital-signs"
export { FactorProfile } from "./factor-profile"
export { EliminationGauntlet } from "./elimination-gauntlet"
export { FilterCard } from "./filter-card"
export { ScoringPillars } from "./scoring-pillars"
export { PillarCard } from "./pillar-card"
export { ConvictionEngine } from "./conviction-engine"
export { ValuationSection } from "./valuation-section"
export { InstitutionalPositioning } from "./institutional-positioning"
export { ModelValidation } from "./model-validation"
export { WatchlistButton } from "./watchlist-button"
```

- [ ] **Step 4: Verify build**

```bash
cd web && npx next build 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
git add -A web/src/components/asset-detail/
git commit -m "feat(report): delete 12 absorbed components, update exports"
```

---

## Task 12: Update Tests + Verify

**Files:** All modified/created files

- [ ] **Step 1: Run tests**

```bash
cd web && npx vitest run 2>&1 | tail -30
```

Identify failures — most will be from tests referencing deleted components or changed DOM structure.

- [ ] **Step 2: Fix or rewrite failing tests**

For each failing test file:
- If it tests a deleted component → delete the test file
- If it tests a restyled component → update selectors, text content, class assertions
- If it tests the orchestrator (asset-detail-view) → rewrite to match new section structure

Key test updates:
- InstrumentHeader tests: check for ticker, score, tier badge, signal, breadcrumb
- VitalSigns tests: check for 5 metrics, eliminated state shows dashes
- FactorProfile tests: check for radar chart container, 5 factor bars
- ModelValidation tests: check for ML status + backtest metrics
- Orchestrator tests: check new section ordering, eliminated state hides sections 5-9

- [ ] **Step 3: Run full build + test suite**

```bash
cd web && npx next build 2>&1 | tail -10
cd web && npx vitest run 2>&1 | tail -10
```

Expected: clean build, all tests passing.

- [ ] **Step 4: Visual verification**

```bash
cd web && npx next dev
```

Navigate to `/asset/AAPL` (or any scored ticker) and verify:
1. InstrumentHeader: ticker, score, tier, signal, timestamp
2. VitalSigns: 5 metrics strip
3. Factor Profile: radar + bars on left, Gauntlet on right
4. Scoring Pillars: 3-column cards
5. Conviction: opportunity type + 3 metrics
6. Valuation: price ruler + methods table
7. Institutional + Model Validation: side by side

Then navigate to an eliminated ticker and verify dimmed state.

- [ ] **Step 5: Commit fixes**

```bash
git add -A web/
git commit -m "fix(report): update tests for report page redesign"
```
