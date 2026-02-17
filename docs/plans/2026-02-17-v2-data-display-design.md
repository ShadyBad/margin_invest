# V2 Data Display Design

## Goal

Surface all Conviction Engine v2 scoring data (opportunity type, buy/sell prices, position sizing, timing signals, factor breakdowns by winning track) through the API and frontend for investor users. Two-view toggle: Thesis View (default, actionable) and Data View (full factor drilldown).

## Architecture

Extend existing data flow: Engine `CompositeScore` (already has v2 fields) -> API schemas (add v2 fields) -> TS types (add v2 fields) -> Components (add toggle + new sections). No new components; evolve `stock-card.tsx` and `asset-detail.tsx`.

## The Two Views

### Thesis View (Default)

Actionable investment summary. What to do and why.

**Stock Card (`stock-card.tsx`) changes:**
- Add opportunity type badge next to conviction badge (e.g. "Compounder", "Mispricing", "Both")
- Add margin of safety below price row (e.g. "MoS: 32%")
- Add position sizing line (e.g. "Max position: 10%")
- Add timing signal as subtle indicator (e.g. "Buy now" / "Add on pullback" / "Wait for catalyst")
- Replace generic Q/V/M percentile bars with winning track's pillar bars:
  - Compounder: Quality, Value, Capital Allocation
  - Mispricing: Value, Quality Floor, Catalyst
  - Both/Neither/null: Show all 3 original bars (backward compat)

**Asset Detail (`asset-detail.tsx`) changes:**
- Show winning track label in header (e.g. "Compounder Track")
- Show asymmetry ratio (e.g. "Asymmetry: 4.2x")
- Factor breakdown component shows winning track pillars by default
- Valuation breakdown gains margin of safety display

### Data View (Toggle)

Full factor drilldown for users who want to see the math.

**Toggled via a "Show Data" / "Show Thesis" text button in asset-detail header.**

**Shows:**
- All sub-factor scores with individual percentile bars, organized by winning track pillars
- Each pillar shows its weight and average percentile
- Valuation methods table with individual method values
- Conviction gates pass/fail list (from `filters_passed`)
- Raw score vs percentile comparison
- Asymmetry ratio calculation breakdown

## Data Flow Changes

### 1. Engine (no changes needed)

`CompositeScore` already has all v2 fields:
- `opportunity_type: OpportunityType | None`
- `winning_track: str | None`
- `asymmetry_ratio: float | None`
- `max_position_pct: float | None`
- `timing_signal: str | None`
- `capital_allocation: FactorBreakdown | None`
- `catalyst: FactorBreakdown | None`

### 2. API Schemas

**`ScoreResponse`** — add 7 fields:
```python
opportunity_type: str | None = None       # "compounder", "mispricing", "both", "neither"
winning_track: str | None = None          # "compounder" or "mispricing"
asymmetry_ratio: float | None = None
max_position_pct: float | None = None
timing_signal: str | None = None          # "buy_now", "add_on_pullback", "wait_for_catalyst"
capital_allocation: FactorBreakdownResponse | None = None
catalyst: FactorBreakdownResponse | None = None
```

Update `from_engine()` to map these fields.

**`PickSummary`** — add 5 fields:
```python
opportunity_type: str | None = None
winning_track: str | None = None
margin_of_safety: float | None = None
max_position_pct: float | None = None
timing_signal: str | None = None
```

### 3. DB Model

Add 5 nullable JSONB/float columns to `scores` table:
- `opportunity_type: String, nullable`
- `winning_track: String, nullable`
- `asymmetry_ratio: Float, nullable`
- `max_position_pct: Float, nullable`
- `timing_signal: String, nullable`

Capital allocation and catalyst breakdowns are already captured in the JSONB `score_data` column — no new columns needed for those.

One Alembic migration.

### 4. TypeScript Types

**`ScoreResponse`** — add:
```typescript
opportunity_type: string | null
winning_track: string | null
asymmetry_ratio: number | null
max_position_pct: number | null
timing_signal: string | null
capital_allocation: FactorBreakdownResponse | null
catalyst: FactorBreakdownResponse | null
```

**`PickSummary`** — add:
```typescript
opportunity_type: string | null
winning_track: string | null
margin_of_safety: number | null
max_position_pct: number | null
timing_signal: string | null
```

### 5. Frontend Components

**`stock-card.tsx`:**
- Opportunity type badge (colored pill: blue for compounder, purple for mispricing, gray for both/neither)
- Margin of safety in price row
- Position sizing line
- Timing signal indicator
- Winning-track-aware percentile bars

**`asset-detail.tsx`:**
- "Show Data" / "Show Thesis" toggle button in header
- Winning track label
- Asymmetry ratio display
- Conditional factor breakdown (thesis = winning track pillars, data = all sub-factors)

**`valuation-breakdown.tsx`:**
- Add margin of safety display
- Add asymmetry ratio if in data view

## Edge Cases

- **`opportunity_type = "neither"`**: Show "Unclassified" badge in muted gray
- **`price_target_invalid_reason` set**: Show warning instead of buy/sell prices, skip position sizing display
- **v1 scores (all v2 fields null)**: Render current layout exactly as-is. No toggle button shown. Backward compatible.
- **Watchlist items (`conviction_level = "watchlist"`)**: Skip position sizing and timing signal (these only apply to high/exceptional conviction)
- **`winning_track = null`**: Show all 3 original Q/V/M bars, no track label

## Files to Modify

1. `api/src/margin_api/schemas/scores.py` — add v2 fields to ScoreResponse + from_engine()
2. `api/src/margin_api/schemas/dashboard.py` — add v2 fields to PickSummary
3. `api/src/margin_api/db/models.py` — add v2 columns to scores table
4. `api/src/margin_api/routes/dashboard.py` — pass v2 fields when building PickSummary
5. `api/src/margin_api/routes/scores.py` — pass v2 fields when building ScoreResponse
6. `api/alembic/versions/` — new migration for v2 columns
7. `web/src/lib/api/types.ts` — add v2 fields to TS interfaces
8. `web/src/components/dashboard/stock-card.tsx` — opportunity badge, MoS, position sizing, timing, track-aware bars
9. `web/src/components/dashboard/asset-detail.tsx` — toggle, track label, asymmetry, conditional breakdown
10. `web/src/components/dashboard/valuation-breakdown.tsx` — margin of safety display
