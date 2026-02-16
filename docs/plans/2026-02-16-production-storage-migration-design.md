# Production Storage Migration Design

**Date**: 2026-02-16
**Status**: Approved
**Scope**: Migrate Margin Invest from local-only storage to production-grade persistence supporting ~8,000 assets with intraday time-series.

---

## 1. Storage Architecture

### Platform Stack

| Component | Service | Rationale |
|---|---|---|
| Database | Timescale Cloud (managed TimescaleDB on PostgreSQL 16) | Hypertables auto-partition 5-min bars by time. Native compression (10-20x). Continuous aggregates auto-materialize daily OHLCV. Managed backups + point-in-time recovery. |
| API + Worker | Railway (Docker container) | Deploys existing `api/Dockerfile`. FastAPI + ARQ worker. Env-driven config. |
| Redis | Railway (managed Redis service) | Live price cache (10-min TTL) + ARQ job queue. Already implemented. |
| Frontend | Vercel (hobby tier) | Zero-config Next.js 15 deploys. API calls proxied via `next.config.js` rewrites. |
| Object Storage | Cloudflare R2 (already in use) | Avatars. Extend for backtest archives if needed. |

### Scale Profile

- **Intraday (5-min bars)**: ~1.57B rows over 10 years. TimescaleDB hypertable, 1-week chunks, compressed after 7 days. ~15-30GB on disk.
- **Daily bars**: Continuous aggregate from intraday. Zero manual maintenance.
- **Fundamentals**: ~320K rows over 10 years. Standard table.
- **Scores**: ~8K rows per scoring run. Low volume.

### Cost Estimate

| Service | Monthly |
|---|---|
| Timescale Cloud (dynamic compute + ~30GB storage) | $10-20 |
| Railway API container | $5-10 |
| Railway Redis | $5 |
| Vercel | $0 |
| Cloudflare R2 | ~$0 |
| **Total** | **$20-35** |

### Redis Justification

Redis stays lean with two existing uses:
- Live price cache with 10-min TTL (prevents hammering upstream providers during dashboard loads)
- ARQ job queue for async scoring/ingestion (critical for 8K ticker batch jobs)

No new Redis usage added.

---

## 2. Schema + Indexing + Partitioning

### New Tables

#### `prices_intraday` (TimescaleDB Hypertable)

5-minute price bars. The largest table by volume.

```sql
CREATE TABLE prices_intraday (
    time    TIMESTAMPTZ      NOT NULL,
    ticker  VARCHAR(10)      NOT NULL,
    open    DOUBLE PRECISION NOT NULL,
    high    DOUBLE PRECISION NOT NULL,
    low     DOUBLE PRECISION NOT NULL,
    close   DOUBLE PRECISION NOT NULL,
    volume  BIGINT,                        -- nullable: some instruments lack volume
    source  VARCHAR(50)      NOT NULL DEFAULT 'unknown'
);

SELECT create_hypertable('prices_intraday', 'time',
    chunk_time_interval => INTERVAL '1 week');

CREATE INDEX ix_prices_intraday_ticker_time
    ON prices_intraday (ticker, time DESC);

CREATE UNIQUE INDEX uq_prices_intraday_ticker_time
    ON prices_intraday (ticker, time);

ALTER TABLE prices_intraday SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ticker',
    timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('prices_intraday', INTERVAL '7 days');
```

#### `prices_daily` (Continuous Aggregate)

Auto-materialized from intraday. Never manually maintained.

```sql
CREATE MATERIALIZED VIEW prices_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS date,
    ticker,
    first(open, time)  AS open,
    max(high)           AS high,
    min(low)            AS low,
    last(close, time)   AS close,
    sum(volume)         AS volume
FROM prices_intraday
GROUP BY date, ticker
WITH NO DATA;

SELECT add_continuous_aggregate_policy('prices_daily',
    start_offset    => INTERVAL '3 days',
    end_offset      => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

CREATE INDEX ix_prices_daily_ticker_date
    ON prices_daily (ticker, date DESC);
```

Backtests and dashboards query `prices_daily`. Charting queries `prices_intraday`.

#### `metrics_derived`

Precomputed factor inputs (ratios, returns, growth rates). One row per asset per date.

```sql
CREATE TABLE metrics_derived (
    id              SERIAL PRIMARY KEY,
    asset_id        INTEGER          NOT NULL REFERENCES assets(id),
    as_of_date      DATE             NOT NULL,

    -- Quality factors
    roe             DOUBLE PRECISION,
    roic            DOUBLE PRECISION,
    gross_margin    DOUBLE PRECISION,
    debt_to_equity  DOUBLE PRECISION,

    -- Value factors
    pe_ratio        DOUBLE PRECISION,
    pb_ratio        DOUBLE PRECISION,
    ev_ebitda       DOUBLE PRECISION,
    fcf_yield       DOUBLE PRECISION,

    -- Momentum factors
    return_1m       DOUBLE PRECISION,
    return_3m       DOUBLE PRECISION,
    return_6m       DOUBLE PRECISION,
    return_12m      DOUBLE PRECISION,

    -- Overflow for new metrics without migration
    extra           JSONB,

    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_metrics_asset_date UNIQUE (asset_id, as_of_date)
);

CREATE INDEX ix_metrics_derived_date ON metrics_derived (as_of_date);
```

Wide table (not EAV) because dashboards need multiple metrics per ticker per request. The `extra` JSONB column provides escape-hatch flexibility.

#### `backtest_runs`

```sql
CREATE TABLE backtest_runs (
    id                   SERIAL PRIMARY KEY,
    name                 VARCHAR(255)   NOT NULL,
    universe_snapshot_id INTEGER        NOT NULL REFERENCES universe_snapshots(id),
    start_date           DATE           NOT NULL,
    end_date             DATE           NOT NULL,
    rebalance_frequency  VARCHAR(20)    NOT NULL,
    config               JSONB          NOT NULL,
    config_hash          VARCHAR(64)    NOT NULL,
    status               VARCHAR(20)    NOT NULL DEFAULT 'pending',
    total_return         DOUBLE PRECISION,
    annualized_return    DOUBLE PRECISION,
    sharpe_ratio         DOUBLE PRECISION,
    max_drawdown         DOUBLE PRECISION,
    summary_stats        JSONB,
    started_at           TIMESTAMPTZ,
    completed_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_backtest_runs_status ON backtest_runs (status);
```

#### `backtest_results`

Per-ticker, per-date scores within a backtest run.

```sql
CREATE TABLE backtest_results (
    id                   SERIAL PRIMARY KEY,
    run_id               INTEGER          NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    asset_id             INTEGER          NOT NULL REFERENCES assets(id),
    as_of_date           DATE             NOT NULL,
    signal               VARCHAR(20)      NOT NULL,
    conviction_level     VARCHAR(20)      NOT NULL,
    composite_percentile DOUBLE PRECISION NOT NULL,
    entry_price          DOUBLE PRECISION,
    exit_price           DOUBLE PRECISION,
    position_return      DOUBLE PRECISION,
    detail               JSONB,

    CONSTRAINT uq_backtest_result UNIQUE (run_id, asset_id, as_of_date)
);

CREATE INDEX ix_backtest_results_run_date ON backtest_results (run_id, as_of_date);
```

### Changes to Existing Tables

**`scores`** -- Add universe version linkage:

```sql
ALTER TABLE scores
    ADD COLUMN universe_snapshot_id INTEGER REFERENCES universe_snapshots(id);
```

**`ingestion_runs`** -- Add data type tracking:

```sql
ALTER TABLE ingestion_runs
    ADD COLUMN data_types JSONB NOT NULL DEFAULT '[]';
```

### Partitioning Strategy

| Table | Strategy | Details |
|---|---|---|
| `prices_intraday` | TimescaleDB hypertable | 1-week chunks. ~624K rows/week. Compressed after 7 days. |
| `prices_daily` | Continuous aggregate | Materialized from intraday, refreshed hourly. |
| `financial_data` | None | ~320K rows over 10 years. B-tree indexes sufficient. |
| `scores` | None | ~8K rows per run. Low volume. |
| `backtest_results` | None (revisit if needed) | Partition by `run_id` if volume grows to hundreds of backtests. |

### Constraint Summary (No Silent Null Drift)

- `prices_intraday`: open, high, low, close are `NOT NULL`. Volume nullable (documented: some instruments don't report it).
- `metrics_derived`: Metric columns nullable (not all tickers have all metrics). `asset_id` and `as_of_date` are `NOT NULL`.
- `backtest_runs`: `config`, `config_hash`, `universe_snapshot_id` are `NOT NULL`.
- `backtest_results`: `signal`, `conviction_level`, `composite_percentile` are `NOT NULL`.
- Unique constraints prevent duplicate price bars, metrics, and backtest results.

---

## 3. Migration Plan (Local to Production)

### Phase 1: Provision Infrastructure

1. **Timescale Cloud**: Create dynamic (consumption-based) service in `us-east-1`. PostgreSQL 16 + TimescaleDB. Database name: `margin_invest`.
2. **Railway**: Create project with three services -- API (from `api/Dockerfile`), Worker (same image, start command `arq margin_api.worker.WorkerSettings`), Redis (managed).
3. **Vercel**: Connect repo, root directory `web/`, framework preset Next.js.

### Phase 2: Run Schema Migrations

```bash
export MARGIN_DATABASE_URL="postgresql+asyncpg://tsdbadmin:<pw>@<host>:<port>/margin_invest?sslmode=require"
uv run alembic -c api/alembic.ini upgrade head
```

The new migration creates all new tables and executes TimescaleDB-specific DDL (hypertable, compression, continuous aggregate) via `op.execute()`.

### Phase 3: Export Local Data

```bash
pg_dump -U margin -d margin_invest \
  --data-only \
  --exclude-table=alembic_version \
  -F custom -f margin_invest_local_backup.dump
```

### Phase 4: Import to Production

```bash
pg_restore \
  --host=<TSDB_HOST> --port=<TSDB_PORT> \
  --username=tsdbadmin --dbname=margin_invest \
  --data-only --no-owner --no-privileges \
  margin_invest_local_backup.dump
```

Existing `financial_data.price_history` JSONB stays. New ingestion writes to `prices_intraday`.

### Phase 5: Validate

- Row count comparison (assets, financial_data, scores) between local and production
- Run `score --tickers AAPL MSFT` against production DB
- Start API and verify `/health` returns `{"status": "ok"}`

### Phase 6: Cut Over

1. Deploy API + Worker on Railway
2. Deploy frontend on Vercel
3. Verify production endpoints return data
4. Stop local Postgres
5. Keep local dump for 30 days

No downtime concern -- this is a first deploy, not a live migration.

---

## 4. Code Changes

### 4.1 `api/src/margin_api/config.py`

- Add connection pool settings: `db_pool_size` (5), `db_max_overflow` (10), `db_pool_timeout` (30), `db_pool_recycle` (1800), `db_pool_pre_ping` (True)
- Add `environment: str = "development"` field
- Keep localhost defaults (they work for local dev; production overrides via env)

### 4.2 `api/src/margin_api/db/session.py`

- Pass pool settings from config to `create_async_engine()`
- Add SSL context for `sslmode=require` connections (Timescale Cloud)
- Add `pool_pre_ping=True` for stale connection detection

### 4.3 `api/src/margin_api/db/models.py`

- Add `PriceIntraday`, `MetricsDerived`, `BacktestRun`, `BacktestResult` models
- Add `universe_snapshot_id` FK to `Score`
- Add `data_types` JSONB column to `IngestionRun`

### 4.4 Alembic Migration

- Standard table creates via autogenerate
- TimescaleDB DDL via `op.execute()` (hypertable, compression policy, continuous aggregate, refresh policy)
- Dialect-guarded: TimescaleDB DDL skipped on SQLite test environments

### 4.5 `api/src/margin_api/cli.py`

- Replace all `print()` with structured `logger.info/warning/error` calls
- Add `upsert_price_bars()`: batch `INSERT ... ON CONFLICT DO UPDATE` for `prices_intraday`
- Add `ingest_price_bars_batched()`: 1,000-row chunks with per-batch commit
- Configure stdlib logging in `main()` entrypoint

### 4.6 `api/src/margin_api/app.py`

- Add production localhost guard: raise `RuntimeError` if `environment=production` and `localhost` in DATABASE_URL
- Add `GET /health` endpoint (verifies DB connectivity)
- Add structured logging configuration at startup

### 4.7 `web/next.config.js`

- Add API rewrite: `/api/:path*` proxied to `NEXT_PUBLIC_API_URL/api/:path*`
- `apiFetch` client (relative URLs) works without changes

### 4.8 `docker-compose.yml`

- Fix env var prefix: `DATABASE_URL` changed to `MARGIN_DATABASE_URL` (matching `SettingsConfigDict(env_prefix="MARGIN_")`)
- Same for `REDIS_URL` to `MARGIN_REDIS_URL`
- Add `MARGIN_ENVIRONMENT: development`

### 4.9 New: `api/src/margin_api/services/ingestion.py`

- `with_retry()`: exponential backoff wrapper (3 attempts, 2s base, 60s cap)
- Used by all provider fetch calls

### 4.10 New: Ingestion API Endpoints

- `GET /api/v1/ingestion/status`: coverage %, fresh tickers, quarantined count, last run details
- `GET /api/v1/ingestion/completeness`: boolean `ready` flag with 90% threshold. Frontend uses this to show ingestion banner vs rankings.

### What Does NOT Change

- `engine/`: Pure Python scoring library. No DB awareness.
- `worker.py`: Already reads config from env. Pool settings flow through automatically.
- Test infrastructure: aiosqlite in-memory. TimescaleDB DDL guarded by dialect check.
- `web/src/lib/api/client.ts`: Already uses relative URLs.

---

## 5. Operational Requirements

### Ingestion Status Tracking

`GET /api/v1/ingestion/status` returns: universe version, total tickers, fresh tickers (data within 7 days), quarantined tickers, coverage percentage, and last run details (status, succeeded/failed counts, duration).

### Idempotent Ingestion

- **Fundamentals**: `UNIQUE(asset_id, period_end)` constraint. Upsert pattern (select, insert or update).
- **Prices**: `INSERT ... ON CONFLICT (ticker, time) DO UPDATE`. Safe to re-run.
- **Scores**: Skip guard prevents double-scoring within the same run.
- **Universe**: `config_hash` deduplicates. Re-activating same YAML is a no-op.

### Backoff/Retry

`with_retry()` wrapper: 3 attempts, exponential backoff (2s, 4s, 8s), 60s cap. Applied to all provider fetch calls.

**Quarantine policy**: 3 consecutive failures sets `Asset.ingestion_status = "quarantined"`. Quarantined assets skipped in normal runs. `unquarantine` CLI command retries after 24 hours.

### Batch Upserts

`ingest_price_bars_batched()`: inserts in 1,000-row chunks with per-batch commit. Prevents transaction memory bloat and allows Postgres checkpointing between batches.

### Completeness Gate

`GET /api/v1/ingestion/completeness` returns `{"ready": true/false}` based on 90% coverage threshold. Frontend checks this before rendering rankings. Below threshold: shows `IngestionBanner` with progress (e.g., "4,200 / 8,000 tickers scored (52.5%)"). Above threshold: renders rankings normally.

---

## 6. Deliverables + Actions Checklist

### Step 1: Create Timescale Cloud Service

1. Go to console.cloud.timescale.com
2. Create dynamic (consumption-based) service, `us-east-1`, database name `margin_invest`
3. Note: `TSDB_HOST`, `TSDB_PORT`, `TSDB_PASSWORD`

### Step 2: Create Railway Project

1. Create project with 3 services: API, Worker, Redis
2. API: GitHub repo, Dockerfile path `api/Dockerfile`
3. Worker: same repo/image, start command `arq margin_api.worker.WorkerSettings`
4. Redis: managed Redis service
5. Set environment variables on API + Worker:

```
MARGIN_DATABASE_URL=postgresql+asyncpg://tsdbadmin:<TSDB_PASSWORD>@<TSDB_HOST>:<TSDB_PORT>/margin_invest?sslmode=require
MARGIN_REDIS_URL=redis://default:<REDIS_PASSWORD>@<REDIS_HOST>:<REDIS_PORT>
MARGIN_ENVIRONMENT=production
MARGIN_JWT_SECRET=<openssl rand -hex 32>
MARGIN_MFA_ENCRYPTION_KEY=<python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
MARGIN_API_KEY_ENCRYPTION_KEY=<python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
MARGIN_CORS_ORIGINS=["https://<your-vercel-domain>"]
MARGIN_WEBAUTHN_RP_ID=<your-vercel-domain>
MARGIN_WEBAUTHN_RP_ORIGIN=https://<your-vercel-domain>
```

6. Generate public domain for API service

### Step 3: Create Vercel Project

1. Import repo, root directory `web`, framework Next.js
2. Set `NEXT_PUBLIC_API_URL=https://<railway-api-domain>`
3. Deploy, note Vercel domain
4. Update Railway CORS/WebAuthn vars with actual Vercel domain

### Step 4: Run Migrations

```bash
export MARGIN_DATABASE_URL="postgresql+asyncpg://tsdbadmin:<pw>@<host>:<port>/margin_invest?sslmode=require"
uv run alembic -c api/alembic.ini upgrade head
```

### Step 5: Export + Import Local Data

```bash
pg_dump -U margin -d margin_invest \
  --data-only --exclude-table=alembic_version \
  -F custom -f margin_invest_local_backup.dump

pg_restore \
  --host=<TSDB_HOST> --port=<TSDB_PORT> \
  --username=tsdbadmin --dbname=margin_invest \
  --data-only --no-owner --no-privileges \
  margin_invest_local_backup.dump
```

### Step 6: Seed + Score on Production

```bash
uv run python -m margin_api.cli universe activate
uv run python -m margin_api.cli seed --tickers AAPL MSFT NVDA GOOGL META
uv run python -m margin_api.cli score --tickers AAPL MSFT NVDA GOOGL META
uv run python -m margin_api.cli pipeline  # full universe
```

### Step 7: Verify

```bash
curl https://<railway-api>/health
curl https://<railway-api>/api/v1/ingestion/completeness
curl https://<railway-api>/api/v1/ingestion/status
curl https://<railway-api>/api/v1/scores
# Open https://<vercel-domain> in browser
```

### Step 8: Post-Deploy

- Keep local dump 30 days
- Stop local Postgres if desired
- Verify Railway auto-deploys on push to `main`

### Environment Variables Reference

| Variable | Dev (.env) | Production (Railway) |
|---|---|---|
| `MARGIN_DATABASE_URL` | `postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest` | `postgresql+asyncpg://tsdbadmin:<pw>@<host>:<port>/margin_invest?sslmode=require` |
| `MARGIN_REDIS_URL` | `redis://localhost:6379` | `redis://default:<pw>@<host>:<port>` |
| `MARGIN_ENVIRONMENT` | `development` | `production` |
| `MARGIN_JWT_SECRET` | `dev-secret-change-me` | `<openssl rand -hex 32>` |
| `MARGIN_CORS_ORIGINS` | `["http://localhost:3000"]` | `["https://<vercel-domain>"]` |

| Variable | Where | Value |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Vercel | `https://<railway-api-domain>` |
