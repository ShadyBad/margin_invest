# Premium Redesign Phase 2 — Product-Led Homepage

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan one step at a time.

**Goal:** Replace the 10-section SaaS template homepage with a 5-section product-first experience that lets the product speak for itself.

**Architecture:** Six tasks transform the homepage. Task 1 strips sections from the orchestrator. Tasks 2-4 create new components (product hero, authority strip, condensed evidence). Task 5 updates pricing. Task 6 simplifies the footer. The public score API (`/api/v1/public/score/{ticker}`) already exists — no backend changes needed. The hero search component (`hero-search.tsx`) already fetches from it and renders inline results. We refactor the hero to make search the primary CTA (no separate "Get Started" button) and add ticker suggestion chips below.

**Tech Stack:** Next.js 16, React 19, Tailwind v4, Vitest, GSAP (animations)

**Design doc:** `docs/plans/2026-03-08-premium-redesign-design.md` — Phase 2 (sections 2.1-2.6)

---

### Task 1: Strip Homepage to 5 Sections

**Files:**
- Modify: `web/src/components/landing/homepage-client.tsx`
- Modify: `web/src/components/landing/section-indicator.tsx`

**Step 1: Remove sections from homepage-client.tsx**

In `homepage-client.tsx`, make these changes:

1a. Delete these imports (lines 5-9, 13):
```tsx
import { ProblemSection } from "./problem-section"
import { EliminationVignette } from "./elimination-vignette"
import { EngineSection } from "./engine-section"
import { ProofSection } from "./proof-section"
import { PositioningSection } from "./positioning-section"
import { SectionIndicator } from "./section-indicator"
```

1b. Delete the `useCallback` import (line 1 — `useCallback` is only used by `handleStageChange`).

1c. Delete the `formatEliminationPct` import (line 14).

1d. Delete the `handleStageChange` callback (lines 43-45).

1e. Replace the JSX body (lines 48-68) with:

```tsx
export function HomepageClient({ data }: HomepageClientProps) {
  return (
    <div className="relative z-10">
      <HeroSection data={data} />
      <PricingSection />
      <FaqSection />
      <FooterSection />
    </div>
  )
}
```

Note: The `SectionGlow` component at the top of the file can stay — it's harmless and may be reused. Or delete it for cleanliness; it's not exported.

Keep all removed section files on disk — they'll be used on `/methodology` and `/faq` pages later.

**Step 2: Update section-indicator.tsx**

In `section-indicator.tsx`, update the `SECTIONS` array (lines 5-15) to match the new homepage:

```tsx
const SECTIONS = [
  { id: "hero", label: "Hero" },
  { id: "pricing", label: "Pricing" },
  { id: "faq", label: "FAQ" },
  { id: "footer", label: "Footer" },
]
```

**Step 3: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All existing tests pass. No landing component tests reference removed sections.

**Step 4: Verify build**

Run: `cd web && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 5: Commit**

Message: "refactor(web): strip homepage to 5 sections for product-led redesign"

---

### Task 2: Refactor Hero into Product Hero

**Files:**
- Modify: `web/src/components/landing/hero-section.tsx`
- Modify: `web/src/components/landing/hero-search.tsx`
- Keep (no changes): `web/src/components/landing/hero-candidate-card.tsx`

The hero currently has: headline (left) + rotating candidate card (right) in a 2-column layout. The new hero: full-width centered layout with search as the primary CTA and ticker suggestion chips. The rotating card is REMOVED — the inline search result replaces it as the product demo.

**Step 1: Rewrite hero-section.tsx**

Replace the entire content of `hero-section.tsx` with:

```tsx
"use client"

import { useEffect, useRef } from "react"
import type { HomepageData } from "./types"
import { HeroSearch } from "./hero-search"

interface HeroSectionProps {
  data: HomepageData | null
}

export function HeroSection({ data }: HeroSectionProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

    let cancelled = false

    async function animate() {
      const gsapModule = await import("gsap")
      if (cancelled) return
      const gsap = gsapModule.default

      const section = sectionRef.current
      if (!section) return

      const headline = section.querySelector("[data-hero-headline]")
      const subtext = section.querySelector("[data-hero-subtext]")
      const search = section.querySelector("[data-hero-ctas]")

      const textTargets = [headline, subtext, search].filter(Boolean)
      gsap.set(textTargets, { opacity: 0, y: 20 })

      textTargets.forEach((target, i) => {
        gsap.to(target, {
          opacity: 1,
          y: 0,
          duration: 0.6,
          delay: i * 0.12,
          ease: "power2.out",
        })
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section
      id="hero"
      ref={sectionRef}
      className="relative flex items-center justify-center overflow-hidden"
      style={{
        minHeight: "100svh",
        background:
          "radial-gradient(ellipse 60% 50% at 50% 30%, rgba(26,122,90,0.10) 0%, transparent 65%), var(--color-bg-primary)",
      }}
    >
      {/* Noise texture overlay */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage: "url('/noise.svg')",
          backgroundRepeat: "repeat",
          opacity: 0.4,
        }}
      />

      {/* Grid overlay for depth */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-grid-line) 1px, transparent 1px), linear-gradient(90deg, var(--color-grid-line) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          opacity: 1,
        }}
      />

      <div className="max-w-3xl w-full text-center pt-16 py-24 px-6 relative z-10">
        <h1
          data-hero-headline
          className="font-display leading-[1.05] tracking-tight mb-6"
          style={{ fontSize: "clamp(48px, 7vw, 72px)" }}
        >
          <span className="block text-text-primary">Discipline.</span>
          <span className="block" style={{ color: "var(--color-accent)" }}>
            Engineered.
          </span>
        </h1>

        <p
          data-hero-subtext
          className="text-lg md:text-xl text-text-secondary max-w-xl mx-auto mb-10 leading-relaxed"
        >
          A deterministic scoring engine for 3,056 US equities. No opinions. No
          overrides. Search one.
        </p>

        <HeroSearch />
      </div>

      {/* Bottom fade gradient */}
      <div
        className="pointer-events-none absolute bottom-0 left-0 right-0 h-32"
        style={{
          background:
            "linear-gradient(to bottom, transparent, var(--color-bg-primary))",
        }}
      />
    </section>
  )
}
```

Key changes from current:
- Removed 2-column grid layout → single centered column
- Removed `HeroCandidateCard` import and usage (kept on disk)
- Removed `data` destructuring for candidates/universeSize/eligibleCount
- Capped headline at 72px max (was 96px) per design doc
- Centered the radial gradient (was offset to 85% 25%)
- Removed gold accent radial gradient (simplification)
- `data` prop kept in interface for future use but not destructured

**Step 2: Add ticker suggestion chips to hero-search.tsx**

In `hero-search.tsx`, add suggestion chips below the search form. After the closing `</form>` tag (line 138) and before the `{/* Result card */}` comment (line 140), add:

```tsx
      {/* Ticker suggestion chips */}
      {state === "idle" && (
        <div className="flex items-center justify-center gap-2 mt-4 flex-wrap">
          <span className="text-xs text-text-tertiary">Try:</span>
          {["AAPL", "TSLA", "JNJ", "COST", "ETSY"].map((ticker) => (
            <button
              key={ticker}
              type="button"
              onClick={() => {
                setQuery(ticker)
                setState("loading")
                setError("")
                setResult(null)
                apiFetch<PublicScoreResult>(`/api/v1/public/score/${ticker}`)
                  .then((data) => {
                    setResult(data)
                    setState("result")
                  })
                  .catch((err) => {
                    if (err instanceof ApiError && err.status === 404) {
                      setError("Ticker not found. Check the symbol and try again.")
                    } else {
                      setError("Something went wrong. Please try again.")
                    }
                    setState("error")
                  })
              }}
              className="font-mono text-xs text-accent hover:text-accent/80 transition-colors px-2 py-1 rounded border border-border-subtle hover:border-accent/30"
            >
              {ticker}
            </button>
          ))}
        </div>
      )}
```

Also update the search form container class. Change line 86:
- Old: `<form onSubmit={handleSubmit} className="flex gap-2 max-w-md">`
- New: `<form onSubmit={handleSubmit} className="flex gap-2 max-w-md mx-auto">`

And update the result card max-width on line 143:
- Old: `className="relative overflow-hidden rounded-xl bg-bg-elevated mt-4 max-w-md animate-in fade-in duration-200"`
- New: `className="relative overflow-hidden rounded-xl bg-bg-elevated mt-4 max-w-md mx-auto animate-in fade-in duration-200"`

And update the error state on line 252:
- Old: `<p className="text-sm text-[var(--color-bearish)] mt-3 max-w-md">`
- New: `<p className="text-sm text-[var(--color-bearish)] mt-3 max-w-md mx-auto text-center">`

**Step 3: Update the CTA link text**

In `hero-search.tsx`, change the forensic report link text (around line 229):
- Old: `See the full forensic report`
- New: `View full forensic report`

And change the link destination:
- Old: `href="/onboarding"`
- New: `href={`/asset/${result.ticker}`}`

This links directly to the asset detail page instead of onboarding. The asset detail page exists and shows the full report.

**Step 4: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All tests pass.

**Step 5: Verify build**

Run: `cd web && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 6: Commit**

Message: "feat(web): refactor hero into centered product hero with search as primary CTA"

---

### Task 3: Add Authority Strip

**Files:**
- Create: `web/src/components/landing/authority-strip.tsx`
- Modify: `web/src/components/landing/homepage-client.tsx`

**Step 1: Create authority-strip.tsx**

Create `web/src/components/landing/authority-strip.tsx`:

```tsx
const COLUMNS = [
  {
    label: "Data Sources",
    items: ["SEC EDGAR Filings", "Earnings Transcripts", "Daily Market Data"],
  },
  {
    label: "Coverage",
    items: ["3,056 equities", "11 GICS sectors", "6 elimination filters"],
  },
  {
    label: "Engine",
    items: ["v1.3.2", "Scored daily"],
  },
]

export function AuthorityStrip() {
  return (
    <section className="border-y border-border-subtle">
      <div className="max-w-5xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
          {COLUMNS.map((col) => (
            <div key={col.label}>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-2">
                {col.label}
              </div>
              <div className="space-y-1">
                {col.items.map((item) => (
                  <div
                    key={item}
                    className="font-mono text-xs text-text-secondary"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 2: Add AuthorityStrip to homepage**

In `homepage-client.tsx`, add the import after the HeroSection import:

```tsx
import { AuthorityStrip } from "./authority-strip"
```

Add `<AuthorityStrip />` after `<HeroSection data={data} />` in the JSX:

```tsx
<HeroSection data={data} />
<AuthorityStrip />
<PricingSection />
```

**Step 3: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All tests pass.

**Step 4: Verify build**

Run: `cd web && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 5: Commit**

Message: "feat(web): add authority strip with data source and coverage facts"

---

### Task 4: Add Condensed Evidence Section

**Files:**
- Create: `web/src/components/landing/evidence-section.tsx`
- Modify: `web/src/components/landing/homepage-client.tsx`

This replaces the old ProofSection (4 separate cards) with a single unified panel containing 3 columns. The old ProofSection and its sub-components stay on disk.

**Step 1: Create evidence-section.tsx**

Create `web/src/components/landing/evidence-section.tsx`:

```tsx
"use client"

import { useEffect, useRef } from "react"
import { ProofSelectivityFunnel } from "./proof-selectivity-funnel"
import { ProofSectorChart } from "./proof-sector-chart"
import { ProofHeatmap } from "./proof-heatmap"
import type { CandidateCard } from "./types"

interface EvidenceSectionProps {
  candidates?: CandidateCard[]
}

export function EvidenceSection({ candidates = [] }: EvidenceSectionProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!panelRef.current) return

    let cancelled = false
    let trigger: { kill: () => void } | null = null

    async function animate() {
      const gsapModule = await import("gsap")
      const { default: ScrollTrigger } = await import("gsap/ScrollTrigger")
      if (cancelled) return

      const gsap = gsapModule.default
      gsap.registerPlugin(ScrollTrigger)

      const el = panelRef.current
      if (!el) return

      gsap.set(el, { opacity: 0, y: 24 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 85%",
        once: true,
        onEnter: () => {
          gsap.to(el, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" })
        },
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [])

  return (
    <section id="evidence" className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        <div
          ref={panelRef}
          className="border border-border-subtle rounded-xl overflow-hidden"
          style={{ background: "var(--color-bg-elevated)" }}
        >
          {/* Terminal-style header */}
          <div
            className="px-6 py-3 border-b border-border-subtle"
            style={{ background: "var(--color-bg-subtle)" }}
          >
            <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary">
              System Output — Current Scoring Cycle
            </span>
          </div>

          {/* 3-column content */}
          <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-border-subtle">
            <div className="p-6">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Selectivity Funnel
              </div>
              <ProofSelectivityFunnel />
            </div>
            <div className="p-6">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Sector Breakdown
              </div>
              <ProofSectorChart candidates={candidates} />
            </div>
            <div className="p-6">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">
                Factor Correlation
              </div>
              <ProofHeatmap />
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-border-subtle text-center">
            <a
              href="/methodology"
              className="text-sm text-text-secondary hover:text-accent transition-colors"
            >
              Structure replaces intuition with evidence.{" "}
              <span className="text-accent">See full methodology →</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
```

**Step 2: Add EvidenceSection to homepage**

In `homepage-client.tsx`, add the import:

```tsx
import { EvidenceSection } from "./evidence-section"
```

Add `<EvidenceSection candidates={data?.allPicks ?? []} />` after `<AuthorityStrip />`:

```tsx
<HeroSection data={data} />
<AuthorityStrip />
<EvidenceSection candidates={data?.allPicks ?? []} />
<PricingSection />
```

**Step 3: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All tests pass.

**Step 4: Verify build**

Run: `cd web && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 5: Commit**

Message: "feat(web): add condensed evidence section with unified 3-column panel"

---

### Task 5: Update Pricing Section

**Files:**
- Modify: `web/src/components/landing/pricing-section.tsx`

**Step 1: Add institutional contact row**

In `pricing-section.tsx`, after the closing `</div>` of the `text-center space-y-3` div (line 74) and before the closing `</div>` of the `max-w-5xl` container, add:

```tsx
        <div className="mt-10 pt-6 border-t border-border-subtle text-center">
          <p className="text-sm text-text-secondary">
            Need API access or custom integration?{" "}
            <a
              href="/contact"
              className="text-accent hover:text-accent/80 transition-colors"
            >
              Contact us →
            </a>
          </p>
        </div>
```

**Step 2: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All tests pass.

**Step 3: Verify build**

Run: `cd web && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 4: Commit**

Message: "feat(web): add institutional contact row to pricing section"

---

### Task 6: Simplify Footer

**Files:**
- Modify: `web/src/components/landing/footer-section.tsx`

**Step 1: Check for tests asserting trust badges**

Run: `cd web && grep -r "SEC Filings\|trustBadges\|trust strip\|No Hidden" src/ -l`

Update any matching test files to remove those assertions.

**Step 2: Remove the trust badge strip**

In `footer-section.tsx`, delete the `trustBadges` array (lines 20-26) and the trust strip `<div>` block (lines 32-40 — the entire `{/* Trust strip */}` section including its containing div).

**Step 3: Fix minimum font sizes**

In `footer-section.tsx`, replace all instances of `text-[10px]` with `text-xs` (minimum 12px per design system). There are 3 occurrences:
- Line 35 (trust badges — deleted in step 2)
- Line 53 (brand column "Deterministic scoring engine")
- Line 60 (Product column heading)
- Line 80 (Company column heading)
- Line 100 (bottom bar tagline)

**Step 4: Run tests**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All tests pass.

**Step 5: Verify build**

Run: `cd web && npx next build 2>&1 | tail -5`
Expected: Build succeeds.

**Step 6: Commit**

Message: "fix(web): simplify footer — remove trust badges, fix minimum font sizes"

---

## Verification Checklist

After all 6 tasks are complete:

1. Full test suite: `cd web && npx vitest run`
2. Build: `cd web && npx next build`
3. Lint: `cd web && npx eslint --fix .`

Visual spot-check (run dev server at localhost:3000):
- Hero is full-width centered with search as the primary CTA
- Ticker suggestion chips ("Try: AAPL · TSLA · JNJ · COST · ETSY") appear below search
- Clicking a chip performs the search and shows inline result
- No rotating candidate card
- Authority strip shows 3 columns of facts below hero
- Evidence section is a single unified panel with 3 columns (Selectivity, Sector, Correlation)
- Evidence panel has terminal-style "SYSTEM OUTPUT" header
- Methodology link at bottom of evidence section
- Pricing section has institutional contact row
- No trust badge strip in footer
- No Problem, Elimination Stat, Engine Pipeline, or Positioning sections on homepage
- All removed sections' files still exist on disk
