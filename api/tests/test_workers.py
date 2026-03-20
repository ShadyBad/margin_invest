"""Tests for ARQ worker configuration and job functions."""

from __future__ import annotations

import asyncio
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
        names = [f.name if hasattr(f, "name") else f.__name__ for f in WorkerSettings.functions]
        assert "orchestrate_ingest" in names
        assert "ingest_batch" in names
        assert "ingest_sweep" in names
        assert "ingest_sweep_complete" in names
        assert "full_score_v3" in names
        assert "full_score_v4" in names
        assert "backtest_validate" in names
        assert "live_price_poll" in names
        assert "retry_quarantined" in names

    def test_job_timeout_set(self):
        assert WorkerSettings.job_timeout <= 1800


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
            result = await full_score_v3({}, pipeline_id="pipe-abc", parent_job_id=42)

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


class TestFullScoreV4:
    @pytest.mark.asyncio
    async def test_full_score_v4_completes(self):
        """full_score_v4 calls run_scoring_v4 and records completion."""
        from margin_api.workers import full_score_v4

        mock_factory, _, _ = _mock_session_factory()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring_v4", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score_v4({})

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_full_score_v4_handles_failure(self):
        """full_score_v4 records failure in JobRun on exception."""
        from margin_api.workers import full_score_v4

        mock_factory, _, _ = _mock_session_factory()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring_v4", side_effect=RuntimeError("V4 boom")),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score_v4({}, pipeline_id="pipe-v4")

        assert result["status"] == "failed"
        assert result["pipeline_id"] == "pipe-v4"
        assert "V4 boom" in result["error"]

    @pytest.mark.asyncio
    async def test_full_score_v4_records_parent_job_id(self):
        """full_score_v4 stores parent_job_id and pipeline_id on its JobRun."""
        from margin_api.workers import full_score_v4

        mock_session = AsyncMock()
        mock_job = MagicMock()
        mock_job.id = 20
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
            patch("margin_api.cli.run_scoring_v4", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score_v4({}, pipeline_id="pipe-v4-abc", parent_job_id=99)

        assert result["status"] == "completed"
        assert result["pipeline_id"] == "pipe-v4-abc"

        # Verify the JobRun was created with parent_job_id and pipeline_id
        # Find the JobRun among all session.add() calls (ReproducibilityAudit may also be added)
        job_runs = [
            call[0][0]
            for call in mock_session.add.call_args_list
            if hasattr(call[0][0], "parent_job_id")
        ]
        assert len(job_runs) >= 1
        add_call = job_runs[0]
        assert add_call.parent_job_id == 99
        assert add_call.pipeline_id == "pipe-v4-abc"

    @pytest.mark.asyncio
    async def test_full_score_v3_chains_to_v4(self):
        """full_score_v3 enqueues full_score_v4 after completion."""
        from margin_api.workers import full_score_v3

        mock_factory, _, mock_job = _mock_session_factory()
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring_v3", new_callable=AsyncMock),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score_v3({"redis": mock_redis}, pipeline_id="pipe-chain")

        assert result["status"] == "completed"
        mock_redis.enqueue_job.assert_called_once()
        call_kwargs = mock_redis.enqueue_job.call_args
        assert call_kwargs[0][0] == "full_score_v4"
        assert call_kwargs[1]["pipeline_id"] == "pipe-chain"
        assert call_kwargs[1]["parent_job_id"] == mock_job.id

    @pytest.mark.asyncio
    async def test_full_score_v3_chains_to_v4_even_on_failure(self):
        """full_score_v3 enqueues full_score_v4 even when v3 scoring fails."""
        from margin_api.workers import full_score_v3

        mock_factory, _, mock_job = _mock_session_factory()
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring_v3", side_effect=RuntimeError("V3 crash")),
            patch("margin_api.workers.reset_engine_cache"),
        ):
            result = await full_score_v3({"redis": mock_redis}, pipeline_id="pipe-fail-chain")

        # V3 failed but v4 was still enqueued
        assert result["status"] == "failed"
        assert "V3 crash" in result["error"]
        mock_redis.enqueue_job.assert_called_once()
        call_kwargs = mock_redis.enqueue_job.call_args
        assert call_kwargs[0][0] == "full_score_v4"
        assert call_kwargs[1]["pipeline_id"] == "pipe-fail-chain"


class TestScoringTimeouts:
    @pytest.mark.asyncio
    async def test_full_score_v4_timeout_marks_failed(self):
        """full_score_v4 times out and records failure when scoring hangs."""
        from margin_api.workers import full_score_v4

        mock_factory, _, _ = _mock_session_factory()

        async def _hang_forever():
            await asyncio.sleep(9999)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring_v4", side_effect=_hang_forever),
            patch("margin_api.workers.reset_engine_cache"),
            patch("margin_api.workers.SCORING_V4_TIMEOUT", 0.01),
        ):
            result = await full_score_v4({}, pipeline_id="pipe-timeout")

        assert result["status"] == "failed"
        assert "timed out" in result["error"].lower() or "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_full_score_v3_timeout_marks_failed(self):
        """full_score_v3 times out and records failure when scoring hangs."""
        from margin_api.workers import full_score_v3

        mock_factory, _, _ = _mock_session_factory()
        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        async def _hang_forever():
            await asyncio.sleep(9999)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.cli.run_scoring_v3", side_effect=_hang_forever),
            patch("margin_api.workers.reset_engine_cache"),
            patch("margin_api.workers.SCORING_V3_TIMEOUT", 0.01),
        ):
            result = await full_score_v3({"redis": mock_redis}, pipeline_id="pipe-v3-timeout")

        assert result["status"] == "failed"
        assert "timed out" in result["error"].lower() or "timeout" in result["error"].lower()
        # Should still chain to v4 even on timeout
        mock_redis.enqueue_job.assert_called_once()


class TestLivePricePoll:
    @pytest.mark.asyncio
    async def test_live_price_poll_no_recommendations(self):
        """Returns no_scored_tickers when no scored tickers exist."""
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

        assert result["status"] == "no_scored_tickers"
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_live_price_poll_with_tickers(self):
        """Fetches prices for recommended tickers and stores in Redis."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # yf.download with a single ticker returns a flat DataFrame (no MultiIndex)
        mock_download_df = pd.DataFrame(
            {
                "Open": [184.00],
                "High": [186.00],
                "Low": [183.50],
                "Close": [185.50],
                "Volume": [3000000],
            },
            index=pd.DatetimeIndex(["2026-03-16"], name="Date"),
        )

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_download_df),
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
        """Tickers with 5+ consecutive failures are skipped via Redis counter."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()
        # Pre-set failure counter for BAD ticker to trigger skip
        await fake_redis.set("price_fail:BAD", "5")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",), ("BAD",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_download_df = pd.DataFrame(
            {
                "Open": [99.0],
                "High": [101.0],
                "Low": [98.0],
                "Close": [100.0],
                "Volume": [1000000],
            },
            index=pd.DatetimeIndex(["2026-03-16"], name="Date"),
        )

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_download_df),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        assert result["status"] == "completed"
        assert result["updated"] == 1
        assert result["skipped"] == 1  # BAD was skipped

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_live_price_poll_stores_bar_data(self):
        """Stores OHLCV bar in Redis alongside price."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # yf.download with single ticker returns flat DataFrame
        mock_download_df = pd.DataFrame(
            {
                "Open": [188.50],
                "High": [192.30],
                "Low": [187.20],
                "Close": [191.75],
                "Volume": [4523000],
            },
            index=pd.DatetimeIndex(["2026-03-06"], name="Date"),
        )

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_download_df),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        assert result["status"] == "completed"

        from margin_api.services.live_prices import LivePriceService

        service = LivePriceService(fake_redis)

        bar = await service.get_bar("AAPL")
        assert bar is not None
        assert bar["date"] == "2026-03-06"
        assert bar["close"] == 191.75
        assert bar["volume"] == 4523000

        price = await service.get_price("AAPL")
        assert price is not None
        assert price["price"] == 191.75

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_live_price_poll_all_scored_tickers(self):
        """Polls all scored tickers, not just high conviction."""
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

        # yf.download with multiple tickers returns MultiIndex columns
        idx = pd.DatetimeIndex(["2026-03-06"], name="Date")
        mock_download_df = pd.DataFrame(
            {
                ("Open", "AAPL"): [99.0],
                ("High", "AAPL"): [101.0],
                ("Low", "AAPL"): [98.0],
                ("Close", "AAPL"): [100.0],
                ("Volume", "AAPL"): [1000],
                ("Open", "MSFT"): [399.0],
                ("High", "MSFT"): [401.0],
                ("Low", "MSFT"): [398.0],
                ("Close", "MSFT"): [400.0],
                ("Volume", "MSFT"): [2000],
            },
            index=idx,
        )
        mock_download_df.columns = pd.MultiIndex.from_tuples(mock_download_df.columns)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_download_df),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        assert result["updated"] == 2

        from margin_api.services.live_prices import LivePriceService

        service = LivePriceService(fake_redis)
        assert await service.get_bar("AAPL") is not None
        assert await service.get_bar("MSFT") is not None

        await fake_redis.aclose()


class TestBacktestValidate:
    @pytest.mark.asyncio
    async def test_backtest_validate_no_data(self):
        """backtest_validate completes with message when no V3Score data exists."""
        from margin_api.workers import backtest_validate

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []  # No V3Scores
        mock_session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 1))
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
        ):
            result = await backtest_validate({})

        assert result["status"] == "completed"
        assert "No V3Score data" in result["message"]

    @pytest.mark.asyncio
    async def test_backtest_validate_creates_job_run(self):
        """backtest_validate creates a JobRun with job_type='backtest_validate'."""
        from margin_api.workers import backtest_validate

        added_objects = []

        mock_session = AsyncMock()
        mock_result_empty = MagicMock()
        mock_result_empty.all.return_value = []

        call_count = 0

        async def _mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                # First call: commit after adding JobRun
                return mock_result_empty
            # Second call: V3Score query returns empty
            return mock_result_empty

        def _add_obj(obj):
            setattr(obj, "id", 1)
            added_objects.append(obj)

        mock_session.add = MagicMock(side_effect=_add_obj)
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=_mock_execute)

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
        ):
            await backtest_validate({})

        # Verify a JobRun was added
        from margin_api.db.models import JobRun as JobRunModel

        job_runs = [o for o in added_objects if isinstance(o, JobRunModel)]
        assert len(job_runs) >= 1
        assert job_runs[0].job_type == "backtest_validate"

    @pytest.mark.asyncio
    async def test_backtest_validate_handles_exception(self):
        """backtest_validate records failure on exception."""
        from margin_api.workers import backtest_validate

        mock_job = MagicMock()
        mock_job.id = 1

        session_num = 0
        raised = False

        mock_session = AsyncMock()
        mock_session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 1))
        mock_session.commit = AsyncMock()

        async def _mock_enter(*a):
            nonlocal session_num
            session_num += 1
            return mock_session

        async def _mock_execute(stmt):
            nonlocal raised
            # Session 2 is the V3Score query — blow up once
            if session_num == 2 and not raised:
                raised = True
                raise RuntimeError("DB connection lost")
            return MagicMock(
                scalar_one=MagicMock(return_value=mock_job),
                all=MagicMock(return_value=[]),
            )

        mock_session.execute = AsyncMock(side_effect=_mock_execute)

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=_mock_enter)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
        ):
            result = await backtest_validate({})

        assert result["status"] == "failed"
        assert "DB connection lost" in result["error"]

    @pytest.mark.asyncio
    async def test_backtest_validate_with_scores(self):
        """backtest_validate runs simulator and returns metrics when data exists."""
        from margin_api.workers import backtest_validate

        # Build mock V3Score + Asset rows
        mock_v3_1 = MagicMock()
        mock_v3_1.scored_at = datetime(2024, 6, 1, tzinfo=UTC)
        mock_v3_1.composite_score = 75.0

        mock_v3_2 = MagicMock()
        mock_v3_2.scored_at = datetime(2024, 7, 1, tzinfo=UTC)
        mock_v3_2.composite_score = 80.0

        mock_v3_3 = MagicMock()
        mock_v3_3.scored_at = datetime(2024, 8, 1, tzinfo=UTC)
        mock_v3_3.composite_score = 70.0

        score_rows = [
            (mock_v3_1, "AAPL"),
            (mock_v3_2, "MSFT"),
            (mock_v3_3, "GOOGL"),
        ]

        # Mock the simulator result
        mock_bt_result = MagicMock()
        mock_bt_result.metrics.cagr = 0.12
        mock_bt_result.metrics.sharpe_ratio = 1.5
        mock_bt_result.metrics.num_months = 3

        mock_job = MagicMock()
        mock_job.id = 1

        session_num = 0
        mock_session = AsyncMock()

        async def _mock_enter(*a):
            nonlocal session_num
            session_num += 1
            return mock_session

        async def _mock_execute(stmt):
            # Session 2 returns the V3Score data
            if session_num == 2:
                return MagicMock(all=MagicMock(return_value=score_rows))
            # All others: return mock job for scalar_one
            return MagicMock(scalar_one=MagicMock(return_value=mock_job))

        mock_session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 1))
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=_mock_execute)

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=_mock_enter)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # Mock the simulator class at the source where it's imported from
        mock_sim_cls = MagicMock()
        mock_sim_instance = MagicMock()
        mock_sim_instance.run.return_value = mock_bt_result
        mock_sim_cls.return_value = mock_sim_instance

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch(
                "margin_engine.backtesting.simulator.WalkForwardSimulator",
                mock_sim_cls,
            ),
        ):
            result = await backtest_validate({})

        assert result["status"] == "completed"
        assert result["cagr"] == 0.12
        assert result["sharpe"] == 1.5
        assert result["num_months"] == 3


class TestTrainMlModels:
    @pytest.mark.asyncio
    async def test_train_ml_models_insufficient_data(self):
        """train_ml_models completes with message when too few samples."""
        from margin_api.workers import train_ml_models

        mock_job = MagicMock()
        mock_job.id = 1

        session_num = 0
        mock_session = AsyncMock()

        async def _mock_enter(*a):
            nonlocal session_num
            session_num += 1
            return mock_session

        async def _mock_execute(stmt):
            # Session 1 is the concurrency guard — return 0 running jobs
            if session_num == 1:
                return MagicMock(scalar=MagicMock(return_value=0))
            # Session 3 is the Score query — returns only 1 row (< min_samples)
            if session_num == 3:
                mock_score = MagicMock()
                mock_score.composite_percentile = 75.0
                mock_score.composite_raw_score = 70.0
                mock_score.data_coverage = 0.9
                return MagicMock(all=MagicMock(return_value=[(mock_score, "AAPL")]))
            return MagicMock(scalar_one=MagicMock(return_value=mock_job))

        mock_session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 1))
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=_mock_execute)

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=_mock_enter)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
        ):
            settings = MagicMock()
            settings.ml_train_min_samples = 100
            settings.ml_n_clusters = 5
            settings.ml_artifact_dir = "/tmp/test_ml"
            mock_settings.return_value = settings
            result = await train_ml_models({})

        assert result["status"] == "completed"
        assert "Insufficient" in result["message"]

    @pytest.mark.asyncio
    async def test_train_ml_models_creates_job_run(self):
        """train_ml_models creates a JobRun with job_type='train_ml_models'."""
        from margin_api.workers import train_ml_models

        added_objects = []
        mock_job = MagicMock()
        mock_job.id = 1

        session_num = 0
        mock_session = AsyncMock()

        async def _mock_enter(*a):
            nonlocal session_num
            session_num += 1
            return mock_session

        async def _mock_execute(stmt):
            # Session 1 is the concurrency guard — return 0 running jobs
            if session_num == 1:
                return MagicMock(scalar=MagicMock(return_value=0))
            if session_num == 3:
                return MagicMock(all=MagicMock(return_value=[]))  # Empty scores
            return MagicMock(scalar_one=MagicMock(return_value=mock_job))

        mock_session.add = MagicMock(
            side_effect=lambda obj: (setattr(obj, "id", 1), added_objects.append(obj))
        )
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=_mock_execute)

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=_mock_enter)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
        ):
            settings = MagicMock()
            settings.ml_train_min_samples = 100
            settings.ml_n_clusters = 5
            settings.ml_artifact_dir = "/tmp/test_ml"
            mock_settings.return_value = settings
            await train_ml_models({})

        from margin_api.db.models import JobRun as JobRunModel

        job_runs = [o for o in added_objects if isinstance(o, JobRunModel)]
        assert len(job_runs) >= 1
        assert job_runs[0].job_type == "train_ml_models"

    @pytest.mark.asyncio
    async def test_train_ml_models_handles_exception(self):
        """train_ml_models records failure on exception inside try block."""
        from margin_api.workers import train_ml_models

        mock_job = MagicMock()
        mock_job.id = 1

        session_num = 0
        mock_session = AsyncMock()

        async def _mock_enter(*a):
            nonlocal session_num
            session_num += 1
            return mock_session

        async def _mock_execute(stmt):
            # Session 1 is the concurrency guard — return 0 running jobs
            if session_num == 1:
                return MagicMock(scalar=MagicMock(return_value=0))
            # Session 3 is Score query — blow up
            if session_num == 3:
                raise RuntimeError("Score query failed")
            return MagicMock(scalar_one=MagicMock(return_value=mock_job))

        mock_session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 1))
        mock_session.commit = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=_mock_execute)

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=_mock_enter)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
        ):
            settings = MagicMock()
            settings.ml_train_min_samples = 100
            settings.ml_n_clusters = 5
            settings.ml_artifact_dir = "/tmp/test_ml"
            mock_settings.return_value = settings
            result = await train_ml_models({})

        assert result["status"] == "failed"
        assert "Score query failed" in result["error"]


class TestWorkerRegistration:
    """Verify new worker functions are registered properly."""

    def test_orchestrate_ingest_registered(self):
        names = [f.name if hasattr(f, "name") else f.__name__ for f in WorkerSettings.functions]
        assert "orchestrate_ingest" in names

    def test_ingest_batch_registered(self):
        names = [f.name if hasattr(f, "name") else f.__name__ for f in WorkerSettings.functions]
        assert "ingest_batch" in names

    def test_ingest_sweep_registered(self):
        names = [f.name if hasattr(f, "name") else f.__name__ for f in WorkerSettings.functions]
        assert "ingest_sweep" in names

    def test_ingest_sweep_complete_registered(self):
        names = [f.name if hasattr(f, "name") else f.__name__ for f in WorkerSettings.functions]
        assert "ingest_sweep_complete" in names

    def test_train_ml_models_registered(self):
        names = [f.name if hasattr(f, "name") else f.__name__ for f in WorkerSettings.functions]
        assert "train_ml_models" in names

    def test_backtest_validate_registered(self):
        names = [f.name if hasattr(f, "name") else f.__name__ for f in WorkerSettings.functions]
        assert "backtest_validate" in names

    def test_cron_includes_orchestrate_ingest(self):
        """orchestrate_ingest should have a daily cron entry."""
        cron_funcs = []
        for job in WorkerSettings.cron_jobs:
            if hasattr(job, "coroutine"):
                cron_funcs.append(job.coroutine.__name__)
        assert "orchestrate_ingest" in cron_funcs

    def test_cron_includes_train_ml_models(self):
        """train_ml_models should have a weekly cron entry."""
        cron_funcs = []
        for job in WorkerSettings.cron_jobs:
            if hasattr(job, "coroutine"):
                cron_funcs.append(job.coroutine.__name__)
        assert "train_ml_models" in cron_funcs

    def test_total_functions_count(self):
        """All 31 worker functions should be registered."""
        assert len(WorkerSettings.functions) == 31

    def test_total_cron_jobs_count(self):
        """Should have 13 cron jobs (12 prior + 1 drawdown screener)."""
        assert len(WorkerSettings.cron_jobs) == 13


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
        safety check should add one."""
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
            await live_price_poll({})

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
            await live_price_poll({})

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
            await live_price_poll({})

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
                {
                    "Open": [150.0],
                    "High": [152.0],
                    "Low": [149.0],
                    "Close": [151.0],
                    "Volume": [1000000],
                },
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


class TestRetryQuarantined:
    @pytest.mark.asyncio
    async def test_recovers_ticker_on_successful_download(self):
        """Quarantined ticker with valid yfinance data gets un-quarantined."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import retry_quarantined

        fake_redis = fakeredis.aioredis.FakeRedis()
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
        assert await fake_redis.get("price_fail:AAPL") is None

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_resets_counter_on_still_failing(self):
        """Ticker that still fails gets counter reset to max_consecutive_fails."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import retry_quarantined

        fake_redis = fakeredis.aioredis.FakeRedis()
        await fake_redis.set("price_fail:BAD", "47")

        mock_df = pd.DataFrame()

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_df),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await retry_quarantined({})

        assert result["still_failing"] >= 1
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

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_permanently_delists_after_max_retry_cycles(self):
        """Ticker failing 3+ retry cycles gets permanently delisted."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import retry_quarantined

        fake_redis = fakeredis.aioredis.FakeRedis()
        await fake_redis.set("price_fail:DEAD", "10")
        # Simulate 2 prior failed retry cycles
        await fake_redis.set("price_retry_count:DEAD", "2")

        mock_df = pd.DataFrame()

        mock_asset = MagicMock()
        mock_asset.ingestion_status = "quarantined"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_asset

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_df),
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await retry_quarantined({})

        assert result["permanently_delisted"] >= 1
        assert result["still_failing"] == 0
        # Redis keys should be cleaned up
        assert await fake_redis.get("price_fail:DEAD") is None
        assert await fake_redis.get("price_retry_count:DEAD") is None
        # DB should be updated
        assert mock_asset.ingestion_status == "permanently_skipped"

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_recovery_clears_retry_counter(self):
        """Recovered ticker has retry counter cleaned up."""
        import fakeredis.aioredis
        import pandas as pd
        from margin_api.workers import retry_quarantined

        fake_redis = fakeredis.aioredis.FakeRedis()
        await fake_redis.set("price_fail:BACK", "10")
        await fake_redis.set("price_retry_count:BACK", "2")

        mock_df = pd.DataFrame(
            {"Close": [42.0]},
            index=pd.DatetimeIndex(["2026-03-17"], name="Date"),
        )

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.download", return_value=mock_df),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await retry_quarantined({})

        assert result["recovered"] >= 1
        assert await fake_redis.get("price_fail:BACK") is None
        assert await fake_redis.get("price_retry_count:BACK") is None

        await fake_redis.aclose()


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

        assert await fake_redis.get("price_fail:AAPL") is None
        assert await fake_redis.get("price_fail:MSFT") is None
        assert await fake_redis.get("price_fail_bulk_reset_done") is not None

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_bulk_reset_runs_only_once(self):
        """Second startup skips bulk reset if flag key exists."""
        import fakeredis.aioredis
        from margin_api.workers import WorkerSettings

        fake_redis = fakeredis.aioredis.FakeRedis()
        await fake_redis.set("price_fail_bulk_reset_done", "1")
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

        assert await fake_redis.get("price_fail:AAPL") is not None

        await fake_redis.aclose()


class TestExpireStaleApprovalsDedup:
    @pytest.mark.asyncio
    async def test_skips_if_lock_exists(self):
        """expire_stale_approvals skips execution if Redis lock exists."""
        import fakeredis.aioredis
        from margin_api.workers import expire_stale_approvals

        fake_redis = fakeredis.aioredis.FakeRedis()
        await fake_redis.set("expire_approvals_lock", "1")

        with (
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.get_engine") as mock_engine,
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await expire_stale_approvals({})

        assert result["status"] == "skipped_dedup"
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
        lock_val = await fake_redis.get("expire_approvals_lock")
        assert lock_val is not None
        ttl = await fake_redis.ttl("expire_approvals_lock")
        assert 17000 < ttl <= 18000  # ~5h

        await fake_redis.aclose()
