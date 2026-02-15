# Homepage Elevation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Elevate the Margin Invest homepage to award-level quality with a signature HTML-to-3D morph moment, differentiated per-section motion, and full-screen positioning climax.

**Architecture:** Modify 13 existing components and create 1 new hook (`useNodePositions`). The signature moment synchronizes HTML element positions with 3D scene nodes via a shared zustand store. All changes respect the existing performance budget (demand frameloop, DPR cap, quality tiers).

**Tech Stack:** React 18, Next.js 15 App Router, Framer Motion, React Three Fiber, Drei, Zustand (new dependency for position sync), Vitest + React Testing Library.

**Design doc:** `docs/plans/2026-02-14-homepage-elevation-design.md`

**Test command:** `cd web && npx vitest run src/components/landing/__tests__/ --reporter=verbose`

**Framer Motion mock pattern** (used in all test files):
```tsx
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    section: ({ children, ...props }: any) => <section {...props}>{children}</section>,
  },
  useInView: () => true,
  useMotionValue: (init: number) => ({ get: () => init, set: () => {} }),
  useTransform: (_: any, __: any, output: any[]) => ({ get: () => output[output.length - 1] }),
  animate: vi.fn(),
}))
```

---

## Wave 1: Independent Section Updates (no cross-dependencies)

These tasks can be executed in any order or in parallel.

---

### Task 1: Hero Section — Copy, Padding, Motion

**Files:**
- Modify: `web/src/components/landing/sections/hero-section.tsx`
- Modify: `web/src/components/landing/__tests__/sections.test.tsx` (HeroSection tests)

**Step 1: Update the test expectations for new copy**

In `web/src/components/landing/__tests__/sections.test.tsx`, update the HeroSection tests:

```tsx
describe("HeroSection", () => {
  it("renders the headline", () => {
    render(<HeroSection />)
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
  })

  it("renders the subline", () => {
    render(<HeroSection />)
    expect(
      screen.getByText("A deterministic scoring engine for capital allocation.")
    ).toBeInTheDocument()
  })

  it("renders the primary CTA", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /explore the engine/i })).toBeInTheDocument()
  })

  it("renders the secondary link", () => {
    render(<HeroSection />)
    expect(screen.getByRole("link", { name: /view methodology/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify the subline test fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: HeroSection "renders the subline" FAILS (old copy still present).

**Step 3: Update hero-section.tsx**

Replace the full contents of `web/src/components/landing/sections/hero-section.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"
import { ButtonPrimary } from "../button-primary"
import { ButtonSecondary } from "../button-secondary"

const ease = [0.22, 1, 0.36, 1] as const

export function HeroSection() {
  return (
    <section className="relative">
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "160px",
          paddingBottom: "120px",
        }}
      >
        <div className="col-span-4 md:col-span-8 lg:col-span-8 flex flex-col justify-center lg:mt-[20px]">
          <motion.h1
            className="text-[48px] md:text-[56px] lg:text-[72px] font-bold leading-[0.98] tracking-[-0.5px] text-text-primary"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2, ease }}
          >
            Structure outperforms emotion.
          </motion.h1>

          <motion.p
            className="mt-6 text-lg md:text-xl text-text-secondary leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.4, ease }}
          >
            A deterministic scoring engine for capital allocation.
          </motion.p>

          <motion.div
            className="mt-10 flex items-center gap-6"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.55, ease }}
          >
            <ButtonPrimary href="/dashboard">Explore the Engine</ButtonPrimary>
            <ButtonSecondary href="/methodology">View methodology</ButtonSecondary>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
```

Changes from original:
- Subhead copy: "Institutional-grade analytics..." → "A deterministic scoring engine..."
- Removed `max-w-[640px]` from subhead
- Padding: 140/80 → 160/120
- Added `lg:mt-[20px]` to content column
- H1 motion: `opacity+y` → `opacity` only (no vertical movement, 800ms)
- Subhead motion: `opacity+y` → `opacity` only (no vertical movement)

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: All HeroSection tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/hero-section.tsx web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat(landing): update hero copy, padding, and motion signature"
```

---

### Task 2: Friction Section — Horizontal Motion, SVG Visibility, Citation

**Files:**
- Modify: `web/src/components/landing/sections/friction-section.tsx`
- Modify: `web/src/components/landing/__tests__/sections.test.tsx` (FrictionSection tests)

**Step 1: Update the test to verify citation text**

In `sections.test.tsx`, update the FrictionSection describe block:

```tsx
describe("FrictionSection", () => {
  it("renders three declarative lines", () => {
    render(<FrictionSection />)
    expect(screen.getByText("Most investors react.")).toBeInTheDocument()
    expect(screen.getByText("Few operate with structure.")).toBeInTheDocument()
    expect(screen.getByText("Emotion is expensive.")).toBeInTheDocument()
  })

  it("renders the behavioral finance citation", () => {
    render(<FrictionSection />)
    expect(screen.getByText(/Barber & Odean/)).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify citation test fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: "renders the behavioral finance citation" FAILS.

**Step 3: Update friction-section.tsx**

Replace the full contents of `web/src/components/landing/sections/friction-section.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const lines = [
  "Most investors react.",
  "Few operate with structure.",
  "Emotion is expensive.",
]

function MarketNoiseViz() {
  const points = [
    { x: 30, y: 20, r: 3.75 },
    { x: 85, y: 55, r: 4.5 },
    { x: 160, y: 30, r: 3 },
    { x: 220, y: 85, r: 5.25 },
    { x: 130, y: 100, r: 3 },
    { x: 300, y: 40, r: 3.75 },
    { x: 250, y: 120, r: 3 },
    { x: 60, y: 140, r: 4.5 },
    { x: 340, y: 90, r: 3.75 },
    { x: 180, y: 160, r: 3 },
    { x: 100, y: 200, r: 4.5 },
    { x: 280, y: 180, r: 3.75 },
    { x: 40, y: 230, r: 3 },
    { x: 200, y: 220, r: 4.5 },
    { x: 320, y: 200, r: 3 },
    { x: 150, y: 250, r: 3.75 },
    { x: 370, y: 150, r: 3 },
    { x: 260, y: 260, r: 4.5 },
  ]

  const connections = [
    [0, 1], [1, 2], [2, 3], [3, 4], [4, 5],
    [6, 7], [8, 9], [10, 11], [12, 13], [14, 15],
    [1, 4], [5, 8], [9, 11], [7, 10], [13, 16],
  ]

  return (
    <svg
      className="w-full h-full"
      viewBox="0 0 400 280"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {connections.map(([a, b], i) => (
        <line
          key={`line-${i}`}
          x1={points[a].x}
          y1={points[a].y}
          x2={points[b].x}
          y2={points[b].y}
          stroke="currentColor"
          strokeWidth="0.8"
          className="text-text-secondary opacity-[0.12]"
        />
      ))}
      {points.map((p, i) => (
        <circle
          key={`point-${i}`}
          cx={p.x}
          cy={p.y}
          r={p.r}
          className="text-text-secondary"
          fill="currentColor"
          opacity={0.15 + (i % 3) * 0.08}
        />
      ))}
      <circle cx={220} cy={85} r={5.25} className="text-accent" fill="currentColor" opacity={0.35} />
      <circle cx={100} cy={200} r={4.5} className="text-accent" fill="currentColor" opacity={0.35} />
    </svg>
  )
}

export function FrictionSection() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "80px",
          paddingBottom: "96px",
        }}
      >
        <div className="col-span-4 md:col-span-4 lg:col-span-6 flex flex-col gap-6">
          {lines.map((line, i) => (
            <motion.h3
              key={line}
              className="text-[28px] md:text-[32px] font-semibold text-text-primary leading-tight"
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.2, ease }}
            >
              {line}
            </motion.h3>
          ))}
          <motion.p
            className="text-[15px] text-text-secondary leading-relaxed max-w-[480px]"
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.6, ease }}
          >
            Behavioral finance research shows that emotional trading costs retail investors
            1.5–4% annually. Structure eliminates the leak.*
          </motion.p>
          <motion.span
            className="text-[11px] text-text-tertiary font-mono"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.3, delay: 0.8 }}
          >
            * Barber & Odean, 2000; Dalbar QAIB, 2023
          </motion.span>
        </div>

        {/* Abstract market noise visualization — tablet + desktop */}
        <motion.div
          className="hidden md:block md:col-start-5 md:col-span-4 lg:col-start-8 lg:col-span-5"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.3, ease }}
        >
          <MarketNoiseViz />
        </motion.div>
      </div>
    </section>
  )
}
```

Changes from original:
- SVG point radii: multiplied by 1.5x
- SVG line strokeWidth: 0.5 → 0.8
- SVG accent point opacity: 0.20/0.25 → 0.35
- SVG viz visibility: `hidden lg:block` → `hidden md:block` (show on tablet)
- SVG viz tablet grid: added `md:col-start-5 md:col-span-4`
- Left column: `md:col-span-6` → `md:col-span-4` (make room for tablet viz)
- H3 motion: `y: 20` → `x: -40` (horizontal confrontational entry)
- Body text motion: `y: 12` → `x: -40` (horizontal)
- H3 stagger: 120ms → 200ms (let each line land)
- SVG viz motion: `opacity: 0` → `opacity: 0, scale: 0.95` (grows in)
- Added citation line with asterisk reference
- Bottom padding: 80px → 96px
- Added asterisk to body text

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: All FrictionSection tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/friction-section.tsx web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat(landing): update friction section with horizontal motion, citation, SVG intensification"
```

---

### Task 3: Nav CTA Label Change

**Files:**
- Modify: `web/src/components/landing/nav-minimal.tsx`
- Modify: `web/src/components/landing/__tests__/page-assembly.test.tsx`

**Step 1: Update page assembly test to expect "Dashboard" in nav**

In `page-assembly.test.tsx`, the test currently checks for `getAllByRole("link", { name: /explore the engine/i })` with `length >= 2`. The nav CTA changes from "Explore the Engine" to "Dashboard", so update:

```tsx
describe("Landing page assembly", () => {
  it("renders all 7 sections", () => {
    render(<Page />)
    expect(screen.getByText("Structure outperforms emotion.")).toBeInTheDocument()
    expect(screen.getByText("Most investors react.")).toBeInTheDocument()
    expect(screen.getAllByText("Market Data").length).toBeGreaterThan(0)
    expect(screen.getByText("What the engine produces.")).toBeInTheDocument()
    expect(screen.getByText("Structured Allocation")).toBeInTheDocument()
    expect(screen.getByText(/not trading/i)).toBeInTheDocument()
    // Hero CTA + Final CTA both say "Explore the Engine"; nav says "Dashboard"
    const engineLinks = screen.getAllByRole("link", { name: /explore the engine/i })
    expect(engineLinks.length).toBeGreaterThanOrEqual(2)
  })

  it("renders the minimal nav", () => {
    render(<Page />)
    expect(screen.getByText("Margin Invest")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify the nav test fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/page-assembly.test.tsx --reporter=verbose`

Expected: "renders the minimal nav" FAILS — currently the nav CTA says "Explore the Engine", not "Dashboard".

**Step 3: Update nav-minimal.tsx**

Change the CTA link text from "Explore the Engine" to "Dashboard":

In `web/src/components/landing/nav-minimal.tsx`, replace:
```tsx
          <Link
            href="/dashboard"
            className="inline-block px-6 py-2 bg-accent text-white font-semibold text-[14px] rounded-[4px] hover:bg-accent-hover transition-colors"
          >
            Explore the Engine
          </Link>
```

With:
```tsx
          <Link
            href="/dashboard"
            className="inline-block px-6 py-2 bg-accent text-white font-semibold text-[14px] rounded-[4px] hover:bg-accent-hover transition-colors"
          >
            Dashboard
          </Link>
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/page-assembly.test.tsx --reporter=verbose`

Expected: All tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing/nav-minimal.tsx web/src/components/landing/__tests__/page-assembly.test.tsx
git commit -m "feat(landing): change nav CTA label to Dashboard to avoid duplicate labels"
```

---

### Task 4: Investor Positioning — Full-Screen Climax

**Files:**
- Modify: `web/src/components/landing/sections/investor-positioning.tsx`

**Step 1: Update the component**

Replace the full contents of `web/src/components/landing/sections/investor-positioning.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function InvestorPositioning() {
  return (
    <section className="min-h-screen flex items-center justify-center">
      <div className="text-center max-w-[800px] px-[8vw]">
        <motion.h2
          className="text-[32px] md:text-[40px] lg:text-[48px] font-bold text-text-primary leading-tight tracking-[-0.5px]"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease }}
        >
          You&rsquo;re not trading. You&rsquo;re operating.
        </motion.h2>
        <motion.p
          className="mt-4 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.8, ease }}
        >
          Capital allocation as a repeatable process.
        </motion.p>
      </div>
    </section>
  )
}
```

Changes from original:
- Layout: 12-col grid with left-aligned text → `min-h-screen flex items-center justify-center` centered
- Only center-aligned section on the page (intentional contrast)
- Removed `max-w-[640px]` constraint on body text; section max-width is 800px
- Body copy changed: "This platform is built for investors who treat capital allocation as a repeatable process, not a series of bets." → "Capital allocation as a repeatable process."
- H2 motion: `y: 20` fade-up → pure opacity fade, **1200ms** duration (slowest on page = climax)
- Body motion: 500ms → 600ms, delay **800ms** (appears after H2 fully settles)
- Removed outer padding div (section handles its own centering)

**Step 2: Run the existing tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: InvestorPositioning test PASSES (test checks for `/not trading/i` which is still present).

**Step 3: Run page assembly tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/page-assembly.test.tsx --reporter=verbose`

Expected: PASS.

**Step 4: Commit**

```bash
git add web/src/components/landing/sections/investor-positioning.tsx
git commit -m "feat(landing): make positioning section full-screen centered climax with 1200ms reveal"
```

---

### Task 5: Final CTA — Copy and Padding

**Files:**
- Modify: `web/src/components/landing/sections/final-cta.tsx`
- Modify: `web/src/components/landing/__tests__/sections.test.tsx` (FinalCTA tests)

**Step 1: Update the test for new CTA copy**

In `sections.test.tsx`, update the FinalCTA describe block:

```tsx
describe("FinalCTA", () => {
  it("renders the CTA heading and button", () => {
    render(<FinalCTA />)
    expect(screen.getByText("Start with structure.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /explore the engine/i })).toBeInTheDocument()
  })

  it("renders the updated CTA subtext", () => {
    render(<FinalCTA />)
    expect(screen.getByText("Run any equity through the engine.")).toBeInTheDocument()
  })

  it("renders footer links", () => {
    render(<FinalCTA />)
    expect(screen.getByRole("link", { name: /methodology/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify the subtext test fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: "renders the updated CTA subtext" FAILS.

**Step 3: Update final-cta.tsx**

Replace the full contents of `web/src/components/landing/sections/final-cta.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"
import { ButtonPrimary } from "../button-primary"
import Link from "next/link"

const ease = [0.22, 1, 0.36, 1] as const

export function FinalCTA() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "120px",
          paddingBottom: "160px",
        }}
      >
        <motion.div
          className="text-center max-w-[560px] mx-auto"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h2 className="text-[28px] md:text-[32px] font-bold text-text-primary leading-tight tracking-[-0.3px] mb-3">
            Start with structure.
          </h2>
          <p className="text-[15px] text-text-secondary mb-8">
            Run any equity through the engine.
          </p>
          <ButtonPrimary href="/dashboard">Explore the Engine</ButtonPrimary>
        </motion.div>

        <div
          className="mt-16 pt-6 border-t border-divider flex flex-col md:flex-row items-center justify-between gap-4 text-[13px] text-text-secondary"
        >
          <span>&copy; {new Date().getFullYear()} Margin Invest</span>
          <div className="flex items-center gap-6">
            <Link href="/methodology" className="hover:text-text-primary transition-colors">
              Methodology
            </Link>
            <Link href="/dashboard" className="hover:text-text-primary transition-colors">
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
```

Changes from original:
- CTA subtext: "No credit card. No commitment. See what the engine produces for any equity." → "Run any equity through the engine."
- Padding: 80/48 → 120/160

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: All FinalCTA tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/final-cta.tsx web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat(landing): update CTA copy and padding for confident operator positioning"
```

---

### Task 6: Capabilities — Alternating L/R Motion

**Files:**
- Modify: `web/src/components/landing/sections/capabilities-section.tsx`

**Step 1: Update the component**

Replace the full contents of `web/src/components/landing/sections/capabilities-section.tsx`:

```tsx
"use client"

import { motion } from "framer-motion"
import { CapabilityBlock } from "../capability-block"

const ease = [0.22, 1, 0.36, 1] as const

const capabilities = [
  {
    title: "Structured Allocation",
    description:
      "Systematic position sizing derived from composite scores, removing discretionary drift from portfolio construction.",
    tinted: false,
    className: "col-span-4 md:col-span-8 lg:col-span-5",
    marginTop: "",
    side: "left" as const,
  },
  {
    title: "Quantified Risk",
    description:
      "Every position carries a deterministic risk profile — drawdown potential, volatility rank, and sector exposure measured precisely.",
    tinted: true,
    className: "col-span-4 md:col-span-8 lg:col-start-7 lg:col-span-6",
    marginTop: "lg:mt-[48px]",
    side: "right" as const,
  },
  {
    title: "Scenario Modeling",
    description:
      "Stress-test allocations against historical regimes and hypothetical shocks before committing capital.",
    tinted: false,
    className: "col-span-4 md:col-span-8 lg:col-start-2 lg:col-span-6",
    marginTop: "lg:mt-[32px]",
    side: "left" as const,
  },
  {
    title: "Bias Reduction",
    description:
      "Eliminate recency bias, anchoring, and narrative attachment. The engine scores what the data shows, not what you hope.",
    tinted: true,
    className: "col-span-4 md:col-span-8 lg:col-start-8 lg:col-span-5",
    marginTop: "lg:mt-[64px]",
    side: "right" as const,
  },
]

export function CapabilitiesSection() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "96px",
          paddingBottom: "96px",
        }}
      >
        {capabilities.map((cap, i) => (
          <motion.div
            key={cap.title}
            className={`${cap.className} ${cap.marginTop}`}
            initial={{ opacity: 0, x: cap.side === "left" ? -30 : 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.12, ease }}
          >
            <CapabilityBlock
              title={cap.title}
              description={cap.description}
              tinted={cap.tinted}
            />
          </motion.div>
        ))}
      </div>
    </section>
  )
}
```

Changes from original:
- Added `side` property to each capability for motion direction
- Motion: `y: 20` → `x: -30` (left cards) or `x: 30` (right cards)
- Padding: 80/80 → 96/96

**Step 2: Run tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: CapabilitiesSection test PASSES (still renders four titles).

**Step 3: Commit**

```bash
git add web/src/components/landing/sections/capabilities-section.tsx
git commit -m "feat(landing): add alternating L/R motion to capabilities cards"
```

---

### Task 7: Engine Proof — Panel Entry, Count-Up Score, Animated Bars

**Files:**
- Modify: `web/src/components/landing/sections/engine-proof.tsx`

**Step 1: Update the component**

Replace the full contents of `web/src/components/landing/sections/engine-proof.tsx`:

```tsx
"use client"

import { motion, useInView, useMotionValue, useTransform, animate } from "framer-motion"
import { useRef, useEffect } from "react"

const ease = [0.22, 1, 0.36, 1] as const
const dataEase = [0.16, 1, 0.3, 1] as const

function AnimatedNumber({ value, decimals = 1 }: { value: number; decimals?: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true })
  const motionValue = useMotionValue(0)
  const display = useTransform(motionValue, (v) => v.toFixed(decimals))

  useEffect(() => {
    if (!isInView) return
    const controls = animate(motionValue, value, {
      duration: 1.2,
      ease: dataEase,
    })
    return controls.stop
  }, [isInView, motionValue, value])

  useEffect(() => {
    const unsubscribe = display.on("change", (v) => {
      if (ref.current) ref.current.textContent = v
    })
    return unsubscribe
  }, [display])

  return <span ref={ref}>0.0</span>
}

function AnimatedBar({ width, color, delay }: { width: number; color: string; delay: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true })

  return (
    <div ref={ref} className="flex-1 h-[6px] bg-bg-subtle rounded-sm overflow-hidden">
      <motion.div
        className={`h-full ${color} rounded-sm`}
        initial={{ width: "0%" }}
        animate={isInView ? { width: `${width}%` } : { width: "0%" }}
        transition={{ duration: 0.8, delay, ease: dataEase }}
      />
    </div>
  )
}

function CompositeScorePanel() {
  const barRef = useRef<HTMLDivElement>(null)
  const isInView = useInView(barRef, { once: true })

  return (
    <div className="border border-border-primary rounded-[6px] p-5 bg-bg-elevated">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-medium text-text-secondary tracking-[0.2px] uppercase">
          Composite Score
        </span>
        <span className="text-[11px] font-mono text-text-secondary">Sample Output</span>
      </div>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-[36px] font-bold text-text-primary leading-none tracking-[-1px]">
          <AnimatedNumber value={78.4} />
        </span>
        <span className="text-[13px] text-accent font-medium">/100</span>
      </div>
      <div ref={barRef} className="w-full h-2 bg-bg-subtle rounded-sm overflow-hidden">
        <motion.div
          className="h-full bg-accent rounded-sm"
          initial={{ width: "0%" }}
          animate={isInView ? { width: "78.4%" } : { width: "0%" }}
          transition={{ duration: 0.8, delay: 0.2, ease: dataEase }}
        />
      </div>
      <div className="flex justify-between mt-2 text-[11px] text-text-secondary font-mono">
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  )
}

function RiskBreakdownPanel() {
  const risks = [
    { label: "Drawdown", value: 34, color: "bg-accent" },
    { label: "Volatility", value: 52, color: "bg-text-secondary" },
    { label: "Sector Conc.", value: 18, color: "bg-accent" },
    { label: "Liquidity", value: 8, color: "bg-text-secondary" },
  ]

  return (
    <div className="border border-border-primary rounded-[6px] p-5 bg-bg-elevated">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-medium text-text-secondary tracking-[0.2px] uppercase">
          Risk Breakdown
        </span>
        <span className="text-[11px] font-mono text-accent">Low–Med</span>
      </div>
      <div className="flex flex-col gap-3">
        {risks.map((risk, i) => (
          <div key={risk.label} className="flex items-center gap-3">
            <span className="text-[12px] text-text-secondary w-20 flex-shrink-0 font-mono">
              {risk.label}
            </span>
            <AnimatedBar width={risk.value} color={risk.color} delay={0.1 + i * 0.08} />
            <span className="text-[11px] text-text-secondary font-mono w-6 text-right">
              {risk.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function FactorWeightsPanel() {
  const factors = [
    { label: "Value", weight: 25, percentile: 82 },
    { label: "Momentum", weight: 20, percentile: 71 },
    { label: "Quality", weight: 30, percentile: 88 },
    { label: "Growth", weight: 15, percentile: 62 },
    { label: "Stability", weight: 10, percentile: 79 },
  ]

  return (
    <div className="border border-border-primary rounded-[6px] p-5 bg-bg-elevated">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-medium text-text-secondary tracking-[0.2px] uppercase">
          Factor Weights
        </span>
        <span className="text-[11px] font-mono text-text-secondary">5 factors</span>
      </div>
      <div className="flex flex-col gap-2.5">
        {factors.map((f, i) => (
          <div key={f.label} className="flex items-center gap-3">
            <span className="text-[12px] text-text-secondary w-16 flex-shrink-0">
              {f.label}
            </span>
            <AnimatedBar width={f.percentile} color="bg-accent" delay={0.1 + i * 0.06} />
            <span className="text-[11px] text-text-secondary font-mono w-8 text-right">
              P{f.percentile}
            </span>
            <span className="text-[10px] text-text-secondary font-mono w-8 text-right opacity-50">
              {f.weight}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function MethodologyLink() {
  return (
    <motion.p
      className="text-[12px] text-text-tertiary mt-4 text-right font-mono"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: 0.5 }}
    >
      Deterministic output from the Margin scoring engine.{" "}
      <a href="/methodology" className="text-accent hover:underline">
        Methodology documentation &rarr;
      </a>
    </motion.p>
  )
}

export function EngineProof() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "64px",
          paddingBottom: "80px",
        }}
      >
        <motion.div
          className="col-span-4 md:col-span-4 lg:col-span-4 flex flex-col justify-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h2 className="text-[32px] md:text-[40px] lg:text-[48px] font-bold text-text-primary leading-tight tracking-[-0.5px]">
            What the engine produces.
          </h2>
          <p className="mt-4 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed">
            Every equity receives a deterministic composite score, risk profile,
            and factor-weighted breakdown — no narrative, no discretion.
          </p>
        </motion.div>

        <div className="col-span-4 md:col-start-5 md:col-span-4 lg:col-start-6 lg:col-span-7 flex flex-col gap-4">
          <motion.div
            initial={{ opacity: 0, x: 60 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0, ease }}
          >
            <CompositeScorePanel />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 60 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15, ease }}
          >
            <RiskBreakdownPanel />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 60 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3, ease }}
          >
            <FactorWeightsPanel />
          </motion.div>
          <MethodologyLink />
        </div>
      </div>
    </section>
  )
}
```

Changes from original:
- Panel entry: `y: 20` → `x: 60` (enter from right)
- Panel stagger: 120ms → 150ms
- Score: static "78.4" → `AnimatedNumber` counting up 0→78.4 over 1200ms
- All progress bars: static width → `AnimatedBar` animating from 0% to target
- Ticker label: "AAPL" → "Sample Output"
- Added `MethodologyLink` component below panels
- Left column: `lg:col-span-5` → `lg:col-span-4`
- Right column: `lg:col-start-7 lg:col-span-6` → `lg:col-start-6 lg:col-span-7`
- Padding: 80/80 → 64/80

**Step 2: Update the framer-motion mock in sections.test.tsx**

The test file's framer-motion mock needs to handle the new imports (`useInView`, `useMotionValue`, `useTransform`, `animate`). Update the mock at the top of `sections.test.tsx`:

```tsx
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    section: ({ children, ...props }: any) => (
      <section {...props}>{children}</section>
    ),
  },
  useInView: () => true,
  useMotionValue: (init: number) => {
    let value = init
    const listeners: Array<(v: string) => void> = []
    return {
      get: () => value,
      set: (v: number) => { value = v },
      on: (_event: string, cb: (v: string) => void) => {
        listeners.push(cb)
        return () => {}
      },
    }
  },
  useTransform: (_mv: any, _transform: any) => ({
    get: () => "0.0",
    on: (_event: string, _cb: any) => () => {},
  }),
  animate: () => ({ stop: () => {} }),
}))
```

**Step 3: Update the EngineProof test expectation**

In `sections.test.tsx`, update the EngineProof test to check for "Sample Output" instead of expecting ticker text, and add a methodology link check:

```tsx
describe("EngineProof", () => {
  it("renders the heading and dashboard panels", () => {
    render(<EngineProof />)
    expect(screen.getByText("What the engine produces.")).toBeInTheDocument()
    expect(screen.getAllByText(/Composite Score/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Risk Breakdown/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Factor Weights/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Sample Output/)).toBeInTheDocument()
  })

  it("renders methodology link", () => {
    render(<EngineProof />)
    expect(screen.getByRole("link", { name: /methodology documentation/i })).toBeInTheDocument()
  })
})
```

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: All tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/engine-proof.tsx web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat(landing): add count-up score, animated bars, panel slide-in, methodology link"
```

---

## Wave 2: Signature Moment (sequential dependencies)

These tasks must execute in order. Task 8 creates the shared store, Task 9 uses it in the HTML diagram, Task 10 uses it in the 3D scene, Task 11 adds the connection line draw.

---

### Task 8: Install Zustand + Create useNodePositions Store

**Files:**
- Create: `web/src/lib/stores/node-positions.ts`
- Create: `web/src/lib/stores/__tests__/node-positions.test.ts`

**Step 1: Install zustand**

Run: `cd /Users/brandon/repos/margin_invest && uv run echo skip && cd web && npm install zustand`

Note: zustand is a tiny (1.2kb) state management library with zero dependencies. It's the standard choice for R3F cross-layer state sharing.

**Step 2: Write the failing test**

Create `web/src/lib/stores/__tests__/node-positions.test.ts`:

```ts
import { describe, it, expect, beforeEach } from "vitest"
import { useNodePositions } from "../node-positions"

describe("useNodePositions store", () => {
  beforeEach(() => {
    useNodePositions.getState().clear()
  })

  it("starts with empty positions", () => {
    const { positions } = useNodePositions.getState()
    expect(Object.keys(positions)).toHaveLength(0)
  })

  it("sets a node position", () => {
    useNodePositions.getState().setPosition("node-0", { x: 100, y: 200, width: 80, height: 80 })
    const { positions } = useNodePositions.getState()
    expect(positions["node-0"]).toEqual({ x: 100, y: 200, width: 80, height: 80 })
  })

  it("sets multiple node positions independently", () => {
    const { setPosition } = useNodePositions.getState()
    setPosition("node-0", { x: 100, y: 200, width: 80, height: 80 })
    setPosition("node-1", { x: 300, y: 200, width: 80, height: 80 })
    const { positions } = useNodePositions.getState()
    expect(Object.keys(positions)).toHaveLength(2)
    expect(positions["node-1"]?.x).toBe(300)
  })

  it("clears all positions", () => {
    useNodePositions.getState().setPosition("node-0", { x: 0, y: 0, width: 0, height: 0 })
    useNodePositions.getState().clear()
    expect(Object.keys(useNodePositions.getState().positions)).toHaveLength(0)
  })
})
```

**Step 3: Run test to verify it fails**

Run: `cd web && npx vitest run src/lib/stores/__tests__/node-positions.test.ts --reporter=verbose`

Expected: FAIL — module not found.

**Step 4: Create the store**

Create `web/src/lib/stores/node-positions.ts`:

```ts
import { create } from "zustand"

export interface NodeRect {
  x: number
  y: number
  width: number
  height: number
}

interface NodePositionsState {
  positions: Record<string, NodeRect>
  setPosition: (id: string, rect: NodeRect) => void
  clear: () => void
}

export const useNodePositions = create<NodePositionsState>((set) => ({
  positions: {},
  setPosition: (id, rect) =>
    set((state) => ({
      positions: { ...state.positions, [id]: rect },
    })),
  clear: () => set({ positions: {} }),
}))
```

**Step 5: Run tests to verify they pass**

Run: `cd web && npx vitest run src/lib/stores/__tests__/node-positions.test.ts --reporter=verbose`

Expected: All 4 tests PASS.

**Step 6: Commit**

```bash
git add web/src/lib/stores/node-positions.ts web/src/lib/stores/__tests__/node-positions.test.ts web/package.json web/package-lock.json
git commit -m "feat(landing): add zustand node-positions store for HTML-to-3D sync"
```

---

### Task 9: Engine Diagram — Scroll-Driven Morph (HTML Side)

**Files:**
- Modify: `web/src/components/landing/sections/engine-diagram.tsx`
- Modify: `web/src/components/landing/__tests__/sections.test.tsx` (EngineDiagram tests)

**Step 1: Update the test to handle the ref-based diagram**

The EngineDiagram test stays the same — it checks for node labels and section label, which are unchanged. No test update needed here.

**Step 2: Update engine-diagram.tsx**

Replace the full contents of `web/src/components/landing/sections/engine-diagram.tsx`:

```tsx
"use client"

import { motion, useScroll, useTransform } from "framer-motion"
import { useRef, useEffect, useCallback } from "react"
import { useNodePositions } from "@/lib/stores/node-positions"

const ease = [0.22, 1, 0.36, 1] as const

const nodes = [
  { label: "Market Data", desc: "Real-time feeds" },
  { label: "Risk Modeling", desc: "Factor analysis" },
  { label: "Allocation Engine", desc: "Score synthesis" },
  { label: "Decision Clarity", desc: "Actionable output" },
]

function Arrow() {
  return (
    <div className="hidden lg:flex items-center justify-center flex-shrink-0 w-12">
      <svg width="48" height="12" viewBox="0 0 48 12" fill="none" className="text-border-primary">
        <line x1="0" y1="6" x2="38" y2="6" stroke="currentColor" strokeWidth="1" />
        <path d="M36 2 L44 6 L36 10" stroke="currentColor" strokeWidth="1" fill="none" />
      </svg>
    </div>
  )
}

interface DiagramNodeProps {
  node: (typeof nodes)[number]
  index: number
  morphProgress: any // MotionValue
}

function DiagramNode({ node, index, morphProgress }: DiagramNodeProps) {
  const ref = useRef<HTMLDivElement>(null)
  const setPosition = useNodePositions((s) => s.setPosition)

  const opacity = useTransform(morphProgress, [0, 0.5], [1, 0])
  const scale = useTransform(morphProgress, [0, 0.5], [1, 0.95])
  const y = useTransform(morphProgress, [0, 0.5], [0, -8])

  const reportPosition = useCallback(() => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    setPosition(`node-${index}`, {
      x: rect.x + rect.width / 2,
      y: rect.y + rect.height / 2,
      width: rect.width,
      height: rect.height,
    })
  }, [index, setPosition])

  useEffect(() => {
    reportPosition()
    window.addEventListener("resize", reportPosition)
    window.addEventListener("scroll", reportPosition)
    return () => {
      window.removeEventListener("resize", reportPosition)
      window.removeEventListener("scroll", reportPosition)
    }
  }, [reportPosition])

  return (
    <motion.div
      ref={ref}
      className="flex flex-col items-center gap-3 px-2"
      style={{ opacity, scale, y }}
    >
      <div className="w-20 h-20 border border-border-primary rounded-[6px] flex items-center justify-center bg-bg-elevated">
        <div className="w-3 h-3 rounded-full bg-accent opacity-60" />
      </div>
      <span className="text-[15px] font-semibold text-text-primary tracking-[-0.01em]">
        {node.label}
      </span>
      <span className="text-[13px] text-text-secondary">
        {node.desc}
      </span>
    </motion.div>
  )
}

export function EngineDiagram() {
  const sectionRef = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  })

  // Morph progress: 0 = HTML visible, 1 = HTML faded out (3D takes over)
  // Maps to approximately scroll range 0.35-0.45 of the full page
  const morphProgress = useTransform(scrollYProgress, [0.4, 0.7], [0, 1])

  // Arrow opacity follows morph
  const arrowOpacity = useTransform(morphProgress, [0, 0.3], [1, 0])

  return (
    <section ref={sectionRef}>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "96px",
          paddingBottom: "96px",
        }}
      >
        <motion.p
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-16"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          How the engine works
        </motion.p>

        {/* Desktop: horizontal pipeline with morph */}
        <div className="hidden lg:flex items-stretch justify-between">
          {nodes.map((node, i) => (
            <div key={node.label} className="flex items-center">
              <DiagramNode node={node} index={i} morphProgress={morphProgress} />
              {i < nodes.length - 1 && (
                <motion.div style={{ opacity: arrowOpacity }}>
                  <Arrow />
                </motion.div>
              )}
            </div>
          ))}
        </div>

        {/* Tablet: 2x2 grid (no morph on tablet) */}
        <div className="hidden md:grid md:grid-cols-2 gap-4 lg:hidden">
          {nodes.map((node, i) => (
            <motion.div
              key={node.label}
              className="flex items-center gap-4 p-4 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <div className="w-10 h-10 border border-border-primary rounded-[4px] flex items-center justify-center flex-shrink-0">
                <div className="w-2 h-2 rounded-full bg-accent opacity-60" />
              </div>
              <div>
                <span className="text-[14px] font-semibold text-text-primary block">
                  {node.label}
                </span>
                <span className="text-[12px] text-text-secondary">
                  {node.desc}
                </span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Mobile: vertical pipeline */}
        <div className="flex flex-col gap-3 md:hidden">
          {nodes.map((node, i) => (
            <motion.div
              key={node.label}
              className="flex items-center gap-4 p-4 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <div className="w-8 h-8 border border-border-primary rounded-[4px] flex items-center justify-center flex-shrink-0">
                <div className="w-1.5 h-1.5 rounded-full bg-accent opacity-60" />
              </div>
              <div>
                <span className="text-[14px] font-semibold text-text-primary block">
                  {node.label}
                </span>
                <span className="text-[12px] text-text-secondary">
                  {node.desc}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

Changes from original:
- Removed Unicode icons (`◈ △ ⬡ ◉`), replaced with small accent dot
- Node boxes: `w-16 h-16` → `w-20 h-20`
- Section label: `mb-10` → `mb-16`
- Padding: 64/64 → 96/96
- Desktop nodes wrapped in `DiagramNode` component that:
  - Reports bounding rect to `useNodePositions` store on mount/scroll/resize
  - Applies scroll-driven fade-out (opacity, scale, translateY) via `morphProgress`
- Arrows fade out with `arrowOpacity` transform
- Removed step numbers from tablet layout
- Added `useScroll` targeting the section element for morph progress
- Updated framer-motion mock in tests to handle `useScroll` and `useTransform`

**Step 3: Update the framer-motion mock to handle useScroll**

In `sections.test.tsx`, update the mock to include `useScroll`:

```tsx
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    section: ({ children, ...props }: any) => (
      <section {...props}>{children}</section>
    ),
  },
  useInView: () => true,
  useScroll: () => ({ scrollYProgress: { get: () => 0, on: () => () => {} } }),
  useMotionValue: (init: number) => {
    let value = init
    return {
      get: () => value,
      set: (v: number) => { value = v },
      on: (_event: string, _cb: any) => () => {},
    }
  },
  useTransform: (_mv: any, _input: any, _output: any) => ({
    get: () => 1,
    on: () => () => {},
  }),
  animate: () => ({ stop: () => {} }),
}))
```

Also mock the zustand store for the diagram test since jsdom doesn't have `getBoundingClientRect`:

```tsx
vi.mock("@/lib/stores/node-positions", () => ({
  useNodePositions: (selector: any) => {
    const state = {
      positions: {},
      setPosition: vi.fn(),
      clear: vi.fn(),
    }
    return typeof selector === "function" ? selector(state) : state
  },
}))
```

Place this mock right after the framer-motion mock, before the imports.

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/sections.test.tsx --reporter=verbose`

Expected: All EngineDiagram tests PASS (labels and section label still render).

**Step 5: Commit**

```bash
git add web/src/components/landing/sections/engine-diagram.tsx web/src/components/landing/__tests__/sections.test.tsx
git commit -m "feat(landing): add scroll-driven morph to engine diagram with position reporting"
```

---

### Task 10: Engine Nodes — 3D Side of the Morph

**Files:**
- Modify: `web/src/components/landing/scene/engine-nodes.tsx`

**Step 1: Update engine-nodes.tsx**

Replace the full contents of `web/src/components/landing/scene/engine-nodes.tsx`:

```tsx
"use client"

import { useRef, useEffect, useMemo } from "react"
import { useFrame, useThree } from "@react-three/fiber"
import { useScroll } from "@react-three/drei"
import * as THREE from "three"
import { useNodePositions } from "@/lib/stores/node-positions"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

const NODE_COUNT = 4
const FORMATION_POSITIONS: [number, number, number][] = [
  [-4.5, 0, 0],
  [-1.5, 0, 0],
  [1.5, 0, 0],
  [4.5, 0, 0],
]

const ACCENT_COLOR = new THREE.Color("#0E4F3A")
const ACCENT_EMISSIVE = new THREE.Color("#1C7A5A")
const INACTIVE_COLOR = new THREE.Color("#888888")

interface EngineNodesProps {
  tier: QualityTier
}

export function EngineNodes({ tier }: EngineNodesProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const scroll = useScroll()
  const { camera, size } = useThree()
  const tempObj = useMemo(() => new THREE.Object3D(), [])
  const tempColor = useMemo(() => new THREE.Color(), [])

  const geometry = useMemo(() => {
    return tier === "high"
      ? new THREE.OctahedronGeometry(0.5, 1)
      : new THREE.OctahedronGeometry(0.5, 0)
  }, [tier])

  // Initialize off-screen
  useEffect(() => {
    if (!meshRef.current) return
    for (let i = 0; i < NODE_COUNT; i++) {
      tempObj.position.set(10 + i * 2, 0, 0)
      tempObj.scale.setScalar(0.01)
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [tempObj])

  useFrame(() => {
    if (!meshRef.current) return

    const positions = useNodePositions.getState().positions

    // Morph phase: HTML fading → 3D appearing (scroll 0.35-0.45)
    const morphProgress = scroll.range(0.32, 0.13)
    // Recede phase: assembled engine moves back (scroll 0.45-0.55)
    const recedeProgress = scroll.range(0.45, 0.1)

    const activeIndex = Math.min(
      Math.floor(morphProgress * NODE_COUNT),
      NODE_COUNT - 1
    )

    for (let i = 0; i < NODE_COUNT; i++) {
      const nodeProgress = Math.max(0, Math.min(1, (morphProgress * NODE_COUNT - i) * 1.5))
      const htmlRect = positions[`node-${i}`]
      const formationTarget = FORMATION_POSITIONS[i]

      let startX = 10 + i * 2
      let startY = 0

      // If we have HTML positions, start from there (unprojected to world space)
      if (htmlRect && morphProgress < 0.8) {
        // Convert screen coords to NDC
        const ndcX = (htmlRect.x / size.width) * 2 - 1
        const ndcY = -(htmlRect.y / size.height) * 2 + 1
        // Unproject to world space at z=0
        const worldPos = new THREE.Vector3(ndcX, ndcY, 0.5).unproject(camera)
        const dir = worldPos.sub(camera.position).normalize()
        const distance = -camera.position.z / dir.z
        const pos = camera.position.clone().add(dir.multiplyScalar(distance))
        startX = pos.x
        startY = pos.y
      }

      const x = THREE.MathUtils.lerp(startX, formationTarget[0], nodeProgress)
      const y = THREE.MathUtils.lerp(startY, formationTarget[1], nodeProgress)
      const z = THREE.MathUtils.lerp(0, formationTarget[2], nodeProgress) - recedeProgress * 3

      tempObj.position.set(x, y, z)
      const scale = THREE.MathUtils.lerp(0.01, 1, nodeProgress) * (1 - recedeProgress * 0.5)
      tempObj.scale.setScalar(scale)
      tempObj.rotation.y += 0.002
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)

      tempColor.copy(i <= activeIndex ? ACCENT_COLOR : INACTIVE_COLOR)
      meshRef.current.setColorAt(i, tempColor)
    }

    meshRef.current.instanceMatrix.needsUpdate = true
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true
    }
  })

  return (
    <instancedMesh ref={meshRef} args={[geometry, undefined, NODE_COUNT]}>
      <meshStandardMaterial
        transparent
        opacity={0.85}
        roughness={0.4}
        metalness={0.1}
        emissive={ACCENT_EMISSIVE}
        emissiveIntensity={0.3}
      />
    </instancedMesh>
  )
}
```

Changes from original:
- Reads HTML positions from `useNodePositions` store
- When HTML positions available, 3D nodes start at the unprojected world-space position of each HTML box
- Lerps from HTML position to formation position based on morph progress
- Added `useThree` to access camera and viewport size for unprojection
- Scroll ranges adjusted: assemble at 0.32-0.45, recede at 0.45-0.55
- Added `emissive={ACCENT_EMISSIVE}` and `emissiveIntensity={0.3}` to material

**Step 2: Verify the landing page still renders in tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/page-assembly.test.tsx --reporter=verbose`

Expected: PASS (WebGL components are mocked via `next/dynamic` mock).

**Step 3: Commit**

```bash
git add web/src/components/landing/scene/engine-nodes.tsx
git commit -m "feat(landing): sync 3D engine nodes with HTML positions for morph effect"
```

---

### Task 11: Connection Lines — Progressive Draw Animation

**Files:**
- Modify: `web/src/components/landing/scene/connection-lines.tsx`

**Step 1: Update connection-lines.tsx**

Replace the full contents of `web/src/components/landing/scene/connection-lines.tsx`:

```tsx
"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll } from "@react-three/drei"
import * as THREE from "three"

const NODE_POSITIONS: [number, number, number][] = [
  [-4.5, 0, 0],
  [-1.5, 0, 0],
  [1.5, 0, 0],
  [4.5, 0, 0],
]

function DrawLine({ start, end, index }: {
  start: [number, number, number]
  end: [number, number, number]
  index: number
}) {
  const ref = useRef<THREE.Line>(null)
  const scroll = useScroll()

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    const positions = new Float32Array([...start, ...end])
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3))
    return geo
  }, [start, end])

  const material = useMemo(
    () =>
      new THREE.LineDashedMaterial({
        color: 0x888888,
        transparent: true,
        opacity: 0.3,
        dashSize: 100,
        gapSize: 0,
        // Total line length for dash animation
      }),
    []
  )

  useFrame(() => {
    if (!ref.current) return

    const assembleProgress = scroll.range(0.32, 0.13)
    const recedeProgress = scroll.range(0.45, 0.1)

    // Each line draws after its preceding node arrives
    // Stagger: line i starts drawing when node i+1 is ~50% materialized
    const lineDelay = (index + 0.5) / NODE_POSITIONS.length
    const drawProgress = Math.max(0, Math.min(1, (assembleProgress - lineDelay) * NODE_POSITIONS.length * 1.5))

    ref.current.visible = drawProgress > 0.01
    ref.current.position.z = -recedeProgress * 3

    // Animate via scale on x-axis (line runs along x)
    ref.current.scale.x = drawProgress
    material.opacity = drawProgress * 0.3
  })

  return <line_ ref={ref} geometry={geometry} material={material} />
}

export function ConnectionLines() {
  return (
    <group>
      {NODE_POSITIONS.slice(0, -1).map((start, i) => (
        <DrawLine
          key={i}
          start={start}
          end={NODE_POSITIONS[i + 1]}
          index={i}
        />
      ))}
    </group>
  )
}
```

Changes from original:
- Lines now draw progressively (left to right, staggered per node arrival)
- Each line appears after its preceding node materializes (~100ms stagger effect)
- Uses scale.x animation to simulate draw effect (line grows from left to right)
- Opacity animates with draw progress
- Removed the group-level visibility toggle; each line manages its own visibility
- Scroll ranges match engine-nodes.tsx (0.32-0.45 assemble, 0.45-0.55 recede)

Note: The `<line_>` JSX element is the React Three Fiber way to render `THREE.Line`. If the project uses a different R3F version that expects `<line>`, adjust accordingly. Check the existing code — the original used `<Line>` from drei. If this causes issues, fall back to:

```tsx
import { Line } from "@react-three/drei"
// and use <Line points={[start, end]} ... /> with animated opacity
```

**Step 2: Run page assembly tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/page-assembly.test.tsx --reporter=verbose`

Expected: PASS (3D components mocked).

**Step 3: Commit**

```bash
git add web/src/components/landing/scene/connection-lines.tsx
git commit -m "feat(landing): add progressive draw animation to connection lines"
```

---

## Wave 3: WebGL Intensification

---

### Task 12: Ambient Grid — Opacity Increase + Scroll Brightening

**Files:**
- Modify: `web/src/components/landing/scene/ambient-grid.tsx`

**Step 1: Update ambient-grid.tsx**

In the `AmbientGrid` component, make two changes:

1. Increase base opacity from `0.04` to `0.08`
2. Add scroll-driven brightening during the engine section (scroll 0.3-0.5 → opacity up to 0.12)

Replace the material and useFrame:

```tsx
  const material = useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color: new THREE.Color(0x888888),
        transparent: true,
        opacity: 0.08,
      }),
    []
  )

  useFrame(() => {
    if (!groupRef.current) return
    const offset = scroll.offset
    groupRef.current.position.y = offset * 2
    groupRef.current.rotation.x = -0.3 + offset * 0.1

    // Brighten during engine section (scroll 0.3-0.5)
    const engineProximity = 1 - Math.abs(offset - 0.4) * 5
    const brightening = Math.max(0, Math.min(1, engineProximity))
    material.opacity = 0.08 + brightening * 0.04
  })
```

**Step 2: Commit**

```bash
git add web/src/components/landing/scene/ambient-grid.tsx
git commit -m "feat(landing): increase grid opacity and add scroll-driven brightening"
```

---

### Task 13: Capability Cards 3D — Opacity + Edges

**Files:**
- Modify: `web/src/components/landing/scene/capability-cards-3d.tsx`

**Step 1: Update capability-cards-3d.tsx**

Two changes:
1. Increase material opacity from `0.06` to `0.15`
2. Add subtle edge borders using drei `<Edges>`

Import `Edges` from drei and update the return:

```tsx
import { useScroll, Edges } from "@react-three/drei"
```

Update the material and add Edges to the instanced mesh. Since `<Edges>` doesn't work directly on `<instancedMesh>`, we need to switch from instanced to individual meshes for the 4 cards (this is only 4 draw calls — negligible performance impact):

Replace the `CapabilityCards3D` component with individual card meshes that each have `<Edges>`:

```tsx
"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll, Edges } from "@react-three/drei"
import * as THREE from "three"

const CARD_COUNT = 4

const CARD_TARGETS: { pos: [number, number, number]; rot: [number, number, number] }[] = [
  { pos: [-3, 1.5, 0], rot: [0, 0.08, 0.03] },
  { pos: [3, 0.5, -0.3], rot: [0, -0.1, -0.02] },
  { pos: [-1, -0.8, -0.1], rot: [0, 0.05, 0.04] },
  { pos: [3.5, -2, -0.4], rot: [0, -0.07, -0.03] },
]

function CapabilityCard({ index }: { index: number }) {
  const ref = useRef<THREE.Mesh>(null)
  const scroll = useScroll()
  const target = CARD_TARGETS[index]

  useFrame(() => {
    if (!ref.current) return

    const floatIn = scroll.range(0.6, 0.15)
    const settle = scroll.range(0.75, 0.15)

    const stagger = Math.max(0, Math.min(1, (floatIn * CARD_COUNT - index) * 1.5))

    ref.current.position.set(
      THREE.MathUtils.lerp(0, target.pos[0], stagger),
      THREE.MathUtils.lerp(-10 + index * -1, target.pos[1], stagger),
      THREE.MathUtils.lerp(-2, target.pos[2], stagger)
    )

    ref.current.rotation.set(
      THREE.MathUtils.lerp(0.2, target.rot[0], stagger),
      THREE.MathUtils.lerp(0.5, target.rot[1], stagger),
      THREE.MathUtils.lerp(0.1, target.rot[2], stagger)
    )

    const scale = THREE.MathUtils.lerp(0.01, 1, stagger) * (1 - settle * 0.3)
    ref.current.scale.set(2.5 * scale, 1.5 * scale, 0.02)

    ref.current.visible = stagger > 0.01
  })

  return (
    <mesh ref={ref}>
      <planeGeometry args={[1, 1]} />
      <meshStandardMaterial
        color="#888888"
        transparent
        opacity={0.15}
        side={THREE.DoubleSide}
        roughness={0.9}
      />
      <Edges threshold={15} color="#1C7A5A" scale={1} lineWidth={0.5}>
        <lineBasicMaterial transparent opacity={0.2} />
      </Edges>
    </mesh>
  )
}

export function CapabilityCards3D() {
  return (
    <group>
      {Array.from({ length: CARD_COUNT }, (_, i) => (
        <CapabilityCard key={i} index={i} />
      ))}
    </group>
  )
}
```

Changes from original:
- InstancedMesh → 4 individual meshes (enables per-mesh Edges)
- Opacity: 6% → 15%
- Added `<Edges>` with accent color at 20% opacity, 0.5px lineWidth
- Same animation logic, refactored to per-card component

**Step 2: Commit**

```bash
git add web/src/components/landing/scene/capability-cards-3d.tsx
git commit -m "feat(landing): intensify capability cards opacity and add accent edge borders"
```

---

### Task 14: Scene Canvas — Scroll Range Adjustments

**Files:**
- Modify: `web/src/components/landing/scene/scene-canvas.tsx`

**Step 1: Verify current scroll ranges align**

The scroll ranges across all 3D components should now be consistent:
- Ambient grid: brightens at 0.3-0.5 (engine section)
- Engine nodes: assemble at 0.32-0.45, recede at 0.45-0.55
- Connection lines: draw at 0.32-0.45, recede at 0.45-0.55
- Capability cards: float in at 0.6-0.75, settle at 0.75-0.9

No changes needed to `scene-canvas.tsx` itself — the scroll ranges are configured within each component via `scroll.range()`. The `ScrollControls pages={7}` in `scene-canvas.tsx` and the `pages={7}` passed from `page.tsx` remain correct.

**Step 2: Add a light source for emissive materials**

The engine nodes now have `emissive` + `emissiveIntensity`. Verify the scene has adequate lighting. The current scene only has what's in `scene-canvas.tsx`. Check if there's an ambient light — if not, the emissive might not be visible enough.

In `scene-canvas.tsx`, add a point light inside the `<Suspense>` block if one doesn't already exist:

```tsx
<Suspense fallback={null}>
  <ambientLight intensity={0.5} />
  <pointLight position={[5, 5, 5]} intensity={0.3} />
  <ScrollControls pages={pages} damping={0.15}>
    ...
  </ScrollControls>
</Suspense>
```

Note: Only add `<pointLight>` if there isn't one already. Check the existing `scene-canvas.tsx` first. If ambient light exists, just add the point light.

**Step 3: Commit**

```bash
git add web/src/components/landing/scene/scene-canvas.tsx
git commit -m "feat(landing): add point light for emissive engine node materials"
```

---

## Wave 4: Final Verification

---

### Task 15: Run Full Test Suite + Visual Verification

**Step 1: Run all landing tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/ --reporter=verbose`

Expected: All tests PASS.

**Step 2: Run full web test suite**

Run: `cd web && npx vitest run --reporter=verbose`

Expected: All tests PASS. No regressions.

**Step 3: Start the dev server and visually verify**

Run: `cd web && npm run dev`

Verify in browser (http://localhost:3000):
1. Hero: New copy, no vertical motion on H1 (fade only), more vertical space
2. Friction: Lines arrive from left, SVG grows in, citation visible
3. Engine Diagram: Nodes have accent dots instead of Unicode, larger boxes
4. Engine Morph: On scroll, HTML boxes fade as 3D nodes materialize at their positions
5. Connection Lines: Draw progressively left-to-right
6. Engine Proof: Panels slide from right, score counts up, bars animate
7. Capabilities: Cards enter from alternating sides
8. Positioning: Full-screen, centered, slow 1200ms fade
9. CTA: New copy, more padding
10. Nav: CTA says "Dashboard"
11. WebGL grid: More visible (8% baseline), brightens during engine section
12. 3D capability cards: More visible (15%), accent edge borders
13. Engine nodes: Subtle green glow from emissive material

**Step 4: Commit all remaining changes (if any unstaged fixes)**

```bash
git add -A
git commit -m "fix: address any visual polish issues from verification pass"
```

---

## Summary

| Wave | Tasks | Dependencies |
|---|---|---|
| Wave 1 | Tasks 1-7 | Independent (parallelizable) |
| Wave 2 | Tasks 8-11 | Sequential (store → HTML → 3D → lines) |
| Wave 3 | Tasks 12-14 | Independent (parallelizable) |
| Wave 4 | Task 15 | After all others |

**Total: 15 tasks, 15 commits, 1 new dependency (zustand), 1 new file, 13 modified files.**
