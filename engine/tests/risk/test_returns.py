"""Tests for risk.returns module."""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
from margin_engine.models.financial import PriceBar
from margin_engine.risk.returns import returns_from_price_bars


def _make_bar(date: str, close: float) -> PriceBar:
    """Create a PriceBar with all fields set to the given close price."""
    d = Decimal(str(close))
    return PriceBar(
        date=date,
        open=d,
        high=d,
        low=d,
        close=d,
        volume=1000,
        adj_close=d,
    )


def _make_bars(count: int = 14) -> list[PriceBar]:
    """Create a list of price bars with sequential dates and prices."""
    return [_make_bar(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, count + 1)]


class TestReturnsFromPriceBars:
    """Tests for returns_from_price_bars."""

    def test_two_tickers_correct_shape_and_values(self) -> None:
        """Two tickers produce correct shape and log return values."""
        bars_a = [_make_bar(f"2025-01-{d:02d}", p) for d, p in [
            (1, 100.0), (2, 105.0), (3, 110.0), (6, 108.0), (7, 112.0),
            (8, 115.0), (9, 118.0), (10, 120.0), (13, 122.0), (14, 125.0),
            (15, 128.0),
        ]]
        bars_b = [_make_bar(f"2025-01-{d:02d}", p) for d, p in [
            (1, 50.0), (2, 52.0), (3, 54.0), (6, 53.0), (7, 55.0),
            (8, 56.0), (9, 57.0), (10, 58.0), (13, 59.0), (14, 60.0),
            (15, 61.0),
        ]]
        matrix, tickers = returns_from_price_bars({"AAPL": bars_a, "MSFT": bars_b})
        assert tickers == ["AAPL", "MSFT"]
        assert matrix.shape == (10, 2)  # 11 bars -> 10 returns, 2 tickers

        # Verify first return: log(105/100) for AAPL
        expected_aapl_r1 = math.log(105.0 / 100.0)
        np.testing.assert_allclose(matrix[0, 0], expected_aapl_r1, rtol=1e-10)

        # Verify first return: log(52/50) for MSFT
        expected_msft_r1 = math.log(52.0 / 50.0)
        np.testing.assert_allclose(matrix[0, 1], expected_msft_r1, rtol=1e-10)

    def test_empty_input_returns_empty(self) -> None:
        """Empty price_data returns empty array and empty list."""
        matrix, tickers = returns_from_price_bars({})
        assert tickers == []
        assert matrix.shape == (0, 0)

    def test_single_ticker_returns_column(self) -> None:
        """Single ticker returns (T, 1) matrix."""
        bars = [_make_bar(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 15)]
        matrix, tickers = returns_from_price_bars({"AAPL": bars})
        assert tickers == ["AAPL"]
        assert matrix.shape[1] == 1
        assert matrix.shape[0] == 13  # 14 bars -> 13 returns

    def test_tickers_with_few_bars_excluded(self) -> None:
        """Tickers with fewer than 10 bars are excluded."""
        # 5 bars -- too few
        short_bars = [_make_bar(f"2025-01-{d:02d}", 100.0) for d in range(1, 6)]
        # 15 bars -- enough
        long_bars = [_make_bar(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 16)]
        matrix, tickers = returns_from_price_bars({"SHORT": short_bars, "LONG": long_bars})
        assert tickers == ["LONG"]
        assert matrix.shape[1] == 1

    def test_window_days_limits_trailing_bars(self) -> None:
        """window_days limits the number of trailing bars used."""
        bars = [_make_bar(f"2025-{m:02d}-{d:02d}", 100.0 + i)
                for i, (m, d) in enumerate(
                    [(1, j) for j in range(1, 32)]
                    + [(2, j) for j in range(1, 29)]
                )]
        # With window_days=15, only last 15 bars used -> 14 returns
        matrix, tickers = returns_from_price_bars({"AAPL": bars}, window_days=15)
        assert tickers == ["AAPL"]
        assert matrix.shape[0] == 14

    def test_tickers_sorted_alphabetically(self) -> None:
        """Tickers are sorted alphabetically in output."""
        data = {"ZZZ": _make_bars(), "AAA": _make_bars(), "MMM": _make_bars()}
        _, tickers = returns_from_price_bars(data)
        assert tickers == ["AAA", "MMM", "ZZZ"]

    def test_missing_dates_filled_with_zero(self) -> None:
        """Tickers with different trading dates get 0.0 for missing dates."""
        # Ticker A has dates 1-12
        bars_a = [_make_bar(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 13)]
        # Ticker B has dates 3-14 (overlapping but shifted)
        bars_b = [_make_bar(f"2025-01-{d:02d}", 50.0 + d) for d in range(3, 15)]
        matrix, tickers = returns_from_price_bars({"A": bars_a, "B": bars_b})
        assert tickers == ["A", "B"]
        # Union of return dates: A has returns for dates 2-12, B has returns for dates 4-14
        # The matrix should contain some zeros for misaligned dates
        a_col = matrix[:, 0]
        b_col = matrix[:, 1]
        # A has no returns past date 12, B has no returns before date 4
        assert np.any(a_col == 0.0)
        assert np.any(b_col == 0.0)

    def test_adj_close_preferred_over_close(self) -> None:
        """adj_close is used when available; close is fallback."""
        bars = []
        for d, c, ac in [(1, 100.0, 95.0), (2, 105.0, 100.0),
                         (3, 110.0, 105.0), (4, 108.0, 103.0),
                         (5, 112.0, 107.0), (6, 115.0, 110.0),
                         (7, 118.0, 113.0), (8, 120.0, 115.0),
                         (9, 122.0, 117.0), (10, 125.0, 120.0),
                         (11, 128.0, 123.0)]:
            bars.append(PriceBar(
                date=f"2025-01-{d:02d}",
                open=Decimal(str(c)),
                high=Decimal(str(c)),
                low=Decimal(str(c)),
                close=Decimal(str(c)),
                volume=1000,
                adj_close=Decimal(str(ac)),
            ))
        matrix, tickers = returns_from_price_bars({"X": bars})
        # First return should use adj_close: log(100/95)
        expected = math.log(100.0 / 95.0)
        np.testing.assert_allclose(matrix[0, 0], expected, rtol=1e-10)
