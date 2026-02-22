# Polygon.io Provider Integration Design

**Goal:** Add Polygon.io as the primary price data provider, with yfinance as fallback. Stub fundamentals and earnings methods for future plan upgrade.

**Constraint:** Free (Basic) tier — 5 API calls/min, end-of-day data, 2-year history max.

---

## Provider Architecture

**New file:** `engine/src/margin_engine/ingestion/providers/polygon_provider.py`

**Class:** `PolygonProvider(DataProvider)`

- Uses official `polygon-io/client-python` SDK (`polygon.RESTClient`)
- Constructor: `api_key: str`, optional `RateLimiter`
- `ProviderInfo`: name=`"polygon"`, priority=`20`, rate_limit=`5` req/min, `requires_api_key=True`
- Supported categories: `[PRICE]` only (fundamentals/earnings stubbed until plan upgrade)

**Dependency:** `polygon-api-client` added to engine package.

**Fallback chains after integration:**

| Category     | Chain (highest priority first) |
|-------------|-------------------------------|
| Price        | Polygon (20) -> yfinance (10) |
| Fundamentals | yfinance (10) -> FMP (5)      |
| Earnings     | yfinance (10) -> FMP (5)      |

## Price History Implementation

`fetch_price_history(ticker: str, days: int = 365) -> FetchResult`

1. Convert ticker via `SymbolMapper` (e.g., `BRK-B` -> `BRK.B`)
2. Clamp `days` to 730 (free tier 2-year limit), log warning if clamped
3. Call `client.get_aggs(ticker, multiplier=1, timespan="day", from_=from_date, to=to_date, adjusted=True, sort="asc")`
4. Map aggregates to `{"bars": [{"date": ..., "open": ..., "high": ..., "low": ..., "close": ..., "volume": ..., "adj_close": ...}]}`
5. Return `FetchResult(provider_name="polygon", category=PRICE, ...)`

No normalizer changes needed — `normalize_price_bar` already handles lowercase keys.

## Stubbed Methods

- `fetch_fundamentals` — raises `NotImplementedError` (requires Starter+ plan)
- `fetch_earnings` — raises `NotImplementedError` (requires Starter+ plan)

Not listed in `supported_categories` so registry won't include them in fallback chains. Add categories + implement methods when upgrading plan.

## Registration & Config

- Export from `providers/__init__.py` and `ingestion/__init__.py`
- `POLYGON_API_KEY` already in `.env.example`
- Add `polygon_api_key` to API config settings
- Wire into registry construction in ingestion service

## Testing

All tests mock the Polygon SDK (no real API calls):

1. Info metadata correctness (name, priority, categories, rate limit)
2. Price history success — verify FetchResult shape and bar mapping
3. Days clamped to 730 for free tier
4. Empty response handling
5. API error -> FetchResult with success=False
6. Stubbed fundamentals/earnings raise NotImplementedError
7. Registry integration — Polygon at top of Price fallback chain
