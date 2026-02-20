# Methodology Page Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the existing 7-section methodology page with a 10-section education-first funnel containing real engine content, named factors, dual-track conviction explanation, and conversion-oriented CTA.

**Architecture:** Replace all files under `web/src/components/methodology/sections/` and add visual components under `web/src/components/methodology/visuals/`. Update the barrel export and page route. One Recharts chart (candidate journey), all other visuals hand-built SVG + Tailwind CSS.

**Tech Stack:** Next.js 15, React, TypeScript, framer-motion, Tailwind CSS, Recharts (already installed)

**Design Doc:** `docs/plans/2026-02-19-methodology-redesign-design.md`

---

## Established Patterns

Every section component follows this exact pattern:
- `"use client"` directive (framer-motion requires it)
- `import { motion } from "framer-motion"`
- `const ease = [0.22, 1, 0.36, 1] as const`
- Section wrapper: `<section className="border-t border-border-subtle">` (first section omits `border-t`)
- Inner container with inline styles: `maxWidth: "1280px"`, `paddingLeft/Right: "8vw"`, `paddingTop/Bottom: "96px"`
- Eyebrow: `text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4`
- H2: `heading-2 text-text-primary mb-12 max-w-2xl`
- Cards: `p-6 border border-border-primary rounded-lg bg-bg-elevated`
- Body text: `text-[14px] text-text-secondary leading-relaxed`
- Stagger: `delay: i * 0.08`
- All animations: `initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}`

Tests mock framer-motion with a static passthrough (see `__tests__/sections.test.tsx`).

---

## Task 1: Delete old section files and create hero-section

**Files:**
- Delete: `web/src/components/methodology/sections/problem-section.tsx`
- Delete: `web/src/components/methodology/sections/approach-section.tsx`
- Delete: `web/src/components/methodology/sections/engine-section.tsx`
- Delete: `web/src/components/methodology/sections/outputs-section.tsx`
- Delete: `web/src/components/methodology/sections/why-section.tsx`
- Delete: `web/src/components/methodology/sections/trust-section.tsx`
- Delete: `web/src/components/methodology/sections/methodology-cta.tsx`
- Create: `web/src/components/methodology/sections/hero-section.tsx`
- Test: `web/src/components/methodology/__tests__/sections.test.tsx` (rewrite)

**Step 1: Delete all old section files**

```bash
rm web/src/components/methodology/sections/problem-section.tsx \
   web/src/components/methodology/sections/approach-section.tsx \
   web/src/components/methodology/sections/engine-section.tsx \
   web/src/components/methodology/sections/outputs-section.tsx \
   web/src/components/methodology/sections/why-section.tsx \
   web/src/components/methodology/sections/trust-section.tsx \
   web/src/components/methodology/sections/methodology-cta.tsx
```

**Step 2: Create hero-section.tsx**

```tsx
// web/src/components/methodology/sections/hero-section.tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const outcomes = [
  "Scores updated daily after market close",
  "Transparent factor breakdowns you can audit",
  "Quantified conviction levels, not subjective ratings",
  "Price targets with explicit margin of safety",
  "Position sizing tied to conviction strength",
]

const builtFor = [
  "Self-directed investors who want a repeatable process",
  "Portfolio managers who value transparency over tips",
  "Analysts who want to eliminate blind spots",
]

const notFor = [
  "Traders looking for intraday signals",
  "Anyone expecting guaranteed returns",
  "Passive index investors",
]

export function HeroSection() {
  return (
    <section>
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          How It Works
        </motion.p>

        <motion.h1
          className="heading-1 text-text-primary mb-6 max-w-3xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          From 7,000+ stocks to the ones worth your attention.
        </motion.h1>

        <motion.p
          className="text-[16px] sm:text-[17px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Margin Invest runs every US-listed equity through a deterministic pipeline of
          elimination filters, multi-factor scoring, and conviction ranking — daily.
          Same inputs, same outputs. No human judgment anywhere in the process.
        </motion.p>

        {/* Outcome bullets */}
        <motion.ul
          className="space-y-3 mb-14"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.16, ease }}
        >
          {outcomes.map((item) => (
            <li key={item} className="flex items-start gap-3">
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                className="text-accent flex-shrink-0 mt-0.5"
              >
                <path
                  d="M3 8.5L6.5 12L13 4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="text-[14px] sm:text-[15px] text-text-primary">
                {item}
              </span>
            </li>
          ))}
        </motion.ul>

        {/* Who it's for / not for */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2, ease }}
          >
            <h3 className="text-[15px] font-semibold text-text-primary mb-4">
              Built for
            </h3>
            <ul className="space-y-2">
              {builtFor.map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <span className="text-accent text-[14px] leading-relaxed">+</span>
                  <span className="text-[14px] text-text-secondary leading-relaxed">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.28, ease }}
          >
            <h3 className="text-[15px] font-semibold text-text-primary mb-4">
              Not built for
            </h3>
            <ul className="space-y-2">
              {notFor.map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <span className="text-text-tertiary text-[14px] leading-relaxed">–</span>
                  <span className="text-[14px] text-text-secondary leading-relaxed">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
```

**Step 3: Write the test for HeroSection**

Replace the entire `__tests__/sections.test.tsx` file. We'll add tests for each section as we build them.

```tsx
// web/src/components/methodology/__tests__/sections.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    h4: ({ children, ...props }: any) => <h4 {...props}>{children}</h4>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    ul: ({ children, ...props }: any) => <ul {...props}>{children}</ul>,
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

import { HeroSection } from "../sections/hero-section"

describe("HeroSection", () => {
  it("renders the H1 headline", () => {
    render(<HeroSection />)
    expect(
      screen.getByText(/From 7,000\+ stocks to the ones worth your attention/)
    ).toBeInTheDocument()
  })

  it("renders outcome bullets", () => {
    render(<HeroSection />)
    expect(screen.getByText("Scores updated daily after market close")).toBeInTheDocument()
    expect(screen.getByText("Position sizing tied to conviction strength")).toBeInTheDocument()
  })

  it("renders built-for and not-built-for cards", () => {
    render(<HeroSection />)
    expect(screen.getByText("Built for")).toBeInTheDocument()
    expect(screen.getByText("Not built for")).toBeInTheDocument()
  })
})
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: PASS for all 3 HeroSection tests

**Step 5: Commit**

```bash
git add -A web/src/components/methodology/sections/ web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): replace old sections with hero-section"
```

---

## Task 2: Create pipeline-section with pipeline diagram visual

**Files:**
- Create: `web/src/components/methodology/visuals/pipeline-diagram.tsx`
- Create: `web/src/components/methodology/sections/pipeline-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (append tests)

**Step 1: Create the pipeline diagram visual**

```tsx
// web/src/components/methodology/visuals/pipeline-diagram.tsx
"use client"

const stages = [
  { num: "01", label: "Universe", desc: "Selection", metric: "~7,000 US equities" },
  { num: "02", label: "Data", desc: "Ingestion", metric: "Daily after close" },
  { num: "03", label: "Filters", desc: "Elimination", metric: "6 independent checks" },
  { num: "04", label: "Scoring", desc: "Multi-Factor", metric: "20+ quantitative factors" },
  { num: "05", label: "Conviction", desc: "Dual-Track", metric: "Compounder & Mispricing" },
  { num: "06", label: "Output", desc: "Decisions", metric: "Cards, targets, sizing" },
]

function PipelineArrow() {
  return (
    <svg
      width="20"
      height="12"
      viewBox="0 0 20 12"
      fill="none"
      className="text-border-primary flex-shrink-0 hidden sm:block"
    >
      <line x1="0" y1="6" x2="14" y2="6" stroke="currentColor" strokeWidth="1" />
      <path d="M12 2 L18 6 L12 10" stroke="currentColor" strokeWidth="1" fill="none" />
    </svg>
  )
}

export function PipelineDiagram() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated overflow-x-auto">
      {/* Desktop: horizontal flow */}
      <div className="hidden sm:flex items-center justify-between gap-2">
        {stages.map((stage, i) => (
          <div key={stage.label} className="flex items-center gap-2">
            <div className="flex flex-col items-center text-center min-w-[90px]">
              <span className="text-[11px] font-mono font-bold text-accent">
                {stage.num}
              </span>
              <span className="text-[13px] font-semibold text-text-primary mt-1">
                {stage.label}
              </span>
              <span className="text-[11px] text-text-tertiary mt-0.5">
                {stage.desc}
              </span>
              <span className="text-[10px] font-mono text-text-tertiary mt-1">
                {stage.metric}
              </span>
            </div>
            {i < stages.length - 1 && <PipelineArrow />}
          </div>
        ))}
      </div>

      {/* Mobile: vertical flow */}
      <div className="flex flex-col gap-4 sm:hidden">
        {stages.map((stage) => (
          <div key={stage.label} className="flex items-start gap-3">
            <span className="text-[11px] font-mono font-bold text-accent w-5 flex-shrink-0 mt-0.5">
              {stage.num}
            </span>
            <div>
              <span className="text-[13px] font-semibold text-text-primary">
                {stage.label}
              </span>
              <span className="text-[11px] text-text-tertiary ml-2">
                {stage.desc}
              </span>
              <p className="text-[10px] font-mono text-text-tertiary mt-0.5">
                {stage.metric}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Step 2: Create pipeline-section.tsx**

```tsx
// web/src/components/methodology/sections/pipeline-section.tsx
"use client"

import { motion } from "framer-motion"
import { PipelineDiagram } from "../visuals/pipeline-diagram"

const ease = [0.22, 1, 0.36, 1] as const

export function PipelineSection() {
  return (
    <section className="border-t border-border-subtle">
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          The Pipeline
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          From raw data to conviction — every day.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Each scoring cycle runs the same sequence. Every stage is deterministic:
          same data in, same scores out.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.16, ease }}
        >
          <PipelineDiagram />
        </motion.div>

        <motion.p
          className="text-[12px] text-text-tertiary mt-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.24, ease }}
        >
          The pipeline runs automatically after each market close. Scores typically
          refresh within 2 hours of the closing bell.
        </motion.p>
      </div>
    </section>
  )
}
```

**Step 3: Add tests for PipelineSection to sections.test.tsx**

Append to the imports and add a new describe block:

```tsx
import { PipelineSection } from "../sections/pipeline-section"

describe("PipelineSection", () => {
  it("renders the headline", () => {
    render(<PipelineSection />)
    expect(
      screen.getByText(/From raw data to conviction/)
    ).toBeInTheDocument()
  })

  it("renders all 6 pipeline stages", () => {
    render(<PipelineSection />)
    expect(screen.getAllByText("Universe").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Filters").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Scoring").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Conviction").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Output").length).toBeGreaterThan(0)
  })
})
```

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/methodology/visuals/pipeline-diagram.tsx \
        web/src/components/methodology/sections/pipeline-section.tsx \
        web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): add pipeline section with 6-stage diagram"
```

---

## Task 3: Create universe-section

**Files:**
- Create: `web/src/components/methodology/sections/universe-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (append tests)

**Step 1: Create universe-section.tsx**

```tsx
// web/src/components/methodology/sections/universe-section.tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const cards = [
  {
    title: "What\u2019s included",
    items: [
      "~7,000+ US-domiciled equities",
      "9 sectors: Technology, Healthcare, Industrials, Energy, Consumer Cyclical, Consumer Defensive, Basic Materials, Utilities, Communication Services",
      "All market caps above liquidity minimums",
    ],
  },
  {
    title: "What\u2019s excluded",
    items: [
      "Financials \u2014 leverage-as-product breaks ROIC metrics",
      "Real Estate \u2014 REITs use different valuation frameworks",
      "OTC / Pink Sheet listings",
      "Foreign ADRs",
    ],
  },
  {
    title: "Data freshness",
    items: [
      "Full scoring cycle runs daily after market close (4:30 PM ET)",
      "Scores refresh within ~2 hours of the closing bell",
      "Each score carries a freshness label: Fresh, Stale, or Expired",
    ],
  },
]

export function UniverseSection() {
  return (
    <section className="border-t border-border-subtle">
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Universe Selection
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Every US-listed equity. No cherry-picking.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          The engine starts with the full universe of US-listed equities across all
          major exchanges — NYSE, NASDAQ, and NYSE American. Financials and Real Estate
          are excluded because their capital structures make standard profitability
          metrics unreliable. Everything else is in.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {cards.map((card, i) => (
            <motion.div
              key={card.title}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-4">
                {card.title}
              </h3>
              <ul className="space-y-2">
                {card.items.map((item) => (
                  <li
                    key={item}
                    className="text-[13px] text-text-secondary leading-relaxed"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 2: Add tests**

```tsx
import { UniverseSection } from "../sections/universe-section"

describe("UniverseSection", () => {
  it("renders the headline", () => {
    render(<UniverseSection />)
    expect(
      screen.getByText(/Every US-listed equity/)
    ).toBeInTheDocument()
  })

  it("renders all three cards", () => {
    render(<UniverseSection />)
    expect(screen.getByText(/What\u2019s included/)).toBeInTheDocument()
    expect(screen.getByText(/What\u2019s excluded/)).toBeInTheDocument()
    expect(screen.getByText("Data freshness")).toBeInTheDocument()
  })
})
```

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: PASS

**Step 4: Commit**

```bash
git add web/src/components/methodology/sections/universe-section.tsx \
        web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): add universe selection section"
```

---

## Task 4: Create filters-section with filter funnel visual

**Files:**
- Create: `web/src/components/methodology/visuals/filter-funnel.tsx`
- Create: `web/src/components/methodology/sections/filters-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (append tests)

**Step 1: Create the filter funnel visual**

```tsx
// web/src/components/methodology/visuals/filter-funnel.tsx
"use client"

const segments = [
  { label: "Universe", count: "~7,000", width: "100%" },
  { label: "Pass all filters", count: "~4,200", width: "60%" },
  { label: "High conviction", count: "~150", width: "12%" },
]

export function FilterFunnel() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      <div className="space-y-3">
        {segments.map((seg, i) => (
          <div key={seg.label} className="flex items-center gap-4">
            <div
              className="h-8 rounded-sm flex items-center px-3 transition-all"
              style={{
                width: seg.width,
                backgroundColor:
                  i === 0
                    ? "var(--color-border-primary)"
                    : i === 1
                      ? "rgba(var(--accent-rgb, 99 102 241) / 0.15)"
                      : "rgba(var(--accent-rgb, 99 102 241) / 0.3)",
              }}
            >
              <span className="text-[12px] font-mono text-text-primary whitespace-nowrap">
                {seg.count}
              </span>
            </div>
            <span className="text-[12px] text-text-secondary whitespace-nowrap">
              {seg.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Step 2: Create filters-section.tsx**

```tsx
// web/src/components/methodology/sections/filters-section.tsx
"use client"

import { motion } from "framer-motion"
import { FilterFunnel } from "../visuals/filter-funnel"

const ease = [0.22, 1, 0.36, 1] as const

const filters = [
  {
    name: "Liquidity",
    desc: "Sufficient trading volume and market cap to build a real position",
  },
  {
    name: "Earnings Quality",
    desc: "Beneish M-Score screens for signs of earnings manipulation",
  },
  {
    name: "Bankruptcy Risk",
    desc: "Altman Z-Score identifies companies in financial distress",
  },
  {
    name: "Cash Flow",
    desc: "Consistent free cash flow generation over multiple years",
  },
  {
    name: "Interest Coverage",
    desc: "Ability to service debt obligations from operating earnings",
  },
  {
    name: "Balance Sheet Health",
    desc: "Current ratio and quick ratio above sector-adjusted thresholds",
  },
]

export function FiltersSection() {
  return (
    <section className="border-t border-border-subtle">
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Elimination Filters
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Bad candidates are removed before scoring begins.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Before any stock receives a score, it must pass six independent elimination
          filters. All six run regardless of earlier failures — you see the full
          diagnostic, not just the first thing that went wrong. Roughly 40% of the
          universe fails at least one filter.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          {filters.map((filter, i) => (
            <motion.div
              key={filter.name}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-2">
                {filter.name}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {filter.desc}
              </p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <FilterFunnel />
        </motion.div>

        <motion.p
          className="text-[12px] text-text-tertiary mt-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.18, ease }}
        >
          Filter thresholds are sector-adjusted — a utility company and a tech company
          are held to different standards where appropriate.
        </motion.p>
      </div>
    </section>
  )
}
```

**Step 3: Add tests**

```tsx
import { FiltersSection } from "../sections/filters-section"

describe("FiltersSection", () => {
  it("renders the headline", () => {
    render(<FiltersSection />)
    expect(
      screen.getByText(/Bad candidates are removed before scoring begins/)
    ).toBeInTheDocument()
  })

  it("renders all six filter cards", () => {
    render(<FiltersSection />)
    expect(screen.getByText("Liquidity")).toBeInTheDocument()
    expect(screen.getByText("Earnings Quality")).toBeInTheDocument()
    expect(screen.getByText("Bankruptcy Risk")).toBeInTheDocument()
    expect(screen.getByText("Cash Flow")).toBeInTheDocument()
    expect(screen.getByText("Interest Coverage")).toBeInTheDocument()
    expect(screen.getByText("Balance Sheet Health")).toBeInTheDocument()
  })
})
```

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/methodology/visuals/filter-funnel.tsx \
        web/src/components/methodology/sections/filters-section.tsx \
        web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): add elimination filters section with funnel visual"
```

---

## Task 5: Create scoring-section with score breakdown bars visual

**Files:**
- Create: `web/src/components/methodology/visuals/score-breakdown-bars.tsx`
- Create: `web/src/components/methodology/sections/scoring-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (append tests)

**Step 1: Create the score breakdown bars visual**

```tsx
// web/src/components/methodology/visuals/score-breakdown-bars.tsx
"use client"

const bars = [
  { label: "Quality", percentile: 78, color: "bg-accent" },
  { label: "Value", percentile: 64, color: "bg-bullish" },
  { label: "Momentum", percentile: 88, color: "bg-warning" },
]

const composite = { label: "Composite", percentile: 79, color: "bg-accent" }

export function ScoreBreakdownBars() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      <div className="flex items-baseline justify-between mb-6">
        <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase">
          Example: ACME Corp
        </p>
        <span className="text-[11px] font-mono text-text-tertiary">Technology</span>
      </div>

      <div className="space-y-4">
        {bars.map((bar) => (
          <div key={bar.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[13px] font-medium text-text-primary">
                {bar.label}
              </span>
              <span className="text-[12px] font-mono text-text-tertiary">
                {bar.percentile}th
              </span>
            </div>
            <div className="h-2 rounded-full bg-bg-primary">
              <div
                className={`h-2 rounded-full ${bar.color}`}
                style={{ width: `${bar.percentile}%` }}
              />
            </div>
          </div>
        ))}

        <div className="border-t border-border-subtle pt-4 mt-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[13px] font-semibold text-text-primary">
              {composite.label}
            </span>
            <span className="text-[12px] font-mono text-text-primary">
              {composite.percentile}th
            </span>
          </div>
          <div className="h-2.5 rounded-full bg-bg-primary">
            <div
              className={`h-2.5 rounded-full ${composite.color}`}
              style={{ width: `${composite.percentile}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Create scoring-section.tsx**

```tsx
// web/src/components/methodology/sections/scoring-section.tsx
"use client"

import { motion } from "framer-motion"
import { ScoreBreakdownBars } from "../visuals/score-breakdown-bars"

const ease = [0.22, 1, 0.36, 1] as const

const pillars = [
  {
    name: "Quality",
    desc: "Measures the durability and efficiency of a business \u2014 how well it converts capital into returns, and whether those returns are real.",
    factors: [
      "ROIC-WACC Spread",
      "ROIC Stability",
      "Incremental ROIC",
      "Gross Profitability",
      "Piotroski F-Score",
      "Accrual Ratio",
      "Moat Durability",
    ],
  },
  {
    name: "Value",
    desc: "Measures what you\u2019re paying relative to what the business generates \u2014 across multiple valuation lenses to avoid single-metric traps.",
    factors: [
      "DCF Margin of Safety",
      "EV/FCF",
      "Acquirer\u2019s Multiple",
      "Owner Earnings Yield",
      "Shareholder Yield",
      "Reverse DCF Growth Gap",
      "Asset Floor",
    ],
  },
  {
    name: "Momentum",
    desc: "Measures whether the market, insiders, and institutions are confirming what the fundamentals suggest.",
    factors: [
      "Price Momentum (12\u20111 month)",
      "Standardized Unexpected Earnings",
      "Insider Cluster Score",
      "Institutional Accumulation",
      "Sentiment Score",
      "Runway Score",
    ],
  },
]

export function ScoringSection() {
  return (
    <section className="border-t border-border-subtle">
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Multi-Factor Scoring
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          20+ factors. Three pillars. Sector-neutral ranking.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Every stock that passes elimination is scored across 20+ quantitative
          factors organized into three pillars. Each factor is ranked within its own
          sector first — a tech company&apos;s profitability is compared to other tech
          companies, not to utilities. This sector-neutral approach ensures scores
          reflect genuine outlier performance among true peers.
        </motion.p>

        {/* Pillar cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {pillars.map((pillar, i) => (
            <motion.div
              key={pillar.name}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated border-t-2 border-t-accent"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[18px] font-semibold text-accent mb-3">
                {pillar.name}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed mb-4">
                {pillar.desc}
              </p>
              <div className="space-y-1">
                {pillar.factors.map((factor) => (
                  <span
                    key={factor}
                    className="block text-[12px] text-text-tertiary font-mono"
                  >
                    {factor}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </div>

        {/* How scoring works */}
        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Factor scores are converted to percentile ranks within each sector, then
          combined into a pillar average. Pillar weights adjust based on the
          company&apos;s growth stage — a high-growth company is weighted differently
          than a mature cash cow. The final composite score is re-ranked across the
          entire universe to produce a single conviction percentile.
        </motion.p>

        {/* Score breakdown visual */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
          className="max-w-lg"
        >
          <ScoreBreakdownBars />
        </motion.div>
      </div>
    </section>
  )
}
```

**Step 3: Add tests**

```tsx
import { ScoringSection } from "../sections/scoring-section"

describe("ScoringSection", () => {
  it("renders the headline", () => {
    render(<ScoringSection />)
    expect(
      screen.getByText(/20\+ factors\. Three pillars\. Sector-neutral ranking\./)
    ).toBeInTheDocument()
  })

  it("renders all three pillars", () => {
    render(<ScoringSection />)
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Value")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
  })

  it("renders named sub-factors", () => {
    render(<ScoringSection />)
    expect(screen.getByText("ROIC-WACC Spread")).toBeInTheDocument()
    expect(screen.getByText("Piotroski F-Score")).toBeInTheDocument()
    expect(screen.getByText("Insider Cluster Score")).toBeInTheDocument()
  })
})
```

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/methodology/visuals/score-breakdown-bars.tsx \
        web/src/components/methodology/sections/scoring-section.tsx \
        web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): add scoring engine section with pillar cards and breakdown bars"
```

---

## Task 6: Create conviction-section with candidate journey chart

**Files:**
- Create: `web/src/components/methodology/visuals/candidate-journey-chart.tsx`
- Create: `web/src/components/methodology/sections/conviction-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (append tests)

**Step 1: Create the candidate journey chart**

```tsx
// web/src/components/methodology/visuals/candidate-journey-chart.tsx
"use client"

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  Tooltip,
} from "recharts"

const data = [
  { month: "Jan", score: 52 },
  { month: "Feb", score: 61 },
  { month: "Mar", score: 70 },
  { month: "Apr", score: 78 },
  { month: "May", score: 85 },
  { month: "Jun", score: 91 },
]

const convictionBands = [
  { y: 98, label: "Watchlist", color: "var(--color-text-tertiary)" },
  { y: 99.3, label: "High", color: "var(--color-warning)" },
  { y: 99.95, label: "Exceptional", color: "var(--color-accent)" },
]

export function CandidateJourneyChart() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      <div className="flex items-baseline justify-between mb-6">
        <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase">
          Example candidate journey
        </p>
        <span className="text-[11px] font-mono text-text-tertiary">6-month period</span>
      </div>

      <div className="h-[240px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border-subtle)"
              vertical={false}
            />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 11, fill: "var(--color-text-tertiary)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--color-border-subtle)" }}
            />
            <YAxis
              domain={[40, 100]}
              tick={{ fontSize: 11, fill: "var(--color-text-tertiary)" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border-primary)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelStyle={{ color: "var(--color-text-secondary)" }}
              itemStyle={{ color: "var(--color-accent)" }}
            />
            {convictionBands.map((band) => (
              <ReferenceLine
                key={band.label}
                y={band.y}
                stroke={band.color}
                strokeDasharray="4 4"
                strokeOpacity={0.5}
              />
            ))}
            <Line
              type="monotone"
              dataKey="score"
              stroke="var(--color-accent)"
              strokeWidth={2}
              dot={{ r: 4, fill: "var(--color-accent)" }}
              activeDot={{ r: 6, fill: "var(--color-accent)" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-4 mt-4">
        {convictionBands.map((band) => (
          <div key={band.label} className="flex items-center gap-1.5">
            <div
              className="w-4 h-px"
              style={{
                backgroundColor: band.color,
                borderTop: `1px dashed ${band.color}`,
              }}
            />
            <span className="text-[11px] text-text-tertiary">{band.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Step 2: Create conviction-section.tsx**

```tsx
// web/src/components/methodology/sections/conviction-section.tsx
"use client"

import { motion } from "framer-motion"
import { CandidateJourneyChart } from "../visuals/candidate-journey-chart"

const ease = [0.22, 1, 0.36, 1] as const

const tracks = [
  {
    name: "Track A \u2014 Compounder",
    desc: "Identifies businesses with durable competitive advantages and strong reinvestment engines. These are companies where incremental capital deployed earns high returns \u2014 the kind of business that compounds value over long holding periods.",
    signals: [
      "Evidence of an economic moat (multiple structural signals)",
      "A reinvestment engine that converts retained earnings into growth",
      "Disciplined capital allocation",
      "A valuation that doesn\u2019t already price in perfection",
    ],
  },
  {
    name: "Track B \u2014 Mispricing",
    desc: "Identifies stocks trading at a significant discount to intrinsic value with a catalyst to close the gap. These are situations where multiple valuation methods converge on a higher value than the market price, and smart money is starting to notice.",
    signals: [
      "Multiple valuation methods agreeing the stock is cheap",
      "Downside protection (a floor on how much you can lose)",
      "A catalyst \u2014 insider buying, institutional accumulation, or earnings momentum",
      "A minimum quality floor (cheap for a reason doesn\u2019t qualify)",
    ],
  },
]

const convictionLevels = [
  {
    level: "Exceptional",
    meaning: "Strongest factor alignment across the universe",
  },
  {
    level: "High",
    meaning: "Strong multi-factor case with clear margin of safety",
  },
  {
    level: "Watchlist",
    meaning: "Promising but missing one dimension",
  },
]

export function ConvictionSection() {
  return (
    <section className="border-t border-border-subtle">
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Conviction System
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Two independent lenses. One conviction score.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Not every great investment looks the same. Some are durable compounders you
          want to hold for years. Others are deeply mispriced assets where the market
          hasn&apos;t caught up to the fundamentals. The engine runs both analyses in
          parallel — a stock can qualify through either track, or both.
        </motion.p>

        {/* Track cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          {tracks.map((track, i) => (
            <motion.div
              key={track.name}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-3">
                {track.name}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed mb-4">
                {track.desc}
              </p>
              <p className="text-[12px] font-medium text-text-tertiary uppercase tracking-wide mb-2">
                What the engine looks for
              </p>
              <ul className="space-y-1.5">
                {track.signals.map((signal) => (
                  <li
                    key={signal}
                    className="text-[13px] text-text-secondary leading-relaxed flex items-start gap-2"
                  >
                    <span className="text-accent mt-0.5 flex-shrink-0">&bull;</span>
                    {signal}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        {/* Orchestration note */}
        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          When a stock qualifies on both tracks simultaneously — a high-quality
          compounder that also happens to be mispriced — it receives the highest
          conviction level and the largest suggested position size.
        </motion.p>

        {/* Conviction levels */}
        <motion.div
          className="flex flex-wrap gap-4 mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          {convictionLevels.map((cl) => (
            <div
              key={cl.level}
              className="px-4 py-3 border border-border-primary rounded-lg bg-bg-elevated"
            >
              <span className="text-[13px] font-semibold text-accent block mb-1">
                {cl.level}
              </span>
              <span className="text-[12px] text-text-secondary">{cl.meaning}</span>
            </div>
          ))}
        </motion.div>

        {/* Candidate journey chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
          className="max-w-2xl"
        >
          <CandidateJourneyChart />
        </motion.div>

        <motion.p
          className="text-[12px] text-text-tertiary mt-4 max-w-2xl"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.18, ease }}
        >
          As a company&apos;s fundamentals improve and the market hasn&apos;t repriced,
          conviction rises. The engine tracks this progression automatically.
        </motion.p>
      </div>
    </section>
  )
}
```

**Step 3: Add tests**

```tsx
import { ConvictionSection } from "../sections/conviction-section"

// Mock recharts to avoid SSR issues in tests
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  LineChart: ({ children }: any) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  ReferenceLine: () => null,
  Tooltip: () => null,
}))

describe("ConvictionSection", () => {
  it("renders the headline", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/Two independent lenses/)
    ).toBeInTheDocument()
  })

  it("renders both track cards", () => {
    render(<ConvictionSection />)
    expect(screen.getByText(/Track A/)).toBeInTheDocument()
    expect(screen.getByText(/Track B/)).toBeInTheDocument()
  })

  it("renders conviction levels", () => {
    render(<ConvictionSection />)
    expect(screen.getByText("Exceptional")).toBeInTheDocument()
    expect(screen.getByText("High")).toBeInTheDocument()
    expect(screen.getByText("Watchlist")).toBeInTheDocument()
  })
})
```

**Note:** The `vi.mock("recharts", ...)` must be placed at the top level of the test file (after the framer-motion mock). Move it up near the top.

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/methodology/visuals/candidate-journey-chart.tsx \
        web/src/components/methodology/sections/conviction-section.tsx \
        web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): add dual-track conviction section with journey chart"
```

---

## Task 7: Create outputs-section with margin of safety band

**Files:**
- Create: `web/src/components/methodology/visuals/margin-of-safety-band.tsx`
- Create: `web/src/components/methodology/sections/outputs-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (append tests)

**Step 1: Create the margin of safety band visual**

```tsx
// web/src/components/methodology/visuals/margin-of-safety-band.tsx
"use client"

export function MarginOfSafetyBand() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated">
      <p className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-6">
        Price vs. Margin Invest Value
      </p>

      <div className="relative h-24 mb-4">
        {/* Background band zones */}
        <div className="absolute inset-y-0 left-0 right-0 flex">
          <div className="flex-[25] bg-bullish/8 rounded-l-md" />
          <div className="flex-[20] bg-accent/5" />
          <div className="flex-[30] bg-warning/5" />
          <div className="flex-[25] bg-bearish/8 rounded-r-md" />
        </div>

        {/* Zone labels */}
        <div className="absolute inset-y-0 left-0 right-0 flex items-center">
          <div className="flex-[25] flex items-center justify-center">
            <span className="text-[11px] font-medium text-bullish">Discount</span>
          </div>
          <div className="flex-[20] flex items-center justify-center">
            <span className="text-[11px] font-medium text-accent">Buy Below</span>
          </div>
          <div className="flex-[30] flex items-center justify-center">
            <span className="text-[11px] font-medium text-text-tertiary">Fair Value</span>
          </div>
          <div className="flex-[25] flex items-center justify-center">
            <span className="text-[11px] font-medium text-bearish">Overvalued</span>
          </div>
        </div>

        {/* Price markers */}
        <div className="absolute bottom-0 left-0 right-0 flex text-[10px] font-mono text-text-tertiary">
          <div className="flex-[25] text-center">$120</div>
          <div className="flex-[20] text-center">$145</div>
          <div className="flex-[30] text-center">$175</div>
          <div className="flex-[25] text-center">$210</div>
        </div>

        {/* Marker lines */}
        <div className="absolute inset-y-2 left-[25%] w-px bg-border-primary" />
        <div className="absolute inset-y-2 left-[45%] w-px bg-accent/30" />
        <div className="absolute inset-y-2 left-[75%] w-px bg-border-primary" />

        {/* Current price indicator */}
        <div className="absolute top-1 left-[32%] flex flex-col items-center">
          <span className="text-[10px] font-mono text-accent mb-0.5">$138</span>
          <div className="w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[6px] border-t-accent" />
        </div>
      </div>

      <div className="flex justify-between text-[11px] text-text-tertiary mt-2">
        <span>Buy Below</span>
        <span>Current Price</span>
        <span>Margin Invest Value</span>
        <span>Sell Target</span>
      </div>
    </div>
  )
}
```

**Step 2: Create outputs-section.tsx**

```tsx
// web/src/components/methodology/sections/outputs-section.tsx
"use client"

import { motion } from "framer-motion"
import { MarginOfSafetyBand } from "../visuals/margin-of-safety-band"

const ease = [0.22, 1, 0.36, 1] as const

const outputs = [
  {
    title: "Candidate cards",
    desc: "Each stock on your dashboard shows its conviction level, opportunity type (Compounder or Mispricing), signal (Buy / Hold / Sell), and pillar percentile bars \u2014 all at a glance. Click any card to open the full analysis.",
  },
  {
    title: "Factor breakdown",
    desc: "Drill into the exact Quality, Value, and Momentum percentile scores. See which factors are driving the conviction level and which are holding it back. Every score is auditable \u2014 no black boxes.",
  },
  {
    title: "Price target framework",
    desc: "The engine synthesizes multiple valuation methods into a single Margin Invest Value, then applies a dynamic margin of safety to produce a buy price and a sell price. You always know where the current price sits relative to the engine\u2019s assessment.",
  },
  {
    title: "Position sizing",
    desc: "Suggested allocation percentages are tied directly to conviction strength and opportunity type. Higher conviction and stronger factor alignment earn a larger suggested position. The engine does the sizing math so you don\u2019t have to.",
  },
]

export function OutputsSection() {
  return (
    <section className="border-t border-border-subtle">
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Product Outputs
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Structured outputs you can act on — not opinions to interpret.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Every scored candidate produces a set of concrete outputs designed to
          eliminate ambiguity. You see exactly why a stock scores the way it does,
          what price represents a good entry, and how much of your portfolio it warrants.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          {outputs.map((output, i) => (
            <motion.div
              key={output.title}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-2">
                {output.title}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {output.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Margin of Safety Band */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <MarginOfSafetyBand />
        </motion.div>

        <motion.p
          className="text-[14px] text-text-secondary leading-relaxed mt-6 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.15, ease }}
        >
          When the current price falls below the buy price, the signal is Buy.
          Between buy and sell, it&apos;s Hold. Above the sell target, it&apos;s Sell.
          The margin of safety widens or tightens based on how much the valuation
          methods agree.
        </motion.p>
      </div>
    </section>
  )
}
```

**Step 3: Add tests**

```tsx
import { OutputsSection } from "../sections/outputs-section"

describe("OutputsSection", () => {
  it("renders the headline", () => {
    render(<OutputsSection />)
    expect(
      screen.getByText(/Structured outputs you can act on/)
    ).toBeInTheDocument()
  })

  it("renders all four output cards", () => {
    render(<OutputsSection />)
    expect(screen.getByText("Candidate cards")).toBeInTheDocument()
    expect(screen.getByText("Factor breakdown")).toBeInTheDocument()
    expect(screen.getByText("Price target framework")).toBeInTheDocument()
    expect(screen.getByText("Position sizing")).toBeInTheDocument()
  })
})
```

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/methodology/visuals/margin-of-safety-band.tsx \
        web/src/components/methodology/sections/outputs-section.tsx \
        web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): add outputs section with margin-of-safety band"
```

---

## Task 8: Create usage-section

**Files:**
- Create: `web/src/components/methodology/sections/usage-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (append tests)

**Step 1: Create usage-section.tsx**

```tsx
// web/src/components/methodology/sections/usage-section.tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const doItems = [
  "Use candidates as a starting point for your own research",
  "Review the factor breakdown to understand why a stock scores well",
  "Compare the engine\u2019s price target to your own valuation work",
  "Use position sizing as a framework, then adjust for your risk tolerance",
  "Monitor conviction changes over time \u2014 a rising score often confirms an improving fundamental picture",
]

const dontItems = [
  "Don\u2019t treat a high conviction score as a buy recommendation",
  "Don\u2019t skip your own due diligence because the engine did quantitative work",
  "Don\u2019t ignore the limitations section below",
  "Don\u2019t assume past scoring accuracy predicts future results",
]

export function UsageSection() {
  return (
    <section className="border-t border-border-subtle">
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Responsible Usage
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-4 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          What to do — and not do — with these candidates.
        </motion.h2>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl mb-10"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.08, ease }}
        >
          Margin Invest surfaces candidates and quantifies conviction. It does not
          make decisions for you. Here&apos;s how to get the most value from the output.
        </motion.p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          {/* Do list */}
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1, ease }}
          >
            <ul className="space-y-3">
              {doItems.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    className="text-accent flex-shrink-0 mt-0.5"
                  >
                    <path
                      d="M3 8.5L6.5 12L13 4"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span className="text-[14px] text-text-secondary leading-relaxed">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Don't list */}
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.18, ease }}
          >
            <ul className="space-y-3">
              {dontItems.map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    className="text-bearish flex-shrink-0 mt-0.5"
                  >
                    <path
                      d="M4 4L12 12M12 4L4 12"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="text-[14px] text-text-secondary leading-relaxed">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>

        <motion.p
          className="text-[14px] sm:text-[15px] text-text-secondary leading-relaxed max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          The engine replaces the tedious parts of investment analysis — data gathering,
          normalization, cross-factor comparison, and ranking. The judgment call on
          whether to act is always yours.
        </motion.p>
      </div>
    </section>
  )
}
```

**Step 2: Add tests**

```tsx
import { UsageSection } from "../sections/usage-section"

describe("UsageSection", () => {
  it("renders the headline", () => {
    render(<UsageSection />)
    expect(
      screen.getByText(/What to do — and not do/)
    ).toBeInTheDocument()
  })

  it("renders do and don't items", () => {
    render(<UsageSection />)
    expect(screen.getByText(/Use candidates as a starting point/)).toBeInTheDocument()
    expect(screen.getByText(/Don\u2019t treat a high conviction score/)).toBeInTheDocument()
  })
})
```

**Step 3: Run tests, commit**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`

```bash
git add web/src/components/methodology/sections/usage-section.tsx \
        web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): add responsible usage section"
```

---

## Task 9: Create transparency-section

**Files:**
- Create: `web/src/components/methodology/sections/transparency-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (append tests)

**Step 1: Create transparency-section.tsx**

```tsx
// web/src/components/methodology/sections/transparency-section.tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const principles = [
  {
    title: "Not financial advice",
    desc: "Margin Invest is an analytical tool for informational and educational purposes. Conviction scores, price targets, and position sizing suggestions are model outputs \u2014 not recommendations to buy, sell, or hold any security. You make the decisions.",
  },
  {
    title: "Models have limits",
    desc: "The engine relies on publicly available financial data. Data can be delayed, restated, or incomplete. Quantitative models cannot capture qualitative factors like management quality, regulatory changes, or geopolitical risk. Edge cases exist in every model.",
  },
  {
    title: "Structure, not prediction",
    desc: "The engine identifies where quality, value, and momentum signals align. It does not predict future prices. A high conviction score means strong current factor alignment \u2014 not a guarantee that the stock will outperform.",
  },
]

const checklist = [
  "Does the thesis make sense to you independent of the score?",
  "Have you checked for recent news the model can\u2019t capture (M&A, litigation, regulatory)?",
  "Is the position size appropriate for your portfolio and risk tolerance?",
  "Do you have an exit plan \u2014 not just an entry plan?",
  "Are you comfortable holding through a drawdown if the fundamentals haven\u2019t changed?",
]

export function TransparencySection() {
  return (
    <section className="border-t border-border-subtle">
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Transparency
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-12 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          What this is — and what it isn&apos;t.
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {principles.map((principle, i) => (
            <motion.div
              key={principle.title}
              className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08, ease }}
            >
              <h3 className="text-[15px] font-semibold text-text-primary mb-3">
                {principle.title}
              </h3>
              <p className="text-[14px] text-text-secondary leading-relaxed">
                {principle.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Validation checklist */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <h3 className="text-[17px] font-semibold text-text-primary mb-6">
            Before acting on any candidate, verify:
          </h3>
          <ul className="space-y-3 max-w-2xl">
            {checklist.map((item) => (
              <li key={item} className="flex items-start gap-3">
                <div className="w-4 h-4 rounded border border-border-primary flex-shrink-0 mt-0.5" />
                <span className="text-[14px] text-text-secondary leading-relaxed">
                  {item}
                </span>
              </li>
            ))}
          </ul>
        </motion.div>
      </div>
    </section>
  )
}
```

**Step 2: Add tests**

```tsx
import { TransparencySection } from "../sections/transparency-section"

describe("TransparencySection", () => {
  it("renders the headline", () => {
    render(<TransparencySection />)
    expect(
      screen.getByText(/What this is — and what it isn't/)
    ).toBeInTheDocument()
  })

  it("renders all three principles", () => {
    render(<TransparencySection />)
    expect(screen.getByText("Not financial advice")).toBeInTheDocument()
    expect(screen.getByText("Models have limits")).toBeInTheDocument()
    expect(screen.getByText("Structure, not prediction")).toBeInTheDocument()
  })

  it("renders the validation checklist", () => {
    render(<TransparencySection />)
    expect(screen.getByText(/Before acting on any candidate/)).toBeInTheDocument()
    expect(screen.getByText(/Does the thesis make sense/)).toBeInTheDocument()
  })
})
```

**Step 3: Run tests, commit**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`

```bash
git add web/src/components/methodology/sections/transparency-section.tsx \
        web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): add transparency and limitations section"
```

---

## Task 10: Create cta-section

**Files:**
- Create: `web/src/components/methodology/sections/cta-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (append tests)

**Step 1: Create cta-section.tsx**

```tsx
// web/src/components/methodology/sections/cta-section.tsx
"use client"

import Link from "next/link"
import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const withoutSystem = [
  "Hours spent gathering data from multiple sources",
  "Ad-hoc screening with different criteria each time",
  "No consistent framework for comparing candidates",
  "Position sizes based on gut feel",
  "No systematic monitoring for changes",
]

const withSystem = [
  "Full universe scored daily \u2014 candidates surface automatically",
  "Same factors, same weights, same process every cycle",
  "Transparent breakdown so you know exactly why",
  "Position sizing calibrated to conviction strength",
  "Score changes flag when something needs your attention",
]

export function CTASection() {
  return (
    <section className="border-t border-border-subtle">
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
          className="text-[13px] font-medium text-text-secondary tracking-[0.5px] uppercase mb-4"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Why Pay
        </motion.p>

        <motion.h2
          className="heading-2 text-text-primary mb-10 max-w-2xl"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          Replace hours of screening with a system that runs every day.
        </motion.h2>

        {/* ROI comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <motion.div
            className="p-6 border border-border-primary rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1, ease }}
          >
            <h3 className="text-[15px] font-semibold text-text-tertiary mb-4">
              Without a system
            </h3>
            <ul className="space-y-2">
              {withoutSystem.map((item) => (
                <li
                  key={item}
                  className="text-[14px] text-text-tertiary leading-relaxed flex items-start gap-2"
                >
                  <span className="mt-0.5 flex-shrink-0">–</span>
                  {item}
                </li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            className="p-6 border border-accent/30 rounded-lg bg-bg-elevated"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.18, ease }}
          >
            <h3 className="text-[15px] font-semibold text-text-primary mb-4">
              With Margin Invest
            </h3>
            <ul className="space-y-2">
              {withSystem.map((item) => (
                <li
                  key={item}
                  className="text-[14px] text-text-secondary leading-relaxed flex items-start gap-2"
                >
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    className="text-accent flex-shrink-0 mt-0.5"
                  >
                    <path
                      d="M3 8.5L6.5 12L13 4"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  {item}
                </li>
              ))}
            </ul>
          </motion.div>
        </div>

        {/* CTA */}
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1, ease }}
        >
          <p className="text-[16px] sm:text-[17px] text-text-secondary mb-8 max-w-lg mx-auto">
            Score your first stock free. See the full factor breakdown, conviction
            score, and price target framework.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/onboarding"
              className="inline-flex items-center justify-center h-12 px-8 text-[14px] font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
            >
              Score your first stock free
            </Link>
            <Link
              href="/#pricing"
              className="inline-flex items-center justify-center h-12 px-6 text-[14px] font-medium text-text-secondary underline underline-offset-4 decoration-border-primary hover:text-text-primary transition-colors"
            >
              Compare plans
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
```

**Step 2: Add tests**

```tsx
import { CTASection } from "../sections/cta-section"

describe("CTASection", () => {
  it("renders the headline", () => {
    render(<CTASection />)
    expect(
      screen.getByText(/Replace hours of screening/)
    ).toBeInTheDocument()
  })

  it("renders both comparison cards", () => {
    render(<CTASection />)
    expect(screen.getByText("Without a system")).toBeInTheDocument()
    expect(screen.getByText("With Margin Invest")).toBeInTheDocument()
  })

  it("renders CTA links", () => {
    render(<CTASection />)
    expect(
      screen.getByRole("link", { name: /Score your first stock free/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: /Compare plans/i })
    ).toBeInTheDocument()
  })
})
```

**Step 3: Run tests, commit**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`

```bash
git add web/src/components/methodology/sections/cta-section.tsx \
        web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(methodology): add CTA section with ROI comparison"
```

---

## Task 11: Update barrel export and page route

**Files:**
- Modify: `web/src/components/methodology/index.ts`
- Modify: `web/src/app/methodology/page.tsx`

**Step 1: Update the barrel export**

Replace the entire `index.ts`:

```ts
// web/src/components/methodology/index.ts
export { HeroSection } from "./sections/hero-section"
export { PipelineSection } from "./sections/pipeline-section"
export { UniverseSection } from "./sections/universe-section"
export { FiltersSection } from "./sections/filters-section"
export { ScoringSection } from "./sections/scoring-section"
export { ConvictionSection } from "./sections/conviction-section"
export { OutputsSection } from "./sections/outputs-section"
export { UsageSection } from "./sections/usage-section"
export { TransparencySection } from "./sections/transparency-section"
export { CTASection } from "./sections/cta-section"
```

**Step 2: Update the page route**

Replace the entire `page.tsx`:

```tsx
// web/src/app/methodology/page.tsx
import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import {
  HeroSection,
  PipelineSection,
  UniverseSection,
  FiltersSection,
  ScoringSection,
  ConvictionSection,
  OutputsSection,
  UsageSection,
  TransparencySection,
  CTASection,
} from "@/components/methodology"

export const metadata: Metadata = {
  title: "How It Works | Margin Invest",
  description:
    "How Margin Invest scores every US-listed equity — a deterministic pipeline of elimination filters, multi-factor scoring across Quality, Value, and Momentum, and dual-track conviction ranking.",
}

export default function MethodologyPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />
        <HeroSection />
        <PipelineSection />
        <UniverseSection />
        <FiltersSection />
        <ScoringSection />
        <ConvictionSection />
        <OutputsSection />
        <UsageSection />
        <TransparencySection />
        <CTASection />
      </div>
    </main>
  )
}
```

**Step 3: Run all methodology tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: All tests PASS

**Step 4: Run the Next.js build to check for compile errors**

Run: `cd web && npx next build`
Expected: Build succeeds (or at minimum, the methodology page compiles without errors)

**Step 5: Commit**

```bash
git add web/src/components/methodology/index.ts \
        web/src/app/methodology/page.tsx
git commit -m "feat(methodology): wire up all 10 sections in page route"
```

---

## Task 12: Visual QA and cleanup

**Files:**
- Possibly modify any section or visual file for polish

**Step 1: Start the dev server**

Run: `cd web && npm run dev`

**Step 2: Open the methodology page in the browser**

Navigate to `http://localhost:3000/methodology`

**Step 3: Verify visually**

Check each section renders correctly:
- [ ] Hero: H1, outcome bullets, built-for/not-for cards
- [ ] Pipeline: 6-stage horizontal diagram (desktop), vertical (mobile)
- [ ] Universe: 3 cards in a row
- [ ] Filters: 6 filter cards (2-col), funnel graphic
- [ ] Scoring: 3 pillar cards with accent top border, factor names, breakdown bars
- [ ] Conviction: 2 track cards, conviction level badges, journey chart (Recharts)
- [ ] Outputs: 4 output cards, margin-of-safety band with current price indicator
- [ ] Usage: Do/Don't columns with check/x icons
- [ ] Transparency: 3 principle cards, checklist with empty checkboxes
- [ ] CTA: ROI comparison, primary CTA button

**Step 4: Fix any issues found**

Apply fixes directly to the relevant section/visual files.

**Step 5: Final commit**

```bash
git add -A web/src/components/methodology/
git commit -m "fix(methodology): visual QA polish"
```

---

## Summary

| Task | Section | Key Deliverable |
|---|---|---|
| 1 | Hero | H1, outcomes, audience cards |
| 2 | Pipeline | 6-stage diagram visual |
| 3 | Universe | 3 detail cards |
| 4 | Filters | 6 filter cards + funnel visual |
| 5 | Scoring | 3 pillar cards + score breakdown bars |
| 6 | Conviction | Dual-track cards + Recharts journey chart |
| 7 | Outputs | 4 output cards + margin-of-safety band |
| 8 | Usage | Do/Don't lists |
| 9 | Transparency | 3 principle cards + checklist |
| 10 | CTA | ROI comparison + CTA buttons |
| 11 | Wiring | Barrel export + page route |
| 12 | QA | Visual verification + polish |
