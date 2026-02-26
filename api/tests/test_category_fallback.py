"""Tests for per-category fallback from yfinance to FMP."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from margin_engine.ingestion.types import DataCategory, FetchResult


def _make_fetch_result(
    category: DataCategory,
    ticker: str = "AAPL",
    success: bool = True,
    raw_data: dict | None = None,
    error: str | None = None,
    provider: str = "yfinance",
) -> FetchResult:
    return FetchResult(
        provider_name=provider,
        category=category,
        ticker=ticker,
        raw_data=raw_data or {},
        fetched_at=datetime.now(UTC).isoformat(),
        success=success,
        error=error,
    )


class TestCategoryFallback:
    @pytest.mark.asyncio
    async def test_fmp_called_for_failed_yfinance_earnings(self):
        """When yfinance earnings fail, FMP earnings should be tried."""
        from margin_api.cli import seed_ticker_data

        # Primary provider: yfinance -- earnings fail
        yf_provider = MagicMock()
        yf_provider.fetch_all.return_value = {
            "fundamentals": _make_fetch_result(
                DataCategory.FUNDAMENTALS,
                raw_data={
                    "income_statement": {"Total Revenue": 100000},
                    "balance_sheet": {"Total Assets": 500000},
                    "cash_flow": {"Operating Cash Flow": 40000},
                },
            ),
            "price": _make_fetch_result(DataCategory.PRICE, raw_data={"bars": [{"Close": 150.0}]}),
            "earnings": _make_fetch_result(
                DataCategory.EARNINGS, success=False, error="lxml missing"
            ),
            "info": _make_fetch_result(
                DataCategory.FUNDAMENTALS,
                raw_data={
                    "shortName": "Apple Inc.",
                    "sector": "Technology",
                    "country": "United States",
                    "marketCap": 3000000000000,
                    "sharesOutstanding": 15000000000,
                },
            ),
        }

        # Fallback provider: FMP -- earnings succeed
        fmp_provider = MagicMock()
        fmp_provider.fetch_earnings.return_value = _make_fetch_result(
            DataCategory.EARNINGS,
            success=True,
            raw_data={"earnings": [{"quarter": "2024-01-25", "actual_eps": 2.18}]},
            provider="fmp",
        )

        mock_session = AsyncMock()
        asset_upsert_result = MagicMock()
        asset_upsert_result.scalar_one.return_value = 1
        fd_upsert_result = MagicMock()
        asset_obj = MagicMock()
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
            provider=yf_provider,
            session=mock_session,
            fallback_provider=fmp_provider,
        )

        assert result.status == "ok"  # FMP rescued the earnings
        fmp_provider.fetch_earnings.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_no_fallback_stays_partial(self):
        """Without fallback provider, failed categories stay failed."""
        from margin_api.cli import seed_ticker_data

        yf_provider = MagicMock()
        yf_provider.fetch_all.return_value = {
            "fundamentals": _make_fetch_result(
                DataCategory.FUNDAMENTALS,
                raw_data={
                    "income_statement": {},
                    "balance_sheet": {},
                    "cash_flow": {},
                },
            ),
            "price": _make_fetch_result(DataCategory.PRICE, raw_data={"bars": []}),
            "earnings": _make_fetch_result(DataCategory.EARNINGS, success=False, error="lxml"),
            "info": _make_fetch_result(
                DataCategory.FUNDAMENTALS,
                raw_data={
                    "shortName": "Apple",
                    "sector": "Technology",
                    "country": "United States",
                    "marketCap": 3000000000000,
                },
            ),
        }

        mock_session = AsyncMock()
        asset_upsert_result = MagicMock()
        asset_upsert_result.scalar_one.return_value = 1
        fd_upsert_result = MagicMock()
        asset_obj = MagicMock()
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
            provider=yf_provider,
            session=mock_session,
            # No fallback_provider
        )

        assert result.status == "partial"
        assert "earnings" in result.categories_failed

    @pytest.mark.asyncio
    async def test_fallback_failure_does_not_crash(self):
        """When fallback provider also fails, the category stays failed."""
        from margin_api.cli import seed_ticker_data

        yf_provider = MagicMock()
        yf_provider.fetch_all.return_value = {
            "fundamentals": _make_fetch_result(
                DataCategory.FUNDAMENTALS,
                raw_data={
                    "income_statement": {"Total Revenue": 100000},
                    "balance_sheet": {"Total Assets": 500000},
                    "cash_flow": {"Operating Cash Flow": 40000},
                },
            ),
            "price": _make_fetch_result(DataCategory.PRICE, raw_data={"bars": [{"Close": 150.0}]}),
            "earnings": _make_fetch_result(
                DataCategory.EARNINGS, success=False, error="lxml missing"
            ),
            "info": _make_fetch_result(
                DataCategory.FUNDAMENTALS,
                raw_data={
                    "shortName": "Apple Inc.",
                    "sector": "Technology",
                    "country": "United States",
                    "marketCap": 3000000000000,
                    "sharesOutstanding": 15000000000,
                },
            ),
        }

        # Fallback provider: FMP -- also fails
        fmp_provider = MagicMock()
        fmp_provider.fetch_earnings.side_effect = Exception("FMP API down")

        mock_session = AsyncMock()
        asset_upsert_result = MagicMock()
        asset_upsert_result.scalar_one.return_value = 1
        fd_upsert_result = MagicMock()
        asset_obj = MagicMock()
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
            provider=yf_provider,
            session=mock_session,
            fallback_provider=fmp_provider,
        )

        # Should still be partial, not crashed
        assert result.status == "partial"
        assert "earnings" in result.categories_failed
        fmp_provider.fetch_earnings.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_fallback_not_called_for_successful_categories(self):
        """When all yfinance categories succeed, fallback is never called."""
        from margin_api.cli import seed_ticker_data

        yf_provider = MagicMock()
        yf_provider.fetch_all.return_value = {
            "fundamentals": _make_fetch_result(
                DataCategory.FUNDAMENTALS,
                raw_data={
                    "income_statement": {"Total Revenue": 100000},
                    "balance_sheet": {"Total Assets": 500000},
                    "cash_flow": {"Operating Cash Flow": 40000},
                },
            ),
            "price": _make_fetch_result(DataCategory.PRICE, raw_data={"bars": [{"Close": 150.0}]}),
            "earnings": _make_fetch_result(
                DataCategory.EARNINGS,
                raw_data={"earnings": [{"quarter": "2024-01-25", "actual_eps": 2.18}]},
            ),
            "info": _make_fetch_result(
                DataCategory.FUNDAMENTALS,
                raw_data={
                    "shortName": "Apple Inc.",
                    "sector": "Technology",
                    "country": "United States",
                    "marketCap": 3000000000000,
                    "sharesOutstanding": 15000000000,
                },
            ),
        }

        fmp_provider = MagicMock()

        mock_session = AsyncMock()
        asset_upsert_result = MagicMock()
        asset_upsert_result.scalar_one.return_value = 1
        fd_upsert_result = MagicMock()
        asset_obj = MagicMock()
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
            provider=yf_provider,
            session=mock_session,
            fallback_provider=fmp_provider,
        )

        assert result.status == "ok"
        # No fallback methods should be called
        fmp_provider.fetch_fundamentals.assert_not_called()
        fmp_provider.fetch_price_history.assert_not_called()
        fmp_provider.fetch_earnings.assert_not_called()
