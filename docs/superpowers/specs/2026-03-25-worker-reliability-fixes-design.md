# Worker Reliability Fixes — Design Spec

**Date:** 2026-03-25
**Status:** Approved
**Scope:** Three production issues observed in Railway worker logs

---

## Problem Statement

Three issues identified from production logs (2026-03-25 02:30–03:30 UTC):

1. **`live_price_poll` timing out every run** — Every 15-min cron invocation hits the 900s ARQ timeout. With 3046 tickers at 100/batch and 60s per-batch timeout, the job can't complete before being killed. The existing "abort after 3 consecutive empty batches" guard doesn't trigger because batches hang (timeout) rather than returning empty.

2. **`publish_scores` race condition** — `_stage_scores_impl` sets `approval.status = "approved"` for auto-approved scores, then enqueues `publish_scores`. But `_publish_scores_impl` rejects anything not in `"staged"` status. Result: scores are auto-approved but never published.

3. **Delisted ticker log noise** — Tickers like TGNA and RAPT generate repeated WARNING-level log lines on every poll cycle before hitting the 5-failure quarantine threshold.

---

## Fix 1: Market-Hours Gating + Elapsed-Time Budget

### 1a: Market-Hours Gating

Add a market-hours check at the top of `live_price_poll`, after the stale-cron guard.

**File:** `api/src/margin_api/workers.py`

**Logic:**
- Use `zoneinfo.ZoneInfo("America/New_York")` (stdlib, zero dependencies)
- Market window: weekdays, 09:15–16:15 ET (15-min buffer around 9:30 open / 4:00 close)
- Weekends: skip entirely
- No holiday calendar — yfinance returns stale data on holidays, which is harmless; the time budget (1b) protects against hangs

```python
from zoneinfo import ZoneInfo
from datetime import time

_ET = ZoneInfo("America/New_York")

def _is_market_hours() -> bool:
    now_et = datetime.now(_ET)
    if now_et.weekday() >= 5:  # Sat/Sun
        return False
    return time(9, 15) <= now_et.time() <= time(16, 15)
```

At the top of `live_price_poll`, after the `_is_stale_cron` check:
```python
if not _is_market_hours():
    return {"status": "skipped_market_closed", "updated": 0}
```

**Impact:** Eliminates ~75% of daily runs (nights + weekends). The cron still fires every 15 min but returns instantly when markets are closed.

### 1b: Elapsed-Time Budget

Add a wall-clock cap to the batch download loop.

**Logic:**
- Budget: 600 seconds (10 minutes)
- Leaves 300s headroom before the 900s ARQ timeout
- Check `time.monotonic()` at the top of each batch iteration
- Log a WARNING when aborting early
- Count remaining tickers as failed in the return dict

```python
import time as _time

budget_seconds = 600
start_wall = _time.monotonic()

try:
    updated = 0
    failed = 0
    consecutive_empty_batches = 0
    max_consecutive_empty = 3
    for i in range(0, len(eligible), batch_size):
        # Time budget check — BEFORE downloading the batch
        elapsed = _time.monotonic() - start_wall
        if elapsed >= budget_seconds:
            remaining = len(eligible) - i
            logger.warning(
                "[prices] Time budget exhausted (%.0fs/%.0fs), "
                "aborting with %d tickers remaining",
                elapsed, budget_seconds, remaining,
            )
            failed += remaining
            break

        batch = eligible[i : i + batch_size]
        batch_ok = await _download_batch(batch)
        updated += batch_ok
        failed += len(batch) - batch_ok

        # Existing empty-batch guard (unchanged)
        if batch_ok == 0:
            consecutive_empty_batches += 1
            if consecutive_empty_batches >= max_consecutive_empty:
                # ... abort logic unchanged
                break
        else:
            consecutive_empty_batches = 0
```

**Complementary to existing guards:** The "3 consecutive empty batches" early-exit catches "Yahoo is down" (empty results). The time budget catches "Yahoo is slow" (hanging batches). Both remain active.

---

## Fix 2: `publish_scores` Status Check

### Problem

In `_stage_scores_impl` (line 977), the auto-approve path sets:
```python
approval.status = "approved"
```

Then `stage_scores` enqueues `publish_scores`. But `_publish_scores_impl` (line 1401) checks:
```python
if approval.status != "staged":
    return {"status": "error", "message": "not in staged status"}
```

The approval is `"approved"`, not `"staged"`, so publish is rejected.

### Fix

Change line 1401 in `_publish_scores_impl`:

```python
# Before
if approval.status != "staged":
    return {"status": "error", "message": "not in staged status"}

# After
if approval.status not in ("staged", "approved"):
    return {"status": "error", "message": f"unexpected status: {approval.status}"}
```

**Why accept "approved":** The auto-approve flow correctly records the approval decision (decided_at, decision_reason). `publish_scores` just needs to flip `V4Score.published = True` — it doesn't need the approval to still be in "staged" state. The guard should only reject genuinely unexpected states like "expired" or "rejected".

The existing `approval.status = "approved"` assignment on line 1420 becomes a no-op for auto-approved approvals, which is harmless. Note: `"approved"` is the terminal state for the approval record — there is no separate `"published"` status. The approval tracks the *decision*, while `V4Score.published` tracks whether scores are live. These are intentionally decoupled.

---

## Fix 3: Delisted Ticker Noise Reduction

### 3a: Lower Quarantine Threshold

Change `max_consecutive_fails` from 5 to 3. Tickers that are genuinely delisted get quarantined 2 cycles sooner.

Promote to a module-level constant for clarity and reuse across all three locations that currently hardcode `5`:

```python
MAX_PRICE_FAIL_COUNT = 3
```

**All locations to update:**
1. `live_price_poll` line 3039: `max_consecutive_fails = 5` → use `MAX_PRICE_FAIL_COUNT`
2. `retry_quarantined` line 3256: `max_consecutive_fails = 5` → use `MAX_PRICE_FAIL_COUNT`
3. `retry_quarantined` docstring (line 3243): update "5+ consecutive failures" → "3+"
4. `_record_fail`: reference `MAX_PRICE_FAIL_COUNT` for log-level thresholds

### 3b: Tiered Log Levels

In `_record_fail`, change from WARNING on every count to:
- **WARNING** on count == 1 (first failure — noteworthy)
- **DEBUG** on intermediate counts (noise reduction)
- **WARNING** on count >= threshold (quarantine event — noteworthy)

Pass `max_fails` as a parameter to `_record_fail`, or reference the module-level constant.

```python
async def _record_fail(redis_client, ticker: str) -> None:
    key = f"price_fail:{ticker}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, 86400)
            logger.warning("price_fail:%s count=%d", ticker, count)
        elif count >= MAX_PRICE_FAIL_COUNT:
            logger.warning("price_fail:%s reached quarantine threshold (count=%d)", ticker, count)
        else:
            # Safety: orphaned key TTL check
            ttl = await redis_client.ttl(key)
            if ttl == -1:
                await redis_client.expire(key, 86400)
            logger.debug("price_fail:%s count=%d", ticker, count)
    except Exception:
        logger.debug("Redis error in _record_fail for %s", ticker, exc_info=True)
```

---

## Testing Strategy

All fixes are in `api/src/margin_api/workers.py`. Tests:

1. **Market-hours gating:** Unit test `_is_market_hours()` with mocked datetimes (weekday in-hours, weekday out-of-hours, weekend). Test that `live_price_poll` returns `skipped_market_closed` when out of hours.

2. **Time budget:** Test with a mock `_download_batch` that sleeps, verify the loop aborts and logs correctly after budget is exceeded.

3. **Publish status check:** Existing test infrastructure for `_publish_scores_impl` — add a case where `approval.status == "approved"` and verify it proceeds instead of erroring. **Update existing test** `test_rejects_non_staged_approval` (if it asserts that "approved" is rejected) to reflect the new accepted states.

4. **Fail threshold + log levels:** Test `_record_fail` with counts 1, 2, 3 and verify log levels. Verify `retry_quarantined` uses the same `MAX_PRICE_FAIL_COUNT` constant.

---

## Files Changed

| File | Change |
|------|--------|
| `api/src/margin_api/workers.py` | All fixes — market-hours gate, time budget, publish status check, fail threshold, log levels |
| `api/tests/` | New/updated tests for the above |

## Risk Assessment

- **Market-hours gating:** Low risk. Worst case: a few minutes of stale prices at market open/close, mitigated by the 15-min buffer.
- **Time budget:** Low risk. Partial results are better than no results (timeout). Prices that weren't fetched remain at their previous cached value in Redis.
- **Publish fix:** Low risk. One-line guard change. The approval state machine is preserved — we just accept an additional valid state.
- **Fail threshold:** Minimal risk. Slightly more aggressive quarantine. 24h TTL resets guarantee retries.
