"""Tests for ARQ worker configuration and job functions."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.services.seed_result import SeedResult
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


def _mock_session_factory():
    """Create a mock session factory used across pipeline tests."""
    mock_session = AsyncMock()
    mock_job = MagicMock()
    mock_job.id = 1

    def _set_id_on_add(obj):
        """Simulate DB assigning an ID on add+commit."""
        obj.id = 1

    mock_session.add = MagicMock(side_effect=_set_id_on_add)
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=MagicMock(
            scalar_one=MagicMock(return_value=mock_job),
        ),
    )

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_factory, mock_session, mock_job


class TestFullIngest:
    @pytest.mark.asyncio
    async def test_full_ingest_no_snapshot(self):
        """full_ingest returns error when no active universe snapshot."""
        from margin_api.workers import full_ingest

        mock_factory, mock_session, _ = _mock_session_factory()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
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
        mock_session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one=MagicMock(return_value=mock_run),
            ),
        )

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
            patch(
                "margin_api.cli.seed_ticker_data",
                return_value=SeedResult(status="ok"),
            ),
            patch("margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider"),
            patch("margin_engine.ingestion.rate_limiter.RateLimiter"),
        ):
            result = await full_ingest({"redis": mock_redis})

        assert result["status"] == "completed"
        assert result["succeeded"] == 2
        assert result["partial"] == 0
        assert result["pipeline_id"] is not None
        # Chains to full_score with the pipeline_id
        mock_redis.enqueue_job.assert_called_once()
        call_args = mock_redis.enqueue_job.call_args
        assert call_args[0][0] == "full_score"
        assert call_args[0][1] == result["pipeline_id"]

    @pytest.mark.asyncio
    async def test_full_ingest_generates_pipeline_id(self):
        """full_ingest generates a pipeline_id when none is provided."""
        from margin_api.workers import full_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "2026.02.19"
        mock_snapshot.tickers = ["AAPL"]

        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.id = 1
        mock_run.started_at = datetime.now(UTC)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one=MagicMock(return_value=mock_run)),
        )

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch("margin_api.cli.seed_ticker_data", return_value=SeedResult(status="ok")),
            patch("margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider"),
            patch("margin_engine.ingestion.rate_limiter.RateLimiter"),
        ):
            result = await full_ingest({"redis": mock_redis})

        assert result["pipeline_id"] is not None
        assert len(result["pipeline_id"]) == 16

    @pytest.mark.asyncio
    async def test_full_ingest_passes_provided_pipeline_id(self):
        """full_ingest uses the pipeline_id passed to it."""
        from margin_api.workers import full_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "2026.02.19"
        mock_snapshot.tickers = ["AAPL"]

        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.id = 1
        mock_run.started_at = datetime.now(UTC)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one=MagicMock(return_value=mock_run)),
        )

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch("margin_api.cli.seed_ticker_data", return_value=SeedResult(status="ok")),
            patch("margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider"),
            patch("margin_engine.ingestion.rate_limiter.RateLimiter"),
        ):
            result = await full_ingest({"redis": mock_redis}, pipeline_id="custom-id-123")

        assert result["pipeline_id"] == "custom-id-123"

    @pytest.mark.asyncio
    async def test_full_ingest_warns_when_no_redis(self, caplog):
        """full_ingest logs a warning when redis is not in worker context."""
        from margin_api.workers import full_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "2026.02.19"
        mock_snapshot.tickers = ["AAPL"]

        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.id = 1
        mock_run.started_at = datetime.now(UTC)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one=MagicMock(return_value=mock_run)),
        )

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch("margin_api.cli.seed_ticker_data", return_value=SeedResult(status="ok")),
            patch("margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider"),
            patch("margin_engine.ingestion.rate_limiter.RateLimiter"),
        ):
            # Pass empty dict — no redis key
            result = await full_ingest({})

        assert result["status"] == "completed"
        assert "cannot chain to full_score" in caplog.text


class TestFullScore:
    @pytest.mark.asyncio
    async def test_full_score_chains_to_v3(self):
        """full_score calls run_scoring and enqueues full_score_v3."""
        from margin_api.workers import full_score

        mock_factory, mock_session, mock_job = _mock_session_factory()
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score({"redis": mock_redis}, pipeline_id="pipe-123")

        assert result["status"] == "completed"
        assert result["pipeline_id"] == "pipe-123"
        # Chains with pipeline_id and parent job_id
        mock_redis.enqueue_job.assert_called_once_with("full_score_v3", "pipe-123", mock_job.id)

    @pytest.mark.asyncio
    async def test_full_score_handles_failure(self):
        """full_score records failure in JobRun on exception."""
        from margin_api.workers import full_score

        mock_factory, _, _ = _mock_session_factory()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring", side_effect=RuntimeError("Scoring failed")),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score({})

        assert result["status"] == "failed"
        assert "Scoring failed" in result["error"]

    @pytest.mark.asyncio
    async def test_full_score_chains_to_v3_even_on_failure(self):
        """full_score enqueues full_score_v3 even when v2 scoring fails (gap #1)."""
        from margin_api.workers import full_score

        mock_factory, _, mock_job = _mock_session_factory()
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring", side_effect=RuntimeError("V2 exploded")),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score({"redis": mock_redis}, pipeline_id="pipe-456")

        # V2 failed but v3 was still enqueued
        assert result["status"] == "failed"
        assert "V2 exploded" in result["error"]
        mock_redis.enqueue_job.assert_called_once_with("full_score_v3", "pipe-456", mock_job.id)

    @pytest.mark.asyncio
    async def test_full_score_warns_when_no_redis(self, caplog):
        """full_score logs a warning when redis is not in worker context (gap #2)."""
        from margin_api.workers import full_score

        mock_factory, _, _ = _mock_session_factory()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score({})

        assert result["status"] == "completed"
        assert "cannot chain to full_score_v3" in caplog.text

    @pytest.mark.asyncio
    async def test_full_score_propagates_pipeline_id(self):
        """full_score passes pipeline_id and parent_job_id to v3 (gap #3)."""
        from margin_api.workers import full_score

        mock_factory, _, mock_job = _mock_session_factory()
        mock_redis = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            await full_score({"redis": mock_redis}, pipeline_id="pipe-789")

        call_args = mock_redis.enqueue_job.call_args[0]
        assert call_args[0] == "full_score_v3"
        assert call_args[1] == "pipe-789"       # pipeline_id
        assert call_args[2] == mock_job.id       # parent_job_id


class TestFullScoreV3:
    @pytest.mark.asyncio
    async def test_full_score_v3_completes(self):
        """full_score_v3 calls run_scoring_v3 and records completion."""
        from margin_api.workers import full_score_v3

        mock_factory, _, _ = _mock_session_factory()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring_v3", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score_v3({})

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_full_score_v3_records_parent_job_id(self):
        """full_score_v3 stores parent_job_id on its JobRun record (gap #3)."""
        from margin_api.workers import full_score_v3

        mock_session = AsyncMock()
        mock_job = MagicMock()
        mock_job.id = 10
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one=MagicMock(return_value=mock_job)),
        )

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring_v3", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score_v3(
                {}, pipeline_id="pipe-abc", parent_job_id=42
            )

        assert result["status"] == "completed"
        assert result["pipeline_id"] == "pipe-abc"

        # Verify the JobRun was created with parent_job_id and pipeline_id
        add_call = mock_session.add.call_args[0][0]
        assert add_call.parent_job_id == 42
        assert add_call.pipeline_id == "pipe-abc"

    @pytest.mark.asyncio
    async def test_full_score_v3_handles_failure(self):
        """full_score_v3 records failure and returns pipeline_id."""
        from margin_api.workers import full_score_v3

        mock_factory, _, _ = _mock_session_factory()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring_v3", side_effect=RuntimeError("V3 boom")),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score_v3({}, pipeline_id="pipe-fail")

        assert result["status"] == "failed"
        assert result["pipeline_id"] == "pipe-fail"
        assert "V3 boom" in result["error"]


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
