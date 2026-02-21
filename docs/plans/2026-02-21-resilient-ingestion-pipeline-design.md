# Resilient Ingestion Pipeline Design

**Date:** 2026-02-21
**Status:** Approved
**Scope:** engine/ingestion, api/cli, api/workers, api/services/ingestion

## Problem

Railway logs show hundreds of tickers failing ingestion with "No earnings dates found, symbol may be delisted." Affected tickers include active blue-chip equities (FSLR, FRPT, FROG, FSLY) — proving this is a systematic pipeline failure, not actual delistings.

## Root Causes (Verified)

### 1. Missing `lxml` dependency (PROVEN)

`yfinance.Ticker.earnings_dates` requires `lxml` to parse Yahoo Finance HTML. It is not in `engine/pyproject.toml`. Every `fetch_earnings()` call raises `Import lxml failed` — 100% failure rate for all tickers.

With `lxml` installed, all 7 tested "failing" tickers returned 23-25 earnings dates each.

### 2. Rate limiter undercounts 4-5x (PROVEN from code)

`cli.py:297` gates once per ticker at 60 req/min. But `seed_ticker_data` makes 4+ HTTP calls per ticker (3 provider fetches + 1 direct `yfinance.Ticker().info`). Effective rate is ~240 req/min — exceeding Yahoo's soft-block threshold for cloud IPs.

### 3. Error classification service is orphaned (PROVEN from code)

`api/services/ingestion.py` has `classify_error()`, `should_ingest_ticker()`, and `update_failure_status()` but none are called from `cli.py:seed_ticker_data` or `workers.py:full_ingest`. Failed tickers are never quarantined or permanently skipped.

### 4. Silent partial failures (PROVEN from code)

When `earnings.success` is `False`, `seed_ticker_data` stores `None` for `earnings_data` and returns `"ok"`. The ticker appears successful but has incomplete data. No logging of which categories failed.

## Design

### Workstream 1: Immediate Fixes

#### 1a. Add `lxml` dependency

Add `lxml` to `engine/pyproject.toml` dependencies. Unblocks `yfinance.Ticker.earnings_dates`.

#### 1b. Provider-owned rate limiting

Move rate limiting inside `YFinanceProvider` so each HTTP request is gated, not each ticker. The provider knows how many requests its methods make.

Remove the per-ticker limiter from the seed loop in `cli.py` and `workers.py`.

#### 1c. Reuse `yf.Ticker` object

`seed_ticker_data` creates 4 separate `yf.Ticker()` objects for the same symbol (3 in provider methods + 1 direct at line 149). yfinance caches data per-instance, so reusing one object reduces HTTP calls.

Change `YFinanceProvider` to accept an optional pre-built `yf.Ticker` instance, or add a `fetch_all(ticker)` method that creates one instance and fetches all categories.

Extract the `info` dict fetch into the provider as well, removing the direct yfinance import from `cli.py`.

### Workstream 2: Error Classification Wiring

#### 2a. Wire classification into seed flow

After catching an exception in `seed_ticker_data`:
- Call `classify_error(exc)` to get `"transient"` / `"permanent"` / `"data_unavailable"`
- Call `update_failure_status(session, asset, error_type, str(exc))`
- Return the classification to callers

#### 2b. Wire skip check into seed loop

Before calling `seed_ticker_data`, check `should_ingest_ticker(asset.ingestion_status, asset.consecutive_failures, asset.last_retry_at)`. Apply in both `cli.py:run_seed` and `workers.py:full_ingest`.

Requires a pre-fetch of the asset record, but avoids wasting API calls on known-bad tickers.

#### 2c. Per-category fetch logging

Log each category's status per ticker:
```
[42/3000] FSLR: fundamentals=ok price=ok earnings=FAIL(lxml) info=ok → stored (partial)
```

Check `fundamentals.success`, `price_history.success`, `earnings.success` individually and log each.

#### 2d. Richer return type

Replace the `str` return (`"ok"` / `"error"` / `"foreign"`) with a dataclass:
```python
@dataclass
class SeedResult:
    status: str                    # "ok", "partial", "failed", "foreign", "skipped"
    categories_failed: list[str]   # e.g., ["earnings"]
    error_message: str | None
```

#### 2e. Partial success tracking

Store a `data_categories_present` on `FinancialData` or as part of the existing JSONB — e.g., `{"fundamentals": true, "price": true, "earnings": false}`. Lets the scoring pipeline know what data is missing.

### Workstream 3: Multi-Provider Architecture

#### 3a. Provider selection

- **Primary:** yfinance (free, covers 90%+ of tickers when lxml is installed)
- **Fallback:** FMP (Financial Modeling Prep) for failed categories only

FMP free tier (250 req/day) covers the ~50-100 tickers where yfinance fails. FMP paid ($14/mo, 300 req/min) covers the full universe as a complete backup.

No need for Polygon (yfinance price data is reliable) or Alpha Vantage (slow, expensive).

#### 3b. Per-category fallback strategy

```
For each ticker:
  1. Try yfinance for ALL categories (fundamentals, price, earnings)
  2. For any category that failed:
     → Try FMP for that specific category only
  3. If both fail for a category:
     → Mark category as unavailable, proceed with partial data
```

Minimizes FMP API calls — only hits FMP for what yfinance couldn't provide.

#### 3c. FMP provider implementation

New file: `engine/src/margin_engine/ingestion/providers/fmp_provider.py`

Implements `DataProvider` ABC with `fetch_fundamentals`, `fetch_earnings`, `fetch_price_history`. Requires `FMP_API_KEY` env var (already in `.env.example`). Provider-aware rate limiting via its own `RateLimiter` instance.

#### 3d. Symbol mapper

New file: `engine/src/margin_engine/ingestion/symbol_mapper.py`

`SymbolMapper` class with:
- `to_provider(ticker: str, provider_name: str) -> str`
- `from_provider(ticker: str, provider_name: str) -> str`
- Default: pass-through (most symbols identical)
- Override map from `engine/symbol_overrides.yaml` for known exceptions (BRK-B vs BRK.B, etc.)

Use yfinance format as canonical (matches DB storage).

#### 3e. What NOT to build (YAGNI)

- OTC/Pink Sheet symbol mapping (excluded by screener)
- International symbol mapping (excluded by currency + country guard)
- ADR mapping (excluded by currency filter)
- Historical symbol chain tracking (backtesting concern, not ingestion)
- Polygon or Alpha Vantage providers

### Workstream 4: Circuit Breaker & Retry

#### 4a. Circuit breaker per provider

New file: `engine/src/margin_engine/ingestion/circuit_breaker.py`

States:
- **Closed** (normal): requests flow through
- **Open** (tripped): skip all requests to this provider
- **Half-open**: allow 1 probe request after cooldown

Thresholds:
- Trip after 10 consecutive failures within 5 minutes
- Cooldown: 15 minutes
- On trip: log WARNING, remaining tickers fall through to next provider in registry

Lives alongside `RateLimiterRegistry` or in a new `ProviderHealth` tracker.

#### 4b. Retry with exponential backoff

Per-request retry for transient errors only:
- Max 3 retries
- Backoff: 2s → 4s → 8s
- Only for errors where `classify_error` returns `"transient"` (timeouts, 429s, 503s)
- Implemented as a decorator or wrapper inside provider fetch methods

#### 4c. Run-level resume

Before seeding a ticker, check if `FinancialData` exists with today's `period_end` and all categories present. If so, skip the ticker entirely — no API calls needed.

Makes the pipeline idempotent and resumable after crashes. No new state tracking required — uses existing data.

### Workstream 5: Dead-Letter Queue & Alerting

#### 5a. Per-ticker audit trail

Write an `IngestionTickerStatus` row for every ticker processed in a run (not just failures). Fields:
- `status`: `"ok"`, `"partial"`, `"failed"`, `"skipped"`, `"foreign"`
- `data_fetched` JSONB: `{"fundamentals": "ok", "price": "ok", "earnings": "failed:lxml"}`
- `duration_ms`: time spent on this ticker

#### 5b. Extended run metrics

Add fields to `IngestionRun`:
- `tickers_partial: int` — tickers that succeeded with missing categories
- `provider_stats: JSONB` — per-provider breakdown: `{"yfinance": {"attempted": 2800, "succeeded": 2750}, "fmp": {"attempted": 50, "succeeded": 45}}`
- `circuit_breaker_trips: int` — number of breaker trips during the run

#### 5c. Threshold-based alerting

After each `full_ingest` run, check thresholds and log at appropriate level:
- **ERROR** if `failed / requested > 0.20` (>20% failed)
- **WARNING** if `partial / requested > 0.10` (>10% partial)
- **WARNING** if any circuit breaker tripped
- **INFO** with full summary stats on every run

Railway log-based alerts can trigger on ERROR/WARNING levels. No external alerting integration needed now — add a `send_alert(run)` hook point for future Slack/PagerDuty.

#### 5d. Quarantine review endpoint

New endpoint: `GET /admin/ingestion/quarantined`

Returns all assets with `ingestion_status in ("quarantined", "permanently_skipped")` with `last_failure_reason` and `consecutive_failures`. Allows quick triage without direct DB queries.

### Workstream 6: Testing

#### Unit tests

- **`FMPProvider`**: Mock HTTP responses, verify normalization into `FetchResult`. Test missing API key → excluded from registry.
- **`CircuitBreaker`**: State transitions (closed → open → half-open → closed), trip threshold, cooldown timer, probe behavior.
- **`SymbolMapper`**: Pass-through default, override lookup, round-trip.
- **Retry decorator**: Backoff timing, max retries, transient-only retry.

#### Integration tests

- Seed with permanent error → verify `ingestion_status == "permanently_skipped"`
- Seed with 3 transient errors → verify `ingestion_status == "quarantined"`
- Seed quarantined ticker within 7 days → verify skipped
- Seed with earnings failure but fundamentals/price success → verify `"partial"` status, verify `data_fetched` JSONB
- Circuit breaker: mock yfinance failing 10x → verify breaker trips → verify fallback to FMP
- Resume: seed ticker, seed again same day → verify no API calls (skipped)

#### Not testing

- Real yfinance/FMP HTTP behavior (flaky, external)
- Railway-specific deployment behavior
- End-to-end tests hitting real APIs in CI

## Files Changed

| File | Change |
|------|--------|
| `engine/pyproject.toml` | Add `lxml` dependency |
| `engine/src/margin_engine/ingestion/providers/yfinance_provider.py` | Accept shared Ticker, internal rate limiting, `fetch_all` method |
| `engine/src/margin_engine/ingestion/providers/fmp_provider.py` | New: FMP data provider |
| `engine/src/margin_engine/ingestion/registry.py` | Circuit breaker integration, per-category fallback |
| `engine/src/margin_engine/ingestion/rate_limiter.py` | Per-request gating inside providers |
| `engine/src/margin_engine/ingestion/circuit_breaker.py` | New: circuit breaker state machine |
| `engine/src/margin_engine/ingestion/symbol_mapper.py` | New: cross-provider symbol translation |
| `engine/symbol_overrides.yaml` | New: symbol override map |
| `api/src/margin_api/cli.py` | Wire error classification, per-category logging, resume check, `SeedResult` return type |
| `api/src/margin_api/workers.py` | Wire same changes into `full_ingest` |
| `api/src/margin_api/services/ingestion.py` | Extend with partial-success handling |
| `api/src/margin_api/db/models.py` | Extend `IngestionRun` with `tickers_partial`, `provider_stats`, `circuit_breaker_trips` |
| `api/src/margin_api/routes/admin.py` | Add `GET /admin/ingestion/quarantined` endpoint |
| `engine/tests/ingestion/` | Unit tests for FMPProvider, CircuitBreaker, SymbolMapper, retry |
| `api/tests/` | Integration tests for error wiring, partial success, resume |

## Dependency Order

```
Workstream 1 (immediate fixes)
  → Workstream 2 (error classification) — depends on 1c (fetch_all refactor)
  → Workstream 4 (circuit breaker & retry) — depends on 1b (provider-owned rate limiting)
    → Workstream 3 (multi-provider) — depends on 4a (circuit breaker) and 2d (richer return type)
      → Workstream 5 (dead-letter & alerting) — depends on 2c/2d (per-category logging) and 3b (provider stats)
        → Workstream 6 (tests) — after all implementation
```
