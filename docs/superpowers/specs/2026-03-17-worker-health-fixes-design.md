# Worker Health Fixes — Design Spec

**Date**: 2026-03-17
**Status**: Draft
**Scope**: ARQ worker reliability — price poll quarantine recovery, failure attribution, log noise

## Problem Statement

Production worker logs reveal that 94% of the ticker universe (2,867 of ~3,054) is quarantined from price polling due to compounding issues in the failure-tracking system:

1. **Batch-level failure misattribution**: When `yf.download()` times out for a batch of ~100 tickers, every ticker in the batch gets a failure recorded — even though the failure is infrastructure-level, not ticker-specific.
2. **Unimplemented recovery**: `retry_quarantined()` is a stub returning `{"status": "not_implemented"}`. Quarantined tickers have no path back.
3. **TTL reset race**: `_record_fail()` resets the 24h Redis TTL on every failure increment, so the 24h window extends indefinitely as long as failures keep happening. For steadily-failing tickers, the counter never expires — making quarantine effectively permanent even without `retry_quarantined`.
4. **Silent exception swallowing**: Redis errors in `_record_fail()` are caught with bare `except: pass`.
5. **yfinance TzCache log spam**: Container lacks a writable cache directory, producing ~16 warning lines per poll cycle.
6. **expire_stale_approvals noise**: Running more frequently than needed; always finds 0 to expire.

## Approach

Surgical fixes to the existing Redis-counter architecture. No schema changes, no new tables, no architectural rewrites.

## Design

### 1. Per-Ticker Failure Attribution in `_download_batch()`

**File**: `api/src/margin_api/workers.py` — `_download_batch()` inner function (~line 2794)

**Current behavior**: On batch-level exception (timeout, network error), ALL tickers in the batch get `_record_fail()`.

**New behavior**:

- **Successful batch download**: Inspect the returned DataFrame per ticker. Tickers with no data or NaN-only rows get `_record_fail()`. Tickers with valid data get their counter **cleared** (`DEL price_fail:{ticker}`).
- **Batch-level exception** (timeout, network error): Do NOT penalize any individual ticker. Log a warning: `"Batch download failed (infrastructure): {exc}"`. The failure is not ticker-specific.
- **Batch timeout recovery**: On `asyncio.TimeoutError` specifically, retry once with the batch split in half (each half gets the same 60s timeout). Halves run sequentially (first half, then second half). Tickers in a successful half are processed normally (per-ticker attribution). Tickers in a failed half are not penalized. Other exception types (e.g., `ConnectionError`) are not retried — just logged and skipped.

**Rationale**: A ticker should only accumulate failures when yfinance specifically returns no data for it, not when the network is flaky. The current `except (TimeoutError, Exception)` is redundant — the refactored handler catches `asyncio.TimeoutError` for the retry path and `Exception` for the log-and-skip path separately.

### 2. Fix `_record_fail()` TTL Race Condition

**File**: `api/src/margin_api/workers.py` — `_record_fail()` (~line 2905)

**Current behavior**: Every call runs `INCR` then `EXPIRE 86400`, resetting the 24h countdown on every failure.

**New behavior**:

```python
async def _record_fail(redis_client, ticker: str) -> None:
    key = f"price_fail:{ticker}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            # Only set TTL on first failure — start the 24h window
            await redis_client.expire(key, 86400)
        else:
            # Safety: if key somehow has no TTL (crash between INCR and EXPIRE),
            # set it now to prevent leaked keys
            ttl = await redis_client.ttl(key)
            if ttl == -1:  # key exists but has no expiry
                await redis_client.expire(key, 86400)
        logger.warning("price_fail:%s count=%d", ticker, count)
    except Exception:
        logger.debug("Redis error in _record_fail for %s", ticker, exc_info=True)
```

**Key changes**:
- `EXPIRE` only called when `INCR` returns 1 (first failure in window)
- Safety fallback: if key has no TTL (crash between INCR and EXPIRE on a prior call), set TTL to prevent leaked keys
- Structured logging replaces silent swallowing
- 24h window starts from first failure and subsequent failures accumulate within it

### 3. Implement `retry_quarantined()`

**File**: `api/src/margin_api/workers.py` — `retry_quarantined()` (~line 2915)

**Current behavior**: Stub — `return {"status": "not_implemented"}`

**New behavior**:

- Scan Redis for all `price_fail:*` keys with value >= 5 (use `SCAN` with `COUNT 500` hint to reduce round trips)
- Take a random sample of up to 50 quarantined tickers per run
- Attempt `yf.download(sample, period="1d")` in small batches of 10
- For each ticker that returns valid data: `DEL price_fail:{ticker}` (un-quarantine)
- For each ticker that still fails: reset counter to exactly `max_consecutive_fails` (5) with a fresh 24h TTL, rather than leaving inflated values from misattribution (e.g., `price_fail:XYZ = 47`)
- Log summary: `"retry_quarantined: tested={n}, recovered={r}, still_failing={f}"`

**Schedule change**: From weekly (Sunday 00:00 UTC) to every 6 hours (`hour={0, 6, 12, 18}`).

**One-time deploy recovery**: On deploy, run a one-time bulk cleanup of all `price_fail:*` keys. The existing counter data is garbage — corrupted by the batch-level misattribution bug. Rather than waiting ~14 days for `retry_quarantined` to cycle through 2,867 tickers at 50/run, clear the slate so `live_price_poll` immediately processes all tickers and builds fresh, accurate failure data. Implementation: add a Redis `SCAN` + `DEL` loop in the worker startup function, gated by a one-time flag key (`price_fail_bulk_reset_done`).

**Rationale**: 50-ticker cap per run prevents hammering yfinance. Repeated 6-hourly runs gradually work through the full quarantine list. A ticker that was quarantined due to a transient outage gets a second chance within hours, not days.

### 4. yfinance TzCache Fix

**File**: `api/src/margin_api/workers.py` — worker startup function

**Change**: Add `yf.set_tz_cache_location("/tmp/yfinance-cache")` at worker startup.

**Rationale**: Gives yfinance a writable directory in the Railway container. `/tmp` is ephemeral per container, which is fine — the timezone cache is a minor optimization that rebuilds quickly.

### 5. Reduce `expire_stale_approvals` Frequency

**File**: `api/src/margin_api/workers.py` — cron_jobs list

**Change**: From `hour={0, 6, 12, 18}` (4x daily) to `hour={0, 12}` (2x daily).

**Additional**: Add a Redis-based dedup guard using `SET expire_approvals_lock 1 NX EX 18000` (5h TTL). If the lock already exists, skip execution and log a warning. This detects the every-minute re-triggering seen in production logs. In-memory state won't work across container restarts.

**Rationale**: Approval expiration within a 12-hour window is adequate for a human-review pipeline. The every-minute behavior warrants investigation but is likely an ARQ misconfiguration or duplicate worker process.

## Files Modified

| File | Change |
|------|--------|
| `api/src/margin_api/workers.py` | All 5 fixes (price poll, retry, TzCache, approvals) |

## Testing Strategy

- **Unit tests** for `_record_fail()`: verify TTL set only on first failure, verify logging on exception
- **Unit tests** for `retry_quarantined()`: mock Redis scan + yfinance download, verify counter clearing on success
- **Unit tests** for `_download_batch()`: mock batch timeout scenario, verify no tickers penalized; mock partial success, verify only missing tickers penalized
- **Integration verification**: After deploy, monitor `live_price_poll` logs — skipped count should decrease from 2,867 over subsequent runs as `retry_quarantined` recovers tickers

## Success Criteria

1. `retry_quarantined` is implemented and runs every 6 hours
2. Batch-level failures no longer penalize individual tickers
3. `_record_fail()` TTL only set on first failure in window
4. yfinance TzCache warnings eliminated from logs
5. `expire_stale_approvals` runs 2x daily instead of 4x
6. Skipped ticker count in `live_price_poll` drops to near 0 on first run after deploy (bulk reset), then builds only from genuine per-ticker failures

## Risks

- **yfinance rate limiting**: `retry_quarantined` adds extra yfinance calls. Mitigated by 50-ticker cap and small batch sizes of 10.
- **Batch split retry**: Doubles yfinance calls on timeout. Mitigated by only retrying once and only on timeout (not other exceptions).
- **Redis SCAN performance**: Scanning for `price_fail:*` keys could be slow with many keys. Mitigated by using SCAN with `COUNT 500` hint (cursor-based, non-blocking) rather than KEYS.
- **Key-without-TTL leak**: If worker crashes between `INCR` (creating key) and `EXPIRE`, the key persists forever. Mitigated by TTL safety check on every `_record_fail()` call.
- **Bulk reset on deploy**: Clears all quarantine data, so genuinely bad tickers will be re-polled once before being re-quarantined. This is acceptable — one wasted poll per bad ticker is negligible cost for immediate recovery of ~2,800 good tickers.
