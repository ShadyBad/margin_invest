# Buy Below Display Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface the existing `buy_price` (intrinsic value) as a prominent "Buy Below" entry price across the dashboard StockCard, panel ExecutiveHeader, and PanelValuation section.

**Architecture:** Pure frontend changes — no API, DB, or engine modifications. The `buy_price` field already flows from engine through API to frontend types (`ScoreResponse.buy_price`, `PickSummary.buy_price`). Three components need updates: wire real values in ExecutiveHeader and AssetPanel, add a visible "Buy Below" row in StockCard and PanelValuation.

**Tech Stack:** Next.js 15, React, TypeScript, Vitest, Testing Library, Tailwind CSS

---

### Task 1: Add "Buy Below" row to PanelValuation

**Files:**
- Test: `web/src/components/dashboard/panel/__tests__/panel-valuation.test.tsx`
- Modify: `web/src/components/dashboard/panel/panel-valuation.tsx`

**Step 1: Write the failing tests**

Add these tests to `panel-valuation.test.tsx`:

```typescript
it("renders buy below price when provided", () => {
  render(<PanelValuation {...baseProps} buyBelow={22.0} />)
  expect(screen.getByText("Buy Below")).toBeInTheDocument()
  expect(screen.getByText("$22.00")).toBeInTheDocument()
})

it("renders attractive explanation when current price is below buy below", () => {
  render(<PanelValuation {...baseProps} buyBelow={25.0} />)
  expect(
    screen.getByText(/looks attractively priced/)
  ).toBeInTheDocument()
})

it("renders wait explanation when current price is above buy below", () => {
  render(<PanelValuation {...baseProps} buyBelow={18.0} />)
  expect(
    screen.getByText(/Consider waiting/)
  ).toBeInTheDocument()
})

it("does not render buy below row when buyBelow is null", () => {
  render(<PanelValuation {...baseProps} buyBelow={null} />)
  expect(screen.queryByText("Buy Below")).not.toBeInTheDocument()
})

it("does not render buy below row when buyBelow is undefined", () => {
  render(<PanelValuation {...baseProps} />)
  expect(screen.queryByText("Buy Below")).not.toBeInTheDocument()
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/panel-valuation.test.tsx`
Expected: FAIL — `buyBelow` prop does not exist yet

**Step 3: Implement the Buy Below row in PanelValuation**

In `panel-valuation.tsx`, update the interface:

```typescript
interface PanelValuationProps {
  intrinsicValue: number | null
  currentPrice: number | null
  marginOfSafety: number | null
  methods: Record<string, number> | null
  buyBelow?: number | null
}
```

Update the destructured props:

```typescript
export function PanelValuation({
  intrinsicValue,
  currentPrice,
  marginOfSafety,
  methods,
  buyBelow,
}: PanelValuationProps) {
```

Add the Buy Below row after the existing MoS line (after the closing `</div>` of the `mb-4` block, around line 60), before the methods bars:

```tsx
{buyBelow != null && (
  <div className="mb-4 pt-3 border-t border-white/[0.06]">
    <div className="flex items-baseline gap-2">
      <span className="text-[12px] text-[#9A9590]">Buy Below</span>
      <span
        className={`text-[18px] font-mono font-medium ${
          currentPrice != null && currentPrice < buyBelow
            ? "text-[#1A7A5A]"
            : "text-[#9A9590]"
        }`}
      >
        ${buyBelow.toFixed(2)}
      </span>
    </div>
    <p className="text-[11px] text-[#5C5955] mt-1 leading-relaxed">
      {currentPrice != null && currentPrice < buyBelow
        ? "This stock trades below our entry price. Based on its fundamentals, it looks attractively priced right now."
        : "Consider waiting for a pullback before buying. This stock trades above our fundamentals-based entry price."}
    </p>
  </div>
)}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/panel-valuation.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/panel-valuation.tsx web/src/components/dashboard/panel/__tests__/panel-valuation.test.tsx
git commit -m "feat(web): add Buy Below row with explanation to PanelValuation"
```

---

### Task 2: Wire buy_price through AssetPanel to PanelValuation

**Files:**
- Test: `web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx`
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx`

**Step 1: Write the failing test**

The AssetPanel test mocks PanelValuation. Update the mock to capture props and add a test:

```typescript
// Replace the existing PanelValuation mock with:
vi.mock("../panel-valuation", () => ({
  PanelValuation: (props: any) => (
    <div data-testid="panel-valuation" data-buy-below={props.buyBelow ?? "none"} />
  ),
}))
```

Add the test:

```typescript
it("passes buy_price to PanelValuation as buyBelow", () => {
  render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} />)
  const valuation = screen.getByTestId("panel-valuation")
  expect(valuation).toHaveAttribute("data-buy-below", "140")
})
```

**Step 2: Run tests to verify the new test fails**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/asset-panel.test.tsx`
Expected: FAIL — `data-buy-below` will be "none" because AssetPanel doesn't pass `buyBelow` yet

**Step 3: Wire the prop in AssetPanel**

In `asset-panel.tsx`, update the `<PanelValuation>` usage (around line 177-182):

```tsx
<PanelValuation
  intrinsicValue={scoredResult.intrinsic_value}
  currentPrice={scoredResult.actual_price}
  marginOfSafety={scoredResult.margin_of_safety}
  methods={scoredResult.valuation_methods}
  buyBelow={scoredResult.buy_price}
/>
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/asset-panel.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/panel/asset-panel.tsx web/src/components/dashboard/panel/__tests__/asset-panel.test.tsx
git commit -m "feat(web): wire buy_price from AssetPanel to PanelValuation"
```

---

### Task 3: Wire buy_price into ExecutiveHeader ActionPill

**Files:**
- Test: `web/src/components/dashboard/panel/__tests__/executive-header.test.tsx`
- Modify: `web/src/components/dashboard/panel/executive-header.tsx`
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx`

**Step 1: Write the failing tests**

Update the ActionPill mock in `executive-header.test.tsx` to capture props:

```typescript
// Replace the existing ActionPill mock:
ActionPill: (props: any) => (
  <span data-testid="action-pill" data-buy-price={props.buyPrice ?? "none"} data-sell-price={props.sellPrice ?? "none"} data-actual-price={props.actualPrice ?? "none"} />
),
```

Add the test:

```typescript
it("passes price props to ActionPill", () => {
  render(<ExecutiveHeader {...baseProps} buyPrice={140} sellPrice={200} actualPrice={150} />)
  const pill = screen.getByTestId("action-pill")
  expect(pill).toHaveAttribute("data-buy-price", "140")
  expect(pill).toHaveAttribute("data-sell-price", "200")
  expect(pill).toHaveAttribute("data-actual-price", "150")
})
```

**Step 2: Run tests to verify the new test fails**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/executive-header.test.tsx`
Expected: FAIL — ExecutiveHeader doesn't accept price props yet

**Step 3: Add price props to ExecutiveHeader**

In `executive-header.tsx`, update the interface:

```typescript
interface ExecutiveHeaderProps {
  ticker: string
  companyName: string
  compositeScore: number
  scoreDelta: number
  conviction: string
  signal: string
  opportunityType: "compounder" | "mispricing"
  timeRange: TimeRange
  onTimeRangeChange: (range: TimeRange) => void
  onClose: () => void
  buyPrice?: number | null
  sellPrice?: number | null
  actualPrice?: number | null
}
```

Update the destructured props to include `buyPrice`, `sellPrice`, `actualPrice`.

Update the `<ActionPill>` usage:

```tsx
<ActionPill
  signal={signal}
  buyPrice={buyPrice}
  sellPrice={sellPrice}
  actualPrice={actualPrice}
/>
```

**Step 4: Wire the values from AssetPanel**

In `asset-panel.tsx`, update the `<ExecutiveHeader>` usage (around line 120-131):

```tsx
<ExecutiveHeader
  ticker={ticker}
  companyName={scoredResult.name}
  compositeScore={scoredResult.score}
  scoreDelta={0}
  conviction={scoredResult.conviction_level}
  signal={scoredResult.signal}
  opportunityType={(scoredResult.winning_track as "compounder" | "mispricing") ?? "compounder"}
  timeRange={timeRange}
  onTimeRangeChange={setTimeRange}
  onClose={onClose}
  buyPrice={scoredResult.buy_price}
  sellPrice={scoredResult.sell_price}
  actualPrice={scoredResult.actual_price}
/>
```

**Step 5: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/dashboard/panel/__tests__/executive-header.test.tsx && npx vitest run src/components/dashboard/panel/__tests__/asset-panel.test.tsx`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add web/src/components/dashboard/panel/executive-header.tsx web/src/components/dashboard/panel/asset-panel.tsx web/src/components/dashboard/panel/__tests__/executive-header.test.tsx
git commit -m "feat(web): wire price data into ExecutiveHeader ActionPill"
```

---

### Task 4: Add "Buy Below" row to StockCard

**Files:**
- Test: `web/src/components/dashboard/__tests__/stock-card.test.tsx`
- Modify: `web/src/components/dashboard/stock-card.tsx`

**Step 1: Write the failing tests**

Add to `stock-card.test.tsx`:

```typescript
it("renders Buy Below price on card", () => {
  render(<StockCard pick={basePick} />)
  expect(screen.getByText("Buy Below:")).toBeInTheDocument()
  expect(screen.getByText("$140.00")).toBeInTheDocument()
})

it("renders Buy Below in green when actual price is below buy price", () => {
  render(<StockCard pick={{ ...basePick, actual_price: 130, buy_price: 140 }} />)
  const buyBelowValue = screen.getByTestId("buy-below-value")
  expect(buyBelowValue).toHaveClass("text-bullish")
})

it("renders Buy Below explanation text", () => {
  render(<StockCard pick={basePick} />)
  expect(screen.getByText("Fundamentals-based entry price")).toBeInTheDocument()
})

it("does not render Buy Below row when buy_price is null", () => {
  render(<StockCard pick={{ ...basePick, buy_price: null }} />)
  expect(screen.queryByText("Buy Below:")).not.toBeInTheDocument()
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/stock-card.test.tsx`
Expected: FAIL — "Buy Below:" text not found

**Step 3: Add Buy Below row to StockCard**

In `stock-card.tsx`, add a new row after the existing price row (after line 226, before the max_position_pct block):

```tsx
{/* Buy Below row */}
{pick.buy_price != null && (
  <div className="flex items-center justify-between mb-4 text-sm">
    <div className="flex items-baseline gap-1">
      <span className="text-text-secondary">Buy Below:</span>
      <span
        className={`font-medium ${
          pick.actual_price != null && pick.actual_price < pick.buy_price
            ? "text-bullish"
            : "text-text-primary"
        }`}
        data-testid="buy-below-value"
      >
        ${pick.buy_price.toFixed(2)}
      </span>
      <span className="text-text-tertiary text-xs ml-1">Fundamentals-based entry price</span>
    </div>
  </div>
)}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/dashboard/__tests__/stock-card.test.tsx`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx web/src/components/dashboard/__tests__/stock-card.test.tsx
git commit -m "feat(web): add Buy Below row to StockCard dashboard cards"
```

---

### Task 5: Run full test suite and verify

**Files:** None (verification only)

**Step 1: Run all web tests**

Run: `cd web && npx vitest run`
Expected: All tests PASS, no regressions

**Step 2: Verify no TypeScript errors**

Run: `cd web && npx tsc --noEmit`
Expected: Clean output, no errors

**Step 3: Commit (if any fixups needed)**

Only if Steps 1-2 surface issues. Otherwise, done.
