# Digital Horologist Landing Page Redesign — Technical Specification

**Date**: 2026-04-14
**Version**: 1.0
**Status**: Draft
**Approach**: Section Rebuild — new section components, keep shared utilities and visualization components

## Summary

Redesign the Margin Invest landing page to embody the "Digital Horologist" design system: an institutional, high-precision aesthetic inspired by Swiss watchmaking. The page is streamlined from 12 sections to 5, with a new color/typography/motion foundation and every section rebuilt from scratch to match the approved design direction.

### Creative North Star

Margin Invest is a deterministic investment analysis engine. The landing page should feel like a precision instrument — mechanically transparent, rigidly logical, editorially authoritative. Not a SaaS product page. Not a fintech dashboard. A calibrated analytical device.

### Page Flow

```
Hero ("DISCIPLINE ENGINEER")
  └─ stats row (absorbed Authority Strip)
Evidence
  ├─ "THE SELECTION FUNNEL" (full-width)
  └─ "FORENSIC ANALYSIS" (3-card grid: sector chart, heatmap, density curves)
Comparison Table
  └─ 4-column feature matrix (Margin Invest vs Screeners vs BlackBox)
Pricing ("CHOOSE YOUR APERTURE")
  └─ 3 tiers: Scout ($0) / Analyst ($19) / Portfolio ($49)
Footer
  └─ Logo + 2-column links + copyright
```

---

## 1. Design Tokens (globals.css)

The foundation layer. All existing CSS custom properties are replaced with the Digital Horologist token set.

### 1.1 Color Palette — Surface Hierarchy

Depth through calibrated tonal layering, not shadows or borders.

| Token | Value | Purpose |
|-------|-------|---------|
| `--surface` | `#08160f` | Base layer + 3% noise texture |
| `--surface-container-lowest` | `#0a1c12` | Recessed areas (inputs, footer) |
| `--surface-container-low` | `#0e2318` | Cards, terminal panels |
| `--surface-container` | `#122a1c` | Default containers |
| `--surface-container-high` | `#163220` | Elevated/active cards |
| `--surface-container-highest` | `#1a3a24` | Focused elements |
| `--primary` | `#80d8b2` | Glow, accent light, chart lines |
| `--primary-container` | `#1A7A5A` | Button fills, "moving parts" |
| `--on-primary-container` | `#EDE9E3` | Text on primary-container fills |
| `--on-surface` | `#EDE9E3` | Primary text |
| `--on-surface-variant` | `#A39E96` | Secondary text |
| `--surface-variant` | `#3f4943` | Grid lines (at 10% opacity) |
| `--outline-variant` | `#3f4943` | Ghost borders (at 15% opacity only) |
| `--surface-tint` | `#80d8b2` | Input focus glow |

Semantic colors (bullish, bearish, warning, percentile tiers) remain unchanged — they serve the dashboard, not the landing page.

### 1.2 The No-Line Rule

Major section boundaries are defined solely by background color shifts or tonal transitions. 1px solid borders are prohibited for section-level separation. The only permitted border is the "ghost border": `outline-variant` at 15% opacity, used on cards and inputs where accessibility requires a visible edge.

### 1.3 Typography

| Role | Font | Weight | Tracking | Usage |
|------|------|--------|----------|-------|
| Display | Newsreader | 400 | -0.02em | Hero headline, section titles |
| Display italic | Newsreader Italic | 400 | -0.02em | Footer tagline |
| UI / Body | Inter Tight | 400, 500, 600 | normal | Paragraphs, buttons, nav links |
| Data / Labels | Space Grotesk | 400, 500, 700 | 0.2em (labels) | Numbers, metrics, card headers, chart axes |

Scale (responsive, clamp-based):

| Token | Size Range | Font | Usage |
|-------|-----------|------|-------|
| `--text-display-lg` | 44px–72px | Newsreader | Hero headline |
| `--text-headline-md` | 28px–40px | Newsreader | Section titles |
| `--text-title-sm` | 17px–20px | Inter Tight 600 | Card titles |
| `--text-body-md` | 16px–17px | Inter Tight 400 | Body copy |
| `--text-label-md` | 14px | Space Grotesk 500 | Data values |
| `--text-label-sm` | 11px | Space Grotesk 500, uppercase | Card headers, axis labels |
| `--text-mono-data` | 24px–32px | Space Grotesk 700 | Large metric numbers |

### 1.4 Elevation

No traditional drop shadows. Depth via tonal layering.

- **Card lift**: Place `surface-container-high` on `surface-container-low` background
- **Ambient shadow** (floating elements only): `on-surface` tint, 32px blur, 0px offset, 6% opacity
- **Glassmorphism** (nav, modals): Semi-transparent `surface-container` + `backdrop-filter: blur(20px)`

### 1.5 Radii

- Buttons: `0.375rem` (6px)
- Cards: `0.5rem` (8px)
- Maximum anywhere: `0.75rem` (12px)
- No pill shapes. No fully rounded elements except status chips.

### 1.6 Motion

Existing GSAP + ScrollTrigger infrastructure preserved. Motion character shifts from "startup bounce" to "instrument needle settling":

- No `back.out` easing (springy overshoot)
- Preferred easings: `power2.out`, `expo.out`
- Entrance effects: `blur-up` and `fade-up` (keep), remove `slide-left`/`slide-right`
- Stagger: 0.08–0.12s between items
- Duration: 0.5–0.7s for section reveals
- `prefers-reduced-motion` support preserved

---

## 2. Navbar

Structural component unchanged. Styling only.

- Background: Semi-transparent `surface-container` with `backdrop-filter: blur(20px)`
- No bottom border (no-line rule) — blur contrast against page content creates separation
- Logo + links in `on-surface`, Inter Tight
- CTA button: `primary-container` fill, `0.375rem` radius, radial glow hover
- Ghost border fallback (15% opacity) only if accessibility audit requires it

---

## 3. Hero Section

Rebuilt from scratch. Absorbs Authority Strip data.

### 3.1 Layout

Two-column on desktop (60/40 split), stacks on mobile.

**Left column:**
- Headline: "DISCIPLINE ENGINEER" — all-caps Newsreader `display-lg`, tracking -0.02em
- Subtext: 1-2 lines describing the platform in Inter Tight `body-md`, `on-surface-variant`
- Stats row: 4 metrics in a horizontal strip
- CTA pair: Primary button (primary-container fill, radial glow hover) + ghost secondary button

**Right column:**
- InstrumentPanel component, restyled:
  - `surface-container-low` background
  - Ghost border
  - All data values in Space Grotesk
  - No solid internal borders — spacing separates content groups

### 3.2 Stats Row (absorbed Authority Strip)

4 metrics, each with:
- Large number: Space Grotesk `mono-data` scale, `on-surface`
- Small label: Space Grotesk `label-sm`, uppercase, `on-surface-variant`
- CountUp animation on scroll entry (preserved from existing CountUp utility)

Metrics: Universe count, score delta, transparency %, determinism %.

Data wiring from `authority-strip.tsx` moves into hero. The Authority Strip component is deleted.

### 3.3 Background

- Radial gradient: `primary` (#80d8b2) at ~8% opacity, centered behind stats row
- Grid overlay: preserved, shifted to `surface-variant` at 5% opacity
- Noise texture: 3% opacity on `surface` base

### 3.4 Animation

- Headline: Word-by-word `blur-up`, GSAP stagger (0.09s) — preserved
- Subtext: `blur-up` fade in
- Stats row: CountUp triggered on viewport entry
- CTA: `blur-up` entrance
- InstrumentPanel: Scale 0.95→1 + blur clear, `expo.out` easing (no rotation, no `back.out`)

---

## 4. Evidence Section

Two distinct visual blocks under one conceptual umbrella.

### 4.1 Block A: "THE SELECTION FUNNEL"

- Section heading: Newsreader, uppercase, tight tracking
- Full-width funnel visualization (SelectivityFunnel component, restyled):
  - Stage colors: each stage a different `surface-container-*` tier (tonal narrowing)
  - Labels: Space Grotesk
  - No solid borders between stages
  - Numbers: CountUp animation
- Summary stat line below: "3,916 → 247 → 74 → 14" in Space Grotesk `label-md`
- Generous vertical padding after

### 4.2 Block B: "FORENSIC ANALYSIS"

- Section heading: Newsreader, uppercase, tight tracking
- 3-card grid (responsive: 1-col mobile, 3-col desktop):
  - Sector bar chart
  - Correlation heatmap
  - Factor density curves
- Card styling:
  - `surface-container-low` background, ghost border
  - Header: Space Grotesk `label-sm`, uppercase (instrument readout aesthetic)
  - No divider lines inside cards — 0.75rem spacing between content groups
- Chart restyling (all 3):
  - Lines: 1.5px thick, `primary` color
  - No area fills under graphs
  - Grid lines: `surface-variant` at 10% opacity
  - Axis labels: Space Grotesk `label-sm`

### 4.3 Animation

- Funnel: ScrollReveal `blur-up` on viewport entry
- Forensic cards: ScrollReveal `blur-up` with 0.1s stagger

---

## 5. Comparison Table

### 5.1 Structure

4-column layout: Category | Margin Invest | Screeners | BlackBox

Rows: Scoring, Transparency, Filters, Auditability, Bias.

### 5.2 Styling

- No table borders (no-line rule)
- Row separation: alternating surface tiers (odd `surface`, even `surface-container-lowest`)
- Margin Invest column: `surface-container-high` background + subtle radial gradient of `primary` at ~5% opacity (spotlight effect)
- Column headers: Space Grotesk `label-sm`, uppercase
- Cell content: Inter Tight `body-md`
- Checkmarks/indicators: `primary` (#80d8b2) — no bright green, no emoji

### 5.3 Mobile

Cards layout — each category becomes a card showing all 3 platform values, rather than horizontal scroll.

### 5.4 Animation

Rows enter with `blur-up` stagger (0.08s between rows). No slide-from-left.

---

## 6. Pricing — "CHOOSE YOUR APERTURE"

### 6.1 Heading

"CHOOSE YOUR APERTURE" — Newsreader, uppercase, tight tracking.

### 6.2 Tier Cards

3 cards in a row (responsive: stack on mobile).

**All cards:**
- `surface-container-low` background, ghost border
- Tier name: Space Grotesk `label-sm`, uppercase
- Price: Newsreader display scale — largest visual element on card
- Feature list: Inter Tight, no bullets — 0.75rem vertical spacing between items (no dividers)
- CTA button: `0.375rem` radius

**Highlighted card (Analyst):**
- `surface-container-high` background (tonal lift, no scale transform)
- CTA: `primary-container` fill, radial glow hover

**Other cards (Scout, Portfolio):**
- Ghost CTA buttons (no fill, `outline-variant` border at 15%)

### 6.3 Monthly/Annual Toggle

- Track: `surface-container-lowest`
- Active indicator: `primary-container`
- No pill shape

### 6.4 Trust Strip

Below cards. Space Grotesk `label-sm`, `on-surface-variant`:
- "No credit card required"
- "30-day guarantee"
- "API available"

No icons. Separated by spacing, not dividers.

### 6.5 Animation

Cards enter with `blur-up` + stagger (0.1s). No `back.out` bounce. `expo.out` easing.

---

## 7. Footer

### 7.1 Layout

Full-width `surface-container-lowest` background — the darkest tier signals page end. No top border (the background shift from pricing is the boundary).

**Left**: Logo + one-line tagline in Newsreader italic.

**Right**: 2-column link grid (Product | Company), Inter Tight, `on-surface-variant`.

**Bottom bar**: Copyright + "Deterministic by design." in Space Grotesk `label-sm`.

---

## 8. Deletions

### 8.1 Sections Removed

| Component | Reason |
|-----------|--------|
| `social-proof-section.tsx` | Stats absorbed into hero |
| `transparency-strip.tsx` | Visual divider, violates no-line rule |
| `pipeline-section.tsx` | Editorial spreads cut for streamlined flow |
| `results-showcase-section.tsx` | Candidate cards cut |
| `faq-section.tsx` | Can live on own route later |
| `authority-strip.tsx` | Data absorbed into hero stats row |

### 8.2 Visualization Components Removed

| Component | Reason |
|-----------|--------|
| `mini-candidate-stack.tsx` | Pipeline section only |
| `sparkline.tsx` | Results Showcase only |
| `animated-counter.tsx` | Redundant with `count-up.tsx` |

### 8.3 Components Kept & Restyled

- `selectivity-funnel.tsx` / `funnel-diagram.tsx`
- `sector-bar-chart.tsx`
- `factor-density-curves.tsx`
- `instrument-panel.tsx`
- `hero-search.tsx`

### 8.4 Shared Utilities Kept (no changes)

- `scroll-canvas.tsx`
- `scroll-reveal.tsx`
- `count-up.tsx`
- `text-reveal.tsx`
- `types.ts`

### 8.5 Also Removed (resolved during review)

| Component | Reason |
|-----------|--------|
| `hero-candidate-card.tsx` | Not imported by any surviving section |
| `radar-chart.tsx` | Only used in pipeline-section (deleted) |

### 8.6 Also Kept & Restyled (resolved during review)

- `proof-heatmap.tsx` — used in evidence-section forensic analysis grid

---

## 9. Files Modified

| File | Change |
|------|--------|
| `web/src/app/globals.css` | Full token replacement |
| `web/src/app/layout.tsx` | Font imports (add Newsreader, Space Grotesk; remove Instrument Serif, Geist Mono) |
| `web/src/app/page.tsx` | Remove Authority Strip data fetch if separate; simplify SEO schema |
| `web/src/components/landing/homepage-client.tsx` | New 5-section flow |
| `web/src/components/nav/navbar.tsx` | Glassmorphism styling |
| `web/src/components/landing/sections/hero-section.tsx` | Rebuild |
| `web/src/components/landing/sections/evidence-section.tsx` | Rebuild (split into Funnel + Forensic) |
| `web/src/components/landing/sections/comparison-section.tsx` | Rebuild |
| `web/src/components/landing/sections/pricing-section.tsx` | Rebuild |
| `web/src/components/landing/sections/footer-section.tsx` | Rebuild |
| `web/src/components/landing/visualizations/selectivity-funnel.tsx` | Restyle |
| `web/src/components/landing/visualizations/sector-bar-chart.tsx` | Restyle |
| `web/src/components/landing/visualizations/factor-density-curves.tsx` | Restyle |
| `web/src/components/landing/hero/instrument-panel.tsx` | Restyle |

---

## 10. Out of Scope

- Dashboard pages (no design system changes beyond the landing page)
- New landing page sections not discussed
- Backend/API changes
- SEO content changes (beyond schema cleanup)
- Mobile app
- A/B testing infrastructure for the redesign
