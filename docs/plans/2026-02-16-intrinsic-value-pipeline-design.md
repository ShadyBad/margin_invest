# Intrinsic Value Pipeline Overhaul — Design Document

**Date**: 2026-02-16
**Status**: Approved
**Goal**: Achieve >75% intrinsic value coverage across the full ~8,000-ticker universe with accurate, sector-appropriate, currency-aware valuation.

## Problem Statement

The current intrinsic value pipeline has three critical gaps:

1. **Low coverage (44.7%)**: 4,252 of 7,692 scored assets lack price targets. Root causes:
   - 2,689 unprofitable companies (negative FCF + EBIT) — all 4 methods require positive cash flows
   - 623 currency-mismatched foreign OTC stocks (financials in JPY/KRW/IDR, price in USD)
   - 276 assets with empty financial JSONB from yfinance
   - 259 assets with extreme intrinsic values (Layer 4 rejection)
   - 245 assets with unreasonable implied market caps

2. **Inaccurate multiples**: Fixed 15x EV/FCF, 12x EV/EBIT, 4% yield targets produce unrealistic valuations. Energy stocks at 15x EV/FCF appear massively undervalued; Tech stocks at 15x appear overvalued.

3. **Data bugs**:
   - `BalanceSheet.total_debt` adds ALL current liabilities instead of financial debt only
   - `shares_outstanding=0` not flagged in some paths
   - Currency mismatch heuristic (10x revenue/share) misses subtle cases like CAD/USD

## Architecture

Four parallel workstreams, each independent at the code level:

1. **Currency conversion service** — store currency metadata, fetch exchange rates, convert financials to USD
2. **Sector-specific multiples** — replace fixed targets with Damodaran-sourced sector defaults
3. **Fallback valuation methods** — P/B and Revenue Multiple for unprofitable companies
4. **Bug fixes and guardrails** — total_debt, empty JSONB detection, growth rate caps

## Detailed Design

### 1. Currency Handling

**New fields on `AssetProfile`:**
```python
financial_currency: str | None = None   # e.g., "JPY", "CAD" — from yfinance info["financialCurrency"]
trading_currency: str = "USD"           # e.g., "USD" — from yfinance info["currency"]
```

**New DB columns on `assets` table:**
```sql
financial_currency VARCHAR(10) NULL
trading_currency VARCHAR(10) DEFAULT 'USD'
```

**Ingestion changes** (normalizer):
- Extract `info["financialCurrency"]` and `info["currency"]` from yfinance Ticker
- Store on AssetProfile and persist to DB

**Exchange rate service** (`engine/src/margin_engine/services/exchange_rates.py`):
- `ExchangeRateService` class
- `fetch_rates(currencies: set[str]) -> dict[str, float]` — batch-fetches rates from yfinance using `{FROM}USD=X` tickers
- Returns dict mapping currency code to USD conversion factor (e.g., `{"JPY": 0.0065, "CAD": 0.74}`)
- 24-hour cache (rates don't need to be real-time for scoring)
- Fallback: if fetch fails for a currency, return None and flag the asset as `currency_rate_unavailable`

**Conversion in `compute_price_targets`:**
- New parameter: `currency_rate: float | None = None`
- If `financial_currency != trading_currency` and rate is provided:
  - Multiply all financial inputs by the rate before computing methods
  - Store `currency_conversion_rate` on PriceTargets for audit
- If rate is not provided and currencies differ: set `invalid_reason="currency_rate_unavailable"`
- Remove `_detect_currency_mismatch` heuristic entirely

### 2. Sector-Specific Target Multiples

**New constant in `price_targets.py`:**

```python
SECTOR_MULTIPLES: dict[GICSSector, dict[str, float]] = {
    GICSSector.ENERGY:                    {"ev_fcf": 8.0,  "ev_ebit": 10.0, "sh_yield": 0.060},
    GICSSector.MATERIALS:                 {"ev_fcf": 12.0, "ev_ebit": 16.0, "sh_yield": 0.040},
    GICSSector.INDUSTRIALS:               {"ev_fcf": 18.0, "ev_ebit": 20.0, "sh_yield": 0.030},
    GICSSector.CONSUMER_DISCRETIONARY:    {"ev_fcf": 16.0, "ev_ebit": 18.0, "sh_yield": 0.030},
    GICSSector.CONSUMER_STAPLES:          {"ev_fcf": 14.0, "ev_ebit": 14.0, "sh_yield": 0.040},
    GICSSector.HEALTHCARE:                {"ev_fcf": 20.0, "ev_ebit": 22.0, "sh_yield": 0.025},
    GICSSector.TECHNOLOGY:                {"ev_fcf": 25.0, "ev_ebit": 28.0, "sh_yield": 0.020},
    GICSSector.COMMUNICATION_SERVICES:    {"ev_fcf": 10.0, "ev_ebit": 12.0, "sh_yield": 0.035},
    GICSSector.UTILITIES:                 {"ev_fcf": 14.0, "ev_ebit": 20.0, "sh_yield": 0.045},
}
FALLBACK_MULTIPLES = {"ev_fcf": 15.0, "ev_ebit": 15.0, "sh_yield": 0.040}
```

Source: Damodaran (NYU Stern) January 2026 EV/EBITDA and EV/EBIT data, with EV/FCF derived from capex intensity ratios.

**Changes to valuation methods:**
- `compute_price_targets` receives `sector: GICSSector` (already available via `profile.sector`)
- Each method looks up its target multiple from the dict
- DCF is unchanged (uses growth/discount/terminal rates, not multiples)

### 3. Fallback Valuation Methods

Only activate when ALL 4 primary methods return None.

**Price-to-Book (P/B) method:**
```python
def _price_to_book_implied_per_share(
    period: FinancialPeriod,
    shares: int,
    sector: GICSSector,
    actual_price: float | None = None,
) -> float | None:
    book_value = period.current_balance.total_equity
    if book_value <= 0:
        return None
    target_pb = SECTOR_PB_MULTIPLES.get(sector, 2.0)
    result = target_pb * float(book_value) / shares
    # Subject to Layer 2 bounds
    ...
```

Sector P/B targets: Tech=5x, Healthcare=4x, Industrials=2.5x, Consumer Disc=3x, Consumer Staples=3x, Energy=1.2x, Materials=1.5x, Comm Services=2x, Utilities=1.5x. Fallback=2.0x.

**Revenue Multiple method:**
```python
def _revenue_multiple_implied_per_share(
    period: FinancialPeriod,
    shares: int,
    sector: GICSSector,
    actual_price: float | None = None,
) -> float | None:
    revenue = period.current_income.revenue
    if revenue <= 0:
        return None
    target_ps = SECTOR_PS_MULTIPLES.get(sector, 2.0)
    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")
    implied_ev = target_ps * float(revenue)
    implied_equity = implied_ev - float(total_debt) + float(cash)
    if implied_equity <= 0:
        return None
    result = implied_equity / shares
    # Subject to Layer 2 bounds
    ...
```

Sector P/S targets: Tech=6x, Healthcare=5x, Comm Services=3x, Consumer Disc=1.5x, Consumer Staples=1.5x, Industrials=1.5x, Energy=1x, Materials=1x, Utilities=2x. Fallback=2.0x.

**Weight allocation when fallbacks are used:**
- If only P/B produces a value: single-method intrinsic = P/B result
- If only Revenue Multiple produces a value: single-method intrinsic = Revenue result
- If both produce values: 60% P/B + 40% Revenue Multiple
- Margin of safety is wider for fallback methods (base MoS + 10% penalty)

### 4. Bug Fixes and Guardrails

**Fix `total_debt`:**
- Add `short_term_debt: Decimal = Decimal("0")` to `BalanceSheet`
- Change `total_debt` property: `return (self.long_term_debt or 0) + self.short_term_debt`
- Normalizer maps yfinance `Current Debt` or `Current Debt And Capital Lease Obligation` to `short_term_debt`

**Empty JSONB detection:**
- In the scoring service, check if `cash_flow == {}` or `income_statement == {}` before building FinancialPeriod
- Set `invalid_reason="financial_data_empty"` early, before valuation

**Growth rate guardrails:**
- In DCF, if `period.revenue_growth` is available, use `min(max(actual_growth, 0.0), 0.15)` instead of fixed 5%
- Cap at 15% prevents runaway projections
- Floor at 0% prevents negative growth in DCF

**Complete `invalid_reason` taxonomy:**
- `shares_outstanding_missing` — shares is 0 or None
- `shares_outstanding_out_of_bounds` — shares outside [100K, 50B]
- `implied_market_cap_unreasonable` — price * shares outside [$1M, $10T]
- `currency_rate_unavailable` — currencies differ but no exchange rate available
- `financial_data_empty` — JSONB is `{}`
- `insufficient_data` — all methods (primary + fallback) returned None
- `intrinsic_value_extreme` — Layer 4: intrinsic outside [1%, 500%] of actual price
- `methods_inconsistent` — Layer 3: all methods filtered as outliers

## Expected Coverage After Fix

| Category | Before | After | Delta |
|----------|--------|-------|-------|
| Valid price target | 3,440 (44.7%) | ~5,800 (75%+) | +2,360 |
| Currency mismatch (now converted) | 623 → blocked | ~580 → valid targets | +580 |
| Unprofitable (P/B/Rev fallback) | 2,689 → blocked | ~1,800 → valid targets | +1,800 |
| Empty JSONB (flagged) | 276 → silent | 276 → `financial_data_empty` | labeled |
| Extreme/bounds/shares | ~520 → partially labeled | ~520 → fully labeled | labeled |
| Truly ineligible | 0 labeled | ~1,400 with clear reason | labeled |

## Constraints

- No placeholder targets
- No arbitrary caps without explanation
- No hardcoded overrides for specific tickers
- No UI-level masking
- All fixes at the calculation layer
- Deterministic and scalable across full universe
