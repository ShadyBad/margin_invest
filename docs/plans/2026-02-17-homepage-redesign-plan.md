# Homepage Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the homepage from glass-morphism SaaS to institutional terminal aesthetic with 8 sections, GSAP ScrollTrigger, and real API data in the hero.

**Architecture:** Full rebuild of `web/src/components/landing/` and `web/src/app/page.tsx`. Remove WebGL shader and three.js deps. Add GSAP ScrollTrigger for scroll-linked animations. Keep Framer Motion for entrance animations. Server component fetches dashboard data for hero panel with mock fallback.

**Tech Stack:** Next.js 15 (RSC), React 19, TypeScript, Tailwind CSS v4, Framer Motion 12, GSAP ScrollTrigger (new), Vitest + Testing Library

---

## Task 1: Install GSAP and Remove Three.js Dependencies

**Files:**
- Modify: `web/package.json`

**Step 1: Install GSAP**

Run: `cd /Users/brandon/repos/margin_invest && npm install --prefix web gsap @gsap/react`

Expected: gsap and @gsap/react added to package.json dependencies

**Step 2: Remove three.js packages**

Run: `npm uninstall --prefix web @react-three/fiber @react-three/drei @react-three/postprocessing three`

Expected: four packages removed from package.json

**Step 3: Verify**

Run: `cd /Users/brandon/repos/margin_invest/web && npm ls gsap && npm ls three 2>&1 | head -5`

Expected: gsap shows installed, three shows not found

**Step 4: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "chore(web): add gsap, remove three.js dependencies"
```

---

## Task 2: Update Color Tokens and Add Terminal Card Style

**Files:**
- Modify: `web/src/app/globals.css`

**Step 1: Read the current globals.css**

Read `web/src/app/globals.css` to find the `.dark` block with color overrides.

**Step 2: Update dark mode background colors**

In the `.dark {}` block, change:
- `--color-bg-primary` from `#110F0D` → `#0A0F0D` (deeper green-black)
- `--color-bg-elevated` from `#1A1714` → `#111A15` (dark emerald tint)
- `--color-bg-subtle` from `#211E1A` → `#1A2420` (emerald-tinted subtle)

**Step 3: Add gold highlight token**

Add to the `.dark {}` block:
```css
--color-gold-highlight: #C9A84C;
```

And in the light `@theme` block:
```css
--color-gold-highlight: #8B7330;
```

**Step 4: Add terminal card CSS class**

After the `.glass-elevated` class definition, add:

```css
.terminal-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-subtle);
  border-radius: 12px;
}

.terminal-card-accent {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-accent);
  border-radius: 12px;
}
```

**Step 5: Commit**

```bash
git add web/src/app/globals.css
git commit -m "style(web): update dark tokens for terminal aesthetic, add terminal-card class"
```

---

## Task 3: Create Hero Candidate Panel Component

**Files:**
- Create: `web/src/components/landing/hero-candidate-panel.tsx`
- Create: `web/src/components/landing/__tests__/hero-candidate-panel.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/landing/__tests__/hero-candidate-panel.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  useInView: () => true,
}))

import { HeroCandidatePanel } from "../hero-candidate-panel"

const mockPick = {
  ticker: "AAPL",
  name: "Apple Inc.",
  actual_price: 173.22,
  buy_price: 214.9,
  margin_of_safety: 0.194,
  composite_percentile: 83,
  quality_percentile: 85,
  value_percentile: 62,
  momentum_percentile: 71,
  scored_at: "2026-02-17T04:02:00Z",
  sector: "Technology",
}

describe("HeroCandidatePanel", () => {
  it("renders ticker and price", () => {
    render(<HeroCandidatePanel pick={mockPick} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText(/173\.22/)).toBeInTheDocument()
  })

  it("renders conviction score", () => {
    render(<HeroCandidatePanel pick={mockPick} />)
    expect(screen.getByText(/83/)).toBeInTheDocument()
  })

  it("renders factor bars", () => {
    render(<HeroCandidatePanel pick={mockPick} />)
    expect(screen.getByText("Quality")).toBeInTheDocument()
    expect(screen.getByText("Value")).toBeInTheDocument()
    expect(screen.getByText("Momentum")).toBeInTheDocument()
  })

  it("renders timestamp", () => {
    render(<HeroCandidatePanel pick={mockPick} />)
    expect(screen.getByText(/last recalculated/i)).toBeInTheDocument()
  })

  it("renders with mock data when no pick provided", () => {
    render(<HeroCandidatePanel pick={null} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/hero-candidate-panel.test.tsx`

Expected: FAIL — module not found

**Step 3: Write the component**

```tsx
// web/src/components/landing/hero-candidate-panel.tsx
"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"

interface PickData {
  ticker: string
  name: string
  actual_price: number | null
  buy_price: number | null
  margin_of_safety: number | null
  composite_percentile: number
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  scored_at: string | null
  sector: string | null
}

const MOCK_PICK: PickData = {
  ticker: "AAPL",
  name: "Apple Inc.",
  actual_price: 173.22,
  buy_price: 214.9,
  margin_of_safety: 0.194,
  composite_percentile: 83,
  quality_percentile: 85,
  value_percentile: 62,
  momentum_percentile: 71,
  scored_at: new Date().toISOString(),
  sector: "Technology",
}

const ease = [0.22, 1, 0.36, 1] as const

function FactorBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-tertiary w-20 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-accent rounded-full"
          initial={{ width: 0 }}
          whileInView={{ width: `${value}%` }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease }}
        />
      </div>
      <span className="font-mono text-xs text-text-secondary w-8 text-right">{value}</span>
    </div>
  )
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return "—"
  const d = new Date(iso)
  const h = d.getHours().toString().padStart(2, "0")
  const m = d.getMinutes().toString().padStart(2, "0")
  return `Last recalculated ${h}:${m} EST`
}

interface HeroCandidatePanelProps {
  pick: PickData | null
}

export function HeroCandidatePanel({ pick }: HeroCandidatePanelProps) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })
  const data = pick ?? MOCK_PICK

  const mosPercent = data.margin_of_safety != null
    ? `${(data.margin_of_safety * 100).toFixed(1)}%`
    : "—"

  return (
    <motion.div
      ref={ref}
      className="terminal-card p-6 md:p-8 w-full max-w-sm"
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: 0.3, ease }}
    >
      {/* Header */}
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <span className="font-mono text-lg font-semibold text-text-primary">{data.ticker}</span>
          <span className="ml-2 text-xs text-text-tertiary">{data.name}</span>
        </div>
        {data.sector && (
          <span className="text-[10px] uppercase tracking-widest text-text-tertiary">{data.sector}</span>
        )}
      </div>

      {/* Price row */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">Current</p>
          <p className="font-mono text-xl text-text-primary">${data.actual_price?.toFixed(2) ?? "—"}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">Target</p>
          <p className="font-mono text-xl text-text-primary">${data.buy_price?.toFixed(2) ?? "—"}</p>
        </div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">Margin of Safety</p>
          <p className="font-mono text-lg text-accent">{mosPercent}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-text-tertiary mb-1">Conviction Score</p>
          <p className="font-mono text-lg text-text-primary">{data.composite_percentile}</p>
        </div>
      </div>

      {/* Factor bars */}
      <div className="space-y-2.5 mb-6">
        <FactorBar label="Quality" value={data.quality_percentile} />
        <FactorBar label="Value" value={data.value_percentile} />
        <FactorBar label="Momentum" value={data.momentum_percentile} />
      </div>

      {/* Timestamp */}
      <p className="font-mono text-[10px] text-text-tertiary text-right">
        {formatTimestamp(data.scored_at)}
      </p>
    </motion.div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/hero-candidate-panel.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/hero-candidate-panel.tsx web/src/components/landing/__tests__/hero-candidate-panel.test.tsx
git commit -m "feat(web): add HeroCandidatePanel component with mock fallback"
```

---

## Task 4: Create Hero Section Component

**Files:**
- Create: `web/src/components/landing/hero-section.tsx`
- Create: `web/src/components/landing/__tests__/hero-section.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/landing/__tests__/hero-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    section: ({ children, ...props }: any) => <section {...props}>{children}</section>,
  },
  useInView: () => true,
}))

import { HeroSection } from "../hero-section"

describe("HeroSection", () => {
  it("renders headline", () => {
    render(<HeroSection pick={null} />)
    expect(screen.getByText(/Conviction/)).toBeInTheDocument()
    expect(screen.getByText(/Engineered/)).toBeInTheDocument()
  })

  it("renders subheadline", () => {
    render(<HeroSection pick={null} />)
    expect(screen.getByText(/deterministic capital allocation/i)).toBeInTheDocument()
  })

  it("renders primary CTA linking to dashboard", () => {
    render(<HeroSection pick={null} />)
    const cta = screen.getByRole("link", { name: /open the dashboard/i })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("renders secondary CTA linking to methodology", () => {
    render(<HeroSection pick={null} />)
    const cta = screen.getByRole("link", { name: /see the methodology/i })
    expect(cta).toHaveAttribute("href", "/methodology")
  })

  it("renders candidate panel", () => {
    render(<HeroSection pick={null} />)
    // Mock fallback should show AAPL
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/hero-section.test.tsx`

Expected: FAIL

**Step 3: Write the component**

```tsx
// web/src/components/landing/hero-section.tsx
"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { HeroCandidatePanel } from "./hero-candidate-panel"

const ease = [0.22, 1, 0.36, 1] as const

const words = ["Conviction.", "Engineered."]

interface HeroSectionProps {
  pick: Parameters<typeof HeroCandidatePanel>[0]["pick"]
}

export function HeroSection({ pick }: HeroSectionProps) {
  return (
    <section
      id="hero"
      className="min-h-screen flex items-center justify-center px-6"
      style={{
        background: "linear-gradient(180deg, #0A0F0D 0%, #0D1510 100%)",
      }}
    >
      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
        {/* Left: headline + CTAs */}
        <div>
          <h1 className="font-display text-5xl md:text-7xl lg:text-[88px] leading-[0.95] tracking-[-0.04em] text-text-primary mb-6">
            {words.map((word, i) => (
              <motion.span
                key={word}
                className="inline-block mr-4"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: i * 0.12, ease }}
              >
                {word}
              </motion.span>
            ))}
          </h1>

          <motion.p
            className="text-lg text-text-secondary max-w-md mb-10 leading-relaxed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4, ease }}
          >
            A deterministic capital allocation system that replaces narrative with structure.
          </motion.p>

          <motion.div
            className="flex items-center gap-6"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6, ease }}
          >
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center h-12 px-8 rounded-lg bg-accent text-white text-sm font-medium tracking-wide transition-colors hover:bg-accent-hover"
            >
              Open the Dashboard
            </Link>
            <Link
              href="/methodology"
              className="text-sm font-medium text-text-secondary underline underline-offset-4 decoration-border-primary hover:text-text-primary transition-colors"
            >
              See the Methodology
            </Link>
          </motion.div>
        </div>

        {/* Right: candidate panel */}
        <div className="flex justify-center lg:justify-end">
          <HeroCandidatePanel pick={pick} />
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/hero-section.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/hero-section.tsx web/src/components/landing/__tests__/hero-section.test.tsx
git commit -m "feat(web): add HeroSection with split layout and candidate panel"
```

---

## Task 5: Create Problem Section

**Files:**
- Create: `web/src/components/landing/problem-section.tsx`
- Create: `web/src/components/landing/__tests__/problem-section.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/landing/__tests__/problem-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    li: ({ children, ...props }: any) => <li {...props}>{children}</li>,
    ul: ({ children, ...props }: any) => <ul {...props}>{children}</ul>,
  },
}))

import { ProblemSection } from "../problem-section"

describe("ProblemSection", () => {
  it("renders headline", () => {
    render(<ProblemSection />)
    expect(screen.getByText(/most investors react/i)).toBeInTheDocument()
  })

  it("renders all four problems", () => {
    render(<ProblemSection />)
    expect(screen.getByText(/filtering discipline/i)).toBeInTheDocument()
    expect(screen.getByText(/factor weighting/i)).toBeInTheDocument()
    expect(screen.getByText(/sector normalization/i)).toBeInTheDocument()
    expect(screen.getByText(/correlation awareness/i)).toBeInTheDocument()
  })

  it("renders closer line", () => {
    render(<ProblemSection />)
    expect(screen.getByText(/replaces guesswork/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/problem-section.test.tsx`

Expected: FAIL

**Step 3: Write the component**

```tsx
// web/src/components/landing/problem-section.tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const problems = [
  "No filtering discipline",
  "No factor weighting memory",
  "No sector normalization",
  "No portfolio-level correlation awareness",
]

export function ProblemSection() {
  return (
    <section id="problem" className="py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <motion.h2
          className="font-display text-4xl md:text-5xl text-text-primary mb-10"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease }}
        >
          Most investors react. Few operate with structure.
        </motion.h2>

        <ul className="space-y-4 mb-10">
          {problems.map((problem, i) => (
            <motion.li
              key={problem}
              className="text-lg text-text-secondary flex items-start gap-3"
              initial={{ opacity: 0, x: -10 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.1, ease }}
            >
              <span className="text-text-tertiary mt-1">—</span>
              {problem}
            </motion.li>
          ))}
        </ul>

        <motion.p
          className="text-lg text-text-primary font-medium"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5, ease }}
        >
          Margin Invest replaces guesswork with a repeatable system.
        </motion.p>

        <div className="mt-16 border-b border-border-subtle" />
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/problem-section.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/problem-section.tsx web/src/components/landing/__tests__/problem-section.test.tsx
git commit -m "feat(web): add ProblemSection component"
```

---

## Task 6: Create Pipeline Diagram Component

**Files:**
- Create: `web/src/components/landing/pipeline-diagram.tsx`
- Create: `web/src/components/landing/__tests__/pipeline-diagram.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/landing/__tests__/pipeline-diagram.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

import { PipelineDiagram } from "../pipeline-diagram"

describe("PipelineDiagram", () => {
  it("renders all 6 pipeline stages", () => {
    render(<PipelineDiagram activeStage={0} />)
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("FILTER")).toBeInTheDocument()
    expect(screen.getByText("FACTOR MODEL")).toBeInTheDocument()
    expect(screen.getByText("NORMALIZE")).toBeInTheDocument()
    expect(screen.getByText("SCORE")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()
  })

  it("highlights the active stage", () => {
    const { container } = render(<PipelineDiagram activeStage={2} />)
    const stages = container.querySelectorAll("[data-pipeline-stage]")
    expect(stages[2]).toHaveAttribute("data-active", "true")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/pipeline-diagram.test.tsx`

Expected: FAIL

**Step 3: Write the component**

```tsx
// web/src/components/landing/pipeline-diagram.tsx
"use client"

import { motion } from "framer-motion"

const STAGES = ["DATA", "FILTER", "FACTOR MODEL", "NORMALIZE", "SCORE", "PORTFOLIO"]

interface PipelineDiagramProps {
  activeStage: number
}

export function PipelineDiagram({ activeStage }: PipelineDiagramProps) {
  return (
    <div className="w-full overflow-x-auto py-4">
      <div className="flex items-center justify-center gap-1 md:gap-2 min-w-[600px] px-4">
        {STAGES.map((stage, i) => (
          <div key={stage} className="flex items-center">
            <motion.div
              data-pipeline-stage
              data-active={i <= activeStage ? "true" : "false"}
              className={`px-3 py-2 rounded-md font-mono text-[10px] md:text-xs tracking-wider transition-all duration-500 ${
                i <= activeStage
                  ? "bg-accent/20 text-accent border border-accent/40 shadow-[0_0_12px_rgba(26,122,90,0.15)]"
                  : "bg-bg-elevated text-text-tertiary border border-border-subtle"
              }`}
            >
              {stage}
            </motion.div>
            {i < STAGES.length - 1 && (
              <div className="flex items-center mx-1">
                <div
                  className={`h-px w-4 md:w-8 transition-colors duration-500 ${
                    i < activeStage ? "bg-accent/60" : "bg-border-subtle"
                  }`}
                />
                <span
                  className={`text-[8px] transition-colors duration-500 ${
                    i < activeStage ? "text-accent/60" : "text-border-subtle"
                  }`}
                >
                  ▸
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/pipeline-diagram.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/pipeline-diagram.tsx web/src/components/landing/__tests__/pipeline-diagram.test.tsx
git commit -m "feat(web): add PipelineDiagram component with active stage highlighting"
```

---

## Task 7: Create Engine Card Component

**Files:**
- Create: `web/src/components/landing/engine-card.tsx`
- Create: `web/src/components/landing/__tests__/engine-card.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/landing/__tests__/engine-card.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}))

import { EngineCard } from "../engine-card"

describe("EngineCard", () => {
  it("renders title and subtitle", () => {
    render(<EngineCard title="Raw Market Signal" subtitle="Input" description="Test desc" />)
    expect(screen.getByText("Raw Market Signal")).toBeInTheDocument()
    expect(screen.getByText("Input")).toBeInTheDocument()
  })

  it("renders description", () => {
    render(<EngineCard title="Test" subtitle="Sub" description="Some description text" />)
    expect(screen.getByText("Some description text")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/engine-card.test.tsx`

Expected: FAIL

**Step 3: Write the component**

```tsx
// web/src/components/landing/engine-card.tsx
"use client"

import { motion, type MotionStyle } from "framer-motion"

interface EngineCardProps {
  title: string
  subtitle: string
  description: string
  style?: MotionStyle
}

export function EngineCard({ title, subtitle, description, style }: EngineCardProps) {
  return (
    <motion.div
      className="w-[320px] flex-shrink-0 terminal-card p-6 md:p-8"
      style={style}
    >
      <p className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-3">
        {subtitle}
      </p>
      <h3 className="font-display text-2xl md:text-3xl leading-tight text-text-primary mb-3">
        {title}
      </h3>
      <p className="text-sm text-text-secondary leading-relaxed">
        {description}
      </p>
    </motion.div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/engine-card.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/engine-card.tsx web/src/components/landing/__tests__/engine-card.test.tsx
git commit -m "feat(web): add EngineCard component with terminal styling"
```

---

## Task 8: Create Engine Section with GSAP ScrollTrigger

This is the most complex component. It combines the pipeline diagram with counter-scrolling card rows driven by GSAP.

**Files:**
- Create: `web/src/components/landing/engine-section.tsx`
- Create: `web/src/components/landing/__tests__/engine-section.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/landing/__tests__/engine-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
}))

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn() },
  gsap: { registerPlugin: vi.fn(), to: vi.fn() },
}))

vi.mock("gsap/ScrollTrigger", () => ({
  default: {},
  ScrollTrigger: {},
}))

import { EngineSection } from "../engine-section"

describe("EngineSection", () => {
  it("renders pipeline diagram with all stages", () => {
    render(<EngineSection />)
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()
  })

  it("renders all 10 engine cards", () => {
    render(<EngineSection />)
    expect(screen.getByText("Raw Market Signal")).toBeInTheDocument()
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
    expect(screen.getByText("Multi-Factor Ranking")).toBeInTheDocument()
    expect(screen.getByText("Portfolio Correlation Mapping")).toBeInTheDocument()
  })

  it("renders two card rows on desktop", () => {
    const { container } = render(<EngineSection />)
    const rows = container.querySelectorAll("[data-card-row]")
    expect(rows.length).toBeGreaterThanOrEqual(2)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/engine-section.test.tsx`

Expected: FAIL

**Step 3: Write the component**

```tsx
// web/src/components/landing/engine-section.tsx
"use client"

import { useRef, useState, useEffect } from "react"
import { PipelineDiagram } from "./pipeline-diagram"
import { EngineCard } from "./engine-card"

const topRowCards = [
  { title: "Raw Market Signal", subtitle: "Input", description: "Earnings transcripts, SEC filings, price targets, institutional flows — hundreds of data points per ticker, gathered and normalized." },
  { title: "Data Integrity + Normalization", subtitle: "Input", description: "Standardize across reporting periods, currencies, and accounting methods. Clean data is the foundation of deterministic scoring." },
  { title: "Elimination Filters", subtitle: "Gating", description: "Penny stocks, delistings, insufficient data — fail-fast filters eliminate noise before scoring begins. Only investable assets proceed." },
  { title: "Survivorship Bias Control", subtitle: "Gating", description: "Delisted and acquired companies remain in historical datasets. No retroactive cleaning of failures from the record." },
  { title: "Liquidity Thresholding", subtitle: "Gating", description: "Minimum volume and market cap requirements ensure every scored asset is actually tradeable at institutional scale." },
]

const bottomRowCards = [
  { title: "Multi-Factor Ranking", subtitle: "Scoring", description: "Five factors — valuation, quality, momentum, growth, sentiment — each scored independently against sector peers." },
  { title: "Percentile Normalization", subtitle: "Scoring", description: "Raw scores converted to percentile ranks (0-100) within GICS sector. Cross-factor comparison becomes meaningful." },
  { title: "Conviction Score Synthesis", subtitle: "Output", description: "Weighted combination of factor percentiles produces a single composite conviction score. Growth stage adjusts weights automatically." },
  { title: "Sector-Neutral Construction", subtitle: "Output", description: "Rank within sector first, then combine. A 60th-percentile bank is compared to banks, not tech stocks." },
  { title: "Portfolio Correlation Mapping", subtitle: "Output", description: "Identify correlated positions across your portfolio. Diversification measured, not assumed." },
]

export function EngineSection() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const topRowRef = useRef<HTMLDivElement>(null)
  const bottomRowRef = useRef<HTMLDivElement>(null)
  const [activeStage, setActiveStage] = useState(0)

  useEffect(() => {
    let gsapModule: any
    let ScrollTriggerModule: any

    async function initGSAP() {
      try {
        gsapModule = (await import("gsap")).default
        ScrollTriggerModule = (await import("gsap/ScrollTrigger")).default
        gsapModule.registerPlugin(ScrollTriggerModule)

        if (!sectionRef.current || !topRowRef.current || !bottomRowRef.current) return

        // Top row scrolls left
        gsapModule.to(topRowRef.current, {
          x: "-30%",
          ease: "none",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top bottom",
            end: "bottom top",
            scrub: 1,
          },
        })

        // Bottom row scrolls right
        gsapModule.to(bottomRowRef.current, {
          x: "30%",
          ease: "none",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top bottom",
            end: "bottom top",
            scrub: 1,
          },
        })

        // Pipeline stage highlighting
        ScrollTriggerModule.create({
          trigger: sectionRef.current,
          start: "top center",
          end: "bottom center",
          onUpdate: (self: any) => {
            const progress = self.progress
            const stage = Math.min(5, Math.floor(progress * 6))
            setActiveStage(stage)
          },
        })
      } catch {
        // GSAP not available — graceful degradation
      }
    }

    initGSAP()

    return () => {
      if (ScrollTriggerModule) {
        ScrollTriggerModule.getAll?.().forEach((t: any) => t.kill())
      }
    }
  }, [])

  return (
    <section ref={sectionRef} id="engine" className="relative py-24 overflow-hidden">
      {/* Sticky pipeline diagram */}
      <div className="sticky top-20 z-10 bg-bg-primary/80 backdrop-blur-sm py-4 mb-12">
        <PipelineDiagram activeStage={activeStage} />
      </div>

      {/* Desktop: counter-scrolling card rows */}
      <div className="hidden md:block space-y-8">
        <div
          ref={topRowRef}
          data-card-row
          data-direction="left"
          className="flex gap-6 pl-[10%]"
          style={{ transform: "translateX(30%)" }}
        >
          {topRowCards.map((card) => (
            <EngineCard key={card.title} {...card} />
          ))}
        </div>

        <div
          ref={bottomRowRef}
          data-card-row
          data-direction="right"
          className="flex gap-6 pl-[10%]"
          style={{ transform: "translateX(-30%)" }}
        >
          {bottomRowCards.map((card) => (
            <EngineCard key={card.title} {...card} />
          ))}
        </div>
      </div>

      {/* Mobile: vertical interleaved stack */}
      <div className="md:hidden flex flex-col items-center gap-4 px-6 max-w-[360px] mx-auto">
        {topRowCards.map((card, i) => (
          <div key={card.title} className="w-full space-y-4">
            <EngineCard {...card} />
            {bottomRowCards[i] && <EngineCard {...bottomRowCards[i]} />}
          </div>
        ))}
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/engine-section.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/engine-section.tsx web/src/components/landing/__tests__/engine-section.test.tsx
git commit -m "feat(web): add EngineSection with GSAP ScrollTrigger and pipeline sync"
```

---

## Task 9: Create Proof Section with Micro-Charts

**Files:**
- Create: `web/src/components/landing/proof-section.tsx`
- Create: `web/src/components/landing/__tests__/proof-section.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/landing/__tests__/proof-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    section: ({ children, ...props }: any) => <section {...props}>{children}</section>,
  },
  useInView: () => true,
}))

import { ProofSection } from "../proof-section"

describe("ProofSection", () => {
  it("renders headline", () => {
    render(<ProofSection pick={null} />)
    expect(screen.getByText(/structure creates measurable advantage/i)).toBeInTheDocument()
  })

  it("renders all 4 proof cards", () => {
    render(<ProofSection pick={null} />)
    expect(screen.getByText(/factor transparency/i)).toBeInTheDocument()
    expect(screen.getByText(/growth vs value/i)).toBeInTheDocument()
    expect(screen.getByText(/portfolio view/i)).toBeInTheDocument()
    expect(screen.getByText(/historical application/i)).toBeInTheDocument()
  })

  it("renders factor percentile bars", () => {
    render(<ProofSection pick={null} />)
    expect(screen.getByText("Valuation")).toBeInTheDocument()
    expect(screen.getByText("Quality")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/proof-section.test.tsx`

Expected: FAIL

**Step 3: Write the component**

```tsx
// web/src/components/landing/proof-section.tsx
"use client"

import { useRef } from "react"
import { motion, useInView } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

interface PickData {
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
}

interface ProofSectionProps {
  pick: PickData | null
}

const MOCK_FACTORS = { quality_percentile: 85, value_percentile: 62, momentum_percentile: 71 }

function PercentileBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-text-tertiary w-20">{label}</span>
      <div className="flex-1 h-2 bg-bg-subtle rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-accent rounded-full"
          initial={{ width: 0 }}
          whileInView={{ width: `${value}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease }}
        />
      </div>
      <span className="font-mono text-xs text-text-primary w-8 text-right">{value}</span>
    </div>
  )
}

function ProofCard({ title, children }: { title: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })

  return (
    <motion.div
      ref={ref}
      className="terminal-card p-6"
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, ease }}
    >
      <p className="text-[10px] uppercase tracking-[0.2em] text-text-tertiary mb-4">{title}</p>
      {children}
    </motion.div>
  )
}

export function ProofSection({ pick }: ProofSectionProps) {
  const factors = pick ?? MOCK_FACTORS

  return (
    <section id="proof" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.h2
          className="font-display text-4xl md:text-5xl text-text-primary mb-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease }}
        >
          Structure creates measurable advantage.
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Factor Transparency */}
          <ProofCard title="Factor Transparency">
            <div className="space-y-3">
              <PercentileBar label="Valuation" value={factors.value_percentile} />
              <PercentileBar label="Quality" value={factors.quality_percentile} />
              <PercentileBar label="Momentum" value={factors.momentum_percentile} />
              <PercentileBar label="Sentiment" value={68} />
              <PercentileBar label="Growth" value={74} />
            </div>
            <p className="text-xs text-text-tertiary mt-4">Every percentile visible. Every factor verifiable.</p>
          </ProofCard>

          {/* Card 2: Growth vs Value Tilt */}
          <ProofCard title="Growth vs Value Tilt">
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs text-text-tertiary mb-1">
                  <span>Growth Weight</span>
                  <span className="font-mono">35%</span>
                </div>
                <div className="h-2 bg-bg-subtle rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-accent/70 rounded-full"
                    initial={{ width: 0 }}
                    whileInView={{ width: "35%" }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, ease }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs text-text-tertiary mb-1">
                  <span>Value Weight</span>
                  <span className="font-mono">25%</span>
                </div>
                <div className="h-2 bg-bg-subtle rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-accent/40 rounded-full"
                    initial={{ width: 0 }}
                    whileInView={{ width: "25%" }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, delay: 0.1, ease }}
                  />
                </div>
              </div>
            </div>
            <p className="text-xs text-text-tertiary mt-4">The engine adapts factor weights by growth stage automatically.</p>
          </ProofCard>

          {/* Card 3: Portfolio View (mock) */}
          <ProofCard title="Portfolio View">
            <div className="grid grid-cols-5 gap-1">
              {Array.from({ length: 25 }, (_, i) => {
                const opacity = 0.15 + Math.random() * 0.85
                return (
                  <div
                    key={i}
                    className="aspect-square rounded-sm bg-accent"
                    style={{ opacity }}
                  />
                )
              })}
            </div>
            <p className="text-xs text-text-tertiary mt-4">Correlation heatmap identifies position overlap before it matters.</p>
          </ProofCard>

          {/* Card 4: Historical Application (mock) */}
          <ProofCard title="Historical Application">
            <div className="h-24 flex items-end gap-1">
              {[40, 55, 48, 62, 58, 70, 65, 75, 72, 80, 78, 85].map((v, i) => (
                <motion.div
                  key={i}
                  className="flex-1 bg-accent/60 rounded-t-sm"
                  initial={{ height: 0 }}
                  whileInView={{ height: `${v}%` }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: i * 0.05, ease }}
                />
              ))}
            </div>
            <p className="text-xs text-text-tertiary mt-4">Backtested conviction vs actual returns. No curve-fitting.</p>
            <p className="text-[10px] text-text-tertiary mt-1 italic">Past performance is not indicative of future results.</p>
          </ProofCard>
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/proof-section.test.tsx`

Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/proof-section.tsx web/src/components/landing/__tests__/proof-section.test.tsx
git commit -m "feat(web): add ProofSection with micro-charts and factor bars"
```

---

## Task 10: Create Positioning Section

**Files:**
- Create: `web/src/components/landing/positioning-section.tsx`
- Create: `web/src/components/landing/__tests__/positioning-section.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/landing/__tests__/positioning-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
  },
}))

import { PositioningSection } from "../positioning-section"

describe("PositioningSection", () => {
  it("renders headline", () => {
    render(<PositioningSection />)
    expect(screen.getByText(/disciplined capital allocators/i)).toBeInTheDocument()
  })

  it("renders not-for items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Day traders")).toBeInTheDocument()
    expect(screen.getByText("Narrative chasers")).toBeInTheDocument()
    expect(screen.getByText("Meme cycles")).toBeInTheDocument()
  })

  it("renders for items", () => {
    render(<PositioningSection />)
    expect(screen.getByText("Long-horizon investors")).toBeInTheDocument()
    expect(screen.getByText("Portfolio operators")).toBeInTheDocument()
    expect(screen.getByText("Capital stewards")).toBeInTheDocument()
  })
})
```

**Step 2: Run test, write component, run test, commit**

Component:

```tsx
// web/src/components/landing/positioning-section.tsx
"use client"

import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const notFor = ["Day traders", "Narrative chasers", "Meme cycles"]
const forItems = ["Long-horizon investors", "Portfolio operators", "Capital stewards"]

export function PositioningSection() {
  return (
    <section id="positioning" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.h2
          className="font-display text-4xl md:text-5xl text-text-primary mb-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease }}
        >
          Built for disciplined capital allocators.
        </motion.h2>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-16"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2, ease }}
        >
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-text-tertiary mb-6">Not for</p>
            <ul className="space-y-3">
              {notFor.map((item) => (
                <li key={item} className="text-lg text-text-tertiary">{item}</li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-accent mb-6">Built for</p>
            <ul className="space-y-3">
              {forItems.map((item) => (
                <li key={item} className="text-lg text-text-primary">{item}</li>
              ))}
            </ul>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
```

**Commit:**

```bash
git add web/src/components/landing/positioning-section.tsx web/src/components/landing/__tests__/positioning-section.test.tsx
git commit -m "feat(web): add PositioningSection for/not-for layout"
```

---

## Task 11: Create Pricing Section with Renamed Tiers

**Files:**
- Create: `web/src/components/landing/pricing-section.tsx`
- Create: `web/src/components/landing/__tests__/pricing-section.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/landing/__tests__/pricing-section.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  },
  useInView: () => true,
}))

import { PricingSection } from "../pricing-section"

describe("PricingSection", () => {
  it("renders all three renamed tiers", () => {
    render(<PricingSection />)
    expect(screen.getByText("Analyst")).toBeInTheDocument()
    expect(screen.getByText("Portfolio")).toBeInTheDocument()
    expect(screen.getByText("Institutional")).toBeInTheDocument()
  })

  it("renders pricing header line", () => {
    render(<PricingSection />)
    expect(screen.getByText(/system scales with your responsibility/i)).toBeInTheDocument()
  })

  it("renders prices", () => {
    render(<PricingSection />)
    expect(screen.getByText("Free")).toBeInTheDocument()
    expect(screen.getByText("$29")).toBeInTheDocument()
    expect(screen.getByText("$79")).toBeInTheDocument()
  })

  it("renders CTA linking to dashboard", () => {
    render(<PricingSection />)
    const cta = screen.getByRole("link", { name: /start building conviction/i })
    expect(cta).toHaveAttribute("href", "/dashboard")
  })

  it("renders fine print with Analyst tier mention", () => {
    render(<PricingSection />)
    expect(screen.getByText(/no credit card required for analyst tier/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test, write component, run test, commit**

Component matches the existing `chapter-path.tsx` structure but with:
- Renamed tiers: Analyst/Portfolio/Institutional
- Header line: "The system scales with your responsibility."
- Terminal card style instead of glass
- Updated CTAs and fine print

```tsx
// web/src/components/landing/pricing-section.tsx
"use client"

import Link from "next/link"
import { motion, useInView } from "framer-motion"
import { useRef } from "react"

const ease = [0.22, 1, 0.36, 1] as const

interface Tier {
  name: string
  price: string
  period: string
  description: string
  features: string[]
  highlighted: boolean
}

const tiers: Tier[] = [
  {
    name: "Analyst",
    price: "Free",
    period: "",
    description: "Evaluate the engine with real positions.",
    features: [
      "3 ticker analyses per month",
      "Composite score + conviction level",
      "Top-level factor breakdown",
      "5-ticker watchlist",
    ],
    highlighted: false,
  },
  {
    name: "Portfolio",
    price: "$29",
    period: "/mo",
    description: "Full scoring for active portfolio management.",
    features: [
      "Unlimited ticker analysis",
      "Full 6-factor breakdown",
      "90-day score history",
      "25-ticker watchlist",
      "Conviction change alerts",
    ],
    highlighted: true,
  },
  {
    name: "Institutional",
    price: "$79",
    period: "/mo",
    description: "Portfolio-level conviction infrastructure.",
    features: [
      "Everything in Portfolio",
      "Unlimited score history",
      "Portfolio correlation analysis",
      "Sector rotation signals",
      "API access",
    ],
    highlighted: false,
  },
]

function TierCard({ tier, index }: { tier: Tier; index: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.12, ease }}
      className={tier.highlighted ? "-mt-4 mb-4 md:-mt-6 md:mb-6" : ""}
    >
      <div className={tier.highlighted ? "terminal-card-accent p-6 md:p-8 flex flex-col" : "terminal-card p-6 md:p-8 flex flex-col"}>
        <p className="text-xs uppercase tracking-[0.2em] text-text-tertiary mb-3">
          {tier.name}
        </p>
        <div className="flex items-baseline gap-1 mb-2">
          <span className="font-display text-4xl text-text-primary">{tier.price}</span>
          {tier.period && (
            <span className="text-sm text-text-tertiary">{tier.period}</span>
          )}
        </div>
        <p className="text-sm text-text-secondary mb-6">{tier.description}</p>
        <ul className="space-y-2 mb-8 flex-1">
          {tier.features.map((f) => (
            <li key={f} className="text-sm text-text-secondary flex items-start gap-2">
              <span className="text-accent mt-0.5">&#x2713;</span>
              {f}
            </li>
          ))}
        </ul>
        <Link
          href="/onboarding"
          className={`inline-flex items-center justify-center h-11 rounded-lg text-sm font-medium transition-colors ${
            tier.highlighted
              ? "bg-accent text-white hover:bg-accent-hover"
              : "border border-border-primary text-text-primary hover:bg-bg-subtle"
          }`}
        >
          {tier.highlighted ? "Start trial" : tier.price === "Free" ? "Start free" : "Get started"}
        </Link>
      </div>
    </motion.div>
  )
}

export function PricingSection() {
  return (
    <section id="pricing" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <p className="text-sm uppercase tracking-[0.15em] text-text-tertiary text-center mb-6">
          The system scales with your responsibility.
        </p>

        <motion.h2
          className="font-display text-4xl md:text-5xl text-center text-text-primary mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease }}
        >
          Start Building Conviction
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {tiers.map((tier, i) => (
            <TierCard key={tier.name} tier={tier} index={i} />
          ))}
        </div>

        <motion.div
          className="mt-20 text-center"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4, ease }}
        >
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center h-12 px-8 rounded-lg bg-accent text-white text-sm font-medium tracking-wide transition-colors hover:bg-accent-hover"
          >
            Start Building Conviction
          </Link>
          <p className="mt-4 text-xs text-text-tertiary">
            No credit card required for Analyst tier.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
```

**Commit:**

```bash
git add web/src/components/landing/pricing-section.tsx web/src/components/landing/__tests__/pricing-section.test.tsx
git commit -m "feat(web): add PricingSection with Analyst/Portfolio/Institutional tiers"
```

---

## Task 12: Create Legitimacy Strip and Institutional Footer

**Files:**
- Create: `web/src/components/landing/legitimacy-strip.tsx`
- Create: `web/src/components/landing/footer-institutional.tsx`
- Create: `web/src/components/landing/__tests__/legitimacy-strip.test.tsx`
- Create: `web/src/components/landing/__tests__/footer-institutional.test.tsx`

**Step 1: Write tests**

Legitimacy strip test:
```tsx
// web/src/components/landing/__tests__/legitimacy-strip.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { LegitimacyStrip } from "../legitimacy-strip"

describe("LegitimacyStrip", () => {
  it("renders trust markers", () => {
    render(<LegitimacyStrip />)
    expect(screen.getByText(/sec filings/i)).toBeInTheDocument()
    expect(screen.getByText(/updated daily/i)).toBeInTheDocument()
    expect(screen.getByText(/no hidden heuristics/i)).toBeInTheDocument()
  })
})
```

Footer test:
```tsx
// web/src/components/landing/__tests__/footer-institutional.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FooterInstitutional } from "../footer-institutional"

describe("FooterInstitutional", () => {
  it("renders all navigation links", () => {
    render(<FooterInstitutional />)
    expect(screen.getByText("Support")).toBeInTheDocument()
    expect(screen.getByText("Methodology")).toBeInTheDocument()
    expect(screen.getByText("Legal")).toBeInTheDocument()
    expect(screen.getByText("API")).toBeInTheDocument()
  })

  it("renders copyright and version", () => {
    render(<FooterInstitutional />)
    expect(screen.getByText(/margin invest/i)).toBeInTheDocument()
    expect(screen.getByText(/engine v/i)).toBeInTheDocument()
  })
})
```

**Step 2: Write both components**

```tsx
// web/src/components/landing/legitimacy-strip.tsx
const markers = [
  "Data Sources: SEC Filings, Earnings Transcripts, Market Feeds",
  "Updated Daily",
  "Encrypted Key Storage",
  "Audit-Friendly Scoring",
  "No Hidden Heuristics",
]

export function LegitimacyStrip() {
  return (
    <div className="border-y border-border-subtle py-6">
      <div className="max-w-6xl mx-auto px-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
        {markers.map((marker, i) => (
          <span key={marker} className="font-mono text-[10px] uppercase tracking-wider text-text-tertiary">
            {marker}
            {i < markers.length - 1 && (
              <span className="ml-6 text-border-subtle hidden md:inline">|</span>
            )}
          </span>
        ))}
      </div>
    </div>
  )
}
```

```tsx
// web/src/components/landing/footer-institutional.tsx
import Link from "next/link"

const links = [
  { href: "/support", label: "Support" },
  { href: "/methodology", label: "Methodology" },
  { href: "/security", label: "Security" },
  { href: "/legal", label: "Legal" },
  { href: "/status", label: "Status" },
  { href: "/api", label: "API" },
  { href: "/support", label: "Contact" },
]

export function FooterInstitutional() {
  return (
    <footer className="border-t border-border-subtle py-12">
      <div className="max-w-6xl mx-auto px-6">
        <nav className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3 mb-8" aria-label="Footer">
          {links.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="text-xs text-text-tertiary hover:text-text-secondary transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <p className="text-center text-[11px] text-text-tertiary">
          &copy; {new Date().getFullYear()} Margin Invest &middot;{" "}
          <span className="font-mono">Engine v1.3.2</span>
        </p>
      </div>
    </footer>
  )
}
```

**Step 3: Run tests, commit**

Run: `npx vitest run web/src/components/landing/__tests__/legitimacy-strip.test.tsx web/src/components/landing/__tests__/footer-institutional.test.tsx`

```bash
git add web/src/components/landing/legitimacy-strip.tsx web/src/components/landing/footer-institutional.tsx web/src/components/landing/__tests__/legitimacy-strip.test.tsx web/src/components/landing/__tests__/footer-institutional.test.tsx
git commit -m "feat(web): add LegitimacyStrip and FooterInstitutional components"
```

---

## Task 13: Create Section Indicator (Updated for 8 Sections)

**Files:**
- Create: `web/src/components/landing/section-indicator.tsx`
- Create: `web/src/components/landing/__tests__/section-indicator.test.tsx`

**Step 1: Write test and component**

The new indicator tracks 8 sections instead of 3. Same IntersectionObserver pattern as the old `ChapterIndicator`.

```tsx
// web/src/components/landing/section-indicator.tsx
"use client"

import { useEffect, useRef, useState } from "react"

const SECTIONS = [
  { id: "hero", label: "Hero" },
  { id: "problem", label: "Problem" },
  { id: "engine", label: "Engine" },
  { id: "proof", label: "Proof" },
  { id: "positioning", label: "Positioning" },
  { id: "pricing", label: "Pricing" },
]

export function SectionIndicator() {
  const [activeIndex, setActiveIndex] = useState(0)
  const observerRef = useRef<IntersectionObserver | null>(null)

  useEffect(() => {
    const elements = SECTIONS.map(({ id }) => document.getElementById(id)).filter(
      Boolean,
    ) as HTMLElement[]

    if (elements.length === 0) return

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const index = SECTIONS.findIndex((s) => s.id === entry.target.id)
            if (index !== -1) setActiveIndex(index)
          }
        }
      },
      { threshold: 0.3 },
    )

    for (const el of elements) {
      observerRef.current.observe(el)
    }

    return () => observerRef.current?.disconnect()
  }, [])

  function handleNavigate(index: number) {
    const id = SECTIONS[index]?.id
    if (id) {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth" })
    }
  }

  return (
    <nav
      aria-label="Page sections"
      className="fixed right-6 top-1/2 -translate-y-1/2 z-50 hidden lg:flex flex-col gap-2"
    >
      {SECTIONS.map((section, i) => (
        <button
          key={section.id}
          data-section-dot
          data-active={i === activeIndex ? "true" : "false"}
          aria-label={section.label}
          aria-current={i === activeIndex ? "step" : undefined}
          onClick={() => handleNavigate(i)}
          className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${
            i === activeIndex
              ? "bg-accent scale-150"
              : "bg-text-tertiary opacity-30 hover:opacity-60"
          }`}
        />
      ))}
    </nav>
  )
}
```

Test:
```tsx
// web/src/components/landing/__tests__/section-indicator.test.tsx
import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { SectionIndicator } from "../section-indicator"

describe("SectionIndicator", () => {
  it("renders 6 navigation dots", () => {
    const { container } = render(<SectionIndicator />)
    const dots = container.querySelectorAll("[data-section-dot]")
    expect(dots).toHaveLength(6)
  })
})
```

**Commit:**

```bash
git add web/src/components/landing/section-indicator.tsx web/src/components/landing/__tests__/section-indicator.test.tsx
git commit -m "feat(web): add SectionIndicator for 6-section navigation"
```

---

## Task 14: Rewrite page.tsx and Update Assembly

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/components/landing/__tests__/page-assembly.test.tsx`

**Step 1: Rewrite page.tsx**

Replace the entire file content:

```tsx
// web/src/app/page.tsx
import { Navbar } from "@/components/nav/navbar"
import { HeroSection } from "@/components/landing/hero-section"
import { ProblemSection } from "@/components/landing/problem-section"
import { EngineSection } from "@/components/landing/engine-section"
import { ProofSection } from "@/components/landing/proof-section"
import { PositioningSection } from "@/components/landing/positioning-section"
import { PricingSection } from "@/components/landing/pricing-section"
import { LegitimacyStrip } from "@/components/landing/legitimacy-strip"
import { FooterInstitutional } from "@/components/landing/footer-institutional"
import { SectionIndicator } from "@/components/landing/section-indicator"
import { serverFetch } from "@/lib/api/server"

interface PickSummary {
  ticker: string
  name: string
  actual_price: number | null
  buy_price: number | null
  margin_of_safety: number | null
  composite_percentile: number
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  scored_at: string | null
  sector: string | null
}

interface DashboardResponse {
  picks: PickSummary[]
}

async function getTopPick(): Promise<PickSummary | null> {
  try {
    const data = await serverFetch<DashboardResponse>("/api/v1/dashboard")
    return data.picks[0] ?? null
  } catch {
    return null
  }
}

export default async function Home() {
  const topPick = await getTopPick()

  return (
    <main>
      <Navbar />
      <div className="relative z-10">
        <HeroSection pick={topPick} />
        <ProblemSection />
        <EngineSection />
        <ProofSection pick={topPick} />
        <PositioningSection />
        <PricingSection />
        <LegitimacyStrip />
        <FooterInstitutional />
      </div>
      <SectionIndicator />
    </main>
  )
}
```

**Step 2: Update the page assembly test**

Replace the existing test file:

```tsx
// web/src/components/landing/__tests__/page-assembly.test.tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/api/server", () => ({
  serverFetch: vi.fn().mockResolvedValue({ picks: [] }),
}))

vi.mock("@/lib/auth", () => ({
  auth: vi.fn().mockResolvedValue(null),
}))

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}))

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }: any) => <h1 {...props}>{children}</h1>,
    h2: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
    h3: ({ children, ...props }: any) => <h3 {...props}>{children}</h3>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
    section: ({ children, ...props }: any) => <section {...props}>{children}</section>,
    li: ({ children, ...props }: any) => <li {...props}>{children}</li>,
    ul: ({ children, ...props }: any) => <ul {...props}>{children}</ul>,
  },
  useInView: () => true,
  useScroll: () => ({ scrollYProgress: { get: () => 0.5 } }),
  useTransform: (_: any, inputOrFn: number[] | Function, output?: any[]) => {
    if (typeof inputOrFn === "function") return inputOrFn(0)
    return output![Math.floor(output!.length / 2)]
  },
  useReducedMotion: () => false,
}))

vi.mock("gsap", () => ({
  default: { registerPlugin: vi.fn(), to: vi.fn() },
}))

vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [] },
}))

import Page from "../../../app/page"

describe("Landing page assembly", () => {
  it("renders all major sections", async () => {
    const jsx = await Page()
    render(jsx)

    // Hero
    expect(screen.getByText(/Conviction/)).toBeInTheDocument()
    expect(screen.getByText(/Engineered/)).toBeInTheDocument()

    // Problem
    expect(screen.getByText(/most investors react/i)).toBeInTheDocument()

    // Engine cards
    expect(screen.getByText("Raw Market Signal")).toBeInTheDocument()
    expect(screen.getByText("Portfolio Correlation Mapping")).toBeInTheDocument()

    // Pipeline
    expect(screen.getByText("DATA")).toBeInTheDocument()
    expect(screen.getByText("PORTFOLIO")).toBeInTheDocument()

    // Proof
    expect(screen.getByText(/structure creates measurable advantage/i)).toBeInTheDocument()

    // Positioning
    expect(screen.getByText(/disciplined capital allocators/i)).toBeInTheDocument()

    // Pricing (renamed tiers)
    expect(screen.getByText("Analyst")).toBeInTheDocument()
    expect(screen.getByText("Portfolio")).toBeInTheDocument()
    expect(screen.getByText("Institutional")).toBeInTheDocument()

    // Legitimacy
    expect(screen.getByText(/no hidden heuristics/i)).toBeInTheDocument()

    // Footer
    expect(screen.getByText(/engine v/i)).toBeInTheDocument()
  })

  it("renders the navbar", async () => {
    const jsx = await Page()
    render(jsx)
    const nav = screen.getByRole("navigation", { name: "Main navigation" })
    expect(nav).toBeInTheDocument()
  })
})
```

**Step 3: Run the test**

Run: `npx vitest run web/src/components/landing/__tests__/page-assembly.test.tsx`

Expected: PASS

**Step 4: Commit**

```bash
git add web/src/app/page.tsx web/src/components/landing/__tests__/page-assembly.test.tsx
git commit -m "feat(web): rewrite homepage with 8-section institutional layout"
```

---

## Task 15: Remove Old Landing Components

**Files:**
- Delete: `web/src/components/landing/chapter-hero.tsx`
- Delete: `web/src/components/landing/chapter-cards.tsx`
- Delete: `web/src/components/landing/chapter-path.tsx`
- Delete: `web/src/components/landing/chapter-indicator.tsx`
- Delete: `web/src/components/landing/flow-card.tsx`
- Delete: `web/src/components/landing/fluid-shader.tsx`
- Delete: `web/src/components/landing/fluid-shader-loader.tsx`
- Delete: `web/src/components/landing/dna-provider.tsx`
- Delete: `web/src/components/landing/__tests__/chapter-hero.test.tsx`
- Delete: `web/src/components/landing/__tests__/chapter-cards.test.tsx`
- Delete: `web/src/components/landing/__tests__/chapter-path.test.tsx`
- Delete: `web/src/components/landing/__tests__/chapter-indicator.test.tsx`
- Delete: `web/src/components/landing/__tests__/flow-card.test.tsx`
- Delete: `web/src/components/landing/__tests__/fluid-shader.test.tsx`
- Delete: `web/src/components/landing/__tests__/dna-provider.test.tsx`

**Step 1: Delete all old files**

```bash
cd /Users/brandon/repos/margin_invest
rm web/src/components/landing/chapter-hero.tsx \
   web/src/components/landing/chapter-cards.tsx \
   web/src/components/landing/chapter-path.tsx \
   web/src/components/landing/chapter-indicator.tsx \
   web/src/components/landing/flow-card.tsx \
   web/src/components/landing/fluid-shader.tsx \
   web/src/components/landing/fluid-shader-loader.tsx \
   web/src/components/landing/dna-provider.tsx
rm web/src/components/landing/__tests__/chapter-hero.test.tsx \
   web/src/components/landing/__tests__/chapter-cards.test.tsx \
   web/src/components/landing/__tests__/chapter-path.test.tsx \
   web/src/components/landing/__tests__/chapter-indicator.test.tsx \
   web/src/components/landing/__tests__/flow-card.test.tsx \
   web/src/components/landing/__tests__/fluid-shader.test.tsx \
   web/src/components/landing/__tests__/dna-provider.test.tsx
```

**Step 2: Check for remaining imports of deleted components**

Run: `grep -r "chapter-hero\|chapter-cards\|chapter-path\|chapter-indicator\|flow-card\|fluid-shader\|dna-provider" web/src/ --include="*.tsx" --include="*.ts" -l`

If any files still reference old components, update their imports.

**Step 3: Run all landing tests**

Run: `npx vitest run web/src/components/landing/`

Expected: All new tests PASS, no old test failures

**Step 4: Commit**

```bash
git add -A web/src/components/landing/
git commit -m "refactor(web): remove old landing components (shader, glass, chapters)"
```

---

## Task 16: Remove GlassSurface if No Longer Used

**Files:**
- Possibly delete: `web/src/components/ui/glass-surface.tsx`

**Step 1: Check if GlassSurface is used anywhere else**

Run: `grep -r "GlassSurface\|glass-surface" web/src/ --include="*.tsx" --include="*.ts" -l`

If only the deleted landing components used it, delete it. If other pages (methodology, dashboard) use it, keep it.

**Step 2: If unused, delete and remove CSS**

Remove the `.glass` and `.glass-elevated` classes from `globals.css` only if truly unused throughout the project. If used elsewhere, keep them.

**Step 3: Commit if changes made**

```bash
git add -A
git commit -m "refactor(web): remove unused GlassSurface component and glass CSS"
```

---

## Task 17: Suppress Global Footer on Homepage

The root layout renders `<Footer />` globally. The homepage now has its own `FooterInstitutional`. We need to prevent the global footer from showing on the homepage.

**Files:**
- Modify: `web/src/app/layout.tsx`
- OR: Modify: `web/src/components/layout/footer.tsx`

**Step 1: Approach**

The simplest approach: wrap the global `<Footer />` in a conditional that hides it on the homepage. Since `layout.tsx` is a server component without access to `usePathname`, use a client wrapper or move the Footer into per-page layouts.

Alternative: The homepage can render its own layout that doesn't include the global footer. Check if a `web/src/app/(landing)/layout.tsx` route group pattern exists.

**Step 2: Implement**

The cleanest approach is a route group: move `page.tsx` into `web/src/app/(landing)/page.tsx` with its own layout that omits the global Footer. OR, add `data-page="home"` to the homepage `<main>` and use CSS to hide the global footer: `.global-footer:has(~ [data-page="home"])`.

**The specific implementation depends on what other pages exist in the root**. The executor should read `layout.tsx` and decide the best approach at implementation time.

**Step 3: Verify and commit**

Run the dev server and confirm: homepage shows `FooterInstitutional`, other pages show the regular `Footer`.

---

## Task 18: Run Full Test Suite

**Step 1: Run all web tests**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run --project web`

Or: `npx vitest run web/src/`

Expected: All tests pass. Fix any failures.

**Step 2: Run TypeScript check**

Run: `cd /Users/brandon/repos/margin_invest/web && npx tsc --noEmit`

Expected: No type errors. Fix any issues.

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix(web): resolve test and type issues from homepage rebuild"
```

---

## Task 19: Tier Rename — Backend Migration (Separate Work Stream)

> **Note:** This task is intentionally separated from the UI rebuild. It should be done after the homepage is stable and working. It touches the database, API, and billing — higher risk than UI changes.

**Files:**
- Create: new Alembic migration
- Modify: `api/src/margin_api/config.py` — rename `stripe_operator_price_id` → `stripe_portfolio_price_id`, `stripe_allocator_price_id` → `stripe_institutional_price_id`
- Modify: `api/src/margin_api/db/models.py` — change defaults from `"scout"` → `"analyst"`
- Modify: `api/src/margin_api/schemas/billing.py` — update comments
- Modify: `api/src/margin_api/services/billing.py` — rename all string literals
- Modify: `api/src/margin_api/routes/billing.py` — update config references and plan check
- Modify: `web/src/components/account/billing-section.tsx` — update PLAN_BADGES keys/labels
- Modify: all test files listed in the tier rename inventory

**Step 1: Create new Alembic migration**

```bash
cd /Users/brandon/repos/margin_invest
uv run alembic -c api/alembic.ini revision --autogenerate -m "rename_tier_scout_operator_allocator_to_analyst_portfolio_institutional"
```

Then edit the migration to contain:
```python
def upgrade():
    op.execute("UPDATE users SET subscription_plan = 'analyst' WHERE subscription_plan = 'scout'")
    op.execute("UPDATE users SET subscription_plan = 'portfolio' WHERE subscription_plan = 'operator'")
    op.execute("UPDATE users SET subscription_plan = 'institutional' WHERE subscription_plan = 'allocator'")
    op.execute("UPDATE credential_users SET subscription_plan = 'analyst' WHERE subscription_plan = 'scout'")
    op.execute("UPDATE credential_users SET subscription_plan = 'portfolio' WHERE subscription_plan = 'operator'")
    op.execute("UPDATE credential_users SET subscription_plan = 'institutional' WHERE subscription_plan = 'allocator'")

def downgrade():
    op.execute("UPDATE users SET subscription_plan = 'scout' WHERE subscription_plan = 'analyst'")
    op.execute("UPDATE users SET subscription_plan = 'operator' WHERE subscription_plan = 'portfolio'")
    op.execute("UPDATE users SET subscription_plan = 'allocator' WHERE subscription_plan = 'institutional'")
    op.execute("UPDATE credential_users SET subscription_plan = 'scout' WHERE subscription_plan = 'analyst'")
    op.execute("UPDATE credential_users SET subscription_plan = 'operator' WHERE subscription_plan = 'portfolio'")
    op.execute("UPDATE credential_users SET subscription_plan = 'allocator' WHERE subscription_plan = 'institutional'")
```

**Step 2: Update all API source files**

Mechanical find-replace across the files listed in the inventory:
- `"scout"` → `"analyst"`
- `"operator"` → `"portfolio"`
- `"allocator"` → `"institutional"`
- `stripe_operator_price_id` → `stripe_portfolio_price_id`
- `stripe_allocator_price_id` → `stripe_institutional_price_id`

**Step 3: Update all API tests**

Same mechanical find-replace across all test files.

**Step 4: Update web billing section**

Update `PLAN_BADGES` keys and labels in `web/src/components/account/billing-section.tsx`.

**Step 5: Run all tests**

```bash
uv run pytest api/tests/ -v
npx vitest run web/src/
```

Expected: All pass

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: rename tiers Scout/Operator/Allocator → Analyst/Portfolio/Institutional"
```

---

## Summary of Implementation Order

| Task | Component | Estimated Steps | Dependencies |
|------|-----------|----------------|--------------|
| 1 | Dependencies | 4 | None |
| 2 | Color tokens + terminal card CSS | 5 | None |
| 3 | HeroCandidatePanel | 5 | Task 2 |
| 4 | HeroSection | 5 | Task 3 |
| 5 | ProblemSection | 5 | Task 2 |
| 6 | PipelineDiagram | 5 | Task 2 |
| 7 | EngineCard | 5 | Task 2 |
| 8 | EngineSection (GSAP) | 5 | Tasks 1, 6, 7 |
| 9 | ProofSection | 5 | Task 2 |
| 10 | PositioningSection | 5 | Task 2 |
| 11 | PricingSection | 5 | Task 2 |
| 12 | LegitimacyStrip + Footer | 5 | None |
| 13 | SectionIndicator | 5 | None |
| 14 | page.tsx rewrite + assembly test | 4 | Tasks 3-13 |
| 15 | Remove old components | 4 | Task 14 |
| 16 | Remove GlassSurface if unused | 3 | Task 15 |
| 17 | Suppress global footer on homepage | 3 | Task 14 |
| 18 | Full test suite run | 3 | Task 15 |
| 19 | Tier rename (backend) | 6 | Task 11 |

Tasks 1-2 must go first. Tasks 3-13 can be parallelized. Tasks 14-18 are sequential. Task 19 is independent.
