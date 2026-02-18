# Metrics Panel Fix — Design Document

**Date**: 2026-02-17
**Branch**: `feat/fluid-intelligence-redesign`
**Status**: Approved

## Problem

The metrics panel (KPI grid) in the asset detail panel displays "—" for Sharpe Ratio, Max Drawdown, Volatility, and Avg Profit Margin. The "Target" field on stock cards shows "N/A" for most candidates. Users see an empty analytics experience despite seeded financial data.

## Root Cause Analysis

Four distinct issues:

### 1. Next.js Proxy Drops Query Parameters

**File**: `web/src/app/api/v1/scores/[ticker]/route.ts`

The proxy route constructs the backend URL without forwarding the incoming request's query string:

```ts
// Current (broken):
fetch(`${API_URL}/api/v1/scores/${ticker}`)
// Frontend sends: ?include=price_history,signal_history
// Backend receives: nothing
```

The FastAPI endpoint at `GET /api/v1/scores/{ticker}` only fetches `price_history` from `FinancialData` when `?include=price_history` is present. Without it, `price_history` returns as `null`, and `computeInstitutionalMetrics()` returns `null` → all price-derived metrics show "—".

### 2. avgProfitMargin Never Implemented

**File**: `web/src/lib/compute-institutional-metrics.ts:89`

```ts
avgProfitMargin: null,  // hardcoded
```

No calculation exists for average profit margin anywhere in the codebase.

### 3. Price Targets Fail Validation for Most Candidates

**File**: `engine/src/margin_engine/scoring/quantitative/price_targets.py`

The engine's `compute_price_targets()` has a 4-layer validation cascade. When any layer rejects, `sell_price` and other price target fields are `None`, causing "Target: N/A" on stock cards. The `price_target_invalid_reason` column stores the failure reason but it's not surfaced to users.

### 4. Client-Side Computation Architecture

Sharpe, Drawdown, and Volatility are computed in the browser from raw price bars. This works mathematically but:
- Sends ~365 OHLCV bars over the wire per ticker
- Splits calculation logic between TypeScript (frontend) and Python (engine)
- Fails silently when data doesn't arrive

## Solution

Combined Approach A + B: Fix the data pipeline AND add a backend metrics endpoint.

### Phase 1: Fix the Proxy Bug

**File**: `web/src/app/api/v1/scores/[ticker]/route.ts`

Forward the incoming request's query string to the backend:

```ts
const url = new URL(_request.url)
const query = url.search
const response = await fetch(`${API_URL}/api/v1/scores/${ticker}${query}`, { ... })
```

This immediately unblocks Sharpe, Drawdown, Volatility in the KPI grid using the existing client-side computation path while Phase 3 builds the proper backend endpoint.

### Phase 2: Surface Price Target Invalid Reasons

**API changes:**
- Add `price_target_invalid_reason` to `PickSummary` schema in `api/schemas/dashboard.py`
- Populate it in `_pick_summary_from_row()` in `api/routes/dashboard.py`

**Frontend changes** (`web/src/components/dashboard/stock-card.tsx`):
- Map machine reasons to human-readable labels:
  - `"insufficient_data"` → `"Needs data"`
  - `"single_method"` → `"Low confidence"`
  - `"low_agreement"` → `"Methods diverge"`
  - Other/null → `"Unavailable"`
- Display the label instead of "N/A" when `sell_price` is null but reason is available

**Data pipeline investigation:**
- Query `price_target_invalid_reason` distribution to identify most common failure
- Fix data gaps in the seed pipeline if the primary cause is missing financial fields

### Phase 3: Backend Metrics Endpoint

**New endpoint**: `GET /api/v1/scores/{ticker}/metrics`

**Response schema:**

```python
class InstitutionalMetricsResponse(BaseModel):
    sharpe_ratio: float | None        # Annualized, daily returns
    max_drawdown: float | None        # Peak-to-trough as decimal (e.g., -0.25)
    volatility: float | None          # Annualized std dev as percentage
    avg_profit_margin: float | None   # Trailing multi-period net income/revenue %
    risk_classification: str          # Conservative/Moderate/Moderate-High/Aggressive
    allocation_weight: float | None   # From Score.max_position_pct
    margin_of_safety: float | None    # (intrinsic - actual) / intrinsic as decimal
```

**Calculation methodology:**

| Metric | Formula | Data Source | Time Horizon |
|--------|---------|-------------|-------------|
| Sharpe Ratio | `(mean_daily_return - Rf/252) / std(daily_returns) * sqrt(252)` | `FinancialData.price_history` | 1Y trailing (all bars) |
| Max Drawdown | Largest peak-to-trough decline | Same price bars | Same period |
| Volatility | `std(daily_returns) * sqrt(252) * 100` | Same | Same |
| Avg Profit Margin | `mean(net_income / revenue)` per period | `FinancialData.income_statement` | Trailing 4 quarters |
| Risk Classification | Volatility buckets: >40 Aggressive, >25 Moderate-High, >15 Moderate, else Conservative | Derived | N/A |
| Allocation Weight | Direct read | `Score.max_position_pct` | N/A |
| Margin of Safety | `(intrinsic - actual) / intrinsic` | `Score` fields | N/A |

**Constants:**
- Risk-free rate: 5% annualized (stored as `RISK_FREE_RATE = 0.05`)
- Trading days per year: 252
- Minimum bars for statistics: 5

**Error handling:** Return `null` for any metric that can't be computed. Return `200 OK` regardless — the frontend handles nulls.

### Phase 4: Frontend Integration

**New data flow:**
```
StockCard expand
  → getScore(ticker, ["price_history", "signal_history"])  // keep for Sparkline
  → getMetrics(ticker)                                      // new parallel call
  → AssetPanel receives both
  → KpiGrid displays server-computed metrics
```

**New files:**
- `web/src/app/api/v1/scores/[ticker]/metrics/route.ts` — Next.js proxy
- Types added to `web/src/lib/api/types.ts`
- `getMetrics()` function in `web/src/lib/api/scores.ts`

**Modified files:**
- `web/src/components/dashboard/stock-card.tsx` — parallel fetch of score + metrics
- `web/src/components/dashboard/panel/asset-panel.tsx` — accept metrics prop, remove client-side computation
- `web/src/components/dashboard/panel/kpi-grid.tsx` — no changes (already accepts the right props)

**Loading states:** KpiGrid shows skeleton/shimmer while metrics load (may arrive after score response).

**Fallback:** Keep `compute-institutional-metrics.ts` available but remove from the main render path.

### Phase 5: Testing

**Backend tests (pytest):**
- `test_metrics_endpoint_returns_all_fields` — happy path with seeded data
- `test_metrics_endpoint_missing_price_history` — null for price-derived metrics
- `test_metrics_endpoint_missing_income_data` — null for avgProfitMargin
- `test_sharpe_ratio_calculation` — golden-value with known price series
- `test_max_drawdown_calculation` — golden-value with known peak/trough
- `test_avg_profit_margin_calculation` — golden-value with known income data
- `test_metrics_endpoint_unknown_ticker` — 404

**Frontend tests (vitest):**
- `test_kpi_grid_renders_server_metrics` — displays values from API
- `test_kpi_grid_handles_null_metrics` — shows "—" for nulls
- `test_stock_card_fetches_metrics_on_expand` — parallel fetch
- `test_target_shows_invalid_reason` — reason string instead of "N/A"

**Parity test:** Compare Python backend vs TypeScript frontend Sharpe/Drawdown/Volatility for identical input data — must match within 0.01.

## Files Changed Summary

| Phase | Files | Type |
|-------|-------|------|
| 1 | `web/src/app/api/v1/scores/[ticker]/route.ts` | Fix |
| 2 | `api/schemas/dashboard.py`, `api/routes/dashboard.py`, `web stock-card.tsx` | Fix + UI |
| 3 | New: `api/routes/metrics.py`, `api/schemas/metrics.py` | New endpoint |
| 3 | New: `web/src/app/api/v1/scores/[ticker]/metrics/route.ts` | New proxy |
| 4 | `web stock-card.tsx`, `web panel/asset-panel.tsx`, `web/src/lib/api/scores.ts`, `web/src/lib/api/types.ts` | Integration |
| 5 | `api/tests/`, `web/src/**/__tests__/` | Tests |

## Out of Scope

- Backtest metrics (separate feature, existing `PerformanceCalculator` pipeline)
- Real-time/WebSocket metric updates
- Caching or pre-computation at scoring time (Approach C — future optimization)
- Additional metrics beyond the 7 specified (Sortino, Beta, Alpha, etc.)
