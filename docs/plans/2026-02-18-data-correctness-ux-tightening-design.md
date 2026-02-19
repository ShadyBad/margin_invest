# Data Correctness & UX Tightening Design

**Date:** 2026-02-18
**Status:** Approved
**Approach:** Data-Up (engine → API → frontend)

## Goals (Priority Order)

1. **Data correctness:** All calculated values—especially Margin Invest Value and MoS—must be 100% accurate, explainable, and reproducible.
2. **Data completeness:** Fields should not display "—" for most assets unless truly unavailable; implement fallbacks and sourcing improvements.
3. **Investor-aligned filtering:** Thresholds must be sensible for institutional-grade investing (not arbitrary global thresholds).
4. **Truthful history:** Anything labeled "history" must be time-series history, not "last run."
5. **UX clarity:** Remove redundant sections and present information cleanly.

## Design Decisions (from brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| MoS model | Dual threshold | `buy = MIV*(1-MoS)`, `sell = MIV*(1+MoS)`. Symmetric band around fair value. |
| Filter config | YAML file | `engine/config/filters.yaml`. Version-controllable, engine stays pure Python. |
| Delta metric | Score change between runs | `current_score - previous_score`. Natural fit with score history. |
| Allocation metric | Position sizing recommendation | Conviction + volatility based. Always computable. |
| Score history source | Expose existing + accumulate | DB already has append-only rows. Build API, no backfill needed. |

---

## Section 1: Valuation Model — Dual Threshold MoS

### Root Cause

`price_targets.py` sets `buy_price = intrinsic_value` (identical values). MoS only pushes `sell_price` upward. "Buy Below" is semantically meaningless—it's just intrinsic value with a different label.

### Fix

Change the core relationship in `compute_price_targets()`:

```
margin_invest_value = weighted_average(DCF, EV/FCF, Acquirer's, SHY)  # unchanged
mos = dynamic_mos(growth_stage, dispersion)                            # unchanged [15%-50%]
buy_price  = margin_invest_value * (1 - mos)                          # NEW: discounted entry
sell_price = margin_invest_value * (1 + mos)                          # unchanged
```

### Signal Logic (5-tier)

| Condition | Signal |
|---|---|
| `price <= buy_price` | BUY |
| `buy_price < price <= margin_invest_value` | HOLD |
| `margin_invest_value < price < sell_price` | HOLD |
| `price >= sell_price` | SELL |
| `price >= sell_price * 1.15` | URGENT_SELL |

### Worked Example (steady_growth, 25% MoS)

```
Margin Invest Value:  $198.00
MoS:                  25%
Buy Price:            $148.50  ($198 * 0.75)
Sell Price:           $247.50  ($198 * 1.25)
Current Price:        $185.00
Signal:               HOLD (between buy and fair value)
```

### Rename

All references to "Intrinsic Value" → "Margin Invest Value" across engine, API, DB (Alembic migration), and frontend.

### What Changes

- `price_targets.py`: `buy_price = iv * (1 - mos)` instead of `buy_price = iv`
- `CompositeScore.signal` property: updated thresholds
- DB column: `intrinsic_value` → `margin_invest_value` (Alembic migration)
- API response field: same rename
- Frontend: all "Intrinsic Value" labels → "Margin Invest Value"

### What Does NOT Change

- The four valuation methods and their weights (DCF 35%, EV/FCF 25%, Acquirer's 20%, SHY 20%)
- The dynamic MoS calculation (growth stage + dispersion)
- The validation layers (bounds checking, outlier filter, clamping)
- How valuation feeds into composite scoring (value sub-factors are independent)

### Acceptance Criteria

- Given identical inputs, `buy_price < margin_invest_value < sell_price` always holds
- `buy_price = margin_invest_value * (1 - mos)` — verified by golden-value test
- `sell_price = margin_invest_value * (1 + mos)` — verified by golden-value test
- Signal transitions match the 5-tier logic
- No reference to "Intrinsic Value" remains in codebase
- Alembic migration renames the column without data loss

---

## Section 2: Filter Redesign

### A1. Liquidity Filter — Tiered Dollar Volume

**Problem:** Single `$1M` dollar volume floor across all market caps.

**Fix:** Tiered thresholds by market cap bucket:

| Market Cap Bucket | Median Daily $ Volume Floor |
|---|---|
| Mega (>$200B) | $50M |
| Large ($10B-$200B) | $20M |
| Mid ($2B-$10B) | $5M |
| Small ($300M-$2B) | $2M |

**Optional position impact check** (off by default):
```
days_to_build = position_value / (median_daily_dollar_vol * participation_rate)
PASS if days_to_build <= max_days  (default: 5 days, 10% participation)
```

Dollar volume window: configurable, default 60 trading days. Currently uses `avg_daily_dollar_volume` from `AssetProfile`.

### A2. Beneish M-Score — Insufficient History

**Problem:** Auto-passes silently when prior period data is missing.

**Fix:**

1. Add `insufficient_data: bool` and `missing_fields: list[str] | None` to `FilterResult`. Filter still passes but flags why M-Score couldn't be computed.

2. Compute M-Score for every fiscal period with adequate data (current+prior pairs) from `FinancialHistory`. Store per-period results in `score_detail` JSONB:
   ```json
   {
     "filter_history": {
       "beneish": [
         {"period": "FY2024", "m_score": -2.79, "passed": true},
         {"period": "FY2023", "m_score": -2.45, "passed": true}
       ]
     }
   }
   ```

3. Frontend shows "M-Score unavailable: missing prior period balance sheet" instead of "—".

### A3. Financial Health — Multi-Year Rules

**FCF Distress** (evolve from single `FCF >= 0`):

| Rule | Default |
|---|---|
| Annual FCF positive in 3 of last 5 years | 3/5 |
| Most recent annual FCF | >= 0 OR trending positive (2yr) |
| FCF margin (FCF/Revenue) | > -5% floor |

**Interest Coverage** (add trend stability):

| Rule | Default |
|---|---|
| Current ICR | Sector-adjusted (Tech 3.0, Utilities 1.2, default 1.5) |
| 3-year median ICR | > 1.0 |
| EBIT anomaly guard | EBIT < 0 with interest > 0: auto-fail with explanation |

**Current Ratio** (add context):

| Rule | Default |
|---|---|
| Current CR | Sector-adjusted (Tech 0.8, Utilities 0.6, default 0.8) |
| Quick Ratio rescue | If CR < threshold, check QR > 0.5 |
| 3-year trend | CR must not decline >30% over 3 years |

Multi-year rules require `FinancialHistory` input. Pipeline signature changes to accept `FinancialHistory | None` with fallback to single-period behavior.

### YAML Configuration

All thresholds move to `engine/config/filters.yaml`:

```yaml
liquidity:
  excluded_sectors: ["Financials", "Real Estate"]
  min_years_of_history: 5
  market_cap_minimum:
    default: 300_000_000
    utilities: 1_000_000_000
    energy: 500_000_000
  dollar_volume:
    mega: 50_000_000
    large: 20_000_000
    mid: 5_000_000
    small: 2_000_000
  dollar_volume_window_days: 60
  position_impact:
    enabled: false
    max_days: 5
    participation_rate: 0.10

beneish:
  threshold: -1.78

altman:
  threshold: 1.1
  equity_tl_cap: 10.0
  exempt_sectors: ["Utilities"]

fcf_distress:
  positive_years_required: 3
  lookback_years: 5
  min_fcf_margin: -0.05
  allow_positive_trend_rescue: true

interest_coverage:
  default: 1.5
  sector_overrides:
    technology: 3.0
    utilities: 1.2
  median_lookback_years: 3
  median_minimum: 1.0

current_ratio:
  default: 0.8
  sector_overrides:
    technology: 0.8
    utilities: 0.6
  quick_ratio_rescue: 0.5
  max_3yr_decline_pct: 30

mediocrity_gate:
  min_roic_5yr_median: 0.08
  gross_margin:
    default: 0.20
    energy: 0.15
    utilities: 0.10
  fcf_positive_years: 4
  fcf_lookback_years: 5
  max_consecutive_revenue_decline: 3
```

A `FilterConfig` Pydantic model validates YAML at startup. Default values match current hardcoded values for zero behavior change if YAML is missing.

### Acceptance Criteria (Section 2)

- All filter thresholds load from `filters.yaml`; hardcoded constants removed
- Liquidity dollar volume threshold varies by market cap bucket
- Beneish `insufficient_data` flag set when data missing; UI shows missing field names
- Multi-period M-Scores stored in `score_detail` JSONB when history available
- FCF checks 3-of-5-years positive when `FinancialHistory` provided; single-period fallback
- Interest coverage checks 3-year median alongside current value
- Current ratio has quick-ratio rescue path
- Golden-value tests for each filter with known fixtures
- Config changes require no code changes—only `filters.yaml` edits

---

## Section 3: Metrics & Data Fixes

### Fix 1: Avg Profit Margin — Key-Name Bug

**Root Cause:** `compute_avg_profit_margin()` looks for `"net_income"` / `"total_revenue"` but yfinance stores `"Net Income"` / `"Total Revenue"`.

**Fix:** Case-insensitive key resolver:

```python
def _get_field(period: dict, *candidates: str) -> float | None:
    for key in candidates:
        if key in period:
            val = period[key]
            return float(val) if val is not None else None
    return None
```

Definition: Net profit margin, averaged across available annual periods. `mean(net_income / total_revenue)`.

### Fix 2: Allocation — Reliable Position Sizing

**Root Cause:** `allocation_weight` pulls from `Score.max_position_pct`, only populated by v2 Conviction Engine (often NULL).

**Fix:** Compute deterministically from conviction + volatility:

```python
def compute_allocation_weight(conviction: str, volatility: float | None) -> float:
    base = {"exceptional": 8.0, "high": 5.0, "moderate": 3.0, "watchlist": 2.0}.get(conviction, 2.0)
    if volatility is not None:
        if volatility > 40:
            base *= 0.5
        elif volatility > 25:
            base *= 0.75
    return round(base, 1)
```

### Fix 3: Delta — Score Change Between Runs

Depends on Section 4 (Score History API). Once available:

```python
delta = current_row.composite_percentile - previous_row.composite_percentile
```

Display: `+4.2 ▲` (green) / `-3.1 ▼` (red) / `—` (first-ever score)

### Fix 4: Structured Unavailability Reasons

Replace bare nulls with `MetricStatus`:

```python
class MetricStatus(BaseModel):
    value: float | None
    unavailable_reason: str | None = None

class InstitutionalMetricsResponse(BaseModel):
    sharpe_ratio: MetricStatus
    max_drawdown: MetricStatus
    volatility: MetricStatus
    avg_profit_margin: MetricStatus
    allocation_weight: MetricStatus
    margin_of_safety: MetricStatus
    risk_classification: str
```

Frontend `KpiCell` shows reason string below "—" in muted text.

### Metric Definitions

| Metric | Definition | Lookback | Min Data |
|---|---|---|---|
| Sharpe Ratio | `(mean_daily - rf/252) / std(daily) * sqrt(252)` | All bars | >= 60 bars |
| Max Drawdown | Peak-to-trough decline | All bars | >= 5 bars |
| Volatility | `std(daily) * sqrt(252) * 100` as % | All bars | >= 60 bars |
| Avg Profit Margin | `mean(net_income / revenue)` annual | All periods | >= 1 period |
| Allocation | Conviction + vol position sizing | Current | Always |
| Margin of Safety | `(MIV - price) / MIV` as % | Current | Valid MIV + price |

Risk-free rate: configurable in YAML, default 4.5%.

### Acceptance Criteria (Section 3)

- Avg Profit Margin populates for all assets with income statement data
- Allocation always shows a value when a score exists
- Delta shows real score change once history is available
- Sharpe/Vol require >= 60 bars; unavailable reason returned when insufficient
- All KPI cells show specific reason instead of bare "—"
- Risk-free rate configurable, not hardcoded

---

## Section 4: Score History & Charts

### Score History API

**New endpoint:** `GET /api/v1/scores/{ticker}/history`

```python
class ScoreHistoryPoint(BaseModel):
    scored_at: datetime
    composite_percentile: float
    composite_raw_score: float | None
    quality_percentile: float | None
    value_percentile: float | None
    momentum_percentile: float | None
    conviction_level: str
    signal: str
    margin_invest_value: float | None
    buy_price: float | None
    sell_price: float | None
    actual_price: float | None
    delta: float | None

class ScoreHistoryResponse(BaseModel):
    ticker: str
    points: list[ScoreHistoryPoint]
    total_runs: int
```

Query uses existing `ix_scores_asset_scored` index. No new tables or migrations needed.

### D1: Score History Chart

`ScoreChart` already renders Recharts `ComposedChart` with time range controls. Changes:

1. Fetch `/api/v1/scores/{ticker}/history` alongside existing calls
2. Map `points` to chart data arrays (replace synthetic single-element arrays)
3. Y-axis: 0-100 percentile
4. Color bands for BUY/HOLD/SELL zones
5. Tooltip: date, score, delta, signal, conviction

### D2: Price vs Buy Price Chart

New `PriceTargetChart` component in `AssetPanel`, below `ScoreChart`.

**Data sources:**
- Price history: `PriceBar[]` from existing `?include=price_history`
- Target history: `ScoreHistoryPoint[]` from new history endpoint

**Rendering:**
- Stock price: solid blue line (daily)
- Buy Price: dashed green line (stepped, changes on scoring runs)
- Margin Invest Value: dotted gray line (stepped)
- Sell Price: dashed red line (stepped)
- Green shading when `price < buy_price`, red shading when `price > sell_price`

**Alignment:** Price is daily, scores are per-run. Use last-observation-carried-forward for target lines.

### Acceptance Criteria (Section 4)

- `GET /api/v1/scores/{ticker}/history` returns all historical rows ordered by `scored_at`
- Delta computed correctly (null for first point, difference for subsequent)
- `ScoreChart` renders multiple points; time range filters work
- `ScoreHistoryTable` shows real deltas and signal transitions
- `PriceTargetChart` overlays daily price with stepped target lines
- Tooltips show date + exact values on both charts
- When <2 points, charts show "accumulating data" message

---

## Section 5: UX Consolidation

### Unified Valuation Module

Replace fragmented display (ActionPill + PanelValuation + KpiGrid MoS) with one block:

```
┌─────────────────────────────────────────────────┐
│  VALUATION                                      │
│                                                 │
│  Margin Invest Value          $198.00           │
│  Current Price                $185.00           │
│  Margin of Safety               25%            │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │  BUY below    $148.50   ●────────       │    │
│  │  CURRENT      $185.00        ●───       │    │
│  │  FAIR VALUE   $198.00          ●──      │    │
│  │  SELL above   $247.50             ●──   │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  Method Breakdown                               │
│  DCF (35%)              ├████████░░░│ $210      │
│  EV/FCF (25%)           ├██████░░░░░│ $185      │
│  Acquirer's (20%)       ├█████░░░░░░│ $178      │
│  SH Yield (20%)         ├████████░░░│ $205      │
│                                                 │
│  ─ Dispersion: Low (CV 12%) · MoS tightened    │
└─────────────────────────────────────────────────┘
```

### Removals

- Separate "Buy Below" row in `PanelValuation` → replaced by price ladder
- "Buy Below" line on `StockCard` → card keeps ActionPill only
- MoS from `KpiGrid` → replaced by Score Delta (MoS lives in valuation module)

### KPI Grid — Revised Six Cells

| Cell | Before | After |
|---|---|---|
| 1 | Sharpe Ratio | Sharpe Ratio |
| 2 | Max Drawdown | Max Drawdown |
| 3 | Volatility | Volatility |
| 4 | Avg Profit Margin | Avg Profit Margin (bug fixed) |
| 5 | Allocation | Allocation (reliably computed) |
| 6 | Margin of Safety | **Score Delta** |

### ActionPill — Updated Subtext

| Signal | Subtext |
|---|---|
| BUY | "Below $148.50 buy target" |
| HOLD | "$185 — between buy ($148) and sell ($247)" |
| SELL | "Above $247.50 sell target" |
| URGENT_SELL | "+X% over sell target" |

### Component Changes

| Component | Change |
|---|---|
| `PanelValuation` | Rewrite: unified layout with price ladder |
| `KpiGrid` | Swap cell 6: MoS → Score Delta |
| `StockCard` | Remove "Buy Below" standalone line |
| `ActionPill` | Update subtext for dual threshold |
| `ExecutiveHeader` | Real `scoreDelta` from history API |
| All labels | "Intrinsic Value" → "Margin Invest Value" |

### Acceptance Criteria (Section 5)

- No separate "Buy Below" panel exists anywhere
- Valuation module shows MIV, Current Price, MoS, price ladder, method breakdown, dispersion note
- MoS removed from KpiGrid; replaced with Score Delta
- KPI grid: 6 metrics, all reliably populated
- ActionPill subtext reflects dual threshold zones
- Zero "Intrinsic Value" references in user-facing text
- Price ladder positions current price relative to buy/fair/sell markers

---

## Implementation Order (Data-Up)

1. **Engine: Valuation model** — dual threshold MoS, rename to Margin Invest Value
2. **Engine: Filter config** — YAML system, `FilterConfig` Pydantic model
3. **Engine: Filter logic** — tiered liquidity, multi-year health checks, Beneish history
4. **API: Score history endpoint** — `GET /scores/{ticker}/history`
5. **API: Metrics fixes** — key-name bug, allocation formula, MetricStatus schema
6. **API: Valuation rename** — Alembic migration, response schema updates
7. **Frontend: Charts** — ScoreChart with real data, new PriceTargetChart
8. **Frontend: Valuation module** — unified block, price ladder
9. **Frontend: KPI grid** — swap MoS→Delta, render unavailability reasons
10. **Frontend: Cleanup** — remove Buy Below section, rename labels, ActionPill subtext

### Dependencies

- Steps 1-3 are engine-only (no API/frontend deps)
- Step 4 requires no engine changes (uses existing DB schema)
- Steps 5-6 depend on step 1 (renamed fields)
- Steps 7-9 depend on steps 4-6 (API changes)
- Step 10 depends on steps 7-9

### Risks

- **Column rename migration:** `intrinsic_value` → `margin_invest_value` requires careful Alembic migration. Run on staging first.
- **Signal distribution shift:** Dual threshold will produce fewer BUY signals (price must be below discounted value). Existing BUY-signal assets may shift to HOLD. This is correct but visually impactful on the dashboard.
- **Multi-year filter data:** `FinancialHistory` may not be available for all assets in the current ingestion pipeline. Graceful fallback to single-period is required.
- **Score history volume:** If CLI has been run many times, history endpoint could return large payloads. The `limit` parameter (default 100) mitigates this.
