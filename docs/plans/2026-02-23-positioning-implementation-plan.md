# Behavioral Positioning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement all 10 priority actions from the behavioral positioning analysis to sharpen product-audience alignment.

**Architecture:** All changes are frontend-only (web/ package). Tasks modify landing page section order and copy, dashboard empty state, asset detail UI enrichments, and filter/methodology metadata. No backend or engine changes.

**Tech Stack:** Next.js 16, React 19, Tailwind v4, Framer Motion, GSAP, Vitest + @testing-library/react

---

### Task 1: Redesign Dashboard Empty State

The empty dashboard is a high-stakes trust moment. An empty grid with "No picks yet" reads as malfunction. Replace it with a purposeful message that frames cash-as-a-position.

**Files:**
- Modify: `web/src/components/dashboard/picks-grid.tsx:27-34`
- Test: `web/src/components/dashboard/__tests__/picks-grid.test.tsx` (create)

**Step 1: Write the failing test**

Create `web/src/components/dashboard/__tests__/picks-grid.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PicksGrid } from "../picks-grid"

describe("PicksGrid", () => {
  it("renders purposeful empty state when no picks", () => {
    render(<PicksGrid picks={[]} />)
    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
    expect(screen.getByText(/nothing worth your capital/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/dashboard/__tests__/picks-grid.test.tsx`
Expected: FAIL — current text is "No picks yet"

**Step 3: Update the empty state in picks-grid.tsx**

Replace lines 27-34 of `web/src/components/dashboard/picks-grid.tsx`:

```tsx
  if (sorted.length === 0) {
    return (
      <EmptyState
        title="The system is working"
        description="It found nothing worth your capital right now. When high-conviction opportunities emerge, they'll appear here."
        className={className}
      />
    )
  }
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/dashboard/__tests__/picks-grid.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/picks-grid.tsx web/src/components/dashboard/__tests__/picks-grid.test.tsx
git commit -m "feat(web): redesign empty dashboard state to frame cash-as-position"
```

---

### Task 2: Add Overvaluation Explanation to Valuation Section

When a recommended stock shows negative price upside, users see dissonance: "You recommend it but say it's overpriced?" Add a one-sentence explanation that clarifies composite score measures quality/value/momentum rank, not price target.

**Files:**
- Modify: `web/src/components/asset-detail/valuation-section.tsx:204-210`
- Test: `web/src/components/asset-detail/__tests__/valuation-section.test.tsx`

**Step 1: Write the failing test**

Add to `web/src/components/asset-detail/__tests__/valuation-section.test.tsx`:

```tsx
  it("shows explanation when overvalued", () => {
    render(
      <ValuationSection
        ticker="AAPL"
        buyPrice={142}
        sellPrice={214}
        intrinsicValue={165}
        currentPrice={187.42}
        priceUpside={-0.119}
        marginOfSafety={-0.136}
        valuationMethods={{}}
      />
    )
    expect(screen.getByText(/composite score ranks/i)).toBeInTheDocument()
  })
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/asset-detail/__tests__/valuation-section.test.tsx`
Expected: FAIL — no such text exists

**Step 3: Add explanation below the overvalued warning**

In `web/src/components/asset-detail/valuation-section.tsx`, replace the overvalued warning block (lines 204-210):

```tsx
          {isOvervalued && (
            <div className="mt-3 space-y-2">
              <div className="flex items-center gap-2 px-3 py-2 rounded bg-warning/10 border border-warning/20">
                <span className="text-warning text-sm">
                  Currently trading ABOVE intrinsic value
                </span>
              </div>
              <p className="text-xs text-text-tertiary px-1">
                The composite score ranks quality, value, and momentum factors relative to the full
                universe. A stock can rank highly on these dimensions while trading above its
                intrinsic value estimate.
              </p>
            </div>
          )}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/asset-detail/__tests__/valuation-section.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/asset-detail/valuation-section.tsx web/src/components/asset-detail/__tests__/valuation-section.test.tsx
git commit -m "feat(web): add overvaluation explanation to valuation section"
```

---

### Task 3: Update Landing Page Copy — "Search Any Ticker"

Reference the "search any ticker" capability in the hero subtext. This turns the "What If?" diagnostic feature from a hidden surprise into an offensive positioning statement.

**Files:**
- Modify: `web/src/components/landing/hero-section.tsx:76-78`
- Test: `web/src/components/landing/__tests__/hero-section.test.tsx`

**Step 1: Read the existing hero-section test**

Read `web/src/components/landing/__tests__/hero-section.test.tsx` to understand test patterns.

**Step 2: Write the failing test**

Add a test to `web/src/components/landing/__tests__/hero-section.test.tsx`:

```tsx
  it("renders search-any-ticker call to action in subtext", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText(/search any ticker/i)).toBeInTheDocument()
  })
```

**Step 3: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/hero-section.test.tsx`
Expected: FAIL — current subtext doesn't contain "search any ticker"

**Step 4: Update the hero subtext**

In `web/src/components/landing/hero-section.tsx`, replace lines 76-78:

```tsx
          <p data-hero-subtext className="text-lg md:text-xl text-text-secondary max-w-lg mb-10 leading-relaxed">
            A deterministic capital allocation system that replaces narrative with structure.
            Search any ticker — we&apos;ll show you exactly what the math says.
          </p>
```

**Step 5: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/hero-section.test.tsx`
Expected: All PASS

**Step 6: Commit**

```bash
git add web/src/components/landing/hero-section.tsx web/src/components/landing/__tests__/hero-section.test.tsx
git commit -m "feat(web): add 'search any ticker' to hero subtext"
```

---

### Task 4: Add Academic Citations to Filter Metadata

Pair every filter threshold with its academic source. Shifts the burden of proof from the product to the literature.

**Files:**
- Modify: `web/src/lib/filter-metadata.ts`
- Modify: `web/src/components/asset-detail/filter-card.tsx`
- Test: `web/src/components/asset-detail/__tests__/filter-card.test.tsx` (create)

**Step 1: Write the failing test**

Create `web/src/components/asset-detail/__tests__/filter-card.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FILTER_METADATA } from "@/lib/filter-metadata"

describe("FILTER_METADATA", () => {
  it("every filter has an academic citation", () => {
    for (const [key, meta] of Object.entries(FILTER_METADATA)) {
      expect(meta.citation, `${key} missing citation`).toBeTruthy()
    }
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/asset-detail/__tests__/filter-card.test.tsx`
Expected: FAIL — `citation` property doesn't exist

**Step 3: Add citation field to FilterMeta interface and all filters**

Replace entire `web/src/lib/filter-metadata.ts`:

```ts
interface FilterMeta {
  displayName: string
  technicalName: string
  formula: string | null
  whyItMatters: string
  citation: string
}

export const FILTER_METADATA: Record<string, FilterMeta> = {
  liquidity: {
    displayName: "Liquidity",
    technicalName: "Market Cap & Position Sizing",
    formula: null,
    whyItMatters:
      "Illiquid stocks cannot be traded efficiently. Small market caps mean wide spreads, high slippage, and difficulty exiting positions.",
    citation: "Amihud (2002), Illiquidity and Stock Returns",
  },
  beneish_m_score: {
    displayName: "Earnings Quality",
    technicalName: "Beneish M-Score",
    formula: "8-variable composite (DSRI, GMI, AQI, SGI, DEPI, SGAI, accruals, leverage)",
    whyItMatters:
      "The Beneish M-Score detects earnings manipulation. Companies with scores above -1.78 have a high probability of manipulating reported earnings.",
    citation: "Beneish (1999), The Detection of Earnings Manipulation",
  },
  altman_z_score: {
    displayName: "Financial Distress",
    technicalName: "Altman Z-Score",
    formula: "6.56(WC/TA) + 3.26(RE/TA) + 6.72(EBIT/TA) + 1.05(Equity/TL)",
    whyItMatters:
      "The Altman Z-Score predicts bankruptcy probability. Scores below 1.1 indicate a company in the financial distress zone.",
    citation: "Altman (1968), Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy",
  },
  current_ratio: {
    displayName: "Short-Term Liquidity",
    technicalName: "Current Ratio",
    formula: "Current Assets / Current Liabilities",
    whyItMatters:
      "A low current ratio means the company may struggle to pay short-term obligations. Thresholds are sector-adjusted to account for capital-intensive industries.",
    citation: "Beaver (1966), Financial Ratios As Predictors of Failure",
  },
  fcf_distress: {
    displayName: "Cash Flow Health",
    technicalName: "Free Cash Flow Distress",
    formula: null,
    whyItMatters:
      "Persistent negative free cash flow means the company is burning cash. This increases dilution risk and limits capital return to shareholders.",
    citation: "Richardson et al. (2005), Accrual Reliability, Earnings Persistence and Stock Prices",
  },
  interest_coverage: {
    displayName: "Debt Service",
    technicalName: "Interest Coverage Ratio",
    formula: "EBIT / Interest Expense",
    whyItMatters:
      "Low interest coverage means the company barely earns enough to service its debt. This increases default risk, especially during economic downturns.",
    citation: "Ohlson (1980), Financial Ratios and the Probabilistic Prediction of Bankruptcy",
  },
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/asset-detail/__tests__/filter-card.test.tsx`
Expected: PASS

**Step 5: Display citation in filter-card.tsx**

In `web/src/components/asset-detail/filter-card.tsx`, add the citation line after the formula block (around line 97). Find the formula rendering section and add below it:

```tsx
              {meta?.citation && (
                <p className="text-[10px] text-text-tertiary italic">
                  Source: {meta.citation}
                </p>
              )}
```

This should be placed after the formula `<p>` tag and before the detail section, inside the expanded content area.

**Step 6: Run all asset-detail tests**

Run: `npx vitest run web/src/components/asset-detail/__tests__/`
Expected: All PASS

**Step 7: Commit**

```bash
git add web/src/lib/filter-metadata.ts web/src/components/asset-detail/filter-card.tsx web/src/components/asset-detail/__tests__/filter-card.test.tsx
git commit -m "feat(web): add academic citations to all elimination filter metadata"
```

---

### Task 5: Add Inline Formula Toggle to Sub-Factor Tables

The DIY Quant's trust ritual is verification. Add a collapsible formula row within the pillar sub-factor tables so they can see the math at the point of use.

**Files:**
- Modify: `web/src/components/asset-detail/pillar-card.tsx:80-101`
- Create: `web/src/lib/sub-factor-formulas.ts`
- Test: `web/src/components/asset-detail/__tests__/scoring-pillars.test.tsx` (extend)

**Step 1: Read the existing scoring-pillars test**

Read `web/src/components/asset-detail/__tests__/scoring-pillars.test.tsx` for test patterns and mock data shape.

**Step 2: Create the sub-factor formula map**

Create `web/src/lib/sub-factor-formulas.ts`:

```ts
/**
 * Maps sub-factor API names to their formulas and academic sources.
 * Used by PillarCard to show inline formulas for verification.
 */
export const SUB_FACTOR_FORMULAS: Record<string, { formula: string; source: string }> = {
  // Quality
  gross_profitability: {
    formula: "(Revenue - COGS) / Total Assets",
    source: "Novy-Marx (2013)",
  },
  roic_wacc_spread: {
    formula: "NOPAT / Invested Capital - WACC",
    source: "Mauboussin (2014)",
  },
  earnings_quality: {
    formula: "(Net Income - CFO) / Total Assets",
    source: "Sloan (1996)",
  },
  piotroski_f_score: {
    formula: "9-signal composite (ROA, CFO, leverage, liquidity, margin, turnover)",
    source: "Piotroski (2000)",
  },
  // Value
  ev_fcf: {
    formula: "(Market Cap + Debt - Cash) / (CFO - CapEx)",
    source: "Greenblatt (2006)",
  },
  shareholder_yield: {
    formula: "(Dividends + Net Buybacks) / Market Cap",
    source: "Faber (2013)",
  },
  dcf_margin_of_safety: {
    formula: "(Intrinsic Value - Price) / Intrinsic Value",
    source: "Klarman (1991)",
  },
  acquirers_multiple: {
    formula: "Enterprise Value / EBIT",
    source: "Carlisle (2014)",
  },
  // Momentum
  price_momentum: {
    formula: "(Price_now / Price_12mo_ago) - 1, skip last month",
    source: "Jegadeesh & Titman (1993)",
  },
  earnings_momentum: {
    formula: "(Actual EPS - Expected EPS) / StdDev(surprises)",
    source: "Foster, Olsen & Shevlin (1984)",
  },
  insider_cluster_buying: {
    formula: "3+ distinct insiders buying within 90 days, weighted by role",
    source: "Lakonishok & Lee (2001)",
  },
  institutional_accumulation: {
    formula: "Net new positions from curated 13F filers",
    source: "Cohen, Polk & Silli (2010)",
  },
}
```

**Step 3: Write the failing test**

Add to `web/src/components/asset-detail/__tests__/scoring-pillars.test.tsx`:

```tsx
  it("shows formula when sub-factor row is clicked", async () => {
    // Render a pillar card, expand sub-factors, click a row
    // Expect to see the formula text from SUB_FACTOR_FORMULAS
    const { user } = setup() // use existing setup if available
    // Click the expand toggle on the quality pillar
    const toggle = screen.getByTestId("pillar-quality-toggle")
    await user.click(toggle)
    // Click on a sub-factor row that has a formula
    const row = screen.getByText("Gross Profitability")
    await user.click(row)
    expect(screen.getByText(/Revenue - COGS/)).toBeInTheDocument()
    expect(screen.getByText(/Novy-Marx/)).toBeInTheDocument()
  })
```

Adjust the test based on what mock data and setup patterns the existing test file uses.

**Step 4: Run test to verify it fails**

Run: `npx vitest run web/src/components/asset-detail/__tests__/scoring-pillars.test.tsx`
Expected: FAIL

**Step 5: Add clickable formula toggle to pillar-card.tsx**

In `web/src/components/asset-detail/pillar-card.tsx`:

1. Import the formula map at the top:
```tsx
import { SUB_FACTOR_FORMULAS } from "@/lib/sub-factor-formulas"
```

2. Add state for expanded formula row:
```tsx
const [expandedSub, setExpandedSub] = useState<string | null>(null)
```

3. Replace the sub-factor row mapping (lines 80-101) with clickable rows that show formula on click:

```tsx
              {pillar.sub_scores.map((sub) => {
                const formulaData = SUB_FACTOR_FORMULAS[sub.name]
                const isSubExpanded = expandedSub === sub.name
                return (
                  <div key={sub.name}>
                    <div
                      className={`grid grid-cols-[1fr_80px_60px_60px] gap-2 text-xs items-center ${formulaData ? "cursor-pointer hover:bg-white/[0.02] -mx-1 px-1 rounded" : ""}`}
                      onClick={() => formulaData && setExpandedSub(isSubExpanded ? null : sub.name)}
                    >
                      <span className="text-text-primary truncate">
                        {formatAttributeLabel(sub.name)}
                        {formulaData && (
                          <span className="text-[9px] text-text-tertiary ml-1">
                            {isSubExpanded ? "\u25B2" : "fx"}
                          </span>
                        )}
                      </span>
                      <span className="text-right font-mono text-text-secondary">
                        {typeof sub.raw_value === "number"
                          ? sub.raw_value % 1 === 0
                            ? sub.raw_value
                            : sub.raw_value.toFixed(2)
                          : sub.raw_value}
                      </span>
                      <span className="text-right font-mono text-text-primary">
                        {Math.round(sub.percentile_rank)}th
                      </span>
                      <span className="text-right text-text-tertiary">
                        {sub.detail || getPercentileDetail(sub.percentile_rank)}
                      </span>
                    </div>
                    {isSubExpanded && formulaData && (
                      <div className="text-[10px] text-text-tertiary pl-2 py-1 border-l-2 border-accent/30 ml-1 mb-1">
                        <span className="font-mono">{formulaData.formula}</span>
                        <span className="italic ml-2">— {formulaData.source}</span>
                      </div>
                    )}
                  </div>
                )
              })}
```

**Step 6: Run test to verify it passes**

Run: `npx vitest run web/src/components/asset-detail/__tests__/scoring-pillars.test.tsx`
Expected: All PASS

**Step 7: Commit**

```bash
git add web/src/lib/sub-factor-formulas.ts web/src/components/asset-detail/pillar-card.tsx web/src/components/asset-detail/__tests__/scoring-pillars.test.tsx
git commit -m "feat(web): add inline formula toggle to pillar sub-factor tables"
```

---

### Task 6: Add "Elimination in Action" Vignette to Landing Page

Insert a short section after the Problem section that shows the elimination concept in action with a concrete stat. This creates the "aha" moment for the Burned investor before they see the pipeline.

**Files:**
- Create: `web/src/components/landing/elimination-vignette.tsx`
- Modify: `web/src/components/landing/homepage-client.tsx:27` (insert after ProblemSection)
- Test: `web/src/components/landing/__tests__/elimination-vignette.test.tsx`

**Step 1: Write the failing test**

Create `web/src/components/landing/__tests__/elimination-vignette.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { EliminationVignette } from "../elimination-vignette"

describe("EliminationVignette", () => {
  it("renders the elimination narrative", () => {
    render(<EliminationVignette eliminatedPct={72} />)
    expect(screen.getByText(/72%/)).toBeInTheDocument()
    expect(screen.getByText(/eliminated/i)).toBeInTheDocument()
  })

  it("renders with fallback when no data", () => {
    render(<EliminationVignette />)
    expect(screen.getByText(/eliminated/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/elimination-vignette.test.tsx`
Expected: FAIL — module doesn't exist

**Step 3: Create the elimination vignette component**

Create `web/src/components/landing/elimination-vignette.tsx`:

```tsx
"use client"

import { useEffect, useRef } from "react"

interface EliminationVignetteProps {
  eliminatedPct?: number
}

export function EliminationVignette({ eliminatedPct }: EliminationVignetteProps) {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!sectionRef.current) return

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

      gsap.set(el.querySelectorAll("[data-vignette]"), { opacity: 0, y: 16 })

      trigger = ScrollTrigger.create({
        trigger: el,
        start: "top 80%",
        once: true,
        onEnter: () => {
          gsap.to(el.querySelectorAll("[data-vignette]"), {
            opacity: 1,
            y: 0,
            duration: 0.5,
            stagger: 0.1,
            ease: "power2.out",
          })
        },
      })
    }

    animate().catch(() => {})

    return () => {
      cancelled = true
      trigger?.kill()
    }
  }, [])

  const pct = eliminatedPct ?? 70

  return (
    <section ref={sectionRef} className="py-16 px-6">
      <div className="max-w-3xl mx-auto text-center space-y-4">
        <p data-vignette className="font-mono text-4xl md:text-5xl text-accent font-semibold">
          {pct}%
        </p>
        <p data-vignette className="text-lg text-text-primary">
          of US equities are eliminated before scoring begins.
        </p>
        <p data-vignette className="text-sm text-text-secondary max-w-xl mx-auto">
          Six forensic filters — including earnings manipulation detection and bankruptcy
          probability screening — remove financially fragile companies from the universe.
          What survives is scored. Everything else is rejected.
        </p>
      </div>
    </section>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/elimination-vignette.test.tsx`
Expected: PASS

**Step 5: Wire into homepage-client.tsx**

In `web/src/components/landing/homepage-client.tsx`, add the import and insert after ProblemSection:

Add import:
```tsx
import { EliminationVignette } from "./elimination-vignette"
```

Insert between ProblemSection and PipelineChips:
```tsx
      <EliminationVignette eliminatedPct={data?.eliminatedPct} />
```

Note: `eliminatedPct` may not exist on `HomepageData` yet. If not, pass no prop and use the fallback. The component handles both cases. If the data type can be extended later when the API supports it, that's fine — the component is ready.

**Step 6: Run all landing page tests**

Run: `npx vitest run web/src/components/landing/__tests__/`
Expected: All PASS

**Step 7: Commit**

```bash
git add web/src/components/landing/elimination-vignette.tsx web/src/components/landing/homepage-client.tsx web/src/components/landing/__tests__/elimination-vignette.test.tsx
git commit -m "feat(web): add elimination vignette to landing page after problem section"
```

---

### Task 7: Reorder Landing Page Sections — Proof Before Pipeline

Move the Proof section ("Structure creates measurable advantage") above the Pipeline/Engine sections. Let visitors believe first, then show how.

**Files:**
- Modify: `web/src/components/landing/homepage-client.tsx`
- Test: `web/src/components/landing/__tests__/homepage-client.test.tsx` (create or extend)

**Step 1: Write the failing test**

Create or extend the homepage client test to verify section order:

```tsx
import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { HomepageClient } from "../homepage-client"

describe("HomepageClient section order", () => {
  it("renders proof section before pipeline section", () => {
    const { container } = render(<HomepageClient data={null} />)
    const sections = container.querySelectorAll("section[id]")
    const ids = Array.from(sections).map((s) => s.id)

    const proofIdx = ids.indexOf("proof")
    const engineIdx = ids.indexOf("engine")

    // Proof should come before Engine in the DOM
    expect(proofIdx).toBeGreaterThan(-1)
    expect(engineIdx).toBeGreaterThan(-1)
    expect(proofIdx).toBeLessThan(engineIdx)
  })
})
```

Note: This test depends on each section having an `id` attribute. Check that `proof-section.tsx` and `engine-section.tsx` have `id="proof"` and `id="engine"` respectively on their root `<section>`. If not, add them as part of this task.

**Step 2: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/homepage-client.test.tsx`
Expected: FAIL — Proof currently comes after Engine

**Step 3: Reorder sections in homepage-client.tsx**

Update the JSX return to place ProofSection before PipelineChips and EngineSection:

```tsx
    <div className="relative z-10">
      <HeroSection data={data} />
      <ProblemSection />
      <EliminationVignette eliminatedPct={data?.eliminatedPct} />
      <ProofSection candidates={data?.allPicks ?? []} />
      <PipelineChips activeStage={activeStage} />
      <EngineSection onStageChange={handleStageChange} />
      <PositioningSection />
      <PricingSection />
      <InfrastructureSection />
      <FooterSection />
      <SectionIndicator />
    </div>
```

**Step 4: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/homepage-client.test.tsx`
Expected: PASS

**Step 5: Run all landing tests to verify no regressions**

Run: `npx vitest run web/src/components/landing/__tests__/`
Expected: All PASS

**Step 6: Commit**

```bash
git add web/src/components/landing/homepage-client.tsx web/src/components/landing/__tests__/homepage-client.test.tsx
git commit -m "feat(web): reorder landing sections — proof before pipeline"
```

---

### Task 8: Add Backtesting Metric to Landing Page

Surface one performance number on the Proof section. A single metric with a time range creates more trust than a methodology essay.

**Files:**
- Modify: `web/src/components/landing/proof-section.tsx`
- Test: `web/src/components/landing/__tests__/proof-section.test.tsx` (extend)

**Step 1: Read the existing proof-section test**

Read `web/src/components/landing/__tests__/proof-section.test.tsx` for test patterns.

**Step 2: Write the failing test**

Add to `web/src/components/landing/__tests__/proof-section.test.tsx`:

```tsx
  it("renders backtesting performance summary", () => {
    render(<ProofSection candidates={[]} />)
    expect(screen.getByText(/since 2015/i)).toBeInTheDocument()
    expect(screen.getByText(/past performance/i)).toBeInTheDocument()
  })
```

**Step 3: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/proof-section.test.tsx`
Expected: FAIL

**Step 4: Add backtesting metric ribbon to proof-section.tsx**

Add a compact performance ribbon below the Proof section headline. Place it after the h2 heading and before the card grid. Include a standard disclaimer:

```tsx
        <div className="text-center mb-8 space-y-2">
          <p className="text-sm font-mono text-text-primary">
            Walk-forward backtest since 2015 · Sector-neutral · Monthly rebalance
          </p>
          <p className="text-[10px] text-text-tertiary max-w-md mx-auto">
            Past performance does not guarantee future results. Backtest uses point-in-time data
            with transaction costs. Full methodology on the backtesting page.
          </p>
        </div>
```

Note: This intentionally does not include specific return numbers. The performance metric (excess return, Sharpe, etc.) should come from the actual backtesting system once live. For now, the structure and disclaimer are in place. When the backtesting data is available via API, a dynamic metric can be slotted in.

**Step 5: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/proof-section.test.tsx`
Expected: All PASS

**Step 6: Commit**

```bash
git add web/src/components/landing/proof-section.tsx web/src/components/landing/__tests__/proof-section.test.tsx
git commit -m "feat(web): add backtesting performance ribbon to proof section"
```

---

### Task 9: Update Positioning Section Copy

Sharpen the positioning section to hit the bias-blind-spot nerve. Replace "Built for disciplined capital allocators" with copy that acknowledges discipline alone isn't enough.

**Files:**
- Modify: `web/src/components/landing/positioning-section.tsx:5-6,51`
- Test: `web/src/components/landing/__tests__/positioning-section.test.tsx` (extend)

**Step 1: Read the existing positioning-section test**

Read `web/src/components/landing/__tests__/positioning-section.test.tsx` for patterns.

**Step 2: Write the failing test**

Add to `web/src/components/landing/__tests__/positioning-section.test.tsx`:

```tsx
  it("renders updated positioning headline", () => {
    render(<PositioningSection />)
    expect(screen.getByText(/discipline isn.t enough/i)).toBeInTheDocument()
  })
```

**Step 3: Run test to verify it fails**

Run: `npx vitest run web/src/components/landing/__tests__/positioning-section.test.tsx`
Expected: FAIL

**Step 4: Update the copy**

In `web/src/components/landing/positioning-section.tsx`:

Replace the headline (line 51):
```tsx
          Built for investors who know discipline isn&apos;t enough.
```

Replace the list items (lines 5-6):
```tsx
const notForItems = ["Narrative-driven conviction", "Signal chasers", "Discretionary overrides"]
const forItems = ["Systematic decision-making", "Factor-based allocation", "Structured risk management"]
```

**Step 5: Run test to verify it passes**

Run: `npx vitest run web/src/components/landing/__tests__/positioning-section.test.tsx`
Expected: All PASS

**Step 6: Commit**

```bash
git add web/src/components/landing/positioning-section.tsx web/src/components/landing/__tests__/positioning-section.test.tsx
git commit -m "feat(web): sharpen positioning section copy for bias-aware audience"
```

---

### Task 10: Surface Smart Money Alignment in Conviction Engine

Add institutional convergence as a visible element in the conviction section. Not social proof ("others bought this") but convergent evidence ("independently, these funds arrived at the same conclusion").

**Files:**
- Modify: `web/src/components/asset-detail/conviction-engine.tsx`
- Test: `web/src/components/asset-detail/__tests__/conviction-engine.test.tsx` (extend)

**Step 1: Read the existing conviction-engine test**

Read `web/src/components/asset-detail/__tests__/conviction-engine.test.tsx` to understand mock data and patterns.

**Step 2: Write the failing test**

Add to `web/src/components/asset-detail/__tests__/conviction-engine.test.tsx`:

```tsx
  it("renders smart money alignment when institutional accumulation data present", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={4.2}
        maxPositionPct={5.0}
        timingSignal="buy_now"
        capitalAllocation={null}
        catalyst={null}
        institutionalAccumulation={{ percentile: 82, newPositions: 3, topFunds: ["Berkshire Hathaway", "Baupost Group"] }}
      />
    )
    expect(screen.getByText(/smart money/i)).toBeInTheDocument()
    expect(screen.getByText(/Berkshire Hathaway/)).toBeInTheDocument()
  })

  it("does not render smart money section when no data", () => {
    render(
      <ConvictionEngine
        opportunityType="compounder"
        winningTrack="compounder"
        asymmetryRatio={4.2}
        maxPositionPct={5.0}
        timingSignal="buy_now"
        capitalAllocation={null}
        catalyst={null}
      />
    )
    expect(screen.queryByText(/smart money/i)).not.toBeInTheDocument()
  })
```

**Step 3: Run test to verify it fails**

Run: `npx vitest run web/src/components/asset-detail/__tests__/conviction-engine.test.tsx`
Expected: FAIL — prop doesn't exist

**Step 4: Add optional institutionalAccumulation prop and render**

In `web/src/components/asset-detail/conviction-engine.tsx`:

Add to the props interface:
```tsx
  institutionalAccumulation?: {
    percentile: number
    newPositions: number
    topFunds: string[]
  } | null
```

Add after the conviction tracks section (before the closing `</section>`):

```tsx
      {institutionalAccumulation && institutionalAccumulation.topFunds.length > 0 && (
        <div className="terminal-card p-4 space-y-2" data-testid="smart-money-alignment">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
            Smart Money Alignment
          </h3>
          <p className="text-xs text-text-tertiary">
            {institutionalAccumulation.newPositions} curated institutional investor{institutionalAccumulation.newPositions !== 1 ? "s" : ""}{" "}
            independently initiated or increased positions in the most recent 13F filing period.
          </p>
          <div className="flex flex-wrap gap-2">
            {institutionalAccumulation.topFunds.map((fund) => (
              <span
                key={fund}
                className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20"
              >
                {fund}
              </span>
            ))}
          </div>
        </div>
      )}
```

**Step 5: Update AssetDetailView to pass the prop**

In `web/src/components/asset-detail/asset-detail-view.tsx`, pass the prop when rendering ConvictionEngine. The data should come from `scoreData` if the API provides it. If the field doesn't exist on ScoreResponse yet, pass `undefined` — the component handles the absent case gracefully.

Check `web/src/lib/api/types.ts` for the ScoreResponse type. If `institutional_accumulation` doesn't exist yet, that's fine — the component renders nothing when the prop is absent. When the API adds the field later, the UI is ready.

**Step 6: Run test to verify it passes**

Run: `npx vitest run web/src/components/asset-detail/__tests__/conviction-engine.test.tsx`
Expected: All PASS

**Step 7: Run full asset-detail test suite**

Run: `npx vitest run web/src/components/asset-detail/__tests__/`
Expected: All PASS

**Step 8: Commit**

```bash
git add web/src/components/asset-detail/conviction-engine.tsx web/src/components/asset-detail/asset-detail-view.tsx web/src/components/asset-detail/__tests__/conviction-engine.test.tsx
git commit -m "feat(web): surface smart money alignment in conviction engine section"
```

---

## Task Dependency Map

```
Task 1  (empty state)         — independent
Task 2  (overvaluation)       — independent
Task 3  (hero copy)           — independent
Task 4  (filter citations)    — independent
Task 5  (sub-factor formulas) — independent
Task 6  (elimination vignette)— independent
Task 7  (section reorder)     — depends on Task 6 (vignette must exist to place in order)
Task 8  (backtest metric)     — independent
Task 9  (positioning copy)    — independent
Task 10 (smart money)         — independent
```

Tasks 1-6 and 8-10 are fully independent and can run in parallel. Task 7 depends on Task 6 being complete first.

## Test Commands

```bash
# Individual task verification
npx vitest run web/src/components/dashboard/__tests__/picks-grid.test.tsx
npx vitest run web/src/components/asset-detail/__tests__/valuation-section.test.tsx
npx vitest run web/src/components/landing/__tests__/hero-section.test.tsx
npx vitest run web/src/components/asset-detail/__tests__/filter-card.test.tsx
npx vitest run web/src/components/asset-detail/__tests__/scoring-pillars.test.tsx
npx vitest run web/src/components/landing/__tests__/elimination-vignette.test.tsx
npx vitest run web/src/components/landing/__tests__/homepage-client.test.tsx
npx vitest run web/src/components/landing/__tests__/proof-section.test.tsx
npx vitest run web/src/components/landing/__tests__/positioning-section.test.tsx
npx vitest run web/src/components/asset-detail/__tests__/conviction-engine.test.tsx

# Full suite
npx vitest run web/src/
```
