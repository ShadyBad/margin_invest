"""Integration tests for the resilient ingestion pipeline.

Tests the seed_ticker_data function with mocked providers and DB sessions.
Verifies SeedResult statuses, per-category tracking, and error classification.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from margin_api.services.seed_result import SeedResult
from margin_engine.ingestion.types import DataCategory, FetchResult


def _make_fetch_result(
    category: DataCategory,
    ticker: str = "AAPL",
    success: bool = True,
    raw_data: dict | None = None,
    error: str | None = None,
) -> FetchResult:
    return FetchResult(
        provider_name="yfinance",
        category=category,
        ticker=ticker,
        raw_data=raw_data or {},
        fetched_at=datetime.now(UTC).isoformat(),
        success=success,
        error=error,
    )


def _make_all_success(ticker: str = "AAPL") -> dict[str, FetchResult]:
    """Return a fetch_all result dict with all categories succeeding."""
    return {
        "fundamentals": _make_fetch_result(
            DataCategory.FUNDAMENTALS,
            ticker,
            raw_data={
                "income_statement": {"Total Revenue": 100000},
                "balance_sheet": {"Total Assets": 500000},
                "cash_flow": {"Operating Cash Flow": 40000},
            },
        ),
        "price": _make_fetch_result(
            DataCategory.PRICE,
            ticker,
            raw_data={"bars": [{"Close": 150.0, "Volume": 1000000}]},
        ),
        "earnings": _make_fetch_result(
            DataCategory.EARNINGS,
            ticker,
            raw_data={"earnings": [{"quarter": "2024-01-25", "actual_eps": 1.52}]},
        ),
        "info": _make_fetch_result(
            DataCategory.FUNDAMENTALS,
            ticker,
            raw_data={
                "shortName": "Apple Inc.",
                "sector": "Technology",
                "country": "United States",
                "marketCap": 3000000000000,
                "sharesOutstanding": 15000000000,
            },
        ),
    }


def _make_partial_failure(ticker: str = "AAPL") -> dict[str, FetchResult]:
    """Return fetch_all result with earnings failing."""
    results = _make_all_success(ticker)
    results["earnings"] = _make_fetch_result(
        DataCategory.EARNINGS,
        ticker,
        success=False,
        error="Import lxml failed",
    )
    return results


def _make_foreign_ticker(ticker: str = "BABA") -> dict[str, FetchResult]:
    """Return fetch_all result for a non-US ticker."""
    results = _make_all_success(ticker)
    results["info"] = _make_fetch_result(
        DataCategory.FUNDAMENTALS,
        ticker,
        raw_data={
            "shortName": "Alibaba Group",
            "sector": "Technology",
            "country": "China",
            "marketCap": 200000000000,
        },
    )
    return results


class TestSeedResultTracking:
    """Test that SeedResult correctly tracks category success/failure."""

    def test_seed_result_ok(self):
        result = SeedResult(
            status="ok",
            categories_succeeded=["fundamentals", "price", "earnings", "info"],
        )
        assert result.is_success is True
        assert result.data_categories_present == {
            "fundamentals": True,
            "price": True,
            "earnings": True,
            "info": True,
        }

    def test_seed_result_partial(self):
        result = SeedResult(
            status="partial",
            categories_succeeded=["fundamentals", "price", "info"],
            categories_failed=["earnings"],
        )
        assert result.is_success is True
        assert result.data_categories_present["earnings"] is False
        assert result.data_categories_present["fundamentals"] is True

    def test_seed_result_failed(self):
        result = SeedResult(
            status="failed",
            error_message="Connection refused",
        )
        assert result.is_success is False

    def test_seed_result_foreign(self):
        result = SeedResult(status="foreign", error_message="Non-US domicile: China")
        assert result.is_success is False

    def test_seed_result_default_provider(self):
        result = SeedResult(status="ok")
        assert result.provider_used == "yfinance"

    def test_seed_result_empty_categories_by_default(self):
        result = SeedResult(status="ok")
        assert result.categories_succeeded == []
        assert result.categories_failed == []


class TestSeedTickerDataIntegration:
    """Integration tests for seed_ticker_data with mocked providers and sessions."""

    @pytest.mark.asyncio
    async def test_successful_seed_returns_ok(self):
        """Full successful seed returns SeedResult with status='ok'."""
        from margin_api.cli import seed_ticker_data

        mock_provider = MagicMock()
        mock_provider.fetch_all.return_value = _make_all_success("AAPL")

        # Mock session to handle pg_insert — needs to support two execute calls
        # (one for Asset upsert returning id, one for FinancialData upsert)
        # and the final select for update_failure_status.
        mock_session = AsyncMock()

        # First execute: Asset upsert returning scalar_one() = 1
        asset_upsert_result = MagicMock()
        asset_upsert_result.scalar_one.return_value = 1

        # Second execute: FinancialData upsert (no return value needed)
        fd_upsert_result = MagicMock()

        # Third execute: select(Asset).where(Asset.id == asset_id) for update_failure_status
        asset_obj = MagicMock()
        asset_obj.id = 1
        asset_obj.consecutive_failures = 0
        asset_obj.ingestion_status = "active"
        asset_obj.last_failure_reason = None
        asset_obj.quarantined_at = None
        asset_obj.last_retry_at = None

        asset_select_result = MagicMock()
        asset_select_result.scalar_one.return_value = asset_obj

        mock_session.execute.side_effect = [
            asset_upsert_result,
            fd_upsert_result,
            asset_select_result,
        ]

        result = await seed_ticker_data(
            ticker="AAPL",
            provider=mock_provider,
            session=mock_session,
        )

        assert result.status == "ok"
        assert "fundamentals" in result.categories_succeeded
        assert "price" in result.categories_succeeded
        assert "earnings" in result.categories_succeeded
        assert "info" in result.categories_succeeded
        assert len(result.categories_failed) == 0
        mock_provider.fetch_all.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_partial_seed_returns_partial(self):
        """Seed with earnings failure returns SeedResult(status='partial')."""
        from margin_api.cli import seed_ticker_data

        mock_provider = MagicMock()
        mock_provider.fetch_all.return_value = _make_partial_failure("FSLR")

        mock_session = AsyncMock()

        asset_upsert_result = MagicMock()
        asset_upsert_result.scalar_one.return_value = 2

        fd_upsert_result = MagicMock()

        asset_obj = MagicMock()
        asset_obj.id = 2
        asset_obj.consecutive_failures = 0
        asset_obj.ingestion_status = "active"
        asset_obj.last_failure_reason = None
        asset_obj.quarantined_at = None
        asset_obj.last_retry_at = None

        asset_select_result = MagicMock()
        asset_select_result.scalar_one.return_value = asset_obj

        mock_session.execute.side_effect = [
            asset_upsert_result,
            fd_upsert_result,
            asset_select_result,
        ]

        result = await seed_ticker_data(
            ticker="FSLR",
            provider=mock_provider,
            session=mock_session,
        )

        assert result.status == "partial"
        assert "earnings" in result.categories_failed
        assert "fundamentals" in result.categories_succeeded

    @pytest.mark.asyncio
    async def test_foreign_ticker_returns_foreign(self):
        """Seed for non-US ticker returns SeedResult(status='foreign')."""
        from margin_api.cli import seed_ticker_data

        mock_provider = MagicMock()
        mock_provider.fetch_all.return_value = _make_foreign_ticker("BABA")

        # Foreign tickers are rejected before any DB operations,
        # so the session is never used.
        mock_session = AsyncMock()

        result = await seed_ticker_data(
            ticker="BABA",
            provider=mock_provider,
            session=mock_session,
        )

        assert result.status == "foreign"
        assert "Non-US domicile" in result.error_message

    @pytest.mark.asyncio
    async def test_provider_exception_returns_failed(self):
        """Seed that raises exception returns SeedResult(status='failed')."""
        from margin_api.cli import seed_ticker_data

        mock_provider = MagicMock()
        mock_provider.fetch_all.side_effect = ConnectionError("Network unreachable")

        # The exception handler does rollback, then tries to select the Asset
        # for failure tracking. Return None so it skips update_failure_status.
        mock_session = AsyncMock()
        asset_select_result = MagicMock()
        asset_select_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = asset_select_result

        result = await seed_ticker_data(
            ticker="FAIL",
            provider=mock_provider,
            session=mock_session,
        )

        assert result.status == "failed"
        assert "Network unreachable" in result.error_message
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_provider_exception_updates_existing_asset_failure_status(self):
        """When seed fails and asset exists, update_failure_status is called."""
        from margin_api.cli import seed_ticker_data

        mock_provider = MagicMock()
        mock_provider.fetch_all.side_effect = ConnectionError("Connection reset")

        # Set up mock so the asset exists in the DB
        mock_session = AsyncMock()
        asset_obj = MagicMock()
        asset_obj.id = 5
        asset_obj.consecutive_failures = 1
        asset_obj.ingestion_status = "active"
        asset_obj.last_failure_reason = None
        asset_obj.quarantined_at = None
        asset_obj.last_retry_at = None

        asset_select_result = MagicMock()
        asset_select_result.scalar_one_or_none.return_value = asset_obj
        mock_session.execute.return_value = asset_select_result

        result = await seed_ticker_data(
            ticker="FAIL",
            provider=mock_provider,
            session=mock_session,
        )

        assert result.status == "failed"
        # ConnectionError is classified as "transient", which sets last_failure_reason
        assert asset_obj.last_failure_reason == "Connection reset"
        # Session should have had commit called (by update_failure_status)
        mock_session.commit.assert_called()


class TestErrorClassification:
    """Test that error classification correctly categorizes errors."""

    def test_connection_error_is_transient(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(ConnectionError("timeout")) == "transient"

    def test_timeout_error_is_transient(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(TimeoutError("timed out")) == "transient"

    def test_os_error_is_transient(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(OSError("Connection refused")) == "transient"

    def test_rate_limit_429_is_transient(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(Exception("429 Too Many Requests")) == "transient"

    def test_503_is_transient(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(Exception("503 Service Unavailable")) == "transient"

    def test_502_is_transient(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(Exception("502 Bad Gateway")) == "transient"

    def test_500_is_transient(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(Exception("500 Internal Server Error")) == "transient"

    def test_not_found_is_permanent(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(ValueError("Ticker not found")) == "permanent"

    def test_delisted_is_permanent(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(Exception("Symbol is delisted")) == "permanent"

    def test_generic_error_is_data_unavailable(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(Exception("No data available")) == "data_unavailable"

    def test_unknown_error_is_data_unavailable(self):
        from margin_api.services.ingestion import classify_error

        assert classify_error(Exception("Something went wrong")) == "data_unavailable"


class TestShouldIngestTicker:
    """Test the should_ingest_ticker decision logic."""

    def test_active_ticker_should_ingest(self):
        from margin_api.services.ingestion import should_ingest_ticker

        assert should_ingest_ticker("active", 0, None) is True

    def test_permanently_skipped_should_not_ingest(self):
        from margin_api.services.ingestion import should_ingest_ticker

        assert should_ingest_ticker("permanently_skipped", 10, None) is False

    def test_quarantined_with_no_retry_should_ingest(self):
        from margin_api.services.ingestion import should_ingest_ticker

        assert should_ingest_ticker("quarantined", 3, None) is True

    def test_quarantined_recently_retried_should_not_ingest(self):
        from margin_api.services.ingestion import should_ingest_ticker

        assert should_ingest_ticker("quarantined", 3, datetime.now(UTC)) is False


class TestUpdateFailureStatus:
    """Test update_failure_status state transitions."""

    @pytest.mark.asyncio
    async def test_success_resets_all_failure_fields(self):
        from margin_api.services.ingestion import update_failure_status

        session = AsyncMock()
        asset = MagicMock()
        asset.consecutive_failures = 3
        asset.ingestion_status = "quarantined"
        asset.last_failure_reason = "old error"
        asset.quarantined_at = datetime.now(UTC)
        asset.last_retry_at = datetime.now(UTC)

        await update_failure_status(session, asset, "success", None)

        assert asset.consecutive_failures == 0
        assert asset.ingestion_status == "active"
        assert asset.last_failure_reason is None
        assert asset.quarantined_at is None
        assert asset.last_retry_at is None
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_transient_sets_reason_only(self):
        from margin_api.services.ingestion import update_failure_status

        session = AsyncMock()
        asset = MagicMock()
        asset.consecutive_failures = 0
        asset.ingestion_status = "active"

        await update_failure_status(session, asset, "transient", "Connection reset")

        assert asset.last_failure_reason == "Connection reset"
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_permanent_sets_permanently_skipped(self):
        from margin_api.services.ingestion import update_failure_status

        session = AsyncMock()
        asset = MagicMock()
        asset.consecutive_failures = 0
        asset.ingestion_status = "active"

        await update_failure_status(session, asset, "permanent", "Ticker delisted")

        assert asset.ingestion_status == "permanently_skipped"
        assert asset.last_failure_reason == "Ticker delisted"
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_unavailable_increments_failures(self):
        from margin_api.services.ingestion import update_failure_status

        session = AsyncMock()
        asset = MagicMock()
        asset.consecutive_failures = 1
        asset.ingestion_status = "active"
        asset.quarantined_at = None

        await update_failure_status(session, asset, "data_unavailable", "No data")

        assert asset.consecutive_failures == 2
        assert asset.last_failure_reason == "No data"

    @pytest.mark.asyncio
    async def test_data_unavailable_quarantines_at_threshold(self):
        from margin_api.services.ingestion import update_failure_status

        session = AsyncMock()
        asset = MagicMock()
        asset.consecutive_failures = 2  # will become 3 (quarantine threshold)
        asset.ingestion_status = "active"
        asset.quarantined_at = None

        await update_failure_status(session, asset, "data_unavailable", "No data")

        assert asset.consecutive_failures == 3
        assert asset.ingestion_status == "quarantined"
        assert asset.quarantined_at is not None

    @pytest.mark.asyncio
    async def test_data_unavailable_permanently_skips_at_threshold(self):
        from margin_api.services.ingestion import update_failure_status

        session = AsyncMock()
        asset = MagicMock()
        asset.consecutive_failures = 5  # will become 6 (permanent threshold)
        asset.ingestion_status = "quarantined"
        asset.quarantined_at = datetime.now(UTC)

        await update_failure_status(session, asset, "data_unavailable", "No data")

        assert asset.consecutive_failures == 6
        assert asset.ingestion_status == "permanently_skipped"


class TestAlertingHelper:
    """Test threshold-based alerting logic."""

    def test_high_failure_rate_logs_error(self, caplog):
        import logging

        from margin_api.workers import _log_run_alerts

        with caplog.at_level(logging.ERROR):
            _log_run_alerts(total=100, succeeded=70, failed=25, partial=5, cb_trips=0)

        assert "ALERT" in caplog.text
        assert "25%" in caplog.text

    def test_high_partial_rate_logs_warning(self, caplog):
        import logging

        from margin_api.workers import _log_run_alerts

        with caplog.at_level(logging.WARNING):
            _log_run_alerts(total=100, succeeded=80, failed=5, partial=15, cb_trips=0)

        assert "15%" in caplog.text

    def test_circuit_breaker_trip_logs_warning(self, caplog):
        import logging

        from margin_api.workers import _log_run_alerts

        with caplog.at_level(logging.WARNING):
            _log_run_alerts(total=100, succeeded=95, failed=5, partial=0, cb_trips=2)

        assert "Circuit breaker tripped 2 time(s)" in caplog.text

    def test_no_alerts_on_healthy_run(self, caplog):
        import logging

        from margin_api.workers import _log_run_alerts

        with caplog.at_level(logging.WARNING):
            _log_run_alerts(total=100, succeeded=95, failed=3, partial=2, cb_trips=0)

        assert "ALERT" not in caplog.text

    def test_no_alerts_on_empty_run(self, caplog):
        import logging

        from margin_api.workers import _log_run_alerts

        with caplog.at_level(logging.WARNING):
            _log_run_alerts(total=0, succeeded=0, failed=0, partial=0, cb_trips=0)

        assert "ALERT" not in caplog.text
