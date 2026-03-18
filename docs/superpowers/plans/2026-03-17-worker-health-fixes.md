# Worker Health Fixes Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 production issues in the ARQ worker that have quarantined 94% of tickers from price polling.

**Architecture:** Surgical fixes to existing Redis-counter architecture in `workers.py`. No schema changes. Fixes: per-ticker failure attribution, TTL race condition, implement `retry_quarantined()`, yfinance TzCache, reduce `expire_stale_approvals` frequency.

**Tech Stack:** Python 3.13, ARQ, redis.asyncio, yfinance, fakeredis, pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-17-worker-health-fixes-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `api/src/margin_api/workers.py` | Modify | All 5 fixes: `_record_fail()`, `_download_batch()`, `retry_quarantined()`, `on_startup()`, cron schedule |
| `api/tests/test_workers.py` | Modify | New test classes for all changed functions |

---

### Task 1: Fix `_record_fail()` TTL Race Condition

**Files:**
- Modify: `api/src/margin_api/workers.py:2905-2912`
- Modify: `api/tests/test_workers.py` (add new test class)

- [ ] **Step 1: Write the failing tests**

Add to `api/tests/test_workers.py`:

```python
class TestRecordFail:
    @pytest.mark.asyncio
    async def test_ttl_set_only_on_first_failure(self):
        """TTL should be set on first failure, not reset on subsequent failures."""
        import fakeredis.aioredis
        from margin_api.workers import _record_fail

        fake_redis = fakeredis.aioredis.FakeRedis()

        # First failure — should set TTL
        await _record_fail(fake_redis, "AAPL")
        ttl_after_first = await fake_redis.ttl("price_fail:AAPL")
        assert 86300 < ttl_after_first <= 86400  # ~24h

        # Simulate time passing: manually reduce TTL to 50000
        await fake_redis.expire("price_fail:AAPL", 50000)

        # Second failure — should NOT reset TTL back to 86400
        await _record_fail(fake_redis, "AAPL")
        ttl_after_second = await fake_redis.ttl("price_fail:AAPL")
        assert ttl_after_second <= 50000  # TTL was NOT reset
        count = int(await fake_redis.get("price_fail:AAPL"))
        assert count == 2  # Counter incremented

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_safety_ttl_on_orphaned_key(self):
        """If a key has no TTL (simulating crash between INCR and EXPIRE), the
        safety check should add one. The old code always calls EXPIRE so this
        scenario can't happen — the test verifies the NEW safety path works by
        simulating the exact orphan condition the new code can create."""
        import fakeredis.aioredis
        from margin_api.workers import _record_fail

        fake_redis = fakeredis.aioredis.FakeRedis()

        # Call _record_fail once to create the key normally
        await _record_fail(fake_redis, "AAPL")
        # Now simulate a crash: manually remove the TTL to create an orphan
        await fake_redis.persist("price_fail:AAPL")
        assert await fake_redis.ttl("price_fail:AAPL") == -1

        # Second call should detect TTL=-1 and fix it
        await _record_fail(fake_redis, "AAPL")
        ttl = await fake_redis.ttl("price_fail:AAPL")
        # Old code: TTL would be -1 because EXPIRE was only called when count==1
        # and count is now 2, so the old code's conditional branch wouldn't fire.
        # New code: safety check detects ttl==-1 and sets it.
        assert ttl > 0, "Orphaned key should have TTL restored"
        assert 86300 < ttl <= 86400
        count = int(await fake_redis.get("price_fail:AAPL"))
        assert count == 2

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_logs_warning_on_failure(self):
        """_record_fail logs a warning with ticker and count."""
        import fakeredis.aioredis
        from margin_api.workers import _record_fail

        fake_redis = fakeredis.aioredis.FakeRedis()

        with patch("margin_api.workers.logger") as mock_logger:
            await _record_fail(fake_redis, "AAPL")
            mock_logger.warning.assert_called_once_with("price_fail:%s count=%d", "AAPL", 1)

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_logs_debug_on_redis_error(self):
        """Redis exceptions are logged at debug level, not swallowed silently."""
        from margin_api.workers import _record_fail

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis down"))

        with patch("margin_api.workers.logger") as mock_logger:
            await _record_fail(mock_redis, "AAPL")  # Should not raise
            mock_logger.debug.assert_called_once()

```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_workers.py::TestRecordFail -v`
Expected: 3 FAIL, 1 PASS — `test_ttl_set_only_on_first_failure`, `test_logs_warning_on_failure`, and `test_logs_debug_on_redis_error` fail on current code. `test_safety_ttl_on_orphaned_key` passes because the old code always calls `EXPIRE` (this test validates the NEW code's safety path — it only becomes meaningful after the primary fix removes unconditional EXPIRE).

- [ ] **Step 3: Implement the fix**

Replace `_record_fail` in `api/src/margin_api/workers.py:2905-2912`:

```python
async def _record_fail(redis_client, ticker: str) -> None:
    """Increment the price-poll failure counter for a ticker.

    TTL (24h) is set only on first failure to create a fixed evaluation window.
    Includes a safety check for orphaned keys with no TTL.
    """
    key = f"price_fail:{ticker}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            # First failure in window — start the 24h countdown
            await redis_client.expire(key, 86400)
        else:
            # Safety: if key has no TTL (crash between INCR and EXPIRE), set it
            ttl = await redis_client.ttl(key)
            if ttl == -1:
                await redis_client.expire(key, 86400)
        logger.warning("price_fail:%s count=%d", ticker, count)
    except Exception:
        logger.debug("Redis error in _record_fail for %s", ticker, exc_info=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_workers.py::TestRecordFail -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "fix(worker): _record_fail TTL only set on first failure, add logging"
```

---

### Task 2: Per-Ticker Failure Attribution in `_download_batch()`

**Files:**
- Modify: `api/src/margin_api/workers.py:2794-2877` (`_download_batch` inner function)
- Modify: `api/tests/test_workers.py` (add new test class)

- [ ] **Step 1: Write the failing tests**

Add to `api/tests/test_workers.py`:

```python
class TestDownloadBatchAttribution:
    """Tests for per-ticker failure attribution in _download_batch."""

    @pytest.mark.asyncio
    async def test_batch_timeout_does_not_penalize_tickers(self):
        """On asyncio.TimeoutError, no tickers get _record_fail."""
        import fakeredis.aioredis
        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",), ("MSFT",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # yf.download always times out
        def _timeout(*args, **kwargs):
            raise TimeoutError("Batch download timed out")

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", side_effect=_timeout),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        # No tickers should have failure counters
        aapl_count = await fake_redis.get("price_fail:AAPL")
        msft_count = await fake_redis.get("price_fail:MSFT")
        assert aapl_count is None, "AAPL should not be penalized on batch timeout"
        assert msft_count is None, "MSFT should not be penalized on batch timeout"

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_partial_batch_penalizes_only_missing_tickers(self):
        """Tickers with no data get _record_fail; tickers with data get counter cleared."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()
        # Pre-set a failure counter for AAPL that should be cleared on success
        await fake_redis.set("price_fail:AAPL", "3")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",), ("BAD",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # MultiIndex DataFrame: AAPL has data, BAD is missing
        idx = pd.DatetimeIndex(["2026-03-17"], name="Date")
        mock_df = pd.DataFrame(
            {
                ("Open", "AAPL"): [150.0],
                ("High", "AAPL"): [152.0],
                ("Low", "AAPL"): [149.0],
                ("Close", "AAPL"): [151.0],
                ("Volume", "AAPL"): [1000000],
            },
            index=idx,
        )
        mock_df.columns = pd.MultiIndex.from_tuples(mock_df.columns)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_df),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        # AAPL succeeded — counter should be cleared
        assert await fake_redis.get("price_fail:AAPL") is None
        # BAD had no data — counter should be set
        bad_count = await fake_redis.get("price_fail:BAD")
        assert bad_count is not None
        assert int(bad_count) >= 1

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_connection_error_does_not_penalize_or_retry(self):
        """On ConnectionError (non-timeout), no tickers penalized, no retry."""
        import fakeredis.aioredis
        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        call_count = 0

        def _conn_error(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network unreachable")

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", side_effect=_conn_error),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        # No tickers penalized
        assert await fake_redis.get("price_fail:AAPL") is None
        # No retry — only called once per batch
        assert call_count == 1

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_batch_split_retry_recovers_on_second_try(self):
        """On timeout, batch splits in half and retries. Successful halves process normally."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",), ("MSFT",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # First call (full batch) times out; subsequent calls (halves) succeed
        call_count = 0
        idx = pd.DatetimeIndex(["2026-03-17"], name="Date")

        def _download_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Batch download timed out")
            # Half-batch calls succeed with single-ticker DataFrames
            return pd.DataFrame(
                {"Open": [150.0], "High": [152.0], "Low": [149.0], "Close": [151.0], "Volume": [1000000]},
                index=idx,
            )

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", side_effect=_download_side_effect),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        # Both halves succeeded after retry
        assert result["updated"] == 2
        # 3 calls: 1 full batch timeout + 2 half-batch retries
        assert call_count == 3
        # No failure counters set
        assert await fake_redis.get("price_fail:AAPL") is None
        assert await fake_redis.get("price_fail:MSFT") is None

        await fake_redis.aclose()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_workers.py::TestDownloadBatchAttribution -v`
Expected: FAIL — current code penalizes all tickers on batch failure

- [ ] **Step 3: Implement the fix**

Replace the `_download_batch` inner function in `api/src/margin_api/workers.py:2794-2877`. **IMPORTANT:** All three new functions (`_download_batch`, `_yf_download_with_timeout`, `_process_batch_df`) must remain **nested inside `live_price_poll`** — they use closure variables `redis_client`, `fail_key_prefix`, `service`, and `batch_timeout` from the enclosing scope.

```python
    async def _download_batch(batch: list[str]) -> int:
        """Download prices for a batch of tickers via yf.download. Returns success count."""
        try:
            df = await _yf_download_with_timeout(batch, batch_timeout)
        except asyncio.TimeoutError:
            # Batch timeout — retry once with split halves
            logger.warning(
                "[prices] Batch timeout (%ds) for %d tickers, retrying in halves",
                batch_timeout,
                len(batch),
            )
            mid = len(batch) // 2
            ok = 0
            for half in (batch[:mid], batch[mid:]):
                if not half:
                    continue
                try:
                    df_half = await _yf_download_with_timeout(half, batch_timeout)
                    ok += await _process_batch_df(half, df_half)
                except asyncio.TimeoutError:
                    logger.warning(
                        "[prices] Half-batch timeout for %d tickers, skipping (no penalty)",
                        len(half),
                    )
                except Exception as exc:
                    logger.warning("[prices] Half-batch failed (infrastructure): %s", exc)
            return ok
        except Exception as exc:
            # Non-timeout infrastructure failure — do NOT penalize individual tickers
            logger.warning("[prices] Batch download failed (infrastructure): %s", exc)
            return 0

        return await _process_batch_df(batch, df)

    async def _yf_download_with_timeout(tickers: list[str], timeout: int) -> pd.DataFrame | None:
        """Run yf.download in a thread with asyncio timeout."""
        tickers_str = " ".join(tickers)
        async with asyncio.timeout(timeout):
            return await asyncio.to_thread(
                lambda: yf.download(
                    tickers_str,
                    period="1d",
                    progress=False,
                    threads=True,
                )
            )

    async def _process_batch_df(batch: list[str], df) -> int:
        """Process a yfinance DataFrame and update Redis. Returns success count."""
        if df is None or df.empty:
            return 0

        ok = 0
        is_multi = len(batch) > 1 and isinstance(df.columns, pd.MultiIndex)

        for ticker in batch:
            try:
                if is_multi:
                    if ticker not in df.columns.get_level_values(1):
                        await _record_fail(redis_client, ticker)
                        continue
                    close = df[("Close", ticker)].dropna()
                    if close.empty:
                        await _record_fail(redis_client, ticker)
                        continue
                    last_close = float(close.iloc[-1])
                    last_row = {
                        col: float(df[(col, ticker)].iloc[-1])
                        for col in ("Open", "High", "Low", "Close")
                    }
                    last_row["Volume"] = int(df[("Volume", ticker)].iloc[-1])
                    bar_date = close.index[-1].strftime("%Y-%m-%d")
                else:
                    close_col = df.get("Close")
                    if close_col is None or close_col.dropna().empty:
                        await _record_fail(redis_client, ticker)
                        continue
                    close_col = close_col.dropna()
                    last_close = float(close_col.iloc[-1])
                    last_row = {
                        col: float(df[col].iloc[-1]) for col in ("Open", "High", "Low", "Close")
                    }
                    last_row["Volume"] = int(df["Volume"].iloc[-1])
                    bar_date = close_col.index[-1].strftime("%Y-%m-%d")

                if last_close > 0:
                    await service.set_price(ticker, last_close)
                    bar = {
                        "date": bar_date,
                        "open": last_row["Open"],
                        "high": last_row["High"],
                        "low": last_row["Low"],
                        "close": last_row["Close"],
                        "volume": last_row["Volume"],
                    }
                    await service.set_bar(ticker, bar)
                    # Reset failure counter on success
                    await redis_client.delete(f"{fail_key_prefix}{ticker}")
                    ok += 1
                else:
                    await _record_fail(redis_client, ticker)
            except Exception:
                logger.debug("[prices] Failed to extract %s from batch", ticker)
                await _record_fail(redis_client, ticker)

        return ok
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_workers.py::TestDownloadBatchAttribution api/tests/test_workers.py::TestLivePricePoll -v`
Expected: All pass (new tests + existing tests still green)

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "fix(worker): per-ticker failure attribution, no penalty on batch timeout"
```

---

### Task 3: Implement `retry_quarantined()`

**Files:**
- Modify: `api/src/margin_api/workers.py:2915-2917` (replace stub)
- Modify: `api/src/margin_api/workers.py:4139` (update cron schedule)
- Modify: `api/tests/test_workers.py` (add new test class)

- [ ] **Step 1: Write the failing tests**

Add to `api/tests/test_workers.py`:

```python
class TestRetryQuarantined:
    @pytest.mark.asyncio
    async def test_recovers_ticker_on_successful_download(self):
        """Quarantined ticker with valid yfinance data gets un-quarantined."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import retry_quarantined

        fake_redis = fakeredis.aioredis.FakeRedis()
        # Quarantined ticker
        await fake_redis.set("price_fail:AAPL", "10")
        await fake_redis.expire("price_fail:AAPL", 86400)

        mock_df = pd.DataFrame(
            {"Close": [150.0]},
            index=pd.DatetimeIndex(["2026-03-17"], name="Date"),
        )

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_df),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await retry_quarantined({})

        assert result["status"] == "completed"
        assert result["recovered"] >= 1
        # Counter should be deleted
        assert await fake_redis.get("price_fail:AAPL") is None

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_resets_counter_on_still_failing(self):
        """Ticker that still fails gets counter reset to max_consecutive_fails, not left inflated."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import retry_quarantined

        fake_redis = fakeredis.aioredis.FakeRedis()
        # Inflated counter from misattribution
        await fake_redis.set("price_fail:BAD", "47")

        # Empty DataFrame — ticker still failing
        mock_df = pd.DataFrame()

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_df),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await retry_quarantined({})

        assert result["still_failing"] >= 1
        # Counter should be reset to 5, not left at 47
        count = int(await fake_redis.get("price_fail:BAD"))
        assert count == 5

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_caps_at_50_tickers_per_run(self):
        """Only samples up to 50 quarantined tickers per run."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import retry_quarantined

        fake_redis = fakeredis.aioredis.FakeRedis()
        # Create 100 quarantined tickers
        for i in range(100):
            await fake_redis.set(f"price_fail:TICK{i:03d}", "10")

        mock_df = pd.DataFrame(
            {"Close": [100.0]},
            index=pd.DatetimeIndex(["2026-03-17"], name="Date"),
        )

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_df),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await retry_quarantined({})

        assert result["tested"] <= 50

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_skips_non_quarantined_tickers(self):
        """Tickers with count < 5 are not retried."""
        import fakeredis.aioredis
        from margin_api.workers import retry_quarantined

        fake_redis = fakeredis.aioredis.FakeRedis()
        # Below threshold — should not be retried
        await fake_redis.set("price_fail:LOW", "2")

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download") as mock_dl,
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await retry_quarantined({})

        assert result["tested"] == 0
        mock_dl.assert_not_called()

        await fake_redis.aclose()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_workers.py::TestRetryQuarantined -v`
Expected: FAIL — current stub returns `{"status": "not_implemented"}`

- [ ] **Step 3: Implement `retry_quarantined()`**

Replace stub in `api/src/margin_api/workers.py:2915-2917`:

```python
async def retry_quarantined(ctx: dict) -> dict:
    """Retry quarantined tickers (5+ consecutive failures).

    Samples up to 50 quarantined tickers, re-tests via yf.download in batches
    of 10. Clears failure counter for recovered tickers; resets inflated
    counters to max_consecutive_fails for still-failing ones.
    """
    import random

    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url)
    max_consecutive_fails = 5
    max_sample = 50
    retry_batch_size = 10

    try:
        # Scan for quarantined tickers (price_fail:* with value >= threshold)
        quarantined = []
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(
                cursor=cursor, match="price_fail:*", count=500
            )
            for key in keys:
                val = await redis_client.get(key)
                if val and int(val) >= max_consecutive_fails:
                    # Extract ticker from key
                    key_str = key.decode() if isinstance(key, bytes) else key
                    ticker = key_str.replace("price_fail:", "")
                    quarantined.append(ticker)
            if cursor == 0:
                break

        if not quarantined:
            logger.info("[retry_quarantined] No quarantined tickers found")
            return {"status": "completed", "tested": 0, "recovered": 0, "still_failing": 0}

        # Sample up to max_sample
        sample = random.sample(quarantined, min(len(quarantined), max_sample))

        logger.info(
            "[retry_quarantined] Testing %d of %d quarantined tickers",
            len(sample),
            len(quarantined),
        )

        recovered = 0
        still_failing = 0

        # Process in small batches
        for i in range(0, len(sample), retry_batch_size):
            batch = sample[i : i + retry_batch_size]
            tickers_str = " ".join(batch)

            try:
                df = await asyncio.to_thread(
                    lambda ts=tickers_str: yf.download(
                        ts, period="1d", progress=False, threads=True
                    )
                )
            except Exception as exc:
                logger.warning("[retry_quarantined] Batch download failed: %s", exc)
                continue

            is_multi = len(batch) > 1 and isinstance(
                getattr(df, "columns", None), pd.MultiIndex
            )

            for ticker in batch:
                has_data = False
                try:
                    if df is not None and not df.empty:
                        if is_multi:
                            if ticker in df.columns.get_level_values(1):
                                close = df[("Close", ticker)].dropna()
                                has_data = not close.empty and float(close.iloc[-1]) > 0
                        else:
                            close_col = df.get("Close")
                            if close_col is not None:
                                close_col = close_col.dropna()
                                has_data = not close_col.empty and float(close_col.iloc[-1]) > 0
                except Exception:
                    has_data = False

                key = f"price_fail:{ticker}"
                if has_data:
                    await redis_client.delete(key)
                    recovered += 1
                else:
                    # Reset to exactly max_consecutive_fails with fresh TTL
                    await redis_client.set(key, str(max_consecutive_fails), ex=86400)
                    still_failing += 1

        logger.info(
            "[retry_quarantined] tested=%d, recovered=%d, still_failing=%d",
            len(sample),
            recovered,
            still_failing,
        )
        return {
            "status": "completed",
            "tested": len(sample),
            "recovered": recovered,
            "still_failing": still_failing,
        }
    finally:
        await redis_client.aclose()
```

- [ ] **Step 4: Update cron schedule**

In `api/src/margin_api/workers.py:4139`, change:

```python
# Old:
cron(retry_quarantined, weekday=6, hour=0, run_at_startup=False),  # Sunday midnight
# New:
cron(retry_quarantined, hour={0, 6, 12, 18}, run_at_startup=False),  # Every 6 hours
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_workers.py::TestRetryQuarantined -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "feat(worker): implement retry_quarantined with 6-hourly schedule"
```

---

### Task 4: yfinance TzCache Fix + One-Time Bulk Reset

**Files:**
- Modify: `api/src/margin_api/workers.py:3993-4060` (`on_startup`)

- [ ] **Step 1: Write the failing tests**

Add to `api/tests/test_workers.py`:

```python
class TestWorkerStartupFixes:
    @pytest.mark.asyncio
    async def test_yfinance_tz_cache_set_on_startup(self):
        """Worker startup sets yfinance TzCache to /tmp/yfinance-cache."""
        from margin_api.workers import WorkerSettings

        mock_redis = AsyncMock()
        mock_redis.keys = AsyncMock(return_value=[])
        mock_redis.scan = AsyncMock(return_value=(0, []))
        mock_redis.get = AsyncMock(return_value=b"1")  # bulk reset already done
        ctx = {"redis": mock_redis}

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory") as mock_sf,
            patch("margin_api.workers.yf") as mock_yf,
        ):
            mock_settings.return_value.redis_url = "redis://localhost"
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one = MagicMock(return_value=1)  # PIT count > 0
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_sf.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.return_value.__aexit__ = AsyncMock(return_value=False)

            await WorkerSettings.on_startup(ctx)

        mock_yf.set_tz_cache_location.assert_called_once_with("/tmp/yfinance-cache")

    @pytest.mark.asyncio
    async def test_bulk_reset_clears_price_fail_keys(self):
        """First deploy bulk-resets all price_fail:* keys."""
        import fakeredis.aioredis
        from margin_api.workers import WorkerSettings

        fake_redis = fakeredis.aioredis.FakeRedis()
        # Simulate quarantined tickers
        await fake_redis.set("price_fail:AAPL", "10")
        await fake_redis.set("price_fail:MSFT", "7")

        ctx = {"redis": fake_redis}

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory") as mock_sf,
        ):
            mock_settings.return_value.redis_url = "redis://localhost"
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one = MagicMock(return_value=1)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_sf.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.return_value.__aexit__ = AsyncMock(return_value=False)

            await WorkerSettings.on_startup(ctx)

        # All price_fail keys should be deleted
        assert await fake_redis.get("price_fail:AAPL") is None
        assert await fake_redis.get("price_fail:MSFT") is None
        # Flag key should be set
        assert await fake_redis.get("price_fail_bulk_reset_done") is not None

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_bulk_reset_runs_only_once(self):
        """Second startup skips bulk reset if flag key exists."""
        import fakeredis.aioredis
        from margin_api.workers import WorkerSettings

        fake_redis = fakeredis.aioredis.FakeRedis()
        # Flag already set from first deploy
        await fake_redis.set("price_fail_bulk_reset_done", "1")
        # This should NOT be deleted
        await fake_redis.set("price_fail:AAPL", "3")

        ctx = {"redis": fake_redis}

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory") as mock_sf,
        ):
            mock_settings.return_value.redis_url = "redis://localhost"
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one = MagicMock(return_value=1)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_sf.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.return_value.__aexit__ = AsyncMock(return_value=False)

            await WorkerSettings.on_startup(ctx)

        # Key should still exist — bulk reset was skipped
        assert await fake_redis.get("price_fail:AAPL") is not None

        await fake_redis.aclose()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_workers.py::TestWorkerStartupFixes -v`
Expected: FAIL — current `on_startup` doesn't set TzCache or do bulk reset

- [ ] **Step 3: Implement startup fixes**

Add two blocks to `WorkerSettings.on_startup()` in `api/src/margin_api/workers.py`. Insert after the Sentry init block (after line 4004) and before the stale ingestion cleanup:

After the Sentry init (after line 4004), add:

```python
        # Fix yfinance TzCache permission errors in containers
        yf.set_tz_cache_location("/tmp/yfinance-cache")
```

After the orphaned ARQ key cleanup (after line 4060), add the bulk reset block:

```python
        # One-time bulk reset of corrupted price_fail:* keys (misattribution bug fix)
        try:
            redis_pool: ArqRedis | None = ctx.get("redis")
            if redis_pool:
                already_done = await redis_pool.get("price_fail_bulk_reset_done")
                if not already_done:
                    deleted = 0
                    cursor = 0
                    while True:
                        cursor, keys = await redis_pool.scan(
                            cursor=cursor, match="price_fail:*", count=500
                        )
                        if keys:
                            await redis_pool.delete(*keys)
                            deleted += len(keys)
                        if cursor == 0:
                            break
                    # Set flag so this only runs once
                    await redis_pool.set("price_fail_bulk_reset_done", "1")
                    if deleted:
                        logger.info(
                            "[worker] Bulk-reset %d corrupted price_fail keys", deleted
                        )
                else:
                    logger.debug("[worker] price_fail bulk reset already done, skipping")
        except Exception:
            logger.exception("[worker] Failed to bulk-reset price_fail keys")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_workers.py::TestWorkerStartupFixes -v`
Expected: 3 passed

- [ ] **Step 5: Run all existing worker tests to verify no regressions**

Run: `uv run pytest api/tests/test_workers.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "fix(worker): yfinance TzCache + one-time bulk reset of quarantine data"
```

---

### Task 5: Reduce `expire_stale_approvals` Frequency + Dedup Guard

**Files:**
- Modify: `api/src/margin_api/workers.py:1426-1440` (`expire_stale_approvals`)
- Modify: `api/src/margin_api/workers.py:4144` (cron schedule)
- Modify: `api/tests/test_workers.py` (add new test class)

- [ ] **Step 1: Write the failing tests**

Add to `api/tests/test_workers.py`:

```python
class TestExpireStaleApprovalsDedup:
    @pytest.mark.asyncio
    async def test_skips_if_lock_exists(self):
        """expire_stale_approvals skips execution if Redis lock exists."""
        import fakeredis.aioredis
        from margin_api.workers import expire_stale_approvals

        fake_redis = fakeredis.aioredis.FakeRedis()
        # Lock already set — should skip
        await fake_redis.set("expire_approvals_lock", "1")

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.get_engine") as mock_engine,
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await expire_stale_approvals({})

        assert result["status"] == "skipped_dedup"
        # Should not have called get_engine (no DB work)
        mock_engine.assert_not_called()

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_sets_lock_on_execution(self):
        """expire_stale_approvals sets Redis lock when it runs."""
        import fakeredis.aioredis
        from margin_api.workers import expire_stale_approvals

        fake_redis = fakeredis.aioredis.FakeRedis()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await expire_stale_approvals({})

        assert result["status"] == "completed"
        # Lock should now exist with TTL
        lock_val = await fake_redis.get("expire_approvals_lock")
        assert lock_val is not None
        ttl = await fake_redis.ttl("expire_approvals_lock")
        assert 17000 < ttl <= 18000  # ~5h

        await fake_redis.aclose()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_workers.py::TestExpireStaleApprovalsDedup -v`
Expected: FAIL — current code has no dedup guard

- [ ] **Step 3: Implement dedup guard + schedule change**

Replace `expire_stale_approvals` in `api/src/margin_api/workers.py:1426-1440`:

```python
async def expire_stale_approvals(ctx: dict) -> dict:
    """Worker entry point: expire staged PipelineApprovals past their deadline.

    Runs every 12 hours. Uses a Redis lock to detect unexpected re-triggering.
    """
    settings = get_settings()
    redis_client = aioredis.from_url(settings.redis_url)

    try:
        # Dedup guard: skip if already executed recently (5h lock)
        acquired = await redis_client.set(
            "expire_approvals_lock", "1", nx=True, ex=18000
        )
        if not acquired:
            logger.warning(
                "[expire_stale_approvals] Skipped — lock exists (ran recently)"
            )
            return {"status": "skipped_dedup"}
    except Exception:
        logger.debug("[expire_stale_approvals] Redis lock check failed, proceeding anyway")
    finally:
        await redis_client.aclose()

    logger.info("[expire_stale_approvals] Starting expiry check")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        expired_count = await _expire_stale_approvals_impl(session)

    logger.info("[expire_stale_approvals] Expired %d stale approvals", expired_count)
    return {"status": "completed", "expired_count": expired_count}
```

Update cron schedule in `api/src/margin_api/workers.py:4144`:

```python
# Old:
cron(expire_stale_approvals, hour={0, 6, 12, 18}, run_at_startup=False),
# New:
cron(expire_stale_approvals, hour={0, 12}, run_at_startup=False),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_workers.py::TestExpireStaleApprovalsDedup -v`
Expected: 2 passed

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `uv run pytest api/tests/test_workers.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "fix(worker): reduce expire_stale_approvals to 2x daily, add dedup guard"
```

---

### Task 6: Final Verification

**Files:** None — verification only

- [ ] **Step 1: Run full API test suite**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All ~1699+ tests pass

- [ ] **Step 2: Run ruff lint check**

Run: `uv run ruff check api/src/margin_api/workers.py api/tests/test_workers.py`
Expected: No errors

- [ ] **Step 3: Run ruff format check**

Run: `uv run ruff format --check api/src/margin_api/workers.py api/tests/test_workers.py`
Expected: No formatting issues (or auto-fix with `ruff format`)

- [ ] **Step 4: Verify cron schedule summary**

Manually verify in `workers.py` that the cron_jobs list shows:
- `retry_quarantined`: `hour={0, 6, 12, 18}` (was `weekday=6, hour=0`)
- `expire_stale_approvals`: `hour={0, 12}` (was `hour={0, 6, 12, 18}`)
- All other cron schedules unchanged

- [ ] **Step 5: Final commit if any lint fixes were needed**

```bash
git add -u
git commit -m "chore: lint fixes for worker health changes"
```
