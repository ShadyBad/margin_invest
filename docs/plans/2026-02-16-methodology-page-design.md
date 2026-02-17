# Methodology Page Design

**Date:** 2026-02-16
**Status:** Approved

## Problem

The `/methodology` route returns a 404. Three landing page components link to it:

- `HeroSection` — "View methodology" button
- `EngineProof` — "Methodology documentation" link
- `FinalCTA` — "Methodology" footer nav link

**Root cause:** The page was never created. `web/src/app/methodology/page.tsx` does not exist.

## Solution

Create a landing-page-style methodology page following the exact architecture established by the homepage: server `page.tsx` with client section components using framer-motion animations, the same dark theme, grid system, and typography.

### Content Scope

High-level marketing overview of the scoring methodology. Explains the approach at a conceptual level (deterministic scoring, factor-based, no human bias) without exposing internal formula details.

### File Structure

```
web/src/app/methodology/
  page.tsx                          # Server component (metadata + layout)
web/src/components/methodology/
  index.ts                          # Barrel export
  sections/
    methodology-hero.tsx            # Page header
    pipeline-section.tsx            # 4-stage pipeline overview
    factor-section.tsx              # Scoring factors grid
    transparency-section.tsx        # Determinism commitment
    methodology-cta.tsx             # CTA + footer
```

### Page Sections

**MethodologyHero** — Title ("How Margin scores equities"), subtitle explaining the deterministic approach. Same layout as landing HeroSection without CTA buttons. Uses `whileInView` fade-in.

**PipelineSection** — Visual 4-stage pipeline (Market Data, Risk Modeling, Allocation Engine, Decision Clarity) with descriptive text. Responsive: horizontal with arrows on desktop, 2x2 grid on tablet, vertical stack on mobile. Reuses the icon/layout pattern from `EngineDiagram`.

**FactorSection** — Grid of 5 scoring factors (Value, Momentum, Quality, Growth, Stability) with 1-sentence descriptions. Uses `CapabilityBlock`-style cards with staggered motion entrance.

**TransparencySection** — Short section on determinism: same inputs produce same outputs, no narrative, no discretion. Two-column layout with text left, visual element right.

**MethodologyCTA** — CTA ("Explore the Engine" button to /dashboard) + footer with copyright and nav links. Mirrors `FinalCTA` pattern.

### Navigation & Metadata

- `NavMinimal` (fixed nav) works on all pages — no changes needed.
- Page metadata: `title: "Methodology | Margin Invest"`, appropriate description.
- No `next.config.ts` changes — standard App Router route resolution.

### Design Constraints

- No new dependencies (no MDX, no `@next/mdx`)
- No changes to `next.config.ts`
- No dynamic content from engine package
- No sidebar/TOC (marketing page, not docs)
- Reuses existing design tokens, grid system, animation patterns
- All section components are `"use client"` for framer-motion

### Verification

- Route loads at `/methodology` without 404
- No hydration errors
- Metadata renders correctly (title, description)
- Navigation links from landing page resolve correctly
- `next build` completes without warnings
- Responsive across mobile/tablet/desktop breakpoints
