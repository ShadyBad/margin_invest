# Full Visual Overhaul - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan one step at a time.

**Goal:** Raise premium perception from 5.5/10 to 7.5+/10 through design system enforcement, homepage redesign (7 sections), dashboard app shell, asset detail two-column layout, and fallback data system.

**Architecture:** Enforce typography scale and spacing grid via CSS custom properties. Restructure homepage into 3 section archetypes (System Panel, Editorial Spread, Data Stage). Add collapsible sidebar + top bar app shell for authenticated pages. Build all visualizations in React + SVG (no D3).

**Tech:** Next.js 16, React 19, Tailwind v4, GSAP ScrollTrigger, custom CSS design variables, code-built SVG

---

## Step 1: Typography Scale Enforcement

**Files:**
- Modify: `web/src/app/globals.css`

**Step 1a: Read the current globals.css**

Verify current heading/body classes (lines ~116-160) and understand the existing scale.

**Step 1b: Replace typography classes with enforced scale**

Replace the existing heading and body utility classes with the new scale:

```css
/* Typography Scale - enforced, not suggested */
.text-display-1 { font-family: var(--font-display); font-size: clamp(44px, 7vw, 72px); line-height: 1.05; font-weight: 400; }
.text-display-2 { font-family: var(--font-display); font-size: clamp(32px, 5vw, 48px); line-height: 1.1; font-weight: 400; }
.text-title-1 { font-family: var(--font-sans); font-size: clamp(22px, 2.5vw, 28px); line-height: 1.2; font-weight: 600; }
.text-title-2 { font-family: var(--font-sans); font-size: clamp(17px, 1.8vw, 20px); line-height: 1.3; font-weight: 600; }
.text-body { font-family: var(--font-sans); font-size: clamp(16px, 1.2vw, 17px); line-height: 1.6; font-weight: 400; }
.text-caption { font-family: var(--font-sans); font-size: clamp(13px, 1vw, 14px); line-height: 1.5; font-weight: 400; }
.text-mono-label { font-family: var(--font-mono); font-size: 11px; line-height: 1.2; letter-spacing: 0.2em; text-transform: uppercase; }
.text-mono-data { font-family: var(--font-mono); font-size: clamp(24px, 3vw, 32px); line-height: 1.1; }
```

**Step 1c: Remove shadcn oklch :root block**

Delete the shadcn oklch variable block (lines ~305-338) and the @layer base block (lines ~340-347). These collide with the custom design system.

**Step 1d: Verify build passes**

Run: `cd web && npx next build 2>&1 | tail -5`
Expected: Build succeeds (warnings OK, no errors)

**Step 1e: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All existing tests pass

**Step 1f: Commit**

```
git add web/src/app/globals.css
git commit -m "refactor(web): enforce typography scale and remove shadcn variable collisions"
```

---

## Step 2: Delete Unused Components

**Files:**
- Delete: `web/src/components/landing/testimonial-section.tsx`
- Delete: `web/src/components/landing/infrastructure-section.tsx`
- Delete: `web/src/components/landing/positioning-section.tsx`
- Delete: `web/src/components/landing/problem-section.tsx`
- Delete: `web/src/components/landing/engine-section.tsx`
- Delete: `web/src/components/landing/engine-card.tsx`
- Delete: `web/src/components/landing/section-indicator.tsx`
- Delete: `web/src/components/landing/differentiator-section.tsx`
- Delete: corresponding test files in `web/src/components/landing/__tests__/`

**Step 2a: Verify no imports reference these files**

Search for imports of each component across the codebase. Ensure none are used in homepage-client.tsx or elsewhere.

**Step 2b: Delete the component files and their tests**

Remove all 8 component files and their corresponding test files.

**Step 2c: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All tests pass (deleted test files no longer run)

**Step 2d: Commit**

```
git add -u
git commit -m "chore(web): delete 8 unused landing section components"
```

---

## Step 3: Reorganize Landing Component Directory

**Files:**
- Create: `web/src/components/landing/sections/` (move section components here)
- Create: `web/src/components/landing/visualizations/` (new viz components go here)
- Create: `web/src/components/landing/shared/` (shared landing utilities)
- Modify: all imports in `homepage-client.tsx` and section files

**Step 3a: Create directory structure**

```
mkdir -p web/src/components/landing/{sections,visualizations,shared}
```

**Step 3b: Move existing section files**

Move hero-section.tsx, authority-strip.tsx, evidence-section.tsx, how-it-works-section.tsx, results-showcase-section.tsx, pillars-section.tsx, pricing-section.tsx, faq-section.tsx, footer-section.tsx, pricing-tier-card.tsx, faq-item.tsx into sections/.

**Step 3c: Move shared files**

Move scroll-canvas.tsx, types.ts into shared/.

**Step 3d: Update all imports in homepage-client.tsx and within moved files**

Update import paths to reflect new locations.

**Step 3e: Run tests and fix any broken imports**

Run: `cd web && npx vitest run`
Expected: All tests pass

**Step 3f: Commit**

```
git add .
git commit -m "refactor(web): reorganize landing components into sections/visualizations/shared"
```

---

## Step 4: Fallback Data System

**Files:**
- Create: `web/src/data/fallback-scoring-snapshot.json`
- Modify: `web/src/components/landing/shared/types.ts` (add `isFallback` field)
- Modify: `web/src/app/page.tsx` (return fallback on fetch failure)
- Create: `web/src/components/landing/shared/staleness-indicator.tsx`

**Step 4a: Create the fallback snapshot JSON**

Create fallback-scoring-snapshot.json with 5-8 realistic candidates across diverse sectors. Include all fields from HomepageData interface: candidates, allPicks, last_updated, universe_size, eligible_count, total_scored, total_universe, surviving_count.

**Step 4b: Add isFallback to HomepageData**

```typescript
export interface HomepageData {
  // ...existing fields...
  isFallback?: boolean
}
```

**Step 4c: Update getHomepageData() catch block**

In page.tsx, change `catch { return null }` to import and return the fallback snapshot with `isFallback: true`.

**Step 4d: Create StalenessIndicator component**

Renders mono-label text: "Sample data from last scoring cycle - Live data loads after engine run" in text-text-tertiary. Only shows when data?.isFallback is true.

**Step 4e: Write test for fallback behavior**

```typescript
test("renders staleness indicator when using fallback data", () => {
  render(<StalenessIndicator isFallback={true} />)
  expect(screen.getByText(/sample data/i)).toBeInTheDocument()
})

test("hides staleness indicator with live data", () => {
  render(<StalenessIndicator isFallback={false} />)
  expect(screen.queryByText(/sample data/i)).not.toBeInTheDocument()
})
```

**Step 4f: Run tests**

Run: `cd web && npx vitest run`
Expected: All pass

**Step 4g: Commit**

```
git add web/src/data/fallback-scoring-snapshot.json web/src/app/page.tsx web/src/components/landing/shared/
git commit -m "feat(web): add fallback data system with staleness indicator"
```

---

## Step 5: Visualization Components - Factor Bars

**Files:**
- Create: `web/src/components/landing/visualizations/factor-bars.tsx`
- Create: `web/src/components/landing/visualizations/__tests__/factor-bars.test.tsx`

**Step 5a: Write the failing test**

```typescript
test("renders 5 factor bars with percentile values", () => {
  const factors = { quality: 85, value: 72, momentum: 65, sentiment: 58, growth: 90 }
  render(<FactorBars factors={factors} />)
  expect(screen.getByText("QUALITY")).toBeInTheDocument()
  expect(screen.getByText("85")).toBeInTheDocument()
})
```

**Step 5b: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/visualizations/__tests__/factor-bars.test.tsx`
Expected: FAIL

**Step 5c: Implement FactorBars**

5 horizontal percentile bars with labels (mono-label), color-encoded by tier (0-20 red, 20-40 orange, 40-60 neutral, 60-80 green, 80-100 bright green), numeric values right-aligned.

**Step 5d: Run test to verify it passes**

Expected: PASS

**Step 5e: Commit**

```
git add web/src/components/landing/visualizations/
git commit -m "feat(web): add FactorBars visualization component"
```

---

## Step 6: Visualization Components - AnimatedCounter, Sparkline, RadarChart

**Files:**
- Create: `web/src/components/landing/visualizations/animated-counter.tsx`
- Create: `web/src/components/landing/visualizations/sparkline.tsx`
- Create: `web/src/components/landing/visualizations/radar-chart.tsx`
- Create: tests for each

**Step 6a: Write failing tests for all three**

AnimatedCounter: renders a number that animates from 0 to target on mount.
Sparkline: renders an SVG polyline from an array of score values.
RadarChart: renders a 5-point SVG pentagon with filled area.

**Step 6b: Run tests to verify they fail**

**Step 6c: Implement all three components**

- AnimatedCounter: Uses useEffect + requestAnimationFrame to count up. Accepts `target: number`, `duration?: number`.
- Sparkline: SVG polyline with normalized y-values. Accepts `data: number[]`, `width?: number`, `height?: number`.
- RadarChart: SVG pentagon with 5 axes. Accepts `factors: { quality, value, momentum, sentiment, growth }`. Filled area uses accent-subtle, border uses accent.

**Step 6d: Run tests to verify they pass**

**Step 6e: Commit**

```
git add web/src/components/landing/visualizations/
git commit -m "feat(web): add AnimatedCounter, Sparkline, and RadarChart visualizations"
```

---

## Step 7: Hero Section Redesign - Editorial Spread

**Files:**
- Modify: `web/src/components/landing/sections/hero-section.tsx`
- Create: `web/src/components/landing/sections/system-report-card.tsx`
- Modify: hero section test file

**Step 7a: Create SystemReportCard component**

Shows top candidate from data:
- Ticker + name + composite score (mono-data)
- 5 thin horizontal factor percentile bars
- "Scored 2h ago" timestamp
- Subtle glow/shadow lift treatment

**Step 7b: Write test for SystemReportCard**

```typescript
test("renders candidate data in system report card", () => {
  render(<SystemReportCard candidate={mockCandidate} />)
  expect(screen.getByText("AAPL")).toBeInTheDocument()
  expect(screen.getByText("85")).toBeInTheDocument()
})
```

**Step 7c: Redesign HeroSection to two-column Editorial Spread**

Left column (55%):
- "Discipline. Engineered." (display-1, Instrument Serif)
- One-line subtext (body)
- Search bar with ticker chips

Right column (45%):
- SystemReportCard with top candidate from fallback/live data

Change minHeight from 100svh to 90svh.

**Step 7d: Run tests**

Run: `cd web && npx vitest run`
Expected: All pass

**Step 7e: Commit**

```
git add web/src/components/landing/sections/
git commit -m "feat(web): redesign hero as two-column Editorial Spread with SystemReportCard"
```

---

## Step 8: Authority Strip - Refined

**Files:**
- Modify: `web/src/components/landing/sections/authority-strip.tsx`
- Modify: test file

**Step 8a: Update AuthorityStrip**

- Accept data prop (HomepageData)
- Widen to max-w-6xl
- Add fourth column: "Last Cycle" with timestamp and cycle count
- Status dot: w-2 h-2 with subtle pulse animation
- Add StalenessIndicator below when using fallback data

**Step 8b: Update test**

Verify 4 columns render, status dot has pulse class.

**Step 8c: Run tests**

Expected: All pass

**Step 8d: Commit**

```
git add web/src/components/landing/sections/authority-strip.tsx
git commit -m "feat(web): refine authority strip with 4th column and data prop"
```

---

## Step 9: Evidence Panel - System Panel Archetype

**Files:**
- Modify: `web/src/components/landing/sections/evidence-section.tsx`
- Create: `web/src/components/landing/visualizations/selectivity-funnel.tsx`
- Create: `web/src/components/landing/visualizations/sector-bar-chart.tsx`
- Create: `web/src/components/landing/visualizations/factor-density-curves.tsx`

**Step 9a: Create visualization subcomponents**

- SelectivityFunnel: animated vertical funnel, counts animate on scroll-enter
- SectorBarChart: horizontal bar chart, color-coded with sector identifiers
- FactorDensityCurves: mini density curves for each of the 5 factors

**Step 9b: Redesign EvidenceSection as System Panel archetype**

Full-width panel with monospace header strip. Row 1 (3 columns): Selectivity Funnel, Sector Breakdown, existing Correlation Heatmap. Row 2 (full width): Factor Distribution Strip.

**Step 9c: Write/update tests**

**Step 9d: Run tests**

**Step 9e: Commit**

```
git add web/src/components/landing/
git commit -m "feat(web): redesign evidence panel as System Panel archetype with new visualizations"
```

---

## Step 10: Pipeline Section - Merged How It Works + Three Pillars

**Files:**
- Create: `web/src/components/landing/sections/pipeline-section.tsx`
- Create: `web/src/components/landing/visualizations/funnel-diagram.tsx`
- Create: `web/src/components/landing/visualizations/mini-candidate-stack.tsx`
- Create: test file

**Step 10a: Create FunnelDiagram visualization**

SVG funnel diagram, animated on scroll. Stocks flow through filter gates, counts decrement.

**Step 10b: Create MiniCandidateStack**

3 mini candidate cards stacked with slight offset for depth effect.

**Step 10c: Build PipelineSection**

Headline: "From 3,056 stocks to the ones worth your screen." (display-2)

Three alternating Editorial Spread subsections:
1. **Eliminate** (text left, visual right): FunnelDiagram
2. **Score** (visual left, text right): Mini RadarChart of top candidate
3. **Surface** (text left, visual right): MiniCandidateStack

Subsections separated by space-16 (64px). Alternating layout creates visual rhythm.

**Step 10d: Write tests**

```typescript
test("renders three pipeline subsections", () => {
  render(<PipelineSection data={mockData} />)
  expect(screen.getByText(/eliminate/i)).toBeInTheDocument()
  expect(screen.getByText(/score/i)).toBeInTheDocument()
  expect(screen.getByText(/surface/i)).toBeInTheDocument()
})
```

**Step 10e: Run tests**

**Step 10f: Commit**

```
git add web/src/components/landing/
git commit -m "feat(web): add Pipeline section merging How It Works and Three Pillars"
```

---

## Step 11: Results Stage - Data Stage Archetype

**Files:**
- Modify: `web/src/components/landing/sections/results-showcase-section.tsx`
- Modify: test file

**Step 11a: Redesign as Data Stage archetype**

Background: bg-bg-subtle for visual shift. 3 candidate cards showing:
- Ticker + company name (title-1)
- Composite score (mono-data, color-encoded)
- 30-day score trend sparkline (code-built SVG, 48px tall)
- 5 thin factor bars with percentile values
- Sector tag + freshness timestamp

Summary stat line below: "3,056 scanned - 2,841 eliminated - 215 scored - 12 survived"

**Step 11b: Update tests**

**Step 11c: Run tests**

**Step 11d: Commit**

```
git add web/src/components/landing/sections/results-showcase-section.tsx
git commit -m "feat(web): redesign Results Stage as Data Stage archetype with sparklines"
```

---

## Step 12: Pricing Refinement + Footer FAQ Absorption

**Files:**
- Modify: `web/src/components/landing/sections/pricing-section.tsx`
- Modify: `web/src/components/landing/sections/pricing-tier-card.tsx`
- Modify: `web/src/components/landing/sections/footer-section.tsx`
- Modify: `web/src/components/landing/sections/faq-section.tsx`

**Step 12a: Fix pricing**

- Remove Scout opacity: 0.85 (line 37 of pricing-tier-card.tsx)
- Use subtler border differentiation instead
- Add annual/monthly toggle (annual gets 2 months free)
- Widen to max-w-6xl

**Step 12b: Absorb FAQ into footer**

- Move FAQ accordion into expandable section within footer area
- Add "Score your first position" CTA + search bar above footer columns
- Delete standalone FaqSection from homepage flow

**Step 12c: Update homepage-client.tsx section ordering**

Remove FaqSection as standalone section. New flow:
Hero -> AuthorityStrip -> Evidence -> Pipeline -> Results -> Pricing -> Footer (with FAQ)

**Step 12d: Run tests**

**Step 12e: Commit**

```
git add web/src/components/landing/
git commit -m "feat(web): refine pricing, absorb FAQ into footer, finalize 7-section flow"
```

---

## Step 13: Dashboard App Shell - Sidebar + Top Bar

**Files:**
- Create: `web/src/components/layout/sidebar.tsx`
- Create: `web/src/components/layout/top-bar.tsx`
- Modify: `web/src/components/layout/app-shell.tsx`
- Create: tests for sidebar and top-bar

**Step 13a: Build Sidebar component**

Expanded: 240px, collapsed: 64px. Groups: CORE (Dashboard, Watchlist, Search), TOOLS (Smart Money, Backtesting), SYSTEM (Methodology, Guides, Status). Bottom: engine version stamp + plan tier badge. Active item: 2px left accent bar + bg-accent-subtle. Collapsed: icons only, tooltip on hover.

**Step 13b: Build TopBar component**

Height: 56px. Left: hamburger toggle + wordmark. Center: ticker search input with Cmd+K badge. Right: help, settings, user avatar/dropdown.

**Step 13c: Integrate into AppShell**

Replace current minimal layout with sidebar + top bar + main content area. Sidebar state managed via React state with localStorage persistence.

**Step 13d: Write tests**

```typescript
test("sidebar toggles between expanded and collapsed", () => {
  render(<Sidebar expanded={true} onToggle={vi.fn()} />)
  expect(screen.getByText("Dashboard")).toBeInTheDocument()
})

test("top bar renders search input", () => {
  render(<TopBar onMenuToggle={vi.fn()} />)
  expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument()
})
```

**Step 13e: Run tests**

**Step 13f: Commit**

```
git add web/src/components/layout/
git commit -m "feat(web): add collapsible sidebar + top bar app shell"
```

---

## Step 14: Dashboard Main Content - 3-Zone Grid

**Files:**
- Create: `web/src/components/dashboard/system-status-strip.tsx`
- Create: `web/src/components/dashboard/market-context-panel.tsx`
- Modify: `web/src/app/dashboard/page.tsx`
- Create: tests

**Step 14a: Build SystemStatusStrip**

Full width, 48px. Monospace: "CYCLE #847 - SCORED 3,056 - SURVIVING 12 - LAST RUN 2H AGO". Left-edge status dot (green/amber/red). Replaces "Good afternoon" greeting.

**Step 14b: Build MarketContextPanel**

Right column, 280px, sticky. Universe/Scored/Surviving counts. Cycle info with timestamp. Mini sector distribution horizontal bars. Mini score distribution histogram.

**Step 14c: Redesign dashboard page**

3-zone grid: SystemStatusStrip (full width) + Top Picks Grid (left, flexible) + MarketContextPanel (right, 280px). Add fallback data support.

**Step 14d: Fix error states**

Pattern: icon (32px) + primary message (title-2) + secondary message (caption). No raw errors, no developer commands.

- API unreachable: "System offline - Scores will appear when the engine reconnects"
- No picks: "No positions survived this cycle - The system found nothing worth your capital"
- Loading: skeleton cards with animated shimmer

**Step 14e: Write tests**

**Step 14f: Commit**

```
git add web/src/components/dashboard/ web/src/app/dashboard/
git commit -m "feat(web): redesign dashboard with 3-zone grid and clean error states"
```

---

## Step 15: Dashboard Keyboard Navigation

**Files:**
- Modify: `web/src/app/dashboard/page.tsx` or create `web/src/hooks/use-keyboard-nav.ts`

**Step 15a: Implement keyboard shortcuts**

- Cmd+K: global ticker search (focus search input)
- Cmd+/: focus sidebar filter
- Arrow Up/Down: navigate pick cards
- Enter: open selected asset
- Escape: close modals/search

**Step 15b: Write tests**

```typescript
test("Cmd+K focuses search input", () => {
  render(<Dashboard />)
  fireEvent.keyDown(document, { key: "k", metaKey: true })
  expect(screen.getByRole("searchbox")).toHaveFocus()
})
```

**Step 15c: Run tests**

**Step 15d: Commit**

```
git add web/src/hooks/ web/src/app/dashboard/
git commit -m "feat(web): add keyboard navigation to dashboard"
```

---

## Step 16: Asset Detail Page Redesign

**Files:**
- Modify: `web/src/app/asset/[ticker]/page.tsx`
- Create: `web/src/components/asset-detail/score-header.tsx`
- Create: `web/src/components/asset-detail/price-context.tsx`
- Create: `web/src/components/asset-detail/factor-panel.tsx`
- Create: `web/src/components/asset-detail/sector-peers.tsx`
- Create: tests

**Step 16a: Build ScoreHeader**

Composite score (mono-data, 48px) + tier badge. Full-width percentile bar (position in universe). Color-encoded by tier.

**Step 16b: Build PriceContext**

Current price, buy price, margin of safety in 3-row data table. Margin of safety color-coded (green positive, red negative).

**Step 16c: Build FactorPanel**

Right column (40%). 5 horizontal percentile bars (Quality, Value, Momentum, Sentiment, Growth). RadarChart below showing factor profile shape.

**Step 16d: Build SectorPeers**

Full-width bottom. System Panel archetype. Horizontal grouped bar chart: stock vs top 5 sector peers across all 5 factors. Monospace header.

**Step 16e: Redesign asset detail page**

Two-column layout (60/40). Left: ScoreHeader, PriceContext, score history sparkline, elimination filters grid. Right: FactorPanel with bars + radar. Bottom: SectorPeers.

**Step 16f: Add error state**

App shell remains visible. Center: icon + "Score data unavailable" + "This ticker will be scored in the next cycle. Check back after market close."

**Step 16g: Write tests, run tests**

**Step 16h: Commit**

```
git add web/src/components/asset-detail/ web/src/app/asset/
git commit -m "feat(web): redesign asset detail as two-column layout with radar chart"
```

---

## Step 17: Secondary Pages - Methodology, Guides, Login

**Files:**
- Modify: `web/src/app/methodology/page.tsx`
- Modify: `web/src/app/guides/page.tsx`
- Modify: `web/src/app/login/page.tsx`
- Create: `web/src/components/shared/page-header.tsx`

**Step 17a: Create standardized PageHeader**

Every non-homepage page gets:
```
[mono-label category tag]
[display-2 Page Title]
[body One-line description]
[space-16 gap before content]
```

**Step 17b: Update Methodology page**

- App shell when authenticated, marketing nav when not
- Widen to max-w-6xl
- Add sticky progress indicator (7 dots) on right edge
- Enforce alternating Editorial Spread layout for stage details

**Step 17c: Update Guides page**

- Add search/filter bar above cards
- Cards: 2px left-edge category color accent bar
- Reading view: max-w-3xl prose column

**Step 17d: Refine Login page**

- Add full wordmark below M logo
- Unify button border styles
- Add "Scoring 3,056 US equities daily" in mono-label below card

**Step 17e: Write tests, run tests**

**Step 17f: Commit**

```
git add web/src/components/shared/ web/src/app/methodology/ web/src/app/guides/ web/src/app/login/
git commit -m "feat(web): update secondary pages with standardized headers and refined layouts"
```

---

## Step 18: Legal Pages + Contact

**Files:**
- Modify: `web/src/app/terms/page.tsx`
- Modify: `web/src/app/privacy/page.tsx`
- Modify: `web/src/app/legal/page.tsx`
- Modify: `web/src/app/contact/page.tsx` (if exists)

**Step 18a: Apply prose styling to legal pages**

- max-w-3xl prose styling with proper heading hierarchy
- Table of contents sidebar on desktop for long documents
- App shell when authenticated, marketing nav when not

**Step 18b: Update contact/support page**

- terminal-card surface for contact form
- Input styling consistent with login page
- FAQ accordion reusing FaqItem pattern

**Step 18c: Run tests**

**Step 18d: Commit**

```
git add web/src/app/terms/ web/src/app/privacy/ web/src/app/legal/
git commit -m "feat(web): apply prose styling to legal pages"
```

---

## Step 19: Scroll Animation Variety

**Files:**
- Modify: all landing section components

**Step 19a: Apply varied animations per section**

| Section | Animation |
|---|---|
| Hero | Text sequential fade. SystemReportCard: scale 0.95 to 1.0 with slight rotation |
| Authority Strip | Slide up from y:30, 0.8s duration |
| Evidence Panel | Border draws in (clip-path), content fades with stagger |
| Pipeline | Alternating: odd sections slide from left, even from right |
| Results Stage | Cards cascade with 150ms stagger, y:30 offset |
| Pricing | Cards fan up with scale 0.97 to 1.0 |
| Footer | Simple fade |

**Step 19b: Replace uniform opacity:0/y:20 pattern with section-specific animations**

Each section GSAP code gets its own animation variant. Use clip-path for Evidence border draw-in. Use alternating x offsets for Pipeline.

**Step 19c: Run tests**

**Step 19d: Commit**

```
git add web/src/components/landing/
git commit -m "feat(web): add varied scroll animations per section archetype"
```

---

## Step 20: Integration Testing + Final Verification

**Files:**
- Run all test suites
- Visual verification

**Step 20a: Run full test suite**

```
cd web && npx vitest run
```
Expected: All tests pass

**Step 20b: Run ESLint**

```
cd web && npx eslint --fix .
```
Expected: Clean (no errors)

**Step 20c: Run build**

```
cd web && npx next build
```
Expected: Build succeeds

**Step 20d: Verify success criteria**

- [ ] All homepage sections render with data (fallback or live)
- [ ] Typography scale enforced: zero inline font-size in landing components
- [ ] Spacing uses only sanctioned values (8px grid)
- [ ] Dashboard app shell renders with sidebar + top bar
- [ ] Asset detail renders two-column layout with radar chart and factor bars
- [ ] All tests pass
- [ ] ESLint clean
- [ ] Unused components deleted
- [ ] Three distinct section archetypes visible on homepage
- [ ] Scroll animations varied across sections
- [ ] Error/empty states follow standard pattern

**Step 20e: Commit any final fixes**

```
git add .
git commit -m "chore(web): final verification and cleanup for visual overhaul"
```
