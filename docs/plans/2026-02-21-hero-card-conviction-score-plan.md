# Hero Card Conviction Score Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Display the raw composite score instead of the percentile rank as the "Conviction Score" on landing page hero cards.

**Architecture:** The landing page fetches picks from `/api/v1/dashboard`, converts them to `CandidateCard` objects, and passes them to `HeroCandidateCard`. The API already returns both `score` (raw composite) and `composite_percentile`. We add `score` to the `CandidateCard` type and display it instead of `composite_percentile`.

**Tech Stack:** Next.js 15, TypeScript, Vitest + React Testing Library

---

### Task 1: Add `score` field to CandidateCard type

**Files:**
- Modify: `web/src/components/landing/types.ts`

**Step 1: Add `score` field**

In `web/src/components/landing/types.ts`, add a `score` field to the `CandidateCard` interface, after `composite_percentile`:

```typescript
export interface CandidateCard {
  ticker: string
  name: string
  sector: string
  actual_price: number
  buy_price: number
  margin_of_safety: number
  score: number                  // Raw weighted composite (0-100) — displayed as Conviction Score
  composite_percentile: number   // Percentile rank — kept for factor bar compat
  conviction_level: string
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  sentiment_percentile: number
  growth_percentile: number
  scored_at: string
  filters_passed: number
  filters_total: number
}
```

**Step 2: Verify TypeScript catches missing `score` in dependents**

Run: `cd web && npx tsc --noEmit 2>&1 | head -30`
Expected: Type errors in `candidate-data.ts` and `page.tsx` (missing `score` property). This confirms the type change propagated.

---

### Task 2: Update fallback candidate data

**Files:**
- Modify: `web/src/components/landing/candidate-data.ts`
- Test: `web/src/components/landing/__tests__/candidate-data.test.ts`

**Step 1: Update the test to check for `score` field**

In `web/src/components/landing/__tests__/candidate-data.test.ts`, add assertion for `score` inside the "every candidate has required fields" test:

```typescript
it("every candidate has required fields", () => {
  for (const c of FALLBACK_CANDIDATES) {
    expect(c.ticker).toBeTruthy()
    expect(c.name).toBeTruthy()
    expect(c.sector).toBeTruthy()
    expect(c.actual_price).toBeGreaterThan(0)
    expect(c.buy_price).toBeGreaterThan(0)
    expect(c.score).toBeGreaterThanOrEqual(0)
    expect(c.score).toBeLessThanOrEqual(100)
    expect(c.composite_percentile).toBeGreaterThanOrEqual(0)
    expect(c.composite_percentile).toBeLessThanOrEqual(100)
    expect(c.quality_percentile).toBeGreaterThanOrEqual(0)
    expect(c.value_percentile).toBeGreaterThanOrEqual(0)
    expect(c.momentum_percentile).toBeGreaterThanOrEqual(0)
  }
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/candidate-data.test.ts 2>&1`
Expected: FAIL — `score` property doesn't exist on fallback objects yet.

**Step 3: Add `score` to each fallback candidate**

In `web/src/components/landing/candidate-data.ts`, add a `score` field to each candidate. Use realistic raw composite scores (these should be lower and more varied than the percentile values — raw scores in the 72-82 range map to high/exceptional conviction):

- AAPL: `score: 78.2`
- MSFT: `score: 75.8`
- JNJ: `score: 73.1`
- COST: `score: 76.9`
- V: `score: 74.5`

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/landing/__tests__/candidate-data.test.ts 2>&1`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/types.ts web/src/components/landing/candidate-data.ts web/src/components/landing/__tests__/candidate-data.test.ts
git commit -m "feat(web): add score field to CandidateCard type and fallback data"
```

---

### Task 3: Map `score` in toCandidateCard and display it on the hero card

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/components/landing/hero-candidate-card.tsx`
- Test: `web/src/components/landing/__tests__/hero-candidate-card.test.tsx`

**Step 1: Update the hero card test**

In `web/src/components/landing/__tests__/hero-candidate-card.test.tsx`, the test on line 41-44 asserts the conviction score displays `83` (AAPL's old `composite_percentile`). Update it to match the new `score` value:

```typescript
it("renders conviction score as largest visual element", () => {
  render(<HeroCandidateCard candidates={FALLBACK_CANDIDATES} />)
  expect(screen.getByText("78")).toBeInTheDocument()
})
```

(78 = `Math.round(78.2)`, the new AAPL `score` value)

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/landing/__tests__/hero-candidate-card.test.tsx 2>&1`
Expected: FAIL — still rendering `83` (the old `composite_percentile`).

**Step 3: Update `toCandidateCard` in `page.tsx`**

In `web/src/app/page.tsx`, add `score` mapping inside `toCandidateCard()`:

```typescript
function toCandidateCard(pick: DashboardResponse["picks"][0]): CandidateCard {
  return {
    ticker: pick.ticker,
    name: pick.name,
    sector: pick.sector ?? "Unknown",
    actual_price: pick.actual_price ?? 0,
    buy_price: pick.buy_price ?? 0,
    margin_of_safety: pick.margin_of_safety ?? 0,
    score: pick.score,
    composite_percentile: pick.composite_percentile,
    conviction_level: pick.conviction_level,
    quality_percentile: pick.quality_percentile,
    value_percentile: pick.value_percentile,
    momentum_percentile: pick.momentum_percentile,
    sentiment_percentile: pick.sentiment_percentile ?? 0,
    growth_percentile: pick.growth_percentile ?? 0,
    scored_at: pick.scored_at ?? new Date().toISOString(),
    filters_passed: 8,
    filters_total: 8,
  }
}
```

**Step 4: Update the hero card to display `score`**

In `web/src/components/landing/hero-candidate-card.tsx`, change line 212 from:

```tsx
{Math.round(candidate.composite_percentile)}
```

to:

```tsx
{Math.round(candidate.score)}
```

**Step 5: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/landing/__tests__/hero-candidate-card.test.tsx 2>&1`
Expected: PASS

**Step 6: Run full landing page test suite**

Run: `cd web && npx vitest run src/components/landing/__tests__/ 2>&1`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add web/src/app/page.tsx web/src/components/landing/hero-candidate-card.tsx web/src/components/landing/__tests__/hero-candidate-card.test.tsx
git commit -m "fix(web): display raw composite score as conviction score on hero cards

composite_percentile showed ~100 for all top picks due to percentile
ranking in small universes. composite_raw_score varies meaningfully
between candidates (72-82 range for high/exceptional conviction)."
```

---

### Task 4: Verify no other references to composite_percentile as conviction score

**Files:** None (verification only)

**Step 1: Run full web test suite**

Run: `cd web && npx vitest run 2>&1`
Expected: All tests PASS

**Step 2: TypeScript check**

Run: `cd web && npx tsc --noEmit 2>&1`
Expected: No errors
