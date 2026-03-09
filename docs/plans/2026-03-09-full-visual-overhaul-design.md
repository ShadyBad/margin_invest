# Full Visual Overhaul — Design Document

**Date:** 2026-03-09
**Status:** Approved
**Approach:** Institutional Editorial (B) with strategic Terminal elements (A)

## Context

A premium fintech design audit scored the product at 5.5/10 overall premium perception. The audit identified strong brand foundations (typography, color, copy positioning) with critical gaps in layout composition, product visibility, dashboard maturity, and visual craft. The product reads as "well-written dark-mode landing page template" rather than "serious financial infrastructure."

Key findings:
- Homepage hero is empty — no product artifact visible
- 9 homepage sections with identical flat grid layouts create scroll fatigue
- Dashboard lacks app shell, information density, and proper error states
- Design system tokens exist but enforcement is weak (dead heading classes, arbitrary spacing, shadcn token collision)
- Zero custom illustrations or data visualizations beyond styled text
- Uniform scroll animation (opacity:0, y:20 everywhere)

## Design Principles

1. **Show, don't tell.** The product is the pitch. Every section earns its place by demonstrating the system, not describing it.
2. **Institutional Editorial meets Terminal.** Instrument Serif headlines create editorial authority. Monospace labels and system panels preserve engineering identity. Neither dominates.
3. **Three section archetypes, not one.** System Panel (data-dense terminal), Editorial Spread (asymmetric text+visual), Data Stage (product showcase). Sections alternate to create visual rhythm.
4. **Always populated.** Fallback data system ensures no section ever shows placeholder text or empty states on the marketing page.
5. **Design system enforced, not suggested.** Typography scale, spacing grid, and section archetypes are rules, not guidelines.

## Scope

Single-phase implementation covering:
- Design system enforcement (typography, spacing, token cleanup)
- Homepage redesign (7 sections, down from 9)
- Dashboard overhaul (collapsible sidebar + top bar app shell)
- Asset detail page redesign (two-column layout with radar chart)
- Secondary pages (methodology, guides, login, legal)
- Fallback data system
- Code-built visualizations with selective SVG illustrations

## Section 1: Design System Enforcement

### Typography Scale

| Token | Desktop | Tablet | Mobile | Font | Use |
|---|---|---|---|---|---|
| `display-1` | 72px | 56px | 44px | Instrument Serif | Hero headline only |
| `display-2` | 48px | 40px | 32px | Instrument Serif | Section headlines |
| `title-1` | 28px | 24px | 22px | Inter Tight 600 | Card/panel titles |
| `title-2` | 20px | 18px | 17px | Inter Tight 600 | Sub-headings |
| `body` | 17px | 16px | 16px | Inter Tight 400 | Body text |
| `caption` | 14px | 13px | 13px | Inter Tight 400 | Secondary descriptions |
| `mono-label` | 11px | 11px | 10px | Geist Mono | System labels, tracking 0.2em |
| `mono-data` | 32px | 28px | 24px | Geist Mono | Large data numbers |

Every component references these tokens. No inline font sizes.

### Spacing Scale (8px base)

Enforced multiples of 8: 4, 8, 12, 16, 24, 32, 48, 64, 80, 96, 128px.

| Token | Value | Tailwind | Use |
|---|---|---|---|
| `space-1` | 4px | `1` | Tight inner gaps |
| `space-2` | 8px | `2` | Label margins |
| `space-3` | 12px | `3` | Small component gaps |
| `space-4` | 16px | `4` | Standard component padding |
| `space-6` | 24px | `6` | Card padding |
| `space-8` | 32px | `8` | Section inner spacing |
| `space-12` | 48px | `12` | Between components within section |
| `space-16` | 64px | `16` | Section padding (small) |
| `space-20` | 80px | `20` | Section padding (standard) |
| `space-24` | 96px | `24` | Section padding (large, hero) |
| `space-32` | 128px | `32` | Maximum section gap |

### Token Cleanup

- Remove shadcn oklch `:root` block, replace with direct references to custom design system tokens
- Delete unused components: `testimonial-section.tsx`, `infrastructure-section.tsx`, `positioning-section.tsx`, `problem-section.tsx`, `engine-section.tsx`, `engine-card.tsx`, `section-indicator.tsx`
- Reorganize landing components: `landing/sections/`, `landing/visualizations/`, `landing/shared/`

### Three Section Archetypes

**Type A — "System Panel":** `bg-bg-elevated` surface, `border-border-subtle`, monospace header strip with status dot, internal grid layout. Used for: Evidence, Pipeline.

**Type B — "Editorial Spread":** Full-width, no border. Instrument Serif headline, asymmetric 40/60 or 60/40 text-to-visual split. Used for: Hero, Pipeline subsections.

**Type C — "Data Stage":** Subtle background shift (`bg-bg-subtle`), centered content, rich visualization as focal point, minimal text. Used for: Results, Pricing.

## Section 2: Homepage Redesign

### New Section Flow (7 sections, down from 9)

```
Hero (with product artifact)
  → Authority Strip (refined)
  → Evidence Panel (expanded)
  → Pipeline (How It Works + Three Pillars merged)
  → Results Stage (live candidates)
  → Pricing (refined)
  → Footer (absorbs FAQ)
```

Narrative arc: product proof → system credibility → how it works → what it surfaces → get access.

### Hero — Editorial Spread Archetype

Left column (55%):
- "Discipline. Engineered." (display-1, Instrument Serif)
- One-line subtext (body)
- Search bar with ticker chips

Right column (45%):
- "System Report" artifact card showing top candidate from fallback data:
  - Ticker + name + composite score (mono-data)
  - 5 thin horizontal factor percentile bars
  - "Scored 2h ago" timestamp
  - Subtle glow/shadow lift treatment

Hero `minHeight` drops from `100svh` to `90svh` so Authority Strip peeks above the fold.

### Authority Strip — Refined

- Widen to `max-w-6xl`
- Add fourth column: "Last Cycle" with timestamp and cycle count
- Status dot: `w-2 h-2` with subtle pulse animation

### Evidence Panel — System Panel Archetype, Expanded

Full-width panel with monospace header strip ("SYSTEM OUTPUT — CYCLE #847 · MARCH 9, 2026").

Row 1 (3 columns):
- Selectivity Funnel: animated vertical funnel, counts animate on scroll-enter
- Sector Breakdown: horizontal bar chart, color-coded with sector tokens
- Factor Correlation Heatmap: keep existing, it's strong

Row 2 (full width):
- Factor Distribution Strip: mini density curves for each of the 5 factors across all scored stocks

### Pipeline — Merged How It Works + Three Pillars

Headline: "From 3,056 stocks to the ones worth your screen." (display-2)

Three alternating Editorial Spread subsections:

1. **Eliminate** (text left, visual right): SVG funnel diagram, animated on scroll. Stocks flow through filter gates, counts decrement.
2. **Score** (visual left, text right): Mini radar chart of top candidate showing all 5 factors. Code-built SVG pentagon.
3. **Surface** (text left, visual right): 3 mini candidate cards stacked with slight offset for depth.

Subsections separated by `space-16` (64px). Alternating layout creates visual rhythm.

### Results Stage — Data Stage Archetype

Background: `bg-bg-subtle` for visual shift.

3 candidate cards showing:
- Ticker + company name (title-1)
- Composite score (mono-data, color-encoded)
- 30-day score trend sparkline (code-built SVG, 48px tall)
- 5 thin factor bars with percentile values
- Sector tag + freshness timestamp

Summary stat line below: "3,056 scanned · 2,841 eliminated · 215 scored · 12 survived"

Always populated via fallback dataset.

### Pricing — Refined

- Remove Scout `opacity: 0.85`, use subtler border differentiation
- Add annual/monthly toggle (annual = 2 months free)
- Widen to `max-w-6xl`
- Keep gold accent on Analyst tier

### Footer — Absorbs FAQ

- FAQ accordion moves into expandable section within footer area
- "Score your first position" CTA + search bar above footer columns
- Footer columns (Product, Company) remain as-is

### Scroll Animation Variety

| Section | Animation |
|---|---|
| Hero | Text sequential fade. System Report card: scale 0.95→1.0 with slight rotation |
| Authority Strip | Slide up from y:30, 0.8s duration |
| Evidence Panel | Border draws in (clip-path), content fades with stagger |
| Pipeline | Alternating: odd sections slide from left, even from right |
| Results Stage | Cards cascade with 150ms stagger, y:30 offset |
| Pricing | Cards fan up with scale 0.97→1.0 |
| Footer | Simple fade |

## Section 3: Dashboard Overhaul

### App Shell — Collapsible Sidebar + Top Bar

**Top bar (56px):**
- Left: hamburger toggle (collapses sidebar to 64px icon rail), wordmark
- Center: always-visible ticker search input with `⌘K` badge
- Right: help, settings, user avatar/dropdown

**Sidebar (expanded: 240px, collapsed: 64px):**
- Groups: CORE (Dashboard, Watchlist, Search), TOOLS (Smart Money, Backtesting), SYSTEM (Methodology, Guides, Status)
- Bottom: engine version stamp + plan tier badge
- Active item: 2px left accent bar + `bg-accent-subtle`
- Collapsed: icons only, tooltip on hover

### Dashboard Main Content — 3-Zone Grid

**System Status Strip (full width, 48px):**
- Monospace: "CYCLE #847 · SCORED 3,056 · SURVIVING 12 · LAST RUN 2H AGO"
- Left-edge status dot (green/amber/red)
- Replaces "Good afternoon" greeting

**Top Picks Grid (left, flexible width):**
- Responsive card grid (3→2→1 columns)
- Each card: ticker, company, composite score (mono-data, color-encoded), tier badge, 5 mini factor bars, sector tag, timestamp
- Clickable → asset detail

**Market Context Panel (right, 280px, sticky):**
- Universe/Scored/Surviving counts
- Cycle info with timestamp
- Mini sector distribution horizontal bars
- Mini score distribution histogram

**Recent Changes (full width, below):**
- Timeline: "AAPL: score 72 → 68 (-4)" with timestamps
- Grouped by day, color-coded (green/red/amber)

### Error & Empty States

Pattern: icon (32px) + primary message (title-2) + secondary message (caption). Never surface developer commands or raw errors.

- API unreachable: "System offline · Scores will appear when the engine reconnects"
- No picks: "No positions survived this cycle · The system found nothing worth your capital"
- Loading: skeleton cards with animated shimmer

### Keyboard Navigation

- `⌘K` — global ticker search
- `⌘/` — focus sidebar filter
- `↑↓` — navigate pick cards
- `Enter` — open selected asset
- `Esc` — close modals/search

## Section 4: Asset Detail Page

### Two-Column Layout

**Top context bar:** breadcrumb + ticker (title-1) + company name + watchlist star + metadata row (sector, exchange, freshness)

**Left column (60%):**

*Score Header:*
- Composite score (mono-data, 48px) + tier badge
- Full-width percentile bar (position in universe)
- Color-encoded by tier

*Price Context:*
- Current price, buy price, margin of safety — 3-row data table
- Margin of safety color-coded (green positive, red negative)

*Score History:*
- 90-day sparkline (code-built SVG, ~120px tall)
- Hover shows point values
- Empty state: "History builds after 7 days of scoring"

*Elimination Filters:*
- 2×3 grid of filter badges with checkmark/X
- Failed filters highlighted red

**Right column (40%):**

*Factor Bars:*
- 5 horizontal percentile bars (Quality, Value, Momentum, Sentiment, Growth)
- Color-encoded with 5-tier percentile tokens
- Numeric values right-aligned

*Radar Chart:*
- 5-point pentagon SVG
- Filled area: `accent-subtle`, border: accent
- Shows factor profile shape at a glance

**Full-width bottom: Sector Peer Comparison**
- System Panel archetype
- Horizontal grouped bar chart: stock vs top 5 sector peers across all 5 factors
- Monospace header: "SECTOR PEERS · [SECTOR NAME]"

### Error State

App shell remains visible. Center: icon + "Score data unavailable" + "This ticker will be scored in the next cycle. Check back after market close." No raw errors.

## Section 5: Secondary Pages

### Methodology

- App shell when authenticated, marketing nav when not
- Widen to `max-w-6xl`
- Add SVG connecting lines between 7-stage cards
- Enforce alternating Editorial Spread layout for stage detail sections
- Add sticky progress indicator (7 dots) on right edge

### Guides

- App shell when authenticated
- Add search/filter bar above cards
- Cards: 2px left-edge category color accent bar
- Hover: preview excerpt expansion
- Reading view: `max-w-3xl` prose column, `body` token, `space-8` paragraph spacing

### Login

- Keep starfield background
- Card: use `shadow-modal` token for lift
- Add full wordmark below M logo
- Unify "Continue with email" button border with OAuth buttons
- Add "Scoring 3,056 US equities daily" in `mono-label` below card

### Legal / Terms / Privacy / Security

- App shell when authenticated, marketing nav when not
- `max-w-3xl` prose styling with proper heading hierarchy
- Table of contents sidebar on desktop for long documents

### Contact / Support

- `terminal-card` surface for contact form
- Input styling consistent with login page
- Support: FAQ accordion reusing `FaqItem` pattern

### Shared: Standardized Page Headers

Every non-homepage page:
```
[mono-label category tag]
[display-2 Page Title]
[body One-line description]
[space-16 gap before content]
```

## Section 6: Fallback Data System

### Static Snapshot File

`web/src/data/fallback-scoring-snapshot.json` — frozen copy of one real scoring cycle with 5-8 candidates across diverse sectors.

### Data Flow

```
page.tsx serverFetch("/api/v1/dashboard")
  → success: use live data
  → failure: import fallback-scoring-snapshot.json
  → HomepageClient always receives populated HomepageData
```

Change in `getHomepageData()`: `catch { return null }` → `catch { return fallbackData }`

### Staleness Indicator

When using fallback: `mono-label` text below Authority Strip:
"Sample data from last scoring cycle · Live data loads after engine run"
Uses `text-text-tertiary`. Disappears when live data is available.

Dashboard uses same strategy: fallback data + staleness indicator instead of error messages.

### Maintenance

Snapshot updated manually when significant scoring cycles complete. Checked into git. Needs to be real, not fresh.

## Code-Built Visualizations

All built in React + SVG. No D3 dependency.

| Visualization | Location | Description |
|---|---|---|
| Animated funnel | Pipeline section | SVG funnel with counts decrementing on scroll |
| Radar chart | Asset detail, Pipeline section | 5-point pentagon, filled area |
| Sparkline | Results Stage, Asset detail | 30-day/90-day score trend line |
| Factor bars | Multiple | Horizontal percentile bars, color-encoded |
| Animated counters | Evidence, How It Works | Numbers count up on scroll-enter |
| Sector bar chart | Evidence, Dashboard | Horizontal bars per GICS sector |
| Score histogram | Dashboard context panel | Distribution of composite scores |
| Factor density curves | Evidence row 2 | Mini distribution shapes per factor |

## Success Criteria

- All homepage sections render with data (fallback or live) — no empty states
- Typography scale enforced: zero inline font-size declarations in landing components
- Spacing uses only sanctioned values (8px grid multiples)
- Dashboard app shell renders with sidebar + top bar for authenticated users
- Asset detail renders two-column layout with radar chart and factor bars
- All existing tests pass (`cd web && npx vitest run`)
- ESLint clean (`cd web && npx eslint --fix .`)
- Unused components deleted
- Three distinct section archetypes visible on homepage scroll
- Scroll animations varied across sections (not uniform fade-up)
- Error/empty states follow the standard pattern (icon + message, no raw errors)
- Premium perception target: 7.5+/10 (up from 5.5)
