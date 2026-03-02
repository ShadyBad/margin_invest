# Elimination Percentage Precision Fix

## Problem

The homepage and asset-detail pages display "100% of US equities are eliminated before scoring begins." This is a rounding artifact — `Math.round()` turns 99.72 into 100, implying total elimination when a small percentage survives.

## Solution

Replace `Math.round()` with an adaptive precision formatter shared across both display locations.

### Formatting Rules

1. Compute `pct = (eliminated / total) * 100`
2. Format to 2 decimal places by default (e.g. `99.72%`)
3. If rounding to 2 decimals produces `100.00` but true value < 100, expand to 4 decimals (e.g. `99.9874%`)
4. Strip trailing zeros (`99.70%` → `99.7%`)
5. True 100% still displays as `100%`

### Files Changed

- **New:** `web/src/lib/format-elimination-pct.ts` — shared utility
- **New:** `web/src/lib/__tests__/format-elimination-pct.test.ts` — unit tests
- **Update:** `web/src/components/landing/homepage-client.tsx` — use utility
- **Update:** `web/src/components/landing/elimination-vignette.tsx` — accept `string` prop
- **Update:** `web/src/components/asset-detail/elimination-gauntlet.tsx` — use utility
- **Update:** component tests as needed

### Edge Cases

| Input | Output |
|-------|--------|
| 7280 eliminated out of 7300 | `99.73%` |
| 7299 eliminated out of 7300 | `99.99%` |
| 7299.9 eliminated out of 7300 | `99.9986%` (4 decimals because 2 would round to 100) |
| 7300 eliminated out of 7300 | `100%` (true 100) |
| 0 eliminated out of 7300 | `0%` |
| 0 eliminated out of 0 | `0%` (guard against division by zero) |
