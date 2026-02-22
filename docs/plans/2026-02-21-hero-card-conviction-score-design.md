# Hero Card Conviction Score Fix

**Date**: 2026-02-21
**Status**: Approved

## Problem

The "Conviction Score" on landing page hero cards displays `composite_percentile` — a percentile rank across all scored tickers. With small universes, the top picks all get ~100, making the number identical and meaningless across cards.

## Solution

Display `composite_raw_score` (the weighted average of quality + value + momentum factor scores, 0-100) instead. This value varies meaningfully between picks and is what determines conviction level thresholds (>=79 exceptional, >=72 high).

## Changes

1. **`web/src/components/landing/types.ts`** — Add `score` field to `CandidateCard`
2. **`web/src/app/page.tsx`** — Map `pick.score` in `toCandidateCard()`
3. **`web/src/components/landing/hero-candidate-card.tsx`** — Display `candidate.score` instead of `candidate.composite_percentile`
4. **`web/src/components/landing/candidate-data.ts`** — Update fallback data with realistic raw scores
5. **Tests** — Update assertions on conviction score display value

## What stays the same

- "Conviction Score" label unchanged
- Factor bars continue using percentile values
- Dashboard (`/dashboard`) cards unaffected
- API response unchanged — `score` field already exists in `PickSummary`
