"""Tests for ARQ worker configuration and job functions."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from margin_api.workers import WorkerSettings


class TestWorkerSettings:
    def test_has_redis_settings(self):
        assert WorkerSettings.redis_settings is not None

    def test_has_functions(self):
        assert len(WorkerSettings.functions) >= 5

    def test_has_cron_jobs(self):
        assert len(WorkerSettings.cron_jobs) >= 2

    def test_function_names(self):
        names = [f.__name__ for f in WorkerSettings.functions]
        assert "full_ingest" in names
        assert "full_score" in names
        assert "full_score_v3" in names
        assert "backtest_validate" in names
        assert "live_price_poll" in names
        assert "retry_quarantined" in names

    def test_job_timeout_set(self):
        assert WorkerSettings.job_timeout >= 3600


class TestFullIngest:
    @pytest.mark.asyncio
    async def test_full_ingest_no_snapshot(self):
        """full_ingest returns error when no active universe snapshot."""
        from margin_api.workers import full_ingest

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_active_snapshot", return_value=None),
        ):
            result = await full_ingest({})

        assert result["status"] == "error"
        assert "No active universe snapshot" in result["message"]

    @pytest.mark.asyncio
    async def test_full_ingest_chains_to_scoring(self):
        """full_ingest enqueues full_score after completion."""
        from margin_api.workers import full_ingest

        # Mock snapshot
        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "2026.02.19"
        mock_snapshot.tickers = ["AAPL", "MSFT"]

        # Mock session
        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.id = 1
        mock_run.started_at = datetime.now(UTC)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_run)))

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # Mock Redis for job chaining
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch("margin_api.cli.seed_ticker_data", return_value="ok"),
            patch("margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider"),
            patch("margin_engine.ingestion.rate_limiter.RateLimiterRegistry") as mock_registry,
        ):
            mock_limiter = MagicMock()
            mock_registry.return_value.get.return_value = mock_limiter

            result = await full_ingest({"redis": mock_redis})

        assert result["status"] == "completed"
        assert result["succeeded"] == 2
        mock_redis.enqueue_job.assert_called_once_with("full_score")


class TestFullScore:
    @pytest.mark.asyncio
    async def test_full_score_chains_to_v3(self):
        """full_score calls run_scoring and enqueues full_score_v3."""
        from margin_api.workers import full_score

        mock_session = AsyncMock()
        mock_job = MagicMock()
        mock_job.id = 1
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_job)))

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.cli.run_scoring", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score({"redis": mock_redis})

        assert result["status"] == "completed"
        mock_redis.enqueue_job.assert_called_once_with("full_score_v3")

    @pytest.mark.asyncio
    async def test_full_score_handles_failure(self):
        """full_score records failure in JobRun on exception."""
        from margin_api.workers import full_score

        mock_session = AsyncMock()
        mock_job = MagicMock()
        mock_job.id = 1
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_job)))

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.cli.run_scoring", side_effect=RuntimeError("Scoring failed")),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score({})

        assert result["status"] == "failed"
        assert "Scoring failed" in result["error"]


class TestFullScoreV3:
    @pytest.mark.asyncio
    async def test_full_score_v3_completes(self):
        """full_score_v3 calls run_scoring_v3 and records completion."""
        from margin_api.workers import full_score_v3

        mock_session = AsyncMock()
        mock_job = MagicMock()
        mock_job.id = 1
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=mock_job)))

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.cli.run_scoring_v3", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score_v3({})

        assert result["status"] == "completed"


class TestLivePricePoll:
    @pytest.mark.asyncio
    async def test_live_price_poll_no_recommendations(self):
        """Returns no_recommendations when no high-conviction tickers exist."""
        from margin_api.workers import live_price_poll

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
        ):
            result = await live_price_poll({})

        assert result["status"] == "no_recommendations"
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_live_price_poll_with_tickers(self):
        """Fetches prices for recommended tickers and stores in Redis."""
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

        mock_ticker = MagicMock()
        mock_ticker.fast_info = MagicMock()
        mock_ticker.fast_info.last_price = 185.50

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.Ticker", return_value=mock_ticker),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        assert result["status"] == "completed"
        assert result["updated"] == 1

        from margin_api.services.live_prices import LivePriceService

        service = LivePriceService(fake_redis)
        cached = await service.get_price("AAPL")
        assert cached is not None
        assert cached["price"] == 185.50

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_live_price_poll_skips_failed_tickers(self):
        """A failing ticker is skipped gracefully."""
        import fakeredis.aioredis

        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",), ("BAD",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        def mock_ticker_factory(ticker):
            if ticker == "BAD":
                raise Exception("yfinance error")
            mock_t = MagicMock()
            mock_t.fast_info = MagicMock()
            mock_t.fast_info.last_price = 100.0
            return mock_t

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.Ticker", side_effect=mock_ticker_factory),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        assert result["status"] == "completed"
        assert result["updated"] == 1

        await fake_redis.aclose()


class TestBacktestValidate:
    @pytest.mark.asyncio
    async def test_backtest_validate_not_implemented(self):
        from margin_api.workers import backtest_validate

        result = await backtest_validate({})
        assert result["status"] == "not_implemented"
