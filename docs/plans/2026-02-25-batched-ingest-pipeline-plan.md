# Batched Ingest Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the monolithic `full_ingest` (which times out at 5 hours on a 17-hour workload) with an orchestrator that enqueues fixed-size batch jobs running 3-at-a-time, coordinated via Redis.

**Architecture:** A cron-triggered `orchestrate_ingest` job chunks ~3,000 tickers into batches of 50 and enqueues ~60 `ingest_batch` jobs. ARQ's `max_jobs=3` runs 3 concurrently. A Redis sliding-window rate limiter coordinates API pacing. A Redis atomic counter tracks batch completion. A sweep job catches missed tickers. Scoring chains after sweep.

**Tech Stack:** Python 3.13, ARQ, Redis, SQLAlchemy 2.0 + asyncpg, yfinance

---

### Task 1: Add Config Variables for Batched Ingest

Three new settings control batch behavior. Add them to the existing `Settings` class.

**Files:**
- Modify: `api/src/margin_api/config.py:68` (after ML settings block)

**Step 1: Write the failing test**

Create `api/tests/test_batched_ingest_config.py`:

```python
"""Tests for batched ingest configuration variables."""

from __future__ import annotations

from margin_api.config import Settings


class TestBatchedIngestConfig:
    def test_default_batch_size(self):
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            _env_file=None,
        )
        assert s.ingest_batch_size == 50

    def test_default_rate_limit(self):
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            _env_file=None,
        )
        assert s.ingest_rate_limit == 36

    def test_default_ingest_concurrency(self):
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            _env_file=None,
        )
        assert s.ingest_concurrency == 3

    def test_custom_values(self, monkeypatch):
        monkeypatch.setenv("MARGIN_INGEST_BATCH_SIZE", "100")
        monkeypatch.setenv("MARGIN_INGEST_RATE_LIMIT", "24")
        monkeypatch.setenv("MARGIN_INGEST_CONCURRENCY", "2")
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            _env_file=None,
        )
        assert s.ingest_batch_size == 100
        assert s.ingest_rate_limit == 24
        assert s.ingest_concurrency == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_batched_ingest_config.py -v`
Expected: FAIL — `Settings` has no attribute `ingest_batch_size`

**Step 3: Write minimal implementation**

In `api/src/margin_api/config.py`, add after line 72 (`vae_enable: bool = True`):

```python
    # Batched ingest
    ingest_batch_size: int = 50
    ingest_rate_limit: int = 36
    ingest_concurrency: int = 3
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_batched_ingest_config.py -v`
Expected: All 4 PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/config.py api/tests/test_batched_ingest_config.py
git commit -m "feat(config): add batched ingest settings (batch_size, rate_limit, concurrency)"
```

---

### Task 2: Create Redis Rate Limiter

A sliding-window rate limiter backed by Redis. Same `async acquire()` interface as the engine's `RateLimiter` so providers can use either.

**Files:**
- Create: `api/src/margin_api/services/redis_rate_limiter.py`
- Test: `api/tests/test_redis_rate_limiter.py`

**Step 1: Write the failing test**

Create `api/tests/test_redis_rate_limiter.py`:

```python
"""Tests for Redis-backed sliding window rate limiter."""

from __future__ import annotations

import asyncio
import time

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from margin_api.services.redis_rate_limiter import RedisRateLimiter


@pytest_asyncio.fixture()
async def redis():
    """Connect to local Redis for integration tests."""
    r = Redis.from_url("redis://localhost:6379", decode_responses=True)
    yield r
    # Cleanup test keys
    keys = [k async for k in r.scan_iter("ratelimit:test:*")]
    if keys:
        await r.delete(*keys)
    await r.aclose()


class TestRedisRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_under_limit(self, redis):
        limiter = RedisRateLimiter(redis, max_per_minute=10, key_prefix="ratelimit:test")
        acquired = await limiter.acquire()
        assert acquired is True

    @pytest.mark.asyncio
    async def test_acquire_at_limit_blocks(self, redis):
        limiter = RedisRateLimiter(redis, max_per_minute=2, key_prefix="ratelimit:test")
        # Exhaust the limit
        await limiter.acquire()
        await limiter.acquire()
        # Third call should indicate rate limited
        acquired = await limiter.acquire()
        assert acquired is False

    @pytest.mark.asyncio
    async def test_wait_and_acquire_blocks_then_succeeds(self, redis):
        limiter = RedisRateLimiter(redis, max_per_minute=60, key_prefix="ratelimit:test")
        # Exhaust all tokens in this 1-second window
        for _ in range(60):
            await limiter.acquire()
        # wait_and_acquire should sleep then succeed
        start = time.monotonic()
        await limiter.wait_and_acquire()
        elapsed = time.monotonic() - start
        # Should have waited ~1 second for the next window
        assert elapsed >= 0.5

    @pytest.mark.asyncio
    async def test_different_prefixes_are_independent(self, redis):
        limiter_a = RedisRateLimiter(redis, max_per_minute=1, key_prefix="ratelimit:test:a")
        limiter_b = RedisRateLimiter(redis, max_per_minute=1, key_prefix="ratelimit:test:b")
        assert await limiter_a.acquire() is True
        assert await limiter_b.acquire() is True
        # Both exhausted independently
        assert await limiter_a.acquire() is False
        assert await limiter_b.acquire() is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_redis_rate_limiter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_api.services.redis_rate_limiter'`

**Step 3: Write minimal implementation**

Create `api/src/margin_api/services/redis_rate_limiter.py`:

```python
"""Redis-backed sliding window rate limiter for cross-job API throttling."""

from __future__ import annotations

import asyncio
import time

from redis.asyncio import Redis


class RedisRateLimiter:
    """Sliding window rate limiter backed by Redis.

    Uses per-second window keys with atomic INCR to coordinate rate limiting
    across multiple concurrent ARQ jobs sharing the same Redis instance.

    Implements the same interface as ``margin_engine.ingestion.rate_limiter.RateLimiter``
    so providers can accept either via duck typing.
    """

    def __init__(
        self,
        redis: Redis,
        max_per_minute: int = 36,
        key_prefix: str = "ratelimit:yfinance",
    ) -> None:
        self._redis = redis
        self._max_per_minute = max_per_minute
        self._max_per_second = max_per_minute / 60.0
        self._key_prefix = key_prefix

    def _window_key(self) -> tuple[str, float]:
        """Return (redis_key, seconds_remaining_in_window) for the current 1-second window."""
        now = time.time()
        window = int(now)
        key = f"{self._key_prefix}:{window}"
        remaining = 1.0 - (now - window)
        return key, remaining

    async def acquire(self) -> bool:
        """Try to acquire a rate limit token.

        Returns True if acquired, False if the current window is exhausted.
        """
        key, remaining = self._window_key()
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, 5)  # auto-cleanup; 5s is generous for a 1s window
        if count <= self._max_per_second:
            return True
        # Over limit — decrement back since we won't use this slot
        await self._redis.decr(key)
        return False

    async def wait_and_acquire(self) -> None:
        """Block (async sleep) until a token is available, then acquire it."""
        while True:
            key, remaining = self._window_key()
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, 5)
            if count <= self._max_per_second:
                return  # acquired
            # Over limit — decrement and wait for next window
            await self._redis.decr(key)
            await asyncio.sleep(remaining + 0.05)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_redis_rate_limiter.py -v`
Expected: All 4 PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/redis_rate_limiter.py api/tests/test_redis_rate_limiter.py
git commit -m "feat(api): add Redis-backed sliding window rate limiter"
```

---

### Task 3: Create `orchestrate_ingest` Job

This job replaces `full_ingest` as the cron entry point. It loads the universe, chunks tickers into batches, sets Redis coordination keys, and enqueues `ingest_batch` jobs.

**Files:**
- Modify: `api/src/margin_api/workers.py` (add new function after `full_ingest`)
- Test: `api/tests/test_orchestrate_ingest.py`

**Step 1: Write the failing test**

Create `api/tests/test_orchestrate_ingest.py`:

```python
"""Tests for orchestrate_ingest worker job."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOrchestrateIngest:
    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_enqueues_batches(self, mock_engine, mock_factory):
        from margin_api.workers import orchestrate_ingest

        # Mock universe snapshot with 120 tickers
        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "1.0"
        mock_snapshot.tickers = [f"T{i:03d}" for i in range(120)]

        mock_session = AsyncMock()
        mock_factory_inst = MagicMock()
        mock_factory_inst.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory_inst.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_factory_inst

        # Mock get_active_snapshot
        with patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot):
            # Mock _load_foreign_skips
            with patch("margin_api.workers._load_foreign_skips", return_value=set()):
                # Mock Redis
                mock_redis = AsyncMock()
                ctx = {"redis": mock_redis}

                # Patch settings for batch_size=50
                with patch("margin_api.workers.get_settings") as mock_settings:
                    mock_settings.return_value.ingest_batch_size = 50
                    result = await orchestrate_ingest(ctx)

        assert result["status"] == "dispatched"
        assert result["total_batches"] == 3  # ceil(120 / 50) = 3
        assert result["total_tickers"] == 120
        # Should enqueue 3 ingest_batch jobs
        assert mock_redis.enqueue_job.call_count == 3
        # Each call should be to "ingest_batch"
        for call in mock_redis.enqueue_job.call_args_list:
            assert call[0][0] == "ingest_batch"

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_no_snapshot_returns_error(self, mock_engine, mock_factory):
        from margin_api.workers import orchestrate_ingest

        mock_session = AsyncMock()
        mock_factory_inst = MagicMock()
        mock_factory_inst.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory_inst.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_factory_inst

        with patch("margin_api.workers.get_active_snapshot", return_value=None):
            ctx = {"redis": AsyncMock()}
            result = await orchestrate_ingest(ctx)

        assert result["status"] == "error"

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_sets_redis_coordination_keys(self, mock_engine, mock_factory):
        from margin_api.workers import orchestrate_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "1.0"
        mock_snapshot.tickers = [f"T{i:03d}" for i in range(75)]

        mock_session = AsyncMock()
        mock_factory_inst = MagicMock()
        mock_factory_inst.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory_inst.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_factory_inst

        with patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot):
            with patch("margin_api.workers._load_foreign_skips", return_value=set()):
                mock_redis = AsyncMock()
                ctx = {"redis": mock_redis}
                with patch("margin_api.workers.get_settings") as mock_settings:
                    mock_settings.return_value.ingest_batch_size = 50
                    result = await orchestrate_ingest(ctx)

        # Should set total and completed keys
        set_calls = [c for c in mock_redis.method_calls if c[0] == "set"]
        assert len(set_calls) >= 2  # total + completed
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_orchestrate_ingest.py -v`
Expected: FAIL — `ImportError: cannot import name 'orchestrate_ingest' from 'margin_api.workers'`

**Step 3: Write minimal implementation**

In `api/src/margin_api/workers.py`, add after the `from margin_api.cli import _load_foreign_skips` import at top (line 105 area), add this function after the `full_ingest` function (after line 308):

```python
async def orchestrate_ingest(ctx: dict) -> dict:
    """Orchestrate batched ingestion of the full universe.

    Loads the active universe snapshot, chunks tickers into batches,
    sets Redis coordination keys, and enqueues ingest_batch jobs.
    """
    from margin_api.cli import _load_foreign_skips

    pipeline_id = uuid.uuid4().hex[:16]
    logger.info("[orchestrate] Starting batched ingest (pipeline=%s)", pipeline_id)

    settings = get_settings()
    batch_size = settings.ingest_batch_size

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Load active universe
    async with session_factory() as session:
        snapshot = await get_active_snapshot(session)
        if snapshot is None:
            logger.error("[orchestrate] No active universe snapshot")
            return {"status": "error", "message": "No active universe snapshot"}

    tickers = list(snapshot.tickers)
    logger.info("[orchestrate] Universe v%s: %d tickers", snapshot.version, len(tickers))

    # Filter out known foreign tickers
    foreign_skips = _load_foreign_skips()
    if foreign_skips:
        before = len(tickers)
        tickers = [t for t in tickers if t not in foreign_skips]
        skipped = before - len(tickers)
        if skipped:
            logger.info("[orchestrate] Skipped %d known foreign tickers", skipped)

    # Create IngestionRun record
    async with session_factory() as session:
        run = IngestionRun(
            snapshot_id=snapshot.id,
            run_type="full",
            tickers_requested=len(tickers),
            status="running",
            started_at=datetime.now(UTC),
            pipeline_id=pipeline_id,
        )
        session.add(run)
        await session.commit()
        run_id = run.id

    # Chunk tickers into batches
    batches = [tickers[i : i + batch_size] for i in range(0, len(tickers), batch_size)]
    total_batches = len(batches)

    logger.info(
        "[orchestrate] Dispatching %d batches of ~%d tickers (pipeline=%s)",
        total_batches,
        batch_size,
        pipeline_id,
    )

    # Set Redis coordination keys
    redis: ArqRedis | None = ctx.get("redis")
    if not redis:
        logger.error("[orchestrate] No redis in worker context")
        return {"status": "error", "message": "No redis in worker context"}

    coord_prefix = f"ingest:{run_id}"
    await redis.set(f"{coord_prefix}:total", total_batches, ex=86400)
    await redis.set(f"{coord_prefix}:completed", 0, ex=86400)

    # Enqueue batch jobs
    for batch_num, batch_tickers in enumerate(batches, start=1):
        await redis.enqueue_job(
            "ingest_batch",
            str(run_id),
            pipeline_id,
            batch_tickers,
            batch_num,
            _job_id=f"ingest-batch-{run_id}-{batch_num}",
        )

    logger.info("[orchestrate] All %d batches enqueued (pipeline=%s)", total_batches, pipeline_id)

    return {
        "status": "dispatched",
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "total_batches": total_batches,
        "total_tickers": len(tickers),
    }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_orchestrate_ingest.py -v`
Expected: All 3 PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_orchestrate_ingest.py
git commit -m "feat(worker): add orchestrate_ingest job — chunks universe into batch jobs"
```

---

### Task 4: Create `ingest_batch` Job

Each batch processes ~50 tickers sequentially, using the Redis rate limiter, recording per-ticker status, and incrementing the Redis completion counter on finish.

**Files:**
- Modify: `api/src/margin_api/workers.py` (add after `orchestrate_ingest`)
- Test: `api/tests/test_ingest_batch.py`

**Step 1: Write the failing test**

Create `api/tests/test_ingest_batch.py`:

```python
"""Tests for ingest_batch worker job."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_ctx(redis=None):
    return {"redis": redis or AsyncMock()}


def _make_mock_session_factory():
    mock_session = AsyncMock()

    def _set_id_on_add(obj):
        obj.id = 1

    mock_session.add = MagicMock(side_effect=_set_id_on_add)
    mock_session.commit = AsyncMock()
    # Default: no existing asset, no resume match
    mock_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    )

    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory, mock_session


class TestIngestBatch:
    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_processes_all_tickers(self, mock_engine, mock_factory):
        from margin_api.services.seed_result import SeedResult
        from margin_api.workers import ingest_batch

        factory, session = _make_mock_session_factory()
        mock_factory.return_value = factory

        mock_redis = AsyncMock()
        # incr returns value less than total (not last batch)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.get = AsyncMock(return_value="5")
        ctx = _make_ctx(mock_redis)

        seed_result = SeedResult(status="ok", data_categories_present=["price"])

        with patch("margin_api.workers.seed_ticker_data", new_callable=AsyncMock, return_value=seed_result):
            with patch("margin_api.workers.RedisRateLimiter") as MockLimiter:
                MockLimiter.return_value.wait_and_acquire = AsyncMock()
                result = await ingest_batch(ctx, "1", "abc123", ["AAPL", "MSFT", "GOOG"], 1)

        assert result["status"] == "completed"
        assert result["succeeded"] == 3
        assert result["failed"] == 0

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_records_failures_without_aborting(self, mock_engine, mock_factory):
        from margin_api.services.seed_result import SeedResult
        from margin_api.workers import ingest_batch

        factory, session = _make_mock_session_factory()
        mock_factory.return_value = factory

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.get = AsyncMock(return_value="5")
        mock_redis.rpush = AsyncMock()
        ctx = _make_ctx(mock_redis)

        # First succeeds, second fails, third succeeds
        results = [
            SeedResult(status="ok", data_categories_present=["price"]),
            SeedResult(status="failed", error_message="yfinance timeout"),
            SeedResult(status="ok", data_categories_present=["price"]),
        ]
        call_count = 0

        async def mock_seed(*args, **kwargs):
            nonlocal call_count
            r = results[call_count]
            call_count += 1
            return r

        with patch("margin_api.workers.seed_ticker_data", side_effect=mock_seed):
            with patch("margin_api.workers.RedisRateLimiter") as MockLimiter:
                MockLimiter.return_value.wait_and_acquire = AsyncMock()
                result = await ingest_batch(ctx, "1", "abc123", ["AAPL", "FAIL", "GOOG"], 1)

        assert result["succeeded"] == 2
        assert result["failed"] == 1
        # Should have pushed failed ticker to Redis
        mock_redis.rpush.assert_called()

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_last_batch_enqueues_sweep(self, mock_engine, mock_factory):
        from margin_api.services.seed_result import SeedResult
        from margin_api.workers import ingest_batch

        factory, session = _make_mock_session_factory()
        mock_factory.return_value = factory

        mock_redis = AsyncMock()
        # incr returns value equal to total — this is the last batch
        mock_redis.incr = AsyncMock(return_value=5)
        mock_redis.get = AsyncMock(return_value="5")
        ctx = _make_ctx(mock_redis)

        seed_result = SeedResult(status="ok", data_categories_present=["price"])

        with patch("margin_api.workers.seed_ticker_data", new_callable=AsyncMock, return_value=seed_result):
            with patch("margin_api.workers.RedisRateLimiter") as MockLimiter:
                MockLimiter.return_value.wait_and_acquire = AsyncMock()
                result = await ingest_batch(ctx, "1", "abc123", ["AAPL"], 5)

        assert result["is_last_batch"] is True
        # Should enqueue ingest_sweep
        sweep_calls = [
            c for c in mock_redis.enqueue_job.call_args_list if c[0][0] == "ingest_sweep"
        ]
        assert len(sweep_calls) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_ingest_batch.py -v`
Expected: FAIL — `ImportError: cannot import name 'ingest_batch' from 'margin_api.workers'`

**Step 3: Write minimal implementation**

In `api/src/margin_api/workers.py`, add after `orchestrate_ingest`:

```python
async def ingest_batch(
    ctx: dict,
    run_id: str,
    pipeline_id: str,
    tickers: list[str],
    batch_num: int,
    is_sweep: bool = False,
) -> dict:
    """Process a batch of tickers for ingestion.

    Seeds each ticker via yfinance (rate-limited by Redis), records per-ticker
    status to the DB, and increments the Redis batch-completion counter.
    When this is the last batch to complete, enqueues ingest_sweep.
    """
    from margin_engine.ingestion.circuit_breaker import CircuitBreaker
    from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

    from margin_api.cli import seed_ticker_data
    from margin_api.services.ingestion import should_ingest_ticker
    from margin_api.services.redis_rate_limiter import RedisRateLimiter

    label = f"[ingest:{run_id}:batch-{batch_num}]"
    logger.info("%s Starting — %d tickers (sweep=%s)", label, len(tickers), is_sweep)

    settings = get_settings()
    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Build rate limiter from worker's Redis connection
    redis: ArqRedis | None = ctx.get("redis")
    raw_redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    limiter = RedisRateLimiter(raw_redis, max_per_minute=settings.ingest_rate_limit)

    provider = YFinanceProvider(rate_limiter=limiter)

    # Optional FMP fallback
    fmp_provider = None
    fmp_key = os.environ.get("FMP_API_KEY")
    if fmp_key:
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider

        fmp_provider = FMPProvider(api_key=fmp_key)

    yf_breaker = CircuitBreaker(failure_threshold=10, cooldown_seconds=900.0)
    fmp_breaker = (
        CircuitBreaker(failure_threshold=10, cooldown_seconds=900.0)
        if fmp_provider
        else None
    )

    successes = 0
    failures = 0
    partial_count = 0
    failed_tickers: list[str] = []
    total = len(tickers)
    int_run_id = int(run_id)
    coord_prefix = f"ingest:{run_id}"

    for i, ticker in enumerate(tickers, start=1):
        logger.info("%s [%d/%d] Seeding %s", label, i, total, ticker)

        # Check if ticker should be ingested
        async with session_factory() as session:
            asset_check = await session.execute(select(Asset).where(Asset.ticker == ticker))
            existing_asset = asset_check.scalar_one_or_none()
            if existing_asset and not should_ingest_ticker(
                existing_asset.ingestion_status,
                existing_asset.consecutive_failures,
                existing_asset.last_retry_at,
            ):
                logger.info("%s %s SKIPPED (status=%s)", label, ticker, existing_asset.ingestion_status)
                continue

        # Resume check: skip if already seeded today
        async with session_factory() as session:
            today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
            resume_check = await session.execute(
                select(FinancialData)
                .join(Asset, FinancialData.asset_id == Asset.id)
                .where(Asset.ticker == ticker, FinancialData.period_end == today_iso)
                .limit(1)
            )
            if resume_check.scalar_one_or_none() is not None:
                logger.info("%s %s SKIPPED (already seeded today)", label, ticker)
                continue

        # Circuit breaker gate
        if not yf_breaker.allow_request():
            logger.warning("%s %s SKIPPED (circuit breaker open)", label, ticker)
            failures += 1
            failed_tickers.append(ticker)
            continue

        tick_started = datetime.now(UTC)
        async with session_factory() as session:
            result = await seed_ticker_data(
                ticker=ticker,
                provider=provider,
                session=session,
                fallback_provider=(
                    fmp_provider
                    if (fmp_breaker is None or fmp_breaker.allow_request())
                    else None
                ),
            )
        tick_ended = datetime.now(UTC)
        duration_ms = int((tick_ended - tick_started).total_seconds() * 1000)

        # Update circuit breaker
        if result.status == "failed":
            yf_breaker.record_failure()
        else:
            yf_breaker.record_success()

        # Record per-ticker audit trail
        if result.status in ("ok", "partial"):
            audit_status = "succeeded"
        else:
            audit_status = result.status
        async with session_factory() as session:
            ticker_status = IngestionTickerStatus(
                run_id=int_run_id,
                ticker=ticker,
                status=audit_status,
                error_message=result.error_message if result.status == "failed" else None,
                data_fetched=result.data_categories_present if result.is_success else None,
                duration_ms=duration_ms,
                started_at=tick_started,
                completed_at=tick_ended,
            )
            session.add(ticker_status)
            await session.commit()

        if result.status == "ok":
            successes += 1
        elif result.status == "partial":
            successes += 1
            partial_count += 1
        elif result.status == "failed":
            failures += 1
            failed_tickers.append(ticker)
            logger.warning("%s %s FAILED: %s", label, ticker, result.error_message)

    # Push failed tickers to Redis list for sweep
    if failed_tickers and redis:
        await redis.rpush(f"{coord_prefix}:failed_tickers", *failed_tickers)

    # Update IngestionRun stats atomically
    async with session_factory() as session:
        ing_result = await session.execute(select(IngestionRun).where(IngestionRun.id == int_run_id))
        run = ing_result.scalar_one()
        run.tickers_succeeded = (run.tickers_succeeded or 0) + successes
        run.tickers_failed = (run.tickers_failed or 0) + failures
        run.tickers_partial = (run.tickers_partial or 0) + partial_count
        await session.commit()

    logger.info(
        "%s Complete: %d succeeded (%d partial), %d failed",
        label,
        successes,
        partial_count,
        failures,
    )

    # Increment completion counter and check if last batch
    is_last_batch = False
    if redis:
        completed = await redis.incr(f"{coord_prefix}:completed")
        total_batches = int(await redis.get(f"{coord_prefix}:total") or 0)
        if completed >= total_batches:
            is_last_batch = True
            logger.info("%s Last batch complete — enqueuing sweep (pipeline=%s)", label, pipeline_id)
            await redis.enqueue_job("ingest_sweep", run_id, pipeline_id)

    # Cleanup Redis connection
    await raw_redis.aclose()

    return {
        "status": "completed",
        "batch_num": batch_num,
        "succeeded": successes,
        "partial": partial_count,
        "failed": failures,
        "is_last_batch": is_last_batch,
    }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_ingest_batch.py -v`
Expected: All 3 PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_ingest_batch.py
git commit -m "feat(worker): add ingest_batch job — processes ticker chunk with Redis rate limiter"
```

---

### Task 5: Create `ingest_sweep` and `ingest_sweep_complete` Jobs

Sweep finds tickers missing successful ingest, enqueues a cleanup batch, then triggers the scoring chain.

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_ingest_sweep.py`

**Step 1: Write the failing test**

Create `api/tests/test_ingest_sweep.py`:

```python
"""Tests for ingest_sweep and ingest_sweep_complete worker jobs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestIngestSweep:
    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_sweep_no_missing_tickers(self, mock_engine, mock_factory):
        from margin_api.workers import ingest_sweep

        mock_session = AsyncMock()
        # First query: get IngestionRun (returns run with snapshot_id)
        mock_run = MagicMock()
        mock_run.snapshot_id = 1
        mock_run.tickers_requested = 100
        mock_run.tickers_succeeded = 100
        mock_run.tickers_failed = 0
        # Second query: get snapshot tickers
        mock_snapshot = MagicMock()
        mock_snapshot.tickers = [f"T{i}" for i in range(100)]
        # Third query: get succeeded tickers from IngestionTickerStatus
        mock_succeeded_rows = [(f"T{i}",) for i in range(100)]

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:  # IngestionRun query
                result.scalar_one.return_value = mock_run
            elif call_count == 2:  # UniverseSnapshot query
                result.scalar_one.return_value = mock_snapshot
            elif call_count == 3:  # IngestionTickerStatus query
                result.all.return_value = mock_succeeded_rows
            return result

        mock_session.execute = mock_execute
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = factory

        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}
        result = await ingest_sweep(ctx, "1", "abc123")

        assert result["missing_count"] == 0
        # Should enqueue ingest_sweep_complete directly
        sweep_complete_calls = [
            c for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "ingest_sweep_complete"
        ]
        assert len(sweep_complete_calls) == 1

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_sweep_with_missing_tickers(self, mock_engine, mock_factory):
        from margin_api.workers import ingest_sweep

        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.snapshot_id = 1
        mock_run.tickers_requested = 100
        mock_snapshot = MagicMock()
        mock_snapshot.tickers = [f"T{i}" for i in range(100)]
        # Only 95 succeeded
        mock_succeeded_rows = [(f"T{i}",) for i in range(95)]

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one.return_value = mock_run
            elif call_count == 2:
                result.scalar_one.return_value = mock_snapshot
            elif call_count == 3:
                result.all.return_value = mock_succeeded_rows
            return result

        mock_session.execute = mock_execute
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = factory

        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}
        result = await ingest_sweep(ctx, "1", "abc123")

        assert result["missing_count"] == 5
        # Should enqueue ingest_batch (sweep batch), not ingest_sweep_complete
        batch_calls = [
            c for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "ingest_batch"
        ]
        assert len(batch_calls) == 1
        # The batch should have is_sweep=True
        call_kwargs = batch_calls[0]
        # Positional args: job_name, run_id, pipeline_id, tickers, batch_num, is_sweep
        assert call_kwargs[0][-1] is True  # is_sweep flag


class TestIngestSweepComplete:
    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_finalizes_run_and_chains_to_scoring(self, mock_engine, mock_factory):
        from margin_api.workers import ingest_sweep_complete

        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.started_at = MagicMock()
        mock_run.tickers_succeeded = 95
        mock_run.tickers_failed = 5
        mock_run.tickers_requested = 100
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one=MagicMock(return_value=mock_run)),
        )
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = factory

        mock_redis = AsyncMock()
        ctx = {"redis": mock_redis}
        result = await ingest_sweep_complete(ctx, "1", "abc123")

        assert result["status"] == "completed"
        # Should chain to full_score
        score_calls = [
            c for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "full_score"
        ]
        assert len(score_calls) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_ingest_sweep.py -v`
Expected: FAIL — `ImportError: cannot import name 'ingest_sweep' from 'margin_api.workers'`

**Step 3: Write minimal implementation**

In `api/src/margin_api/workers.py`, add after `ingest_batch`:

```python
async def ingest_sweep(ctx: dict, run_id: str, pipeline_id: str) -> dict:
    """Find tickers that were not successfully ingested and enqueue a cleanup batch.

    If all tickers succeeded, goes straight to ingest_sweep_complete.
    The sweep runs once — any tickers that fail the sweep are left for
    the weekly retry_quarantined cron.
    """
    label = f"[sweep:{run_id}]"
    logger.info("%s Starting sweep (pipeline=%s)", label, pipeline_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        # Get the IngestionRun
        run_result = await session.execute(
            select(IngestionRun).where(IngestionRun.id == int(run_id))
        )
        run = run_result.scalar_one()

        # Get universe tickers from snapshot
        snap_result = await session.execute(
            select(UniverseSnapshot).where(UniverseSnapshot.id == run.snapshot_id)
        )
        snapshot = snap_result.scalar_one()
        universe_tickers = set(snapshot.tickers)

        # Get tickers that succeeded in this run
        succeeded_result = await session.execute(
            select(IngestionTickerStatus.ticker).where(
                IngestionTickerStatus.run_id == int(run_id),
                IngestionTickerStatus.status == "succeeded",
            )
        )
        succeeded_tickers = {row[0] for row in succeeded_result.all()}

    missing_tickers = sorted(universe_tickers - succeeded_tickers)
    logger.info("%s %d missing tickers out of %d", label, len(missing_tickers), len(universe_tickers))

    redis: ArqRedis | None = ctx.get("redis")
    if not redis:
        return {"status": "error", "message": "No redis"}

    if missing_tickers:
        # Enqueue a single sweep batch
        await redis.enqueue_job(
            "ingest_batch",
            run_id,
            pipeline_id,
            missing_tickers,
            0,  # batch_num=0 for sweep
            True,  # is_sweep=True
            _job_id=f"ingest-sweep-batch-{run_id}",
        )
        logger.info("%s Enqueued sweep batch with %d tickers", label, len(missing_tickers))
    else:
        # All done — go straight to completion
        await redis.enqueue_job("ingest_sweep_complete", run_id, pipeline_id)
        logger.info("%s No missing tickers — enqueuing sweep_complete", label)

    return {
        "status": "sweep_dispatched" if missing_tickers else "all_complete",
        "missing_count": len(missing_tickers),
    }


async def ingest_sweep_complete(ctx: dict, run_id: str, pipeline_id: str) -> dict:
    """Finalize the ingestion run and chain to scoring.

    Updates the IngestionRun record with final stats, then enqueues full_score.
    """
    label = f"[sweep_complete:{run_id}]"
    logger.info("%s Finalizing ingestion run (pipeline=%s)", label, pipeline_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    completed_at = datetime.now(UTC)
    async with session_factory() as session:
        run_result = await session.execute(
            select(IngestionRun).where(IngestionRun.id == int(run_id))
        )
        run = run_result.scalar_one()
        run.status = "failed" if (run.tickers_failed or 0) > run.tickers_requested * 0.5 else "completed"
        run.completed_at = completed_at
        run.duration_seconds = (completed_at - run.started_at).total_seconds()
        await session.commit()

    logger.info(
        "%s Ingestion complete: %d succeeded, %d failed (%.0fs)",
        label,
        run.tickers_succeeded or 0,
        run.tickers_failed or 0,
        run.duration_seconds or 0,
    )

    # Chain to scoring
    redis: ArqRedis | None = ctx.get("redis")
    if redis:
        await redis.enqueue_job("full_score", pipeline_id)
        logger.info("%s Enqueued full_score (pipeline=%s)", label, pipeline_id)

    return {
        "status": "completed",
        "pipeline_id": pipeline_id,
        "succeeded": run.tickers_succeeded or 0,
        "failed": run.tickers_failed or 0,
        "duration_seconds": run.duration_seconds,
    }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_ingest_sweep.py -v`
Expected: All 3 PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_ingest_sweep.py
git commit -m "feat(worker): add ingest_sweep and ingest_sweep_complete jobs"
```

---

### Task 6: Handle Sweep Batch Completion

When `ingest_batch` runs with `is_sweep=True`, it should enqueue `ingest_sweep_complete` instead of `ingest_sweep` after finishing.

**Files:**
- Modify: `api/src/margin_api/workers.py` (update `ingest_batch`)
- Modify: `api/tests/test_ingest_batch.py` (add sweep-specific test)

**Step 1: Write the failing test**

Add to `api/tests/test_ingest_batch.py`:

```python
class TestIngestBatchSweep:
    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_sweep_batch_enqueues_sweep_complete(self, mock_engine, mock_factory):
        from margin_api.services.seed_result import SeedResult
        from margin_api.workers import ingest_batch

        factory, session = _make_mock_session_factory()
        mock_factory.return_value = factory

        mock_redis = AsyncMock()
        # For sweep batches, the incr/total check is skipped — always enqueue sweep_complete
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.get = AsyncMock(return_value="1")
        ctx = _make_ctx(mock_redis)

        seed_result = SeedResult(status="ok", data_categories_present=["price"])

        with patch("margin_api.workers.seed_ticker_data", new_callable=AsyncMock, return_value=seed_result):
            with patch("margin_api.workers.RedisRateLimiter") as MockLimiter:
                MockLimiter.return_value.wait_and_acquire = AsyncMock()
                result = await ingest_batch(
                    ctx, "1", "abc123", ["AAPL"], 0, is_sweep=True,
                )

        # Sweep batch should enqueue ingest_sweep_complete, not ingest_sweep
        complete_calls = [
            c for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "ingest_sweep_complete"
        ]
        assert len(complete_calls) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_ingest_batch.py::TestIngestBatchSweep -v`
Expected: FAIL — sweep batch currently enqueues `ingest_sweep`

**Step 3: Update implementation**

In the `ingest_batch` function, modify the completion logic (the block after `redis.incr`) to:

```python
    # Increment completion counter and check if last batch
    is_last_batch = False
    if redis:
        if is_sweep:
            # Sweep batch always goes to sweep_complete
            is_last_batch = True
            logger.info("%s Sweep batch complete — enqueuing sweep_complete (pipeline=%s)", label, pipeline_id)
            await redis.enqueue_job("ingest_sweep_complete", run_id, pipeline_id)
        else:
            completed = await redis.incr(f"{coord_prefix}:completed")
            total_batches = int(await redis.get(f"{coord_prefix}:total") or 0)
            if completed >= total_batches:
                is_last_batch = True
                logger.info("%s Last batch complete — enqueuing sweep (pipeline=%s)", label, pipeline_id)
                await redis.enqueue_job("ingest_sweep", run_id, pipeline_id)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_ingest_batch.py -v`
Expected: All 4 PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_ingest_batch.py
git commit -m "feat(worker): sweep batch routes to ingest_sweep_complete instead of re-sweeping"
```

---

### Task 7: Wire WorkerSettings — Replace `full_ingest` with New Pipeline

Update `WorkerSettings` to register the new jobs, update cron, and set `max_jobs` from config.

**Files:**
- Modify: `api/src/margin_api/workers.py:1508-1557` (WorkerSettings class)
- Modify: `api/tests/test_workers.py` (update registration tests)

**Step 1: Write the failing test**

Update `api/tests/test_workers.py` — replace `TestWorkerSettings` and `TestWorkerRegistration`:

```python
class TestWorkerSettings:
    def test_has_redis_settings(self):
        assert WorkerSettings.redis_settings is not None

    def test_has_functions(self):
        assert len(WorkerSettings.functions) >= 8

    def test_has_cron_jobs(self):
        assert len(WorkerSettings.cron_jobs) >= 2

    def test_function_names(self):
        names = [f.__name__ for f in WorkerSettings.functions]
        # New batched pipeline jobs
        assert "orchestrate_ingest" in names
        assert "ingest_batch" in names
        assert "ingest_sweep" in names
        assert "ingest_sweep_complete" in names
        # Retained jobs
        assert "full_score" in names
        assert "full_score_v3" in names
        assert "full_score_v4" in names
        assert "live_price_poll" in names
        assert "retry_quarantined" in names
        # Old monolithic job should be gone
        assert "full_ingest" not in names

    def test_job_timeout_is_batch_scale(self):
        """Default timeout should be batch-scale (~20 min), not pipeline-scale (~5h)."""
        assert WorkerSettings.job_timeout <= 1800

    def test_max_jobs_from_config(self):
        assert WorkerSettings.max_jobs >= 2

    def test_cron_uses_orchestrate_ingest(self):
        cron_funcs = [j.coroutine.__name__ for j in WorkerSettings.cron_jobs]
        assert "orchestrate_ingest" in cron_funcs
        assert "full_ingest" not in cron_funcs
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_workers.py::TestWorkerSettings -v`
Expected: FAIL — `full_ingest` still registered, `orchestrate_ingest` missing

**Step 3: Update implementation**

Replace the `WorkerSettings` class in `api/src/margin_api/workers.py`:

```python
class WorkerSettings:
    """ARQ worker settings.

    Run the worker with:
        arq margin_api.workers.WorkerSettings
    """

    redis_settings = _parse_redis_settings()
    max_jobs = get_settings().ingest_concurrency

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Log worker startup info for debugging connectivity."""
        settings = get_settings()
        url = settings.redis_url
        if "@" in url:
            scheme = url.split("://")[0]
            host_part = url.split("@", 1)[1]
            url = f"{scheme}://***@{host_part}"
        logger.info("[worker] Started — Redis: %s, max_jobs: %d", url, WorkerSettings.max_jobs)
        logger.info(
            "[worker] Registered functions: %s",
            [f.__name__ if callable(f) else str(f) for f in WorkerSettings.functions],
        )

    functions = [
        orchestrate_ingest,
        ingest_batch,
        ingest_sweep,
        ingest_sweep_complete,
        full_score,
        full_score_v3,
        full_score_v4,
        backtest_validate,
        train_ml_models,
        live_price_poll,
        retry_quarantined,
        full_13f_ingest,
        compute_accumulation_signals,
    ]
    cron_jobs = [
        cron(orchestrate_ingest, hour=21, minute=30),  # 4:30 PM ET — after market close
        cron(
            live_price_poll,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
            run_at_startup=False,
        ),
        cron(retry_quarantined, weekday=6, hour=0),  # Sunday midnight
        cron(train_ml_models, weekday=5, hour=2),  # Saturday 2 AM UTC
        cron(full_13f_ingest, hour=22, minute=0),  # 5 PM ET — after daily ingest
    ]
    # Default job timeout: 20 minutes (batch-scale, not pipeline-scale)
    job_timeout = 1200
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_workers.py::TestWorkerSettings -v`
Expected: All PASS

**Step 5: Also update `TestWorkerRegistration` at end of file**

Replace the old `TestWorkerRegistration` class:

```python
class TestWorkerRegistration:
    """Verify all jobs are registered in WorkerSettings."""

    def test_orchestrate_ingest_registered(self):
        names = [f.__name__ for f in WorkerSettings.functions]
        assert "orchestrate_ingest" in names

    def test_ingest_batch_registered(self):
        names = [f.__name__ for f in WorkerSettings.functions]
        assert "ingest_batch" in names

    def test_ingest_sweep_registered(self):
        names = [f.__name__ for f in WorkerSettings.functions]
        assert "ingest_sweep" in names

    def test_cron_includes_orchestrate_ingest(self):
        cron_funcs = [j.coroutine.__name__ for j in WorkerSettings.cron_jobs]
        assert "orchestrate_ingest" in cron_funcs

    def test_total_functions_count(self):
        assert len(WorkerSettings.functions) == 13

    def test_total_cron_jobs_count(self):
        assert len(WorkerSettings.cron_jobs) == 5
```

**Step 6: Run all worker tests**

Run: `uv run pytest api/tests/test_workers.py -v`
Expected: All PASS (some `TestFullIngest` tests will now fail because `full_ingest` is no longer registered — see Task 8)

**Step 7: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "feat(worker): wire WorkerSettings to batched pipeline — replace full_ingest cron"
```

---

### Task 8: Remove `full_ingest` and Update Stale Tests

The monolithic `full_ingest` function is no longer used. Remove it and update any tests that reference it.

**Files:**
- Modify: `api/src/margin_api/workers.py` (delete `full_ingest` function, lines 92-308)
- Modify: `api/tests/test_workers.py` (delete `TestFullIngest` class)

**Step 1: Delete `full_ingest` function**

Remove the entire `full_ingest` function from `workers.py` (lines 92-308). Keep the imports that are still used by the new batch jobs.

**Step 2: Delete `TestFullIngest` class**

Remove the `TestFullIngest` class from `api/tests/test_workers.py` (it tests the deleted function).

**Step 3: Run all tests to verify nothing is broken**

Run: `uv run pytest api/tests/test_workers.py -v`
Expected: All remaining tests PASS

Run: `uv run pytest api/tests/ -v --timeout=60`
Expected: No test references `full_ingest` in a way that breaks

**Step 4: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "refactor(worker): remove monolithic full_ingest — replaced by batched pipeline"
```

---

### Task 9: Make `YFinanceProvider` Accept Async Rate Limiter

The `YFinanceProvider._acquire_rate_limit()` calls `wait_and_acquire()` synchronously. With the Redis rate limiter, it needs to `await`. Add duck-typed support for both sync and async rate limiters.

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/yfinance_provider.py:73-79`
- Test: `engine/tests/test_yfinance_rate_limit.py` (create)

**Step 1: Write the failing test**

Create `engine/tests/test_yfinance_rate_limit.py`:

```python
"""Tests for YFinanceProvider rate limiter integration (sync and async)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.rate_limiter import RateLimiter


class TestRateLimiterDuckTyping:
    def test_sync_rate_limiter_works(self):
        """Original sync RateLimiter should still work."""
        limiter = RateLimiter(requests_per_minute=60)
        provider = YFinanceProvider(rate_limiter=limiter)
        # Should not raise
        provider._acquire_rate_limit()

    @pytest.mark.asyncio
    async def test_async_rate_limiter_works(self):
        """An async rate limiter with async wait_and_acquire should work."""
        limiter = AsyncMock()
        limiter.wait_and_acquire = AsyncMock()
        provider = YFinanceProvider(rate_limiter=limiter)
        # Should detect async and await it
        await provider._acquire_rate_limit_async()
        limiter.wait_and_acquire.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_yfinance_rate_limit.py -v`
Expected: FAIL — `YFinanceProvider` has no `_acquire_rate_limit_async`

**Step 3: Write minimal implementation**

In `engine/src/margin_engine/ingestion/providers/yfinance_provider.py`, change:

```python
    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        self._rate_limiter = rate_limiter

    def _acquire_rate_limit(self) -> None:
        """Block until a rate-limit token is available (if limiter configured)."""
        if self._rate_limiter is not None:
            self._rate_limiter.wait_and_acquire()

    async def _acquire_rate_limit_async(self) -> None:
        """Async version — awaits if the limiter's wait_and_acquire is a coroutine."""
        if self._rate_limiter is not None:
            result = self._rate_limiter.wait_and_acquire()
            if asyncio.iscoroutine(result):
                await result
```

Add `import asyncio` to the imports at the top of the file.

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_yfinance_rate_limit.py -v`
Expected: All 2 PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/yfinance_provider.py engine/tests/test_yfinance_rate_limit.py
git commit -m "feat(engine): add async rate limiter support to YFinanceProvider"
```

---

### Task 10: Wire `ingest_batch` to Use Async Rate Limiting

Update `ingest_batch` so the `YFinanceProvider` uses the async `_acquire_rate_limit_async` path when the Redis rate limiter is injected. The provider's `fetch_all` calls `_acquire_rate_limit()` internally (sync). Since `seed_ticker_data` calls the provider, we need to ensure the async limiter is awaited before each API call.

The cleanest approach: have `ingest_batch` call `await limiter.wait_and_acquire()` **before** calling `seed_ticker_data` for each ticker (at the batch job level), and pass `rate_limiter=None` to the provider so it doesn't double-limit.

**Files:**
- Modify: `api/src/margin_api/workers.py` (in `ingest_batch`)
- Modify: `api/tests/test_ingest_batch.py` (verify rate limiter is called per ticker)

**Step 1: Write the failing test**

Add to `api/tests/test_ingest_batch.py`:

```python
class TestIngestBatchRateLimiting:
    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_rate_limiter_called_per_ticker(self, mock_engine, mock_factory):
        from margin_api.services.seed_result import SeedResult
        from margin_api.workers import ingest_batch

        factory, session = _make_mock_session_factory()
        mock_factory.return_value = factory

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.get = AsyncMock(return_value="5")
        ctx = _make_ctx(mock_redis)

        seed_result = SeedResult(status="ok", data_categories_present=["price"])
        mock_limiter = AsyncMock()
        mock_limiter.wait_and_acquire = AsyncMock()

        with patch("margin_api.workers.seed_ticker_data", new_callable=AsyncMock, return_value=seed_result):
            with patch("margin_api.workers.RedisRateLimiter", return_value=mock_limiter):
                result = await ingest_batch(ctx, "1", "abc123", ["AAPL", "MSFT", "GOOG"], 1)

        # Rate limiter should be called once per ticker that was actually seeded
        assert mock_limiter.wait_and_acquire.call_count == 3
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_ingest_batch.py::TestIngestBatchRateLimiting -v`
Expected: FAIL — rate limiter not called per ticker

**Step 3: Update implementation**

In `ingest_batch`, change the provider creation to not pass the rate limiter, and add an explicit `await limiter.wait_and_acquire()` before each `seed_ticker_data` call:

```python
    # Don't pass limiter to provider — we rate-limit at the batch level
    provider = YFinanceProvider(rate_limiter=None)
```

And in the per-ticker loop, just before `seed_ticker_data`:

```python
        # Rate limit at batch level (shared Redis limiter)
        await limiter.wait_and_acquire()

        tick_started = datetime.now(UTC)
        async with session_factory() as session:
            result = await seed_ticker_data(...)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_ingest_batch.py -v`
Expected: All 5 PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_ingest_batch.py
git commit -m "feat(worker): rate-limit at batch level via Redis before each seed_ticker_data call"
```

---

### Task 11: Integration Test — Full Pipeline Flow

An integration test that verifies the entire orchestrate → batch → sweep → score chain using mocks.

**Files:**
- Create: `api/tests/test_batched_pipeline_integration.py`

**Step 1: Write the integration test**

```python
"""Integration test for the full batched ingest pipeline flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from margin_api.services.seed_result import SeedResult


class TestBatchedPipelineFlow:
    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_orchestrate_to_sweep_complete(self, mock_engine, mock_factory):
        """Verify the full pipeline: orchestrate → batch → sweep → score."""
        from margin_api.workers import (
            ingest_batch,
            ingest_sweep_complete,
            orchestrate_ingest,
        )

        # Setup mock DB
        mock_session = AsyncMock()
        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "test"
        mock_snapshot.tickers = ["AAPL", "MSFT", "GOOG"]

        def _set_id_on_add(obj):
            obj.id = 42

        mock_session.add = MagicMock(side_effect=_set_id_on_add)
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=None),
                scalar_one=MagicMock(return_value=MagicMock(
                    started_at=MagicMock(),
                    tickers_succeeded=3,
                    tickers_failed=0,
                    tickers_requested=3,
                    tickers_partial=0,
                )),
            ),
        )

        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = factory

        mock_redis = AsyncMock()
        # Simulate: incr returns 1 (== total of 1 batch → last batch)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.get = AsyncMock(return_value="1")
        ctx = {"redis": mock_redis}

        # Step 1: Orchestrate
        with patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot):
            with patch("margin_api.workers._load_foreign_skips", return_value=set()):
                with patch("margin_api.workers.get_settings") as mock_settings:
                    mock_settings.return_value.ingest_batch_size = 50
                    mock_settings.return_value.ingest_rate_limit = 36
                    mock_settings.return_value.redis_url = "redis://localhost:6379"
                    orch_result = await orchestrate_ingest(ctx)

        assert orch_result["status"] == "dispatched"
        assert orch_result["total_batches"] == 1

        # Step 2: Batch (simulate what ARQ would pick up)
        seed_result = SeedResult(status="ok", data_categories_present=["price"])
        with patch("margin_api.workers.seed_ticker_data", new_callable=AsyncMock, return_value=seed_result):
            with patch("margin_api.workers.RedisRateLimiter") as MockLimiter:
                MockLimiter.return_value.wait_and_acquire = AsyncMock()
                with patch("margin_api.workers.get_settings") as mock_settings:
                    mock_settings.return_value.ingest_rate_limit = 36
                    mock_settings.return_value.redis_url = "redis://localhost:6379"
                    batch_result = await ingest_batch(
                        ctx, "42", orch_result["pipeline_id"], ["AAPL", "MSFT", "GOOG"], 1,
                    )

        assert batch_result["succeeded"] == 3
        assert batch_result["is_last_batch"] is True

        # Step 3: Sweep complete (simulate enqueued by batch)
        sc_result = await ingest_sweep_complete(ctx, "42", orch_result["pipeline_id"])
        assert sc_result["status"] == "completed"

        # Verify full_score was enqueued
        score_calls = [
            c for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "full_score"
        ]
        assert len(score_calls) >= 1
```

**Step 2: Run test**

Run: `uv run pytest api/tests/test_batched_pipeline_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add api/tests/test_batched_pipeline_integration.py
git commit -m "test(worker): add integration test for full batched ingest pipeline flow"
```

---

### Task 12: Run Full Test Suite

Verify nothing is broken across the entire codebase.

**Step 1: Run all API tests**

Run: `uv run pytest api/tests/ -v --timeout=120`
Expected: All pass. Watch for:
- Tests that import `full_ingest` directly
- Tests that reference `WorkerSettings.job_timeout == 18000`
- Tests that check `WorkerSettings.functions` count

**Step 2: Run all engine tests**

Run: `uv run pytest engine/tests/ -v --timeout=120`
Expected: All pass (engine changes are minimal — just the async rate limit method)

**Step 3: Fix any broken tests**

If any test imports or references `full_ingest`, update it to reference `orchestrate_ingest` or remove the reference. Common patterns to check:
- `from margin_api.workers import full_ingest`
- `assert "full_ingest" in names`
- `WorkerSettings.job_timeout >= 3600` (now 1200)

**Step 4: Commit fixes**

```bash
git add -u
git commit -m "fix(tests): update test assertions for batched ingest pipeline"
```

---

Plan complete and saved to `docs/plans/2026-02-25-batched-ingest-pipeline-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

Which approach?