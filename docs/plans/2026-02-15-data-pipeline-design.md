# Data Pipeline Design — Deterministic, Production-Grade

**Date:** 2026-02-15
**Status:** Approved

## Overview

Replace the current manual, 50-ticker CLI pipeline with a production-grade system that ingests the full US equity universe (~5000 tickers), tracks completeness, and enforces determinism at every layer.

### Global Principles

- Default behavior = full universe. Subset requires explicit `--tickers` flag.
- No silent fallbacks. No silent skipping. No partial data without indication.
- All ingestion runs logged. Universe version always tracked.
- Web app reflects ingestion completeness at all times.

### Key Decisions

| Decision | Choice |
|----------|--------|
| Universe size | All US equities (~5000), excluding financials and REITs |
| Universe source | yfinance screener + persist to versioned YAML config |
| Universe storage | Approach A: Universe-as-Config (YAML in git + DB snapshots) |
| CLI interface | Python (`uv run`), not pnpm |
| Data providers | Multi-provider architecture, ship with yfinance only |
| Scheduling | ARQ + Redis background job queue |
| Incomplete data UX | Banner warning + full functionality with available data |
| Backtesting | Automatic validation after each scoring cycle (not user-triggered) |

---

## 1. Universe Definition System

### Config File

`engine/universe.yaml` — checked into the repo, version-controlled via git.

```yaml
version: "2026.02.15"
description: "US equities, excluding financials and REITs"
source: "yfinance_screener"
generated_at: "2026-02-15T12:00:00Z"

exclusions:
  sectors:
    - "Financial Services"
    - "Real Estate"
  min_market_cap: 300_000_000
  min_avg_volume: 1_000_000

tickers:
  - AAPL
  - MSFT
  - NVDA
  # ... ~5000 entries
```

### CLI Commands

```bash
# Refresh universe from yfinance screener → overwrites universe.yaml
uv run python -m margin_api.cli universe refresh

# Activate: hash the YAML, create universe_snapshots row in DB
uv run python -m margin_api.cli universe activate

# Show current universe status
uv run python -m margin_api.cli universe status
```

### Flow

1. `universe refresh` — queries yfinance screener for all US equities, applies exclusion filters, writes `universe.yaml`
2. Developer reviews diff, commits to git
3. `universe activate` — reads `universe.yaml`, computes SHA-256 hash, inserts `universe_snapshots` row
4. All subsequent `ingest` and `score` commands reference the active snapshot

### DB Table: `universe_snapshots`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `version` | String | From YAML `version` field |
| `config_hash` | String(64) | SHA-256 of universe.yaml content |
| `ticker_count` | Integer | Number of tickers in this snapshot |
| `tickers` | JSONB | Full ticker list as JSON array |
| `exclusion_rules` | JSONB | Sector exclusions, min market cap, etc. |
| `is_active` | Boolean | Only one active at a time |
| `activated_at` | DateTime(tz) | When activated |

### Enforcement

`ingest` and `score` commands refuse to run if no active snapshot exists. Hard error: "No active universe snapshot. Run 'universe activate' first."

---

## 2. Stale Data Caching Policy

### Freshness Tiers

Scores use `scored_at` to compute freshness. The API computes and returns the tier — the frontend reacts to the string.

| Tier | Score Age | Behavior |
|------|-----------|----------|
| `fresh` | < 18 hours | Normal display. Scored after the most recent market close. |
| `stale` | 18h - 3 calendar days | Show score + "Updated Xh ago" badge, slightly muted. Directionally correct but may have drifted. |
| `expired` | > 3 calendar days | Exclude from rankings. Placeholder: "Score data expired. Re-scoring in progress." |

### Rationale

- **18 hours**: Tied to market close (4 PM ET). Score at 5 PM Monday is fresh until 11 AM Tuesday.
- **3 calendar days**: Covers a weekend gap. Beyond 2 trading days, price-dependent factors (momentum, EV/FCF, margin of safety) have drifted enough to mislead.
- **No 7-day window**: A week-old buy signal at $142 is dangerous if the stock is now at $165.

---

## 3. Live Price Polling for Recommended Candidates

### Scope

Only tickers with `conviction_level` in `[exceptional, high]` or `signal` in `[buy, hold, sell, urgent_sell]`. Typically 10-30 tickers.

### Cadence

| Window | Frequency | Rationale |
|--------|-----------|-----------|
| Market hours (9:30 AM - 4:00 PM ET) | Every 5 minutes | yfinance handles 30 tickers in a single batch call. |
| Pre/post market | No polling | Extended hours pricing unreliable for signal decisions. |
| Weekends/holidays | No polling | Markets closed. |

### Architecture

```
ARQ background task (every 5 min during market hours)
    → yfinance batch price fetch (30 tickers, ~1 API call)
    → Write to Redis: live_prices:{ticker} → {price, updated_at}

API reads:
    1. Check Redis for live_prices:{ticker}
    2. If exists and < 10 min old → use as actual_price, price_source = "live"
    3. Else → fall back to scores.actual_price, price_source = "daily_close"
```

### Signal Recalculation

- `buy_price`, `sell_price`, `intrinsic_value` are fixed (from daily scoring)
- Only `actual_price` changes with live data
- Signal recomputed on-the-fly: compare live `actual_price` vs stored targets
- Does NOT re-run the full scoring pipeline, update momentum factors, or affect composite_percentile/conviction_level

### API Response Fields

```json
{
  "actual_price": 141.50,
  "price_source": "live",
  "price_updated_at": "2026-02-15T14:35:00Z",
  "signal": "buy"
}
```

---

## 4. Ingestion Layer

### Unified CLI Command

Replaces the current separate `seed` and `score` commands.

```bash
uv run python -m margin_api.cli ingest                    # Full universe + score
uv run python -m margin_api.cli ingest --tickers AAPL,MSFT  # Explicit subset
uv run python -m margin_api.cli ingest --skip-scoring     # Ingest only
uv run python -m margin_api.cli score                     # Score only (existing data)
```

### Default Behavior Enforcement

- `ingest` with no flags reads the active universe snapshot
- No active snapshot → hard error (not silent fallback to old 50-ticker list)
- `--tickers` is the only way to run a subset

### DB Table: `ingestion_runs`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `snapshot_id` | FK → universe_snapshots | Which universe version |
| `run_type` | String | `"full"` or `"subset"` |
| `tickers_requested` | Integer | How many tickers in this run |
| `tickers_succeeded` | Integer | Successfully ingested |
| `tickers_failed` | Integer | Failed with errors |
| `tickers_skipped` | Integer | Skipped (already fresh) |
| `failed_tickers` | JSONB | `[{"ticker": "XYZ", "error": "..."}]` |
| `status` | String | `"running"` / `"completed"` / `"failed"` / `"cancelled"` |
| `started_at` | DateTime(tz) | Run start |
| `completed_at` | DateTime(tz) | Run end (null if running) |
| `duration_seconds` | Float | Wall clock time |

### DB Table: `ingestion_ticker_status`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `run_id` | FK → ingestion_runs | Which run |
| `ticker` | String | Ticker symbol |
| `status` | String | `"pending"` / `"ingesting"` / `"succeeded"` / `"failed"` |
| `error_message` | Text | Null on success |
| `data_fetched` | JSONB | `{"fundamentals": true, "prices": true, "earnings": false}` |
| `duration_ms` | Integer | Per-ticker fetch time |
| `started_at` | DateTime(tz) | |
| `completed_at` | DateTime(tz) | |

### Idempotency

- Ticker successfully ingested within last 24 hours → skip with status `"skipped"`
- `--force` flag overrides and re-fetches everything
- Keyed on `(ticker, date)` — same as existing `(asset_id, period_end)` unique constraint

### Concurrency

- Configurable worker count (default: 4 concurrent tickers)
- Respects rate limiter per provider (existing `RateLimiterRegistry`)
- asyncio semaphore to cap concurrent yfinance requests

### CLI Report

```
Ingestion complete (universe v2026.02.15):
  Total:     4,847
  Succeeded: 4,812 (99.3%)
  Failed:    23 (0.5%)
  Skipped:   12 (0.2% — already fresh)

Failed tickers:
  XYZW — ConnectionTimeout: yfinance rate limit exceeded
  ABCD — ValueError: No financial data available

Run ID: 47 | Duration: 2h 14m
```

---

## 5. Progressive Failure Policy

### Error Classification

| Error Type | Examples | Behavior |
|------------|----------|----------|
| **Transient** | Network timeout, rate limit (429), server error (503) | Retry next run. Does NOT count toward consecutive failures. |
| **Data unavailable** | No financial statements, empty response, parsing failure | Counts toward consecutive failure escalation. |
| **Permanent** | Ticker not found / delisted / merged | Immediately mark as `permanently_skipped`. |

### Escalation Ladder

| Stage | Trigger | Behavior |
|-------|---------|----------|
| **Active** | Default state | Ingested every run |
| **Quarantined** | 3 consecutive data-unavailable failures across separate runs | Retried once per week. Frees up daily capacity. |
| **Permanently skipped** | 3 additional weekly retries fail (6 total consecutive failures) | Removed from active ingestion. Only retried on `--force` or universe refresh. |

### Rationale

- **3 to quarantine**: Industry standard (Bloomberg, FactSet). 3 days rules out transient provider issues.
- **6 to permanently skip**: 3 daily + 3 weekly = ~24 calendar days. If no data after a month, it won't appear.

### New Columns on `assets` Table

| Column | Type | Description |
|--------|------|-------------|
| `ingestion_status` | String | `"active"` / `"quarantined"` / `"permanently_skipped"` |
| `consecutive_failures` | Integer | Resets to 0 on success |
| `last_failure_reason` | Text | Most recent error message |
| `quarantined_at` | DateTime(tz) | When quarantine started |
| `last_retry_at` | DateTime(tz) | When last weekly retry was attempted |

### Recovery

- Any successful ingestion resets `consecutive_failures` to 0 and `ingestion_status` to `"active"`
- `universe refresh` resets all permanently skipped tickers (new version = fresh start)
- Manual override: `uv run python -m margin_api.cli ingest --reset-status TICKER`

---

## 6. Database Integrity & Universe Completeness

### Universe Completeness Model

```python
class UniverseStatus(BaseModel):
    universe_version: str
    universe_size: int
    assets_ingested: int
    assets_scored: int
    assets_fresh: int               # scored < 18h ago
    assets_stale: int               # scored 18h-3d ago
    assets_expired: int             # scored > 3d ago
    assets_quarantined: int
    assets_permanently_skipped: int
    ingestion_coverage: float       # assets_ingested / universe_size
    scoring_coverage: float
    last_ingestion_run: datetime
    last_scoring_run: datetime
    is_complete: bool               # both coverages >= 0.95
```

### Completeness Threshold

`is_complete = true` when ingestion and scoring coverage are both >= 95%. Accounts for permanently skipped / quarantined tickers. 100% is unrealistic with 5000+ tickers on a free provider.

### Pre-flight Checks

| Operation | Check | Failure |
|-----------|-------|---------|
| `ingest` | Active universe snapshot exists | Hard error |
| `score` | >= 50 assets with fresh financial data | Hard error |
| `backtest_validate` | Scoring coverage >= 80% | Hard error |
| Dashboard API | None (always serves available data) | Returns UniverseStatus alongside data |

### Integrity Constraints

- `assets.ticker` unique
- `financial_data.(asset_id, period_end)` unique
- `scores.(asset_id, scored_at)` indexed
- New index: `assets.ingestion_status` for fast filtering
- FK cascade: deleting an asset cascades to financial_data, scores, signal_transitions

---

## 7. API Contract (Universe-Aware)

### New Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/universe/status` | GET | Full UniverseStatus model |
| `/api/v1/ingestion/runs` | GET | Paginated run history with failure details |
| `/api/v1/jobs/latest` | GET | Most recent job of each type (pipeline health) |
| `/api/v1/jobs/{id}` | GET | Specific job detail |

### Modified Endpoints

**`GET /api/v1/dashboard`** — add `universe` and `warnings` fields:

```json
{
  "picks": [],
  "watchlist": [],
  "last_updated": "2026-02-15T16:45:00Z",
  "total_scored": 4790,
  "universe": {
    "version": "2026.02.15",
    "size": 4847,
    "scoring_coverage": 0.988,
    "is_complete": true,
    "last_scoring_run": "2026-02-15T16:45:00Z"
  },
  "warnings": []
}
```

**`GET /api/v1/scores/{ticker}`** — add per-ticker metadata:

```json
{
  "ticker": "AAPL",
  "data_freshness": "fresh",
  "scored_at": "2026-02-15T16:45:00Z",
  "actual_price": 141.50,
  "price_source": "live",
  "price_updated_at": "2026-02-15T14:35:00Z",
  "ingestion_status": "complete",
  "universe_version": "2026.02.15"
}
```

### Warning Responses

| Scoring Coverage | Severity | Message |
|-----------------|----------|---------|
| >= 95% | None | No warning |
| 50-95% | `"warning"` | "Rankings based on X% of universe. Results may shift." |
| < 50% | `"error"` | "Universe coverage too low for reliable rankings." |

---

## 8. Web App Integration

### Ingestion Status Banner

Displayed at top of dashboard when `universe.is_complete === false`:

| Coverage | Style | Message |
|----------|-------|---------|
| >= 95% | No banner | — |
| 50-95% | Yellow warning | "Data ingestion in progress — X% of universe scored. Rankings may shift." |
| < 50% | Red alert | "Universe coverage too low for reliable rankings. Ingestion in progress." |

Dismissible but reappears on page reload if condition persists.

### Per-Card Freshness Indicators

| `data_freshness` | Treatment |
|-------------------|-----------|
| `fresh` | Normal rendering |
| `stale` | Muted border + "Updated Xh ago" badge |
| `expired` | Excluded from picks grid. Placeholder if accessed directly. |

### Live Price Indicator

During market hours when `price_source === "live"`:
- Small green dot next to price
- Action pill recalculates with live price

### New TypeScript Types

```typescript
interface UniverseSummary {
  version: string
  size: number
  scoring_coverage: number
  is_complete: boolean
  last_scoring_run: string
}

interface Warning {
  code: string
  message: string
  severity: "warning" | "error"
}

interface DashboardResponse {
  picks: PickSummary[]
  watchlist: WatchlistItem[]
  last_updated: string
  total_scored: number
  universe: UniverseSummary
  warnings?: Warning[]
}

interface PickSummary {
  // ... existing fields ...
  data_freshness: "fresh" | "stale" | "expired"
  scored_at: string
  actual_price: number | null
  price_source: "live" | "daily_close"
  price_updated_at: string | null
  ingestion_status: "complete" | "processing" | "failed" | "pending"
}
```

No new pages. Universe status lives in the dashboard banner.

---

## 9. Backtesting (Automatic Validation)

### Role

Backtesting is a system validation mechanism, not a user tool. It runs automatically after each full scoring cycle and surfaces methodology health.

### Flow

```
full_score completes
    → backtest_validate triggered (ARQ chained job)
    → runs predefined validation: rolling 1-year, monthly rebalance, top 10 picks
    → stores result with universe_version
    → if Sharpe < 0.5 or max drawdown > 30% → methodology_health = "degraded"
```

### Pre-flight Checks

| Check | Threshold | Failure |
|-------|-----------|---------|
| Scoring coverage | >= 80% | Hard error |
| Price history for date range | >= 90% of scored tickers | Hard error |
| Universe version | Must resolve | Hard error |

### Result Metadata

```python
class BacktestResult(BaseModel):
    id: int
    universe_version: str
    scoring_coverage_at_run: float
    tickers_included: int
    tickers_excluded_reason: dict
    start_date: date
    end_date: date
    rebalance_frequency: str
    created_at: datetime
    methodology_health: str  # "passing" | "degraded"
```

### Reproducibility

- Operates on stored `financial_data` and `scores` only — never fetches live data
- `universe_version` + `scored_at` pins the exact data used
- Re-running with same parameters produces identical results

### Web

`/backtesting` page is read-only — shows latest automatic validation results and methodology health status.

---

## 10. Background Job Queue (ARQ + Redis)

### Job Types

| Job | Trigger | Cadence | Duration |
|-----|---------|---------|----------|
| `full_ingest` | Daily schedule or CLI | 4:30 PM ET daily | 2-4 hours |
| `full_score` | Chained after ingest | After ingestion | 15-30 min |
| `backtest_validate` | Chained after score | After scoring | 5-10 min |
| `live_price_poll` | Recurring market hours | Every 5 min | < 5 seconds |
| `retry_quarantined` | Weekly schedule | Sundays midnight | 10-30 min |
| `universe_refresh` | CLI-triggered only | Manual | 1-2 min |

### Daily Pipeline Chain

```
4:30 PM ET: full_ingest
    → on success: full_score
    → on success: backtest_validate
    → on success: pipeline complete, last_scoring_run updated
    → on failure at any stage: pipeline halted, status = "failed"
      Previous day's scores remain active (stale tier kicks in)
```

### DB Table: `job_runs`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | Auto-increment |
| `job_type` | String | Job type identifier |
| `status` | String | `"queued"` / `"running"` / `"completed"` / `"failed"` / `"cancelled"` |
| `progress` | Float | 0.0 - 1.0 |
| `progress_detail` | String | "Ingesting ticker 2,180 of 4,847" |
| `triggered_by` | String | `"schedule"` / `"cli"` / `"chained"` |
| `parent_job_id` | FK → job_runs (nullable) | For chained jobs |
| `error_message` | Text | Null on success |
| `started_at` | DateTime(tz) | |
| `completed_at` | DateTime(tz) | |

### ARQ Worker Configuration

```python
class WorkerSettings:
    redis_settings = RedisSettings(host="localhost", port=6379)
    functions = [full_ingest, full_score, backtest_validate, live_price_poll, retry_quarantined]
    cron_jobs = [
        cron(full_ingest, hour=16, minute=30, tz="US/Eastern"),
        cron(live_price_poll, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
             run_at_startup=False),
        cron(retry_quarantined, weekday=6, hour=0),
    ]
```

### CLI Integration

```bash
uv run python -m margin_api.cli ingest              # Enqueue (returns immediately)
uv run python -m margin_api.cli ingest --sync        # Run synchronously (debugging)
uv run python -m margin_api.cli jobs                 # List recent jobs
uv run python -m margin_api.cli jobs --id 47         # Job detail
uv run python -m margin_api.cli jobs --cancel 47     # Cancel running job
```

### Infrastructure

- Redis (already in docker-compose.yml, currently unused)
- ARQ worker process: `uv run arq margin_api.workers.WorkerSettings`

---

## Summary of Changes

### New DB Tables (4)

| Table | Purpose |
|-------|---------|
| `universe_snapshots` | Versioned universe definitions |
| `ingestion_runs` | Per-run metadata and coverage stats |
| `ingestion_ticker_status` | Per-ticker per-run success/failure detail |
| `job_runs` | ARQ job tracking with progress |

### Modified Tables (1)

| Table | New Columns |
|-------|------------|
| `assets` | `ingestion_status`, `consecutive_failures`, `last_failure_reason`, `quarantined_at`, `last_retry_at` |

### New API Endpoints (4)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/universe/status` | GET | Universe completeness |
| `/api/v1/ingestion/runs` | GET | Run history |
| `/api/v1/jobs/latest` | GET | Pipeline health |
| `/api/v1/jobs/{id}` | GET | Job detail |

### New CLI Commands

| Command | Purpose |
|---------|---------|
| `universe refresh` | Screener → update universe.yaml |
| `universe activate` | YAML → snapshot in DB |
| `universe status` | Print current state |
| `ingest` | Enqueue full ingestion (replaces `seed`) |
| `ingest --sync` | Synchronous mode |
| `ingest --tickers X,Y` | Explicit subset |
| `jobs` / `jobs --id N` / `jobs --cancel N` | Job management |

### New Config Files

| File | Purpose |
|------|---------|
| `engine/universe.yaml` | Versioned universe definition (~5000 tickers) |

### Infrastructure

| Component | Status |
|-----------|--------|
| Redis | Already in docker-compose.yml, needs activation |
| ARQ worker | New process to run alongside the API |
