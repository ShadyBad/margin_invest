# Digital Horologist Landing Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan one task at a time. Steps use checkbox syntax for tracking.

**Goal:** Rebuild the Margin Invest landing page with the Digital Horologist design system — new fonts, tonal surface hierarchy, no-line rule, streamlined from 12 sections to 5.

**Architecture:** Section rebuild — replace globals.css with new design system, swap fonts in layout.tsx, rebuild each of the 5 surviving sections (Hero, Evidence, Comparison, Pricing, Footer) from scratch, restyle kept visualizations, delete cut sections. Shared scroll utilities (ScrollCanvas, ScrollReveal, CountUp, TextReveal) are kept unchanged.

**Tech Stack:** Next.js 16, React 19, Tailwind v4, GSAP + ScrollTrigger, Recharts, Google Fonts (Newsreader, Space Grotesk, Inter Tight)

**Spec:** `docs/superpowers/specs/2026-04-14-digital-horologist-redesign-design.md`

---

## File Map

### Modified
| File | Responsibility |
|------|---------------|
| `web/src/app/globals.css` | Full design system replacement — surface hierarchy, typography scale, motion, radii |
| `web/src/app/layout.tsx` | Font imports: add Newsreader + Space Grotesk, remove Instrument Serif + Geist Mono |
| `web/src/components/landing/homepage-client.tsx` | New 5-section flow, remove cut section imports |
| `web/src/components/nav/navbar.tsx` | Glassmorphism styling |
| `web/src/components/landing/sections/hero-section.tsx` | Rebuild: absorb authority strip, new headline/stats/layout |
| `web/src/components/landing/sections/evidence-section.tsx` | Rebuild: two blocks (Funnel + Forensic Analysis) |
| `web/src/components/landing/sections/comparison-section.tsx` | Rebuild: tonal rows, no borders, spotlight column |
| `web/src/components/landing/sections/pricing-section.tsx` | Rebuild: "CHOOSE YOUR APERTURE", tonal cards, no bounce |
| `web/src/components/landing/sections/pricing-tier-card.tsx` | Restyle: ghost borders, radial glow hover, no pills |
| `web/src/components/landing/sections/footer-section.tsx` | Rebuild: simplified, no CTA/FAQ, tonal background |
| `web/src/components/landing/visualizations/selectivity-funnel.tsx` | Restyle: tonal stage colors, Space Grotesk labels |
| `web/src/components/landing/index.ts` | Remove cut exports |

### Deleted
| File | Reason |
|------|--------|
| `sections/authority-strip.tsx` | Absorbed into hero |
| `sections/social-proof-section.tsx` | Cut |
| `sections/transparency-strip.tsx` | Cut |
| `sections/pipeline-section.tsx` | Cut |
| `sections/results-showcase-section.tsx` | Cut |
| `sections/faq-section.tsx` | Cut (footer rebuilt without FAQ) |
| `sections/how-it-works-section.tsx` | Cut (not in page flow) |
| `sections/pillars-section.tsx` | Cut (not in page flow) |
| `visualizations/radar-chart.tsx` | Only used in pipeline (deleted) |
| `visualizations/mini-candidate-stack.tsx` | Only used in pipeline (deleted) |
| `visualizations/sparkline.tsx` | Only used in results showcase (deleted) |
| `visualizations/animated-counter.tsx` | Redundant with count-up.tsx |
| `hero-candidate-card.tsx` | Not used by any surviving section |

### Kept Unchanged
- `shared/scroll-canvas.tsx`, `shared/scroll-reveal.tsx`, `shared/count-up.tsx`, `shared/text-reveal.tsx`, `shared/types.ts`
- `hero-search.tsx`, `sections/instrument-panel.tsx`
- `visualizations/sector-bar-chart.tsx`, `visualizations/factor-density-curves.tsx`
- `proof-heatmap.tsx`

---

## Task 1: Design System — globals.css

**Files:**
- Modify: `web/src/app/globals.css`

Foundation layer — every subsequent step depends on these being correct.

- [ ] **Step 1: Replace the `@theme` block (lines 11–113) with the Digital Horologist surface hierarchy**

```css
@theme {
  /* ── Surface Hierarchy (tonal layering, no borders) ── */
  --color-surface: #08160f;
  --color-surface-container-lowest: #0a1c12;
  --color-surface-container-low: #0e2318;
  --color-surface-container: #122a1c;
  --color-surface-container-high: #163220;
  --color-surface-container-highest: #1a3a24;

  /* ── Primary accent — emerald ── */
  --color-primary: #80d8b2;
  --color-primary-container: #1A7A5A;
  --color-on-primary-container: #EDE9E3;

  /* ── Text ── */
  --color-on-surface: #EDE9E3;
  --color-on-surface-variant: #A39E96;
  --color-text-tertiary: #6B6660;

  /* ── Borders — ghost only ── */
  --color-outline-variant: #3f4943;
  --color-ghost-border: rgba(63, 73, 67, 0.15);

  /* ── Surface utilities ── */
  --color-surface-variant: #3f4943;
  --color-surface-tint: #80d8b2;

  /* ── Semantic (unchanged — dashboard use) ── */
  --color-bullish: #22C55E;
  --color-bearish: #D45A5F;
  --color-warning: #D4A843;
  --color-danger: #D45A5F;

  /* ── 5-tier percentile (unchanged) ── */
  --color-percentile-exceptional: #10B981;
  --color-percentile-strong: #1C7A5A;
  --color-percentile-average: #6B7280;
  --color-percentile-below: #D97706;
  --color-percentile-weak: #DC2626;

  /* ── Sector accents (unchanged) ── */
  --color-sector-tech: #6AB0D4;
  --color-sector-healthcare: #50B88E;
  --color-sector-financials: #5A8EC4;
  --color-sector-consumer-disc: #D08868;
  --color-sector-consumer-staples: #B8AA58;
  --color-sector-energy: #D0A440;
  --color-sector-industrials: #9AA0AC;
  --color-sector-materials: #C09070;
  --color-sector-real-estate: #B0A07A;
  --color-sector-utilities: #60B860;
  --color-sector-comms: #AA72C4;

  /* ── Elevation — tonal, not shadow ── */
  --shadow-ambient: 0 0 32px rgba(237, 233, 227, 0.06);

  /* ── Motion ── */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out-smooth: cubic-bezier(0.45, 0, 0.55, 1);
  --duration-micro: 150ms;
  --duration-fast: 100ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;
  --stagger-base: 80ms;
}
```

- [ ] **Step 2: Replace typography scale (lines 116–131)**

```css
/* ── Typography Scale — Digital Horologist ── */
.text-display-lg  { font-family: var(--font-display); font-size: clamp(44px, 7vw, 72px); line-height: 1.05; font-weight: 400; letter-spacing: -0.02em; }
.text-headline-md { font-family: var(--font-display); font-size: clamp(28px, 4vw, 40px); line-height: 1.1; font-weight: 400; letter-spacing: -0.02em; }
.text-title-sm    { font-family: var(--font-sans); font-size: clamp(17px, 1.8vw, 20px); line-height: 1.3; font-weight: 600; }
.text-body-md     { font-family: var(--font-sans); font-size: clamp(16px, 1.2vw, 17px); line-height: 1.6; font-weight: 400; }
.text-label-md    { font-family: var(--font-data); font-size: 14px; line-height: 1.4; font-weight: 500; }
.text-label-sm    { font-family: var(--font-data); font-size: 11px; line-height: 1.2; font-weight: 500; letter-spacing: 0.2em; text-transform: uppercase; }
.text-mono-data   { font-family: var(--font-data); font-size: clamp(24px, 3vw, 32px); line-height: 1.1; font-weight: 700; }
```

- [ ] **Step 3: Update `@theme inline` font mappings (lines 134–138)**

```css
@theme inline {
  --font-sans: var(--font-inter-tight);
  --font-data: var(--font-space-grotesk);
  --font-display: var(--font-newsreader);
  /* ... rest of @theme inline unchanged ... */
}
```

- [ ] **Step 4: Update body styles (lines 175–182)**

```css
body {
  background-color: var(--color-surface);
  color: var(--color-on-surface);
  font-family: var(--font-sans);
  background-image: url('/noise.svg');
  background-repeat: repeat;
  overflow-x: hidden;
}
```

- [ ] **Step 5: Update `.terminal-card` (lines 242–251)**

```css
.terminal-card {
  background: var(--color-surface-container-low);
  border: 1px solid var(--color-ghost-border);
  border-radius: 0.5rem;
  transition: border-color var(--duration-normal) ease, box-shadow var(--duration-normal) ease;
}

.terminal-card:hover {
  border-color: rgba(63, 73, 67, 0.3);
  box-shadow: var(--shadow-ambient);
}
```

- [ ] **Step 6: Update `:root` shadcn compat (lines 276–309)**

```css
:root {
  --radius: 0.5rem;
  --background: var(--color-surface);
  --foreground: var(--color-on-surface);
  --card: var(--color-surface-container-low);
  --card-foreground: var(--color-on-surface);
  --popover: var(--color-surface-container);
  --popover-foreground: var(--color-on-surface);
  --primary: var(--color-on-surface);
  --primary-foreground: var(--color-surface);
  --secondary: var(--color-surface-container);
  --secondary-foreground: var(--color-on-surface);
  --muted: var(--color-surface-container);
  --muted-foreground: var(--color-on-surface-variant);
  --accent: var(--color-primary-container);
  --accent-foreground: var(--color-on-surface);
  --destructive: var(--color-danger);
  --border: var(--color-ghost-border);
  --input: var(--color-ghost-border);
  --ring: var(--color-primary-container);
  --chart-1: var(--color-primary-container);
  --chart-2: var(--color-bullish);
  --chart-3: var(--color-warning);
  --chart-4: #3BA5D0;
  --chart-5: var(--color-bearish);
  --sidebar: var(--color-surface-container-low);
  --sidebar-foreground: var(--color-on-surface);
  --sidebar-primary: var(--color-primary-container);
  --sidebar-primary-foreground: var(--color-on-surface);
  --sidebar-accent: var(--color-surface-container);
  --sidebar-accent-foreground: var(--color-on-surface);
  --sidebar-border: var(--color-ghost-border);
  --sidebar-ring: var(--color-primary-container);
}
```

- [ ] **Step 7: Verify dev server compiles**

Run: `cd web && npx next build --no-lint 2>&1 | head -20`
Expected: No CSS compilation errors.

- [ ] **Step 8: Commit**

```bash
git add web/src/app/globals.css
git commit -m "feat(landing): replace design system with Digital Horologist surface hierarchy"
```

---

## Task 2: Font Imports — layout.tsx

**Files:**
- Modify: `web/src/app/layout.tsx`

- [ ] **Step 1: Replace font imports (line 4)**

Change:
```typescript
import { Inter_Tight, Geist_Mono, Instrument_Serif } from "next/font/google";
```
To:
```typescript
import { Inter_Tight, Newsreader, Space_Grotesk } from "next/font/google";
```

- [ ] **Step 2: Replace font configurations (lines 16–32)**

```typescript
const interTight = Inter_Tight({
  variable: "--font-inter-tight",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  weight: ["400"],
  style: ["normal", "italic"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});
```

- [ ] **Step 3: Update body className (line 67)**

Change:
```typescript
className={`${interTight.variable} ${geistMono.variable} ${instrumentSerif.variable} antialiased text-text-primary`}
```
To:
```typescript
className={`${interTight.variable} ${newsreader.variable} ${spaceGrotesk.variable} antialiased`}
```

- [ ] **Step 4: Update `bg-bg-primary` reference (line 82)**

Change `bg-bg-primary` to `bg-surface`.

- [ ] **Step 5: Update Toaster styles (lines 90–94)**

```typescript
style: {
  background: "var(--color-surface-container-low)",
  border: "1px solid var(--color-ghost-border)",
  color: "var(--color-on-surface)",
},
```

- [ ] **Step 6: Commit**

```bash
git add web/src/app/layout.tsx
git commit -m "feat(landing): swap fonts — Newsreader (display), Space Grotesk (data)"
```

---

## Task 3: Navbar — Glassmorphism

**Files:**
- Modify: `web/src/components/nav/navbar.tsx`

- [ ] **Step 1: Update nav container (line 21)**

Change:
```tsx
<div className="relative flex items-center justify-between bg-bg-elevated border border-border-primary rounded-2xl px-6 py-3 backdrop-blur-md shadow-[0_2px_16px_rgba(0,0,0,0.12)]">
```
To:
```tsx
<div className="relative flex items-center justify-between rounded-xl px-6 py-3 backdrop-blur-[20px]" style={{ background: "rgba(18, 42, 28, 0.7)", border: "1px solid var(--color-ghost-border)" }}>
```

Key: semi-transparent surface-container, ghost border, max `rounded-xl` (0.75rem), blur(20px), no shadow.

- [ ] **Step 2: Commit**

```bash
git add web/src/components/nav/navbar.tsx
git commit -m "feat(nav): glassmorphism navbar — blur(20px), semi-transparent surface"
```

---

## Task 4: Homepage Client — New Section Flow

**Files:**
- Modify: `web/src/components/landing/homepage-client.tsx`

- [ ] **Step 1: Rewrite homepage-client.tsx**

Replace entire file:

```tsx
"use client"

import { HeroSection } from "./sections/hero-section"
import { EvidenceSection } from "./sections/evidence-section"
import { ComparisonSection } from "./sections/comparison-section"
import { PricingSection } from "./sections/pricing-section"
import { FooterSection } from "./sections/footer-section"
import { ScrollCanvas } from "./shared/scroll-canvas"
import type { HomepageData } from "./shared/types"

interface HomepageClientProps {
  data: HomepageData | null
}

export function HomepageClient({ data }: HomepageClientProps) {
  return (
    <ScrollCanvas>
      <HeroSection data={data} />
      <EvidenceSection
        candidates={data?.allPicks ?? []}
        totalUniverse={data?.total_universe}
        eligibleCount={data?.eligible_count}
        totalScored={data?.total_scored}
        survivingCount={data?.surviving_count}
      />
      <ComparisonSection />
      <PricingSection totalUniverse={data?.total_universe} />
      <FooterSection />
    </ScrollCanvas>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/landing/homepage-client.tsx
git commit -m "feat(landing): streamline to 5-section flow"
```

---

## Task 5: Hero Section — Rebuild

**Files:**
- Modify: `web/src/components/landing/sections/hero-section.tsx`

This is the largest single rebuild. The hero absorbs authority strip data and adopts the new headline/typography.

- [ ] **Step 1: Rewrite hero-section.tsx**

Replace entire file. Key changes from current:
- Headline: "DISCIPLINE ENGINEER" (all-caps Newsreader) replaces "Discipline. Engineered."
- Layout: 60/40 split (was 55/45)
- Stats row: 4 metrics (Universe, Scored, Surviving, Last Cycle) with CountUp — absorbed from authority-strip.tsx
- Card animation: scale 0.95→1, no rotation, `expo.out` easing (was `power2.out` with rotation)
- Background gradient uses `--color-primary` (#80d8b2) at 8% opacity (was accent at 18%)
- Grid lines use `--color-surface-variant` at 5% (was `--color-grid-line`)
- Bottom fade targets `--color-surface` (was `--color-bg-primary`)
- `formatRelativeTime()` utility moved in from authority-strip.tsx

```tsx
"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import type { HomepageData } from "../shared/types"
import { HeroSearch } from "../hero-search"
import { InstrumentPanel } from "./instrument-panel"
import { CountUp } from "../shared/count-up"

interface HeroSectionProps {
  data: HomepageData | null
}

function formatRelativeTime(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  if (isNaN(then)) return "\u2014"
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function HeroSection({ data }: HeroSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)
  const noiseRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return
    let cancelled = false
    const cleanups: (() => void)[] = []

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        const section = sectionRef.current
        if (!section) return
        section.querySelectorAll("[data-hero-headline] [data-word]").forEach((el) => {
          const htmlEl = el as HTMLElement
          htmlEl.style.opacity = "1"
          htmlEl.style.transform = "none"
          htmlEl.style.filter = "none"
        })
        const subtext = section.querySelector("[data-hero-subtext]") as HTMLElement | null
        const ctas = section.querySelector("[data-hero-ctas]") as HTMLElement | null
        const card = section.querySelector("[data-hero-card]") as HTMLElement | null
        const stats = section.querySelector("[data-hero-stats]") as HTMLElement | null
        if (subtext) subtext.style.opacity = "1"
        if (ctas) ctas.style.opacity = "1"
        if (card) card.style.opacity = "1"
        if (stats) stats.style.opacity = "1"
        return
      }

      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return
      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)
      const section = sectionRef.current
      if (!section) return

      // Word-by-word headline reveal
      const words = section.querySelectorAll("[data-hero-headline] [data-word]")
      if (words.length > 0) {
        gsap.set(words, { opacity: 0, y: 20, filter: "blur(8px)" })
        gsap.to(words, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.55, stagger: 0.09, delay: 0.1, ease: "power2.out" })
      }

      // Subtext blur-up
      const subtext = section.querySelector("[data-hero-subtext]")
      if (subtext) {
        gsap.set(subtext, { opacity: 0, y: 16, filter: "blur(6px)" })
        gsap.to(subtext, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, delay: 0.45, ease: "power2.out" })
      }

      // Stats row blur-up
      const stats = section.querySelector("[data-hero-stats]")
      if (stats) {
        gsap.set(stats, { opacity: 0, y: 16, filter: "blur(4px)" })
        gsap.to(stats, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, delay: 0.55, ease: "power2.out" })
      }

      // CTAs blur-up
      const ctas = section.querySelector("[data-hero-ctas]")
      if (ctas) {
        gsap.set(ctas, { opacity: 0, y: 16, filter: "blur(4px)" })
        gsap.to(ctas, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, delay: 0.65, ease: "power2.out" })
      }

      // Card: scale + blur, no rotation, expo.out
      const card = section.querySelector("[data-hero-card]")
      if (card) {
        gsap.set(card, { opacity: 0, scale: 0.95, filter: "blur(10px)" })
        gsap.to(card, { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.9, delay: 0.35, ease: "expo.out" })
      }

      // Parallax
      const grid = gridRef.current
      const noise = noiseRef.current
      if (grid) {
        gsap.to(grid, { y: 120, ease: "none", scrollTrigger: { trigger: section, start: "top top", end: "bottom top", scrub: true } })
        cleanups.push(() => ScrollTrigger.getAll().forEach((t) => t.kill()))
      }
      if (noise) {
        gsap.to(noise, { y: 60, ease: "none", scrollTrigger: { trigger: section, start: "top top", end: "bottom top", scrub: true } })
      }
    }

    animate().catch(() => {})
    return () => { cancelled = true; cleanups.forEach((fn) => fn()) }
  }, [])

  const topCandidate = data?.candidates?.[0] ?? null

  return (
    <section id="hero" ref={sectionRef} className="relative flex items-center justify-center overflow-x-clip"
      style={{ minHeight: "80svh", background: "radial-gradient(ellipse 70% 55% at 50% 30%, rgba(128,216,178,0.08) 0%, transparent 60%), var(--color-surface)" }}>
      {/* Noise */}
      <div ref={noiseRef} className="pointer-events-none absolute inset-0"
        style={{ backgroundImage: "url('/noise.svg')", backgroundRepeat: "repeat", opacity: 0.4, willChange: "transform" }} />
      {/* Grid */}
      <div ref={gridRef} className="pointer-events-none absolute inset-0"
        style={{ backgroundImage: "linear-gradient(rgba(63,73,67,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(63,73,67,0.05) 1px, transparent 1px)", backgroundSize: "64px 64px", willChange: "transform" }} />

      <div className="grid grid-cols-1 lg:grid-cols-[60%_40%] gap-10 lg:gap-6 max-w-7xl w-full items-center pt-16 py-24 px-6 relative z-10">
        <div className="flex flex-col justify-center">
          <h1 data-hero-headline className="text-display-lg uppercase mb-6">
            <span className="block" style={{ color: "var(--color-on-surface)" }}>
              <span data-word style={{ display: "inline-block" }}>DISCIPLINE</span>
            </span>
            <span className="block" style={{ color: "var(--color-primary)" }}>
              <span data-word style={{ display: "inline-block" }}>ENGINEER</span>
            </span>
          </h1>

          <p data-hero-subtext className="text-body-md max-w-xl mb-8 leading-relaxed" style={{ color: "var(--color-on-surface-variant)" }}>
            A forensic scoring engine that replaces narrative with structure. {(data?.total_universe ?? 3056).toLocaleString()} US equities filtered to the ones worth your capital.
          </p>

          {/* Stats row — absorbed from Authority Strip */}
          <div data-hero-stats className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-10">
            <div>
              <div className="text-mono-data" style={{ color: "var(--color-on-surface)" }}>
                <CountUp value={data?.total_universe ?? 3056} duration={1.5} start="top 95%" />
              </div>
              <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>UNIVERSE</div>
            </div>
            <div>
              <div className="text-mono-data" style={{ color: "var(--color-on-surface)" }}>
                <CountUp value={data?.total_scored ?? 0} duration={1.5} start="top 95%" />
              </div>
              <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>SCORED</div>
            </div>
            <div>
              <div className="text-mono-data" style={{ color: "var(--color-on-surface)" }}>
                <CountUp value={data?.surviving_count ?? 0} duration={1.5} start="top 95%" />
              </div>
              <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>SURVIVING</div>
            </div>
            <div>
              <div className="text-label-md" style={{ color: "var(--color-on-surface)", fontFamily: "var(--font-data)" }}>
                {data?.last_updated ? formatRelativeTime(data.last_updated) : "\u2014"}
              </div>
              <div className="text-label-sm mt-1" style={{ color: "var(--color-on-surface-variant)" }}>LAST CYCLE</div>
            </div>
          </div>

          <div data-hero-ctas className="max-w-md">
            <HeroSearch />
            <p className="mt-4 text-sm" style={{ color: "var(--color-on-surface-variant)" }}>
              or{" "}
              <Link href="/explore" className="underline underline-offset-2 transition-colors duration-150 hover:text-[var(--color-primary)]"
                style={{ color: "var(--color-on-surface-variant)" }}>
                browse this week&apos;s top picks &rarr;
              </Link>
            </p>
          </div>
        </div>

        <div className="flex items-center justify-center lg:justify-end" data-hero-card>
          <InstrumentPanel candidate={topCandidate} />
        </div>
      </div>

      <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-32"
        style={{ background: "linear-gradient(to bottom, transparent, var(--color-surface))" }} />
    </section>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/landing/sections/hero-section.tsx
git commit -m "feat(landing): rebuild hero — DISCIPLINE ENGINEER headline, absorbed stats row"
```

---

## Task 6: Evidence Section — Rebuild

**Files:**
- Modify: `web/src/components/landing/sections/evidence-section.tsx`

Split into two visual blocks: "THE SELECTION FUNNEL" (full-width) and "FORENSIC ANALYSIS" (3-card grid).

- [ ] **Step 1: Rewrite evidence-section.tsx**

Replace entire file:

```tsx
"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import { SelectivityFunnel } from "../visualizations/selectivity-funnel"
import { SectorBarChart } from "../visualizations/sector-bar-chart"
import { FactorDensityCurves } from "../visualizations/factor-density-curves"
import { ProofHeatmap } from "../proof-heatmap"
import type { CandidateCard } from "../shared/types"

interface EvidenceSectionProps {
  candidates?: CandidateCard[]
  totalUniverse?: number
  eligibleCount?: number
  totalScored?: number
  survivingCount?: number
}

export function EvidenceSection({
  candidates = [],
  totalUniverse = 0,
  eligibleCount = 0,
  totalScored = 0,
  survivingCount = 0,
}: EvidenceSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return
    let cancelled = false
    const cleanups: (() => void)[] = []

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return
      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)
      const el = sectionRef.current
      if (!el) return

      // Funnel block
      const funnelBlock = el.querySelector("[data-funnel-block]")
      if (funnelBlock) {
        gsap.set(funnelBlock, { opacity: 0, y: 24, filter: "blur(6px)" })
        const st = ScrollTrigger.create({ trigger: funnelBlock, start: "top 88%", once: true,
          onEnter: () => { gsap.to(funnelBlock, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, ease: "power2.out" }) },
        })
        cleanups.push(() => st.kill())
      }

      // Forensic cards
      const cards = el.querySelectorAll("[data-forensic-card]")
      if (cards.length > 0) {
        gsap.set(cards, { opacity: 0, y: 24, filter: "blur(6px)" })
        const st = ScrollTrigger.create({ trigger: cards[0], start: "top 88%", once: true,
          onEnter: () => { gsap.to(cards, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.6, stagger: 0.1, ease: "power2.out" }) },
        })
        cleanups.push(() => st.kill())
      }
    }

    animate().catch(() => {})
    return () => { cancelled = true; cleanups.forEach((fn) => fn()) }
  }, [])

  return (
    <section id="evidence" ref={sectionRef} className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Block A: THE SELECTION FUNNEL */}
        <div data-funnel-block className="mb-20">
          <h2 className="text-headline-md uppercase mb-10" style={{ color: "var(--color-on-surface)" }}>
            The Selection Funnel
          </h2>
          <div className="p-8 rounded-lg" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
            <SelectivityFunnel universeCount={totalUniverse} eligibleCount={eligibleCount} scoredCount={totalScored} survivingCount={survivingCount} />
          </div>
          <p className="text-label-md mt-6 text-center" style={{ color: "var(--color-on-surface-variant)" }}>
            {totalUniverse.toLocaleString()} &rarr; {eligibleCount.toLocaleString()} &rarr; {totalScored.toLocaleString()} &rarr; {survivingCount.toLocaleString()}
          </p>
        </div>

        {/* Block B: FORENSIC ANALYSIS */}
        <div>
          <h2 className="text-headline-md uppercase mb-10" style={{ color: "var(--color-on-surface)" }}>
            Forensic Analysis
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div data-forensic-card className="p-6 rounded-lg" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
              <div className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>SECTOR BREAKDOWN</div>
              <SectorBarChart candidates={candidates} />
            </div>
            <div data-forensic-card className="p-6 rounded-lg" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
              <div className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>FACTOR CORRELATION</div>
              <ProofHeatmap candidates={candidates} />
            </div>
            <div data-forensic-card className="p-6 rounded-lg" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
              <div className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>FACTOR DISTRIBUTIONS</div>
              <FactorDensityCurves candidates={candidates} />
            </div>
          </div>
          <div className="mt-8 text-center">
            <Link href="/methodology" className="text-sm transition-colors duration-150" style={{ color: "var(--color-on-surface-variant)" }}>
              Structure replaces intuition with evidence.{" "}
              <span style={{ color: "var(--color-primary)" }}>See full methodology &rarr;</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/landing/sections/evidence-section.tsx
git commit -m "feat(landing): rebuild evidence — Selection Funnel + Forensic Analysis grid"
```

---

## Task 7: Comparison Section — Rebuild

**Files:**
- Modify: `web/src/components/landing/sections/comparison-section.tsx`

- [ ] **Step 1: Rewrite comparison-section.tsx**

Replace entire file. Key changes:
- No table borders (no-line rule)
- Alternating surface tiers for row separation
- Margin Invest column: `surface-container-high` spotlight
- `blur-up` animation replaces `slide-from-left`
- Mobile: card layout instead of horizontal scroll

```tsx
"use client"

import { useEffect, useRef } from "react"

const ROWS = [
  { label: "Scoring", us: "Sector-neutral percentiles", screeners: "Absolute filters", blackbox: "Opaque composite" },
  { label: "Transparency", us: "Every formula documented", screeners: "Filter-based", blackbox: "Hidden methodology" },
  { label: "Filters", us: "6 forensic (Beneish, Altman)", screeners: "Price/volume only", blackbox: "None" },
  { label: "Auditability", us: "Spreadsheet-verifiable", screeners: "Limited", blackbox: "None" },
  { label: "Bias", us: "Deterministic, zero discretion", screeners: "User-configured", blackbox: "Analyst opinions" },
]

export function ComparisonSection() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return
      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)
      const el = sectionRef.current
      if (!el) return
      const rows = el.querySelectorAll("[data-comparison-row]")
      if (rows.length === 0) return
      gsap.set(rows, { opacity: 0, y: 16, filter: "blur(4px)" })
      trigger = ScrollTrigger.create({ trigger: el, start: "top 82%", once: true,
        onEnter: () => { gsap.to(rows, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.5, stagger: 0.08, ease: "power2.out" }) },
      })
    }

    animate().catch(() => {})
    return () => { cancelled = true; trigger?.kill() }
  }, [])

  return (
    <section ref={sectionRef} className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-headline-md uppercase text-center mb-12" style={{ color: "var(--color-on-surface)" }}>
          How We Compare
        </h2>

        {/* Desktop */}
        <div className="hidden md:block rounded-lg overflow-hidden" style={{ border: "1px solid var(--color-ghost-border)" }}>
          <table className="w-full text-left">
            <caption className="sr-only">Comparison of Margin Invest vs Screeners vs Black Box platforms</caption>
            <thead>
              <tr style={{ background: "var(--color-surface-container)" }}>
                <th scope="col" className="px-6 py-4 text-label-sm w-1/6" style={{ color: "var(--color-on-surface-variant)" }} />
                <th scope="col" className="px-6 py-4 text-label-sm w-[28%]" style={{ color: "var(--color-primary)", background: "var(--color-surface-container-high)" }}>MARGIN INVEST</th>
                <th scope="col" className="px-6 py-4 text-label-sm w-[28%]" style={{ color: "var(--color-on-surface-variant)" }}>SCREENERS</th>
                <th scope="col" className="px-6 py-4 text-label-sm w-[28%]" style={{ color: "var(--color-on-surface-variant)" }}>BLACK BOX</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row, i) => (
                <tr key={row.label} data-comparison-row style={{ background: i % 2 === 0 ? "var(--color-surface)" : "var(--color-surface-container-lowest)" }}>
                  <th scope="row" className="px-6 py-4 text-sm font-medium" style={{ color: "var(--color-on-surface)" }}>{row.label}</th>
                  <td className="px-6 py-4 text-sm" style={{ color: "var(--color-on-surface)", background: i % 2 === 0 ? "var(--color-surface-container-high)" : "rgba(22, 50, 32, 0.6)" }}>{row.us}</td>
                  <td className="px-6 py-4 text-sm" style={{ color: "var(--color-text-tertiary)" }}>{row.screeners}</td>
                  <td className="px-6 py-4 text-sm" style={{ color: "var(--color-text-tertiary)" }}>{row.blackbox}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile cards */}
        <div className="md:hidden flex flex-col gap-4">
          {ROWS.map((row) => (
            <div key={row.label} data-comparison-row className="p-5 rounded-lg" style={{ background: "var(--color-surface-container-low)", border: "1px solid var(--color-ghost-border)" }}>
              <div className="text-label-sm mb-3" style={{ color: "var(--color-on-surface-variant)" }}>{row.label.toUpperCase()}</div>
              <div className="flex flex-col gap-2">
                <div>
                  <span className="text-label-sm" style={{ color: "var(--color-primary)" }}>MARGIN INVEST</span>
                  <p className="text-sm mt-0.5" style={{ color: "var(--color-on-surface)" }}>{row.us}</p>
                </div>
                <div>
                  <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>SCREENERS</span>
                  <p className="text-sm mt-0.5" style={{ color: "var(--color-text-tertiary)" }}>{row.screeners}</p>
                </div>
                <div>
                  <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>BLACK BOX</span>
                  <p className="text-sm mt-0.5" style={{ color: "var(--color-text-tertiary)" }}>{row.blackbox}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/landing/sections/comparison-section.tsx
git commit -m "feat(landing): rebuild comparison — tonal rows, spotlight column, mobile cards"
```

---

## Task 8: Pricing Section — Rebuild

**Files:**
- Modify: `web/src/components/landing/sections/pricing-section.tsx`
- Modify: `web/src/components/landing/sections/pricing-tier-card.tsx`

- [ ] **Step 1: Rewrite pricing-section.tsx**

Replace entire file. Key changes:
- Heading: "Choose Your Aperture" (Newsreader uppercase)
- Toggle: `surface-container-lowest` track, `primary-container` active indicator, no pill
- Cards: `expo.out` stagger (no `back.out` bounce)
- Trust strip: Space Grotesk labels, no icons
- Remove ScrollReveal wrapper — use direct GSAP for card entrance

```tsx
"use client"

import { useEffect, useRef, useState } from "react"
import posthog from "posthog-js"
import { PricingTierCard, type Tier } from "./pricing-tier-card"

interface TierBase {
  name: string
  monthlyPrice: number | null
  description: string
  features: string[]
  highlighted: boolean
}

const TIER_DATA: TierBase[] = [
  {
    name: "Scout", monthlyPrice: null, description: "Search any ticker. See what survives.",
    features: ["Unlimited ticker searches", "Composite score + factor bars", "Elimination filter results", "1 full forensic report / month", "5-ticker watchlist"],
    highlighted: false,
  },
  {
    name: "Analyst", monthlyPrice: 19, description: "Full forensic access for serious investors.",
    features: ["Everything in Scout", "Unlimited forensic reports", "90-day score history", "25-ticker watchlist", "Score alerts", "Sector peer comparison"],
    highlighted: true,
  },
  {
    name: "Portfolio", monthlyPrice: 49, description: "The system that runs your portfolio.",
    features: ["Everything in Analyst", "Unlimited history", "Correlation analysis", "Smart Money (13F tracking)", "API access", "Priority support"],
    highlighted: false,
  },
]

function buildTiers(annual: boolean): Tier[] {
  return TIER_DATA.map((t) => {
    if (t.monthlyPrice === null) return { name: t.name, price: "Free", period: "", description: t.description, features: t.features, highlighted: t.highlighted }
    if (annual) {
      const annualPrice = t.monthlyPrice * 10
      return { name: t.name, price: `$${annualPrice}`, period: "/year", description: t.description, features: t.features, highlighted: t.highlighted }
    }
    return { name: t.name, price: `$${t.monthlyPrice}`, period: "/mo", description: t.description, features: t.features, highlighted: t.highlighted }
  })
}

interface PricingSectionProps { totalUniverse?: number }

export function PricingSection({ totalUniverse }: PricingSectionProps) {
  const [annual, setAnnual] = useState(false)
  const sectionRef = useRef<HTMLElement>(null)
  const cardRefs = useRef<(HTMLDivElement | null)[]>([])
  const tiers = buildTiers(annual)

  useEffect(() => { posthog.capture("pricing_page_viewed") }, [])

  useEffect(() => {
    if (!sectionRef.current) return
    let cancelled = false
    const cleanups: (() => void)[] = []

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return
      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)
      const section = sectionRef.current
      const cards = cardRefs.current.filter(Boolean) as HTMLDivElement[]
      if (!section || cards.length !== 3) return
      gsap.set(cards, { opacity: 0, y: 32, filter: "blur(8px)" })
      const st = ScrollTrigger.create({ trigger: section, start: "top 78%", once: true,
        onEnter: () => { gsap.to(cards, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.65, stagger: 0.1, ease: "expo.out" }) },
      })
      cleanups.push(() => st.kill())
    }

    animate().catch(() => {})
    return () => { cancelled = true; cleanups.forEach((fn) => fn()) }
  }, [])

  return (
    <section ref={sectionRef} id="pricing" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-headline-md uppercase text-center mb-4" style={{ color: "var(--color-on-surface)" }}>Choose Your Aperture</h2>
        <p className="text-body-md text-center max-w-md mx-auto mb-10" style={{ color: "var(--color-on-surface-variant)" }}>Upgrade when the data changes how you think.</p>

        {/* Billing toggle */}
        <div className="flex items-center justify-center gap-1 mb-12 p-1 rounded-lg mx-auto w-fit" style={{ background: "var(--color-surface-container-lowest)" }}>
          <button type="button" onClick={() => setAnnual(false)} className="text-sm font-medium px-4 py-1.5 rounded-md transition-all duration-200" aria-pressed={!annual}
            style={{ background: !annual ? "var(--color-primary-container)" : "transparent", color: !annual ? "var(--color-on-primary-container)" : "var(--color-text-tertiary)" }}>Monthly</button>
          <button type="button" onClick={() => setAnnual(true)} className="text-sm font-medium px-4 py-1.5 rounded-md transition-all duration-200 inline-flex items-center gap-2" aria-pressed={annual}
            style={{ background: annual ? "var(--color-primary-container)" : "transparent", color: annual ? "var(--color-on-primary-container)" : "var(--color-text-tertiary)" }}>
            Annual
            <span className="text-label-sm px-1.5 py-0.5 rounded" style={{ color: "var(--color-bullish)", background: "rgba(34,197,94,0.12)" }}>2 FREE</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {tiers.map((tier, i) => (
            <div key={tier.name} ref={(el) => { cardRefs.current[i] = el }}>
              <PricingTierCard tier={tier} />
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-2 mt-4">
          <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>NO CREDIT CARD REQUIRED</span>
          <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>30-DAY GUARANTEE</span>
          <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>API AVAILABLE</span>
        </div>

        <div className="text-center mt-6">
          <p className="text-label-sm" style={{ color: "var(--color-primary)" }}>
            Scoring {(totalUniverse ?? 3056).toLocaleString()} US equities daily
          </p>
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Rewrite pricing-tier-card.tsx**

Replace entire file. Key changes:
- Ghost border cards, no `terminal-card` class
- Highlighted card: `surface-container-high` (tonal lift, no scale transform, no `-mt-2`)
- Price in Newsreader `text-headline-md` (was `font-mono text-4xl`)
- CTA: `0.375rem` radius, primary-container fill for highlighted, ghost for others
- No hover translate

```tsx
"use client"

import Link from "next/link"
import posthog from "posthog-js"

export interface Tier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  highlighted?: boolean
}

const CTA_TEXT: Record<string, string> = { Scout: "Search Any Ticker", Analyst: "Start Analyzing", Portfolio: "Start Building" }

export function PricingTierCard({ tier }: { tier: Tier }) {
  const bg = tier.highlighted ? "var(--color-surface-container-high)" : "var(--color-surface-container-low)"

  return (
    <div className="rounded-lg flex flex-col h-full p-6 md:p-8 transition-all duration-200"
      style={{ background: bg, border: "1px solid var(--color-ghost-border)" }}>
      <div className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>
        {tier.name.toUpperCase()}
        {tier.highlighted && (
          <span className="ml-2 text-label-sm px-2 py-0.5 rounded" style={{ color: "var(--color-primary)", background: "rgba(128, 216, 178, 0.1)" }}>POPULAR</span>
        )}
      </div>

      <div className="mb-2">
        <span className="text-headline-md" style={{ color: "var(--color-on-surface)" }}>{tier.price}</span>
        {tier.period && <span className="text-sm ml-1" style={{ color: "var(--color-text-tertiary)" }}>{tier.period}</span>}
      </div>

      <p className="text-sm mb-1" style={{ color: "var(--color-on-surface-variant)" }}>{tier.description}</p>
      {tier.period ? (
        <p className="text-label-sm mb-6" style={{ color: "var(--color-text-tertiary)" }}>billed {tier.period === "/year" ? "annually" : "monthly"}</p>
      ) : <div className="mb-6" />}

      <div className="flex flex-col gap-3 mb-8 flex-1">
        {tier.features.map((feature) => (
          <div key={feature} className="flex items-start gap-2 text-sm" style={{ color: "var(--color-on-surface-variant)" }}>
            <span style={{ color: "var(--color-primary)" }}>&#10003;</span>
            <span>{feature}</span>
          </div>
        ))}
      </div>

      <Link href="/onboarding" onClick={() => posthog.capture("checkout_started", { plan: tier.name })}
        className="block text-center text-sm font-medium py-2.5 transition-all duration-200"
        style={{
          borderRadius: "0.375rem",
          background: tier.highlighted ? "var(--color-primary-container)" : "transparent",
          color: tier.highlighted ? "var(--color-on-primary-container)" : "var(--color-primary)",
          border: tier.highlighted ? "none" : "1px solid var(--color-ghost-border)",
        }}>
        {CTA_TEXT[tier.name] ?? "Get Started"}
      </Link>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/landing/sections/pricing-section.tsx web/src/components/landing/sections/pricing-tier-card.tsx
git commit -m "feat(landing): rebuild pricing — CHOOSE YOUR APERTURE, tonal cards, expo.out"
```

---

## Task 9: Footer Section — Rebuild

**Files:**
- Modify: `web/src/components/landing/sections/footer-section.tsx`

- [ ] **Step 1: Rewrite footer-section.tsx**

Replace entire file. Key changes:
- Remove CTA search block and FAQ accordion
- Remove `faq-section` import (file will be deleted)
- `surface-container-lowest` background (darkest tier = page end)
- Newsreader italic tagline
- 2-column links (Product | Company), Inter Tight, `on-surface-variant`
- Space Grotesk `label-sm` copyright + "DETERMINISTIC BY DESIGN."
- No borders — background shift is the boundary

```tsx
"use client"

import Link from "next/link"
import { useEffect, useRef } from "react"
import { LogoIcon } from "@/components/ui/logo-icon"

const productLinks = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Explore", href: "/explore" },
  { label: "Methodology", href: "/methodology" },
  { label: "API", href: "/api-docs" },
  { label: "Status", href: "/status" },
]

const companyLinks = [
  { label: "About", href: "/about" },
  { label: "Legal", href: "/legal" },
  { label: "Terms", href: "/terms" },
  { label: "Privacy", href: "/privacy" },
  { label: "Contact", href: "/contact" },
]

export function FooterSection() {
  const footerRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!footerRef.current) return
    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return
      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)
      const el = footerRef.current
      if (!el) return
      const content = el.querySelector("[data-footer-content]")
      if (!content) return
      gsap.set(content, { opacity: 0 })
      trigger = ScrollTrigger.create({ trigger: el, start: "top 90%", once: true,
        onEnter: () => { gsap.to(content, { opacity: 1, duration: 0.6, ease: "power2.out" }) },
      })
    }

    animate().catch(() => {})
    return () => { cancelled = true; trigger?.kill() }
  }, [])

  return (
    <footer id="footer" ref={footerRef} style={{ background: "var(--color-surface-container-lowest)" }}>
      <div data-footer-content className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr] gap-10">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <LogoIcon size={20} />
              <span className="text-headline-md" style={{ color: "var(--color-on-surface)", fontSize: "1.125rem" }}>Margin Invest</span>
            </div>
            <p className="text-sm max-w-xs leading-relaxed" style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-display)", fontStyle: "italic" }}>
              A deterministic capital allocation system. Structure replaces narrative.
            </p>
          </div>

          <div>
            <h4 className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>PRODUCT</h4>
            <nav className="flex flex-col gap-2">
              {productLinks.map((link) => (
                <Link key={link.label} href={link.href} className="text-sm transition-colors duration-150" style={{ color: "var(--color-on-surface-variant)" }}>{link.label}</Link>
              ))}
            </nav>
          </div>

          <div>
            <h4 className="text-label-sm mb-4" style={{ color: "var(--color-on-surface-variant)" }}>COMPANY</h4>
            <nav className="flex flex-col gap-2">
              {companyLinks.map((link) => (
                <Link key={link.label} href={link.href} className="text-sm transition-colors duration-150" style={{ color: "var(--color-on-surface-variant)" }}>{link.label}</Link>
              ))}
            </nav>
          </div>
        </div>

        <div className="mt-12 pt-6 flex flex-col md:flex-row justify-between items-center gap-3">
          <p className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>&copy; 2026 MARGIN INVEST</p>
          <p className="text-label-sm" style={{ color: "var(--color-text-tertiary)" }}>DETERMINISTIC BY DESIGN.</p>
        </div>
      </div>
    </footer>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/landing/sections/footer-section.tsx
git commit -m "feat(landing): rebuild footer — simplified, tonal background, no CTA/FAQ"
```

---

## Task 10: Selectivity Funnel — Restyle

**Files:**
- Modify: `web/src/components/landing/visualizations/selectivity-funnel.tsx`

- [ ] **Step 1: Update `STAGE_COLORS` (lines 29–34)**

Change:
```typescript
const STAGE_COLORS = [
  "rgba(26,122,90,0.15)",
  "rgba(26,122,90,0.30)",
  "rgba(26,122,90,0.55)",
  "rgba(26,122,90,0.85)",
]
```
To:
```typescript
const STAGE_COLORS = [
  "var(--color-surface-container)",
  "var(--color-surface-container-high)",
  "var(--color-surface-container-highest)",
  "var(--color-primary-container)",
]
```

- [ ] **Step 2: Update FunnelStage label typography (around line 97)**

Change:
```tsx
<span className="text-mono-label text-text-tertiary transition-colors duration-200 group-hover/funnel:text-text-secondary">
```
To:
```tsx
<span className="text-label-sm transition-colors duration-200" style={{ color: "var(--color-on-surface-variant)" }}>
```

- [ ] **Step 3: Update description text (around line 100)**

Change:
```tsx
<p className="text-xs text-text-tertiary mt-0.5">{stage.description}</p>
```
To:
```tsx
<p className="text-xs mt-0.5" style={{ color: "var(--color-text-tertiary)" }}>{stage.description}</p>
```

- [ ] **Step 4: Update count span (around line 103)**

Change the className and add style prop:
```tsx
className="text-label-md tabular-nums transition-colors duration-200 ml-4"
style={{
  color: isFinal && allDone ? "var(--color-primary)" : "var(--color-on-surface-variant)",
  fontWeight: isFinal && allDone ? 700 : 400,
}}
```

Remove the existing ternary className logic.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/landing/visualizations/selectivity-funnel.tsx
git commit -m "feat(landing): restyle funnel — tonal stage colors, Space Grotesk labels"
```

---

## Task 11: Delete Cut Sections and Components

**Files:**
- Delete: 13 component files + associated tests
- Modify: `web/src/components/landing/index.ts`
- Modify: `web/src/app/page.tsx`

- [ ] **Step 1: Delete cut section files**

```bash
rm -f web/src/components/landing/sections/authority-strip.tsx
rm -f web/src/components/landing/sections/social-proof-section.tsx
rm -f web/src/components/landing/sections/transparency-strip.tsx
rm -f web/src/components/landing/sections/pipeline-section.tsx
rm -f web/src/components/landing/sections/results-showcase-section.tsx
rm -f web/src/components/landing/sections/faq-section.tsx
rm -f web/src/components/landing/sections/how-it-works-section.tsx
rm -f web/src/components/landing/sections/pillars-section.tsx
```

- [ ] **Step 2: Delete cut visualization files**

```bash
rm -f web/src/components/landing/visualizations/radar-chart.tsx
rm -f web/src/components/landing/visualizations/mini-candidate-stack.tsx
rm -f web/src/components/landing/visualizations/sparkline.tsx
rm -f web/src/components/landing/visualizations/animated-counter.tsx
rm -f web/src/components/landing/hero-candidate-card.tsx
```

- [ ] **Step 3: Delete associated test files**

```bash
rm -f web/src/components/landing/__tests__/hero-candidate-card.test.tsx
rm -f web/src/components/landing/visualizations/__tests__/radar-chart.test.tsx
```

Also find and delete any other test files that import deleted components:

```bash
grep -rl "authority-strip\|social-proof\|transparency-strip\|pipeline-section\|results-showcase\|faq-section\|how-it-works\|pillars-section" web/src --include="*.test.*" | xargs rm -f
```

- [ ] **Step 4: Update barrel export `index.ts`**

Replace `web/src/components/landing/index.ts`:

```typescript
export { HeroSection } from "./sections/hero-section"
export { EvidenceSection } from "./sections/evidence-section"
export { ComparisonSection } from "./sections/comparison-section"
export { PricingSection } from "./sections/pricing-section"
export { FooterSection } from "./sections/footer-section"
```

- [ ] **Step 5: Remove FAQ import and schema from page.tsx**

In `web/src/app/page.tsx`:

1. Remove line 7: `import { FAQ_ITEMS } from "@/data/faq-items"`

2. Remove the FAQPage block from the jsonLd `@graph` array (the object with `"@type": "FAQPage"`). This is the third item in the array, around lines 118-128.

- [ ] **Step 6: Verify build**

```bash
cd web && npx next build --no-lint 2>&1 | tail -10
```

Expected: No import resolution errors.

- [ ] **Step 7: Commit**

```bash
git add -A web/src/components/landing/ web/src/app/page.tsx
git commit -m "feat(landing): delete cut sections and components

Remove: authority-strip, social-proof, transparency-strip, pipeline,
results-showcase, faq, how-it-works, pillars, radar-chart,
mini-candidate-stack, sparkline, animated-counter, hero-candidate-card."
```

---

## Task 12: Verify and Fix

**Files:** All modified files

- [ ] **Step 1: Run the build**

```bash
cd web && npx next build 2>&1 | tail -30
```

Expected: Clean build. Fix any TypeScript errors or missing imports.

- [ ] **Step 2: Run tests**

```bash
cd web && npx vitest run 2>&1 | tail -20
```

Delete any remaining test files that reference deleted components.

- [ ] **Step 3: Visual verification**

```bash
cd web && npx next dev
```

Open http://localhost:3000 and verify:
1. Navbar: frosted glass, no bottom border
2. Hero: "DISCIPLINE ENGINEER" in Newsreader, stats row with counting, instrument panel
3. Evidence: funnel + 3 forensic cards, no solid borders
4. Comparison: tonal rows, Margin Invest column highlighted
5. Pricing: "CHOOSE YOUR APERTURE", tonal cards, no bounce
6. Footer: dark background, no CTA/FAQ, Newsreader italic tagline
7. All fonts load: Newsreader (headlines), Space Grotesk (data/labels), Inter Tight (body)

- [ ] **Step 4: Commit any fixes**

```bash
git add -A web/
git commit -m "fix(landing): resolve build and test issues from redesign"
```
