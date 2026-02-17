# Methodology Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create the `/methodology` route so it renders a landing-page-style overview of the Margin scoring methodology, resolving the current 404.

**Architecture:** Server `page.tsx` at `web/src/app/methodology/` with client section components in `web/src/components/methodology/sections/`. Mirrors the homepage pattern: server component for metadata, barrel-exported client sections with framer-motion animations, same grid system and design tokens.

**Tech Stack:** Next.js 15 App Router, React 19, framer-motion, Tailwind CSS 4

---

### Task 1: Methodology Hero Section

**Files:**
- Create: `web/src/components/methodology/sections/methodology-hero.tsx`

**Step 1: Write the section component**

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

export function MethodologyHero() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "160px",
          paddingBottom: "80px",
        }}
      >
        <motion.h1
          className="text-[48px] md:text-[56px] lg:text-[72px] font-bold leading-[0.98] tracking-[-0.5px] text-text-primary max-w-[800px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2, ease }}
        >
          How Margin scores equities.
        </motion.h1>
        <motion.p
          className="mt-6 text-lg md:text-xl text-text-secondary leading-relaxed max-w-[600px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4, ease }}
        >
          A deterministic pipeline that transforms raw market data into
          composite conviction scores — no narrative, no discretion, no human
          judgment.
        </motion.p>
      </div>
    </section>
  )
}
```

**Step 2: Verify no syntax errors**

Run: `cd web && npx tsc --noEmit src/components/methodology/sections/methodology-hero.tsx 2>&1 || true`

This may fail until the barrel export exists — that's fine, just confirming the file parses.

**Step 3: Commit**

```bash
git add web/src/components/methodology/sections/methodology-hero.tsx
git commit -m "feat(web): add methodology hero section component"
```

---

### Task 2: Pipeline Section

**Files:**
- Create: `web/src/components/methodology/sections/pipeline-section.tsx`

**Step 1: Write the pipeline section**

This reuses the same 4-stage pipeline concept from the landing page `EngineDiagram` but with more descriptive text. Uses the same responsive pattern (horizontal desktop, 2x2 tablet, vertical mobile) but as a standalone component without scroll-morph effects.

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const stages = [
  {
    label: "Market Data",
    desc: "Real-time price feeds, fundamentals, and financial statements from institutional-grade sources.",
  },
  {
    label: "Elimination Filters",
    desc: "Fail-fast binary checks remove disqualified equities before any scoring begins.",
  },
  {
    label: "Factor Scoring",
    desc: "Percentile-ranked scoring across value, momentum, quality, growth, and stability factors.",
  },
  {
    label: "Composite Output",
    desc: "Weighted factor synthesis produces a single conviction score with full factor breakdown.",
  },
]

function StageIcon({ index }: { index: number }) {
  return (
    <div className="w-10 h-10 border border-border-primary rounded-[4px] flex items-center justify-center flex-shrink-0 bg-bg-elevated">
      <span className="text-[14px] font-bold text-accent font-mono">
        {String(index + 1).padStart(2, "0")}
      </span>
    </div>
  )
}

function Arrow() {
  return (
    <div className="hidden lg:flex items-center justify-center flex-shrink-0 w-8">
      <svg width="32" height="12" viewBox="0 0 32 12" fill="none" className="text-border-primary">
        <line x1="0" y1="6" x2="24" y2="6" stroke="currentColor" strokeWidth="1" />
        <path d="M22 2 L30 6 L22 10" stroke="currentColor" strokeWidth="1" fill="none" />
      </svg>
    </div>
  )
}

export function PipelineSection() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "64px",
          paddingBottom: "96px",
        }}
      >
        <motion.p
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-12"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          The Pipeline
        </motion.p>

        {/* Desktop: horizontal */}
        <div className="hidden lg:flex items-start justify-between">
          {stages.map((stage, i) => (
            <div key={stage.label} className="flex items-start">
              <motion.div
                className="flex flex-col items-center text-center max-w-[220px]"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1, ease }}
              >
                <StageIcon index={i} />
                <span className="text-[15px] font-semibold text-text-primary mt-3">
                  {stage.label}
                </span>
                <span className="text-[13px] text-text-secondary mt-2 leading-relaxed">
                  {stage.desc}
                </span>
              </motion.div>
              {i < stages.length - 1 && <Arrow />}
            </div>
          ))}
        </div>

        {/* Tablet: 2x2 grid */}
        <div className="hidden md:grid md:grid-cols-2 gap-4 lg:hidden">
          {stages.map((stage, i) => (
            <motion.div
              key={stage.label}
              className="flex items-start gap-4 p-4 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <StageIcon index={i} />
              <div>
                <span className="text-[14px] font-semibold text-text-primary block">
                  {stage.label}
                </span>
                <span className="text-[12px] text-text-secondary mt-1 block leading-relaxed">
                  {stage.desc}
                </span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Mobile: vertical stack */}
        <div className="flex flex-col gap-3 md:hidden">
          {stages.map((stage, i) => (
            <motion.div
              key={stage.label}
              className="flex items-start gap-4 p-4 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <StageIcon index={i} />
              <div>
                <span className="text-[14px] font-semibold text-text-primary block">
                  {stage.label}
                </span>
                <span className="text-[12px] text-text-secondary mt-1 block leading-relaxed">
                  {stage.desc}
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

**Step 2: Commit**

```bash
git add web/src/components/methodology/sections/pipeline-section.tsx
git commit -m "feat(web): add methodology pipeline section"
```

---

### Task 3: Factor Section

**Files:**
- Create: `web/src/components/methodology/sections/factor-section.tsx`

**Step 1: Write the factor scoring section**

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const factors = [
  {
    title: "Value",
    description:
      "Price-to-earnings, price-to-book, and free cash flow yield compared against sector peers.",
  },
  {
    title: "Momentum",
    description:
      "Relative strength across multiple timeframes, measuring sustained directional price movement.",
  },
  {
    title: "Quality",
    description:
      "Return on equity, debt ratios, and earnings consistency — indicators of operational strength.",
  },
  {
    title: "Growth",
    description:
      "Revenue and earnings growth rates, adjusted for the company's growth stage and sector norms.",
  },
  {
    title: "Stability",
    description:
      "Volatility rank, drawdown history, and beta — measuring how predictably an equity behaves.",
  },
]

export function FactorSection() {
  return (
    <section>
      <div
        className="mx-auto grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-6"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "64px",
          paddingBottom: "96px",
        }}
      >
        <motion.div
          className="col-span-4 md:col-span-8 lg:col-span-5 flex flex-col justify-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4">
            Scoring Factors
          </p>
          <h2 className="text-[32px] md:text-[40px] lg:text-[48px] font-bold text-text-primary leading-tight tracking-[-0.5px]">
            Five factors. One score.
          </h2>
          <p className="mt-4 text-[16px] md:text-[17px] lg:text-[18px] text-text-secondary leading-relaxed">
            Each equity is scored across five orthogonal factors. Scores are
            percentile-ranked within GICS sector first, then combined into a
            single composite.
          </p>
        </motion.div>

        <div className="col-span-4 md:col-span-8 lg:col-start-7 lg:col-span-6 flex flex-col gap-3">
          {factors.map((factor, i) => (
            <motion.div
              key={factor.title}
              className="p-5 border border-border-primary rounded-[6px] bg-bg-elevated"
              initial={{ opacity: 0, x: 40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-[11px] font-mono text-accent bg-accent/10 px-2 py-0.5 rounded">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="text-[16px] font-semibold text-text-primary">
                  {factor.title}
                </h3>
              </div>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {factor.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 2: Commit**

```bash
git add web/src/components/methodology/sections/factor-section.tsx
git commit -m "feat(web): add methodology factor scoring section"
```

---

### Task 4: Transparency Section

**Files:**
- Create: `web/src/components/methodology/sections/transparency-section.tsx`

**Step 1: Write the transparency/determinism section**

```tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const principles = [
  {
    label: "Deterministic",
    detail: "Same inputs always produce the same outputs. No randomness, no discretion.",
  },
  {
    label: "Sector-Neutral",
    detail: "Equities are ranked within their GICS sector before cross-sector comparison.",
  },
  {
    label: "Transparent",
    detail: "Every score includes a full factor breakdown. No black boxes.",
  },
]

export function TransparencySection() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "64px",
          paddingBottom: "96px",
        }}
      >
        <motion.div
          className="text-center max-w-[640px] mx-auto mb-12"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4">
            Principles
          </p>
          <h2 className="text-[32px] md:text-[40px] font-bold text-text-primary leading-tight tracking-[-0.3px]">
            Structure you can verify.
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-[960px] mx-auto">
          {principles.map((p, i) => (
            <motion.div
              key={p.label}
              className="p-6 border border-border-primary rounded-[6px] bg-bg-elevated text-center"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1, ease }}
            >
              <h3 className="text-[18px] font-semibold text-text-primary mb-2">
                {p.label}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {p.detail}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 2: Commit**

```bash
git add web/src/components/methodology/sections/transparency-section.tsx
git commit -m "feat(web): add methodology transparency section"
```

---

### Task 5: Methodology CTA Section

**Files:**
- Create: `web/src/components/methodology/sections/methodology-cta.tsx`

**Step 1: Write the CTA + footer section**

```tsx
"use client"

import { motion } from "framer-motion"
import { ButtonPrimary } from "@/components/landing/button-primary"
import Link from "next/link"

const ease = [0.22, 1, 0.36, 1] as const

export function MethodologyCTA() {
  return (
    <section>
      <div
        className="mx-auto"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "80px",
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
            See it in action.
          </h2>
          <p className="text-[15px] text-text-secondary mb-8">
            Run any equity through the engine and inspect the full factor breakdown.
          </p>
          <ButtonPrimary href="/dashboard">Explore the Engine</ButtonPrimary>
        </motion.div>

        <div className="mt-16 pt-6 border-t border-divider flex flex-col md:flex-row items-center justify-between gap-4 text-[13px] text-text-secondary">
          <span suppressHydrationWarning>
            &copy; {new Date().getFullYear()} Margin Invest
          </span>
          <div className="flex items-center gap-6">
            <Link href="/" className="hover:text-text-primary transition-colors">
              Home
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

**Step 2: Commit**

```bash
git add web/src/components/methodology/sections/methodology-cta.tsx
git commit -m "feat(web): add methodology CTA section"
```

---

### Task 6: Barrel Export

**Files:**
- Create: `web/src/components/methodology/index.ts`

**Step 1: Create the barrel export**

```ts
export { MethodologyHero } from "./sections/methodology-hero"
export { PipelineSection } from "./sections/pipeline-section"
export { FactorSection } from "./sections/factor-section"
export { TransparencySection } from "./sections/transparency-section"
export { MethodologyCTA } from "./sections/methodology-cta"
```

**Step 2: Commit**

```bash
git add web/src/components/methodology/index.ts
git commit -m "feat(web): add methodology barrel export"
```

---

### Task 7: Page Route

**Files:**
- Create: `web/src/app/methodology/page.tsx`

**Step 1: Create the page with metadata**

```tsx
import type { Metadata } from "next"
import { NavMinimal } from "@/components/landing/nav-minimal"
import {
  MethodologyHero,
  PipelineSection,
  FactorSection,
  TransparencySection,
  MethodologyCTA,
} from "@/components/methodology"

export const metadata: Metadata = {
  title: "Methodology | Margin Invest",
  description:
    "How Margin scores equities — a deterministic pipeline from market data to composite conviction scores, using five orthogonal factors with sector-neutral percentile ranking.",
}

export default function MethodologyPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <NavMinimal />
        <MethodologyHero />
        <PipelineSection />
        <FactorSection />
        <TransparencySection />
        <MethodologyCTA />
      </div>
    </main>
  )
}
```

**Step 2: Verify the dev server renders the page**

Run: `cd web && npx next build 2>&1 | tail -20`

Expected: Build succeeds, `/methodology` appears in the route list.

**Step 3: Commit**

```bash
git add web/src/app/methodology/page.tsx
git commit -m "feat(web): add /methodology route — resolves 404"
```

---

### Task 8: Tests

**Files:**
- Create: `web/src/components/methodology/__tests__/sections.test.tsx`

**Step 1: Write tests for all methodology sections**

Uses the same framer-motion mock pattern as `web/src/components/landing/__tests__/sections.test.tsx`.

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

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
  useMotionValue: (init: number) => ({
    get: () => init,
    set: () => {},
    on: () => () => {},
  }),
  useTransform: () => ({
    get: () => "0",
    on: () => () => {},
  }),
  useScroll: () => ({ scrollYProgress: { get: () => 0, on: () => () => {} } }),
  animate: () => ({ stop: () => {} }),
}))

import {
  MethodologyHero,
  PipelineSection,
  FactorSection,
  TransparencySection,
  MethodologyCTA,
} from "../index"

describe("MethodologyHero", () => {
  it("renders the headline", () => {
    render(<MethodologyHero />)
    expect(screen.getByText("How Margin scores equities.")).toBeInTheDocument()
  })

  it("renders the description", () => {
    render(<MethodologyHero />)
    expect(screen.getByText(/deterministic pipeline/i)).toBeInTheDocument()
  })
})

describe("PipelineSection", () => {
  it("renders the section label", () => {
    render(<PipelineSection />)
    expect(screen.getByText("The Pipeline")).toBeInTheDocument()
  })

  it("renders all four pipeline stages", () => {
    render(<PipelineSection />)
    expect(screen.getAllByText("Market Data").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Elimination Filters").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Factor Scoring").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Composite Output").length).toBeGreaterThanOrEqual(1)
  })
})

describe("FactorSection", () => {
  it("renders the heading", () => {
    render(<FactorSection />)
    expect(screen.getByText("Five factors. One score.")).toBeInTheDocument()
  })

  it("renders all five factors", () => {
    render(<FactorSection />)
    expect(screen.getByText("Value")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Growth")).toBeInTheDocument()
    expect(screen.getByText("Stability")).toBeInTheDocument()
  })
})

describe("TransparencySection", () => {
  it("renders the heading", () => {
    render(<TransparencySection />)
    expect(screen.getByText("Structure you can verify.")).toBeInTheDocument()
  })

  it("renders all three principles", () => {
    render(<TransparencySection />)
    expect(screen.getByText("Deterministic")).toBeInTheDocument()
    expect(screen.getByText("Sector-Neutral")).toBeInTheDocument()
    expect(screen.getByText("Transparent")).toBeInTheDocument()
  })
})

describe("MethodologyCTA", () => {
  it("renders the CTA heading and button", () => {
    render(<MethodologyCTA />)
    expect(screen.getByText("See it in action.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /explore the engine/i })).toBeInTheDocument()
  })

  it("renders footer links", () => {
    render(<MethodologyCTA />)
    expect(screen.getByRole("link", { name: /home/i })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument()
  })
})
```

**Step 2: Run the tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`

Expected: All tests pass (6 describe blocks, ~10 tests).

**Step 3: Commit**

```bash
git add web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "test(web): add methodology section tests"
```

---

### Task 9: Build Verification

**Step 1: Run the full web test suite**

Run: `cd web && npx vitest run`

Expected: All existing tests still pass + new methodology tests pass.

**Step 2: Run a production build**

Run: `cd web && npx next build 2>&1 | tail -30`

Expected:
- Build succeeds with no errors or warnings
- `/methodology` appears in the route output
- No hydration warnings

**Step 3: Final commit (if any adjustments needed)**

If everything passes, no additional commit needed. If fixes were required, commit them with an appropriate message.
