# Card Data Integrity: Audit-First Fix

**Date:** 2026-02-20
**Status:** Approved
**Scope:** Display correctness — ensure dashboard cards faithfully show authoritative Score record values

## Problem

Dashboard cards show incorrect conviction scores, signals, and prices. Multiple card fields don't match known real-world values for recently scored tickers. Root cause unknown — this design takes an audit-first approach to diagnose before fixing.

## Architecture: Data Pipeline

```
Engine (CompositeScore) → CLI save → DB Score table → Dashboard API → Frontend Card
                            ↓                            ↓
                     score_detail JSONB          _pick_summary_from_row()
                     (missing @property)         reads DB columns directly
```

**Key insight:** The engine's `CompositeScore` has `conviction_level`, `signal`, `average_percentile`, and `verdict` as `@property` decorators. These are NOT included in `model_dump()`, so the `score_detail` JSONB blob is missing them. The CLI save code correctly extracts these via the @property at save time into DB columns — but any code path that reconstructs from JSONB instead of columns gets wrong values.

## Failure Mode Analysis

### 1. JS Falsy Fallback (HIGH)

**File:** `web/src/components/dashboard/stock-card.tsx:188`

```tsx
// Current (broken for score=0):
pick.score || pick.composite_percentile

// Problem: if composite_raw_score is 0.0 (DB default),
// JavaScript treats it as falsy and falls through to
// composite_percentile — a DIFFERENT metric.
```

### 2. `score_detail` JSONB Missing @property Fields (HIGH)

**File:** `api/src/margin_api/cli.py:438`

`composite.model_dump(mode="json")` excludes:
- `conviction_level` (computed from composite_raw_score thresholds)
- `signal` (computed from conviction + price targets)
- `average_percentile` on each FactorBreakdown
- `verdict` on each FilterResult

The score detail endpoint (`scores.py:59-77`) patches these in via `setdefault()`, but any failure in that patching path falls through to a summary-column fallback silently.

### 3. Two Divergent Mapping Functions (MEDIUM)

- `_pick_summary_from_row()` in `dashboard.py` — reads DB columns directly
- `_score_response_from_row()` in `scores.py` — tries JSONB first, falls back to columns

Card and detail panel use different code paths. Any divergence means clicking a card shows different values than the card itself.

### 4. Price Target Field Confusion (MEDIUM)

- `price_upside` computed from `margin_invest_value` (intrinsic value) and `actual_price`
- `sell_price` is the actual target price
- Card shows `sell_price` as "Target" but upside is based on `margin_invest_value`

### 5. Stale `actual_price` (MEDIUM)

Dashboard endpoint does NOT attempt Redis live price lookup (unlike score detail endpoint). Card shows scoring-time price as "Price" without age indicator.

### 6. No Engine Run Traceability (LOW)

No `score_id` or `engine_run_id` on the card response. Impossible to audit which DB record produced a given card.

## Data Contract

### Card Field → Authoritative Source

| Card Element | Authoritative Source | DB Column |
|---|---|---|
| Score number ("Conviction") | `Score.composite_raw_score` | `composite_raw_score` |
| Conviction badge | `Score.conviction_level` | `conviction_level` |
| Action pill | `Score.signal` | `signal` |
| Quality bar | `Score.quality_percentile` | `quality_percentile` |
| Value bar | `Score.value_percentile` | `value_percentile` |
| Momentum bar | `Score.momentum_percentile` | `momentum_percentile` |
| Price | `Score.actual_price` | `actual_price` |
| Target | `Score.sell_price` | `sell_price` |
| Price upside | Derived: `(margin_invest_value - actual_price) / actual_price` | N/A |
| Margin of safety | Derived: `(margin_invest_value - actual_price) / margin_invest_value` | N/A |
| Opportunity type | `Score.opportunity_type` | `opportunity_type` |
| Max position | `Score.max_position_pct` | `max_position_pct` |
| Timing signal | `Score.timing_signal` | `timing_signal` |
| Data freshness | Derived: `compute_freshness(Score.scored_at)` | N/A |

### Required Identifiers

Every `PickSummary` response MUST include:
- `scored_at` (ISO 8601) — when score was computed
- `score_id` (int) — primary key of Score row for direct DB lookup

### Validation Rules

1. `conviction_level` MUST match engine thresholds applied to `composite_raw_score`: >= 79 → exceptional, >= 72 → high, >= 65 → medium, < 65 → none
2. `signal` MUST match engine derivation from conviction + price targets
3. `price_upside` MUST be null when `price_target_invalid_reason` is set
4. `actual_price` MUST carry freshness context

## Implementation Plan

### Phase 1: Audit Endpoint

Add `GET /api/v1/dashboard/audit` that returns, for each card:
- `card_values`: what `_pick_summary_from_row()` produces
- `db_values`: raw DB column values
- `derived_values`: re-derived conviction_level and signal from composite_raw_score
- `mismatches`: list of field names where values disagree

### Phase 2: Targeted Fixes

**Fix 1: JS falsy fallback**
- File: `web/src/components/dashboard/stock-card.tsx:188`
- Change: `pick.score || pick.composite_percentile` → `pick.score ?? pick.composite_percentile`

**Fix 2: Add `score_id` to PickSummary**
- Files: `api/src/margin_api/schemas/dashboard.py`, `api/src/margin_api/routes/dashboard.py`
- Add `score_id: int` populated from `s.id`

**Fix 3: Consolidate mapping functions (if audit confirms divergence)**
- Extract shared mapping logic into `ScoreMapper` service
- Both dashboard and score detail endpoints use same mapper

### Phase 3: Regression Tests

- Unit: `_pick_summary_from_row()` with `composite_raw_score=0.0` shows 0.0 (not percentile)
- Unit: conviction derivation boundary: 79.0 → exceptional, 78.9 → high
- Integration: dashboard API response matches direct DB query for each field
- E2E: Playwright test comparing card DOM values to API response JSON

### Performance

- Audit endpoint: read-only, reuses existing dashboard query
- `score_id`: already on ORM object, zero DB cost
- `??` fix: zero-cost JS operator

### Missing/Late Data

- `composite_raw_score` null/0 AND `composite_percentile` null → show "—"
- `actual_price` null → show "N/A" (already implemented)
- `scored_at` > 7 days → show "expired" badge (already implemented)

## Bug Ticket

**Title:** Card values don't match authoritative Score record — data integrity audit needed

**Impact:** Users see incorrect conviction scores, signals, and prices on dashboard cards, undermining trust.

**Severity:** P1

**Repro:**
1. `uv run python -m margin_api.cli seed --tickers AAPL MSFT`
2. `uv run python -m margin_api.cli score --tickers AAPL MSFT`
3. Open dashboard at `http://localhost:3000/dashboard`
4. Compare card values against `GET /api/v1/scores/AAPL`
5. Compare API response against `SELECT * FROM scores WHERE asset_id = (SELECT id FROM assets WHERE ticker = 'AAPL') ORDER BY scored_at DESC LIMIT 1`

**Expected:** Card values match latest Score DB record exactly.

**Actual:** Multiple card fields show incorrect values.

**Acceptance Criteria:**
1. Audit endpoint confirms zero mismatches between card and DB values
2. `??` used instead of `||` for score display
3. `PickSummary` includes `score_id` and `scored_at`
4. Conviction badge matches `composite_raw_score` threshold derivation
5. Detail panel values match card values for same ticker
