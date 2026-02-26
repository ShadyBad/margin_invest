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
        mock_run = MagicMock()
        mock_run.snapshot_id = 1
        mock_snapshot = MagicMock()
        mock_snapshot.tickers = [f"T{i}" for i in range(100)]
        mock_succeeded_rows = [(f"T{i}",) for i in range(100)]

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

        assert result["missing_count"] == 0
        complete_calls = [
            c
            for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "ingest_sweep_complete"
        ]
        assert len(complete_calls) == 1

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_sweep_with_missing_tickers(self, mock_engine, mock_factory):
        from margin_api.workers import ingest_sweep

        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.snapshot_id = 1
        mock_snapshot = MagicMock()
        mock_snapshot.tickers = [f"T{i}" for i in range(100)]
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
        batch_calls = [
            c
            for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "ingest_batch"
        ]
        assert len(batch_calls) == 1

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_sweep_no_redis(self, mock_engine, mock_factory):
        from margin_api.workers import ingest_sweep

        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.snapshot_id = 1
        mock_snapshot = MagicMock()
        mock_snapshot.tickers = ["AAPL"]
        mock_succeeded_rows = []

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

        ctx: dict = {}
        result = await ingest_sweep(ctx, "1", "abc123")

        assert result["status"] == "error"
        assert "No redis" in result["message"]


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
        score_calls = [
            c
            for c in mock_redis.enqueue_job.call_args_list
            if c[0][0] == "full_score"
        ]
        assert len(score_calls) == 1

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_marks_run_failed_when_over_half_fail(self, mock_engine, mock_factory):
        from margin_api.workers import ingest_sweep_complete

        mock_session = AsyncMock()
        mock_run = MagicMock()
        mock_run.started_at = MagicMock()
        mock_run.tickers_succeeded = 30
        mock_run.tickers_failed = 70
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

        assert mock_run.status == "failed"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_no_redis_still_completes(self, mock_engine, mock_factory):
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

        ctx: dict = {}
        result = await ingest_sweep_complete(ctx, "1", "abc123")

        assert result["status"] == "completed"
        assert result["succeeded"] == 95
        assert result["failed"] == 5
