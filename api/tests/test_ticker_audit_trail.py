"""Tests for IngestionTickerStatus audit trail in full_ingest."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.db.models import IngestionTickerStatus
from margin_api.services.seed_result import SeedResult


class TestIngestionTickerStatusAuditTrail:
    """Verify that full_ingest writes an IngestionTickerStatus row per ticker."""

    @pytest.mark.asyncio
    async def test_creates_ticker_status_for_each_ticker(self):
        """full_ingest writes an IngestionTickerStatus for every successfully seeded ticker."""
        from margin_api.workers import full_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "2026.02.23"
        mock_snapshot.tickers = ["AAPL", "MSFT"]

        mock_run = MagicMock()
        mock_run.id = 42
        mock_run.started_at = datetime.now(UTC)

        added_objects: list = []
        add_counter = 0

        mock_session = AsyncMock()

        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None
        run_result = MagicMock()
        run_result.scalar_one.return_value = mock_run

        mock_session.execute = AsyncMock(
            side_effect=[
                no_result,   # AAPL should_ingest check
                no_result,   # AAPL resume check
                no_result,   # MSFT should_ingest check
                no_result,   # MSFT resume check
                run_result,  # IngestionRun update
            ],
        )

        def _track_add(obj):
            nonlocal add_counter
            add_counter += 1
            # IngestionRun is the first add; give it id=42 to match mock_run
            obj.id = 42 if add_counter == 1 else add_counter
            added_objects.append(obj)

        mock_session.add = MagicMock(side_effect=_track_add)
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch(
                "margin_api.cli.seed_ticker_data",
                return_value=SeedResult(
                    status="ok",
                    categories_succeeded=["income_statement", "balance_sheet"],
                ),
            ),
            patch("margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider"),
            patch("margin_engine.ingestion.rate_limiter.RateLimiter"),
        ):
            result = await full_ingest({"redis": AsyncMock()})

        assert result["status"] == "completed"
        assert result["succeeded"] == 2

        # Verify IngestionTickerStatus objects were created
        ticker_statuses = [
            o for o in added_objects if isinstance(o, IngestionTickerStatus)
        ]
        assert len(ticker_statuses) == 2

        tickers_recorded = {ts.ticker for ts in ticker_statuses}
        assert tickers_recorded == {"AAPL", "MSFT"}

        for ts in ticker_statuses:
            assert ts.run_id == 42
            assert ts.status == "succeeded"
            assert ts.duration_ms is not None
            assert ts.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_records_failed_ticker_status(self):
        """full_ingest records status='failed' and error_message for failed tickers."""
        from margin_api.workers import full_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "2026.02.23"
        mock_snapshot.tickers = ["FAIL"]

        mock_run = MagicMock()
        mock_run.id = 10
        mock_run.started_at = datetime.now(UTC)

        added_objects: list = []

        mock_session = AsyncMock()

        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None
        run_result = MagicMock()
        run_result.scalar_one.return_value = mock_run

        mock_session.execute = AsyncMock(
            side_effect=[
                no_result,   # FAIL should_ingest check
                no_result,   # FAIL resume check
                run_result,  # IngestionRun update
            ],
        )

        def _track_add(obj):
            obj.id = 1
            added_objects.append(obj)

        mock_session.add = MagicMock(side_effect=_track_add)
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch(
                "margin_api.cli.seed_ticker_data",
                return_value=SeedResult(
                    status="failed",
                    error_message="yfinance timeout",
                ),
            ),
            patch("margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider"),
            patch("margin_engine.ingestion.rate_limiter.RateLimiter"),
        ):
            await full_ingest({"redis": AsyncMock()})

        ticker_statuses = [
            o for o in added_objects if isinstance(o, IngestionTickerStatus)
        ]
        assert len(ticker_statuses) == 1
        ts = ticker_statuses[0]
        assert ts.ticker == "FAIL"
        assert ts.status == "failed"
        assert ts.error_message == "yfinance timeout"
        assert ts.data_fetched is None

    @pytest.mark.asyncio
    async def test_records_partial_ticker_status(self):
        """full_ingest records status='succeeded' for partial results with data_fetched."""
        from margin_api.workers import full_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "2026.02.23"
        mock_snapshot.tickers = ["PARTIAL"]

        mock_run = MagicMock()
        mock_run.id = 5
        mock_run.started_at = datetime.now(UTC)

        added_objects: list = []

        mock_session = AsyncMock()

        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None
        run_result = MagicMock()
        run_result.scalar_one.return_value = mock_run

        mock_session.execute = AsyncMock(
            side_effect=[
                no_result,   # PARTIAL should_ingest check
                no_result,   # PARTIAL resume check
                run_result,  # IngestionRun update
            ],
        )

        def _track_add(obj):
            obj.id = 1
            added_objects.append(obj)

        mock_session.add = MagicMock(side_effect=_track_add)
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch(
                "margin_api.cli.seed_ticker_data",
                return_value=SeedResult(
                    status="partial",
                    categories_succeeded=["income_statement"],
                    categories_failed=["balance_sheet"],
                ),
            ),
            patch("margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider"),
            patch("margin_engine.ingestion.rate_limiter.RateLimiter"),
        ):
            await full_ingest({"redis": AsyncMock()})

        ticker_statuses = [
            o for o in added_objects if isinstance(o, IngestionTickerStatus)
        ]
        assert len(ticker_statuses) == 1
        ts = ticker_statuses[0]
        assert ts.ticker == "PARTIAL"
        assert ts.status == "succeeded"
        assert ts.error_message is None
        assert ts.data_fetched == {
            "income_statement": True,
            "balance_sheet": False,
        }

    @pytest.mark.asyncio
    async def test_records_foreign_ticker_status(self):
        """full_ingest records status for foreign/skipped results."""
        from margin_api.workers import full_ingest

        mock_snapshot = MagicMock()
        mock_snapshot.id = 1
        mock_snapshot.version = "2026.02.23"
        mock_snapshot.tickers = ["FOREIGN"]

        mock_run = MagicMock()
        mock_run.id = 7
        mock_run.started_at = datetime.now(UTC)

        added_objects: list = []

        mock_session = AsyncMock()

        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None
        run_result = MagicMock()
        run_result.scalar_one.return_value = mock_run

        mock_session.execute = AsyncMock(
            side_effect=[
                no_result,   # FOREIGN should_ingest check
                no_result,   # FOREIGN resume check
                run_result,  # IngestionRun update
            ],
        )

        def _track_add(obj):
            obj.id = 1
            added_objects.append(obj)

        mock_session.add = MagicMock(side_effect=_track_add)
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch("margin_api.workers.get_active_snapshot", return_value=mock_snapshot),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch(
                "margin_api.cli.seed_ticker_data",
                return_value=SeedResult(status="foreign"),
            ),
            patch("margin_engine.ingestion.providers.yfinance_provider.YFinanceProvider"),
            patch("margin_engine.ingestion.rate_limiter.RateLimiter"),
        ):
            await full_ingest({"redis": AsyncMock()})

        ticker_statuses = [
            o for o in added_objects if isinstance(o, IngestionTickerStatus)
        ]
        assert len(ticker_statuses) == 1
        ts = ticker_statuses[0]
        assert ts.ticker == "FOREIGN"
        assert ts.status == "foreign"
