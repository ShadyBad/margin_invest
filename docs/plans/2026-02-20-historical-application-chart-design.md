# Historical Application Chart Design

**Date:** 2026-02-20
**Status:** Approved

## Goal

Update the Historical Application chart so the benchmark is explicitly the S&P 500 (SPY total return) and the portfolio series is a reproducible, well-defined portfolio built from Exceptional candidates with a Margin of Safety > 30%.

## Approach

Modify the existing `WalkForwardSimulator` to support a new `CONVICTION_MOS` selection mode alongside the existing `TOP_PERCENTILE` mode. Extend `ScoredStock` to carry `margin_of_safety`. Update chart legend to accept props and add tooltips.

## Architecture & Data Flow

**Unchanged:** `WalkForwardSimulator` loop, rebalance date generation, turnover calculation, transaction costs, metrics calculation, `MonthlySnapshot`/`PerformanceMetrics`/`BacktestResult` models, `PerformanceChart` SVG structure, API endpoints.

**Changes (5 touchpoints):**

| Layer | File | Change |
|-------|------|--------|
| Engine model | `backtesting/simulator.py` | Extend `ScoredStock` with `margin_of_safety: float \| None` |
| Engine selection | `backtesting/simulator.py` | New `_select_by_conviction_mos()` method |
| Engine config | `backtesting/models.py` | Add `SelectionMode` enum, `min_conviction_score`, `min_margin_of_safety` to `BacktestConfig` |
| Engine benchmark | Provider implementation | Ensure SPY prices use `auto_adjust=True` (total return) |
| Web chart | `performance-chart.tsx` | Add `portfolioLabel`/`benchmarkLabel` props, add tooltips |

**Data flow:**

```
BacktestConfig(selection_mode=CONVICTION_MOS, min_mos=0.30)
  -> WalkForwardSimulator.run()
    -> For each rebalance date:
      -> ScoredUniverseProvider.get_scores(date) -> [ScoredStock with MoS]
      -> _select_by_conviction_mos() filters Exceptional + MoS > 30%
      -> If zero eligible: keep prev_holdings (no rebalance, no turnover)
      -> BenchmarkProvider.get_price("SPY", date) -> dividend-adjusted price
    -> MonthlySnapshot[]
  -> PerformanceMetrics
  -> API response -> PerformanceChart
```

## Benchmark Definition

- **Instrument:** SPY (SPDR S&P 500 ETF Trust) — investable, includes real expense ratio drag (0.09%)
- **Return type:** Total return (dividend-adjusted). yfinance `auto_adjust=True` returns adjusted close prices.
- **Frequency:** Monthly, aligned to rebalance dates (first business day of each month)
- **Time window:** 2015-01-01 to today (existing default)
- **Tracking:** `benchmark_value = starting_capital * (adj_close_t / adj_close_0)`
- **Currency/timezone:** USD, US market EOD prices. No conversion needed.

## Portfolio Construction Rules

### Eligibility Filter

A candidate enters the portfolio only if **all three** conditions hold at the point-in-time evaluation:

| Condition | Definition | Source |
|-----------|-----------|--------|
| Exceptional conviction | `composite_raw_score >= 79.0` | `ScoringConfig.exceptional_threshold` |
| MoS > 30% | `margin_of_safety > 0.30` (strictly greater) | `CompositeScore.margin_of_safety` from DCF |
| Data completeness | `margin_of_safety is not None` and `composite_raw_score > 0` | Excludes candidates where DCF couldn't run |

### Rebalancing

- **Cadence:** Monthly (first business day of each month)
- **Selection timing:** Scores and prices as-of the rebalance date (point-in-time)
- **Hold-through rule:** If zero candidates pass the filter, keep the prior portfolio unchanged. `turnover = 0.0`, `transaction_costs = 0.0`.

### Weighting

- **Equal-weight:** `weight = 1.0 / len(selected)`
- **Deterministic sort:** `(-composite_raw_score, -margin_of_safety, ticker)` before assigning weights

### Holding Period

- Hold until next rebalance. No intra-month exits.
- At rebalance, full eligible universe is re-evaluated. Stocks no longer qualifying are sold.

### Transaction Costs

- 10 bps transaction + 5 bps slippage = 15 bps total (unchanged)
- Applied proportionally to turnover: `cost = portfolio_value * turnover * 15 / 10_000`
- Zero-eligible months: `turnover = 0.0`, `cost = 0.0`

### Survivorship / Look-ahead Bias Prevention

- `ScoredUniverseProvider.get_scores(as_of_date)` returns only data available on that date
- Engine re-scores using historical fundamentals from yfinance (quarterly filings with dates)
- Delisted stocks: treat return as 0% for that period, drop from portfolio at next rebalance

## Model Changes

### `ScoredStock` Extension

```python
class ScoredStock(BaseModel):
    ticker: str
    composite_score: float        # composite_raw_score
    price: float
    margin_of_safety: float | None = None  # NEW
```

### `BacktestConfig` Extension

```python
class SelectionMode(StrEnum):
    TOP_PERCENTILE = "top_percentile"
    CONVICTION_MOS = "conviction_mos"

class BacktestConfig(BaseModel):
    # ... existing fields ...
    selection_mode: SelectionMode = SelectionMode.TOP_PERCENTILE
    min_conviction_score: float = 79.0
    min_margin_of_safety: float = 0.30
```

### Selection Pseudocode

```python
def _select_holdings(self, scores, prev_holdings):
    if self._config.selection_mode == SelectionMode.CONVICTION_MOS:
        return self._select_by_conviction_mos(scores, prev_holdings)
    return self._select_by_top_percentile(scores)

def _select_by_conviction_mos(self, scores, prev_holdings):
    eligible = [
        s for s in scores
        if s.composite_score >= self._config.min_conviction_score
        and s.margin_of_safety is not None
        and s.margin_of_safety > self._config.min_margin_of_safety
    ]

    if not eligible:
        return prev_holdings  # hold prior portfolio

    eligible.sort(key=lambda s: (-s.composite_score, -(s.margin_of_safety or 0), s.ticker))

    weight = 1.0 / len(eligible)
    return [
        HoldingRecord(
            ticker=s.ticker, weight=weight,
            entry_price=s.price, composite_score=s.composite_score,
        )
        for s in eligible
    ]
```

## Chart Output

### Display

- Two lines on shared axes, normalized to starting value = 1.0 (cumulative % return)
- Portfolio line: accent color, 2.5px stroke
- Benchmark line: secondary color, 2px stroke

### Legend (via props)

```typescript
interface PerformanceChartProps {
  snapshots: SnapshotData[]
  portfolioLabel?: string   // default "Portfolio"
  benchmarkLabel?: string   // default "Benchmark"
  className?: string
}
```

Default labels for this strategy:
- Portfolio: `"Exceptional Portfolio (MoS > 30%, Equal-Weight, Monthly)"`
- Benchmark: `"S&P 500 (SPY Total Return)"`

### Tooltips

- Column-based hover: invisible `<rect>` per data point spanning full plot height
- React state `hoveredIndex: number | null`
- Floating `<div>` overlay showing:
  - Date (formatted as "Feb 2024")
  - Portfolio cumulative return %
  - Benchmark cumulative return %
  - Excess return % (green if positive, red if negative)
- Flips to left side when hovering points in the right half of the chart

### Empty / Edge States

| Scenario | Behavior |
|----------|----------|
| No eligible candidates entire backtest | Portfolio flat at 0% (cash). Benchmark shows SPY. |
| No eligible candidates some months | Hold prior portfolio. Line reflects held stocks' movement. |
| Zero snapshots | "No chart data available." (existing empty state) |

## Acceptance Criteria

### AC-1: Benchmark Correctness

**Given** `BacktestConfig` with `benchmark_ticker="SPY"`
**When** simulation runs
**Then** benchmark uses dividend-adjusted SPY prices and `benchmark_value = starting_capital * (adj_close_t / adj_close_0)`

Tests: mock SPY prices verify correct benchmark values; two identical runs produce identical benchmark series.

### AC-2: Portfolio Eligibility Logic

**Given** scored universe with various `composite_raw_score` and `margin_of_safety` values
**When** `selection_mode=CONVICTION_MOS`, `min_conviction_score=79.0`, `min_margin_of_safety=0.30`
**Then** only stocks passing all three conditions are selected

Tests:
- `score=82, mos=0.35` -> selected
- `score=82, mos=0.25` -> rejected (MoS too low)
- `score=75, mos=0.40` -> rejected (not Exceptional)
- `score=80, mos=None` -> rejected (MoS unavailable)
- `score=79, mos=0.30` -> rejected (MoS not strictly > 0.30)
- `score=79, mos=0.3001` -> selected
- All fail -> returns `prev_holdings`

### AC-3: Equal Weighting & Determinism

**Given** N eligible candidates
**When** holdings are selected
**Then** each receives `weight = 1/N`, sorted by `(-composite_score, -margin_of_safety, ticker)`

Tests: 4 stocks -> 0.25 each; 1 stock -> 1.0; tied scores sorted by ticker; two runs produce identical output.

### AC-4: Zero-Eligible Hold-Through

**Given** portfolio holding [AAPL, MSFT] from prior rebalance
**When** current rebalance has zero eligible candidates
**Then** holdings unchanged, `turnover=0.0`, `transaction_costs=0.0`

Tests: hold-through across multiple months; resume normal selection when eligible candidates return; first rebalance with zero eligible -> empty holdings (cash).

### AC-5: Point-in-Time Correctness

**Given** stock with changing scores across dates
**When** simulator evaluates each rebalance date
**Then** uses the as-of-date score, not current values

Tests: mock provider returns date-specific scores; assert `get_scores()` called with rebalance date.

### AC-6: Transaction Costs

**Given** portfolio value, turnover, and `total_cost_bps=15`
**When** costs calculated
**Then** `cost = portfolio_value * turnover * 15 / 10_000`

Tests: full turnover, zero turnover, costs deducted before snapshot recording.

### AC-7: Chart Rendering

**Given** completed backtest snapshots
**When** `PerformanceChart` renders
**Then** two polylines visible, legend reflects props, tooltips show cumulative returns

Tests: SVG polylines present; custom labels rendered; tooltip appears on hover; tooltip flips on right-side points; empty state for zero snapshots; default labels when props omitted.

### AC-8: Backward Compatibility

**Given** existing configs with no `selection_mode`
**When** simulation runs
**Then** defaults to `TOP_PERCENTILE`, existing behavior unchanged

Tests: no `selection_mode` -> top percentile; explicit `CONVICTION_MOS` -> new filter.
