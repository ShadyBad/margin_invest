# Candidate Data Pipeline Design

**Date:** 2026-02-14
**Status:** Approved
**Approach:** Engine-First (Approach A)

## Problem

The candidate view has critical data gaps: no buy/sell/actual prices, no meaningful action states, and historical price data exists in the database but is not exposed through the API or rendered in the frontend. The current signal system is stateless — it recomputes fresh each scoring run with no transition history.

## Solution Overview

Add multi-factor intrinsic value computation to the scoring engine, price-aware signal transitions with an audit trail, and enriched frontend components with price charts and action pills.

## 1. Multi-Factor Intrinsic Value Engine

### New Module: `engine/src/margin_engine/scoring/quantitative/price_targets.py`

Synthesizes all four existing value sub-factors into a consensus intrinsic value estimate per share.

### Valuation Methods

| Method | Source Data | Derives Price Via |
|--------|-----------|-------------------|
| DCF Margin of Safety | Projected FCF, discount rate | Direct intrinsic value from 10-year FCF projection |
| EV/FCF | Enterprise value, free cash flow | `(sector_median_ev_fcf * fcf + cash - debt) / shares_outstanding` |
| Acquirer's Multiple | Enterprise value, EBIT | `(sector_median_ev_ebit * ebit + cash - debt) / shares_outstanding` |
| Shareholder Yield | Dividends, buybacks, market cap | `(dividends + net_buybacks) / sector_median_yield / shares_outstanding` |

### Consensus Calculation

```
intrinsic_value = weighted_average(
    dcf_value        * 0.35,
    ev_fcf_value     * 0.25,
    acq_mult_value   * 0.20,
    shyd_value       * 0.20,
)
```

Only methods with valid data contribute. Weights renormalize when a method returns None (e.g., FCF <= 0 invalidates both DCF and EV/FCF methods).

### Output Fields on CompositeScore

| Field | Type | Derivation |
|-------|------|-----------|
| `intrinsic_value` | `Decimal | None` | Multi-factor consensus value per share |
| `buy_price` | `Decimal | None` | `intrinsic_value * (1 - margin_of_safety)` |
| `sell_price` | `Decimal | None` | `intrinsic_value` (fair value = sell target) |
| `actual_price` | `Decimal | None` | Latest close from price_bars |
| `price_upside` | `float | None` | `(intrinsic_value - actual_price) / actual_price` |
| `valuation_methods` | `dict | None` | Individual method estimates for transparency |

### Margin of Safety by Conviction

| Conviction Level | Margin of Safety | Rationale |
|-----------------|-----------------|-----------|
| Exceptional (99%+) | 15% | Strong multi-factor support reduces required margin |
| High (95-98%) | 20% | High confidence, moderate margin |
| Watchlist (90-94%) | 25% | Standard margin for monitoring |
| None (<90%) | 30% | Higher uncertainty requires wider margin |

### Data Dependency: Shares Outstanding

The engine needs `shares_outstanding` to convert enterprise-level values to per-share prices. Options:
- Add to `AssetProfile` model (preferred)
- Derive from `market_cap / current_price` (fallback)

## 2. Signal Transitions & State Tracking

### New DB Table: `signal_transitions`

```sql
CREATE TABLE signal_transitions (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(id),
    previous_signal VARCHAR NOT NULL,
    new_signal VARCHAR NOT NULL,
    previous_conviction VARCHAR NOT NULL,
    new_conviction VARCHAR NOT NULL,
    actual_price_at_transition NUMERIC,
    intrinsic_value_at_transition NUMERIC,
    composite_percentile FLOAT NOT NULL,
    transitioned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(asset_id, transitioned_at)
);
CREATE INDEX ix_signal_transitions_asset ON signal_transitions(asset_id);
```

### Price-Aware Signal Logic

Replaces the current conviction-only signal computation:

| Condition | Signal |
|-----------|--------|
| `actual_price <= buy_price` AND conviction >= HIGH | **BUY** |
| `buy_price < actual_price <= sell_price` AND conviction >= HIGH | **HOLD** |
| `actual_price > sell_price` AND conviction >= HIGH | **SELL** |
| conviction = WATCHLIST | **WATCH** |
| `actual_price > sell_price * 1.15` | **URGENT_SELL** |
| conviction = NONE | **NO_ACTION** |

### Transition Detection

At scoring time, after computing the new signal, compare to the most recent `signal_transitions` row for that asset. If the signal changed, insert a new transition record with both states, the price, and the intrinsic value at the time of transition.

## 3. API Changes

### Enhanced Score Response

Single endpoint with optional depth via query params:

`GET /api/v1/scores/{ticker}?include=price_history,signal_history`

- No params: base score + price target fields (lightweight)
- `include=price_history`: adds OHLCV bars (up to 365 days)
- `include=signal_history`: adds transition audit trail
- Both: full payload for expanded candidate detail view

New fields on `ScoreResponse` (always included, nullable):

```python
intrinsic_value: float | None = None
buy_price: float | None = None
sell_price: float | None = None
actual_price: float | None = None
price_upside: float | None = None
valuation_methods: dict | None = None

# Conditionally included via ?include=
price_history: list[PriceBarResponse] | None = None
signal_history: list[SignalTransitionResponse] | None = None
```

### Enhanced Dashboard PickSummary

Always includes price summary (no query param needed):

```python
# New fields
actual_price: float | None = None
buy_price: float | None = None
sell_price: float | None = None
price_upside: float | None = None
```

### New Pydantic Schemas

- `PriceBarResponse`: date, open, high, low, close, volume, adj_close
- `SignalTransitionResponse`: previous_signal, new_signal, previous_conviction, new_conviction, actual_price_at_transition, intrinsic_value_at_transition, composite_percentile, transitioned_at

## 4. Frontend Components

### Action Pill (replaces SignalBadge)

Colored pill component showing signal with contextual subtext:

| Signal | Color | Subtext |
|--------|-------|---------|
| BUY | Green | "Buy below $142" |
| HOLD | Blue | "Holding +12.3%" |
| SELL | Orange | "Sell above $195" |
| WATCH | Yellow | "Monitoring" |
| URGENT_SELL | Red | "Overvalued by 18%" |
| NO_ACTION | Gray | "N/A" |

### Stock Card Enhancements

New price row:
```
Actual: $167.42    Target: $195.20    Upside: +16.6%
```

Sparkline: Inline 90-day SVG price trend. Green if below buy target, red if above sell target, neutral otherwise.

### Expanded Detail (AssetDetail) Enhancements

**Interactive Price Chart:**
- Full OHLCV chart using Recharts
- Horizontal reference lines for buy_price and sell_price
- Hover tooltips with OHLCV data
- Time range selector: 1M / 3M / 6M / 1Y

**Valuation Breakdown:**
- Shows each method's implied price
- Visual comparison bar chart
- Highlights consensus weighted average

**Signal Timeline:**
- Vertical timeline of signal transitions
- Each entry: date, old signal -> new signal, price at transition

### Null State Handling

All null/undefined states:
- Styled placeholder text ("N/A" or "Pending") in muted color
- Fixed height containers that never collapse
- Consistent typography matching populated state
- Grid cells maintain dimensions regardless of data presence

## 5. DB Schema Changes Summary

### Modified Tables

**scores** — add columns:
- `intrinsic_value NUMERIC`
- `buy_price NUMERIC`
- `sell_price NUMERIC`
- `actual_price NUMERIC`

### New Tables

- `signal_transitions` (see Section 2)

### Modified Models

**Score (SQLAlchemy):**
- Add `intrinsic_value`, `buy_price`, `sell_price`, `actual_price` columns
- These are nullable (backward compatible)

**CompositeScore (Pydantic, engine):**
- Add `intrinsic_value`, `buy_price`, `sell_price`, `actual_price`, `price_upside`, `valuation_methods` fields

**AssetProfile (Pydantic, engine):**
- Add `shares_outstanding: int | None` field

## 6. TypeScript Type Changes

```typescript
// Enhanced ScoreResponse
interface ScoreResponse {
  // ... existing fields ...
  intrinsic_value: number | null;
  buy_price: number | null;
  sell_price: number | null;
  actual_price: number | null;
  price_upside: number | null;
  valuation_methods: Record<string, number> | null;
  price_history?: PriceBar[] | null;
  signal_history?: SignalTransition[] | null;
}

// Enhanced PickSummary
interface PickSummary {
  // ... existing fields ...
  actual_price: number | null;
  buy_price: number | null;
  sell_price: number | null;
  price_upside: number | null;
}

// New types
interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adj_close: number | null;
}

interface SignalTransition {
  previous_signal: string;
  new_signal: string;
  previous_conviction: string;
  new_conviction: string;
  actual_price_at_transition: number | null;
  intrinsic_value_at_transition: number | null;
  composite_percentile: number;
  transitioned_at: string;
}
```

## Testing Strategy

- **Engine:** Golden-value tests for each valuation method's implied price
- **Engine:** Consensus calculation with various method availability combinations
- **Engine:** Signal transition logic with price/conviction combinations
- **API:** Integration tests for enhanced score responses with/without include params
- **API:** Signal transition persistence and retrieval
- **Frontend:** Component tests for action pill states, null handling, chart rendering
