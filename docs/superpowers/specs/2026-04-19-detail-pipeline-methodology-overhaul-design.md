# Detail Page, Data Pipeline & Methodology Overhaul — Design Spec

**Date:** 2026-04-19  
**Scope:** Unified full-stack fix covering asset detail page UX, data pipeline bugs, smart money market signals, methodology page visuals, and reference guide styling.  
**Approach:** Phased by priority — Detail Page UX (Cluster 1), Data Pipeline (Cluster 3), Methodology Visuals (Cluster 2).

---

## 1. Signal & Score Fix (Data Layer)

### Problem

`CompositeScore.signal` is a `@property` on the engine model — excluded from Pydantic's `model_dump()` output. When V4Score records are persisted via `cli.py:1850`, the signal is never stored in the `detail` JSONB blob.

The API response builder (`scores.py:229`) attempts to reconstruct it:

```python
detail.setdefault("signal", detail.get("signal", "no_action"))
```

Since `signal` was never stored, this hardcodes `"no_action"` for every candidate. The frontend then displays `"NO_ACTION"` (uppercased raw string) instead of a meaningful signal.

### Root Cause Chain

```
Engine CompositeScore.signal @property
  → NOT included in model_dump() during persistence (cli.py:1850)
  → V4Score.detail JSONB has no "signal" key
  → API fallback hardcodes "no_action" string (scores.py:229)
  → Frontend displays "NO_ACTION"
```

### Fix

Add a `_recompute_signal()` function in `scores.py` that derives the signal from the stored `composite_tier` and price data, mirroring the engine's `CompositeScore.signal` property logic:

| Composite Tier | Condition | Signal |
|---|---|---|
| `exceptional` / `high` | margin_of_safety > 0 | `"strong"` |
| `exceptional` / `high` | margin_of_safety ≤ 0 | `"stable"` |
| `medium` | — | `"emerging"` |
| `none` | — | `"neutral"` |

Replace `scores.py:229` with:

```python
detail["signal"] = _recompute_signal(
    composite_tier=detail.get("composite_tier"),
    margin_of_safety=detail.get("margin_of_safety"),
)
```

~15 lines. No engine changes needed.

### Files Changed

- `api/src/margin_api/routes/scores.py` — add `_recompute_signal()`, replace line 229

---

## 2. Detail Page UX Redesign

### 2A. Timing Signal → Hero Position

**Current:** Timing signal is one of three small metrics in the Conviction Engine section, buried below the scoring breakdown.

**Change:** Elevate timing signal into `InstrumentHeader`, displayed directly below the score/tier as a prominent color-coded pill:

```
[ Score: 78 ]
[ EXCEPTIONAL ]
[ ▶ BUY NOW ]         ← color-coded pill
```

Color mapping:
- `buy_now` → green (`--color-bullish`)
- `add_on_pullback` → amber (`--color-warning`)
- `wait_for_catalyst` → muted (`--color-on-surface-variant`)

The Conviction Engine retains asymmetry ratio and max position but loses the timing signal (no duplication).

**Files changed:**
- `web/src/components/asset-detail/instrument-header.tsx` — add `timingSignal` prop, render pill below tier badge
- `web/src/components/asset-detail/asset-detail-view.tsx` — pass `timingSignal` to InstrumentHeader
- `web/src/components/asset-detail/conviction-engine.tsx` — remove timing signal from 3-metric grid (becomes 2-metric)

### 2B. Elimination Gauntlet → Filter Pills

**Current:** Each filter renders as a full FilterCard with Value/Threshold/Result table, formula, citation, and "Why This Matters" expandable sections.

**Change:** Replace with a compact horizontal pill strip. Each filter becomes a rounded pill:

```
[✓ Beneish -2.4] [✓ Altman 3.1] [✓ Current Ratio 1.8] [✗ Liquidity $12M]
```

Pill design:
- Pass/fail icon (✓/✗/?) + filter short name + formatted value
- Border color: green (pass), red (fail), amber (inconclusive)
- Background: subtle tinted fill matching border color at 8% opacity
- No threshold displayed
- **Click to expand:** Opens the existing FilterCard detail content inline below the pill strip (formula, citation, "Why This Matters")
- Section header ("ELIMINATION GAUNTLET") and elimination stats ("X of Y passed", "N% eliminated") remain

Layout: `flex flex-wrap gap-2` — pills flow naturally across available width.

**Files changed:**
- `web/src/components/asset-detail/elimination-gauntlet.tsx` — replace FilterCard list with pill strip + expandable detail
- `web/src/components/asset-detail/filter-card.tsx` — refactor into `FilterPill` (compact) and `FilterDetail` (expanded content)

### 2C. Remove "Weighted by Growth Stage"

**Current:** `ScoringPillars` header shows `"Weighted by growth stage: [Stage] (Q:XX% · V:XX% · M:XX%)"`.

**Change:** Remove the entire weight description line. Section header remains as `"SCORING BREAKDOWN"` with just the three pillar cards below.

**Files changed:**
- `web/src/components/asset-detail/scoring-pillars.tsx` — remove `formatGrowthStage()`, `getWeightLabel()`, and the `<p>` tag showing weights. Remove `growthStage` prop.
- `web/src/components/asset-detail/asset-detail-view.tsx` — stop passing `growthStage` to ScoringPillars

### 2D. Max Position — More Context

**Current:** Shows `"4.2%"` with label `"Kelly-optimal sizing"`.

**Change:** Expand to include:
- **Kelly confidence level:** `"Half-Kelly"` or `"Quarter-Kelly"` (derived from the engine's Kelly sizing logic — verify threshold against `engine/src/margin_engine/sizing/` during implementation)
- **Dollar example:** `"~$2,100 per $50K portfolio"` (compute `maxPositionPct * 50000 / 100`)
- **Risk context:** `"Based on asymmetry ratio and conviction score"`

Layout (vertical stack within the existing metric cell):
```
MAX POSITION
4.2%  · Half-Kelly
~$2,100 per $50K portfolio
Based on asymmetry ratio and conviction score
```

**Files changed:**
- `web/src/components/asset-detail/conviction-engine.tsx` — expand max position rendering with Kelly level and dollar example

### 2E. Sentiment Score — Pending State

**Current:** When sentiment is null, the factor profile bar shows `"—"`.

**Root cause:** `MARGIN_NLP_ENABLED` defaults to `"false"`. The NLP pipeline (Claude API on SEC filings) never runs, so `filing_sentiment_cache` is empty.

**Change (frontend only — enabling the pipeline is out of scope):**
- When sentiment percentile is null, display `"PENDING"` in the factor profile bar instead of `"—"`
- Add a tooltip: `"Sentiment analysis available when NLP pipeline is enabled"`
- Use a distinct muted style (dashed border, 30% opacity) to differentiate from scored factors

**Files changed:**
- `web/src/components/asset-detail/factor-profile.tsx` — handle null sentiment with "PENDING" label and tooltip

---

## 3. Data Pipeline Fixes

### 3A. Shadow Portfolio — Unblock from Governance Gate

**Problem:** `snapshot_shadow_portfolio` worker (`workers.py:3933`) queries `.where(V4Score.published.is_(True))`. No scores have been approved since 2/28, so the worker finds nothing to snapshot despite running daily at 22:30 UTC.

**Fix:** Remove the `published == True` filter. The shadow portfolio is a forward-looking tracking tool — it should reflect the system's current best-scored picks regardless of governance approval status.

- Query all V4Scores ordered by `composite_score DESC`
- Add a `source` string field to each position in `positions_json`: `"published"` if the V4Score is published, `"staged"` otherwise
- Frontend can optionally display a subtle badge if picks are from staged (unapproved) scores

**Files changed:**
- `api/src/margin_api/workers.py` — `snapshot_shadow_portfolio()`: remove `.where(published == True)`, add `source` field to positions

### 3B. Backtest Results — Persist to DB

**Problem:** Default backtest results are stored in `_backtest_store` (in-memory dict, `backtest.py:50`). This resets on every Railway deployment. The `precompute_default_backtest` cron (Sunday 3AM) populates it, but it's lost within hours.

**Fix:** Persist default backtest results to the `backtest_results` table in the database instead of the in-memory dict. The endpoint reads from DB.

**Files changed:**
- `api/src/margin_api/routes/backtest.py` — `get_default_backtest()`: read from DB instead of `_backtest_store`
- `api/src/margin_api/workers.py` — `precompute_default_backtest()`: write to DB instead of `_backtest_store`

### 3C. Institutional Holdings — No Code Change

The `InstitutionalPositioning` component is already wired (`asset-detail-view.tsx:209`) and fetches from `/api/v1/13f/holdings/{ticker}`. Empty display means the 13F pipeline hasn't ingested holdings for that specific ticker. This is a data availability issue, not a code issue. No change needed.

---

## 4. Smart Money — Market Pulse

### Problem

The Market Signals tab shows only ticker-level data (most-held positions, new positions, crowded trades). No market-level aggregate signals exist.

### New: Market Pulse Section

Add a `MarketPulse` component at the top of the Market Signals tab, above the existing three sections. All metrics are derived from existing `accumulation_signals` and `institutional_holdings` data — no new data ingestion required.

#### 4 Metrics

1. **Institutional Breadth**
   - Metric: `% of tracked universe in net accumulation` (where `curated_net_shares > 0`)
   - Display: `"62% Accumulating"` with directional arrow (↑/↓)
   - Color: green if > 50%, red if < 50%

2. **Sector Rotation Heatmap**
   - Compact grid, one cell per GICS sector
   - Color: green (net buying), red (net selling), gray (neutral)
   - Derived by aggregating `curated_net_shares` per sector from `accumulation_signals`
   - Each cell shows sector abbreviation + directional indicator

3. **Smart Money Consensus**
   - Top 5 tickers where the most curated managers agree
   - Ranked by `curated_holders` count relative to total tracked curated managers
   - Display: ticker + agreement strength percentage

4. **Flow Trend**
   - Quarter-over-quarter change in total institutional positions
   - Compare current quarter's total `curated_holders` sum vs prior quarter
   - Display: `"↑ 12% more positions vs last quarter"` or `"↓ 8% fewer positions"`

#### Backend

New endpoint: `GET /api/v1/13f/analytics/market-pulse`

Response schema:
```python
class MarketPulseResponse(BaseModel):
    breadth_pct: float                          # % of universe in net accumulation
    breadth_direction: str                      # "up" | "down" | "flat"
    sector_flows: list[SectorFlowItem]          # sector, net_shares, direction
    consensus_picks: list[ConsensusPick]        # ticker, curated_holders, agreement_pct
    flow_trend_pct: float                       # QoQ change in total positions
    flow_trend_direction: str                   # "up" | "down" | "flat"
    as_of_quarter: str                          # "Q1 2026"
```

Implementation: single DB query aggregating `accumulation_signals` joined with `assets` (for sector). No new tables, no new ingestion.

#### Frontend

New component: `web/src/components/smart-money/market-pulse.tsx`
- 4-metric grid at the top of the Market Signals tab
- Responsive: 2×2 on mobile, 4×1 on desktop
- Uses existing design tokens (bullish/bearish colors, surface hierarchy)

**Files changed:**
- `api/src/margin_api/routes/thirteenf.py` — add `GET /analytics/market-pulse` endpoint
- `api/src/margin_api/schemas/thirteenf.py` — add `MarketPulseResponse`, `SectorFlowItem`, `ConsensusPick` schemas
- `web/src/lib/api/thirteenf.ts` — add `getMarketPulse()` client function
- `web/src/lib/api/types.ts` — add TypeScript types for market pulse response
- `web/src/components/smart-money/market-pulse.tsx` — new component
- `web/src/components/smart-money/market-signals.tsx` — render MarketPulse at top

---

## 5. Methodology Page Visual Fixes

### 5A. Define `--color-value` CSS Variable

**Root cause:** `score-breakdown-bars.tsx` and `outputs-section.tsx` reference `bg-[var(--color-value)]` but `--color-value` is never defined in `globals.css`. Value-colored bars render invisible.

**Fix:** Add to `globals.css` `@theme` block:
```css
--color-value: #14B8A6;
```

Teal (#14B8A6) — creates a consistent three-color factor system:
- Quality → emerald (`--color-accent` / `--color-primary`)
- Value → teal (`--color-value`)
- Momentum → gold (`--color-warning`)

This single fix resolves bars missing in Stage 2 example, Stage 3 example card, and Stage 7 factor breakdown.

**Files changed:**
- `web/src/app/globals.css` — add `--color-value` to `@theme` block

### 5B. Stage 2 — Filter Funnel Bar Visibility

The `FilterFunnel` component renders correctly but bars may appear faint due to `--color-accent-subtle` on the dark surface.

**Fix:** Increase bar opacity and add a left border accent to each bar for definition.

**Files changed:**
- `web/src/components/methodology/visuals/filter-funnel.tsx` — increase opacity, add left border

### 5C. Stage 3 — Momentum Gold/Yellow

**Intentional design.** No change. `--color-warning: #D4A843` is the designated momentum color.

### 5D. Candidate Journey Line Graph — Contrast

**Current:** Emerald line at `strokeWidth={2}`, dot radius 4. Low contrast on dark background.

**Fix:**
- Increase `strokeWidth` from 2 to 3
- Add subtle glow via SVG filter (`drop-shadow(0 0 4px var(--color-accent))`)
- Increase dot radius from 4 to 5
- Add score value labels at each data point

**Files changed:**
- `web/src/components/methodology/visuals/candidate-journey-chart.tsx` — increase stroke, add glow, label data points

### 5E. Outputs Section Bars

Fixed by 5A (`--color-value` definition). Verify example data in `outputs-section.tsx` includes all expected factors with non-zero percentile values.

**Files changed:**
- `web/src/components/methodology/sections/outputs-section.tsx` — verify/fix example data if needed

---

## 6. Reference Guide Color

**Current:** Concepts = blue (`#3B82F6`), Workflows = teal (`#14B8A6`), Reference = gray (`text-text-tertiary`).

**Change:** Assign Reference the color amber (`#D4A843`) — the existing `--color-warning` token.

Palette rationale:
- **Concepts** — Blue (learning/theory)
- **Workflows** — Teal (process/action)
- **Reference** — Amber (lookup/specification)

Three distinct, meaningful colors.

**Files changed:**
- `web/src/components/guides/guide-card.tsx` — update `CATEGORY_COLORS`, `CATEGORY_TEXT`, `CATEGORY_BG` for Reference:
  ```typescript
  Reference: "#D4A843"
  Reference: "text-[#D4A843]"
  Reference: "bg-[#D4A843]/10"
  ```

---

## Summary of All Files Changed

### API (Python)
| File | Change |
|---|---|
| `api/src/margin_api/routes/scores.py` | Add `_recompute_signal()`, fix signal reconstruction |
| `api/src/margin_api/routes/backtest.py` | Read default backtest from DB, not in-memory |
| `api/src/margin_api/routes/thirteenf.py` | Add `GET /analytics/market-pulse` endpoint |
| `api/src/margin_api/schemas/thirteenf.py` | Add MarketPulseResponse, SectorFlowItem, ConsensusPick |
| `api/src/margin_api/workers.py` | Shadow portfolio: remove published filter; default backtest: persist to DB |

### Web (TypeScript/CSS)
| File | Change |
|---|---|
| `web/src/app/globals.css` | Add `--color-value: #14B8A6` |
| `web/src/components/asset-detail/instrument-header.tsx` | Add timing signal pill below tier |
| `web/src/components/asset-detail/asset-detail-view.tsx` | Pass timingSignal to header, remove growthStage from pillars |
| `web/src/components/asset-detail/elimination-gauntlet.tsx` | Replace FilterCard list with pill strip |
| `web/src/components/asset-detail/filter-card.tsx` | Refactor into FilterPill + FilterDetail |
| `web/src/components/asset-detail/scoring-pillars.tsx` | Remove growth stage weight text |
| `web/src/components/asset-detail/conviction-engine.tsx` | Remove timing signal, expand max position context |
| `web/src/components/asset-detail/factor-profile.tsx` | Sentiment "PENDING" state |
| `web/src/components/smart-money/market-pulse.tsx` | **New** — market pulse metrics |
| `web/src/components/smart-money/market-signals.tsx` | Render MarketPulse at top |
| `web/src/lib/api/thirteenf.ts` | Add `getMarketPulse()` |
| `web/src/lib/api/types.ts` | Add market pulse TypeScript types |
| `web/src/components/methodology/visuals/filter-funnel.tsx` | Increase bar visibility |
| `web/src/components/methodology/visuals/candidate-journey-chart.tsx` | Thicker line, glow, labels |
| `web/src/components/methodology/visuals/score-breakdown-bars.tsx` | Verify renders with --color-value |
| `web/src/components/methodology/sections/outputs-section.tsx` | Verify example data completeness |
| `web/src/components/guides/guide-card.tsx` | Reference → amber color |

### New Files
| File | Purpose |
|---|---|
| `web/src/components/smart-money/market-pulse.tsx` | Market-level aggregate signals component |

---

## Out of Scope

- Enabling the NLP sentiment pipeline in production (requires Claude API budget)
- Governance approval workflow automation
- 13F data ingestion for specific tickers missing institutional holdings
- Backfilling shadow portfolio snapshots for the 2/28–4/19 gap (forward-only)
