"""Tests for the price backfill service."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from margin_api.services.edgar.price_backfill import build_price_rows


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
