"""Tests for the price backfill service."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from margin_api.services.edgar.price_backfill import (
    _download_and_extract,
    backfill_prices_for_tickers,
    build_price_rows,
)


class TestBuildPriceRows:
    """Tests for build_price_rows conversion from yfinance DataFrame."""

    def test_build_price_rows_from_dataframe(self) -> None:
        """Convert a yfinance DataFrame into price row dicts."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        df = pd.DataFrame(
            {
                "Open": [150.0, 152.0, 153.0],
                "High": [155.0, 157.0, 158.0],
                "Low": [149.0, 151.0, 152.0],
                "Close": [154.0, 156.0, 157.0],
                "Adj Close": [153.5, 155.5, 156.5],
                "Volume": [1000000, 1100000, 1200000],
            },
            index=dates,
        )

        rows = build_price_rows("AAPL", df)

        assert len(rows) == 3
        assert rows[0]["ticker"] == "AAPL"
        assert rows[0]["date"] == date(2024, 1, 2)
        assert rows[0]["open"] == 150.0
        assert rows[0]["high"] == 155.0
        assert rows[0]["low"] == 149.0
        assert rows[0]["close"] == 154.0
        assert rows[0]["adj_close"] == 153.5
        assert rows[0]["volume"] == 1000000
        assert rows[0]["source"] == "yfinance"

        # Verify types are native Python, not numpy
        assert type(rows[0]["open"]) is float
        assert type(rows[0]["volume"]) is int
        assert type(rows[0]["date"]) is date

        # Verify all rows have correct ticker
        assert all(r["ticker"] == "AAPL" for r in rows)

        # Verify second row
        assert rows[1]["date"] == date(2024, 1, 3)
        assert rows[1]["close"] == 156.0
        assert rows[1]["volume"] == 1100000

    def test_build_price_rows_skips_nan(self) -> None:
        """NaN close values should be skipped."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        df = pd.DataFrame(
            {
                "Open": [150.0, 152.0],
                "High": [155.0, 157.0],
                "Low": [149.0, 151.0],
                "Close": [154.0, float("nan")],
                "Adj Close": [153.5, float("nan")],
                "Volume": [1000000, 1100000],
            },
            index=dates,
        )

        rows = build_price_rows("AAPL", df)

        assert len(rows) == 1
        assert rows[0]["date"] == date(2024, 1, 2)
        assert rows[0]["close"] == 154.0

    def test_build_price_rows_empty(self) -> None:
        """Empty DataFrame returns empty list."""
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"])

        rows = build_price_rows("AAPL", df)

        assert rows == []

    def test_build_price_rows_numpy_types_converted(self) -> None:
        """Numpy types (float64, int64) are converted to native Python types."""
        dates = pd.to_datetime(["2024-06-15"])
        df = pd.DataFrame(
            {
                "Open": np.array([100.5], dtype=np.float64),
                "High": np.array([105.0], dtype=np.float64),
                "Low": np.array([99.0], dtype=np.float64),
                "Close": np.array([103.0], dtype=np.float64),
                "Adj Close": np.array([102.5], dtype=np.float64),
                "Volume": np.array([5000000], dtype=np.int64),
            },
            index=dates,
        )

        rows = build_price_rows("MSFT", df)

        assert len(rows) == 1
        row = rows[0]
        assert type(row["open"]) is float
        assert type(row["high"]) is float
        assert type(row["low"]) is float
        assert type(row["close"]) is float
        assert type(row["adj_close"]) is float
        assert type(row["volume"]) is int
        assert row["ticker"] == "MSFT"

    def test_build_price_rows_all_nan_close(self) -> None:
        """DataFrame where all Close values are NaN returns empty list."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        df = pd.DataFrame(
            {
                "Open": [150.0, 152.0],
                "High": [155.0, 157.0],
                "Low": [149.0, 151.0],
                "Close": [float("nan"), float("nan")],
                "Adj Close": [float("nan"), float("nan")],
                "Volume": [1000000, 1100000],
            },
            index=dates,
        )

        rows = build_price_rows("AAPL", df)

        assert rows == []


def _make_ticker_df(tickers: list[str], missing: set[str] | None = None) -> pd.DataFrame:
    """Build a fake DataFrame like yfinance group_by='ticker', auto_adjust=False returns.

    Returns a MultiIndex-columned DataFrame with (ticker, field) pairs.
    Tickers in ``missing`` are excluded to simulate no-data responses.
    """
    if missing is None:
        missing = set()
    dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
    cols = {}
    for t in tickers:
        if t in missing:
            continue
        for field, vals in [
            ("Open", [100.0, 101.0]),
            ("High", [105.0, 106.0]),
            ("Low", [99.0, 100.0]),
            ("Close", [103.0, 104.0]),
            ("Adj Close", [102.5, 103.5]),
            ("Volume", [1_000_000, 1_100_000]),
        ]:
            cols[(t, field)] = vals
    df = pd.DataFrame(cols, index=dates)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


class TestDownloadAndExtract:
    """Tests for _download_and_extract helper."""

    @patch("yfinance.download")
    def test_single_ticker_success(self, mock_download: MagicMock) -> None:
        """Single ticker download returns rows and no failures."""
        mock_download.return_value = _make_ticker_df(["AAPL"])

        rows, failed = _download_and_extract(["AAPL"], "2024-01-01", "2024-01-05")

        assert len(rows) == 2  # 2 dates in the mock
        assert rows[0]["ticker"] == "AAPL"
        assert failed == []

    @patch("yfinance.download")
    def test_single_ticker_empty(self, mock_download: MagicMock) -> None:
        """Single ticker with no data is reported as failed."""
        mock_download.return_value = pd.DataFrame()

        rows, failed = _download_and_extract(["AAPL"], "2024-01-01", "2024-01-05")

        assert rows == []
        assert failed == ["AAPL"]

    @patch("yfinance.download")
    def test_multi_ticker_partial_failure(self, mock_download: MagicMock) -> None:
        """Multi-ticker download where some tickers are missing from result."""
        mock_download.return_value = _make_ticker_df(["AAPL", "MSFT", "GOOG"], missing={"GOOG"})

        rows, failed = _download_and_extract(["AAPL", "MSFT", "GOOG"], "2024-01-01", "2024-01-05")

        tickers_in_rows = {r["ticker"] for r in rows}
        assert "AAPL" in tickers_in_rows
        assert "MSFT" in tickers_in_rows
        assert "GOOG" not in tickers_in_rows
        assert failed == ["GOOG"]


class TestBackfillRetryLogic:
    """Tests for backfill_prices_for_tickers retry and alerting."""

    @pytest.mark.asyncio
    @patch("margin_api.services.edgar.price_backfill._download_and_extract")
    async def test_retries_failed_tickers(self, mock_extract: MagicMock) -> None:
        """Failed tickers from first pass are retried with smaller batches."""
        # First call: GOOG fails
        mock_extract.side_effect = [
            (
                [{"ticker": "AAPL", "close": 100.0}],
                ["GOOG"],
            ),
            # Retry attempt 1: GOOG succeeds
            (
                [{"ticker": "GOOG", "close": 200.0}],
                [],
            ),
        ]

        result = await backfill_prices_for_tickers(
            tickers=["AAPL", "GOOG"],
            batch_size=10,
            batch_delay=0,
            max_retries=1,
        )

        assert "AAPL" in result
        assert "GOOG" in result
        assert mock_extract.call_count == 2

    @pytest.mark.asyncio
    @patch("margin_api.services.edgar.price_backfill._download_and_extract")
    async def test_no_retry_when_all_succeed(self, mock_extract: MagicMock) -> None:
        """No retry phase when all tickers succeed."""
        mock_extract.return_value = (
            [{"ticker": "AAPL", "close": 100.0}],
            [],
        )

        result = await backfill_prices_for_tickers(
            tickers=["AAPL"],
            batch_size=10,
            batch_delay=0,
        )

        assert "AAPL" in result
        assert mock_extract.call_count == 1

    @pytest.mark.asyncio
    @patch("margin_api.services.edgar.price_backfill._download_and_extract")
    async def test_high_failure_rate_logs_error(
        self, mock_extract: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When >50% tickers fail, an ERROR log is emitted."""
        # All tickers fail
        mock_extract.return_value = ([], ["A", "B", "C"])

        import logging

        with caplog.at_level(logging.ERROR, logger="margin_api.services.edgar.price_backfill"):
            await backfill_prices_for_tickers(
                tickers=["A", "B", "C"],
                batch_size=10,
                batch_delay=0,
                max_retries=0,
            )

        assert any("HIGH FAILURE RATE" in msg for msg in caplog.messages)

    @pytest.mark.asyncio
    @patch("margin_api.services.edgar.price_backfill._download_and_extract")
    async def test_batch_delay_is_applied(self, mock_extract: MagicMock) -> None:
        """Verify asyncio.sleep is called between batches."""
        mock_extract.return_value = ([{"ticker": "A", "close": 1.0}], [])

        with patch("margin_api.services.edgar.price_backfill.asyncio.sleep") as mock_sleep:
            await backfill_prices_for_tickers(
                tickers=["A", "B"],
                batch_size=1,
                batch_delay=0.5,
                max_retries=0,
            )
            # Sleep called between batch 1 and batch 2
            mock_sleep.assert_called()
            mock_sleep.assert_any_call(0.5)
