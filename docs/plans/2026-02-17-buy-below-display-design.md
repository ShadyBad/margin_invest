# Buy Below Display — Design Document

**Date**: 2026-02-17
**Status**: Approved
**Goal**: Surface the existing `buy_price` (intrinsic value) as a prominent "Buy Below" entry price across dashboard cards, panel header, and valuation section with actionable, retail-friendly explanation copy.

## Problem Statement

The engine already computes `buy_price` (= intrinsic value, the weighted average of 4 valuation methods: DCF, EV/FCF, Acquirer's Multiple, Shareholder Yield). The API already returns it in `ScoreResponse` and `PickSummary`. But the frontend doesn't display it prominently:

- `ExecutiveHeader` passes `null` to ActionPill's `buyPrice` prop
- `PanelValuation` doesn't receive `buy_price` at all
- `StockCard` passes it to ActionPill but has no visible text row for it

## Design

### Label & Tone

- **Label**: "Buy Below" — actionable, unambiguous, not confused with Wall Street analyst "target prices"
- **Tone**: Actionable and direct — tells investors what to do with the number
- **Value**: `buy_price` from the existing scoring pipeline (= intrinsic_value)

### 1. Data Flow Fixes

No new API fields, DB columns, or endpoints. Three wiring fixes:

1. **ExecutiveHeader**: Pass `scoredResult.buy_price` instead of `null` to ActionPill's `buyPrice` prop
2. **AssetPanel → PanelValuation**: Thread `buy_price` and `actual_price` through as new props
3. **StockCard**: Already passes `buy_price` to ActionPill — no change needed for ActionPill

### 2. Dashboard StockCard

- Add a "Buy Below $X.XX" line in the price metrics area
- Green text when `actual_price < buy_price` (stock is below entry threshold), muted when above
- Below the price: "Fundamentals-based entry price" in small muted text
- If `buy_price` is null, show nothing — no placeholder, no "N/A"

### 3. ExecutiveHeader (Panel Top)

- Pass real `buy_price` to ActionPill (1-line prop fix)
- ActionPill already formats "Buy below $X.XX" as subtext — no UI changes needed

### 4. PanelValuation Section

- Add "Buy Below" row after current price row, same label-left / value-right layout
- Value styled larger and green when `actual_price < buy_price`, muted when above
- Contextual explanation copy below the value:
  - When `actual_price < buy_price`: "This stock trades below our entry price. Based on its fundamentals, it looks attractively priced right now."
  - When `actual_price > buy_price`: "Consider waiting for a pullback before buying. This stock trades above our fundamentals-based entry price."
- If `buy_price` is null, entire Buy Below row is hidden

### 5. Explicit Non-Goals

- No new API endpoints or DB columns
- No new reusable component (Buy Below lives inline in existing components)
- No redesign of PanelValuation layout
- No price history chart overlays or animated states
- No sorting/filtering by Buy Below on the dashboard
- No tooltip explaining the 4 valuation methods

## Files Changed

| File | Change |
|------|--------|
| `web/src/components/dashboard/panel/executive-header.tsx` | Pass real `buy_price` to ActionPill |
| `web/src/components/dashboard/panel/panel-valuation.tsx` | Add `buyBelow` and `actualPrice` props, render Buy Below row with explanation |
| `web/src/components/dashboard/panel/asset-panel.tsx` | Thread `buy_price` and `actual_price` to PanelValuation |
| `web/src/components/dashboard/stock-card.tsx` | Add visible "Buy Below" text row in price section |
