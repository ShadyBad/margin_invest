# Selectivity Funnel Label Visibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make all labels readable in the selectivity funnel by rendering them outside narrow bars, and add hover tooltips with stage-over-stage context.

**Architecture:** Conditional label placement (inside vs. outside the bar) based on a 25% width threshold. Tooltip state managed by `hoveredIndex`. Pure Tailwind + Framer Motion — no chart library.

**Tech Stack:** React 19, Tailwind v4, Framer Motion, Vitest + Testing Library

---

### Task 1: External Label Positioning

**Files:**
- Modify: `web/src/components/landing/proof-selectivity-funnel.tsx:103-134`
- Test: `web/src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`

**Step 1: Write the failing tests**

Add these tests to the existing `describe` block in `proof-selectivity-funnel.test.tsx`:

```typescript
it("renders labels outside narrow bars", async () => {
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => MOCK_FUNNEL,
  })
  render(<ProofSelectivityFunnel />)
  // Exceptional bar = 12/3200 = 0.375% → clamped to 4% → labels external
  const label = await screen.findByText(/12 Exceptional/)
  // External label should NOT have truncate class
  expect(label.className).not.toContain("truncate")
  // External label should be a sibling of the bar, not a child
  const bar = label.closest("[data-testid='funnel-row-exceptional_count']")
  expect(bar).toBeInTheDocument()
  const coloredBar = bar!.querySelector("[data-testid='funnel-bar']")
  expect(coloredBar).toBeInTheDocument()
  expect(coloredBar!.contains(label)).toBe(false)
})

it("renders labels inside wide bars", async () => {
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => MOCK_FUNNEL,
  })
  render(<ProofSelectivityFunnel />)
  // Universe bar = 100% → labels internal
  const label = await screen.findByText(/3,200 equities screened/)
  const bar = label.closest("[data-testid='funnel-row-universe_size']")
  const coloredBar = bar!.querySelector("[data-testid='funnel-bar']")
  expect(coloredBar!.contains(label)).toBe(true)
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`
Expected: FAIL — `data-testid` attributes not found

**Step 3: Implement conditional label positioning**

Replace the bar rendering block (lines 103-134) in `proof-selectivity-funnel.tsx` with:

```tsx
const LABEL_THRESHOLD = 25

return (
  <div aria-label="Selectivity funnel showing how many equities survive each scoring stage">
    <div className="space-y-2">
      {BARS.map((bar, i) => {
        const raw =
          bar.key === "high_count"
            ? data.high_count + data.exceptional_count
            : (data[bar.key] as number)
        const widthPct = Math.max(4, (raw / maxVal) * 100)
        const isExternal = widthPct < LABEL_THRESHOLD

        return (
          <motion.div
            key={bar.key}
            data-testid={`funnel-row-${bar.key}`}
            className="relative flex items-center gap-3"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
          >
            <div
              data-testid="funnel-bar"
              className={`${bar.color} rounded h-8 shrink-0 ${
                !isExternal ? "flex items-center justify-between px-3" : ""
              }`}
              style={{ width: `${widthPct}%` }}
            >
              {!isExternal && (
                <>
                  <span className="text-xs text-text-primary font-mono truncate">
                    {bar.label(data)}
                  </span>
                  <span className="text-[10px] text-text-secondary font-mono ml-2 shrink-0">
                    {bar.right(data)}
                  </span>
                </>
              )}
            </div>
            {isExternal && (
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xs text-text-primary font-mono whitespace-nowrap">
                  {bar.label(data)}
                </span>
                <span className="text-[10px] text-text-secondary font-mono shrink-0">
                  {bar.right(data)}
                </span>
              </div>
            )}
          </motion.div>
        )
      })}
    </div>
    <p className="text-[10px] text-text-tertiary mt-3 text-center">
      Most equities are eliminated before scoring begins.
    </p>
    <p className="text-[9px] text-text-tertiary mt-1 text-center italic">
      Elimination removes stocks with insufficient data or failing fundamentals — not a
      quality judgment on the business.
    </p>
  </div>
)
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/proof-selectivity-funnel.tsx web/src/components/landing/__tests__/proof-selectivity-funnel.test.tsx
git commit -m "feat(web): render funnel labels outside narrow bars"
```

---

### Task 2: Hover Tooltip

**Files:**
- Modify: `web/src/components/landing/proof-selectivity-funnel.tsx`
- Test: `web/src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`

**Step 1: Write the failing test**

Add to the test file:

```typescript
import { fireEvent } from "@testing-library/react"

it("shows tooltip on hover with stage details", async () => {
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => MOCK_FUNNEL,
  })
  render(<ProofSelectivityFunnel />)
  // Wait for data
  await screen.findByText(/3,200 equities screened/)
  // Hover over the exceptional bar row
  const row = screen.getByTestId("funnel-row-exceptional_count")
  fireEvent.mouseEnter(row)
  // Tooltip should show stage name, count, % of universe, % of previous stage
  expect(screen.getByTestId("funnel-tooltip")).toBeInTheDocument()
  expect(screen.getByTestId("funnel-tooltip")).toHaveTextContent("Exceptional candidates")
  expect(screen.getByTestId("funnel-tooltip")).toHaveTextContent("12")
  expect(screen.getByTestId("funnel-tooltip")).toHaveTextContent("0.4%")
  // 12 of (35+12) = 25.5% of previous stage
  expect(screen.getByTestId("funnel-tooltip")).toHaveTextContent("25.5%")
})

it("hides tooltip on mouse leave", async () => {
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => MOCK_FUNNEL,
  })
  render(<ProofSelectivityFunnel />)
  await screen.findByText(/3,200 equities screened/)
  const row = screen.getByTestId("funnel-row-exceptional_count")
  fireEvent.mouseEnter(row)
  expect(screen.getByTestId("funnel-tooltip")).toBeInTheDocument()
  fireEvent.mouseLeave(row)
  expect(screen.queryByTestId("funnel-tooltip")).not.toBeInTheDocument()
})
```

Note: The existing import line `import { render, screen } from "@testing-library/react"` needs `fireEvent` added to it.

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`
Expected: FAIL — `funnel-tooltip` not found

**Step 3: Implement tooltip**

Add state and tooltip data to the component. Below `const [error, setError] = useState(false)`, add:

```typescript
const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
```

Add a helper above the component or inside it to compute tooltip data:

```typescript
function getTooltipData(
  data: FunnelData,
  barIndex: number
): { stage: string; count: number; pctUniverse: string; pctPrevious: string | null } {
  const stages = [
    {
      stage: "Equities screened",
      count: data.universe_size,
      raw: data.universe_size,
      prevRaw: null as number | null,
    },
    {
      stage: "Survived elimination",
      count: data.survived_filters,
      raw: data.survived_filters,
      prevRaw: data.universe_size,
    },
    {
      stage: "High or Exceptional",
      count: data.high_count + data.exceptional_count,
      raw: data.high_count + data.exceptional_count,
      prevRaw: data.survived_filters,
    },
    {
      stage: "Exceptional candidates",
      count: data.exceptional_count,
      raw: data.exceptional_count,
      prevRaw: data.high_count + data.exceptional_count,
    },
  ]
  const s = stages[barIndex]
  return {
    stage: s.stage,
    count: s.count,
    pctUniverse: pct(s.raw, data.universe_size),
    pctPrevious:
      s.prevRaw !== null ? `${pct(s.raw, s.prevRaw)} of previous` : null,
  }
}
```

On each `motion.div` row, add hover handlers:

```tsx
onMouseEnter={() => setHoveredIndex(i)}
onMouseLeave={() => setHoveredIndex(null)}
```

Inside the `motion.div`, after the bar and external labels, add:

```tsx
{hoveredIndex === i && (
  <div
    data-testid="funnel-tooltip"
    className="absolute left-0 bottom-full mb-2 z-10 terminal-card px-3 py-2 text-xs font-mono shadow-lg min-w-[200px]"
  >
    {(() => {
      const tip = getTooltipData(data, i)
      return (
        <>
          <p className="text-text-primary font-medium">{tip.stage}</p>
          <p className="text-text-secondary">
            {formatCount(tip.count)} &middot; {tip.pctUniverse} of universe
          </p>
          {tip.pctPrevious && (
            <p className="text-text-tertiary">{tip.pctPrevious}</p>
          )}
        </>
      )
    })()}
  </div>
)}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/landing/proof-selectivity-funnel.tsx web/src/components/landing/__tests__/proof-selectivity-funnel.test.tsx
git commit -m "feat(web): add hover tooltip to selectivity funnel bars"
```

---

### Task 3: External Label Fade-In Animation

**Files:**
- Modify: `web/src/components/landing/proof-selectivity-funnel.tsx`

**Step 1: Wrap external labels in a `motion.div` with fade-in**

Replace the external label `<div>` with:

```tsx
{isExternal && (
  <motion.div
    className="flex items-center gap-2 min-w-0"
    initial={{ opacity: 0 }}
    whileInView={{ opacity: 1 }}
    viewport={{ once: true }}
    transition={{ duration: 0.3, delay: i * 0.1 + 0.5 }}
  >
    <span className="text-xs text-text-primary font-mono whitespace-nowrap">
      {bar.label(data)}
    </span>
    <span className="text-[10px] text-text-secondary font-mono shrink-0">
      {bar.right(data)}
    </span>
  </motion.div>
)}
```

The `delay: i * 0.1 + 0.5` ensures labels appear after the bar's 0.5s entrance animation.

**Step 2: Run all tests to verify nothing broke**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`
Expected: All tests PASS (Framer Motion is mocked — animations don't affect test DOM)

**Step 3: Commit**

```bash
git add web/src/components/landing/proof-selectivity-funnel.tsx
git commit -m "feat(web): add fade-in animation for external funnel labels"
```

---

### Task 4: Run Full Test Suite

**Step 1: Run component tests**

Run: `cd web && npx vitest run src/components/landing/__tests__/proof-selectivity-funnel.test.tsx`
Expected: All tests PASS

**Step 2: Run full web test suite to check for regressions**

Run: `cd web && npx vitest run`
Expected: All tests PASS

**Step 3: Final commit if any cleanup needed**

Only if there are lint or formatting fixes needed.
