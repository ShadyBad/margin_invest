# Transaction Costs in Backtesting — Design Document

**Date**: 2026-02-27
**Status**: Approved
**Approach**: Promote existing non-linear cost model + add transparency layers + academic validation

## Problem

Many systems demonstrating high predictive accuracy omit transaction costs, slippage, and market impact. When included, these significantly diminish actual profitability. Our backtesting engine already deducts costs (flat bps model by default), but users cannot see the cost impact, stress-test the assumptions, or evaluate strategy capacity.

## Current State

The engine has two cost models:

1. **Flat model** (current default): `portfolio_value × turnover × transaction_cost_bps / 10,000`
2. **Non-linear model** (`cost_model.py`): Commission + spread (market-cap dependent) + market impact (square-root scaling)

All metrics (CAGR, Sharpe, Sortino, etc.) are already computed from net-of-cost returns. The non-linear model exists and is tested but requires explicit opt-in. Users see net numbers but have no way to assess cost drag, stress-test assumptions, or evaluate capacity.

## Design

### 1. Cost Model Upgrade

**Make the non-linear model the default** for all backtests. The flat model remains available as a fallback for users who manually set `transaction_cost_bps`.

Non-linear model components (already implemented in `cost_model.py`):

| Component | Formula | Default |
|-----------|---------|---------|
| Commission | Fixed bps | 5 bps round-trip |
| Spread | `3.0 + 50.0 / sqrt(market_cap_billions)` | ~4 bps mega-cap, ~18 bps small-cap |
| Market impact | `coefficient × sqrt(trade_value / ADV) × 10,000` | coefficient = 0.1 |

**Changes required**:
- `WalkForwardSimulator` and `ReplayOrchestrator`: Default to non-linear model when `cost_model_config` is not explicitly set
- Populate `CostModelConfig` defaults from `COST_ASSUMPTIONS` constant
- ADV data: Use volume data from yfinance ingest (`RawFinancialData.volume`); fall back to market-cap proxy if unavailable

### 2. Gross-vs-Net Transparency

Track gross returns alongside net returns to surface cost drag.

**Engine changes**:
- `MonthlySnapshot` gains `gross_return: float` — the return before cost deduction
- Both orchestrators compute gross return before subtracting costs (trivial: they already have pre-cost and post-cost portfolio values)
- `PerformanceCalculator.calculate()` computes parallel gross metrics: `gross_cagr`, `gross_sharpe`, `gross_max_drawdown`

**Schema additions to `PerformanceMetrics`**:
- `gross_cagr: float`
- `gross_sharpe: float`
- `gross_max_drawdown: float`
- `cost_drag_bps: float` — annualized cost as basis points: `(gross_cagr - net_cagr) × 10,000`

**Frontend**:
- `MetricsSummary` shows each key metric with a subtle "(gross: X%)" annotation beneath the net value
- `cost_drag_bps` shown as a standalone metric card

### 3. Sensitivity Analysis

Show how performance degrades when transaction costs are 2x and 3x the baseline.

**Engine**:
- New function `run_sensitivity_analysis(snapshots, gross_returns, costs, multipliers=[1.0, 2.0, 3.0])` in `metrics.py`
- Takes existing snapshot data and scales dollar costs by each multiplier, recomputing net returns
- No need to re-run the full simulation — simple arithmetic on existing data

**Schema**:
```python
class CostSensitivityRow(BaseModel):
    multiplier: float        # 1.0, 2.0, 3.0
    cagr: float
    sharpe: float
    max_drawdown: float
    cost_drag_bps: float

class SensitivityResult(BaseModel):
    rows: list[CostSensitivityRow]
```

**API**: `FullBacktestResponse` gains `sensitivity: SensitivityResult`, computed automatically.

**Frontend**: Inline on backtest page:
- Small line chart (Recharts) showing CAGR and Sharpe degradation across cost multipliers
- Compact table below with precise values:

| | Base (1x) | Conservative (2x) | Stress (3x) |
|---|---|---|---|
| CAGR | 10.4% | 8.9% | 7.4% |
| Sharpe | 0.85 | 0.72 | 0.59 |
| Max DD | -18.2% | -19.1% | -20.0% |
| Cost Drag | 47 bps | 94 bps | 141 bps |

### 4. Capacity Analysis

Answer "at what AUM does this strategy break?"

**Engine**:
- New module `engine/src/margin_engine/backtesting/capacity.py`
- Function `run_capacity_analysis(snapshots, aum_levels=[1e6, 10e6, 50e6, 100e6, 250e6, 500e6, 1e9])`
- For each AUM level, scale `trade_value` proportionally and recompute market impact costs (commission and spread are AUM-independent)
- Uses the same square-root impact model: as AUM grows, `trade_value / ADV` increases, impact cost grows sub-linearly

**ADV handling**: Use actual ADV from yfinance data when available. Fall back to market-cap proxy: `ADV_proxy = market_cap × 0.005` (0.5% daily turnover, conservative).

**Schema**:
```python
class CapacityRow(BaseModel):
    aum: float              # e.g., 1_000_000
    cagr: float
    sharpe: float
    avg_impact_bps: float   # average market impact cost at this AUM

class CapacityResult(BaseModel):
    rows: list[CapacityRow]
    breakeven_aum: float | None  # AUM where Sharpe drops below 0.5
```

**Frontend**: Line chart with:
- X-axis: AUM (log scale, $1M to $1B)
- Y-axis: Sharpe ratio
- Horizontal dashed line at Sharpe = 0.5 ("strategy breaks" threshold)
- `breakeven_aum` displayed as a callout annotation

### 5. Academic Benchmark Validation

Ground cost assumptions in published research.

**Reference data** (static, hardcoded with citations):

| Source | Market Cap Range | Round-Trip Cost Range |
|--------|-----------------|----------------------|
| Frazzini, Israel & Moskowitz (2015) | Large-cap | 10–20 bps |
| Frazzini, Israel & Moskowitz (2015) | Small-cap | 30–60 bps |
| Novy-Marx & Velikov (2016) | By decile | Varies |
| Korajczyk & Sadka (2004) | Momentum strategies | Impact estimates |

**Engine**:
- `ACADEMIC_BENCHMARKS` constant in `cost_model.py` with per-decile cost ranges
- `validate_cost_assumptions(model_cost_bps, market_cap_decile) -> CostValidation`
- Returns whether model costs are within_range, below_benchmark (potentially optimistic), or above_benchmark (conservative)

**Schema**:
```python
class AcademicBenchmark(BaseModel):
    source: str
    cost_range_bps: tuple[float, float]
    asset_class: str

class CostValidation(BaseModel):
    model_cost_bps: float
    benchmark_range_bps: tuple[float, float]
    status: str  # "within_range" | "below_benchmark" | "above_benchmark"
    source: str
```

**Frontend**: Inline annotation below sensitivity table:
> "Our estimated round-trip cost of 12 bps for large-cap equities is within the 10–20 bps range reported by Frazzini, Israel & Moskowitz (2015)."

Flags optimistic or conservative estimates explicitly.

### 6. Cost Disclosure & Documentation

**Code**:
- `COST_ASSUMPTIONS` constant in `cost_model.py` containing all defaults with derivation comments
- Docstrings on every cost function with formula and academic basis

**Frontend** — new `CostDisclosure` component (collapsible panel on backtest page):
1. Commission: 5 bps round-trip
2. Spread: market-cap dependent formula with example values
3. Market impact: square-root model with coefficient
4. What's NOT modeled: short-selling costs, taxes, management fees, opportunity cost
5. Academic grounding: brief citations with validation status

**API**: Update `honesty_disclosure` in `FullBacktestResponse` to reference the non-linear model and specific assumptions.

## Files Affected

### Engine
- `engine/src/margin_engine/backtesting/cost_model.py` — add `COST_ASSUMPTIONS`, `ACADEMIC_BENCHMARKS`, `validate_cost_assumptions()`
- `engine/src/margin_engine/backtesting/models.py` — add `gross_return` to `MonthlySnapshot`
- `engine/src/margin_engine/backtesting/metrics.py` — add gross metrics, `run_sensitivity_analysis()`
- `engine/src/margin_engine/backtesting/capacity.py` — new module for capacity analysis
- `engine/src/margin_engine/backtesting/simulator.py` — default to non-linear model
- `engine/src/margin_engine/backtesting/replay_orchestrator.py` — default to non-linear model, compute gross return

### API
- `api/src/margin_api/schemas/backtest.py` — add gross metrics, sensitivity, capacity to response schemas
- `api/src/margin_api/services/backtest.py` — wire sensitivity and capacity analysis into response builder

### Web
- `web/src/components/backtesting/metrics-summary.tsx` — gross annotations, cost drag card
- `web/src/components/backtesting/cost-sensitivity.tsx` — new: sensitivity table + chart
- `web/src/components/backtesting/capacity-chart.tsx` — new: AUM vs Sharpe chart
- `web/src/components/backtesting/cost-disclosure.tsx` — new: collapsible cost assumptions panel
- Backtest page layout — integrate new sections inline

## What's NOT Modeled (Explicit)

- Short-selling costs / borrow fees
- Taxes (capital gains, wash sale rules)
- Management fees / fund expenses
- Opportunity cost of delayed execution
- Time-of-day effects
- Cross-asset transaction costs (equities only)

## Testing Strategy

- Golden-value tests for non-linear cost model at various market cap tiers
- Sensitivity analysis: verify costs scale linearly with multiplier
- Capacity analysis: verify impact grows sub-linearly with AUM (square-root)
- Academic validation: verify classification logic (within/below/above range)
- Frontend: snapshot tests for new components, integration tests for data flow
