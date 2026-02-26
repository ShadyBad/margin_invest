"""Tests for orchestrate_ingest worker job."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOrchestrateIngest:
    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_enqueues_batches(self, mock_engine, mock_factory):
        from margin_api.workers import orchestrate_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "1.0"
        mock_snapshot.tickers = [f"T{i:03d}" for i in range(120)]

        mock_session = AsyncMock()
        mock_factory_inst = MagicMock()
        mock_factory_inst.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory_inst.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_factory_inst

        with patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot):
            with patch("margin_api.cli._load_foreign_skips", return_value=set()):
                mock_redis = AsyncMock()
                ctx = {"redis": mock_redis}
                with patch("margin_api.workers.get_settings") as mock_settings:
                    mock_settings.return_value.ingest_batch_size = 50
                    result = await orchestrate_ingest(ctx)

        assert result["status"] == "dispatched"
        assert result["total_batches"] == 3  # ceil(120 / 50) = 3
        assert result["total_tickers"] == 120
        assert mock_redis.enqueue_job.call_count == 3
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
            with patch("margin_api.cli._load_foreign_skips", return_value=set()):
                mock_redis = AsyncMock()
                ctx = {"redis": mock_redis}
                with patch("margin_api.workers.get_settings") as mock_settings:
                    mock_settings.return_value.ingest_batch_size = 50
                    result = await orchestrate_ingest(ctx)

        set_calls = [c for c in mock_redis.method_calls if c[0] == "set"]
        assert len(set_calls) >= 2

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_filters_foreign_tickers(self, mock_engine, mock_factory):
        from margin_api.workers import orchestrate_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "1.0"
        mock_snapshot.tickers = ["AAPL", "MSFT", "FOREIGN1", "GOOG"]

        mock_session = AsyncMock()
        mock_factory_inst = MagicMock()
        mock_factory_inst.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory_inst.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_factory_inst

        with patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot):
            with patch("margin_api.cli._load_foreign_skips", return_value={"FOREIGN1"}):
                mock_redis = AsyncMock()
                ctx = {"redis": mock_redis}
                with patch("margin_api.workers.get_settings") as mock_settings:
                    mock_settings.return_value.ingest_batch_size = 50
                    result = await orchestrate_ingest(ctx)

        assert result["total_tickers"] == 3  # FOREIGN1 filtered out

    @pytest.mark.asyncio
    @patch("margin_api.workers.get_session_factory")
    @patch("margin_api.workers.get_engine")
    async def test_no_redis_returns_error(self, mock_engine, mock_factory):
        from margin_api.workers import orchestrate_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "1.0"
        mock_snapshot.tickers = ["AAPL", "MSFT"]

        mock_session = AsyncMock()
        mock_factory_inst = MagicMock()
        mock_factory_inst.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory_inst.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_factory_inst

        with patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot):
            with patch("margin_api.cli._load_foreign_skips", return_value=set()):
                ctx = {}  # No redis key
                with patch("margin_api.workers.get_settings") as mock_settings:
                    mock_settings.return_value.ingest_batch_size = 50
                    result = await orchestrate_ingest(ctx)

        assert result["status"] == "error"
        assert "redis" in result["message"].lower()
