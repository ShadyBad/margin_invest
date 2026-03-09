# Continuous Canvas Homepage Redesign

**Date:** 2026-03-09
**Status:** Approved

## Vision

Reimagine the Margin Invest homepage as a single cinematic scroll experience — "The Continuous Canvas." The page is not sections stacked on a screen; it is one continuous flow where backgrounds morph, elements parallax, and scenes transition through scroll-driven choreography.

**Creative Direction — Three Voices:**

- **Jony Ive:** Obsessive reduction. Every element justified. Generous whitespace. The confidence to leave things out.
- **Alex Hormozi:** Direct, high-conviction narrative. Value-first framing. The visitor knows within 3 seconds what this does and why it matters. The page builds an argument, not a brochure.
- **Jon Contino:** Type as identity. Bold, industrial, unapologetic. Monospace data labels and serif headlines create a broadsheet manifesto energy.

**Narrative Structure:** Indictment → Machine → Proof → Offer → Resolve

**Emotional Arc:**

| Scene | Emotion | Mechanism |
|-------|---------|-----------|
| 1. The Indictment | Confrontation → curiosity | Massive data-point demands attention |
| 2. The Authority Bridge | Quiet credibility | Raw inputs, no adjectives |
| 3. The Evidence Machine | Awe → trust | Watch the system work with live data |
| 4. The Offer | Clarity → relief | One statement splits into three tiers |
| 5. The Questions | Reassurance → resolve | Objections answered, CTA closes the loop |
| 6. The Footer | — | Utility exit, the page already did its job |

**Scope:** Homepage only (first phase). The Continuous Canvas design language will extend to all other pages in subsequent phases.

---

## Technical Foundation

### Stack

- **GSAP ScrollTrigger + ScrollSmoother** — scroll-linked animations and buttery smooth scroll interpolation (~25KB gzipped, already using GSAP)
- **Next.js 16 / React 19 / Tailwind v4** — existing stack, no changes
- **Dynamic imports** — GSAP loaded client-side only, same pattern as current hero/evidence animations

### ScrollSmoother Configuration

The entire page wrapped in a ScrollSmoother instance:

```
smooth: 1.2          // interpolation factor (1 = none, 2 = heavy)
effects: true         // enables data-speed parallax attributes
normalizeScroll: true // prevents mobile address bar jank
```

Hero search, FAQ accordion, and all interactive elements remain immediately responsive — ScrollSmoother does not interfere with form inputs or click events. Pinned sections use ScrollTrigger `pin: true` which integrates natively.

### Three Cross-Cutting Systems

**1. Background Gradient Breathing**

One full-viewport element behind all content. A single GSAP timeline scrubbed by scroll position animates a radial gradient's position, color, and opacity:

- 0-150vh: Pure dark `#0A0F0D` with faint emerald radial glow near hero center
- 150-350vh: Emerald glow migrates center-right (evidence panel region)
- 350-500vh: Warm shift — `--color-accent-warm-muted` blends in through pricing
- 500-620vh: Cools back to pure dark

**2. Grid Overlay Continuity**

The background grid persists through the entire page but transforms with scroll:

- Hero: Full opacity (0.04), 64px spacing
- Evidence: Tightens to 48px — lines become the panel's visual structure
- Pricing: Fades to near-invisible (0.01) — warm section feels open
- FAQ/Footer: Returns at 0.02 — subtle system presence

One DOM element, scroll-driven opacity and backgroundSize tweens.

**3. Noise Texture**

Existing `noise.svg` overlay persists at constant opacity (0.4) across the entire page. No scroll interaction — it's a static texture layer.

---

## Scene 1: The Indictment (0vh - 100vh)

### On Load (400ms delay)

Nearly empty dark viewport. Grid overlay visible but faint. After 400ms, content appears:

- **"94% eliminated."** — Geist Mono, centered, filling ~60% viewport width. This is the hook.
- Below: *"3,056 US equities scored. 178 survived."* — Inter Tight, text-secondary, single line.
- Numbers are **live from the API**. Real universe count, real survival count. Elimination percentage computed. Fallback: last-known cached values.

### Scroll Behavior (0-30vh scroll progress)

- "94% eliminated." fades and scales down (opacity 1→0, scale 1→0.97)
- Behind it, "Discipline." and "Engineered." rise from below in Instrument Serif display font — the brand reveal emerges from the data
- Grid overlay tightens (64px → 48px) — a "focusing" sensation

### At Rest (~80vh)

- "Discipline. Engineered." is the dominant element
- Subtext and search box fade in below
- Subtle scroll indicator (thin animated line) hints at more content

### Design Rationale

- Hormozi: First thing you read is a confrontation. 94% didn't make it.
- Contino: Monospace number as brand mark. Typography IS the design.
- Ive: Near-empty viewport. One idea. Maximum confidence.

---

## Scene 2: The Authority Bridge (100vh - 150vh)

### Scroll Behavior (100vh-120vh)

- Hero content (headline + search) stays pinned, fades to 20% opacity — becomes ghost background
- Three data points float in from edges, staggered 80ms:
  - **"SEC EDGAR filings"**
  - **"11 GICS sectors"**
  - **"Scored daily"**
- Each: mono, uppercase, tracking-wide, text-tertiary
- Arranged on a single faint horizontal rule — ticker-tape presentation

### Scroll Behavior (120vh-150vh)

- Three data points pin and hold
- Background emerald gradient migrates downward
- Grid overlay morphs from 48px hero grid into the evidence panel's border structure — lines become the container. No hard section break.

### Design Rationale

- Ive: Three facts. No adjectives.
- Hormozi: Raw inputs, not boasts. "This is what goes in."
- Contino: Ticker-tape. Industrial. Broadsheet.

---

## Scene 3: The Evidence Machine (150vh - 350vh)

This is the centerpiece — the pinned, sequentially-revealed system output. The viewer watches the machine work.

### 150vh-170vh: Container Assembly

- Grid lines from Scene 2 converge into a bordered terminal panel
- "SYSTEM OUTPUT — Current Scoring Cycle" types in character-by-character (mono, uppercase, tracking-wide)
- Panel pins to viewport. Scrolling now drives content inside, not the panel itself.

### 170vh-230vh: Column 1 — Selectivity Funnel

- Left column activates. "SELECTIVITY FUNNEL" label fades in.
- Funnel bars animate sequentially top to bottom — each bar's width animates from 100% to real proportion
- Live API numbers count up (3,056 → 1,847 → 612 → 178) with each bar
- Other two columns remain empty/dark — focuses attention on one idea

### 230vh-290vh: Column 2 — Sector Breakdown

- Vertical divider line draws itself between columns 1 and 2
- Column 2 activates: "SECTOR BREAKDOWN" label fades in
- Sector data animates in with 80ms stagger
- Column 1 dims slightly (opacity 0.7) — "done," attention shifts right
- Live data: real sector distribution from candidates

### 290vh-350vh: Column 3 — Factor Correlation

- Second divider draws itself
- Column 3 activates: "FACTOR CORRELATION" label fades in
- Heatmap cells fill row by row — each cell's background transitions from transparent to its correlation color
- All three columns now fully visible
- Hold for 20vh of scroll with no change — let the viewer absorb

### 350vh: Pin Release

- Panel unpins and scrolls naturally
- Methodology CTA visible at bottom: "Structure replaces intuition with evidence. See full methodology."

### Design Rationale

- Hormozi: Show them the machine. Don't explain — demonstrate. Sequential reveal creates "this is thorough."
- Contino: Terminal aesthetic. Monospace headers. Printed from a machine, not designed by a marketer.
- Ive: One column at a time. Empty columns create anticipation. The 20vh pause respects absorption time.

### Technical Note

Most GSAP-intensive scene: ScrollTrigger timeline with pinning and ~12 tweens. 200vh of scroll progress provides unhurried animation pace.

---

## Scene 4: The Offer (350vh - 500vh)

### 350vh-380vh: Transition

- Background gradient warms (dark → `--color-accent-warm-muted` blend)
- Single line in Instrument Serif, centered, large (clamp 36px-48px): **"Start free. Full access from $19/month."**
- Below: "Upgrade when the data changes how you think." in text-secondary
- Full viewport. The statement breathes alone.

### 380vh-420vh: The Split

- "$19" in headline briefly pulses (scale 1→1.02→1 with glow)
- The statement separates horizontally into three cards:
  - Scout materializes, slides left
  - Analyst stays center, elevates with shadow (highlighted tier)
  - Portfolio materializes, slides right
- Cards fade in with 100ms stagger
- Analyst card border shifts to `--color-accent-medium`

### 420vh-470vh: Details Fill In

- Cards pinned. Scroll drives content within.
- Tier names and prices visible immediately
- Feature lists type in line by line per scroll — green checkmarks pop (scale 0→1, 100ms, ease-out-back)
- CTA buttons fade in last
- "Scoring 3,056 US equities daily" mono line appears below in accent

### 470vh-500vh: Release

- Cards unpin
- "No credit card required. 30-day money-back guarantee." + "Need API access? Contact us."
- Natural scroll resumes

### Design Rationale

- Hormozi: Lead with the price. Don't hide it. Features type in line-by-line — each feels earned, not listed.
- Ive: One statement first. Full viewport. Then the reveal. Restraint before expansion.
- Contino: Cards splitting from a single typographic statement is theatrical. Layout tells a story.

---

## Scene 5: The Questions (500vh - 580vh)

### 500vh-520vh: Transition

- Background cools back to pure `#0A0F0D`
- Mono label drifts in: **"COMMON QUESTIONS"** — same terminal voice

### 520vh-570vh: Accordion

- Questions appear one at a time as you scroll — staggered 80ms
- Interaction is standard click-to-expand (interactive element, not scroll-driven)
- Arrival is choreographed through scroll progress
- Max-width 3xl — generous side margins, centered editorial column

### 570vh-580vh: The Final Statement

- Below last FAQ, one line in Instrument Serif, centered: **"Score your first position."**
- Below: compact inline search field (reuses HeroSearch component) — closes the loop
- The page started with "94% eliminated" and ends with "do something about it"

### Design Rationale

- Hormozi: Page ends with a CTA, not a footer. Specific instruction.
- Ive: FAQ is quiet. Final CTA is one line with a search box. Nothing competing.
- Contino: Centered text column, repeating mono headers — one design language, first scroll to last.

---

## Scene 6: The Footer (580vh - 620vh)

### Content

- Thin horizontal rule fades in — the only hard divider on the page
- Footer content fades as a single unit
- "Margin Invest" wordmark left, Product and Company link columns right
- Tagline: "Deterministic scoring engine" in mono, text-tertiary
- Links: text-secondary → text-primary on hover, duration-100
- Copyright + system tagline bottom

### What's Removed

- No repeated "Scoring 3,056 US equities daily" (shown in pricing)
- No decorative elements. The footer is utility.

### Design Rationale

- Ive: Know when to stop designing. The footer is not a moment.
- Hormozi: Everything above the footer pushed toward conversion.
- Contino: Mono wordmark and system tagline maintain the industrial voice through the last pixel.

---

## Live Data Integration

The homepage must feel like a live system, not a brochure:

| Data Point | Source | Fallback |
|------------|--------|----------|
| Universe count (3,056) | `/api/v1/dashboard` → `universe.total` | Last-known cached value |
| Survival count (178) | `/api/v1/dashboard` → `picks.length` or `universe.surviving` | Last-known cached value |
| Elimination % | Computed from above | Last-known cached value |
| Selectivity funnel stages | `/api/v1/dashboard` → `universe` fields | Cached or placeholder bars |
| Sector distribution | `/api/v1/dashboard` → `candidates` grouped by sector | "Scoring in progress" message |
| Factor correlation | Hardcoded (changes infrequently) | Always available |
| Top candidates (search) | `/api/v1/dashboard` → `eligible_picks[0:5]` | Search still works via API |

Server-side fetch on page load (existing `serverFetch` pattern). Client components receive data as props. No client-side polling — data refreshes on page load.

---

## Animation Budget

Total GSAP-driven animations across the page:

| Scene | Pinned | Tweens | Scroll Range |
|-------|--------|--------|-------------|
| 1. Indictment | No | 5 (fade, scale, rise, grid, indicator) | 0-100vh |
| 2. Authority Bridge | Yes (50vh) | 4 (float-in x3, fade hero) | 100-150vh |
| 3. Evidence Machine | Yes (200vh) | 12 (container, header, 3x column reveals, dividers, dimming, hold) | 150-350vh |
| 4. The Offer | Yes (90vh) | 10 (statement, pulse, split x3, features, CTAs, unpin) | 350-500vh |
| 5. Questions | No | 3 (label, stagger questions, final CTA) | 500-580vh |
| 6. Footer | No | 1 (fade in) | 580-620vh |
| **Cross-cutting** | — | 3 (gradient breathing, grid transform, noise) | 0-620vh |
| **Total** | 3 pins | ~38 tweens | 620vh |

All GSAP loaded via dynamic import. ScrollSmoother + ScrollTrigger + core: ~25KB gzipped.

---

## What Changes From Current

### Components Modified
- `homepage-client.tsx` — ScrollSmoother wrapper, scroll timeline orchestration
- `hero-section.tsx` — Indictment number + brand reveal scroll sequence
- `evidence-section.tsx` — Pinned sequential column reveals
- `pricing-section.tsx` — Statement → split → fill scroll sequence
- `faq-section.tsx` — Scroll-staggered question arrival + final CTA
- `footer-section.tsx` — Minimal changes (fade-in entrance)
- `authority-strip.tsx` — Reimagined as scroll-driven floating data points

### Components Created
- `scroll-canvas.tsx` — ScrollSmoother wrapper + background gradient breathing + grid overlay
- `scroll-scene.tsx` — Reusable wrapper for each scene's ScrollTrigger registration

### Components Removed
- None removed — existing components are modified, not replaced

### Design System Additions
- No new CSS tokens needed — existing duration, easing, and color tokens cover all animations
- May need `--color-grid-line-dense` for the 48px grid variant (or compute inline)

---

## Success Criteria

1. The page feels like one continuous experience, not sections on a screen
2. A first-time visitor scrolls to the bottom (the experience compels completion)
3. The emotional arc lands: confrontation → credibility → awe → clarity → action
4. Live data is woven throughout — the visitor knows this system is running right now
5. Page weight increase < 30KB gzipped (GSAP ScrollSmoother + new animation code)
6. All existing tests continue to pass
7. Mobile experience degrades gracefully — simpler animations, no ScrollSmoother, sections still work as standalone blocks
