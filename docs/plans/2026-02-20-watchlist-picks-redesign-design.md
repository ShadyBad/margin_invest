# Watchlist Picks Redesign

**Date:** 2026-02-20
**Status:** Approved

## User Story

As a dashboard user, I want Watchlist Picks to display a clear conviction label (Exceptional/High/Medium) based on absolute score thresholds and be expandable inline so I can review details without leaving the watchlist section.

## Overview

Two changes:
1. Replace percentile-based conviction thresholds with absolute `composite_raw_score` thresholds globally.
2. Make Watchlist Picks expandable within the watchlist section (compact list rows, not large standalone cards).

## Approach

Approach A with fetch-on-expand: keep `WatchlistItem` lean on the dashboard response, fetch full score details via `GET /api/v1/scores/{ticker}` when a user expands a row. Reuses existing `AssetPanel` overlay component.

---

## Section 1: Engine — Global Conviction Threshold Change

### ConvictionLevel Enum

Rename `WATCHLIST` to `MEDIUM`:

```
EXCEPTIONAL = "exceptional"   # composite_raw_score >= 79
HIGH = "high"                 # composite_raw_score >= 72
MEDIUM = "medium"             # composite_raw_score >= 65
NONE = "none"                 # < 65
```

### CompositeScore.conviction_level Property

Switch from percentile-based to raw-score-based:

- `composite_raw_score >= 79` -> EXCEPTIONAL
- `composite_raw_score >= 72` -> HIGH
- `composite_raw_score >= 65` -> MEDIUM
- `< 65` -> NONE (excluded from all pick lists)

No turnaround exception. Thresholds are absolute across all growth stages.

### ScoringConfig

Update threshold fields:
- `exceptional_threshold: 79.0`
- `high_threshold: 72.0`
- `medium_threshold: 65.0` (renamed from `watchlist_threshold`)

### Signal Mapping

Unchanged logic. MEDIUM maps to `WATCH` (same as WATCHLIST did).

### Impact

Every scored asset gets reclassified on next scoring run. Historical `conviction_level` strings in DB keep old values; only new scores use new thresholds.

---

## Section 2: API — Enriched Watchlist Response + Sorting

### WatchlistItem Schema

Enrich with fields for the compact row display:

```python
class WatchlistItem(BaseModel):
    ticker: str
    name: str
    composite_raw_score: float        # Source of truth for label
    conviction_level: str             # "medium" (was "watchlist")
    sector: str | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    opportunity_type: str | None = None
```

### Dashboard Endpoint Changes

In `_fetch_picks_and_watchlist`:
- Picks: `WHERE conviction_level IN ("exceptional", "high")` — unchanged logic
- Watchlist: `WHERE conviction_level == "medium"` (was `"watchlist"`)
- Both sort by `composite_raw_score DESC` (was `composite_percentile DESC`)
- No limit on watchlist results

### No New Endpoints

Expansion details fetched from existing `GET /api/v1/scores/{ticker}?include=price_history,signal_history`.

### String Migration

Old DB rows store `"watchlist"`, new rows store `"medium"`. Either handle both strings during transition or run one-time migration: `UPDATE scores SET conviction_level = 'medium' WHERE conviction_level = 'watchlist'`.

---

## Section 3: Frontend — Watchlist Picks UI

### New Component: WatchlistPicksList

Replaces `WatchlistTable`. Lives in `web/src/components/dashboard/`.

### Collapsed State (compact row)

Each item renders as a row within a single card container:
- Sector color dot (left edge)
- Ticker (bold) + company name (truncated)
- `ConvictionBadge` showing "medium"
- Conviction score (numeric, e.g. "67")
- Price + upside % (if available)
- Chevron icon (right edge, rotates on expand)

Container: `.bg-bg-elevated` with border. Rows separated by subtle borders. Visually subordinate to Top Picks card grid above.

### Expanded State

- Click row -> fetch `GET /api/v1/scores/{ticker}?include=price_history,signal_history`
- Loading: skeleton/spinner inline below the row
- Success: render `AssetPanel` overlay (same as `StockCard`)
- Error: inline error below the row with "Retry" button; list remains intact
- Click again or Escape -> collapse

### Keyboard Accessibility

- Rows: `role="button"` with `tabIndex={0}`
- Enter/Space toggles expand/collapse
- Focus ring on tab navigation

### Empty State

Zero items: show "No Watchlist Picks available" — plain text, no placeholders.

### ConvictionBadge Update

Add `medium` style to `conviction-badge.tsx`:
- `bg-amber-500/10 text-amber-600 border-amber-500/20`
- Keep `watchlist` as alias for backward compat
- Badge text displays capitalized level name ("Medium", "High", "Exceptional")

---

## Section 4: Analytics + Error Handling

### Analytics Events

| Event | Payload | Trigger |
|---|---|---|
| `watchlist_pick_expand` | `{ ticker, conviction_score, conviction_level }` | User expands a row |
| `watchlist_pick_collapse` | `{ ticker, time_expanded_ms }` | User collapses a row |
| `watchlist_pick_expand_error` | `{ ticker, error_code, error_message }` | Score fetch fails |
| `watchlist_pick_expand_retry` | `{ ticker, attempt_number }` | User clicks Retry |

### Error Handling

- Fetch failure on expand: inline error below the row, rest of list untouched
- Retry re-fires same `GET /api/v1/scores/{ticker}` call
- No toast/modal — errors scoped to the failed row

---

## Acceptance Criteria

### Threshold Mapping

- **Given** an asset with `composite_raw_score` of 80, **when** conviction is computed, **then** `conviction_level` = "exceptional"
- **Given** an asset with `composite_raw_score` of 72, **when** conviction is computed, **then** `conviction_level` = "high"
- **Given** an asset with `composite_raw_score` of 65, **when** conviction is computed, **then** `conviction_level` = "medium"
- **Given** an asset with `composite_raw_score` of 64.9, **when** conviction is computed, **then** `conviction_level` = "none"

### Exclusion

- **Given** an asset with `composite_raw_score` < 65, **when** the dashboard loads, **then** the asset does not appear in Watchlist Picks or Top Picks

### Sorting

- **Given** multiple watchlist items, **when** the dashboard loads, **then** items are sorted by `composite_raw_score` descending

### Expansion

- **Given** a collapsed watchlist row, **when** the user clicks it (or presses Enter/Space), **then** the row expands and fetches score details via `/api/v1/scores/{ticker}`
- **Given** an expanded row, **when** the user clicks it again, **then** it collapses and the detail view is removed

### Error State

- **Given** an expanded row where the score fetch fails, **when** the error is displayed, **then** an inline error with "Retry" appears below the row and other rows remain interactive

### Empty State

- **Given** zero assets with `composite_raw_score` >= 65, **when** the dashboard loads, **then** the Watchlist section shows "No Watchlist Picks available"

---

## Files Affected

### Engine
- `engine/src/margin_engine/models/scoring.py` — ConvictionLevel enum, CompositeScore.conviction_level property, ScoringConfig thresholds

### API
- `api/src/margin_api/schemas/dashboard.py` — WatchlistItem schema enrichment
- `api/src/margin_api/routes/dashboard.py` — query filters, sort order, row extraction
- DB migration: `conviction_level` string values `"watchlist"` -> `"medium"`

### Frontend
- `web/src/lib/api/types.ts` — WatchlistItem type update
- `web/src/components/dashboard/watchlist-table.tsx` — replace with WatchlistPicksList
- `web/src/components/ui/conviction-badge.tsx` — add medium style
- `web/src/app/dashboard/page.tsx` — swap component import

### Tests
- Engine: golden-value tests for new thresholds
- API: dashboard endpoint tests for enriched watchlist, sorting, exclusion
- Frontend: component tests for expand/collapse, keyboard nav, error/empty states
