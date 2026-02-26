# Batched Ingest Pipeline Design

**Date:** 2026-02-25
**Status:** Approved
**Problem:** `full_ingest` processes ~3,000 tickers sequentially at 3 tickers/min, requiring ~17 hours. The ARQ job timeout is 5 hours. The job can never finish. When it times out, the DB connection is killed mid-query, surfacing as a `TimeoutError` on asyncpg ping.

**Solution:** Replace the monolithic `full_ingest` with an orchestrator that enqueues fixed-size batch jobs. ARQ runs 2-3 batches concurrently. A Redis-based rate limiter coordinates API call pacing across batches. A sweep job guarantees no ticker is missed. Scoring runs once after all ingestion completes.

---

## Job Architecture

Five new jobs replace `full_ingest`:

| Job | Purpose | Timeout | Triggered by |
|-----|---------|---------|-------------|
| `orchestrate_ingest` | Load universe, chunk into batches of 50, enqueue batch jobs, set Redis counters | 60s | Cron (daily 21:00 UTC) |
| `ingest_batch` | Seed ~50 tickers, record per-ticker status, increment Redis completion counter | 1200s (20 min) | `orchestrate_ingest` |
| `ingest_sweep` | Find tickers missing successful ingest today, enqueue cleanup batch | 120s | Last `ingest_batch` to complete |
| `ingest_sweep_complete` | Enqueue `full_score` → `full_score_v3` → `full_score_v4` chain | 60s | `ingest_sweep` (or its cleanup batch) |

Retained unchanged: `full_score`, `full_score_v3`, `full_score_v4`, `live_price_poll`, `full_13f_ingest`, `retry_quarantined`.

**Worker config**: `max_jobs=3` (from 1). ARQ runs 3 `ingest_batch` coroutines concurrently in one event loop.

**Batch size**: 50 tickers (configurable via `MARGIN_INGEST_BATCH_SIZE`). At 3 concurrent batches × ~3 tickers/min each = ~9 tickers/min. 3,000 tickers ≈ 333 min ≈ 5.5 hours. With rate limit at 36/min: ~1.8 hours.

---

## Redis Rate Limiter

Replaces the in-process `RateLimiter` (token bucket) with a Redis sliding window counter.

**Implementation** (new class `RedisRateLimiter` in `api/src/margin_api/services/rate_limiter.py`):

```
key = "ratelimit:yfinance:{window_timestamp}"
count = INCR key
if count == 1: EXPIRE key 60
if count > max_per_minute: sleep until next window
```

**Config**: `MARGIN_INGEST_RATE_LIMIT=36` (default). Supports 3 concurrent batches at 12 req/min each.

**Behavior when limit hit**: `await asyncio.sleep(seconds_until_next_window)` — yields to event loop so other batches can do DB writes during the wait.

**Provider change**: `fetch_all()` receives the `RedisRateLimiter` via injection (same `async acquire()` interface as the in-process limiter). The engine's `RateLimiter` stays as fallback for tests and local dev.

---

## Batch Completion Coordination

Redis keys namespaced under the ingestion run ID:

| Key | Type | Purpose | TTL |
|-----|------|---------|-----|
| `ingest:{run_id}:total` | STRING | Total batch count | 24h |
| `ingest:{run_id}:completed` | STRING | Atomic counter (INCR per batch) | 24h |
| `ingest:{run_id}:failed_tickers` | LIST | Tickers that failed (RPUSH per failure) | 24h |

**Flow:**

1. `orchestrate_ingest` sets `total=60`, `completed=0`, creates `IngestionRun` DB row
2. Each `ingest_batch` finishes → `INCR completed` → reads result
3. If `completed == total` → that batch enqueues `ingest_sweep`
4. If `completed < total` → batch exits normally

**Sweep logic:**

- Queries `IngestionTickerStatus` for current run: finds tickers with `status != 'success'` or tickers in active universe with no status row
- If missing > 0: enqueues one `ingest_batch` with just those tickers (`is_sweep=True`)
- That sweep batch completes → enqueues `ingest_sweep_complete` → triggers scoring chain
- If missing == 0: directly enqueues `ingest_sweep_complete`

**Sweep runs once.** Tickers that fail the sweep are logged to `IngestionRun.failed_tickers` and left for the Sunday `retry_quarantined` cron. No infinite retry loops.

---

## Per-Ticker Tracking & Batch Job Internals

**`ingest_batch` signature:**

```python
async def ingest_batch(
    ctx: dict,
    run_id: str,
    tickers: list[str],
    is_sweep: bool = False,
)
```

**Per-ticker loop:**

1. Check `IngestionTickerStatus` — skip if already succeeded today (resume support)
2. Acquire Redis rate limit
3. Call `seed_ticker_data()` for the ticker
4. On success: write `IngestionTickerStatus(status='success')`
5. On failure: write `IngestionTickerStatus(status='failed', error=str(e))`, RPUSH to failed list
6. Continue to next ticker (never abort batch on single failure)

**Session management**: One `async with session_factory() as session` per ticker. Connection returned to pool after each ticker.

**Circuit breaker**: Retained. 10 consecutive yfinance failures → batch exits early, remaining tickers marked `circuit_breaker_tripped`. Sweep picks them up.

**No changes to `seed_ticker_data` or `cli.py`**. Batching is purely at the worker layer.

---

## Cron Schedule & Worker Config

**WorkerSettings changes:**

| Setting | Current | New |
|---------|---------|-----|
| `max_jobs` | 1 | 3 |
| `job_timeout` (default) | 18000s | 1200s |
| `cron_jobs` | `full_ingest` 21:00 UTC | `orchestrate_ingest` 21:00 UTC |

**Complete daily pipeline:**

```
21:00 UTC   orchestrate_ingest     enqueues ~60 batches
~21:00-23:00  ingest_batch ×60     3 concurrent, ~2 hours
~23:00      ingest_sweep           auto-triggered by last batch
~23:10      full_score chain       auto-triggered by sweep
22:00 UTC   full_13f_ingest        unchanged, independent
```

**`live_price_poll` interaction**: With `max_jobs=3`, price polls may wait for a slot during ingest hours. Acceptable — worst case delay is ~20-30s (time for one ticker to finish).

---

## Observability

**Logging**: Each batch logs with prefix `[ingest:{run_id}:batch-{n}]`. Orchestrator logs full plan (universe size, batch count, tickers per batch).

**DB tracking**: `IngestionRun` row per day with `succeeded_count`, `failed_count`, updated atomically by each batch. Sweep writes final summary.

---

## Migration Path

1. Delete `full_ingest` function and its cron entry
2. Add 4 new jobs: `orchestrate_ingest`, `ingest_batch`, `ingest_sweep`, `ingest_sweep_complete`
3. Add `RedisRateLimiter` service in `api/src/margin_api/services/rate_limiter.py`
4. Update `WorkerSettings` (max_jobs, default timeout, new cron)
5. Add config vars: `MARGIN_INGEST_BATCH_SIZE`, `MARGIN_INGEST_RATE_LIMIT`, `MARGIN_INGEST_CONCURRENCY`

**Rollback**: Revert the commit. Old `full_ingest` cron returns. New Redis keys TTL away in 24h.

---

## New Config Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MARGIN_INGEST_BATCH_SIZE` | 50 | Tickers per batch job |
| `MARGIN_INGEST_RATE_LIMIT` | 36 | Max yfinance API calls per minute (Redis limiter) |
| `MARGIN_INGEST_CONCURRENCY` | 3 | ARQ `max_jobs` setting |
