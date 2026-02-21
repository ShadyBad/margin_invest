# Historical Application Chart v2 — Precedence-Fill Portfolio

**Date**: 2026-02-20
**Status**: Approved
**Scope**: Engine selection logic, API schema, web tooltip/legend updates
**Builds on**: `2026-02-20-historical-application-chart-design.md` (v1, merged in PR #5)

## Problem Statement

The v1 Historical Application chart selects only Exceptional candidates (score >= 79) with MoS > 30%. This is too restrictive — few candidates qualify, leading to frequent hold-through periods and an under-diversified portfolio. The chart should use a precedence-based fill to 5 holdings, incorporating High-conviction candidates as backfill.

## Decisions Locked

| Decision | Answer | Rationale |
|----------|--------|-----------|
| Benchmark | SPY total return (dividend-adjusted) | No change from v1; includes dividends, apples-to-apples |
| Selection rule | Precedence fill to 5: Exceptional first, backfill with High | More holdings, better diversification, still conviction-driven |
| MoS threshold | > 20% (strict inequality) | Loosened from 30%; admits more candidates while maintaining meaningful margin |
| Rebalance cadence | Monthly (first business day) | No change from v1; aligns with earnings cycles |
| Approach | Extend existing CONVICTION_MOS mode | Smallest diff, v1 not in production yet, no backward-compat concern |

---

## 1. Portfolio Construction Logic

### 1.1 Eligibility (Point-in-Time)

At each rebalance date `t`, a candidate is eligible if all three conditions hold:
1. Has a valid `composite_raw_score` as-of `t`
2. Has a non-null `margin_of_safety` as-of `t`
3. `margin_of_safety > 0.20` (strictly greater — 0.20 exactly is excluded)

### 1.2 Selection (Precedence Fill to 5)

```python
eligible_exceptional = [
    s for s in scored
    if s.composite_score >= 79.0 and s.margin_of_safety is not None
    and s.margin_of_safety > 0.20
]
eligible_high = [
    s for s in scored
    if 72.0 <= s.composite_score < 79.0 and s.margin_of_safety is not None
    and s.margin_of_safety > 0.20
]

# Deterministic sort: highest score first, then highest MoS, then ticker alphabetical
eligible_exceptional.sort(key=lambda s: (-s.composite_score, -(s.margin_of_safety or 0), s.ticker))
eligible_high.sort(key=lambda s: (-s.composite_score, -(s.margin_of_safety or 0), s.ticker))

# Precedence fill
selected = eligible_exceptional[:max_holdings]
if len(selected) < max_holdings:
    remaining = max_holdings - len(selected)
    selected += eligible_high[:remaining]

# Hold-through: if zero eligible across both tiers, keep previous holdings
if not selected:
    return prev_holdings  # turnover = 0.0, cost = 0.0
```

### 1.3 Weighting

Equal-weight: `1.0 / len(selected)` at each rebalance. If 3 stocks qualify, each gets 33.3%.

### 1.4 Hold-Through Behavior

When zero candidates pass eligibility across both tiers:
- Carry forward all holdings from previous month unchanged
- Turnover = 0.0, transaction costs = 0.0
- Chart line continues (no gap)

### 1.5 Config Changes

```python
# BacktestConfig — modified fields
max_holdings: int = 5                      # NEW: cap on portfolio size
min_conviction_score: float = 79.0         # Exceptional threshold (tier 1, unchanged)
min_conviction_score_high: float = 72.0    # NEW: High threshold (tier 2 backfill)
min_margin_of_safety: float = 0.20         # CHANGED: from 0.30 to 0.20
```

---

## 2. Benchmark

No changes from v1:
- **Instrument**: SPY (SPDR S&P 500 ETF Trust)
- **Return type**: Total return (dividend-adjusted via `yfinance auto_adjust=True`)
- **Frequency**: Monthly, aligned to rebalance dates
- **Calculation**: `benchmark_value_t = starting_capital × (adj_close_t / adj_close_0)`
- **Default window**: 2015-01-01 to today
- **Missing data**: Use last available adjusted close

---

## 3. Chart Behavior

### 3.1 Display
- Two series: Portfolio (accent, 2.5px stroke) vs S&P 500 (secondary, 2px stroke)
- Both normalized to 100 at start of selected period
- No change from v1

### 3.2 Tooltip (Enhanced)

Add holding count and MoS threshold to existing tooltip:

```
Feb 2024
Portfolio:  +42.3%
Benchmark:  +28.1%
Excess:     +14.2%
Holdings:   4 of 5
MoS:        > 20%
```

### 3.3 Legend

Update labels to describe construction rule:
- Portfolio: `"Portfolio: Up to 5 holdings, Exceptional then High, MoS > 20%, Equal-Weight, Monthly"`
- Benchmark: `"S&P 500 (SPY Total Return)"`

### 3.4 Empty/Error States
- **No eligible candidates at rebalance**: Hold-through (chart line continues)
- **API failure**: Inline error message with retry button (existing pattern)
- **Zero snapshots**: "No chart data available" (existing empty state)

---

## 4. Changes from v1

| Aspect | v1 | v2 |
|--------|----|----|
| Selection | All Exceptional with MoS > 30% | Precedence fill to 5: Exceptional first, backfill with High |
| Max holdings | Unlimited | 5 |
| MoS threshold | > 30% | > 20% |
| High candidates | Excluded | Included as tier 2 backfill |
| Tooltip | Date, portfolio %, benchmark %, excess % | + holding count, MoS threshold |
| Legend | Generic labels | Describes construction rule |

---

## 5. Acceptance Criteria

### AC-1: Exceptional Precedence
- **Given**: 4 Exceptional (MoS > 20%) and 3 High (MoS > 20%) at rebalance
- **When**: Portfolio is constructed
- **Then**: All 4 Exceptional selected, top 1 High backfills to 5 total

### AC-2: Max Holdings Cap
- **Given**: 7 Exceptional candidates all with MoS > 20%
- **When**: Portfolio is constructed
- **Then**: Top 5 by (score, MoS, ticker) selected; remaining 2 excluded

### AC-3: High-Only Portfolio
- **Given**: 0 Exceptional and 6 High with MoS > 20%
- **When**: Portfolio is constructed
- **Then**: Top 5 High selected

### AC-4: MoS Filter at 20%
- **Given**: Exceptional candidate with MoS = 0.20 exactly
- **When**: Eligibility is checked
- **Then**: Candidate is excluded (strictly greater required)

### AC-5: Hold-Through
- **Given**: Zero eligible candidates across both tiers at rebalance month M
- **When**: Portfolio is constructed for month M
- **Then**: Holdings from month M-1 carry forward, turnover = 0.0, cost = 0.0

### AC-6: Equal Weighting
- **Given**: 3 candidates selected (2 Exceptional + 1 High)
- **When**: Weights are assigned
- **Then**: Each holding gets 1/3 weight

### AC-7: Benchmark Accuracy
- **Given**: SPY adjusted close on a known date
- **When**: Benchmark value is calculated
- **Then**: Matches yfinance SPY data within 0.01%

### AC-8: Chart Tooltip
- **Given**: User hovers over a data point
- **When**: Tooltip renders
- **Then**: Shows date, portfolio %, benchmark %, excess %, holding count (e.g., "4 of 5"), MoS threshold ("> 20%")

### AC-9: Reproducibility
- **Given**: Same config + date range
- **When**: Backtest runs twice
- **Then**: All snapshot values are bit-for-bit identical

### AC-10: Backward Compatibility
- **Given**: `SelectionMode.TOP_PERCENTILE` config
- **When**: Backtest runs
- **Then**: Behavior is identical to before this change

---

## 6. Files Affected

| Layer | File | Change |
|-------|------|--------|
| Engine | `engine/src/margin_engine/backtesting/models.py` | Add `max_holdings`, `min_conviction_score_high` fields; change MoS default |
| Engine | `engine/src/margin_engine/backtesting/simulator.py` | Rewrite `_select_by_conviction_mos()` with precedence-fill logic |
| API | `api/src/margin_api/schemas/backtest.py` | Expose new config fields |
| Web | `web/src/components/backtesting/performance-chart.tsx` | Add holding count + MoS to tooltip |
| Web | `web/src/app/backtesting/page.tsx` | Update legend labels |
| Tests | `engine/tests/backtesting/test_simulator.py` | Add 9+ new test cases |
| Tests | `web/src/components/backtesting/__tests__/performance-chart.test.tsx` | Test new tooltip fields |
