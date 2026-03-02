# Scoring Factors Audit & Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix UI color collision, rewrite methodology page to match actual engine architecture, correct factor claims, and add missing disclosures.

**Architecture:** Content-only changes to the Next.js methodology page components + one CSS token addition. No engine changes. All 8 Tier 1 items from the design doc.

**Tech Stack:** Next.js 15, React 19, Tailwind v4, Framer Motion, Vitest + @testing-library/react

---

### Task 1: Add `--color-value` Design Token

**Files:**
- Modify: `web/src/app/globals.css:22-33` (light mode tokens) and `web/src/app/globals.css:112-121` (dark mode tokens)

**Step 1: Add the Value pillar color token to light mode**

In `web/src/app/globals.css`, after line 24 (`--color-accent-subtle`), add:

```css
  --color-value: #1A6B8A;
  --color-value-hover: #155A74;
  --color-value-subtle: rgba(26, 107, 138, 0.08);
```

This is a teal-blue that contrasts clearly with accent green (#0E4F3A) and warning gold (#B8860B).

**Step 2: Add the Value pillar color token to dark mode**

In `web/src/app/globals.css`, after line 114 (`--color-accent-subtle`), add:

```css
  --color-value: #3BA5D0;
  --color-value-hover: #4BB8E0;
  --color-value-subtle: rgba(59, 165, 208, 0.10);
```

**Step 3: Verify the site still builds**

Run: `cd web && npx next build --no-lint 2>&1 | tail -5`
Expected: Build succeeds (new CSS variables are passive until referenced)

**Step 4: Commit**

```bash
git add web/src/app/globals.css
git commit -m "style(web): add --color-value design token for Value pillar differentiation"
```

---

### Task 2: Fix ScoreBreakdownBars Color Collision

**Files:**
- Modify: `web/src/components/methodology/visuals/score-breakdown-bars.tsx:4-9`
- Test: `web/src/components/methodology/__tests__/sections.test.tsx`

**Step 1: Write a test for distinct bar colors**

Add to the ScoringSection describe block in `web/src/components/methodology/__tests__/sections.test.tsx`:

```typescript
it("renders score breakdown bars with distinct pillar colors", () => {
  render(<ScoringSection />)
  // The visual component should render without errors
  expect(screen.getByText("Quality")).toBeInTheDocument()
  expect(screen.getByText("Value")).toBeInTheDocument()
  expect(screen.getByText("Momentum")).toBeInTheDocument()
  expect(screen.getByText("Composite")).toBeInTheDocument()
})
```

**Step 2: Run test to verify it passes (existing component)**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -20`
Expected: PASS

**Step 3: Update bar colors in ScoreBreakdownBars**

In `web/src/components/methodology/visuals/score-breakdown-bars.tsx`, replace lines 3-9:

```typescript
const bars = [
  { label: "Quality", percentile: 78, color: "bg-accent" },
  { label: "Value", percentile: 64, color: "bg-[var(--color-value)]" },
  { label: "Momentum", percentile: 88, color: "bg-warning" },
]

const composite = { label: "Composite", percentile: 79, color: "bg-text-secondary" }
```

Key changes:
- Value: `bg-bullish` → `bg-[var(--color-value)]` (new teal-blue)
- Composite: `bg-accent` → `bg-text-secondary` (neutral, not pillar-specific)

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -20`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/methodology/visuals/score-breakdown-bars.tsx web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "fix(web): differentiate Value pillar bar color from Quality (green→blue)"
```

---

### Task 3: Fix Pillar Card Border Colors in ScoringSection

**Files:**
- Modify: `web/src/components/methodology/sections/scoring-section.tsx:26-41`

**Step 1: Update Value pillar border and title colors**

In `web/src/components/methodology/sections/scoring-section.tsx`, change the Value pillar (lines 26-41):

```typescript
  {
    name: "Value",
    count: 7,
    desc: "Measures what you're paying relative to what the business generates — across multiple valuation lenses to avoid single-metric traps.",
    borderColor: "border-t-[var(--color-value)]",
    titleColor: "text-[var(--color-value)]",
    factors: [
      "DCF Margin of Safety",
      "EV/FCF",
      "Acquirer's Multiple",
      "Owner Earnings Yield",
      "Shareholder Yield",
      "Reverse DCF Growth Gap",
      "Asset Floor",
    ],
  },
```

Key changes:
- `border-t-bullish` → `border-t-[var(--color-value)]`
- `text-bullish` → `text-[var(--color-value)]`

**Step 2: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -20`
Expected: All PASS (tests check content, not CSS classes)

**Step 3: Commit**

```bash
git add web/src/components/methodology/sections/scoring-section.tsx
git commit -m "fix(web): use distinct blue border/title for Value pillar cards"
```

---

### Task 4: Fix OutputsSection Pillar Colors

**Files:**
- Modify: `web/src/components/methodology/sections/outputs-section.tsx:14-18`

**Step 1: Update factorBreakdown colors**

In `web/src/components/methodology/sections/outputs-section.tsx`, replace lines 14-18:

```typescript
const factorBreakdown = [
  { pillar: "Quality", percentile: 82, suffix: "nd", color: "text-accent" },
  { pillar: "Value", percentile: 64, suffix: "th", color: "text-[var(--color-value)]" },
  { pillar: "Momentum", percentile: 71, suffix: "st", color: "text-warning" },
]
```

Also update the factor breakdown bar (line 120) to use pillar-specific colors instead of hardcoded accent:

Replace line 119-122:
```typescript
                  <div className="flex-1 h-2 bg-bg-subtle rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        fb.pillar === "Quality" ? "bg-accent/60" :
                        fb.pillar === "Value" ? "bg-[var(--color-value)]/60" :
                        "bg-warning/60"
                      }`}
                      style={{ width: `${fb.percentile}%` }}
                    />
                  </div>
```

**Step 2: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -20`
Expected: All PASS

**Step 3: Commit**

```bash
git add web/src/components/methodology/sections/outputs-section.tsx
git commit -m "fix(web): apply distinct pillar colors in OutputsSection factor breakdown"
```

---

### Task 5: Update ScoringSection — Change "20 factors" to "17 factors"

**Files:**
- Modify: `web/src/components/methodology/sections/scoring-section.tsx:16-56,91,101-104,160-173`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx:188,204`

**Step 1: Update the test to expect 17 factors**

In `web/src/components/methodology/__tests__/sections.test.tsx`, update:

- Line 188: Change `/20 factors/` to `/17 factors/`
- Line 204: Change `expect(screen.getAllByText("7 factors").length).toBe(2)` to account for new counts

Replace the ScoringSection test block assertions:

```typescript
  it("renders the headline", () => {
    render(<ScoringSection />)
    expect(
      screen.getByText(/17 factors\. Three pillars\. Sector-neutral ranking\./)
    ).toBeInTheDocument()
  })
```

And update factor count test:

```typescript
  it("renders all three pillars with factor counts", () => {
    render(<ScoringSection />)
    expect(screen.getAllByText("Quality").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Value").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("Momentum").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("6 factors")).toBeInTheDocument() // Quality
    expect(screen.getByText("7 factors")).toBeInTheDocument() // Value
    expect(screen.getByText("4 factors")).toBeInTheDocument() // Momentum
  })
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | grep -A2 "FAIL\|fails"`
Expected: FAIL — page still says "20 factors" and old factor counts

**Step 3: Update ScoringSection content**

In `web/src/components/methodology/sections/scoring-section.tsx`:

Update Quality pillar (remove Moat Durability — LOW confidence factor):
```typescript
  {
    name: "Quality",
    count: 6,
    desc: "Measures the durability and efficiency of a business — how well it converts capital into returns, and whether those returns are real.",
    borderColor: "border-t-accent",
    titleColor: "text-accent",
    factors: [
      "ROIC-WACC Spread",
      "ROIC Stability",
      "Incremental ROIC",
      "Gross Profitability",
      "Piotroski F-Score",
      "Accrual Ratio",
    ],
  },
```

Update Momentum pillar (remove Sentiment Score and Runway Score — both LOW confidence):
```typescript
  {
    name: "Momentum",
    count: 4,
    desc: "Measures whether the market, insiders, and institutions are confirming what the fundamentals suggest.",
    borderColor: "border-t-warning",
    titleColor: "text-warning",
    factors: [
      "Price Momentum (12\u20111 month)",
      "Standardized Unexpected Earnings",
      "Insider Cluster Score",
      "Institutional Accumulation",
    ],
  },
```

Update heading (line 91):
```
17 factors. Three pillars. Sector-neutral ranking.
```

Update explanation paragraph (lines 160-173) to accurately describe the scoring process:
```
Factor scores are converted to percentile ranks within each company's
GICS sector, measuring relative strength against sector peers. These
factor scores feed into a multi-gate scoring system where each track
evaluates a different investment thesis — compounding, mispricing, or
efficient growth.
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -20`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/methodology/sections/scoring-section.tsx web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "fix(web): correct factor count to 17, remove LOW-confidence factors from claims"
```

---

### Task 6: Update UsageSection — Change "20 factors" Reference

**Files:**
- Modify: `web/src/components/methodology/sections/usage-section.tsx:21`

**Step 1: Update the guide description**

In `web/src/components/methodology/sections/usage-section.tsx`, change line 21:

```typescript
    desc: "Deep dive into all 17 factors across three pillars",
```

**Step 2: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -10`
Expected: All PASS

**Step 3: Commit**

```bash
git add web/src/components/methodology/sections/usage-section.tsx
git commit -m "fix(web): update guide description to reflect 17 factors"
```

---

### Task 7: Rewrite ConvictionSection — Match Engine Architecture

**Files:**
- Modify: `web/src/components/methodology/sections/conviction-section.tsx` (full rewrite of data + some layout)
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx` (ConvictionSection tests)

**Step 1: Update ConvictionSection tests**

Replace the ConvictionSection describe block:

```typescript
describe("ConvictionSection", () => {
  it("renders the stage label", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/Stage 4 · Multi-Track Scoring/)
    ).toBeInTheDocument()
  })

  it("renders the headline", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/Three independent tracks/)
    ).toBeInTheDocument()
  })

  it("renders AAPL narrative about multiplicative scoring", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/one weak gate kills the score/)
    ).toBeInTheDocument()
  })

  it("renders all three track cards with gates", () => {
    render(<ConvictionSection />)
    expect(screen.getByText(/Track A/)).toBeInTheDocument()
    expect(screen.getByText(/Track B/)).toBeInTheDocument()
    expect(screen.getByText(/Track C/)).toBeInTheDocument()
    expect(screen.getByText("Moat Evidence")).toBeInTheDocument()
    expect(screen.getByText("Reinvestment Engine")).toBeInTheDocument()
    expect(screen.getByText("Capital Allocation")).toBeInTheDocument()
    expect(screen.getByText("Ensemble Valuation")).toBeInTheDocument()
    expect(screen.getByText("Downside Protection")).toBeInTheDocument()
    expect(screen.getByText("Quality Floor")).toBeInTheDocument()
    expect(screen.getByText("Growth Efficiency")).toBeInTheDocument()
    expect(screen.getByText("Unit Economics")).toBeInTheDocument()
  })

  it("renders all four conviction levels with correct names", () => {
    render(<ConvictionSection />)
    expect(screen.getByText("EXCEPTIONAL")).toBeInTheDocument()
    expect(screen.getByText("HIGH")).toBeInTheDocument()
    expect(screen.getByText("MEDIUM")).toBeInTheDocument()
    expect(screen.getByText("NONE")).toBeInTheDocument()
  })

  it("mentions Track C is growth-only", () => {
    render(<ConvictionSection />)
    expect(
      screen.getByText(/growth-style companies only/)
    ).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | grep -A2 "FAIL"`
Expected: Multiple FAILs (old content doesn't match new expectations)

**Step 3: Rewrite ConvictionSection component**

Replace the data definitions at the top of `web/src/components/methodology/sections/conviction-section.tsx`:

```typescript
"use client"

import { motion } from "framer-motion"
import { CandidateJourneyChart } from "../visuals/candidate-journey-chart"

const ease = [0.22, 1, 0.36, 1] as const

const trackA = {
  name: "Track A — Compounder",
  desc: "Identifies businesses with durable competitive advantages and strong reinvestment engines — the kind that compounds value over long holding periods.",
  gates: [
    {
      label: "Moat Evidence",
      detail: "Multiple structural signals of a durable competitive advantage",
    },
    {
      label: "Reinvestment Engine",
      detail:
        "Retained earnings are being deployed at high incremental returns",
    },
    {
      label: "Capital Allocation",
      detail:
        "Management allocates capital with discipline — buybacks, dividends, or reinvestment",
    },
    {
      label: "Valuation/Growth Gap",
      detail:
        "The stock's price doesn't already reflect perfection — room for upside exists",
    },
  ],
}

const trackB = {
  name: "Track B — Mispricing",
  desc: "Identifies stocks trading at a significant discount to intrinsic value with a catalyst to close the gap.",
  gates: [
    {
      label: "Ensemble Valuation",
      detail:
        "Multiple valuation methods agree the stock is cheap — not just one ratio",
    },
    {
      label: "Downside Protection",
      detail: "A floor exists on how much you can lose — asset backing or cash flow stability",
    },
    {
      label: "Catalyst",
      detail:
        "Insider buying, institutional accumulation, or earnings momentum to trigger re-rating",
    },
    {
      label: "Quality Floor",
      detail:
        "Cheap for a reason doesn't qualify — a minimum quality bar must be met",
    },
  ],
}

const trackC = {
  name: "Track C — Efficient Growth",
  desc: "Evaluates high-growth companies on unit economics, capital efficiency, and growth durability. Runs for growth-style companies only.",
  gates: [
    {
      label: "Growth Efficiency",
      detail: "Rule of 40 score or strong revenue growth with high gross margins",
    },
    {
      label: "Unit Economics",
      detail: "Stable or expanding gross margins with operating leverage",
    },
    {
      label: "Capital Efficiency",
      detail: "Incremental returns on invested capital exceed cost of capital",
    },
    {
      label: "Growth Durability",
      detail: "Growth deceleration is manageable and addressable market has headroom",
    },
  ],
}

const convictionLevels = [
  {
    level: "EXCEPTIONAL",
    meaning: "Qualifies strongly on multiple tracks simultaneously — strongest composite tier",
  },
  {
    level: "HIGH",
    meaning:
      "Strong multi-factor case with clear margin of safety on at least one track",
  },
  {
    level: "MEDIUM",
    meaning: "Promising alignment but one gate is weak — monitor for improvement",
  },
  {
    level: "NONE",
    meaning: "Does not meet the threshold on any track",
  },
]
```

Update the stage label (line ~100):
```
Stage 4 · Multi-Track Scoring
```

Update the headline (line ~110):
```
Three independent tracks. Multiplicative scoring.
```

Update the body text:
```
With factor scores in hand, AAPL enters the multi-track scoring
system. Each track evaluates a different investment thesis through four gates.
Scoring is multiplicative — one weak gate kills the score. A company
can't compensate for a missing moat with cheap valuation.
```

Update the track cards grid to render all three tracks:
```tsx
{[trackA, trackB, trackC].map((track, i) => (
```

Change grid from `md:grid-cols-2` to `md:grid-cols-3`:
```tsx
<div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
```

Add a note below the Track C card about growth-style-only eligibility. After the track cards grid closing div, before conviction levels:

```tsx
        <motion.p
          className="text-[12px] text-text-tertiary mb-10"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, ease }}
        >
          Track C runs for growth-style companies only. Investment style is
          classified by majority vote across four signals: valuation multiple,
          revenue growth rate, earnings acceleration, and R&amp;D intensity.
        </motion.p>
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -30`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/methodology/sections/conviction-section.tsx web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "fix(web): rewrite ConvictionSection to match engine 3-track gate cascade"
```

---

### Task 8: Update ScoringSection Body Text — Remove Pillar Weight Claims

**Files:**
- Modify: `web/src/components/methodology/sections/scoring-section.tsx:94-105,160-173`

**Step 1: Update the AAPL intro paragraph**

Replace lines 101-104:

```
AAPL passed all filters. Now it enters multi-factor scoring across
three pillars. Each factor is ranked within AAPL's GICS sector —
a percentile of 85 means AAPL scores better than 85% of its
tech-sector peers on that factor.
```

This removes the old description and focuses on what the engine actually does (sector-relative percentile ranking).

**Step 2: Verify the explanation paragraph was already updated in Task 5**

The paragraph at lines 160-173 should already be updated. If not, replace with:

```
Factor scores are converted to percentile ranks within each company's
GICS sector, measuring relative strength against sector peers. These
factor scores feed into a multi-gate scoring system where each track
evaluates a different investment thesis — compounding, mispricing, or
efficient growth.
```

**Step 3: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -10`
Expected: All PASS

**Step 4: Commit**

```bash
git add web/src/components/methodology/sections/scoring-section.tsx
git commit -m "fix(web): remove pillar-weight claims, describe actual sector-relative ranking"
```

---

### Task 9: Add Survivorship Bias Disclosure to TransparencySection

**Files:**
- Modify: `web/src/components/methodology/sections/transparency-section.tsx:7-20`

**Step 1: Update the "Known limitations" principle**

In `web/src/components/methodology/sections/transparency-section.tsx`, replace the `principles` array (lines 7-20):

```typescript
const principles = [
  {
    title: "Deterministic",
    desc: "Same inputs produce the same outputs. Enter AAPL today and tomorrow with the same data — the scores will be identical. No randomness, no hidden state, no human override.",
  },
  {
    title: "Published formulas",
    desc: "Every formula used in scoring is documented in our guides. You can verify any factor calculation yourself with publicly available financial data.",
  },
  {
    title: "Known limitations",
    desc: "The engine scores currently-listed equities only — delisted stocks are not included, which introduces survivorship bias in historical comparisons. Data can be delayed, restated, or incomplete. Conviction thresholds are theory-derived pending empirical backtesting validation. The engine cannot capture qualitative factors like management quality, regulatory changes, or geopolitical risk.",
  },
]
```

**Step 2: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -10`
Expected: All PASS (test checks for "Known limitations" title, not desc content)

**Step 3: Commit**

```bash
git add web/src/components/methodology/sections/transparency-section.tsx
git commit -m "fix(web): add survivorship bias and threshold calibration disclosures"
```

---

### Task 10: Update PipelineSection Stage Label

**Files:**
- Modify: `web/src/components/methodology/sections/pipeline-section.tsx`
- Modify: `web/src/components/methodology/__tests__/sections.test.tsx`

**Step 1: Update the test**

In the PipelineSection test, change "Dual-Track Scoring" to "Multi-Track Scoring":

```typescript
  it("renders all 7 pipeline stages including ML and Smart Money", () => {
    render(<PipelineSection />)
    expect(screen.getAllByText("Universe").length).toBeGreaterThan(0)
    expect(screen.getByText("Elimination Filters")).toBeInTheDocument()
    expect(screen.getByText("Factor Scoring")).toBeInTheDocument()
    expect(screen.getByText("Multi-Track Scoring")).toBeInTheDocument()
    expect(screen.getByText("ML Refinement")).toBeInTheDocument()
    expect(screen.getByText("Smart Money Overlay")).toBeInTheDocument()
    expect(screen.getByText("Position Sizing")).toBeInTheDocument()
  })
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | grep -A2 "FAIL"`
Expected: FAIL — still says "Dual-Track Scoring"

**Step 3: Update pipeline stage label**

In `web/src/components/methodology/sections/pipeline-section.tsx`, find the stage that says "Dual-Track Scoring" and change it to "Multi-Track Scoring". Also update its description to mention three tracks.

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose 2>&1 | tail -10`
Expected: All PASS

**Step 5: Commit**

```bash
git add web/src/components/methodology/sections/pipeline-section.tsx web/src/components/methodology/__tests__/sections.test.tsx
git commit -m "fix(web): rename 'Dual-Track Scoring' to 'Multi-Track Scoring' in pipeline"
```

---

### Task 11: Fix FilterFunnel Browser Compatibility

**Files:**
- Modify: `web/src/components/methodology/visuals/filter-funnel.tsx:64-65`

**Step 1: Replace color-mix with pre-computed rgba**

In `web/src/components/methodology/visuals/filter-funnel.tsx`, replace lines 63-66:

```typescript
          style={{
            width: "25%",
            backgroundColor: "rgba(14, 79, 58, 0.25)",
          }}
```

This replaces `color-mix(in srgb, var(--color-accent) 25%, transparent)` with the equivalent pre-computed rgba value, ensuring cross-browser compatibility.

**Step 2: Run the build to verify**

Run: `cd web && npx next build --no-lint 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add web/src/components/methodology/visuals/filter-funnel.tsx
git commit -m "fix(web): replace color-mix with rgba fallback for browser compat"
```

---

### Task 12: Run Full Test Suite and Visual Verification

**Step 1: Run all methodology tests**

Run: `cd web && npx vitest run src/components/methodology/__tests__/sections.test.tsx --reporter=verbose`
Expected: All tests PASS

**Step 2: Run the full web test suite**

Run: `cd web && npx vitest run --reporter=verbose 2>&1 | tail -20`
Expected: All tests PASS (no regressions)

**Step 3: Run the build**

Run: `cd web && npx next build --no-lint 2>&1 | tail -10`
Expected: Build succeeds

**Step 4: Commit (if any fixes needed from test failures)**

Fix any failures, then create a final cleanup commit if needed.

---

## Summary of Changes

| Task | Files Modified | What Changes |
|------|---------------|-------------|
| 1 | globals.css | Add `--color-value` token (light + dark) |
| 2 | score-breakdown-bars.tsx, tests | Fix Value bar: green → blue |
| 3 | scoring-section.tsx | Fix Value pillar border/title color |
| 4 | outputs-section.tsx | Fix factor breakdown pillar colors |
| 5 | scoring-section.tsx, tests | 20→17 factors, remove LOW-confidence |
| 6 | usage-section.tsx | Update guide desc "20" → "17" |
| 7 | conviction-section.tsx, tests | Add Track C, fix WATCHLIST→MEDIUM |
| 8 | scoring-section.tsx | Remove pillar-weight/re-ranking claims |
| 9 | transparency-section.tsx | Add survivorship + threshold disclosures |
| 10 | pipeline-section.tsx, tests | Dual-Track → Multi-Track |
| 11 | filter-funnel.tsx | color-mix → rgba fallback |
| 12 | — | Full test suite verification |
