# Data Correctness & UX Tightening Design

**Date:** 2026-02-18
**Status:** Approved (v2 — supersedes previous version)
**Branch:** feat/data-correctness-ux-tightening

## Goals (Priority Order)

1. **Data correctness**: All calculated values — especially Margin Invest Value and MoS — must be 100% accurate, explainable, and reproducible.
2. **Data completeness**: Fields should not display "–" for most assets unless truly unavailable; implement fallbacks and specific unavailable reasons.
3. **Investor-aligned filtering**: Thresholds must be sensible for institutional-grade investing.
4. **Truthful history**: Anything labeled "history" must be real time-series data, not "last run."
5. **UX clarity**: Remove redundant sections and present information cleanly.

## Key Decisions (from brainstorming)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Allocation metric | **Removed** | Portfolio construction concern, not scoring |
| Delta definition | **Price-to-value gap** | `(MIV - price) / price`, already computed as `price_upside` |
| Liquidity approach | **Full redesign** | Multi-window + position-sizing + divergence check |
| Risk metric windows | **1Y + 3Y** | 1Y primary, 3Y for structural risk |
| Profit margin definition | **TTM Net Margin** | Simple, widely understood, already available |
| Health filter depth | **Multi-year median + trend guard** | Removes one-off spikes, catches deterioration |
| Score history problem | **Operational** (need runs) | Schema is fine, just need `score-universe` CLI + cadence |

---

## Section A: Liquidity Filter Redesign

### Problem

The liquidity filter uses a single precomputed `avg_daily_volume` value with no window specification, no position-sizing model, and no venue awareness. The legacy path applies a flat $1M minimum across all assets.

### Design

Replace the single-value approach with a multi-window liquidity assessment.

#### New Data Model: `LiquidityProfile`

| Field | Type | Description |
|-------|------|-------------|
| `median_dollar_volume_20d` | `Decimal` | Median daily $ volume over 20 trading days |
| `median_dollar_volume_60d` | `Decimal` | Median daily $ volume over 60 trading days |
| `median_dollar_volume_90d` | `Decimal` | Median daily $ volume over 90 trading days (baseline) |
| `listing_venue` | `str` | Exchange (NYSE, NASDAQ, LSE, etc.) |
| `country_code` | `str` | ISO country code |
| `avg_spread_bps` | `float | None` | Average bid-ask spread in basis points (if available) |

#### Position-Sizing Simulation

```
days_to_fill(position_size, participation_rate, median_dollar_volume) =
    position_size / (median_dollar_volume × participation_rate)

market_impact_estimate(participation_rate) =
    0.1 × sqrt(participation_rate)   # simplified Almgren-Chriss
```

Default assumptions (all YAML configurable):

| Parameter | Default | Description |
|-----------|---------|-------------|
| Target position size | $500K | Configurable per portfolio tier |
| Max participation rate | 5% | % of daily volume |
| Max days to fill | 5 | Trading days |
| Max estimated impact | 50 bps | Market impact ceiling |

#### Filter Pass Criteria (ALL must pass)

1. `median_dollar_volume_90d` ≥ market-cap-tiered minimum (existing tiers preserved)
2. `days_to_fill` ≤ 5 days at 5% participation for a $500K position
3. No 20d/90d divergence > 3× (catches sudden liquidity evaporation)
4. Sector eligibility (Financials/RE exclusion preserved)
5. Min trading history ≥ 5 years (preserved)

#### Filter Output

Includes all computed metrics, pass/fail per criterion, human-readable reason string, and the full `LiquidityProfile` for auditability.

#### YAML Configuration

```yaml
liquidity:
  excluded_sectors: ["Financials", "Real Estate"]
  min_years_of_history: 5
  market_cap_minimum:
    default: 300_000_000
    utilities: 1_000_000_000
    energy: 500_000_000
  dollar_volume_tiers:
    mega: 50_000_000
    large: 20_000_000
    mid: 5_000_000
    small: 2_000_000
  windows: [20, 60, 90]
  divergence_max_ratio: 3.0
  position_sizing:
    target_position: 500_000
    max_participation_rate: 0.05
    max_days_to_fill: 5
    max_impact_bps: 50
```

### Acceptance Criteria

- No single universal threshold applied to all assets
- Multi-window median dollar volume (20d/60d/90d) computed from price bars
- Position-sizing simulation answers "can I build a $500K position in 5 days?"
- Liquidity divergence check (20d vs 90d) catches evaporation
- Filter output includes all computed metrics and pass/fail reasons
- All parameters YAML configurable
- Unit tests: tiered thresholds, position sizing, divergence detection, venue/region

---

## Section B: Financial Health Filters — Multi-Year Median + Trend Guard

### Problem

FCF Distress, Interest Coverage, and Current Ratio all use single-period checks. A single bad year eliminates otherwise healthy companies; a single good year masks deterioration.

### Design

Shared pattern across all three filters:

1. **Primary metric**: 3-year median (removes one-off spikes)
2. **Trend guard**: Flag if metric deteriorated >20% from 3-year-ago value to current, even if still above threshold
3. **Sector-normalized thresholds**: Expanded sector overrides
4. **All configurable via YAML**

#### FCF Distress (currently single-period FCF ≥ 0)

| Rule | Description |
|------|-------------|
| Primary | 3 of last 5 years must have positive FCF |
| FCF margin floor | Median FCF margin (FCF/Revenue) over 5 years > -5% |
| Positive trend rescue | If FCF negative but improving YoY for 2+ consecutive years → WARNING (passes with flag) |
| Cyclical adjustment | Energy/Materials get 2-of-5 instead of 3-of-5 |

Activates existing but unwired config fields: `positive_years_required`, `lookback_years`, `min_fcf_margin`, `allow_positive_trend_rescue`.

#### Interest Coverage (currently single-period EBIT/Interest)

| Rule | Description |
|------|-------------|
| Primary | 3-year median ICR must exceed sector threshold |
| Trend guard | Current ICR can't be >20% below 3-year median |
| Negative EBIT | Automatic FAIL (no ratio computation) |

Expanded sector thresholds (applied to 3-year median):

| Sector | Median ICR Threshold | Rationale |
|--------|---------------------|-----------|
| Information Technology | > 5.0 | Should be nearly debt-free |
| Health Care | > 3.0 | R&D-heavy but funded |
| Consumer Staples | > 3.0 | Stable cash flows |
| Utilities | > 1.5 | Regulated, capital-intensive |
| Energy | > 2.0 | Cyclical, needs buffer |
| Industrials | > 2.5 | Moderate leverage OK |
| Default | > 2.5 | Up from 1.5 |

#### Current Ratio (currently single-period CA/CL)

| Rule | Description |
|------|-------------|
| Primary | 3-year median CR must exceed sector threshold |
| Trend guard | CR can't have declined >30% over 3 years |
| Quick ratio rescue | If CR fails but quick ratio (CA - Inventory)/CL > 0.5 → passes with flag |

Threshold values stay largely the same but applied to median, not spot value.

#### FilterResult Enhancement

New fields added to `FilterResult`:

```python
warning: bool = False
warning_reason: str | None = None
computed_metrics: dict[str, float] | None = None
```

#### YAML Configuration

```yaml
fcf_distress:
  positive_years_required: 3
  lookback_years: 5
  min_fcf_margin: -0.05
  allow_positive_trend_rescue: true
  cyclical_positive_years: 2  # Energy/Materials relaxed threshold

interest_coverage:
  default: 2.5
  sector_overrides:
    information_technology: 5.0
    health_care: 3.0
    consumer_staples: 3.0
    utilities: 1.5
    energy: 2.0
    industrials: 2.5
  median_lookback_years: 3
  trend_guard_decline_pct: 20

current_ratio:
  default: 0.8
  sector_overrides:
    information_technology: 0.8
    utilities: 0.6
  quick_ratio_rescue: 0.5
  max_3yr_decline_pct: 30
```

### Acceptance Criteria

- Each filter uses 3-year median as primary metric
- Trend guard catches deterioration even when above threshold
- Negative EBIT produces automatic FAIL for interest coverage
- Quick ratio rescue works for current ratio
- All thresholds configurable via YAML without code changes
- Golden test cases: normal pass, trend guard trigger, negative EBIT, quick ratio rescue, cyclical FCF

---

## Section C: Beneish M-Score — Historical Backfill + INCONCLUSIVE Verdict

### Problem

Beneish requires current + prior period data. When prior data is missing, it silently returns PASS with `insufficient_data=True`, letting potentially manipulative companies through undetected.

### Design

#### Multi-Period Computation

Change Beneish to accept `FinancialHistory` instead of single `FinancialPeriod`:
- Compute M-Score for every consecutive pair of periods
- Store per-period M-Scores for charting and audit
- Use most recent M-Score for pass/fail
- Flag trend (worsening M-Score over time)

#### New Return Model

```python
class BeneishResult(BaseModel):
    current_m_score: float | None
    historical_m_scores: list[dict]   # [{period_end, m_score, components}]
    passed: bool
    insufficient_periods: int
    missing_inputs: list[str]
    trend: str | None                 # "improving" | "deteriorating" | "stable"
```

#### New Verdict: INCONCLUSIVE

Add `FilterVerdict.INCONCLUSIVE` to the enum. Applies to ALL filters:

| Condition | Verdict |
|-----------|---------|
| 0 periods computable | INCONCLUSIVE — "Cannot assess — insufficient financial history" |
| 1+ periods computed | Use latest valid M-Score for PASS/FAIL |

#### UI Treatment

| Verdict | Badge Color | Behavior |
|---------|-------------|----------|
| PASS | Green | Normal |
| FAIL | Red | Normal |
| INCONCLUSIVE | Amber/Yellow | Shows missing fields list and periods available |

Historical M-Scores shown as mini sparkline in filter detail expansion.

### Acceptance Criteria

- Beneish computes M-Score for every consecutive period pair in history
- Per-period M-Scores stored in filter result for auditability
- Missing data produces INCONCLUSIVE, not silent PASS
- UI distinguishes PASS / FAIL / INCONCLUSIVE with different visual treatment
- Trend detection flags worsening M-Score trajectory
- Golden tests: multi-period, single-period fallback, zero-period INCONCLUSIVE

---

## Section D: Missing Metrics — Risk Metrics + Profit Margin + Delta

### Problem

KPI grid shows "–" for Sharpe, Max Drawdown, Volatility, Avg Profit Margin, and Delta because backend computation isn't implemented or isn't wired.

### Design

#### New Engine Module: `risk_metrics.py`

All risk metrics computed from `PriceBar[]` (daily OHLCV).

##### Sharpe Ratio (1Y + 3Y)

```
daily_returns = [close[t] / close[t-1] - 1]
annualized_return = mean(daily_returns) × 252
annualized_vol = std(daily_returns) × sqrt(252)
sharpe = (annualized_return - risk_free_rate) / annualized_vol
```

- Risk-free rate: Hardcoded 3-month T-bill (e.g., 4.3%) with config override
- 1Y: 252 trading days required
- 3Y: 756 trading days required
- Price return only (dividends excluded)

##### Max Drawdown (1Y + 3Y)

```
running_max = cumulative_max(close_prices)
drawdowns = (close_prices - running_max) / running_max
max_drawdown = min(drawdowns)
```

Returns as negative percentage (e.g., -12.5%).

##### Volatility (1Y + 3Y)

```
annualized_vol = std(daily_returns) × sqrt(252)
```

Returns as percentage (e.g., 18.3%).

##### Avg Profit Margin (TTM Net Margin)

```
net_margin = net_income / revenue
```

Source: `FinancialPeriod.current_income.net_margin` (already exists as computed property).

##### Delta (Price-to-Value)

```
delta = (margin_invest_value - actual_price) / actual_price
```

Already computed as `price_upside` on `CompositeScore`. Wired to KPI grid, renamed "Delta" in UI. Positive = undervalued, negative = overvalued.

#### KPI Grid Layout (2×3 → 2×2 + 1 wide)

| Cell 1 | Cell 2 |
|--------|--------|
| Sharpe (1Y) | Max Drawdown (1Y) |
| Volatility (1Y) | Avg Profit Margin |
| **Delta** (full width, prominent) | |

- **Removed**: Allocation Weight
- 1Y as primary display, 3Y available on hover or as secondary label

#### Unavailable Reasons

| Metric | Condition | Reason String |
|--------|-----------|---------------|
| Sharpe 1Y | < 252 bars | "Insufficient price history: need 252 trading days, have {N}" |
| Sharpe 3Y | < 756 bars | "Insufficient price history: need 756 trading days, have {N}" |
| Max Drawdown | < 20 bars | "Insufficient price history: need 20+ trading days" |
| Volatility | < 20 bars | "Insufficient price history: need 20+ trading days" |
| Net Margin | No income data | "No income statement data available" |
| Net Margin | Revenue = 0 | "Revenue is zero — cannot compute margin" |
| Delta | No MIV/price | "Valuation not available" or "No current price" |

#### Configuration

```yaml
risk_metrics:
  risk_free_rate: 0.043  # 3-month T-bill
  windows: [252, 756]    # 1Y, 3Y in trading days
  min_bars_sharpe: 252
  min_bars_drawdown: 20
  min_bars_volatility: 20
```

### Acceptance Criteria

- Sharpe, Max Drawdown, Volatility computed for 1Y and 3Y windows
- KPI grid shows 1Y primary, 3Y as secondary
- Majority of liquid equities with 1+ year price history display all risk metrics
- TTM Net Margin sourced from existing income statement data
- Delta wired from existing `price_upside` field
- Allocation removed from KPI grid
- Unavailable metrics show specific reason, not just "–"
- Deterministic: same price bars produce same metrics

---

## Section E: Score History Accumulation + Scheduled Runs

### Problem

DB schema, API endpoint, and frontend charts all support time-series score history. The pipeline has only been run once per ticker, producing a single data point.

### Design

#### `score-universe` CLI Command

```bash
uv run python -m margin_api.cli score-universe
```

Wraps existing `score_tickers` logic:
- Queries all assets from DB (or configured watchlist)
- Runs filters + scoring for full universe
- Creates new `Score` rows with current `scored_at` timestamp
- Logs summary: N scored, N filtered out, N failed

#### Recommended Cadence

- **Weekly** (Sunday evening): Full universe re-score
- **Daily** (future, optional): Price-sensitive metrics only (actual_price, price_upside, signal)

Weekly is sufficient for launch. User runs manually or via cron/launchd.

#### Frontend Behavior

- ScoreChart uses step-after interpolation between scoring dates (already implemented)
- Single-point state: "Score tracking begins after the next scoring run. Scores are computed weekly."
- No historical backfill feasible — scores depend on full universe ranking at a point in time

### Acceptance Criteria

- `score-universe` CLI command scores all eligible assets in one batch
- Each run produces new Score rows (no overwriting)
- After 2+ runs, score chart renders a time-series line
- Single-point state shows explanatory message

---

## Section F: Valuation Correctness + UX Consolidation

### Problem

1. "Intrinsic Value" naming persists in some places despite partial rename
2. Valuation breakdown shows method bars but not inputs/formulas/intermediates
3. Need to verify no leftover "Buy Below" section exists

### Design

#### 1. Complete Rename

All references to "intrinsic_value" / "Intrinsic Value" → `margin_invest_value` / "Margin Invest Value" across engine, API, and web. Engine model field `CompositeScore.intrinsic_value` → `margin_invest_value`.

#### 2. ValuationAudit Model

```python
class MethodAudit(BaseModel):
    method: str                         # "dcf", "ev_fcf", etc.
    result_per_share: float | None
    weight: float                       # Original weight
    renormalized_weight: float | None   # After outlier removal
    included: bool
    exclusion_reason: str | None
    inputs: dict[str, float]            # Method-specific inputs
    intermediates: dict[str, float]     # Method-specific intermediate values

class ValuationAudit(BaseModel):
    margin_invest_value: float
    margin_of_safety: float
    buy_price: float
    sell_price: float
    actual_price: float | None
    methods: list[MethodAudit]
    mos_base: float
    mos_cv: float | None
    mos_adjustment: float
    was_clamped: bool
    clamp_reason: str | None
```

Stored in `score_detail` JSONB — no migration needed.

#### 3. API Endpoint

```
GET /api/v1/scores/{ticker}/valuation-audit
```

Returns `ValuationAudit` for the latest score.

#### 4. UI: Expandable Valuation Detail

Clicking a method bar in `PanelValuation` expands to show:
- Key inputs (FCF, EBIT, shares, rates)
- Intermediate values (PV stage 1, terminal value, etc.)
- Result per share
- Inclusion/exclusion status and reason

Default view stays clean; full audit available on demand.

#### 5. Buy Below Consolidation

Verify and remove any remaining standalone "Buy Below" section. Price Ladder in `PanelValuation` already shows Buy / Fair / Sell / Current in one visual.

#### 6. Golden Test Cases

| Case | Description |
|------|-------------|
| Normal | All 4 methods valid, known inputs → exact MIV, MoS, Buy/Sell |
| Negative FCF | DCF + EV/FCF return None → renormalized 2-method weights |
| High leverage | Acquirer's implied equity ≤ 0 → excluded |
| Cyclical | Higher base MoS (0.35) + high CV → MoS near ceiling |
| Outlier removal | One method 15× median → excluded, weights renormalized |
| Currency mismatch | Revenue/share > 10× price → validation flag |

### Acceptance Criteria

- Zero remaining references to "Intrinsic Value" in user-facing UI or API responses
- `ValuationAudit` captures all inputs, intermediates, weights, and exclusion reasons
- Audit stored in `score_detail` JSONB — no migration needed
- Frontend can expand each valuation method to see full computation trail
- No separate "Buy Below" section — integrated into PanelValuation
- 6+ golden test cases covering normal, edge, and error paths
- Deterministic: identical inputs produce identical outputs

---

## Section G: Detail Page Charts

### Problem

ScoreChart and PriceTargetChart already exist but show flat/single-point data because only one scoring run has been executed. Both are solved by Section E (score accumulation).

### Design

No new chart components needed. Small enhancements only:

#### Empty State Improvements

| Chart | < 2 Points | Behavior |
|-------|------------|----------|
| ScoreChart | Single score centered | "Score tracking begins after the next scoring run. Scores are computed weekly." |
| PriceTargetChart | Price line only | "Buy/Sell targets will appear after 2+ scoring runs." |

#### Tooltip Enrichment

**ScoreChart tooltip:**
- Date, Composite score, Delta, Conviction level, Q/V/M sub-scores

**PriceTargetChart tooltip:**
- Date, Current price, Buy/MIV/Sell prices, Zone label

#### Missing-Series Behavior

| Condition | Behavior |
|-----------|----------|
| Price history, no score history | PriceTargetChart shows price line only, "(No valuation data)" label |
| Score history, no price history | "Price data unavailable" message |

### Acceptance Criteria

- Both charts render correctly with 1 data point (graceful degradation)
- Both charts render full time-series with 2+ scoring runs
- Tooltips show date + all relevant values
- Missing-series states are explicit with user-facing explanation

---

## Dependencies Between Sections

```
E (Score Accumulation) ← G (Charts need data)
                       ← D (Delta needs score history for context)
F (Valuation)          ← independent
A (Liquidity)          ← independent
B (Health Filters)     ← independent
C (Beneish)            ← independent (but shares INCONCLUSIVE verdict with B)
D (Risk Metrics)       ← independent (uses existing price bars)
```

## Implementation Order

Recommended: **A → B → C → D → F → E → G**

1. **A: Liquidity filter redesign** — new `LiquidityProfile`, multi-window, position-sizing
2. **B: Health filter upgrade** — multi-year median + trend guard for FCF/ICR/CR
3. **C: Beneish historical + INCONCLUSIVE** — multi-period M-Score, new verdict enum
4. **D: Risk metrics + KPI grid** — Sharpe/Drawdown/Vol computation, remove Allocation, wire Delta
5. **F: Valuation audit + rename** — complete rename, `ValuationAudit` model, golden tests, Buy Below removal
6. **E: Score accumulation** — `score-universe` CLI command
7. **G: Chart enhancements** — empty states, tooltip enrichment

### Risks

- **Column rename migration:** `intrinsic_value` → `margin_invest_value` requires careful Alembic migration if column exists. Current codebase may already use `margin_invest_value` column name — verify before migrating.
- **Signal distribution shift:** If buy_price formula changes, existing BUY signals may shift to HOLD. This is correct but visually impactful on the dashboard.
- **Multi-year filter data:** `FinancialHistory` may not be available for all assets. Graceful fallback to single-period behavior required.
- **Price bar volume:** Risk metrics need 252-756 daily bars. Ensure the price ingestion pipeline fetches sufficient history.
