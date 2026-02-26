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

        # First execute: should_ingest check -> returns asset (active, passes through)
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = asset

        # Second execute: resume check -> no FinancialData for today
        no_fd_result = MagicMock()
        no_fd_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [asset_result, no_fd_result]

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
