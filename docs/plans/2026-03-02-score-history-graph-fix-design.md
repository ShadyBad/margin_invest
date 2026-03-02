# Score History Graph Fix — Display Raw Score Instead of Percentile

**Date:** 2026-03-02
**Status:** Approved

## Problem

The score history graph in the candidate scoring modal displays incorrect values. The header badge shows the raw composite score (e.g., 73 for AMR), but the graph plots `composite_percentile` (the percentile rank within the universe, e.g., 100). Users see a mismatch: the badge says 73 but the graph tooltip says 100.

## Root Cause

Two different score fields are used:

| Component | Field | Value (AMR example) |
|---|---|---|
| Header badge (`ExecutiveHeader`) | `scoredResult.score` → `Score.composite_raw_score` | 73 |
| Graph (`ScoreChart`) | `p.composite_percentile` → `Score.composite_percentile` | 100 |

The history API returns both `composite_raw_score` and `composite_percentile` in each `ScoreHistoryPoint`, but the frontend maps the graph to the wrong field.

## Solution

### 1. API: Add `score` field to `ScoreHistoryPoint`

Add a `score: float` field to the `ScoreHistoryPoint` Pydantic schema, populated from `Score.composite_raw_score`. This aligns with the `ScoreResponse.score` naming convention so consumers use consistent field names.

**Files:**
- `api/src/margin_api/schemas/score_history.py` — add `score: float` field
- `api/src/margin_api/routes/scores.py` — populate `score=row.composite_raw_score`

Existing `composite_raw_score` and `composite_percentile` fields remain for backward compatibility.

### 2. Frontend Types: Add `score` to `ScoreHistoryPoint`

**File:** `web/src/lib/api/types.ts`

Add `score: number` to the `ScoreHistoryPoint` interface.

### 3. Frontend: Map graph data to `score`

**File:** `web/src/components/dashboard/panel/asset-panel.tsx`

Change both `scoreHistory` and `scoreChartData` `useMemo` blocks:
- `score: p.composite_percentile` → `score: p.score ?? p.composite_raw_score ?? 0`

Fallback chain: new API field → old field → zero.

### 4. Tests

- `api/tests/test_score_history.py` — assert `score` field matches `composite_raw_score`
- Vitest tests for chart components if they reference `composite_percentile`

## Acceptance Criteria

- Tooltip value matches stored raw score for that date
- Current graph endpoint equals the displayed current score (73 in AMR example)
- Historical graph points match backend `composite_raw_score` records
- No artificial scaling relative to universe distribution
- Y-axis remains 0–100 (raw scores are already on this scale)
