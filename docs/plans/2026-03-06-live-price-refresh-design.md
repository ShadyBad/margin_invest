# Live Price Refresh Design

**Date:** 2026-03-06
**Status:** Approved

## Problem

The price chart in the candidate expanded view shows stale data. Price history (`FinancialData.price_history`) only updates during the nightly `orchestrate_ingest` cron job (21:30 UTC). The `live_price_poll` worker updates `actual_price` via Redis every 5 minutes but does not update the chart's bar data. If nightly ingestion fails or hasn't run, chart data becomes stale indefinitely.

**Expected:** Chart reflects prices within ~15 minutes of real-time during market hours.
**Actual:** Chart shows data as old as the last successful ingestion run.

## Root Cause

Two independent issues:

1. **No ingestion runs recorded** — the `ingestion_runs` table is empty, meaning the nightly `orchestrate_ingest` worker hasn't been running (or hasn't been running against this database).
2. **Architectural gap** — even when nightly ingestion works, `price_history` bars only update once per day. There is no mechanism to refresh chart data during market hours.

## Data Flow (Current)

```
Chart bars <- score.price_history <- FinancialData.price_history (JSONB, DB)
                                     ^ Only updated by seed_ticker_data()
                                     ^ Runs during nightly ingest or manual CLI seed

Live price <- score.actual_price  <- Redis cache (LivePriceService)
                                     ^ Updated every 5 min by live_price_poll
                                     ^ Only for high/exceptional conviction tickers
```

## Solution: Redis-backed Live Bar Injection (Approach A)

Extend the existing `live_price_poll` worker to store today's full OHLCV bar in Redis, then inject it into the `price_history` response at API serving time. No frontend changes required.

### Data Flow (New)

```
Chart bars <- score.price_history <- DB bars + Redis live bar (merged at API response time)
                                     ^ DB: historical daily bars (nightly ingest)
                                     ^ Redis: today's bar (updated every 15 min)
```

## Design

### 1. Worker: `live_price_poll` Changes

**Current:** Every 5 min, fetches `last_price` for high/exceptional conviction tickers.

**New:**
- **Scope:** All scored tickers (query latest score per asset, remove conviction filter)
- **Interval:** Every 15 minutes (reduce yfinance API load)
- **Data:** Fetch today's daily bar (open, high, low, close, volume) via yfinance `fast_info` + `history(period="1d")`
- **Storage:** Redis key `live_bar:{ticker}` with 24h TTL

Redis bar format:
```json
{
  "date": "2026-03-06",
  "open": 188.50,
  "high": 192.30,
  "low": 187.20,
  "close": 191.75,
  "volume": 4523000,
  "updated_at": "2026-03-06T15:45:00Z"
}
```

Keep existing `live_price:{ticker}` cache for backward compat with `actual_price` override.

### 2. LivePriceService: New Methods

Add to `services/live_prices.py`:

- `set_bar(ticker: str, bar: dict) -> None` — store today's OHLCV bar, TTL 24h
- `get_bar(ticker: str) -> dict | None` — retrieve today's bar

Existing `set_price`/`get_price` remain unchanged.

### 3. Scores API: Bar Injection

In `routes/scores.py`, when `"price_history"` is in the `include` param:

1. Fetch `FinancialData.price_history` bars from DB (existing, unchanged)
2. Call `LivePriceService.get_bar(ticker)` from Redis
3. If live bar exists:
   - If last DB bar date == live bar date: **replace** last bar (update today's close)
   - If last DB bar date != live bar date: **append** live bar (new trading day)
4. Return merged list

### 4. Error Handling

- Redis unavailable: fall back to DB-only bars (current behavior)
- yfinance failure for individual ticker: skip, don't block other tickers
- Stale live bar (weekend/holiday date): don't inject — DB bars are authoritative
- Market closed: live_price_poll still runs but yfinance returns yesterday's close; the date check prevents duplicate injection

### 5. Frontend

No changes. `PriceChart` renders whatever `bars` array it receives from the API.

## Files Changed

| File | Change |
|------|--------|
| `api/src/margin_api/workers.py` | Expand `live_price_poll` scope, fetch OHLCV bar, store via `set_bar` |
| `api/src/margin_api/services/live_prices.py` | Add `set_bar`/`get_bar` methods |
| `api/src/margin_api/routes/scores.py` | Inject live bar into `price_history` response |
| `api/tests/` | Tests for bar injection logic, worker scope change |

## Constraints

- yfinance free tier: no explicit rate limit but aggressive polling risks IP blocks. 15-min interval with ~10 tickers is conservative.
- Redis TTL 24h: bars expire overnight. Nightly ingestion provides canonical daily bars.
- No paid data provider required.

## Not In Scope

- Intraday candle chart (1D view with 5-min/15-min bars)
- PriceIntraday table integration
- Fixing the nightly ingestion on Railway (separate operational issue)
- WebSocket/SSE real-time streaming
