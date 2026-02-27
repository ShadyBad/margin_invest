# Methodology & Guides Content Rework — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure and rewrite all public educational content (methodology page + guides) with progressive disclosure, V4 pipeline accuracy, and three-audience accessibility.

**Architecture:** Methodology page becomes a narrative spine (one stock's journey through the pipeline) with expandable `<TechnicalDetail>` panels. Guides split into Concepts, Workflows, and Reference categories. Three new MDX components (`TechnicalDetail`, `VerifyItYourself`, `KnownLimitations`). New Glossary page with linkable term anchors. Guide index page gets category tabs.

**Tech Stack:** Next.js 15, MDX via `next-mdx-remote/rsc`, Tailwind v4, Framer Motion, Vitest + Testing Library

**Design doc:** `docs/plans/2026-02-26-methodology-guides-rework-design.md`

---

## Task Groups

- **Group A (Infrastructure):** Tasks 1-3 — New MDX components, glossary infrastructure, guide category system
- **Group B (Methodology Rewrite):** Tasks 4-5 — Rewrite methodology page sections with narrative spine and expandable technical details
- **Group C (Concept Guides):** Tasks 6-11 — Write/rewrite all concept guides
- **Group D (Workflow Guides):** Tasks 12-16 — Write/rewrite all workflow guides
- **Group E (Visual Updates):** Task 17 — Update methodology visuals for V4 pipeline
- **Group F (Integration):** Task 18 — Wire updated in-app metadata, verify links, update frontmatter

**Dependencies:** Group A must complete first. Groups B, C, D can run in parallel after A. Group E can run in parallel with B/C/D. Group F runs last.

---

### Task 1: Build TechnicalDetail MDX Component

**Files:**
- Create: `web/src/components/guides/technical-detail.tsx`
- Modify: `web/src/components/guides/mdx-components.tsx`
- Test: `web/src/components/guides/__tests__/technical-detail.test.tsx`

**Step 1: Write the failing test**

```tsx
// web/src/components/guides/__tests__/technical-detail.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { TechnicalDetail } from "../technical-detail"

describe("TechnicalDetail", () => {
  it("renders collapsed by default with summary visible", () => {
    render(
      <TechnicalDetail summary="Scoring formula">
        <p>ROIC = NOPAT / Invested Capital</p>
      </TechnicalDetail>
    )
    expect(screen.getByText("Scoring formula")).toBeInTheDocument()
    expect(screen.queryByText("ROIC = NOPAT / Invested Capital")).not.toBeVisible()
  })

  it("expands when clicked to show children", async () => {
    const user = userEvent.setup()
    render(
      <TechnicalDetail summary="Scoring formula">
        <p>ROIC = NOPAT / Invested Capital</p>
      </TechnicalDetail>
    )
    await user.click(screen.getByText("Scoring formula"))
    expect(screen.getByText("ROIC = NOPAT / Invested Capital")).toBeVisible()
  })

  it("collapses when clicked again", async () => {
    const user = userEvent.setup()
    render(
      <TechnicalDetail summary="Scoring formula">
        <p>ROIC = NOPAT / Invested Capital</p>
      </TechnicalDetail>
    )
    await user.click(screen.getByText("Scoring formula"))
    await user.click(screen.getByText("Scoring formula"))
    expect(screen.queryByText("ROIC = NOPAT / Invested Capital")).not.toBeVisible()
  })

  it("renders with open prop when provided", () => {
    render(
      <TechnicalDetail summary="Always open" defaultOpen>
        <p>Visible content</p>
      </TechnicalDetail>
    )
    expect(screen.getByText("Visible content")).toBeVisible()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/guides/__tests__/technical-detail.test.tsx`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```tsx
// web/src/components/guides/technical-detail.tsx
"use client"

import { useState, type ReactNode } from "react"

interface TechnicalDetailProps {
  summary: string
  children: ReactNode
  defaultOpen?: boolean
}

export function TechnicalDetail({ summary, children, defaultOpen = false }: TechnicalDetailProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="my-6 rounded-lg border border-border-subtle overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-text-primary bg-bg-subtle hover:bg-bg-elevated transition-colors"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <span className="text-accent text-xs font-mono">{"{ }"}</span>
          {summary}
        </span>
        <svg
          className={`h-4 w-4 text-text-tertiary transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div
        className={`overflow-hidden transition-all ${open ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0"}`}
        role="region"
        aria-hidden={!open}
      >
        <div className="px-4 py-4 border-t border-border-subtle text-sm">
          {children}
        </div>
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/guides/__tests__/technical-detail.test.tsx`
Expected: PASS (4 tests)

**Step 5: Register in mdx-components.tsx**

Add `TechnicalDetail` to the `mdxComponents` object in `web/src/components/guides/mdx-components.tsx`:

```tsx
import { TechnicalDetail } from "./technical-detail"

// Add to the mdxComponents object:
TechnicalDetail,
```

**Step 6: Commit**

```bash
git add web/src/components/guides/technical-detail.tsx web/src/components/guides/__tests__/technical-detail.test.tsx web/src/components/guides/mdx-components.tsx
git commit -m "feat(web): add TechnicalDetail expandable MDX component"
```

---

### Task 2: Build VerifyItYourself and KnownLimitations MDX Components

**Files:**
- Create: `web/src/components/guides/verify-it-yourself.tsx`
- Create: `web/src/components/guides/known-limitations.tsx`
- Modify: `web/src/components/guides/mdx-components.tsx`
- Test: `web/src/components/guides/__tests__/verify-it-yourself.test.tsx`
- Test: `web/src/components/guides/__tests__/known-limitations.test.tsx`

**Step 1: Write failing tests**

```tsx
// web/src/components/guides/__tests__/verify-it-yourself.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { VerifyItYourself } from "../verify-it-yourself"

describe("VerifyItYourself", () => {
  it("renders claim and verification steps", () => {
    render(
      <VerifyItYourself claim="Deterministic scoring">
        Enter the same ticker twice. Scores will match.
      </VerifyItYourself>
    )
    expect(screen.getByText("Deterministic scoring")).toBeInTheDocument()
    expect(screen.getByText(/Enter the same ticker twice/)).toBeInTheDocument()
  })

  it("renders verify-it-yourself label", () => {
    render(
      <VerifyItYourself claim="Test claim">Steps here</VerifyItYourself>
    )
    expect(screen.getByText("Verify it yourself")).toBeInTheDocument()
  })
})
```

```tsx
// web/src/components/guides/__tests__/known-limitations.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { KnownLimitations } from "../known-limitations"

describe("KnownLimitations", () => {
  it("renders heading and children", () => {
    render(
      <KnownLimitations>
        <li>ML models need 90+ days of data</li>
      </KnownLimitations>
    )
    expect(screen.getByText("Known Limitations")).toBeInTheDocument()
    expect(screen.getByText(/ML models need 90/)).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/guides/__tests__/verify-it-yourself.test.tsx src/components/guides/__tests__/known-limitations.test.tsx`
Expected: FAIL — modules not found

**Step 3: Implement both components**

```tsx
// web/src/components/guides/verify-it-yourself.tsx
import type { ReactNode } from "react"

interface VerifyItYourselfProps {
  claim: string
  children: ReactNode
}

export function VerifyItYourself({ claim, children }: VerifyItYourselfProps) {
  return (
    <div className="my-6 rounded-lg border border-accent/30 bg-accent/5 px-5 py-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-accent text-sm font-mono">&#10003;</span>
        <span className="text-xs font-semibold uppercase tracking-wider text-accent">
          Verify it yourself
        </span>
      </div>
      <p className="font-semibold text-text-primary mb-2">{claim}</p>
      <div className="text-sm text-text-secondary leading-relaxed">{children}</div>
    </div>
  )
}
```

```tsx
// web/src/components/guides/known-limitations.tsx
import type { ReactNode } from "react"

interface KnownLimitationsProps {
  children: ReactNode
}

export function KnownLimitations({ children }: KnownLimitationsProps) {
  return (
    <div className="my-6 rounded-lg border border-warning/30 bg-warning/5 px-5 py-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-warning text-sm">&#9888;</span>
        <span className="text-xs font-semibold uppercase tracking-wider text-warning">
          Known Limitations
        </span>
      </div>
      <div className="text-sm text-text-secondary leading-relaxed">{children}</div>
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/guides/__tests__/verify-it-yourself.test.tsx src/components/guides/__tests__/known-limitations.test.tsx`
Expected: PASS (3 tests total)

**Step 5: Register both in mdx-components.tsx**

Add imports and entries to `mdxComponents` in `web/src/components/guides/mdx-components.tsx`:

```tsx
import { VerifyItYourself } from "./verify-it-yourself"
import { KnownLimitations } from "./known-limitations"

// Add to the mdxComponents object:
VerifyItYourself,
KnownLimitations,
```

**Step 6: Commit**

```bash
git add web/src/components/guides/verify-it-yourself.tsx web/src/components/guides/known-limitations.tsx web/src/components/guides/__tests__/verify-it-yourself.test.tsx web/src/components/guides/__tests__/known-limitations.test.tsx web/src/components/guides/mdx-components.tsx
git commit -m "feat(web): add VerifyItYourself and KnownLimitations MDX components"
```

---

### Task 3: Build Glossary Page and Guide Category Tabs

**Files:**
- Create: `web/src/content/guides/glossary.mdx`
- Create: `web/src/components/guides/guide-category-tabs.tsx`
- Modify: `web/src/app/guides/page.tsx` — add category tabs
- Modify: `web/src/lib/guides.ts` — add category constants, guide category grouping function
- Test: `web/src/components/guides/__tests__/guide-category-tabs.test.tsx`
- Test: `web/src/lib/__tests__/guides.test.ts` — add tests for new grouping function

**Step 1: Write failing tests for guide category grouping**

Add to `web/src/lib/__tests__/guides.test.ts`:

```typescript
describe("groupGuidesByCategory", () => {
  it("groups guides into Concepts, Workflows, and Reference", async () => {
    const { groupGuidesByCategory } = await import("../guides")
    const guides = [
      { slug: "a", category: "Concepts", title: "A", description: "", order: 1, updatedAt: "", readingTime: 1 },
      { slug: "b", category: "Workflows", title: "B", description: "", order: 2, updatedAt: "", readingTime: 1 },
      { slug: "c", category: "Reference", title: "C", description: "", order: 3, updatedAt: "", readingTime: 1 },
      { slug: "d", category: "Concepts", title: "D", description: "", order: 4, updatedAt: "", readingTime: 1 },
    ]
    const grouped = groupGuidesByCategory(guides)
    expect(grouped.Concepts).toHaveLength(2)
    expect(grouped.Workflows).toHaveLength(1)
    expect(grouped.Reference).toHaveLength(1)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/lib/__tests__/guides.test.ts`
Expected: FAIL — `groupGuidesByCategory` not exported

**Step 3: Implement groupGuidesByCategory in guides.ts**

Add to `web/src/lib/guides.ts`:

```typescript
export const GUIDE_CATEGORIES = ["Concepts", "Workflows", "Reference"] as const
export type GuideCategory = (typeof GUIDE_CATEGORIES)[number]

export function groupGuidesByCategory(
  guides: GuideMetadata[]
): Record<GuideCategory, GuideMetadata[]> {
  const grouped: Record<GuideCategory, GuideMetadata[]> = {
    Concepts: [],
    Workflows: [],
    Reference: [],
  }
  for (const guide of guides) {
    const cat = guide.category as GuideCategory
    if (cat in grouped) {
      grouped[cat].push(guide)
    }
  }
  return grouped
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/lib/__tests__/guides.test.ts`
Expected: PASS

**Step 5: Write failing test for GuideCategoryTabs component**

```tsx
// web/src/components/guides/__tests__/guide-category-tabs.test.tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { GuideCategoryTabs } from "../guide-category-tabs"

const mockGrouped = {
  Concepts: [
    { slug: "filters", title: "Elimination Filters", description: "Filter desc", order: 1, updatedAt: "2026-02-26", readingTime: 5, category: "Concepts" },
  ],
  Workflows: [
    { slug: "getting-started", title: "Getting Started", description: "Start desc", order: 1, updatedAt: "2026-02-26", readingTime: 3, category: "Workflows" },
  ],
  Reference: [
    { slug: "glossary", title: "Glossary", description: "Terms", order: 1, updatedAt: "2026-02-26", readingTime: 10, category: "Reference" },
  ],
}

describe("GuideCategoryTabs", () => {
  it("renders all three category tabs", () => {
    render(<GuideCategoryTabs grouped={mockGrouped} />)
    expect(screen.getByRole("tab", { name: /concepts/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /workflows/i })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: /reference/i })).toBeInTheDocument()
  })

  it("shows Concepts guides by default", () => {
    render(<GuideCategoryTabs grouped={mockGrouped} />)
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
  })

  it("switches to Workflows tab when clicked", async () => {
    const user = userEvent.setup()
    render(<GuideCategoryTabs grouped={mockGrouped} />)
    await user.click(screen.getByRole("tab", { name: /workflows/i }))
    expect(screen.getByText("Getting Started")).toBeInTheDocument()
  })
})
```

**Step 6: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/guides/__tests__/guide-category-tabs.test.tsx`
Expected: FAIL — module not found

**Step 7: Implement GuideCategoryTabs**

```tsx
// web/src/components/guides/guide-category-tabs.tsx
"use client"

import { useState } from "react"
import { GuideCard } from "./guide-card"
import { GUIDE_CATEGORIES, type GuideCategory, type GuideMetadata } from "@/lib/guides"

interface GuideCategoryTabsProps {
  grouped: Record<GuideCategory, GuideMetadata[]>
}

export function GuideCategoryTabs({ grouped }: GuideCategoryTabsProps) {
  const [active, setActive] = useState<GuideCategory>("Concepts")

  return (
    <div>
      <div role="tablist" className="flex gap-1 mb-8 border-b border-border-subtle">
        {GUIDE_CATEGORIES.map((cat) => (
          <button
            key={cat}
            role="tab"
            aria-selected={active === cat}
            onClick={() => setActive(cat)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              active === cat
                ? "border-accent text-accent"
                : "border-transparent text-text-tertiary hover:text-text-secondary"
            }`}
          >
            {cat}
            <span className="ml-1.5 text-xs text-text-tertiary">({grouped[cat].length})</span>
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        {grouped[active].map((guide, i) => (
          <GuideCard key={guide.slug} guide={guide} index={i} />
        ))}
      </div>
    </div>
  )
}
```

**Step 8: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/guides/__tests__/guide-category-tabs.test.tsx`
Expected: PASS (3 tests)

**Step 9: Update guides index page to use category tabs**

Modify `web/src/app/guides/page.tsx` to import `groupGuidesByCategory` and `GuideCategoryTabs`, replace the flat grid with the tabbed view. The server component calls `groupGuidesByCategory(guides)` and passes the result to the client `GuideCategoryTabs` component.

**Step 10: Create glossary MDX file**

Create `web/src/content/guides/glossary.mdx` with frontmatter:

```yaml
---
title: "Glossary"
description: "Definitions for every term used across Margin Invest methodology and guides."
order: 1
updatedAt: "2026-02-26"
readingTime: 12
category: "Reference"
---
```

Populate with all terms from `filter-metadata.ts`, `sub-factor-formulas.ts`, and existing guide content. Each term gets an `<h3>` with a slugified ID for deep linking (e.g., `### ROIC` → `#roic`). Group alphabetically.

Key terms to include: Altman Z-Score, Asymmetry Ratio, Beneish M-Score, Catalyst Strength, Compounder, Conviction Level, Current Ratio, DCF Margin of Safety, Elimination Filter, Enterprise Value, EV/FCF, Free Cash Flow, Growth Gap, Growth Stage, Interest Coverage, Invested Capital, Mispricing, Moat Durability Score, NOPAT, Piotroski F-Score, Percentile Rank, Position Sizing, ROIC, Sector-Neutral Scoring, Shareholder Yield, Track A, Track B, V4 Pipeline.

**Step 11: Commit**

```bash
git add web/src/lib/guides.ts web/src/lib/__tests__/guides.test.ts web/src/components/guides/guide-category-tabs.tsx web/src/components/guides/__tests__/guide-category-tabs.test.tsx web/src/app/guides/page.tsx web/src/content/guides/glossary.mdx
git commit -m "feat(web): add glossary page and guide category tabs"
```

---

### Task 4: Rewrite Methodology Page — Narrative Spine (Sections 1-4)

**Files:**
- Modify: `web/src/components/methodology/sections/hero-section.tsx`
- Modify: `web/src/components/methodology/sections/universe-section.tsx`
- Modify: `web/src/components/methodology/sections/filters-section.tsx`
- Modify: `web/src/components/methodology/sections/pipeline-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx`

**Context:** The methodology page currently has 10 marketing-style sections. We're rewriting them as a narrative — following a stock (use "AAPL" as the running example) through the pipeline. Each section gets a plain-English summary visible by default, with expandable technical detail panels.

**Step 1: Read all four existing section files**

Read the current implementations to understand the Framer Motion patterns, styling tokens, and visual component integrations used. Preserve animation patterns and design token usage.

**Step 2: Rewrite HeroSection**

Update the headline and copy to set up the narrative:
- Headline: "From 7,000+ stocks to the ones worth your attention"
- Subhead: "Follow one stock through our entire scoring pipeline — every filter, every factor, every decision — to see exactly how conviction scores are built."
- Remove "Built for" vs "Not built for" grid (move to a FAQ or separate section)
- Add a "Pipeline Version: V4" badge and last-updated date
- Keep the CTA buttons

**Step 3: Rewrite PipelineSection as the narrative opener**

Replace the generic pipeline diagram intro with narrative framing:
- "Let's follow Apple (AAPL) through the pipeline. At every stage, we'll show you exactly what the system checks and what it finds."
- Update pipeline stages to include ML Refinement and 13F Smart Money Overlay (7 stages, not 4)
- Each stage in the diagram links/scrolls to its detailed section below

**Step 4: Rewrite UniverseSection with concrete numbers**

Narrative style: "Every morning at market open, the pipeline evaluates 7,000+ US-listed equities. AAPL is one of them. To even enter scoring, a stock must pass six elimination filters."

Add a `<TechnicalDetail>` expandable with: data sources, update cadence, universe construction rules.

**Step 5: Rewrite FiltersSection as narrative stage**

Narrative: "AAPL faces six binary pass/fail checks. One failure = immediate elimination. No exceptions."

Show AAPL passing each filter with concrete values:
- Beneish M-Score: -2.41 (threshold: < -1.78) — PASS
- Altman Z-Score: 5.12 (threshold: > 1.1) — PASS
- etc.

Add `<TechnicalDetail>` expandable for each filter: formula, academic citation, sector adjustment rules.

**Step 6: Update tests**

Update `web/src/components/methodology/__tests__/sections.test.tsx` to reflect new text content. Tests should verify:
- HeroSection renders the narrative headline
- PipelineSection shows 7 stages (not 4)
- UniverseSection mentions 7,000+ equities
- FiltersSection renders all 6 filter names

**Step 7: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: PASS

**Step 8: Commit**

```bash
git add web/src/components/methodology/sections/hero-section.tsx web/src/components/methodology/sections/universe-section.tsx web/src/components/methodology/sections/filters-section.tsx web/src/components/methodology/sections/pipeline-section.tsx web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "feat(web): rewrite methodology sections 1-4 with narrative spine"
```

---

### Task 5: Rewrite Methodology Page — Narrative Spine (Sections 5-10)

**Files:**
- Modify: `web/src/components/methodology/sections/scoring-section.tsx`
- Modify: `web/src/components/methodology/sections/conviction-section.tsx`
- Modify: `web/src/components/methodology/sections/outputs-section.tsx`
- Modify: `web/src/components/methodology/sections/usage-section.tsx`
- Modify: `web/src/components/methodology/sections/transparency-section.tsx`
- Modify: `web/src/components/methodology/sections/cta-section.tsx`
- Create: `web/src/components/methodology/sections/ml-refinement-section.tsx` — NEW
- Create: `web/src/components/methodology/sections/smart-money-section.tsx` — NEW
- Modify: `web/src/components/methodology/index.ts` — add new exports
- Modify: `web/src/app/methodology/page.tsx` — add new sections to page
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx`

**Step 1: Read all existing section files**

Read scoring, conviction, outputs, usage, transparency, and CTA sections.

**Step 2: Rewrite ScoringSection**

Narrative: "AAPL passed all filters. Now it enters multi-factor scoring across three pillars."

Show AAPL's factor scores across Quality (7 factors), Value (7 factors), Momentum (6 factors) with concrete example values. Each pillar has a `<TechnicalDetail>` expandable listing all factors, formulas, and citations. Reference the Scoring Factors concept guide for full detail.

**Step 3: Rewrite ConvictionSection**

Narrative: "With factor scores in hand, AAPL enters the dual-track conviction system."

Walk through AAPL's path through Track A (Compounder) and Track B (Mispricing) gates. Show which gates it passes and how the multiplicative score is calculated. Add `<TechnicalDetail>` expandable with gate thresholds and formulas.

**Step 4: Create MLRefinementSection (NEW)**

Narrative: "The deterministic scores are now adjusted by machine learning models trained on the system's own prediction history."

Explain at a high level: cluster models group similar stocks, VAE identifies anomalous patterns, rank IC validates model quality. Only models with rank IC > 0.15 are used. Show that AAPL's score may be adjusted up or down based on ML signals, but the adjustment is bounded and auditable.

Add `<TechnicalDetail>` expandable with: model training cadence (Saturday 2AM UTC), minimum data requirements (90 days), rank IC threshold, cluster model and VAE architecture overview.

**Step 5: Create SmartMoneySection (NEW)**

Narrative: "Finally, the system checks what institutional investors are doing with AAPL."

Explain 13F filings, accumulation signals, and how institutional positioning feeds into the catalyst strength score. Show that accumulation is one input to momentum scoring, not a standalone signal.

Add `<TechnicalDetail>` expandable with: 13F filing mechanics, 45-day lag, curated manager list criteria, accumulation percentile calculation.

**Step 6: Rewrite OutputsSection**

Narrative: "After all stages, AAPL receives its final output." Show: conviction level (e.g., HIGH), opportunity type (e.g., Compounder), suggested position size (e.g., 8%), factor breakdown. Explain what each output means and how to act on it.

**Step 7: Rewrite UsageSection and TransparencySection**

UsageSection: Brief framing of "how to use these outputs" with links to workflow guides.

TransparencySection: Strengthen with `<VerifyItYourself>` blocks:
- "Enter AAPL today and tomorrow. Same data = same scores."
- "Check the factor breakdown. Every number traces to a formula in our guides."
- "Read our Known Limitations. We tell you what we can't do."

**Step 8: Update barrel exports and methodology page**

Add `MLRefinementSection` and `SmartMoneySection` to `web/src/components/methodology/index.ts` exports and to the page layout in `web/src/app/methodology/page.tsx`. Order: Hero → Pipeline → Universe → Filters → Scoring → Conviction → ML Refinement → Smart Money → Outputs → Usage → Transparency → CTA (12 sections total).

**Step 9: Update tests**

Add test cases for the two new sections. Update existing test cases for rewritten sections.

**Step 10: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx`
Expected: PASS

**Step 11: Commit**

```bash
git add web/src/components/methodology/
git commit -m "feat(web): rewrite methodology sections 5-10, add ML and smart money sections"
```

---

### Task 6: Rewrite Elimination Filters Concept Guide

**Files:**
- Modify: `web/src/content/guides/elimination-filters.mdx`

**Step 1: Read current guide**

Read `web/src/content/guides/elimination-filters.mdx` (133 lines).

**Step 2: Rewrite with new structure**

Update frontmatter:
```yaml
---
title: "Elimination Filters"
description: "Six binary pass/fail checks that remove financially distressed, manipulated, or illiquid stocks before scoring begins."
order: 1
updatedAt: "2026-02-26"
readingTime: 7
category: "Concepts"
---
```

Structure each filter section with:
1. Plain-English one-sentence summary
2. What it measures and why it matters
3. `<Formula>` block with the formula
4. `<TechnicalDetail>` expandable with: threshold values, sector-specific adjustments, academic citation, edge cases
5. `<Example>` block with a concrete stock example

End with `<KnownLimitations>`:
- Sector-adjusted thresholds may not perfectly fit every sub-industry
- REITs and financial companies have different capital structures
- Newly IPO'd companies may lack sufficient history

**Step 3: Verify rendering**

Run: `cd web && npx next build` (or dev server) and visit `/guides/elimination-filters` to verify rendering.

**Step 4: Commit**

```bash
git add web/src/content/guides/elimination-filters.mdx
git commit -m "docs(web): rewrite elimination filters guide with progressive disclosure"
```

---

### Task 7: Create Scoring Factors Concept Guide (replaces Metrics & Terminology)

**Files:**
- Create: `web/src/content/guides/scoring-factors.mdx`
- Delete: `web/src/content/guides/metrics-and-terminology.mdx` (content migrated to scoring-factors + glossary)

**Step 1: Read current metrics-and-terminology.mdx**

Read `web/src/content/guides/metrics-and-terminology.mdx` (242 lines) and `web/src/lib/sub-factor-formulas.ts` for all factor formulas and citations.

**Step 2: Create scoring-factors.mdx**

Frontmatter:
```yaml
---
title: "Scoring Factors"
description: "All 20 factors across Quality, Value, and Momentum pillars — formulas, academic sources, and what each one measures."
order: 2
updatedAt: "2026-02-26"
readingTime: 15
category: "Concepts"
---
```

Organize by pillar:
- **Quality** (7 factors): Gross Profitability, ROIC-WACC Spread, Earnings Quality, Piotroski F-Score, Accrual Ratio, Moat Durability, ROIC Stability
- **Value** (7 factors): DCF Margin of Safety, EV/FCF, Acquirer's Multiple, Owner Earnings Yield, Shareholder Yield, Growth Gap, Asset Floor
- **Momentum** (6 factors): Price Momentum, Standardized Unexpected Earnings, Insider Cluster Score, Institutional Accumulation, Sentiment Score, Runway Score

Each factor gets:
1. One-sentence plain-English explanation
2. `<Formula>` with the math
3. Citation (from `sub-factor-formulas.ts`)
4. `<TechnicalDetail>` with: why this factor predicts returns, sector normalization notes, percentile ranking method

End with `<KnownLimitations>`:
- Insider and institutional data have reporting lags
- Some factors are more predictive in certain market regimes
- Percentile ranks are relative to sector peers, not absolute

**Step 3: Delete old metrics-and-terminology.mdx**

Terms from this file have been migrated to the Glossary (Task 3) and factor details to scoring-factors.mdx.

**Step 4: Commit**

```bash
git add web/src/content/guides/scoring-factors.mdx
git rm web/src/content/guides/metrics-and-terminology.mdx
git commit -m "docs(web): replace metrics guide with comprehensive scoring factors guide"
```

---

### Task 8: Create Conviction & Tracks Concept Guide

**Files:**
- Create: `web/src/content/guides/conviction-and-tracks.mdx`

**Step 1: Read how-scoring-works.mdx for conviction content**

Read `web/src/content/guides/how-scoring-works.mdx` — extract the dual-track and conviction sections.

**Step 2: Create conviction-and-tracks.mdx**

Frontmatter:
```yaml
---
title: "Conviction & Tracks"
description: "How the dual-track system evaluates stocks as Compounders, Mispricings, or Both — and determines conviction levels."
order: 3
updatedAt: "2026-02-26"
readingTime: 10
category: "Concepts"
---
```

Content sections:
- **The Dual-Track System**: Why two tracks (different investment theses require different evidence)
- **Track A — Compounder**: 4 gates (moat evidence, reinvestment engine, capital allocation, valuation/growth gap). Each gate: what it checks, threshold, formula in `<TechnicalDetail>`
- **Track B — Mispricing**: 4 gates (ensemble valuation, downside protection, catalyst, quality floor). Same structure.
- **Multiplicative Scoring**: Why multiplication (one weak gate kills the score). `<Formula>` with worked example.
- **Conviction Levels**: EXCEPTIONAL, HIGH, WATCHLIST, NONE — thresholds and meaning
- **Opportunity Types**: Compounder, Mispricing, Both, Neither — what each means for holding period and position sizing

Include `<Example>` with a stock scoring through both tracks. End with `<VerifyItYourself>` block showing how to check a stock's gate-by-gate breakdown on the asset detail page.

**Step 3: Commit**

```bash
git add web/src/content/guides/conviction-and-tracks.mdx
git commit -m "docs(web): add conviction and tracks concept guide"
```

---

### Task 9: Create ML Pipeline Concept Guide (NEW)

**Files:**
- Create: `web/src/content/guides/ml-pipeline.mdx`

**Step 1: Read ML-related code for accuracy**

Read these files to understand the actual ML pipeline:
- `engine/src/margin_engine/services/v4_scoring.py` — V4 scoring with ML adjustments
- `engine/src/margin_engine/ml/` — ML model implementations
- `api/src/margin_api/workers.py` — `train_ml_models` job
- Design doc: `docs/plans/2026-02-24-ml-pipeline-fix-and-frontend-visibility-design.md`

**Step 2: Create ml-pipeline.mdx**

Frontmatter:
```yaml
---
title: "ML Pipeline"
description: "How machine learning models are trained on Margin Invest's own scoring history to refine predictions — and why they're optional."
order: 4
updatedAt: "2026-02-26"
readingTime: 8
category: "Concepts"
---
```

Content sections:
- **Why ML?**: Deterministic scoring captures known factors. ML captures patterns humans haven't codified. But it's additive — deterministic scores come first.
- **Training Process**: Weekly training (Saturday 2AM UTC). Models train on 90+ days of scoring history. Only activated when rank IC > 0.15 (predictive quality threshold).
- **Cluster Models**: Group stocks with similar factor profiles. Identify which combinations predict outperformance.
- **VAE (Variational Autoencoder)**: Detect anomalous scoring patterns — stocks that look different from their cluster peers.
- **Score Adjustment**: ML models can adjust the deterministic score up or down. Adjustment is bounded and visible in the ML Audit Panel.
- **Graceful Degradation**: First V4 run falls back to rules-only scoring if no qualified model exists. System works with or without ML.

Each section gets a `<TechnicalDetail>` expandable with implementation details.

End with `<KnownLimitations>`:
- Models need 90+ days of scoring data before activation
- Rank IC threshold (0.15) means models may not activate for months
- ML adjustments are correlational, not causal
- Models retrain weekly — scores may shift on weekends

Include `<VerifyItYourself>`: "Check any stock's asset detail page. If ML is active, you'll see an 'ML Adjusted' badge on the conviction panel with the adjustment amount."

**Step 3: Commit**

```bash
git add web/src/content/guides/ml-pipeline.mdx
git commit -m "docs(web): add ML pipeline concept guide"
```

---

### Task 10: Create Institutional Signals Concept Guide (NEW)

**Files:**
- Create: `web/src/content/guides/institutional-signals.mdx`

**Step 1: Read 13F-related code for accuracy**

Read:
- `api/src/margin_api/services/thirteenf_ingest.py`
- `api/src/margin_api/services/accumulation_service.py`
- `engine/src/margin_engine/services/accumulation.py`
- Design doc: `docs/plans/2026-02-24-13f-pipeline-design.md`

**Step 2: Create institutional-signals.mdx**

Frontmatter:
```yaml
---
title: "Institutional Signals"
description: "How 13F filings from institutional investors feed into scoring — accumulation signals, curated managers, and what it means."
order: 5
updatedAt: "2026-02-26"
readingTime: 7
category: "Concepts"
---
```

Content sections:
- **What Are 13F Filings?**: SEC requirement for institutional managers with $100M+ AUM. Filed quarterly with a 45-day lag.
- **Accumulation Signals**: Net new positions from curated 13F filers. Calculated as percentile rank across universe.
- **Curated Manager List**: Not all 13F filers are equal. System tracks a curated set of high-conviction managers.
- **How It Feeds Into Scoring**: Accumulation percentile is one input to catalyst strength in the Momentum pillar. Not a standalone signal.
- **Smart Money Page**: Overview of the three tabs (Fund Tracker, Market Signals, Clone Lab) and what each shows.

`<TechnicalDetail>` expandables with: filing mechanics, update cadence (daily at 22:00 UTC), backfill capability, percentile calculation.

`<KnownLimitations>`:
- 45-day reporting lag means positions may have changed
- Not all managers file 13F (e.g., foreign investors)
- Crowded trades analysis requires previous quarter comparison (currently unavailable)
- Clone Lab is educational — not a recommendation engine

**Step 3: Commit**

```bash
git add web/src/content/guides/institutional-signals.mdx
git commit -m "docs(web): add institutional signals concept guide"
```

---

### Task 11: Rewrite Data Sources & Freshness Concept Guide

**Files:**
- Modify: `web/src/content/guides/data-freshness.mdx`

**Step 1: Read current guide and batched ingest code**

Read current `data-freshness.mdx` (104 lines) and `api/src/margin_api/workers.py` for the batched ingest pipeline details.

**Step 2: Rewrite with V4 pipeline accuracy**

Update frontmatter:
```yaml
---
title: "Data Sources & Freshness"
description: "Where Margin Invest's data comes from, how often it updates, and what the known lags and limitations are."
order: 6
updatedAt: "2026-02-26"
readingTime: 6
category: "Concepts"
---
```

Update content to reflect:
- Batched ingest pipeline (not `full_ingest`): `orchestrate_ingest` at 21:30 UTC → concurrent batches of ~50 tickers → sweep → score chain
- Rate limiting: 36 req/min via RedisRateLimiter
- Data provider fallback chains (unchanged but verify accuracy)
- 13F data: daily ingest at 22:00 UTC, 45-day reporting lag
- ML model training: weekly Saturday 2AM UTC

Add `<TechnicalDetail>` for each data source: provider, fallback chain, update cadence, known lag.

Add data freshness timeline visual (reference existing or create description for Task 17).

End with `<KnownLimitations>` (updated for batched pipeline).

**Step 3: Commit**

```bash
git add web/src/content/guides/data-freshness.mdx
git commit -m "docs(web): rewrite data freshness guide for batched ingest pipeline"
```

---

### Task 12: Create Getting Started Workflow Guide (NEW)

**Files:**
- Create: `web/src/content/guides/getting-started.mdx`

**Step 1: Create getting-started.mdx**

Frontmatter:
```yaml
---
title: "Getting Started"
description: "Your first 5 minutes with Margin Invest — what to look at, what it means, and what to do next."
order: 1
updatedAt: "2026-02-26"
readingTime: 4
category: "Workflows"
---
```

Content (task-oriented, step-by-step):
1. **Open the Dashboard**: What you see — ranked stock cards sorted by conviction
2. **Read a Stock Card**: Conviction badge (color + level), opportunity type, sector tag, key score
3. **Understand Conviction Levels**: Quick reference table — EXCEPTIONAL (deep research), HIGH (evaluate), WATCHLIST (monitor), NONE (skip)
4. **Expand a Candidate**: Click to see factor breakdown, position sizing suggestion, filter results
5. **Search a Ticker**: Use the global search to look up any stock you're curious about
6. **What to Do Next**: Links to "Reading the Dashboard" and "Analyzing a Stock" workflow guides

Keep it under 100 lines. Beginners should finish in 4 minutes.

**Step 2: Commit**

```bash
git add web/src/content/guides/getting-started.mdx
git commit -m "docs(web): add getting started workflow guide"
```

---

### Task 13: Rewrite Reading the Dashboard Workflow Guide

**Files:**
- Modify: `web/src/content/guides/using-margin-invest.mdx` — rename and restructure

**Step 1: Read current guide**

Read `using-margin-invest.mdx` (119 lines).

**Step 2: Restructure as dashboard-focused workflow**

Rename file to `reading-the-dashboard.mdx` (delete old, create new). Update frontmatter:

```yaml
---
title: "Reading the Dashboard"
description: "How to interpret stock cards, conviction badges, opportunity types, and the dashboard's ranking logic."
order: 2
updatedAt: "2026-02-26"
readingTime: 5
category: "Workflows"
---
```

Extract dashboard-specific content from the old guide. Focus on:
- Card anatomy (what each element means)
- Conviction badge colors and levels
- Opportunity type badges (Compounder, Mispricing, Both)
- Sector color coding
- Sort order (conviction strength)
- Empty states (when no stocks qualify)
- Common pitfalls (from old guide's pitfalls section, dashboard-specific only)

Move weekly review content to Task 16 (Weekly Review Process guide).

**Step 3: Commit**

```bash
git rm web/src/content/guides/using-margin-invest.mdx
git add web/src/content/guides/reading-the-dashboard.mdx
git commit -m "docs(web): restructure dashboard guide from using-margin-invest"
```

---

### Task 14: Create Analyzing a Stock Workflow Guide (NEW)

**Files:**
- Create: `web/src/content/guides/analyzing-a-stock.mdx`

**Step 1: Read asset detail components for accuracy**

Read `web/src/components/asset-detail/asset-detail-view.tsx` and the design doc `docs/plans/2026-02-23-asset-detail-ui-design.md` to understand the 9 sections of the asset detail page.

**Step 2: Create analyzing-a-stock.mdx**

Frontmatter:
```yaml
---
title: "Analyzing a Stock"
description: "A walkthrough of the asset detail page — what each section shows and how to use it for investment research."
order: 3
updatedAt: "2026-02-26"
readingTime: 8
category: "Workflows"
---
```

Walk through each section of the asset detail page:
1. Hero Header (ticker, price, conviction badge, opportunity type)
2. Elimination Gauntlet (pass/fail results for all 6 filters)
3. Scoring Pillars (Quality, Value, Momentum factor breakdowns)
4. Conviction Engine (dual-track gate results, ML adjustment if active)
5. Valuation Section (DCF, margin of safety, fair value range)
6. Institutional Positioning (13F holder data, accumulation signals)
7. Hypothetical Scenarios (what-if score exploration)
8. How to use this information for research (not as a buy/sell signal)

Include annotated descriptions of what each section shows. Reference concept guides for deeper detail on any factor or metric.

End with a decision checklist: "Before acting on any candidate, verify: [checklist items]"

**Step 3: Commit**

```bash
git add web/src/content/guides/analyzing-a-stock.mdx
git commit -m "docs(web): add analyzing a stock workflow guide"
```

---

### Task 15: Rewrite Building a Portfolio Workflow Guide

**Files:**
- Modify: `web/src/content/guides/position-sizing.mdx` — rename and restructure

**Step 1: Read current guide**

Read `position-sizing.mdx` (91 lines).

**Step 2: Restructure as portfolio workflow**

Rename file to `building-a-portfolio.mdx`. Update frontmatter:

```yaml
---
title: "Building a Portfolio"
description: "Position sizing rules, diversification constraints, and how to construct a portfolio from Margin Invest's scored candidates."
order: 4
updatedAt: "2026-02-26"
readingTime: 6
category: "Workflows"
---
```

Restructure content as a workflow:
1. **Start with qualifying candidates**: Only EXCEPTIONAL and HIGH conviction stocks get allocations
2. **Check the sizing matrix**: Show the conviction × opportunity type table
3. **Apply diversification**: Maximum 10 positions, sector concentration limits
4. **Calculate cash position**: What's left after allocation is a deliberate position
5. **Example portfolio**: Walk through building a 5-stock portfolio from scratch

Keep position sizing rules (these are correct) but reframe from "here are the rules" to "here's how to build a portfolio step by step."

Add `<VerifyItYourself>`: "Check your dashboard. Stocks with WATCHLIST conviction show 0% suggested allocation. The system won't suggest sizing for stocks it doesn't have high conviction in."

**Step 3: Commit**

```bash
git rm web/src/content/guides/position-sizing.mdx
git add web/src/content/guides/building-a-portfolio.mdx
git commit -m "docs(web): restructure position sizing guide as portfolio building workflow"
```

---

### Task 16: Create Weekly Review Process Workflow Guide (NEW)

**Files:**
- Create: `web/src/content/guides/weekly-review.mdx`

**Step 1: Create weekly-review.mdx**

Frontmatter:
```yaml
---
title: "Weekly Review Process"
description: "A structured weekly workflow for reviewing your dashboard, checking score changes, and maintaining your investment research process."
order: 5
updatedAt: "2026-02-26"
readingTime: 5
category: "Workflows"
---
```

Content (extracted and expanded from old using-margin-invest.mdx):
1. **Monday: Check the dashboard** — New candidates, conviction changes, eliminations
2. **Review score changes** — Which stocks moved up/down in conviction? Why? (check factor breakdown)
3. **Check eliminations** — Any stocks you hold that got eliminated? Check the filter that triggered.
4. **Review institutional signals** — Any significant accumulation or distribution from smart money?
5. **Update your watchlist** — Add new EXCEPTIONAL/HIGH candidates, remove downgraded ones
6. **Common pitfalls**: Don't over-trade on small score changes. Don't ignore eliminations. Don't chase conviction upgrades without understanding why.

**Step 2: Commit**

```bash
git add web/src/content/guides/weekly-review.mdx
git commit -m "docs(web): add weekly review process workflow guide"
```

---

### Task 17: Update Methodology Visuals for V4 Pipeline

**Files:**
- Modify: `web/src/components/methodology/visuals/pipeline-diagram.tsx`
- Modify: `web/src/components/methodology/visuals/filter-funnel.tsx`
- Modify: `web/src/components/methodology/visuals/score-breakdown-bars.tsx`
- Modify: `web/src/components/methodology/visuals/candidate-journey-chart.tsx`
- Modify: `web/src/components/methodology/visuals/margin-of-safety-band.tsx`

**Step 1: Read all visual component files**

Read each visual component to understand current implementation.

**Step 2: Update PipelineDiagram**

Update from 4 stages to 7: Universe → Filters → Factor Scoring → Conviction → ML Refinement → Smart Money → Position Sizing. Maintain existing animation patterns and styling.

**Step 3: Update FilterFunnel**

Ensure all 6 filters are shown with their correct names. Add sector-adjustment indicator where applicable.

**Step 4: Update ScoreBreakdownBars**

Verify factor names match V4 pipeline (20 factors across 3 pillars). Add visual indicators for ML-adjusted scores if the section supports it.

**Step 5: Update CandidateJourneyChart**

Extend to show the full 7-stage journey including ML refinement and smart money stages.

**Step 6: Update tests if any visual components have dedicated tests**

Check `web/src/components/methodology/__tests__/` for visual component tests and update.

**Step 7: Run tests**

Run: `cd web && npx vitest run src/components/methodology/`
Expected: PASS

**Step 8: Commit**

```bash
git add web/src/components/methodology/visuals/
git commit -m "feat(web): update methodology visuals for V4 pipeline (7 stages)"
```

---

### Task 18: Integration — Delete Old Guide, Update Metadata, Verify Links

**Files:**
- Delete: `web/src/content/guides/how-scoring-works.mdx` (content moved to methodology page + conviction guide)
- Modify: `web/src/lib/filter-metadata.ts` — verify all citations match guide content
- Modify: `web/src/lib/sub-factor-formulas.ts` — verify all formulas match scoring factors guide
- Modify: `web/src/components/methodology/sections/cta-section.tsx` — update guide links
- Verify: All internal links between guides resolve correctly

**Step 1: Delete how-scoring-works.mdx**

This guide's content has been distributed to:
- Methodology page narrative (Tasks 4-5)
- Conviction & Tracks concept guide (Task 8)
- Scoring Factors concept guide (Task 7)

```bash
git rm web/src/content/guides/how-scoring-works.mdx
```

**Step 2: Verify filter-metadata.ts and sub-factor-formulas.ts**

Cross-reference all entries against the new guides. Ensure citations, formulas, and display names are consistent between in-app metadata and guide content.

**Step 3: Update CTA section links**

Update any links in `cta-section.tsx` that pointed to old guide slugs (e.g., `/guides/how-scoring-works` → `/guides/conviction-and-tracks`, `/guides/metrics-and-terminology` → `/guides/scoring-factors`).

**Step 4: Verify all guide slugs**

Final guide inventory (12 guides + 1 glossary):

| Slug | Category | Status |
|------|----------|--------|
| `elimination-filters` | Concepts | Updated |
| `scoring-factors` | Concepts | New (replaces metrics-and-terminology) |
| `conviction-and-tracks` | Concepts | New |
| `ml-pipeline` | Concepts | New |
| `institutional-signals` | Concepts | New |
| `data-freshness` | Concepts | Updated |
| `getting-started` | Workflows | New |
| `reading-the-dashboard` | Workflows | Renamed (from using-margin-invest) |
| `analyzing-a-stock` | Workflows | New |
| `building-a-portfolio` | Workflows | Renamed (from position-sizing) |
| `weekly-review` | Workflows | New |
| `glossary` | Reference | New |

**Step 5: Run full web test suite**

Run: `cd web && npx vitest run`
Expected: All tests pass (update any tests that reference old guide slugs)

**Step 6: Build verification**

Run: `cd web && npx next build`
Expected: Build succeeds with no broken links or missing modules

**Step 7: Commit**

```bash
git add -A
git commit -m "feat(web): complete methodology and guides rework integration"
```
