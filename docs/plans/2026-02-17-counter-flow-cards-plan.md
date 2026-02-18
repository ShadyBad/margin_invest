# Counter-Flow Cards Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the Engine + Proof horizontal scroll chapters with a single counter-flow card section where two rows of cards move in opposite horizontal directions on scroll, with depth-of-field fade+blur effects.

**Architecture:** A new `ChapterCards` client component uses Framer Motion's `useScroll` and `useTransform` to map vertical scroll progress to horizontal `translateX` on two card rows (top row moves left, bottom row moves right). Individual cards track their own viewport position for per-card opacity + blur depth-of-field. Mobile falls back to a single interleaved column with vertical scroll-fade only.

**Tech Stack:** Next.js 15, Framer Motion 12 (`useScroll`, `useTransform`, `useReducedMotion`), Tailwind CSS, existing `GlassSurface` component, Vitest + React Testing Library.

**Design Doc:** `docs/plans/2026-02-17-counter-flow-cards-design.md`

---

### Task 1: Create the FlowCard primitive component

**Files:**
- Create: `web/src/components/landing/flow-card.tsx`
- Test: `web/src/components/landing/__tests__/flow-card.test.tsx`

This is the individual card with depth-of-field scroll tracking (opacity + blur based on viewport position).

**Step 1: Write the failing test**

Create `web/src/components/landing/__tests__/flow-card.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, style, ...props }: any) => (
      <div style={style} {...props}>{children}</div>
    ),
  },
  useScroll: () => ({ scrollYProgress: { get: () => 0.5 } }),
  useTransform: (_: any, input: number[], output: any[]) => output[Math.floor(output.length / 2)],
  useReducedMotion: () => false,
}))

import { FlowCard } from "../flow-card"

describe("FlowCard", () => {
  it("renders children inside a glass surface", () => {
    render(
      <FlowCard title="Raw Signal" subtitle="The Engine">
        <p>Test content</p>
      </FlowCard>,
    )
    expect(screen.getByText("Raw Signal")).toBeInTheDocument()
    expect(screen.getByText("The Engine")).toBeInTheDocument()
    expect(screen.getByText("Test content")).toBeInTheDocument()
  })

  it("renders with data-flow-card attribute", () => {
    const { container } = render(
      <FlowCard title="Test" subtitle="Sub">
        <p>Content</p>
      </FlowCard>,
    )
    expect(container.querySelector("[data-flow-card]")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/flow-card.test.tsx`
Expected: FAIL — module `../flow-card` not found

**Step 3: Write the FlowCard component**

Create `web/src/components/landing/flow-card.tsx`:

```tsx
"use client"

import { useRef, type ReactNode } from "react"
import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion"
import { GlassSurface } from "../ui/glass-surface"

interface FlowCardProps {
  title: string
  subtitle: string
  children: ReactNode
}

export function FlowCard({ title, subtitle, children }: FlowCardProps) {
  const ref = useRef<HTMLDivElement>(null)
  const prefersReducedMotion = useReducedMotion()

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  })

  const opacity = useTransform(
    scrollYProgress,
    [0, 0.3, 0.5, 0.7, 1],
    [0.15, 0.6, 1, 0.6, 0.15],
  )

  const blur = useTransform(
    scrollYProgress,
    [0, 0.3, 0.5, 0.7, 1],
    prefersReducedMotion ? [0, 0, 0, 0, 0] : [4, 1.5, 0, 1.5, 4],
  )

  const filterBlur = useTransform(blur, (v) => `blur(${v}px)`)

  return (
    <motion.div
      ref={ref}
      data-flow-card
      className="w-[320px] flex-shrink-0 md:w-[320px]"
      style={{ opacity, filter: filterBlur }}
    >
      <GlassSurface className="p-6 md:p-8 h-full">
        <p className="text-xs uppercase tracking-[0.2em] text-[var(--color-text-tertiary)] mb-3">
          {subtitle}
        </p>
        <h3 className="font-display text-2xl md:text-3xl leading-tight text-[var(--color-text-primary)] mb-4">
          {title}
        </h3>
        {children}
      </GlassSurface>
    </motion.div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/flow-card.test.tsx`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add web/src/components/landing/flow-card.tsx web/src/components/landing/__tests__/flow-card.test.tsx
git commit -m "feat(web): add FlowCard primitive with scroll-driven depth-of-field"
```

---

### Task 2: Create the ChapterCards component (counter-flow rows)

**Files:**
- Create: `web/src/components/landing/chapter-cards.tsx`
- Test: `web/src/components/landing/__tests__/chapter-cards.test.tsx`

This is the main section component with two counter-flowing rows and mobile interleaving.

**Step 1: Write the failing test**

Create `web/src/components/landing/__tests__/chapter-cards.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, style, ...props }: any) => (
      <div style={style} {...props}>{children}</div>
    ),
  },
  useScroll: () => ({ scrollYProgress: { get: () => 0.5 } }),
  useTransform: (_: any, input: number[], output: any[]) => output[Math.floor(output.length / 2)],
  useReducedMotion: () => false,
}))

import { ChapterCards } from "../chapter-cards"

describe("ChapterCards", () => {
  it("renders the section with data-chapter-cards attribute", () => {
    const { container } = render(<ChapterCards />)
    expect(container.querySelector("[data-chapter-cards]")).toBeInTheDocument()
  })

  it("renders engine row cards", () => {
    render(<ChapterCards />)
    expect(screen.getByText("Raw Signal")).toBeInTheDocument()
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
    expect(screen.getByText("Factor Analysis")).toBeInTheDocument()
    expect(screen.getByText("Sector Normalization")).toBeInTheDocument()
    expect(screen.getByText("Conviction Output")).toBeInTheDocument()
  })

  it("renders proof row cards", () => {
    render(<ChapterCards />)
    expect(screen.getByText("Sample Score")).toBeInTheDocument()
    expect(screen.getByText("Factor Breakdown")).toBeInTheDocument()
    expect(screen.getByText("Growth vs Value")).toBeInTheDocument()
    expect(screen.getByText("Portfolio View")).toBeInTheDocument()
    expect(screen.getByText("Historical Accuracy")).toBeInTheDocument()
  })

  it("renders two row containers on desktop", () => {
    const { container } = render(<ChapterCards />)
    const rows = container.querySelectorAll("[data-card-row]")
    expect(rows).toHaveLength(2)
  })

  it("renders 10 total flow cards", () => {
    const { container } = render(<ChapterCards />)
    const cards = container.querySelectorAll("[data-flow-card]")
    expect(cards).toHaveLength(10)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/chapter-cards.test.tsx`
Expected: FAIL — module `../chapter-cards` not found

**Step 3: Write the ChapterCards component**

Create `web/src/components/landing/chapter-cards.tsx`:

```tsx
"use client"

import { useRef } from "react"
import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion"
import { FlowCard } from "./flow-card"

const engineCards = [
  {
    title: "Raw Signal",
    subtitle: "The Engine",
    content:
      "Earnings transcripts, SEC filings, price targets, institutional flows — hundreds of data points per ticker, gathered and normalized in real time.",
  },
  {
    title: "Elimination Filters",
    subtitle: "The Engine",
    content:
      "Penny stocks, delistings, insufficient data — fail-fast filters eliminate noise before scoring begins. Only investable assets proceed.",
  },
  {
    title: "Factor Analysis",
    subtitle: "The Engine",
    content:
      "Five scoring factors — valuation, quality, momentum, growth, and sentiment — each ranked against sector peers using percentile normalization.",
  },
  {
    title: "Sector Normalization",
    subtitle: "The Engine",
    content:
      "Rank within GICS sector first, then combine. A 60th-percentile bank is compared to banks, not to tech stocks. Sector-neutral by design.",
  },
  {
    title: "Conviction Output",
    subtitle: "The Engine",
    content:
      "A composite conviction score from 0 to 100 with a clear signal: strong buy, buy, hold, or avoid. Factor breakdowns show exactly what's driving it.",
  },
]

const proofCards = [
  {
    title: "Sample Score",
    subtitle: "The Proof",
    content:
      "AAPL scores 78 — Strong Buy. Driven by quality fundamentals and institutional accumulation. Valuation slightly below sector median.",
  },
  {
    title: "Factor Breakdown",
    subtitle: "The Proof",
    content:
      "Valuation 62 · Quality 85 · Momentum 71 · Growth 68 · Sentiment 89. Every factor transparent, every percentile verifiable.",
  },
  {
    title: "Growth vs Value",
    subtitle: "The Proof",
    content:
      "Growth-stage companies weight momentum and growth higher. Mature companies weight valuation and quality. The engine adapts automatically.",
  },
  {
    title: "Portfolio View",
    subtitle: "The Proof",
    content:
      "AAPL 78 · MSFT 72 · GOOGL 65 · NVDA 58 · AMZN 45. Compare conviction across your entire portfolio at a glance.",
  },
  {
    title: "Historical Accuracy",
    subtitle: "The Proof",
    content:
      "Backtest any scoring period against actual returns. No curve-fitting, no survivorship bias. The same deterministic engine, applied historically.",
  },
]

function CardRow({
  cards,
  direction,
  scrollYProgress,
}: {
  cards: typeof engineCards
  direction: "left" | "right"
  scrollYProgress: any
}) {
  const prefersReducedMotion = useReducedMotion()

  const x = useTransform(
    scrollYProgress,
    [0, 1],
    prefersReducedMotion
      ? ["0%", "0%"]
      : direction === "left"
        ? ["20%", "-20%"]
        : ["-20%", "20%"],
  )

  return (
    <motion.div
      data-card-row
      data-direction={direction}
      className="flex gap-6 py-4"
      style={{ x }}
    >
      {cards.map((card) => (
        <FlowCard key={card.title} title={card.title} subtitle={card.subtitle}>
          <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
            {card.content}
          </p>
        </FlowCard>
      ))}
    </motion.div>
  )
}

export function ChapterCards() {
  const sectionRef = useRef<HTMLDivElement>(null)

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  })

  return (
    <section
      ref={sectionRef}
      data-chapter-cards
      id="engine"
      className="relative h-[200vh] overflow-hidden"
    >
      <div className="sticky top-0 h-screen flex flex-col items-center justify-center gap-8">
        {/* Desktop: two counter-flowing rows */}
        <div className="hidden md:block w-full">
          <CardRow
            cards={engineCards}
            direction="left"
            scrollYProgress={scrollYProgress}
          />
          <CardRow
            cards={proofCards}
            direction="right"
            scrollYProgress={scrollYProgress}
          />
        </div>

        {/* Mobile: single interleaved column */}
        <div className="md:hidden flex flex-col items-center gap-4 px-6 max-w-[360px] mx-auto overflow-y-auto max-h-screen py-8">
          {engineCards.map((card, i) => (
            <div key={card.title} className="w-full">
              <FlowCard title={card.title} subtitle={card.subtitle}>
                <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                  {card.content}
                </p>
              </FlowCard>
              {proofCards[i] && (
                <div className="mt-4">
                  <FlowCard
                    title={proofCards[i].title}
                    subtitle={proofCards[i].subtitle}
                  >
                    <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
                      {proofCards[i].content}
                    </p>
                  </FlowCard>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/chapter-cards.test.tsx`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add web/src/components/landing/chapter-cards.tsx web/src/components/landing/__tests__/chapter-cards.test.tsx
git commit -m "feat(web): add ChapterCards with counter-flow scroll animation"
```

---

### Task 3: Update page.tsx to use new 3-section layout

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/components/landing/__tests__/page-assembly.test.tsx`

Replace the 4-chapter layout with 3 sections, remove 50vh spacers, remove ChapterEngine/ChapterProof imports.

**Step 1: Update the page assembly test**

Edit `web/src/components/landing/__tests__/page-assembly.test.tsx` to reflect the new structure:

Replace the entire file with:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/components/landing/fluid-shader-loader", () => ({
  FluidShaderLoader: () => null,
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
    section: ({ children, ...props }: any) => (
      <section {...props}>{children}</section>
    ),
  },
  useInView: () => true,
  useScroll: () => ({ scrollYProgress: { get: () => 0.5 } }),
  useTransform: (_: any, input: number[], output: any[]) => output[Math.floor(output.length / 2)],
  useReducedMotion: () => false,
}))

import Page from "../../../app/page"

describe("Landing page assembly", () => {
  it("renders all 3 chapters", async () => {
    const jsx = await Page()
    render(jsx)
    // Chapter 1: Hero
    expect(screen.getByText("Conviction,")).toBeInTheDocument()
    expect(screen.getByText("Quantified.")).toBeInTheDocument()
    // Chapter 2: Counter-flow cards (engine + proof)
    expect(screen.getByText("Raw Signal")).toBeInTheDocument()
    expect(screen.getByText("Factor Analysis")).toBeInTheDocument()
    expect(screen.getByText("Sample Score")).toBeInTheDocument()
    expect(screen.getByText("Portfolio View")).toBeInTheDocument()
    // Chapter 3: Pricing
    expect(screen.getByText("Scout")).toBeInTheDocument()
    expect(screen.getByText("Operator")).toBeInTheDocument()
    expect(screen.getByText("Allocator")).toBeInTheDocument()
  })

  it("renders the navbar", async () => {
    const jsx = await Page()
    render(jsx)
    const nav = screen.getByRole("navigation", { name: "Main navigation" })
    expect(nav).toBeInTheDocument()
  })

  it("has no 50vh chapter break spacers", async () => {
    const jsx = await Page()
    const { container } = render(jsx)
    const breaks = container.querySelectorAll(".h-\\[50vh\\]")
    expect(breaks.length).toBe(0)
  })

  it("renders chapter indicator with 3 chapters", async () => {
    const jsx = await Page()
    render(jsx)
    expect(screen.getByLabelText("Page chapters")).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/page-assembly.test.tsx`
Expected: FAIL — still rendering old 4-chapter layout with spacers

**Step 3: Update page.tsx**

Replace the content of `web/src/app/page.tsx` with:

```tsx
import { auth } from "@/lib/auth"
import { Navbar } from "@/components/nav/navbar"
import { DNAProvider } from "@/components/landing/dna-provider"
import { FluidShaderLoader } from "@/components/landing/fluid-shader-loader"
import { ChapterHero } from "@/components/landing/chapter-hero"
import { ChapterCards } from "@/components/landing/chapter-cards"
import { ChapterPath } from "@/components/landing/chapter-path"
import { ChapterIndicator } from "@/components/landing/chapter-indicator"

async function getDNA() {
  try {
    const session = await auth()
    if (!session) return null
    const res = await fetch(`${process.env.API_URL || "http://localhost:8000"}/api/v1/users/me/dna`, {
      headers: {
        "X-User-Id": String((session as any).userId || ""),
        "X-User-Email": (session as any).user?.email || "",
      },
      next: { revalidate: 3600 },
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export default async function Home() {
  const dna = await getDNA()

  return (
    <DNAProvider dna={dna}>
      <main>
        <FluidShaderLoader
          baseColor={dna?.base}
          midColor={dna?.mid}
          accentColor={dna?.accent}
          tempo={dna?.tempo}
          density={dna?.density}
        />
        <Navbar />
        <div className="relative z-10">
          <ChapterHero />
          <ChapterCards />
          <div className="py-16">
            <ChapterPath />
          </div>
        </div>
        <ChapterIndicator
          chapters={3}
          activeChapter={0}
          labels={["The Signal", "The Engine", "The Path"]}
        />
      </main>
    </DNAProvider>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/page-assembly.test.tsx`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add web/src/app/page.tsx web/src/components/landing/__tests__/page-assembly.test.tsx
git commit -m "feat(web): replace 4-chapter layout with 3-section counter-flow layout"
```

---

### Task 4: Update ChapterIndicator test for 3 chapters

**Files:**
- Modify: `web/src/components/landing/__tests__/chapter-indicator.test.tsx`

The ChapterIndicator component is generic (takes `chapters` as a prop), so no code change is needed — only the test should verify the new 3-chapter usage works.

**Step 1: Update the test**

Edit `web/src/components/landing/__tests__/chapter-indicator.test.tsx`:

Add a new test case after the existing ones:

```tsx
  it("works with 3 chapters for new layout", () => {
    const { container } = render(
      <ChapterIndicator
        chapters={3}
        activeChapter={0}
        labels={["The Signal", "The Engine", "The Path"]}
      />,
    )
    const dots = container.querySelectorAll("[data-chapter-dot]")
    expect(dots).toHaveLength(3)
  })
```

**Step 2: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/chapter-indicator.test.tsx`
Expected: PASS (4 tests)

**Step 3: Commit**

```bash
git add web/src/components/landing/__tests__/chapter-indicator.test.tsx
git commit -m "test(web): add 3-chapter indicator test for new layout"
```

---

### Task 5: Update existing landing tests for removed components

**Files:**
- Modify: `web/src/components/landing/__tests__/chapter-engine.test.tsx`
- Modify: `web/src/components/landing/__tests__/chapter-proof.test.tsx`
- Modify: `web/src/components/landing/__tests__/horizontal-scroll.test.tsx`

These test files reference components that still exist in the codebase (we're not deleting the files yet — they're just unused by page.tsx). However, if the project removes them, these tests should be removed too. For now, verify the full test suite passes with all changes.

**Step 1: Run the full landing test suite**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run web/src/components/landing/__tests__/`
Expected: ALL PASS — old component tests still pass (components still exist), new tests pass

**Step 2: Run the full web test suite to check for regressions**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run`
Expected: ALL PASS

**Step 3: Commit (if any fixes were needed)**

Only commit if fixes were required. Otherwise skip.

---

### Task 6: Clean up removed components

**Files:**
- Delete: `web/src/components/landing/chapter-engine.tsx`
- Delete: `web/src/components/landing/chapter-proof.tsx`
- Delete: `web/src/components/landing/horizontal-scroll.tsx`
- Delete: `web/src/components/landing/__tests__/chapter-engine.test.tsx`
- Delete: `web/src/components/landing/__tests__/chapter-proof.test.tsx`
- Delete: `web/src/components/landing/__tests__/horizontal-scroll.test.tsx`

**Step 1: Verify no other files import the removed components**

Run grep for imports of these components across the codebase:
- Search for `chapter-engine` in `web/src/`
- Search for `chapter-proof` in `web/src/`
- Search for `horizontal-scroll` in `web/src/`

Expected: Only the deleted files and their tests reference these. `page.tsx` no longer imports them (updated in Task 3).

**Step 2: Delete the files**

```bash
rm web/src/components/landing/chapter-engine.tsx
rm web/src/components/landing/chapter-proof.tsx
rm web/src/components/landing/horizontal-scroll.tsx
rm web/src/components/landing/__tests__/chapter-engine.test.tsx
rm web/src/components/landing/__tests__/chapter-proof.test.tsx
rm web/src/components/landing/__tests__/horizontal-scroll.test.tsx
```

**Step 3: Run full test suite**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add -u web/src/components/landing/
git commit -m "refactor(web): remove ChapterEngine, ChapterProof, HorizontalScroll"
```

---

### Task 7: Visual smoke test and tuning

**Files:**
- Possibly modify: `web/src/components/landing/chapter-cards.tsx`
- Possibly modify: `web/src/components/landing/flow-card.tsx`

**Step 1: Start the dev server**

Run: `cd /Users/brandon/repos/margin_invest/web && npx next dev`

**Step 2: Open browser and verify**

Open `http://localhost:3000` and check:
- [ ] Hero section renders full-screen with word reveal animation
- [ ] Scrolling past hero immediately shows counter-flow cards
- [ ] Top row moves left as you scroll down
- [ ] Bottom row moves right as you scroll down
- [ ] Cards nearest viewport center are fully opaque and sharp
- [ ] Cards at edges are faded and blurred
- [ ] Pricing section appears after cards with minimal gap
- [ ] Chapter indicator shows 3 dots
- [ ] Mobile (resize to <768px): single column, cards interleaved, no horizontal motion
- [ ] `prefers-reduced-motion`: no horizontal translation, no blur, opacity still works
- [ ] Fluid shader background visible behind glass cards

**Step 3: Tune values if needed**

Adjust these values based on visual feel:
- `translateX` range (currently `±20%`) — increase for more dramatic motion, decrease for subtlety
- Opacity curve breakpoints (currently `0.15` at edges) — increase if too faded
- Blur amount (currently `4px` max) — adjust if too heavy or too light
- Section height (currently `200vh`) — adjust scroll distance for motion speed
- Card gap and sizing

**Step 4: Run tests one final time**

Run: `cd /Users/brandon/repos/margin_invest && npx vitest run`
Expected: ALL PASS

**Step 5: Commit any tuning changes**

```bash
git add web/src/components/landing/
git commit -m "fix(web): tune counter-flow card animation values"
```
