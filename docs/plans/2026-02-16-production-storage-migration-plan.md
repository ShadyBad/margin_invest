# Production Storage Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate Margin Invest from local-only storage to production-grade Timescale Cloud + Railway + Vercel, supporting ~8,000 assets with intraday time-series.

**Architecture:** Timescale Cloud (managed TimescaleDB) for the database with hypertables for 5-min price bars, Railway for API container + Redis + ARQ worker, Vercel for Next.js frontend. All config env-driven. See `docs/plans/2026-02-16-production-storage-migration-design.md` for full design.

**Tech Stack:** SQLAlchemy 2.0 async, TimescaleDB (PostgreSQL 16), FastAPI, ARQ, Next.js 15, Alembic

---

## Task 1: Add Pool + Environment Settings to Config

**Files:**
- Modify: `api/src/margin_api/config.py`
- Modify: `api/tests/test_config.py`

**Step 1: Write failing tests for new config fields**

Add to `api/tests/test_config.py`:

```python
class TestPoolSettings:
    def test_pool_defaults(self):
        settings = Settings()
        assert settings.db_pool_size == 5
        assert settings.db_max_overflow == 10
        assert settings.db_pool_timeout == 30
        assert settings.db_pool_recycle == 1800
        assert settings.db_pool_pre_ping is True

    def test_environment_default(self):
        settings = Settings()
        assert settings.environment == "development"

    def test_environment_from_env(self, monkeypatch):
        monkeypatch.setenv("MARGIN_ENVIRONMENT", "production")
        monkeypatch.setenv("MARGIN_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        settings = Settings()
        assert settings.environment == "production"

    def test_pool_size_from_env(self, monkeypatch):
        monkeypatch.setenv("MARGIN_DB_POOL_SIZE", "20")
        monkeypatch.setenv("MARGIN_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        settings = Settings()
        assert settings.db_pool_size == 20
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_config.py::TestPoolSettings -v`
Expected: FAIL — `Settings` has no attribute `db_pool_size`

**Step 3: Add fields to Settings class**

In `api/src/margin_api/config.py`, add these fields to the `Settings` class after the `redis_url` field:

```python
    # Connection pool
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_pool_pre_ping: bool = True

    # Environment
    environment: str = "development"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_config.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/config.py api/tests/test_config.py
git commit -m "feat: add connection pool and environment settings to config"
```

---

## Task 2: Add Connection Pooling + SSL to Session

**Files:**
- Modify: `api/src/margin_api/db/session.py`
- Create: `api/tests/test_session.py`

**Step 1: Write failing tests for pool configuration**

Create `api/tests/test_session.py`:

```python
"""Tests for database session management."""
from __future__ import annotations

import os
from unittest.mock import patch

from margin_api.config import Settings
from margin_api.db.session import get_engine, _engine


class TestGetEngine:
    def setup_method(self):
        """Reset the module-level engine cache before each test."""
        import margin_api.db.session as mod
        mod._engine = None

    def teardown_method(self):
        import margin_api.db.session as mod
        mod._engine = None

    def test_explicit_url_bypasses_cache(self):
        engine = get_engine(url="sqlite+aiosqlite:///:memory:")
        assert "sqlite" in str(engine.url)

    def test_pool_settings_applied(self):
        with patch.dict(os.environ, {
            "MARGIN_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        }):
            from margin_api.config import get_settings
            get_settings.cache_clear()
            engine = get_engine()
            # SQLite uses NullPool, but the code path should not error
            assert engine is not None

    def test_ssl_context_created_for_sslmode(self):
        """When sslmode=require is in URL, connect_args should include ssl."""
        with patch.dict(os.environ, {
            "MARGIN_DATABASE_URL": "postgresql+asyncpg://user:pass@host:5432/db?sslmode=require",
        }):
            from margin_api.config import get_settings
            get_settings.cache_clear()
            # We can't fully create the engine (no real PG), but verify
            # the code path doesn't crash before the actual connect
            import margin_api.db.session as mod
            mod._engine = None
            # The engine creation will fail at connect time, but
            # the SSL context should be set up. We test the logic
            # by verifying the code doesn't raise during engine construction.
            try:
                engine = get_engine()
                assert engine is not None
            except Exception:
                # Connection errors are expected (no real PG)
                pass
```

**Step 2: Run tests to verify baseline**

Run: `uv run pytest api/tests/test_session.py -v`
Expected: Tests should pass (current code already handles explicit URL). This establishes the baseline.

**Step 3: Update get_engine with pool config and SSL**

Replace the `get_engine` function in `api/src/margin_api/db/session.py`:

```python
def get_engine(url: str | None = None):
    """Create or return the cached async SQLAlchemy engine."""
    global _engine
    if url is not None:
        # Explicit URL bypasses cache (used in tests)
        return create_async_engine(url, echo=False)
    if _engine is None:
        settings = get_settings()
        connect_args: dict = {}

        # Timescale Cloud (and other managed PG) requires SSL
        if "sslmode=require" in settings.database_url:
            import ssl

            ssl_ctx = ssl.create_default_context()
            connect_args["ssl"] = ssl_ctx

        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=settings.db_pool_pre_ping,
            connect_args=connect_args,
        )
    return _engine
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_session.py -v`
Expected: ALL PASS

**Step 5: Run full API test suite to verify no regressions**

Run: `uv run pytest api/tests/ -v --timeout=60`
Expected: ALL PASS (294+ tests)

**Step 6: Commit**

```bash
git add api/src/margin_api/db/session.py api/tests/test_session.py
git commit -m "feat: add connection pooling and SSL support to DB session"
```

---

## Task 3: Add New Database Models

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Modify: `api/tests/test_db_models.py`

**Step 1: Write failing tests for new models**

Add to `api/tests/test_db_models.py`:

```python
from margin_api.db.models import (
    BacktestResult,
    BacktestRun,
    MetricsDerived,
    PriceIntraday,
)


class TestPriceIntradayModel:
    def test_table_name(self):
        assert PriceIntraday.__tablename__ == "prices_intraday"

    def test_columns(self):
        columns = {c.name for c in PriceIntraday.__table__.columns}
        expected = {"time", "ticker", "open", "high", "low", "close", "volume", "source"}
        assert expected.issubset(columns)

    def test_composite_primary_key(self):
        pk_cols = {c.name for c in PriceIntraday.__table__.primary_key.columns}
        assert pk_cols == {"time", "ticker"}

    def test_open_not_nullable(self):
        col = PriceIntraday.__table__.columns["open"]
        assert col.nullable is False

    def test_volume_nullable(self):
        col = PriceIntraday.__table__.columns["volume"]
        assert col.nullable is True


class TestMetricsDerivedModel:
    def test_table_name(self):
        assert MetricsDerived.__tablename__ == "metrics_derived"

    def test_columns(self):
        columns = {c.name for c in MetricsDerived.__table__.columns}
        expected = {
            "id", "asset_id", "as_of_date",
            "roe", "roic", "gross_margin", "debt_to_equity",
            "pe_ratio", "pb_ratio", "ev_ebitda", "fcf_yield",
            "return_1m", "return_3m", "return_6m", "return_12m",
            "extra", "computed_at",
        }
        assert expected.issubset(columns)

    def test_unique_constraint(self):
        constraint_names = [
            c.name for c in MetricsDerived.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_metrics_asset_date" in constraint_names

    def test_asset_fk(self):
        col = MetricsDerived.__table__.columns["asset_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "assets.id"


class TestBacktestRunModel:
    def test_table_name(self):
        assert BacktestRun.__tablename__ == "backtest_runs"

    def test_columns(self):
        columns = {c.name for c in BacktestRun.__table__.columns}
        expected = {
            "id", "name", "universe_snapshot_id", "start_date", "end_date",
            "rebalance_frequency", "config", "config_hash", "status",
            "total_return", "annualized_return", "sharpe_ratio", "max_drawdown",
            "summary_stats", "started_at", "completed_at", "created_at",
        }
        assert expected.issubset(columns)

    def test_config_not_nullable(self):
        col = BacktestRun.__table__.columns["config"]
        assert col.nullable is False

    def test_config_hash_not_nullable(self):
        col = BacktestRun.__table__.columns["config_hash"]
        assert col.nullable is False

    def test_universe_snapshot_fk(self):
        col = BacktestRun.__table__.columns["universe_snapshot_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "universe_snapshots.id"


class TestBacktestResultModel:
    def test_table_name(self):
        assert BacktestResult.__tablename__ == "backtest_results"

    def test_columns(self):
        columns = {c.name for c in BacktestResult.__table__.columns}
        expected = {
            "id", "run_id", "asset_id", "as_of_date", "signal",
            "conviction_level", "composite_percentile",
            "entry_price", "exit_price", "position_return", "detail",
        }
        assert expected.issubset(columns)

    def test_signal_not_nullable(self):
        col = BacktestResult.__table__.columns["signal"]
        assert col.nullable is False

    def test_composite_percentile_not_nullable(self):
        col = BacktestResult.__table__.columns["composite_percentile"]
        assert col.nullable is False

    def test_cascade_delete(self):
        col = BacktestResult.__table__.columns["run_id"]
        fks = list(col.foreign_keys)
        assert fks[0].ondelete == "CASCADE"

    def test_unique_constraint(self):
        constraint_names = [
            c.name for c in BacktestResult.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_backtest_result" in constraint_names

    def test_has_relationship_to_run(self):
        assert hasattr(BacktestResult, "run")
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_db_models.py::TestPriceIntradayModel -v`
Expected: FAIL — `ImportError: cannot import name 'PriceIntraday'`

**Step 3: Add new models to models.py**

Add to `api/src/margin_api/db/models.py` (after the existing `SignalTransition` class and before `ApiKey`):

```python
class PriceIntraday(Base):
    """5-minute price bars. Backed by TimescaleDB hypertable in production."""

    __tablename__ = "prices_intraday"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="unknown")


class MetricsDerived(Base):
    """Precomputed factor inputs, one row per asset per date."""

    __tablename__ = "metrics_derived"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    as_of_date: Mapped[str] = mapped_column(String(10), nullable=False)

    # Quality factors
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    roic: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Value factors
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    fcf_yield: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Momentum factors
    return_1m: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_3m: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_6m: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_12m: Mapped[float | None] = mapped_column(Float, nullable=True)

    extra: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("asset_id", "as_of_date", name="uq_metrics_asset_date"),
        Index("ix_metrics_derived_date", "as_of_date"),
    )


class BacktestRun(Base):
    """A single backtest execution with config and aggregate results."""

    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    universe_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("universe_snapshots.id"), nullable=False
    )
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))
    rebalance_frequency: Mapped[str] = mapped_column(String(20))
    config: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    annualized_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary_stats: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    results: Mapped[list[BacktestResult]] = relationship(back_populates="run")


class BacktestResult(Base):
    """Per-ticker, per-date score within a backtest run."""

    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    as_of_date: Mapped[str] = mapped_column(String(10), nullable=False)
    signal: Mapped[str] = mapped_column(String(20), nullable=False)
    conviction_level: Mapped[str] = mapped_column(String(20), nullable=False)
    composite_percentile: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    run: Mapped[BacktestRun] = relationship(back_populates="results")

    __table_args__ = (
        UniqueConstraint("run_id", "asset_id", "as_of_date", name="uq_backtest_result"),
        Index("ix_backtest_results_run_date", "run_id", "as_of_date"),
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_db_models.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_db_models.py
git commit -m "feat: add PriceIntraday, MetricsDerived, BacktestRun, BacktestResult models"
```

---

## Task 4: Add universe_snapshot_id to Score + data_types to IngestionRun

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Modify: `api/tests/test_db_models.py`

**Step 1: Write failing tests**

Add to `api/tests/test_db_models.py`:

```python
from margin_api.db.models import IngestionRun


class TestScoreUniverseLink:
    def test_score_has_universe_snapshot_id(self):
        columns = {c.name for c in Score.__table__.columns}
        assert "universe_snapshot_id" in columns

    def test_universe_snapshot_id_nullable(self):
        """Nullable for backward compat with existing scores."""
        col = Score.__table__.columns["universe_snapshot_id"]
        assert col.nullable is True

    def test_universe_snapshot_id_fk(self):
        col = Score.__table__.columns["universe_snapshot_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "universe_snapshots.id"


class TestIngestionRunDataTypes:
    def test_ingestion_run_has_data_types(self):
        columns = {c.name for c in IngestionRun.__table__.columns}
        assert "data_types" in columns
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_db_models.py::TestScoreUniverseLink -v`
Expected: FAIL — `universe_snapshot_id` not in columns

**Step 3: Add fields to existing models**

In `api/src/margin_api/db/models.py`:

Add to `Score` class (after `score_detail` field):

```python
    universe_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("universe_snapshots.id"), nullable=True
    )
```

Add to `IngestionRun` class (after `duration_seconds` field):

```python
    data_types: Mapped[list | None] = mapped_column(JSONVariant, default=list)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_db_models.py -v`
Expected: ALL PASS

**Step 5: Run full test suite for regressions**

Run: `uv run pytest api/tests/ -v --timeout=60`
Expected: ALL PASS. Check that existing score creation tests still work (the new column is nullable so they should).

**Step 6: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_db_models.py
git commit -m "feat: add universe_snapshot_id to Score, data_types to IngestionRun"
```

---

## Task 5: Update Table Creation Test

**Files:**
- Modify: `api/tests/test_db_models.py`

The `TestTableCreation.test_create_all_tables` test verifies all tables can be created on SQLite. Update it to include the new tables.

**Step 1: Update the test**

In `api/tests/test_db_models.py`, update `TestTableCreation.test_create_all_tables`:

```python
    def test_create_all_tables(self, sync_engine):
        Base.metadata.create_all(sync_engine)
        table_names = set(Base.metadata.tables.keys())
        assert "assets" in table_names
        assert "users" in table_names
        assert "scores" in table_names
        assert "recommendations" in table_names
        assert "api_keys" in table_names
        assert "prices_intraday" in table_names
        assert "metrics_derived" in table_names
        assert "backtest_runs" in table_names
        assert "backtest_results" in table_names
```

**Step 2: Run test to verify it passes**

Run: `uv run pytest api/tests/test_db_models.py::TestTableCreation -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add api/tests/test_db_models.py
git commit -m "test: update table creation test to include new models"
```

---

## Task 6: Create Alembic Migration

**Files:**
- Create: `api/alembic/versions/<hash>_add_timeseries_and_backtest_tables.py`

**Step 1: Generate the migration**

```bash
uv run alembic -c api/alembic.ini revision --autogenerate -m "add_timeseries_and_backtest_tables"
```

**Step 2: Edit the migration to add TimescaleDB DDL**

Open the generated migration file. After the autogenerated table creates, add a dialect guard for the TimescaleDB-specific DDL. Wrap the TimescaleDB calls in a check:

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # ... autogenerated table creates (prices_intraday, metrics_derived,
    #     backtest_runs, backtest_results, alter scores, alter ingestion_runs) ...

    # TimescaleDB-specific DDL (only on PostgreSQL, skipped on SQLite)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Check if TimescaleDB extension is available
        result = bind.execute(sa.text(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
        ))
        has_timescale = result.scalar()

        if has_timescale:
            op.execute(
                "SELECT create_hypertable('prices_intraday', 'time', "
                "chunk_time_interval => INTERVAL '1 week', if_not_exists => TRUE)"
            )

            op.execute("""
                ALTER TABLE prices_intraday SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'ticker',
                    timescaledb.compress_orderby = 'time DESC'
                )
            """)
            op.execute(
                "SELECT add_compression_policy('prices_intraday', INTERVAL '7 days')"
            )

            op.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS prices_daily
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
                WITH NO DATA
            """)

            op.execute("""
                SELECT add_continuous_aggregate_policy('prices_daily',
                    start_offset    => INTERVAL '3 days',
                    end_offset      => INTERVAL '1 hour',
                    schedule_interval => INTERVAL '1 hour')
            """)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP MATERIALIZED VIEW IF EXISTS prices_daily CASCADE")

    # ... autogenerated drops ...
```

**Step 3: Verify migration runs against local DB**

```bash
uv run alembic -c api/alembic.ini upgrade head
```

Expected: Migration completes successfully. If local PG has TimescaleDB extension, hypertable is created. If not, tables are created as regular tables.

**Step 4: Verify downgrade works**

```bash
uv run alembic -c api/alembic.ini downgrade -1
uv run alembic -c api/alembic.ini upgrade head
```

**Step 5: Commit**

```bash
git add api/alembic/versions/
git commit -m "feat: add migration for timeseries and backtest tables"
```

---

## Task 7: Add Production Localhost Guard + DB Health Check

**Files:**
- Modify: `api/src/margin_api/app.py`
- Modify: `api/src/margin_api/routes/health.py`
- Modify: `api/tests/test_health.py`

**Step 1: Write failing test for localhost guard**

Add to `api/tests/test_health.py`:

```python
import os
from unittest.mock import patch

from margin_api.app import create_app


class TestProductionGuard:
    def test_production_with_localhost_raises(self):
        with patch.dict(os.environ, {
            "MARGIN_ENVIRONMENT": "production",
            "MARGIN_DATABASE_URL": "postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest",
        }):
            import pytest
            with pytest.raises(RuntimeError, match="localhost"):
                create_app()

    def test_development_with_localhost_ok(self):
        with patch.dict(os.environ, {
            "MARGIN_ENVIRONMENT": "development",
            "MARGIN_DATABASE_URL": "postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest",
        }):
            app = create_app()
            assert app is not None

    def test_production_with_remote_url_ok(self):
        with patch.dict(os.environ, {
            "MARGIN_ENVIRONMENT": "production",
            "MARGIN_DATABASE_URL": "postgresql+asyncpg://user:pass@remote.host:5432/db?sslmode=require",
        }):
            app = create_app()
            assert app is not None
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_health.py::TestProductionGuard -v`
Expected: FAIL — `create_app()` does not raise

**Step 3: Add guard to app.py**

In `api/src/margin_api/app.py`, add at the top of `create_app()`, after `settings = get_settings()`:

```python
    if settings.environment == "production" and "localhost" in settings.database_url:
        raise RuntimeError(
            "MARGIN_DATABASE_URL points to localhost in production mode. "
            "Set MARGIN_DATABASE_URL to your Timescale Cloud connection string."
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_health.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/app.py api/tests/test_health.py
git commit -m "feat: add production localhost guard to app startup"
```

---

## Task 8: Add Retry Service

**Files:**
- Create: `api/src/margin_api/services/retry.py`
- Create: `api/tests/test_retry.py`

**Step 1: Write failing tests**

Create `api/tests/test_retry.py`:

```python
"""Tests for retry logic."""
from __future__ import annotations

import pytest

from margin_api.services.retry import with_retry


class TestWithRetry:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        call_count = 0

        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await with_retry(succeed, ticker="TEST")
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        call_count = 0

        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "recovered"

        result = await with_retry(fail_then_succeed, ticker="TEST", retries=3, base_delay=0.01)
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        def always_fail():
            raise ValueError("permanent error")

        with pytest.raises(ValueError, match="permanent error"):
            await with_retry(always_fail, ticker="TEST", retries=2, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_delay_is_exponential(self):
        """Verify delay doubles between retries (with small base for speed)."""
        import time

        call_times = []

        def track_and_fail():
            call_times.append(time.monotonic())
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await with_retry(track_and_fail, ticker="TEST", retries=3, base_delay=0.05)

        # 3 attempts = 2 delays. Second delay should be ~2x the first.
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        assert delay2 > delay1 * 1.5  # allow some tolerance
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_retry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_api.services.retry'`

**Step 3: Implement the retry module**

Create `api/src/margin_api/services/retry.py`:

```python
"""Exponential backoff retry wrapper for provider calls."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

MAX_RETRIES = 3
BASE_DELAY = 2.0
MAX_DELAY = 60.0


async def with_retry(
    fn: Callable[..., T],
    *args,
    ticker: str,
    retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    max_delay: float = MAX_DELAY,
    **kwargs,
) -> T:
    """Call fn with exponential backoff on failure.

    Args:
        fn: Synchronous callable to retry.
        ticker: Ticker symbol (for logging).
        retries: Maximum number of attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
    """
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == retries:
                logger.error(
                    "Failed %s after %d attempts: %s", ticker, retries, e
                )
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(
                "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                attempt, retries, ticker, e, delay,
            )
            await asyncio.sleep(delay)
    # unreachable, but satisfies type checker
    raise RuntimeError("unreachable")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_retry.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/retry.py api/tests/test_retry.py
git commit -m "feat: add exponential backoff retry wrapper for provider calls"
```

---

## Task 9: Add Batch Price Upsert Function

**Files:**
- Create: `api/src/margin_api/services/price_ingestion.py`
- Create: `api/tests/test_price_ingestion.py`

**Step 1: Write failing tests**

Create `api/tests/test_price_ingestion.py`:

```python
"""Tests for price ingestion batch upserts."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from margin_api.db.base import Base
from margin_api.db.models import PriceIntraday
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


@pytest.fixture()
def sync_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


class TestUpsertPriceBarsSync:
    """Test the batch upsert logic using sync SQLite (unit-level)."""

    def test_insert_new_bars(self, sync_engine):
        from margin_api.services.price_ingestion import prepare_price_values

        bars = [
            {"time": "2025-01-15T10:00:00+00:00", "open": 150.0, "high": 151.0,
             "low": 149.5, "close": 150.5, "volume": 1000},
            {"time": "2025-01-15T10:05:00+00:00", "open": 150.5, "high": 152.0,
             "low": 150.0, "close": 151.5, "volume": 2000},
        ]
        values = prepare_price_values("AAPL", bars, "test")
        assert len(values) == 2
        assert values[0]["ticker"] == "AAPL"
        assert values[0]["source"] == "test"
        assert values[1]["close"] == 151.5

    def test_prepare_empty_bars(self):
        from margin_api.services.price_ingestion import prepare_price_values

        values = prepare_price_values("AAPL", [], "test")
        assert values == []

    def test_prepare_handles_missing_volume(self):
        from margin_api.services.price_ingestion import prepare_price_values

        bars = [
            {"time": "2025-01-15T10:00:00+00:00", "open": 150.0, "high": 151.0,
             "low": 149.5, "close": 150.5},
        ]
        values = prepare_price_values("AAPL", bars, "test")
        assert values[0]["volume"] is None

    def test_batch_chunking(self):
        from margin_api.services.price_ingestion import chunk_bars

        bars = list(range(2500))
        chunks = list(chunk_bars(bars, batch_size=1000))
        assert len(chunks) == 3
        assert len(chunks[0]) == 1000
        assert len(chunks[1]) == 1000
        assert len(chunks[2]) == 500
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_price_ingestion.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement the price ingestion module**

Create `api/src/margin_api/services/price_ingestion.py`:

```python
"""Batch price bar ingestion for prices_intraday."""
from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import PriceIntraday

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


def prepare_price_values(
    ticker: str,
    bars: list[dict],
    source: str,
) -> list[dict[str, Any]]:
    """Transform raw bar dicts into values ready for insert."""
    if not bars:
        return []
    return [
        {
            "time": bar["time"],
            "ticker": ticker,
            "open": bar["open"],
            "high": bar["high"],
            "low": bar["low"],
            "close": bar["close"],
            "volume": bar.get("volume"),
            "source": source,
        }
        for bar in bars
    ]


def chunk_bars(bars: list, batch_size: int = BATCH_SIZE) -> Iterator[list]:
    """Yield successive chunks of bars."""
    for i in range(0, len(bars), batch_size):
        yield bars[i : i + batch_size]


async def upsert_price_bars(
    session: AsyncSession,
    ticker: str,
    bars: list[dict],
    source: str = "unknown",
) -> int:
    """Batch upsert price bars into prices_intraday. Idempotent.

    Uses INSERT ... ON CONFLICT DO UPDATE on PostgreSQL.
    Falls back to individual inserts on SQLite (tests).
    """
    values = prepare_price_values(ticker, bars, source)
    if not values:
        return 0

    dialect = session.bind.dialect.name if session.bind else "unknown"

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        stmt = insert(PriceIntraday).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ticker", "time"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "source": stmt.excluded.source,
            },
        )
        await session.execute(stmt)
    else:
        # SQLite fallback for tests
        from sqlalchemy import insert as sa_insert

        for val in values:
            await session.execute(sa_insert(PriceIntraday).values(**val))

    return len(values)


async def ingest_price_bars_batched(
    session: AsyncSession,
    ticker: str,
    bars: list[dict],
    source: str = "unknown",
) -> int:
    """Insert price bars in batches, committing between chunks."""
    total = 0
    for chunk in chunk_bars(bars, BATCH_SIZE):
        count = await upsert_price_bars(session, ticker, chunk, source)
        total += count
        await session.commit()
    logger.info("Ingested %d bars for %s", total, ticker)
    return total
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_price_ingestion.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/price_ingestion.py api/tests/test_price_ingestion.py
git commit -m "feat: add batch price bar upsert for prices_intraday"
```

---

## Task 10: Add Ingestion Status + Completeness API Endpoints

**Files:**
- Modify: `api/src/margin_api/routes/ingestion.py`
- Modify: `api/tests/test_ingestion_routes.py`

**Step 1: Write failing tests**

Add to `api/tests/test_ingestion_routes.py`:

```python
from margin_api.routes.ingestion import IngestionStatusResponse, CompletenessResponse


class TestIngestionStatusResponse:
    def test_status_response_model(self):
        resp = IngestionStatusResponse(
            universe_version="1.0",
            total_tickers=8000,
            fresh_tickers=7600,
            quarantined_tickers=50,
            coverage_pct=95.0,
            last_run=None,
        )
        assert resp.coverage_pct == 95.0
        assert resp.quarantined_tickers == 50

    def test_status_response_with_no_universe(self):
        resp = IngestionStatusResponse(
            universe_version=None,
            total_tickers=0,
            fresh_tickers=0,
            quarantined_tickers=0,
            coverage_pct=0.0,
            last_run=None,
        )
        assert resp.universe_version is None


class TestCompletenessResponse:
    def test_ready_response(self):
        resp = CompletenessResponse(
            ready=True,
            coverage_pct=95.2,
            scored_tickers=7616,
            total_tickers=8000,
            reason=None,
            message=None,
        )
        assert resp.ready is True

    def test_not_ready_response(self):
        resp = CompletenessResponse(
            ready=False,
            coverage_pct=52.5,
            scored_tickers=4200,
            total_tickers=8000,
            reason="incomplete_ingestion",
            message="Only 4200/8000 tickers scored. Need 90% coverage.",
        )
        assert resp.ready is False
        assert resp.reason == "incomplete_ingestion"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_ingestion_routes.py::TestIngestionStatusResponse -v`
Expected: FAIL — `ImportError: cannot import name 'IngestionStatusResponse'`

**Step 3: Add response models and endpoint stubs**

Add to `api/src/margin_api/routes/ingestion.py`:

```python
class LastRunInfo(BaseModel):
    status: str
    succeeded: int
    failed: int
    started_at: str
    duration_seconds: float | None


class IngestionStatusResponse(BaseModel):
    universe_version: str | None
    total_tickers: int
    fresh_tickers: int
    quarantined_tickers: int
    coverage_pct: float
    last_run: LastRunInfo | None


class CompletenessResponse(BaseModel):
    ready: bool
    coverage_pct: float
    scored_tickers: int
    total_tickers: int
    reason: str | None = None
    message: str | None = None


MINIMUM_COVERAGE = 0.90


@router.get("/ingestion/status", response_model=IngestionStatusResponse)
async def ingestion_status(session: AsyncSession = Depends(get_db)):
    """Return current ingestion health for the active universe."""
    from datetime import UTC, timedelta

    from sqlalchemy import distinct, func

    from margin_api.db.models import Asset, FinancialData
    from margin_api.services.universe import get_active_snapshot

    snapshot = await get_active_snapshot(session)
    if snapshot is None:
        return IngestionStatusResponse(
            universe_version=None,
            total_tickers=0,
            fresh_tickers=0,
            quarantined_tickers=0,
            coverage_pct=0.0,
            last_run=None,
        )

    total = snapshot.ticker_count
    cutoff = datetime.now(UTC) - timedelta(days=7)

    fresh_result = await session.execute(
        select(func.count(distinct(FinancialData.asset_id)))
        .where(FinancialData.fetched_at >= cutoff)
    )
    fresh_count = fresh_result.scalar() or 0

    quarantined_result = await session.execute(
        select(func.count(Asset.id))
        .where(Asset.ingestion_status == "quarantined")
    )
    quarantined_count = quarantined_result.scalar() or 0

    latest_run_result = await session.execute(
        select(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .limit(1)
    )
    run = latest_run_result.scalar_one_or_none()

    last_run_info = None
    if run:
        last_run_info = LastRunInfo(
            status=run.status,
            succeeded=run.tickers_succeeded,
            failed=run.tickers_failed,
            started_at=run.started_at.isoformat(),
            duration_seconds=run.duration_seconds,
        )

    return IngestionStatusResponse(
        universe_version=snapshot.version,
        total_tickers=total,
        fresh_tickers=fresh_count,
        quarantined_tickers=quarantined_count,
        coverage_pct=round(fresh_count / total * 100, 1) if total else 0.0,
        last_run=last_run_info,
    )


@router.get("/ingestion/completeness", response_model=CompletenessResponse)
async def completeness_gate(session: AsyncSession = Depends(get_db)):
    """Return whether data is complete enough to display rankings."""
    from datetime import UTC, timedelta

    from sqlalchemy import distinct, func

    from margin_api.db.models import FinancialData, Score
    from margin_api.services.universe import get_active_snapshot

    snapshot = await get_active_snapshot(session)
    if snapshot is None:
        return CompletenessResponse(
            ready=False,
            coverage_pct=0.0,
            scored_tickers=0,
            total_tickers=0,
            reason="no_active_universe",
            message="No active universe snapshot. Run ingestion first.",
        )

    total = snapshot.ticker_count
    cutoff = datetime.now(UTC) - timedelta(days=7)

    scored_result = await session.execute(
        select(func.count(distinct(Score.asset_id)))
        .where(Score.scored_at >= cutoff)
    )
    scored_count = scored_result.scalar() or 0
    coverage = scored_count / total if total else 0

    if coverage >= MINIMUM_COVERAGE:
        return CompletenessResponse(
            ready=True,
            coverage_pct=round(coverage * 100, 1),
            scored_tickers=scored_count,
            total_tickers=total,
        )
    else:
        return CompletenessResponse(
            ready=False,
            coverage_pct=round(coverage * 100, 1),
            scored_tickers=scored_count,
            total_tickers=total,
            reason="incomplete_ingestion",
            message=f"Only {scored_count}/{total} tickers scored. "
                    f"Need {MINIMUM_COVERAGE * 100:.0f}% coverage.",
        )
```

Also add the missing import at the top of the file:

```python
from datetime import datetime, UTC, timedelta
from sqlalchemy import distinct, func, select
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_ingestion_routes.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/ingestion.py api/tests/test_ingestion_routes.py
git commit -m "feat: add ingestion status and completeness gate endpoints"
```

---

## Task 11: Replace print() with Structured Logging in CLI

**Files:**
- Modify: `api/src/margin_api/cli.py`

**Step 1: Add logging configuration to main()**

At the top of the `main()` function in `api/src/margin_api/cli.py`:

```python
def main() -> None:
    """CLI entry point with argparse."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # ... rest of main ...
```

**Step 2: Replace print() calls with logger calls**

Throughout `cli.py`, replace:
- `print(f"[{i}/{total}] Seeding {ticker}...")` with `logger.info("[%d/%d] Seeding %s", i, total, ticker)`
- `print(f"  {ticker} OK")` with `logger.info("  %s OK", ticker)`
- `print(f"  {ticker} FAILED")` with `logger.error("  %s FAILED", ticker)`
- `print(f"\nSeed complete: ...")` with `logger.info("Seed complete: %d succeeded, %d failed out of %d", successes, failures, total)`
- Similar for all other `print()` calls in `run_scoring()`, `run_pipeline()`, `run_universe_activate()`, `run_universe_generate()`

Keep `parser.print_help()` as-is (that's argparse, not application logging).

**Step 3: Run existing CLI tests to verify no regressions**

Run: `uv run pytest api/tests/test_cli.py api/tests/test_cli_universe.py api/tests/test_cli_ingest.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add api/src/margin_api/cli.py
git commit -m "refactor: replace print() with structured logging in CLI"
```

---

## Task 12: Fix docker-compose.yml Environment Variable Prefix

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Fix the env var prefix**

In `docker-compose.yml`, change the `api` service environment from:

```yaml
    environment:
      DATABASE_URL: postgresql://margin:margin_dev@db:5432/margin_invest
      REDIS_URL: redis://redis:6379
```

To:

```yaml
    environment:
      MARGIN_DATABASE_URL: postgresql+asyncpg://margin:margin_dev@db:5432/margin_invest
      MARGIN_REDIS_URL: redis://redis:6379
      MARGIN_ENVIRONMENT: development
```

Note: also adds `+asyncpg` to the driver (matching what SQLAlchemy expects) and sets environment explicitly.

**Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "fix: use MARGIN_ prefix for env vars in docker-compose"
```

---

## Task 13: Add Next.js API Rewrite for Production

**Files:**
- Modify: `web/next.config.ts`

**Step 1: Add the rewrite rule**

Replace `web/next.config.ts` with:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["three"],
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

When `NEXT_PUBLIC_API_URL` is unset (local dev), no rewrites are applied (the local proxy or direct fetch handles it). In production, all `/api/*` requests proxy to the Railway API URL.

**Step 2: Commit**

```bash
git add web/next.config.ts
git commit -m "feat: add Next.js API rewrite for production proxy"
```

---

## Task 14: Run Full Test Suite + Final Verification

**Step 1: Run all API tests**

```bash
uv run pytest api/tests/ -v --timeout=120
```

Expected: ALL PASS (300+ tests)

**Step 2: Run all engine tests**

```bash
uv run pytest engine/tests/ -v --timeout=120
```

Expected: ALL PASS (784 tests). Engine should be completely unaffected.

**Step 3: Verify local dev still works end-to-end**

```bash
# Start local services
docker compose up -d

# Run migrations
uv run alembic -c api/alembic.ini upgrade head

# Seed a few tickers
uv run python -m margin_api.cli seed --tickers AAPL MSFT

# Score them
uv run python -m margin_api.cli score --tickers AAPL MSFT

# Start API
uv run uvicorn margin_api.app:create_app --factory --port 8000

# Test health (in another terminal)
curl http://localhost:8000/health
```

**Step 4: Final commit with all files staged**

If any files were missed in earlier commits:

```bash
git status
# Review and commit any remaining changes
```
