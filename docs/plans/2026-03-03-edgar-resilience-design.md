# EDGAR Fetch Resilience Design

**Date**: 2026-03-03
**Status**: Approved

## Problem

`bootstrap_pit_data` crashes with `httpx.ReadTimeout` when fetching EDGAR quarter indices from SEC. The index-building phase has zero retry logic — a single timeout on any of ~68 quarter fetches kills the entire bootstrap. No partial progress is saved, so a restart refetches everything.

## Design

### 1. Retry Layer (tenacity)

Add `tenacity` retry decorators to all SEC-facing HTTP functions:

- **`fetch_quarter_index`**: Retry on `httpx.ReadTimeout`, `httpx.ConnectTimeout`, `httpx.HTTPStatusError` (5xx). Exponential backoff: 2s → 4s → 8s → 16s → 32s (5 attempts max) with jitter.
- **`fetch_and_parse_filing`**: Same retry profile. 4xx errors (bad accession, not transient) do not retry — fall through to return `None`.
- **`load_cik_ticker_map`**: Same retry profile as `fetch_quarter_index`.

### 2. Per-Quarter Index Caching

New DB table `edgar_index_cache`:

```
edgar_index_cache
  - id (PK)
  - year (int)
  - quarter (int)
  - entries_json (JSONB) — serialized list of EdgarIndexEntry dicts
  - entry_count (int)
  - fetched_at (DateTime(timezone=True))
  - UNIQUE(year, quarter)
```

`build_full_index` changes:
- Accept optional `session_factory` parameter
- For each year/quarter: check cache first
- Cache freshness: < 24 hours for current quarter, permanent for past quarters
- Fetch from SEC only if not cached, then persist to DB
- No `session_factory` (CLI usage) → fall back to current behavior (no caching)
- CIK ticker map also cached (same table or simple key-value row)

### 3. Adaptive Circuit Breaker

`ConsecutiveFailureTracker` — simple counter-based circuit breaker:

**Index phase**:
- Consecutive failure counter increments when a quarter fails all retries, resets to 0 on success
- Threshold: 3 consecutive failures (= 15 HTTP attempts with no success)
- On trip: raise `EdgarUnavailableError` with descriptive message
- `bootstrap_pit_data` catches it, marks job failed gracefully

**Filing phase**:
- 10 consecutive filing fetch failures → abort current chunk, move to next
- Prevents burning through thousands of doomed requests

No half-open state or timers — worker cron retries naturally on next run, per-quarter cache means it picks up where it left off.

### 4. Timeout Configuration

- Index fetches (`company.idx`): Default 60s (up from 30s — files are 2-5MB)
- Filing fetches (XBRL): Default 45s
- CIK ticker map: Default 30s
- Env var: `MARGIN_EDGAR_TIMEOUT=60` overrides all (single knob)

## Files Changed

| File | Change |
|------|--------|
| `edgar/index_builder.py` | tenacity retries, per-quarter DB caching, `ConsecutiveFailureTracker`, bumped timeouts |
| `edgar/backfill.py` | tenacity retry on `fetch_and_parse_filing`, consecutive-failure abort for filing chunks, configurable timeout |
| `db/models.py` | New `EdgarIndexCache` model |
| `workers.py` | Catch `EdgarUnavailableError` in `bootstrap_pit_data`, mark job failed gracefully |
| Alembic migration | Create `edgar_index_cache` table |
| `pyproject.toml` | Add `tenacity` to `margin-api` |

## Not Changing

- Existing checkpoint file logic in `run_edgar_backfill` — complements index cache (quarter-level vs filing-level resume)
- Rate limiter (`_RateLimiter`) — already working correctly at 8 req/sec
