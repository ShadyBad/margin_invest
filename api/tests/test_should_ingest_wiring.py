"""Tests for should_ingest_ticker wiring in run_seed and full_ingest."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunSeedSkipsQuarantined:
    @pytest.mark.asyncio
    async def test_run_seed_skips_permanently_skipped_ticker(self):
        """run_seed should skip tickers with ingestion_status='permanently_skipped'."""
        from margin_api.cli import run_seed

        mock_engine = MagicMock()
        mock_session_factory = MagicMock()
        mock_session = AsyncMock()

        # Asset with permanently_skipped status
        asset = MagicMock()
        asset.ingestion_status = "permanently_skipped"
        asset.consecutive_failures = 10
        asset.last_retry_at = None

        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = asset
        mock_session.execute.return_value = asset_result

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session
        mock_session_ctx.__aexit__.return_value = None
        mock_session_factory.return_value = mock_session_ctx

        with (
            patch("margin_api.cli.get_engine", return_value=mock_engine),
            patch("margin_api.cli.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch("margin_api.cli.seed_ticker_data") as mock_seed,
        ):
            await run_seed(tickers=["DLST"])

        # seed_ticker_data should NOT have been called
        mock_seed.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_seed_processes_active_ticker(self):
        """run_seed should process tickers with ingestion_status='active'."""
        from margin_api.cli import run_seed
        from margin_api.services.seed_result import SeedResult

        mock_engine = MagicMock()
        mock_session_factory = MagicMock()
        mock_session = AsyncMock()

        # Asset with active status
        asset = MagicMock()
        asset.ingestion_status = "active"
        asset.consecutive_failures = 0
        asset.last_retry_at = None

        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = asset
        mock_session.execute.return_value = asset_result

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session
        mock_session_ctx.__aexit__.return_value = None
        mock_session_factory.return_value = mock_session_ctx

        with (
            patch("margin_api.cli.get_engine", return_value=mock_engine),
            patch("margin_api.cli.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch(
                "margin_api.cli.seed_ticker_data",
                return_value=SeedResult(status="ok"),
            ) as mock_seed,
        ):
            await run_seed(tickers=["AAPL"])

        # seed_ticker_data SHOULD have been called
        mock_seed.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_seed_processes_new_ticker_with_no_asset(self):
        """run_seed should process new tickers that don't have an asset record yet."""
        from margin_api.cli import run_seed
        from margin_api.services.seed_result import SeedResult

        mock_engine = MagicMock()
        mock_session_factory = MagicMock()
        mock_session = AsyncMock()

        # No existing asset
        no_asset_result = MagicMock()
        no_asset_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = no_asset_result

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session
        mock_session_ctx.__aexit__.return_value = None
        mock_session_factory.return_value = mock_session_ctx

        with (
            patch("margin_api.cli.get_engine", return_value=mock_engine),
            patch("margin_api.cli.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch(
                "margin_api.cli.seed_ticker_data",
                return_value=SeedResult(status="ok"),
            ) as mock_seed,
        ):
            await run_seed(tickers=["NEW"])

        mock_seed.assert_called_once()


class TestFullIngestSkipsQuarantined:
    @pytest.mark.asyncio
    async def test_full_ingest_skips_permanently_skipped_ticker(self):
        """full_ingest should skip tickers with ingestion_status='permanently_skipped'."""
        from margin_api.workers import full_ingest

        mock_engine = MagicMock()
        mock_session = AsyncMock()

        # Snapshot mock
        snapshot = MagicMock()
        snapshot.tickers = ["DLST"]
        snapshot.version = "1.0"
        snapshot.id = 1

        # Asset with permanently_skipped status
        asset = MagicMock()
        asset.ingestion_status = "permanently_skipped"
        asset.consecutive_failures = 10
        asset.last_retry_at = None

        # IngestionRun mock
        run_mock = MagicMock()
        run_mock.id = 1
        run_mock.started_at = MagicMock()
        run_mock.duration_seconds = 0.1

        # Session.execute call pattern in full_ingest:
        # 1. (no execute for snapshot - get_active_snapshot is patched)
        # 2. (no execute for IngestionRun create - uses session.add + commit)
        # 3. select(Asset) for should_ingest check -> returns asset
        # 4. select(IngestionRun) for updating run record -> returns run_mock
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Asset check in the for loop
                result.scalar_one_or_none.return_value = asset
            else:
                # IngestionRun update at end
                result.scalar_one.return_value = run_mock
            return result

        mock_session.execute = mock_execute
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session
        mock_session_ctx.__aexit__.return_value = None

        mock_session_factory = MagicMock()
        mock_session_factory.return_value = mock_session_ctx

        ctx = {"redis": AsyncMock()}

        with (
            patch("margin_api.workers.get_engine", return_value=mock_engine),
            patch(
                "margin_api.workers.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "margin_api.workers.get_active_snapshot",
                return_value=snapshot,
            ),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch("margin_api.cli.seed_ticker_data") as mock_seed,
        ):
            await full_ingest(ctx)

        # seed_ticker_data should NOT have been called
        mock_seed.assert_not_called()
