# Institutional Homepage — 10/10 Rebuild Design

**Date:** 2026-02-18
**Status:** Approved
**Approach:** Full rebuild — delete all `web/src/components/landing/` components, rebuild from scratch
**Animation Library:** GSAP only (remove Framer Motion from homepage)
**Branch:** `feat/fluid-intelligence-redesign`

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Candidate rotation data | Static fallback pool + dashboard picks override | Always renders without API; real data when available |
| Pipeline chips placement | Standalone section (section 3) | Spec requires it before engine cards; sticky on scroll into section 4 |
| Factor bars count | 5 (add sentiment + growth to API) | Extend PickSummary with sentiment_percentile, growth_percentile from score_detail JSONB |
| Micro-density metadata | Real where possible, static rest | last_updated, universe count from API; version strings hardcoded |
| Proof section charts | Full Recharts (Historical + Heatmap) + CSS (factor bars, tilt) | Maximum polish for institutional feel |
| Animation library | GSAP only | Spec mandates cubic-bezier(0.4, 0, 0.2, 1), no spring physics; single library consistency |
| Sparkline on hero card | Omitted | Card already dense with conviction score, 5 factor bars, prices, margin of safety |
| Implementation approach | Full rebuild | Every component changes substantially; clean build ensures spec compliance |

## Global Design Rules

### Tone
Controlled. Dense but not cluttered. Analytical. Intentional.

### Motion
- No spring physics, no bounce, no overshoot
- Easing: `cubic-bezier(0.4, 0.0, 0.2, 1)` — registered as GSAP custom ease
- All transitions under 300ms unless scroll-bound

### Color (Dark Mode Primary)
- Background: `#0A0F0D` (bg-primary)
- Elevated: `#111A15` (bg-elevated)
- Accent: `#1A7A5A` (muted emerald)
- Text primary: `#EDE9E3`
- Text secondary: `#A39E96`
- Text tertiary: `#6B6660`
- Heatmap gradient: danger red → tertiary gray → accent green

### Typography
- Display: Instrument Serif (headlines)
- Sans: Inter Tight (body)
- Mono: Geist Mono (metadata, timestamps, version numbers)

### Micro-Details
- Version numbers, recalculation timestamps, universe counts scattered throughout
- `font-geist-mono`, `text-[10px]` or `text-xs`, `text-tertiary`, `tracking-wide`, `uppercase`
- Low contrast but visible — increases perceived system depth

---

## Section Order (9 Sections)

1. Hero (Live Engine Output)
2. Problem Section
3. Pipeline Stage Chips (standalone, sticky)
4. Horizontal Engine Cards (counter-scroll)
5. Proof Section (analytical charts)
6. Allocator Positioning
7. Pricing
8. Institutional Infrastructure
9. Footer

---

## Section 1: Hero — Live Engine Output

### Layout
Two-column split: left 55%, right 45%. Stacks vertically on mobile (left on top).

### Left Column
- **Headline:** "Conviction. Engineered." — `font-instrument-serif`, ~48px desktop / 36px mobile
- **Subtext:** "A deterministic capital allocation system that replaces narrative with structure." — Inter Tight, `text-secondary`, max-width ~480px
- **Primary CTA:** "Open the Dashboard" — solid accent button, links to `/dashboard`
- **Secondary CTA:** "See the Methodology" — text link with subtle underline, links to `/methodology`
- **Entrance:** GSAP stagger reveal (headline → subtext → CTAs), 150ms stagger

### Right Column — Rotating Candidate Card
- **Header bar:** "Live Engine Output — Today" (left), "Updated HH:MM EST · Engine v1.3.2" (right) — `font-geist-mono text-xs text-tertiary`
- **Data source:** Static fallback pool of 3-5 candidates (AAPL, MSFT, JNJ, COST, V), overridden by dashboard `picks[]` when API available
- **Card content:**
  - Ticker + sector badge (small pill, sector color from design tokens)
  - Current Price / Target Price side by side
  - Margin of Safety percentage
  - **Conviction Score** — largest element, ~48px mono font, color-coded by percentile tier
  - 5 factor bars: Valuation, Quality, Momentum, Sentiment, Growth (horizontal, animated fill)
  - Bottom metadata: "Universe: X,XXX · Eligible: XXX · Filters passed: X/X"
- **Rotation:** 7s interval. GSAP timeline: fade out 150ms → swap data → fade in 200ms. No carousel/slide.
- **Card styling:** `bg-bg-elevated`, 1px `border-accent/20`, low-opacity shadow, `rounded-xl`

### Mobile
- Rotation disabled
- Swipe gesture via touch events to manually advance
- Dot indicators below card

### Background
Solid `bg-primary` (#0A0F0D). No gradients, no mesh.

---

## Section 2: Problem Section

### Layout
Single centered column, `max-w-3xl`. Generous vertical padding (120px top, 80px bottom).

### Content
- **Headline:** "Most investors react. Few operate with structure." — `font-instrument-serif`, ~36px
- **Bullets** (em dash prefix, `text-secondary`, `text-base`, 24px spacing):
  - No filtering discipline
  - No factor weighting memory
  - No sector normalization
  - No portfolio-level correlation awareness
- No closing statement — section acts as deliberate pause

### Animation
GSAP ScrollTrigger: headline fades in, bullets stagger (100ms delay each), 300ms duration.

### Divider
Thin 1px `border-subtle` at section bottom.

---

## Section 3: Pipeline Stage Chips (Standalone)

### Layout
Full-width, horizontally centered row of 6 labels. Becomes sticky when entering Section 4.

### Stages
`DATA → FILTER → FACTOR MODEL → NORMALIZE → SCORE → PORTFOLIO`

### Styling
- `font-geist-mono`, `text-xs`, `tracking-widest`
- Arrow separators: `→` in `text-tertiary`
- Inactive: `text-tertiary`
- Active: `text-accent` with 2px underline bar (not a pill)
- Active glow: `box-shadow: 0 0 8px rgba(26, 122, 90, 0.3)` — 250ms fade in, no pulsing

### Scroll Behavior
- `position: sticky; top: 0` with `bg-primary/95 backdrop-blur-sm` when reaching viewport top
- GSAP ScrollTrigger maps engine section scroll progress (0→1) to stages (0→5)
- All 6 stages highlighted by 75-80% scroll progress
- Metadata label below stages: "Factor Model v2.1" — `text-[10px] text-tertiary`

### Mobile
Wraps to 2 rows (3 stages per row), same highlighting behavior.

---

## Section 4: Horizontal Engine Cards

### Layout
Two horizontal rows in a tall scroll-driven container, pinned during scroll.

### Top Row (INPUT → GATING) — scrolls left
1. Raw Market Signal
2. Data Integrity + Normalization
3. Elimination Filters
4. Survivorship Bias Control
5. Liquidity Thresholding

### Bottom Row (SCORING → OUTPUT) — scrolls right
1. Multi-Factor Ranking
2. Percentile Normalization
3. Conviction Score Synthesis
4. Sector-Neutral Construction
5. Portfolio Correlation Mapping

### Card Styling
- Fixed 320px width, `terminal-card` base
- Uppercase subtitle: `text-xs text-tertiary tracking-wide`
- Title: `font-instrument-serif text-2xl`
- Description: `text-sm text-secondary`, 1-2 lines

### Enhancements
- **Connection lines:** 8-10% opacity `border-accent` dashed lines grouping INPUT → SCORING → OUTPUT
- **Center highlight:** Card closest to viewport center gets `opacity-100`, others `opacity-70`. 200ms transition.
- **No clipping:** Clean bleed into adjacent sections

### GSAP Implementation
ScrollTrigger with `scrub: true`. Top row `x: 0 → -30%`, bottom row `x: -30% → 0`. Section pinned during scroll.

### Mobile
Vertical interleaved stack, no horizontal motion, staggered fade-in.

---

## Section 5: Proof Section

### Layout
Centered headline, 2x2 grid below (single column on mobile).

### Headline
"Structure creates measurable advantage." — `font-instrument-serif`, ~36px

### Card 1: Factor Transparency
- 5 horizontal percentile bars: Valuation, Quality, Momentum, Sentiment, Growth
- Small numeric labels at bar ends
- Minimal grid guides at 25/50/75 marks
- CSS-rendered bars with GSAP fill animation on scroll

### Card 2: Growth vs Value Tilt
- Two horizontal bars (Recharts BarChart)
- Clean labels, minimal annotation
- Shows portfolio growth vs value tilt ratio

### Card 3: Correlation Heatmap
- Recharts custom component or CSS grid
- Institutional red → gray → green gradient (danger/tertiary/accent tokens)
- 5x5 grid with numeric overlays in 2-3 key cells
- Small axis labels, legend with value range (-1.0 to +1.0)
- Thin 1px cell dividers

### Card 4: Historical Application
- Recharts LineChart
- Portfolio line: muted emerald (accent)
- Benchmark line: thin neutral gray (text-tertiary)
- X-axis date markers, Y-axis percentage markers
- Subtle dashed grid lines, dotted baseline at 0%
- No decorative gradients or rounded shapes

### Card Wrapper
`terminal-card` styling, uppercase title in `text-xs text-tertiary tracking-wide`. GSAP fade-in on scroll.

### Metadata
"Sector-neutral by design" — `text-[10px] text-tertiary` near section header.

---

## Section 6: Allocator Positioning

### Layout
Centered `max-w-4xl`. Headline above two micro-columns.

### Headline
"Built for disciplined capital allocators." — `font-instrument-serif`, ~36px

### Two Columns (equal width desktop, stacked mobile)

**Left — "Not for:" (`text-tertiary`)**
- Narrative traders
- Signal chasers
- Emotion-driven decisions

**Right — "For:" (`text-accent`)**
- Long-horizon allocators
- Portfolio operators
- Structured decision-makers

### Styling
`text-sm`, subtle weight. Generous whitespace. Thin vertical divider between columns on desktop. Authority through restraint.

---

## Section 7: Pricing

### Pre-Headline
"The system scales with your responsibility." — `text-sm text-tertiary`, centered

### Tiers (3 cards in a row, stacked on mobile)

**Analyst** (Free) — standard `terminal-card`
- 3 ticker analyses/month
- Composite score + conviction level
- Top-level factor breakdown
- 5-ticker watchlist

**Portfolio** ($29/mo) — `terminal-card` with `border-accent/30`
- "Most Popular" tag: `text-xs text-accent bg-accent/10 px-2 py-0.5 rounded` (subtle, not bright)
- Slight negative margin lift (`-mt-2`)
- Unlimited ticker analysis
- Full 6-factor breakdown
- 90-day score history
- 25-ticker watchlist
- Conviction change alerts

**Institutional** ($79/mo) — standard `terminal-card`
- Everything in Portfolio
- Unlimited score history
- Portfolio correlation analysis
- Sector rotation signals
- API access

### Styling
Flattened shadows: `shadow-sm` or `shadow-none`, 1px border only. Institutional, not SaaS.

---

## Section 8: Institutional Infrastructure (NEW)

### Layout
Full-width section, centered content `max-w-5xl`. Generous padding (100px+ vertical).

### Headline
"Institutional-Grade Infrastructure" — `font-instrument-serif`, ~36px

### Subtext
"Built on verified public data and deterministic scoring architecture." — `text-secondary`

### Bullet Blocks (3-column grid desktop, 1-column mobile)
- SEC Filings + Earnings Transcripts
- Market Data Feeds (Daily Refresh)
- Encrypted API Key Storage
- Deterministic, Audit-Friendly Scoring
- No Hidden Heuristics

Each: em dash prefix, `text-sm`, generous spacing, thin 1px `border-subtle` dividers.

---

## Section 9: Footer

### Layout
Two-column, full-width. Thin `border-subtle` top border.

### Left
Links: Support, Methodology, Security, Legal, Status, API, Contact — `text-sm text-secondary`, horizontal desktop, vertical mobile.

### Right
"Engine v1.3.2" and "© 2026 Margin Invest" — right-aligned, `font-geist-mono text-xs text-tertiary`.

---

## API Changes Required

### Extend PickSummary Schema
Add two fields to `PickSummary` in `api/src/margin_api/schemas/dashboard.py`:
- `sentiment_percentile: float | None`
- `growth_percentile: float | None`

Pull from `score_detail` JSONB during dashboard query construction in `api/src/margin_api/routes/dashboard.py`.

No new endpoints required.

---

## Performance Constraints

- No layout shift on card rotation (fixed-dimension container)
- Preload hero data server-side (SSR with `serverFetch`)
- Static fallback pool ensures instant render without API
- Fast LCP — no heavy client-side data fetching before first paint
- Mobile degrades gracefully: no auto-rotation, no horizontal scroll, simplified animations
- No WebGL

---

## File Structure (New)

```
web/src/components/landing/
├── hero-section.tsx              # Section 1
├── hero-candidate-card.tsx       # Rotating candidate card
├── hero-candidate-data.ts        # Static fallback pool + types
├── problem-section.tsx           # Section 2
├── pipeline-chips.tsx            # Section 3 (standalone, sticky)
├── engine-section.tsx            # Section 4 (counter-scroll)
├── engine-card.tsx               # Individual engine card
├── proof-section.tsx             # Section 5
├── proof-factor-bars.tsx         # CSS percentile bars
├── proof-tilt-chart.tsx          # Recharts bar chart
├── proof-heatmap.tsx             # Recharts/CSS heatmap
├── proof-historical-chart.tsx    # Recharts line chart
├── positioning-section.tsx       # Section 6
├── pricing-section.tsx           # Section 7
├── pricing-tier-card.tsx         # Individual tier card
├── infrastructure-section.tsx    # Section 8 (new)
├── footer-section.tsx            # Section 9
├── micro-metadata.tsx            # Reusable metadata label component
├── section-indicator.tsx         # Fixed right-side nav dots
├── index.ts                      # Barrel exports
└── __tests__/
    ├── hero-section.test.tsx
    ├── pipeline-chips.test.tsx
    ├── engine-section.test.tsx
    ├── proof-section.test.tsx
    ├── pricing-section.test.tsx
    └── infrastructure-section.test.tsx
```

## Success Criteria

The homepage must:
- Feel like a live capital allocation engine
- Feel serious enough for institutional allocators
- Remove all startup softness
- Preserve horizontal card counter-motion
- Complete pipeline highlight before scroll end (75-80%)
- Make the hero card the dominant focal element
- Create daily relevance through live rotation
- Pass all existing tests (or have replacements)

If any change introduces playfulness, flashiness, or startup SaaS feel — remove it.
