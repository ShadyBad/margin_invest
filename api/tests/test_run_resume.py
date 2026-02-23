"""Tests for run-level resume — skip tickers already seeded today."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunLevelResume:
    @pytest.mark.asyncio
    async def test_skips_ticker_already_seeded_today(self):
        """run_seed skips ticker that has FinancialData with today's period_end."""
        from margin_api.cli import run_seed

        mock_engine = MagicMock()
        mock_session_factory = MagicMock()
        mock_session = AsyncMock()

        # First execute: should_ingest_ticker check — no asset yet (new ticker, passes through)
        no_asset_result = MagicMock()
        no_asset_result.scalar_one_or_none.return_value = None

        # Second execute: resume check — FinancialData exists for today
        resume_result = MagicMock()
        resume_result.scalar_one_or_none.return_value = MagicMock()  # non-None = already seeded

        mock_session.execute.side_effect = [no_asset_result, resume_result]

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
            await run_seed(tickers=["AAPL"])

        mock_seed.assert_not_called()

    @pytest.mark.asyncio
    async def test_proceeds_when_not_seeded_today(self):
        """run_seed proceeds when no FinancialData for today."""
        from margin_api.cli import run_seed
        from margin_api.services.seed_result import SeedResult

        mock_engine = MagicMock()
        mock_session_factory = MagicMock()
        mock_session = AsyncMock()

        # First execute: should_ingest check — no asset (new ticker)
        no_asset_result = MagicMock()
        no_asset_result.scalar_one_or_none.return_value = None

        # Second execute: resume check — no FinancialData for today
        no_fd_result = MagicMock()
        no_fd_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [no_asset_result, no_fd_result]

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

        mock_seed.assert_called_once()
