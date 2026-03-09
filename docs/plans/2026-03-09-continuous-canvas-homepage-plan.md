# Continuous Canvas Homepage Implementation Plan

**Goal:** Transform the Margin Invest homepage from stacked sections into a single cinematic scroll experience with GSAP ScrollSmoother, scroll-driven scene transitions, and live data integration.

**Architecture:** Create a ScrollCanvas wrapper that provides ScrollSmoother + three cross-cutting systems (gradient breathing, grid continuity, noise). Modify each existing landing component to become a "scene" within the canvas — adding scroll-linked animations, pinning, and transition choreography. No components deleted, all modified in place.

**Tech Stack:** Next.js 16, React 19, Tailwind v4, GSAP 3.14 (ScrollTrigger + ScrollSmoother), Vitest

**Ordering:** Task 1 (ScrollCanvas foundation) must come first. Tasks 2-6 (scenes) are sequential because each scene's scroll range depends on the previous. Task 7 (mobile fallback) comes last.

---

### Task 1: ScrollCanvas Foundation — Wrapper + Cross-Cutting Systems

**Context:** The entire page needs a ScrollSmoother wrapper and three persistent background systems: gradient breathing, grid overlay continuity, and noise texture. This is the foundation everything else builds on.

**Files:**
- Create: `web/src/components/landing/scroll-canvas.tsx`
- Create: `web/src/components/landing/__tests__/scroll-canvas.test.tsx`
- Modify: `web/src/components/landing/homepage-client.tsx`

**Steps:**

1. Write test for ScrollCanvas: renders children, renders gradient layer, renders grid layer, renders noise layer.
2. Run test — should fail (module not found).
3. Implement ScrollCanvas:
   - "use client" component that wraps children in a ScrollSmoother-compatible DOM structure
   - Three persistent layers (gradient, grid, noise) as absolutely-positioned divs behind content
   - Dynamic import of GSAP + ScrollTrigger + ScrollSmoother in useEffect
   - ScrollSmoother config: `smooth: 1.2, effects: true, normalizeScroll: true`
   - Gradient breathing: one div with radial-gradient, GSAP timeline scrubbed by scroll position (emerald glow position/opacity shifts across 0-620vh)
   - Grid overlay: one div with CSS grid background, GSAP tweens backgroundSize (64px→48px→64px) and opacity (0.04→0.04→0.01→0.02) across scroll
   - Noise: existing noise.svg overlay at constant opacity 0.4
   - Export `useScrollTimeline` context hook so child scenes can register their own ScrollTrigger instances after ScrollSmoother initializes
   - Cleanup: kill ScrollSmoother and all ScrollTriggers on unmount
4. Run test — should pass.
5. Integrate into homepage-client.tsx: wrap all sections in `<ScrollCanvas>`. The outer div gains `id="smooth-wrapper"` and an inner `id="smooth-content"` div (required by ScrollSmoother). Pass `data` through so child components still receive their props.
6. Run: `cd web && npx vitest run`
7. Commit: `feat(web): add ScrollCanvas foundation with ScrollSmoother and cross-cutting systems`

**Important details:**
- ScrollSmoother requires a specific DOM structure: `#smooth-wrapper > #smooth-content > [page content]`
- GSAP must be dynamically imported (SSR-safe). Use the same `async function animate()` pattern as existing hero-section.tsx (line 20-43)
- The gradient div uses inline style for the radial-gradient. GSAP animates CSS custom properties (`--glow-x`, `--glow-y`, `--glow-color`, `--glow-opacity`) that the gradient references
- Grid div uses inline style for backgroundImage (linear-gradient grid lines) and backgroundSize. GSAP animates backgroundSize and opacity directly

---

### Task 2: Scene 1 — The Indictment (Hero Rewrite)

**Context:** The hero section transforms from "Discipline. Engineered." + search on load to a two-phase scroll reveal: the indictment number appears first, then the brand + search emerge as you scroll.

**Files:**
- Modify: `web/src/components/landing/hero-section.tsx` (119 lines)
- Modify: `web/src/components/landing/types.ts` (add `total_universe` and `surviving_count` to HomepageData)
- Modify: `web/src/app/page.tsx` (pass universe data)
- Modify: `web/src/components/landing/homepage-client.tsx` (pass universe data to HeroSection)

**Steps:**

1. Update `HomepageData` interface in types.ts: add `total_universe: number` (default 3056) and `surviving_count: number` (default 0). Update `getHomepageData()` in page.tsx to populate from `data.universe?.size` and `data.universe?.surviving ?? data.picks.length`.
2. Rewrite hero-section.tsx:
   - Remove existing GSAP stagger animation (lines 15-51)
   - Phase 1 (on load, 400ms delay): show indictment number
     - Compute `eliminationPct` from `Math.round((1 - survivingCount / totalUniverse) * 100)`
     - Render `"{eliminationPct}% eliminated."` in Geist Mono, centered, font-size `clamp(48px, 8vw, 96px)`
     - Below: `"{totalUniverse.toLocaleString()} US equities scored. {survivingCount} survived."` in text-secondary
     - Fallback: if `totalUniverse` is 0, show "3,056" and "—" for surviving (cached/default)
   - Phase 2 (scroll-driven, 0-30vh): GSAP ScrollTrigger timeline
     - Indictment text: opacity 1→0, scale 1→0.97
     - Brand text ("Discipline." / "Engineered."): y 40→0, opacity 0→1 (Instrument Serif display)
   - Phase 3 (at ~80vh): subtext + HeroSearch fade in (opacity 0→1)
   - Subtle scroll indicator at bottom: thin line, animate opacity pulse
   - Keep existing noise overlay and grid overlay divs (they're now controlled by ScrollCanvas, remove from hero)
   - Keep `minHeight: "100svh"` — hero is still a full viewport scene
   - Remove the radial-gradient background inline style (now handled by ScrollCanvas gradient breathing)
3. Update homepage-client.tsx to pass `totalUniverse` and `survivingCount` to HeroSection from `data`.
4. Run: `cd web && npx vitest run`
5. Commit: `feat(web): rewrite hero as indictment scene with scroll-driven brand reveal`

**Important details:**
- The HeroSearch component (294 lines) is NOT modified — it's reused as-is, just faded in later
- The hero's background overlays (noise, grid) are removed from hero-section.tsx because ScrollCanvas now provides them globally
- The `data-hero-headline`, `data-hero-subtext`, `data-hero-ctas` attributes are replaced with new refs for the indictment/brand/search phases

---

### Task 3: Scene 2 — The Authority Bridge

**Context:** The static AuthorityStrip becomes a scroll-driven transition that bridges hero into evidence. Three data points float in, pin, then the grid morphs into the evidence panel.

**Files:**
- Modify: `web/src/components/landing/authority-strip.tsx` (42 lines — full rewrite)

**Steps:**

1. Rewrite authority-strip.tsx as a scroll-driven scene:
   - "use client" (needs GSAP)
   - Replace the static 3-column grid with three inline data points on a horizontal rule
   - Three items: "SEC EDGAR filings", "11 GICS sectors", "Scored daily" — distilled from the current COLUMNS data (lines 1-14)
   - Each: `font-mono text-xs uppercase tracking-[0.2em] text-text-tertiary`
   - Wrap in a section with `min-height: 50vh` (this scene covers 100vh-150vh of scroll)
   - GSAP ScrollTrigger timeline (scrub: true):
     - 100vh-120vh: three data points float in from edges with 80ms stagger (x: -30→0, opacity: 0→1 for left/center, x: 30→0 for right)
     - 120vh-150vh: data points pin and hold position
   - Remove `border-y border-border-subtle` — no hard section border (Continuous Canvas)
   - Remove the "Data Sources" / "Coverage" / "Engine" group labels — just the three key facts
2. Run: `cd web && npx vitest run`
3. Commit: `feat(web): rewrite authority strip as scroll-driven bridge scene`

**Important details:**
- The pinning of data points during 120-150vh creates the visual hold while the background gradient migrates (handled by ScrollCanvas)
- The section element needs appropriate height to give ScrollTrigger enough scroll travel

---

### Task 4: Scene 3 — The Evidence Machine (Pinned Sequential Reveal)

**Context:** The evidence section becomes a pinned panel where scrolling drives sequential column reveals. This is the most complex scene — ~12 GSAP tweens over 200vh of scroll.

**Files:**
- Modify: `web/src/components/landing/evidence-section.tsx` (109 lines — substantial rewrite)
- Modify: `web/src/components/landing/proof-selectivity-funnel.tsx` (add animation-ready props)
- Modify: `web/src/components/landing/proof-sector-chart.tsx` (add animation-ready props)
- Modify: `web/src/components/landing/proof-heatmap.tsx` (add animation-ready props)

**Steps:**

1. Rewrite evidence-section.tsx scroll animation:
   - Remove existing simple ScrollTrigger (lines 17-52) that just fades the panel in
   - Create a multi-phase ScrollTrigger timeline with `pin: true`:
     - **Container assembly (0-10% of timeline):** Panel opacity 0→1, border draws in (clipPath or opacity). Header text ("SYSTEM OUTPUT — Current Scoring Cycle") types character-by-character using GSAP's `text` plugin or a stagger on individual chars
     - **Column 1 — Funnel (10-40%):** Left column opacity 0→1, ProofSelectivityFunnel triggers its internal animation. Other two columns stay at opacity 0.
     - **Divider 1 (40-42%):** Vertical divider line between col 1 and 2 draws (scaleY: 0→1)
     - **Column 2 — Sectors (42-70%):** Center column fades in, ProofSectorChart triggers. Column 1 dims to opacity 0.7.
     - **Divider 2 (70-72%):** Second vertical divider draws
     - **Column 3 — Heatmap (72-95%):** Right column fades in, ProofHeatmap triggers.
     - **Hold (95-100%):** All columns visible, 20vh of scroll with no animation change — absorption time
   - The pin duration should cover ~200vh of scroll
   - Keep the methodology CTA footer at the bottom of the panel (unpins with the panel)
2. Add `animateIn` boolean prop to ProofSelectivityFunnel, ProofSectorChart, ProofHeatmap. When false, content is hidden (opacity 0). When true, each component runs its own internal reveal animation (bar widths, chart segments, heatmap cells). The parent timeline sets these via refs or state.
3. Run: `cd web && npx vitest run`
4. Commit: `feat(web): rewrite evidence section as pinned sequential machine reveal`

**Important details:**
- GSAP ScrollTrigger `pin: true` works with ScrollSmoother — the pinned element stays fixed while scroll progress drives the timeline
- The "typing" header effect can use a simple GSAP stagger on a span-per-character approach, or a clipPath reveal. Keep it simple — don't import a typewriter library.
- The three proof child components need to NOT animate on mount (current behavior) and instead wait for the parent to trigger them. Add `autoAnimate={false}` prop with default `true` for backward compat.
- The timeline percentages map to scroll vh: 10% of 200vh = 20vh of scroll per phase

---

### Task 5: Scene 4 — The Offer (Pricing Scroll Reveal)

**Context:** Pricing transforms from a static 3-column grid into a scroll-driven sequence: a single statement appears, then splits into three cards, then features type in.

**Files:**
- Modify: `web/src/components/landing/pricing-section.tsx` (90 lines — substantial rewrite)
- Modify: `web/src/components/landing/pricing-tier-card.tsx` (add animation props)

**Steps:**

1. Rewrite pricing-section.tsx:
   - Phase 1 (350-380vh equivalent — first 20% of scene): the headline "Start free. Full access from $19/month." appears alone, centered, in Instrument Serif `clamp(36px, 5vw, 48px)`. Subtitle below. Full-viewport moment. Cards are not visible yet.
   - Phase 2 (380-420vh — 20-50%): ScrollTrigger timeline
     - Headline fades slightly (opacity 1→0.3) and translates up
     - Three PricingTierCard components animate from a central position outward:
       - Scout: x 0→-100%, opacity 0→1
       - Analyst: y 0→0, opacity 0→1, elevate with shadow
       - Portfolio: x 0→100%, opacity 0→1
     - 100ms stagger between cards
   - Phase 3 (420-470vh — 50-85%): Cards pin. Features fill in.
     - Each feature line in each card appears sequentially as you scroll
     - Green checkmark pops: scale 0→1, ease-out-back, 100ms
     - CTA buttons fade in last
   - Phase 4 (470-500vh — 85-100%): Unpin. Bottom text ("No credit card required...") fades in.
   - Keep `tiers` array data (lines 5-49) — no content changes
   - Replace the `linear-gradient` background with a transparent section (background is handled by ScrollCanvas gradient breathing warming at this scroll position)
2. Add `visible` and `revealFeatures` props to PricingTierCard. When `visible` is false, card is invisible. When `revealFeatures` is false, features are hidden. Parent controls these via the scroll timeline.
3. Run: `cd web && npx vitest run`
4. Commit: `feat(web): rewrite pricing as scroll-driven statement-to-cards reveal`

**Important details:**
- The "split" animation is the signature moment of this scene. The three cards emerge from the center — don't just fade them in from below.
- The feature line-by-line typing effect should use GSAP stagger on the feature list items within each card. Each feature is a separate element.
- Pricing section no longer has its own background gradient — the ScrollCanvas gradient breathing handles the warm shift at this scroll position.
- The pin should cover roughly 120vh of scroll (scenes overlap slightly for the transition in).

---

### Task 6: Scene 5 + 6 — FAQ + Footer (Scroll-Staggered Arrival)

**Context:** FAQ questions arrive one at a time via scroll. The final CTA ("Score your first position.") with a search box closes the loop. Footer is a simple fade-in utility section.

**Files:**
- Modify: `web/src/components/landing/faq-section.tsx` (95 lines)
- Modify: `web/src/components/landing/footer-section.tsx` (89 lines)

**Steps:**

1. Modify faq-section.tsx:
   - Add GSAP ScrollTrigger for the section
   - "COMMON QUESTIONS" label: fade in when section enters viewport (opacity 0→1, y 20→0)
   - Each FaqItem: stagger reveal via ScrollTrigger `batch` or individual triggers
     - Each question fades in (opacity 0→1, y 12→0) as it enters the scroll viewport
     - 80ms stagger feel (use ScrollTrigger start offsets or batch stagger)
     - Accordion click-to-expand still works normally (interactive, not scroll-driven)
   - After the last FAQ item, add a new closing CTA block:
     - "Score your first position." in Instrument Serif, centered, `text-2xl md:text-3xl`
     - Below: render `<HeroSearch />` component (import from `./hero-search`) — same search box as the hero, closing the loop
     - The CTA block fades in as the last scroll element
   - Keep existing FAQ_ITEMS array and FaqItem component structure — only add scroll-driven entrance animations
2. Modify footer-section.tsx:
   - Add a GSAP ScrollTrigger fade-in for the entire footer (opacity 0→1, once: true, start: "top 90%")
   - Add a thin `<hr>` above the footer content with `border-border-subtle` — the only hard divider on the page
   - Remove the "Scoring 3,056 US equities daily" text if it exists (already shown in pricing)
   - Keep all existing links and structure
3. Run: `cd web && npx vitest run`
4. Commit: `feat(web): add scroll-staggered FAQ reveals and closing CTA with search`

**Important details:**
- The HeroSearch import in faq-section.tsx creates a circular-ish dependency concern — both hero-section and faq-section import from `./hero-search`. This is fine in Next.js, just note it.
- FAQ items use `"use client"` already (useState for accordion). The GSAP additions are compatible.
- The footer fade-in is intentionally simple — one tween. The footer is utility, not a performance.

---

### Task 7: Mobile Fallback + Polish

**Context:** ScrollSmoother should be disabled on mobile for performance. Scenes should still look good but with simpler animations. This task also handles final testing and cleanup.

**Files:**
- Modify: `web/src/components/landing/scroll-canvas.tsx` (add mobile detection)
- Modify: `web/src/components/landing/hero-section.tsx` (mobile fallback)
- Modify: `web/src/components/landing/evidence-section.tsx` (mobile fallback)
- Modify: `web/src/components/landing/pricing-section.tsx` (mobile fallback)
- Create: `web/src/hooks/use-media-query.ts` (if not exists)

**Steps:**

1. Create or verify `use-media-query.ts` hook: returns boolean for a CSS media query match. Used to detect `(max-width: 768px)`.
2. In scroll-canvas.tsx: if mobile, skip ScrollSmoother initialization entirely. Still render the gradient/grid/noise layers but with static (non-scroll-driven) values. Export an `isSmoothScrolling` flag from context so child scenes can check.
3. In each scene component (hero, evidence, pricing, faq): if `isSmoothScrolling` is false, fall back to simpler animations:
   - Hero: show both indictment and brand simultaneously (no scroll phasing). Simple fade-in on load.
   - Evidence: show all three columns at once with a simple viewport-enter fade-in (similar to current behavior)
   - Pricing: show all three cards immediately, no split animation. Simple viewport-enter fade-in.
   - FAQ: all questions visible immediately, no scroll stagger. Simple section fade-in.
4. Test on mobile viewport: `cd web && npx vitest run` (existing tests should pass since they render without ScrollSmoother)
5. Final full test suite: `cd web && npx vitest run`
6. Commit: `refactor(web): add mobile fallback for scroll animations, disable ScrollSmoother on mobile`

**Important details:**
- ScrollSmoother's `normalizeScroll: true` can cause issues on iOS Safari. The mobile fallback avoids this entirely.
- The `isSmoothScrolling` context flag is the clean way to let each scene decide its own fallback behavior without prop drilling.
- Tests run in jsdom which has no GSAP — all scroll animations are inherently skipped in tests. The fallback logic ensures the static rendering path works.

---

## Task Summary

| Task | Description | Depends on |
|------|-------------|------------|
| 1 | ScrollCanvas foundation (ScrollSmoother + gradient/grid/noise) | - |
| 2 | Scene 1: Hero indictment rewrite | Task 1 |
| 3 | Scene 2: Authority bridge rewrite | Task 1 |
| 4 | Scene 3: Evidence machine pinned reveal | Tasks 1, 3 |
| 5 | Scene 4: Pricing scroll reveal | Tasks 1, 4 |
| 6 | Scene 5+6: FAQ stagger + Footer fade | Tasks 1, 5 |
| 7 | Mobile fallback + polish | Tasks 1-6 |

**All tasks are sequential** — each scene's scroll range depends on the previous scene's height and pin duration.

**Test command:** `cd web && npx vitest run`
**Lint command:** `cd web && npx eslint --fix .`
