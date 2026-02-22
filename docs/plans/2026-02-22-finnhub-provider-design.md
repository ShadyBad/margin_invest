# Finnhub Provider Integration Design

**Goal:** Add Finnhub as the provider for earnings, news, insider transactions, and institutional holdings data categories.

**Constraint:** Free tier — 60 API calls/min, 30 calls/sec hard cap.

---

## Provider Architecture

**New file:** `engine/src/margin_engine/ingestion/providers/finnhub_provider.py`

**Class:** `FinnhubProvider(DataProvider)`

- Uses official `finnhub-python` SDK (`finnhub.Client`)
- Constructor: `api_key: str`, optional `RateLimiter`
- `ProviderInfo`: name=`"finnhub"`, priority=`5`, rate_limit=`60` req/min, `requires_api_key=True`
- Supported categories: `[EARNINGS, INSIDER, INSTITUTIONAL, NEWS]`

**Dependency:** `finnhub-python` added to engine package.

**Fallback chains after integration:**

| Category       | Chain (highest priority first) |
|---------------|-------------------------------|
| Price          | Polygon (20) -> yfinance (10) |
| Fundamentals   | yfinance (10) -> FMP (5)      |
| Earnings       | Finnhub (5)                   |
| News           | Finnhub (5)                   |
| Insider        | Finnhub (5)                   |
| Institutional  | Finnhub (5)                   |

## Fetch Methods

### fetch_earnings(ticker) -> FetchResult

- Calls `client.company_earnings(symbol=ticker, limit=12)` (3 years of quarters)
- Free tier returns last 4 quarters — accept whatever comes back
- Returns `raw_data: {"earnings": [{actual, estimate, period, quarter, surprise, surprisePercent, year}, ...]}`

### fetch_insider_transactions(ticker) -> FetchResult

- Calls `client.stock_insider_transactions(symbol=ticker, from_=from_date, to=to_date)` (last 365 days)
- Returns `raw_data: {"transactions": [{name, share, change, filingDate, transactionDate, transactionCode, transactionPrice, ...}]}`
- Finnhub returns data nested under a `data` key — extract it

### fetch_institutional_holdings(ticker) -> FetchResult

- Calls `client.institutional_ownership(symbol=ticker, from_=from_date, to=to_date)` (last 365 days)
- Returns `raw_data: {"holdings": [{cik, name, putCall, change, noVoting, percentage, share, value, ...}]}`

### fetch_news(ticker) -> FetchResult

- New method added to `DataProvider` ABC
- Calls `client.company_news(symbol=ticker, _from=from_date, to=to_date)` (last 30 days)
- Returns `raw_data: {"articles": [{headline, summary, source, datetime, url, category, ...}]}`

All methods catch exceptions and return `FetchResult(success=False, error=...)` on failure.

## Registry & ABC Changes

1. **DataProvider ABC** — Add `fetch_news(ticker: str) -> FetchResult` default method (raises NotImplementedError)

2. **registry.py** — Remove `DataCategory.NEWS` from `_NON_TICKER_CATEGORIES` (becomes just `{MACRO}`). Add `DataCategory.NEWS: "fetch_news"` to `_CATEGORY_METHOD_MAP`.

3. **Config** — Add `finnhub_api_key: str = ""` to API settings (env var: `MARGIN_FINNHUB_API_KEY`).

4. **Exports** — Add `FinnhubProvider` to `providers/__init__.py` and `ingestion/__init__.py`.

## Testing

All tests mock the Finnhub SDK (no real API calls):

1. Info metadata correctness (name, priority, categories, rate limit)
2. Empty API key raises ValueError
3. Earnings success — FetchResult shape and data mapping
4. Insider transactions success — FetchResult shape
5. Institutional holdings success — FetchResult shape
6. News success — FetchResult shape
7. Each method: API error returns FetchResult with success=False
8. Each method: empty response handled gracefully
9. Registry integration — Finnhub in correct fallback chains for all 4 categories
10. Registry: fetch_news dispatches via NEWS category
11. ABC: fetch_news default raises NotImplementedError
