"""Tests for shrunk return correlation computation."""

import datetime as dt
from decimal import Decimal

import pytest
from margin_engine.correlation import compute_shrunk_return_correlations
from margin_engine.models.financial import PriceBar


def _bar(date_str: str, close: float) -> PriceBar:
    p = Decimal(str(close))
    return PriceBar(date=date_str, open=p, high=p, low=p, close=p, volume=100_000)


def _daily_bars(start: str, prices: list[float]) -> list[PriceBar]:
    base = dt.date.fromisoformat(start)
    bars = []
    day = 0
    for p in prices:
        d = base + dt.timedelta(days=day)
        while d.weekday() >= 5:
            day += 1
            d = base + dt.timedelta(days=day)
        bars.append(_bar(d.isoformat(), p))
        day += 1
    return bars


def _correlated_prices(n: int, base: float = 100.0, step: float = 0.5) -> list[float]:
    """Generate prices that trend upward."""
    return [base + i * step for i in range(n)]


def _anticorrelated_prices(n: int, base: float = 100.0, step: float = 0.5) -> list[float]:
    """Generate prices that trend downward."""
    return [base - i * step for i in range(n)]


def _noisy_prices(n: int, base: float = 100.0) -> list[float]:
    """Generate prices with an alternating zig-zag pattern."""
    return [base + (i % 3) * 2 - 1 for i in range(n)]


@pytest.fixture()
def three_ticker_data():
    """Three tickers: two correlated (upward), one anticorrelated (downward)."""
    n = 85
    return {
        "AAA": _daily_bars("2024-01-02", _correlated_prices(n, base=100.0, step=0.3)),
        "BBB": _daily_bars("2024-01-02", _correlated_prices(n, base=50.0, step=0.15)),
        "CCC": _daily_bars("2024-01-02", _anticorrelated_prices(n, base=200.0, step=0.2)),
    }


class TestShrunkCorrelationMatrix:
    def test_diagonal_is_one(self, three_ticker_data):
        """Diagonal of the correlation matrix should be 1.0."""
        result = compute_shrunk_return_correlations(three_ticker_data)
        assert len(result.tickers) == 3
        for i in range(len(result.tickers)):
            assert result.matrix[i][i] == pytest.approx(1.0)

    def test_symmetric(self, three_ticker_data):
        """Correlation matrix should be symmetric: matrix[i][j] == matrix[j][i]."""
        result = compute_shrunk_return_correlations(three_ticker_data)
        n = len(result.tickers)
        for i in range(n):
            for j in range(n):
                assert result.matrix[i][j] == pytest.approx(result.matrix[j][i])

    def test_values_in_range(self, three_ticker_data):
        """All correlation values should be between -1 and 1."""
        result = compute_shrunk_return_correlations(three_ticker_data)
        for row in result.matrix:
            for val in row:
                assert val is not None
                assert -1.0 <= val <= 1.0

    def test_single_ticker_fallback(self):
        """Single ticker should fall back gracefully to a 1x1 matrix."""
        data = {
            "SOLO": _daily_bars("2024-01-02", _correlated_prices(85)),
        }
        result = compute_shrunk_return_correlations(data)
        assert len(result.tickers) == 1
        assert result.tickers[0] == "SOLO"
        assert result.matrix == [[1.0]]

    def test_excluded_tickers_populated(self):
        """Ticker with too few bars should appear in excluded list."""
        data = {
            "GOOD1": _daily_bars("2024-01-02", _correlated_prices(85)),
            "GOOD2": _daily_bars("2024-01-02", _anticorrelated_prices(85, base=200.0)),
            "SHORT": _daily_bars("2024-01-02", _correlated_prices(3)),  # only 3 bars
        }
        result = compute_shrunk_return_correlations(data, min_bars=10)
        excluded_tickers = [e.ticker for e in result.excluded]
        assert "SHORT" in excluded_tickers
        assert "GOOD1" not in excluded_tickers
        assert "GOOD2" not in excluded_tickers
        # Valid tickers should still be in the matrix
        assert "GOOD1" in result.tickers
        assert "GOOD2" in result.tickers

    def test_method_propagates(self, three_ticker_data):
        """Calling with method='linear' still returns a valid CorrelationMatrix."""
        result = compute_shrunk_return_correlations(
            three_ticker_data, method="linear"
        )
        assert len(result.tickers) == 3
        # Should still be a valid correlation matrix
        for i in range(len(result.tickers)):
            assert result.matrix[i][i] == pytest.approx(1.0)
        for row in result.matrix:
            for val in row:
                assert val is not None
                assert -1.0 <= val <= 1.0
