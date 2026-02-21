# Growth vs Value Tilt Chart — Design

**Date**: 2026-02-20
**Status**: Approved
**Scope**: Frontend only — no API changes

## Problem

The "Growth vs Value Tilt" chart in the Proof section on the main page displays hardcoded data (Growth: 35%, Value: 25%) representing default scoring weights. It does not reflect actual candidate data.

## Solution

Replace the hardcoded chart with a vertical bar chart that classifies all dashboard picks into three tilt categories (Value, Blend, Growth) based on their percentile scores, and displays the count of candidates in each category.

## Data

### Source
- All picks from `GET /api/v1/dashboard` (the full `picks[]` array)
- Fields used: `growth_percentile`, `value_percentile` (both already exist on `PickSummary`)

### Classification Rule
For each candidate, compute `diff = growth_percentile - value_percentile`:
- `diff > 10` → **Growth**
- `diff < -10` → **Value**
- `-10 ≤ diff ≤ 10` → **Blend**

### Output
Three category counts, e.g. `{ Value: 4, Blend: 2, Growth: 6 }`

### Data Flow
`page.tsx` already fetches all picks. Currently only the top 5 are passed into `HomepageData.candidates`. Change: pass all picks to `HomepageClient`, then thread them through `ProofSection` → `ProofTiltChart`.

## Visual Design

### Chart Layout
- Switch from horizontal bars to **vertical bars** (3 discrete categories side by side)
- Chart height: 120px (unchanged)
- recharts `BarChart` with `ResponsiveContainer`

### Bars
- X-axis: category labels — "Value", "Blend", "Growth" (left to right) in `text-text-tertiary` at 10-11px
- Y-axis: hidden
- Bar color: all use `var(--color-accent)` with varying opacity — Value 40%, Blend 60%, Growth 100%
- Bar radius: `[4, 4, 0, 0]` (rounded top corners)
- Zero-count bars: 2px baseline stub so the "0" label has an anchor

### Count Labels
- Small number directly above each bar (11px, `text-text-tertiary`)
- Displayed for every category including zero

### Legend
Single line below the chart, replacing the current subtitle:

> Candidates by dominant factor · Value ← Blend → Growth

Styled at 10px, `text-text-tertiary`, centered.

## States

| State | Behavior |
|-------|----------|
| **Normal** | Bars + count labels + legend render from SSR data |
| **Empty** (0 picks) | No bars; centered "No candidates scored yet" in muted text; legend still renders |
| **Error** | Handled upstream — `page.tsx` returns `null` on fetch failure, maps to empty state |
| **Loading** | N/A — server-side rendered, data arrives with HTML |

No tooltips — count labels already communicate the key information.

Update frequency: refreshes on every page load (SSR).

## Acceptance Criteria

### AC-1: Correct counts
- **Given** 12 picks where 4 have `value_pct - growth_pct > 10`, 2 are within 10, and 6 have `growth_pct - value_pct > 10`
- **When** the main page renders
- **Then** the chart shows bars with labels "4", "2", "6" above Value, Blend, Growth

### AC-2: Legend present
- **Given** the chart renders with any candidate data
- **When** the user views the Proof section
- **Then** a legend reading "Candidates by dominant factor · Value ← Blend → Growth" appears below the chart

### AC-3: Count labels shown
- **Given** any non-negative count per category
- **When** the chart renders
- **Then** a numeric label appears directly above each bar (including "0" for empty categories)

### AC-4: Empty state
- **Given** 0 picks returned from the dashboard
- **When** the main page renders
- **Then** the chart area shows "No candidates scored yet" with no bars

### AC-5: Zero-count bar
- **Given** all candidates fall into Growth and none into Value
- **When** the chart renders
- **Then** Value shows a 2px stub with "0" above it

## Engineering Notes

### Files to Modify
1. `web/src/app/page.tsx` — pass all picks (not just sliced 5) into `HomepageData`
2. `web/src/components/landing/homepage-client.tsx` — pass candidates to `ProofSection`
3. `web/src/components/landing/proof-section.tsx` — accept candidates prop, forward to `ProofTiltChart`
4. `web/src/components/landing/proof-tilt-chart.tsx` — rewrite: vertical bars, real data, count labels, legend

### Classification Function
Extract `classifyTilt(candidates) → { Value: number, Blend: number, Growth: number }` as a pure function for testability.

### Testing
- **Unit test** `classifyTilt()`: all-growth, all-value, all-blend, empty array, boundary (diff = 10 → Blend, diff = 11 → Growth)
- **Snapshot test** `ProofTiltChart` with known input to verify labels render

### Caching
None needed — SSR on page load; dashboard endpoint handles its own caching.
