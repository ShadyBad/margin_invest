"""Tests for forward returns computation."""

from __future__ import annotations

from datetime import date, timedelta

from margin_engine.ml.forward_returns import compute_forward_returns


def _make_price_series(
    start_price: float,
    end_price: float,
    n_bars: int,
    scored_at_idx: int,
    base_date: date | None = None,
) -> list[dict]:
    """Create price bars with linear interpolation.

    The bar at scored_at_idx has close=start_price.
    The bar at scored_at_idx + 252 has close=end_price (if within range).
    Bars before scored_at_idx and after scored_at_idx + 252 hold constant values.
    """
    if base_date is None:
        base_date = date(2024, 1, 2)

    horizon = 252
    bars: list[dict] = []

    for i in range(n_bars):
        if i <= scored_at_idx:
            close = start_price
        elif i >= scored_at_idx + horizon:
            close = end_price
        else:
            # Linear interpolation between scored_at_idx and scored_at_idx + horizon
            frac = (i - scored_at_idx) / horizon
            close = start_price + frac * (end_price - start_price)

        bars.append(
            {
                "date": (base_date + timedelta(days=i)).isoformat(),
                "close": close,
            }
        )

    return bars


class TestBasicForwardReturn:
    def test_basic_forward_return(self) -> None:
        """Price 100 -> 120 over horizon = 20% return."""
        scored_at_idx = 10
        bars = _make_price_series(
            start_price=100.0,
            end_price=120.0,
            n_bars=300,
            scored_at_idx=scored_at_idx,
        )
        scored_at_date = bars[scored_at_idx]["date"]

        result = compute_forward_returns(
            scored_tickers=[{"ticker": "AAPL", "scored_at": scored_at_date}],
            price_data={"AAPL": bars},
            horizon_days=252,
        )

        assert "AAPL" in result
        assert abs(result["AAPL"] - 0.20) < 1e-10


class TestInsufficientFutureData:
    def test_ticker_excluded_when_insufficient_future_data(self) -> None:
        """Fewer bars than horizon after scored_at = excluded."""
        scored_at_idx = 10
        # Only 200 bars total, so after index 10 there are only 189 bars (< 252)
        bars = _make_price_series(
            start_price=100.0,
            end_price=120.0,
            n_bars=200,
            scored_at_idx=scored_at_idx,
        )
        scored_at_date = bars[scored_at_idx]["date"]

        result = compute_forward_returns(
            scored_tickers=[{"ticker": "AAPL", "scored_at": scored_at_date}],
            price_data={"AAPL": bars},
            horizon_days=252,
        )

        assert "AAPL" not in result
        assert result == {}


class TestNegativeReturn:
    def test_negative_return(self) -> None:
        """Price 100 -> 80 = -20% return."""
        scored_at_idx = 10
        bars = _make_price_series(
            start_price=100.0,
            end_price=80.0,
            n_bars=300,
            scored_at_idx=scored_at_idx,
        )
        scored_at_date = bars[scored_at_idx]["date"]

        result = compute_forward_returns(
            scored_tickers=[{"ticker": "TEST", "scored_at": scored_at_date}],
            price_data={"TEST": bars},
            horizon_days=252,
        )

        assert "TEST" in result
        assert abs(result["TEST"] - (-0.20)) < 1e-10


class TestMultipleTickers:
    def test_multiple_tickers(self) -> None:
        """Two tickers each get their own return."""
        scored_at_idx = 10

        bars_a = _make_price_series(
            start_price=100.0,
            end_price=150.0,
            n_bars=300,
            scored_at_idx=scored_at_idx,
        )
        bars_b = _make_price_series(
            start_price=200.0,
            end_price=180.0,
            n_bars=300,
            scored_at_idx=scored_at_idx,
        )

        scored_at_date = bars_a[scored_at_idx]["date"]

        result = compute_forward_returns(
            scored_tickers=[
                {"ticker": "AAA", "scored_at": scored_at_date},
                {"ticker": "BBB", "scored_at": scored_at_date},
            ],
            price_data={"AAA": bars_a, "BBB": bars_b},
            horizon_days=252,
        )

        assert len(result) == 2
        assert abs(result["AAA"] - 0.50) < 1e-10
        assert abs(result["BBB"] - (-0.10)) < 1e-10


class TestDelistedTickers:
    def test_delisted_ticker_gets_negative_100(self) -> None:
        """Delisted tickers get -100% return (survivorship bias handling)."""
        result = compute_forward_returns(
            scored_tickers=[{"ticker": "DLST", "scored_at": "2024-01-12"}],
            price_data={},
            delisted_tickers={"DLST"},
            horizon_days=252,
        )

        assert "DLST" in result
        assert result["DLST"] == -1.0

    def test_delisted_overrides_price_data(self) -> None:
        """Even if price data exists, delisted flag takes precedence."""
        scored_at_idx = 10
        bars = _make_price_series(
            start_price=100.0,
            end_price=120.0,
            n_bars=300,
            scored_at_idx=scored_at_idx,
        )
        scored_at_date = bars[scored_at_idx]["date"]

        result = compute_forward_returns(
            scored_tickers=[{"ticker": "DLST", "scored_at": scored_at_date}],
            price_data={"DLST": bars},
            delisted_tickers={"DLST"},
            horizon_days=252,
        )

        assert result["DLST"] == -1.0

    def test_delisted_mixed_with_normal(self) -> None:
        """Delisted and normal tickers coexist in the same call."""
        scored_at_idx = 10
        bars = _make_price_series(
            start_price=100.0,
            end_price=120.0,
            n_bars=300,
            scored_at_idx=scored_at_idx,
        )
        scored_at_date = bars[scored_at_idx]["date"]

        result = compute_forward_returns(
            scored_tickers=[
                {"ticker": "AAPL", "scored_at": scored_at_date},
                {"ticker": "DLST", "scored_at": scored_at_date},
            ],
            price_data={"AAPL": bars},
            delisted_tickers={"DLST"},
            horizon_days=252,
        )

        assert abs(result["AAPL"] - 0.20) < 1e-10
        assert result["DLST"] == -1.0


class TestMissingTickerExcluded:
    def test_missing_ticker_in_prices_excluded(self) -> None:
        """Ticker not in price_data = excluded."""
        result = compute_forward_returns(
            scored_tickers=[{"ticker": "MISSING", "scored_at": "2024-01-12"}],
            price_data={},
            horizon_days=252,
        )

        assert "MISSING" not in result
        assert result == {}
