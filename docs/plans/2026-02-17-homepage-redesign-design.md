# Homepage Redesign Design

Date: 2026-02-17
Status: Approved
Approach: Full rebuild (delete existing landing components, build from scratch)
Branch: feat/fluid-intelligence-redesign

## Overview

Complete homepage redesign shifting from fluid glass-morphism SaaS aesthetic to institutional hedge-fund terminal tone. The current 3-section homepage (Hero, Engine/Proof cards, Pricing) becomes an 8-section structured progression that communicates deterministic rigor.

## Decisions

- **Background**: Remove WebGL fluid shader entirely. Replace with CSS gradients (deep green-black).
- **Hero data**: Real API data with hardcoded mock fallback for unauthenticated/error states.
- **Pipeline + Cards**: Merge the pipeline diagram and engine card sections into one cohesive section. Pipeline is a sticky visual anchor; cards provide scrollable detail beneath.
- **Tier rename**: Full rename across entire stack: Scout → Analyst, Operator → Portfolio, Allocator → Institutional. Requires DB migration + API + billing + UI changes.
- **Proof section**: Real data for factor breakdown and growth/value tilt. Mock/illustrative for correlation heatmap and backtest.
- **Animation**: Add GSAP ScrollTrigger alongside existing Framer Motion. GSAP handles scroll-linked animations (pipeline highlighting, card motion). Framer Motion handles entrance animations.
- **Mobile**: Vertical stack with scroll-reveal for all sections. No horizontal motion on mobile.

## Section Structure (Top to Bottom)

### 1. Hero — Outcome + Immediate Proof

Full viewport height, split layout.

**Left side:**
- Headline: "Conviction. Engineered." — font-display (Instrument Serif), ~88px desktop, word-by-word Framer Motion reveal
- Subheadline: "A deterministic capital allocation system that replaces narrative with structure." — Inter Tight, text-lg, muted secondary
- Primary CTA: "Open the Dashboard" → /dashboard — solid accent button
- Secondary CTA: "See the Methodology" → /methodology — ghost/underline link

**Right side — HeroCandidatePanel component:**
- Server component fetches top-scored asset from API, falls back to hardcoded AAPL mock
- Displays: ticker, current price, price target, margin of safety %, conviction score (animated counter), sector rank percentile
- Mini sparkline chart (SVG, last 30 days)
- 5-factor horizontal bars (valuation/quality/momentum/sentiment/growth)
- Timestamp: "Last recalculated 04:02 EST" — font-mono, text-xs

**Background:** CSS gradient — deep #0A0F0D to #0D1510, subtle radial highlight behind candidate panel in muted emerald.

**Mobile:** Stacks vertically — headline on top, candidate panel below (scaled down).

### 2. The Problem (Short. Controlled.)

Centered, constrained width (max-w-3xl), ~60vh height.

- Headline: "Most investors react. Few operate with structure." — font-display, text-4xl
- Four bullet points with dash markers:
  - No filtering discipline
  - No factor weighting memory
  - No sector normalization
  - No portfolio-level correlation awareness
- Closer: "Margin Invest replaces guesswork with a repeatable system."

**Animation:** Headline fades in on scroll. Bullets stagger in (0.1s delay each). Closer fades in last. Thin horizontal rule below.

### 3. The Engine (Merged Pipeline + Counter-Scrolling Cards)

Most complex section. Two sub-parts.

**Part A — Pipeline Diagram (Sticky Anchor):**

Sticky at top of section during card scroll. Six nodes in horizontal line:

DATA → FILTER → FACTOR MODEL → NORMALIZE → SCORE → PORTFOLIO

- Each node: small rounded rectangle, font-mono, text-xs uppercase
- Connected by thin lines with subtle animated pulse (GSAP)
- Corresponding stage highlights (emerald glow + fill) as matching cards pass center
- Mobile: condensed 3x2 grid or horizontal scrollable strip

**Part B — Counter-Scrolling Card Rows:**

Below the sticky pipeline, two rows scroll horizontally driven by vertical scroll (GSAP ScrollTrigger).

Top Row (scrolls left) — INPUT + GATING:
1. Raw Market Signal
2. Data Integrity + Normalization
3. Elimination Filters
4. Survivorship Bias Control
5. Liquidity Thresholding

Bottom Row (scrolls right) — SCORING + OUTPUT:
1. Multi-Factor Ranking
2. Percentile Normalization
3. Conviction Score Synthesis
4. Sector-Neutral Construction
5. Portfolio Correlation Mapping

**Card design:** 320px wide, dark background with thin border (no glass). Uppercase subtitle, font-display title, 1-2 line description. Subtle connecting lines between cards animate with scroll. Spotlight effect: cards brighten at center, dim at edges.

**Pipeline ↔ Cards sync:** Top row maps to first 3 pipeline stages (DATA, FILTER, FACTOR MODEL). Bottom row maps to last 3 (NORMALIZE, SCORE, PORTFOLIO). Cards passing center trigger the corresponding pipeline stage highlight.

**Mobile:** Pipeline as small header. Cards stack vertically with scroll-reveal, interleaved from both rows.

### 4. Proof — The Machine in Action

Full-width section, max-w-6xl content area.

Headline: "Structure creates measurable advantage." — font-display, text-4xl

Four proof cards in 2x2 grid (desktop), single column (mobile):

**Card 1 — Factor Transparency (real data with mock fallback):**
- Single scored asset's factor breakdown
- Horizontal bars animate from 0 to value on scroll-in
- Data source: top-scored asset from API

**Card 2 — Growth vs Value Tilt (real data with mock fallback):**
- Mini bar visualization: growth factor weight vs value factor weight
- Shows engine adjustment based on growth stage detection

**Card 3 — Portfolio View (mock/illustrative):**
- Correlation heatmap snapshot — 5x5 colored grid SVG
- Shows correlated position identification

**Card 4 — Historical Application (mock/illustrative):**
- Small line chart: backtested conviction scores vs actual returns
- Includes appropriate disclaimer text

**Card styling:** Dark background, thin border, font-mono for numbers. Percentile bars use 5-tier color scale. Charts animate from zero with ease-in-out cubic.

### 5. Positioning — Who This Is For

Centered, two-column on desktop (max-w-4xl).

Headline: "Built for disciplined capital allocators." — font-display, text-4xl, centered

Left column ("Not for") — muted text-text-tertiary:
- Day traders
- Narrative chasers
- Meme cycles

Right column ("For") — brighter text-text-primary with subtle accent:
- Long-horizon investors
- Portfolio operators
- Capital stewards

**Animation:** Columns fade in together on scroll. No stagger. Mobile: stacks vertically.

### 6. Pricing (Renamed Tiers)

Three-column grid (max-w-4xl), centered.

Header line: "The system scales with your responsibility." — text-sm, uppercase, tracking-wide

| Tier | Price | Highlight | Key Features |
|------|-------|-----------|--------------|
| Analyst | Free | — | 3 analyses/mo, composite score, top-level breakdown, 5-ticker watchlist |
| Portfolio | $29/mo | Elevated, accent border | Unlimited, full 6-factor, 90-day history, 25-ticker watchlist, alerts |
| Institutional | $79/mo | — | Everything + unlimited history, portfolio correlation, sector rotation, API access |

**Card design:** Dark cards with thin borders. Portfolio tier slightly elevated with accent border. No glass effects.

**Animation:** Cards fade up with useInView, staggered 0.12s. Slight elevation on hover.

**CTA below:** "Start Building Conviction" → /dashboard. Caption: "No credit card required for Analyst tier."

### 7. Legitimacy Strip

Full-width thin strip (py-6), subtle border top/bottom.

Single row of trust markers — font-mono, text-xs, uppercase, muted:
- Data Sources: SEC Filings, Earnings Transcripts, Market Feeds
- Updated Daily
- Encrypted Key Storage
- Audit-Friendly Scoring
- No Hidden Heuristics

Static. No animation. Separated by thin vertical dividers.

### 8. Footer (Institutional)

Replaces current minimal footer. Full-width, max-w-6xl.

Multi-column link grid:
Support | Methodology | Security | Legal | Status | API | Contact

Bottom: Copyright + version stamp: "© 2026 Margin Invest · Engine v1.3.2"

Styling: font-mono for version, text-xs, muted. Horizontal rule above.

## Visual Direction

### Tone
Controlled dominance. Bloomberg x Stripe x Apple minimalism.

### Avoid
- Playful SaaS gradients
- Neon crypto vibes
- Loud animations
- Glass-morphism effects

### Adopt
- Dense data areas with breathing margins
- Thin separators
- Subtle grid overlays
- High contrast typography
- Small numeric details everywhere (timestamps, version numbers, engine build IDs)

### Typography
- Headlines: Instrument Serif (font-display) — keep existing
- Body/UI: Inter Tight (font-sans) — keep existing
- Data/numbers: Geist Mono (font-mono) — keep existing

### Color Updates (Dark Mode)
- --color-bg-primary: #0A0F0D (deeper green-black, was #110F0D)
- --color-bg-elevated: #111A15 (dark emerald tint, was #1A1714)
- --color-accent: #1A7A5A (keep existing muted emerald)
- NEW --color-gold-highlight: soft gold for micro-accent highlights
- Keep existing 5-tier percentile colors and sector accent colors

### Motion Architecture
- Easing: cubic-bezier(0.4, 0.0, 0.2, 1) — no spring bounce
- GSAP ScrollTrigger: scroll-linked pipeline highlighting, card horizontal motion, connecting line animation
- Framer Motion: entrance animations (fade-up, word reveal), hover states, animated counters
- All motion respects prefers-reduced-motion

## Dependencies

### Added
- gsap + @gsap/react — ScrollTrigger for scroll-linked animations

### Removed
- @react-three/fiber — WebGL shader removed
- three — WebGL shader removed
- @react-three/drei — WebGL shader removed
- @react-three/postprocessing — WebGL shader removed

Estimated bundle savings: ~200KB+

## Components Removed
- fluid-shader.tsx
- fluid-shader-loader.tsx
- dna-provider.tsx
- glass-surface.tsx (no more glass effects)
- chapter-hero.tsx
- chapter-cards.tsx
- chapter-path.tsx
- chapter-indicator.tsx
- flow-card.tsx

## Components Created
- hero-section.tsx — Split hero with headline + candidate panel
- hero-candidate-panel.tsx — Live/mock scored asset preview
- problem-section.tsx — Problem statement bullets
- engine-section.tsx — Container for pipeline + cards
- pipeline-diagram.tsx — Sticky 6-stage horizontal pipeline
- engine-card-rows.tsx — Counter-scrolling card rows (GSAP)
- engine-card.tsx — Individual engine card (terminal style)
- proof-section.tsx — 2x2 proof cards grid
- proof-card.tsx — Individual proof card with micro-chart
- positioning-section.tsx — For/not-for two-column
- pricing-section.tsx — Renamed tier cards
- tier-card.tsx — Individual pricing tier (terminal style)
- legitimacy-strip.tsx — Trust marker strip
- footer-institutional.tsx — Expanded institutional footer

## Migration: Tier Rename

Full rename: Scout → Analyst, Operator → Portfolio, Allocator → Institutional

Affected:
- DB: plan column values in users/subscriptions tables (migration required)
- API: plan enum values, billing endpoints, Stripe product metadata
- Web: all pricing UI, pro-gate component, settings page, account page
- Billing: Stripe product/price names if applicable

This is a separate work stream from the homepage UI rebuild and should be coordinated carefully.

## Mobile Strategy

All sections degrade to vertical stack with scroll-reveal:
- Hero: headline above, candidate panel below
- Problem: single column
- Engine: pipeline as condensed header, cards in interleaved vertical column
- Proof: single column card stack
- Positioning: "Not for" above "For"
- Pricing: single column, Portfolio tier still visually elevated
- Legitimacy: wraps to 2-3 rows
- Footer: single column link list

## Acceptance Criteria

1. No generic SaaS stacking — scroll feels like unlocking a system
2. Cards move horizontally while vertical scroll continues (desktop)
3. Pipeline stages highlight in sync with card scroll position
4. Page loads fast (no WebGL, reduced bundle size)
5. Mobile gracefully degrades all horizontal motion to vertical
6. All components are modular and independently testable
7. Real data integration works with graceful mock fallback
8. prefers-reduced-motion fully respected
