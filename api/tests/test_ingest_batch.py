"""Tests for ingest_batch worker job."""

from __future__ import annotations

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
    mock_session.execute = AsyncMock(
        return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None),
            scalar_one=MagicMock(
                return_value=MagicMock(
                    tickers_succeeded=0,
                    tickers_failed=0,
                    tickers_partial=0,
                ),
            ),
        ),
    )

    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory, mock_session


def _patch_deps(factory, seed_mock, limiter_cls=None):
    """Build the standard set of context-manager patches for ingest_batch tests.

    Returns a tuple of (patches_context_manager, mock_holders) where mock_holders
    is a dict of mock objects that need further configuration.
    """
    import contextlib

    class _Patches:
        def __init__(self):
            self.mock_settings = None
            self.mock_aioredis = None
            self.mock_breaker_cls = None

        @contextlib.contextmanager
        def __call__(self):
            with (
                patch("margin_api.workers.get_engine"),
                patch("margin_api.workers.get_session_factory", return_value=factory),
                patch("margin_api.workers.get_settings") as mock_settings,
                patch("margin_api.workers.aioredis") as mock_aioredis,
                patch("margin_api.cli.seed_ticker_data", **seed_mock),
                patch(
                    "margin_api.services.redis_rate_limiter.RedisRateLimiter",
                    **({"return_value": limiter_cls} if limiter_cls else {}),
                ) as mock_limiter,
                patch(
                    "margin_engine.ingestion.circuit_breaker.CircuitBreaker",
                ) as mock_breaker,
                patch(
                    "margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider",
                ),
            ):
                mock_settings.return_value.ingest_rate_limit = 36
                mock_settings.return_value.redis_url = "redis://localhost:6379"
                mock_aioredis.from_url.return_value = AsyncMock(aclose=AsyncMock())
                mock_limiter.return_value.wait_and_acquire = AsyncMock()
                mock_breaker.return_value.allow_request.return_value = True
                mock_breaker.return_value.record_success = MagicMock()
                mock_breaker.return_value.record_failure = MagicMock()
                yield

    return _Patches()


class TestIngestBatch:
    @pytest.mark.asyncio
    async def test_processes_all_tickers(self):
        from margin_api.services.seed_result import SeedResult

        factory, _session = _make_mock_session_factory()
        seed_result = SeedResult(status="ok", categories_succeeded=["price"])

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.get = AsyncMock(return_value="5")
        ctx = _make_ctx(mock_redis)

        patches = _patch_deps(
            factory,
            {"new_callable": AsyncMock, "return_value": seed_result},
        )
        with patches():
            from margin_api.workers import ingest_batch

            result = await ingest_batch(
                ctx, "1", "abc123", ["AAPL", "MSFT", "GOOG"], 1,
            )

        assert result["status"] == "completed"
        assert result["succeeded"] == 3
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_records_failures_without_aborting(self):
        from margin_api.services.seed_result import SeedResult

        factory, _session = _make_mock_session_factory()

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.get = AsyncMock(return_value="5")
        mock_redis.rpush = AsyncMock()
        ctx = _make_ctx(mock_redis)

        results = [
            SeedResult(status="ok", categories_succeeded=["price"]),
            SeedResult(status="failed", error_message="yfinance timeout"),
            SeedResult(status="ok", categories_succeeded=["price"]),
        ]
        call_count = 0

        async def mock_seed(*args, **kwargs):
            nonlocal call_count
            r = results[call_count]
            call_count += 1
            return r

        patches = _patch_deps(factory, {"side_effect": mock_seed})
        with patches():
            from margin_api.workers import ingest_batch

            result = await ingest_batch(
                ctx, "1", "abc123", ["AAPL", "FAIL", "GOOG"], 1,
            )

        assert result["succeeded"] == 2
        assert result["failed"] == 1
        mock_redis.rpush.assert_called()

    @pytest.mark.asyncio
    async def test_last_batch_enqueues_sweep(self):
        from margin_api.services.seed_result import SeedResult

        factory, _session = _make_mock_session_factory()
        seed_result = SeedResult(status="ok", categories_succeeded=["price"])

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=5)
        mock_redis.get = AsyncMock(return_value="5")
        ctx = _make_ctx(mock_redis)

        patches = _patch_deps(
            factory,
            {"new_callable": AsyncMock, "return_value": seed_result},
        )
        with patches():
            from margin_api.workers import ingest_batch

            result = await ingest_batch(ctx, "1", "abc123", ["AAPL"], 5)

        assert result["is_last_batch"] is True
        sweep_calls = [
            c
            for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "ingest_sweep"
        ]
        assert len(sweep_calls) == 1


class TestIngestBatchSweep:
    @pytest.mark.asyncio
    async def test_sweep_batch_enqueues_sweep_complete(self):
        from margin_api.services.seed_result import SeedResult

        factory, _session = _make_mock_session_factory()
        seed_result = SeedResult(status="ok", categories_succeeded=["price"])

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.get = AsyncMock(return_value="1")
        ctx = _make_ctx(mock_redis)

        patches = _patch_deps(
            factory,
            {"new_callable": AsyncMock, "return_value": seed_result},
        )
        with patches():
            from margin_api.workers import ingest_batch

            await ingest_batch(
                ctx, "1", "abc123", ["AAPL"], 0, is_sweep=True,
            )

        complete_calls = [
            c
            for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "ingest_sweep_complete"
        ]
        assert len(complete_calls) == 1


class TestIngestBatchRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limiter_called_per_ticker(self):
        from margin_api.services.seed_result import SeedResult

        factory, _session = _make_mock_session_factory()
        seed_result = SeedResult(status="ok", categories_succeeded=["price"])

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.get = AsyncMock(return_value="5")
        ctx = _make_ctx(mock_redis)

        mock_limiter_instance = AsyncMock()
        mock_limiter_instance.wait_and_acquire = AsyncMock()

        patches = _patch_deps(
            factory,
            {"new_callable": AsyncMock, "return_value": seed_result},
            limiter_cls=mock_limiter_instance,
        )
        with patches():
            from margin_api.workers import ingest_batch

            await ingest_batch(
                ctx, "1", "abc123", ["AAPL", "MSFT", "GOOG"], 1,
            )

        assert mock_limiter_instance.wait_and_acquire.call_count == 3
