"""Tests for compute_historical_forward_returns."""

from __future__ import annotations

from datetime import date, timedelta

from margin_engine.ml.historical_forward_returns import compute_historical_forward_returns


def _make_pit_prices(
    n_bars: int,
    start_date: date,
    start_price: float = 100.0,
    end_price: float | None = None,
) -> list[dict]:
    """Create date-indexed price bars with linear price interpolation.

    Args:
        n_bars: Total number of bars to create.
        start_date: The date for bar index 0.
        start_price: Price at the first bar.
        end_price: Price at the last bar. If None, holds constant at start_price.

    Returns:
        List of dicts with 'date' (ISO string) and 'close' (float).
    """
    if end_price is None:
        end_price = start_price

    bars: list[dict] = []
    for i in range(n_bars):
        if n_bars == 1:
            close = start_price
        else:
            frac = i / (n_bars - 1)
            close = start_price + frac * (end_price - start_price)

        bars.append(
            {
                "date": (start_date + timedelta(days=i)).isoformat(),
                "close": close,
            }
        )

    return bars


class TestHistoricalForwardReturns:
    def test_basic_forward_return(self) -> None:
        """Score date with enough data -> return computed correctly."""
        # 600 bars starting 2024-01-01; score_date somewhere in the middle
        start = date(2024, 1, 1)
        bars = _make_pit_prices(
            n_bars=600,
            start_date=start,
            start_price=100.0,
            end_price=200.0,  # linear ramp so we can calculate expected return
        )

        # score_date is around bar index ~90 (2024-03-31 = day 90 from Jan 1)
        score_date = date(2024, 3, 31)

        result = compute_historical_forward_returns(
            pit_prices={"AAPL": bars},
            score_date=score_date,
            horizon_days=252,
        )

        assert "AAPL" in result
        # Return must be a non-trivial float
        assert isinstance(result["AAPL"], float)
        # Price increases from start to end over 600 bars; return should be positive
        assert result["AAPL"] > 0.0

    def test_basic_forward_return_exact_value(self) -> None:
        """Verify exact return calculation using constant prices around score date."""
        start = date(2024, 1, 1)
        # Flat at 100 for first 200 bars, then flat at 150 after bar 200
        # We'll use a 2-segment approach via a simple construct:
        # Create 600 bars: score bar is index 100 (date=2024-04-10), future bar index 352
        bars: list[dict] = []
        score_bar_idx = 100
        for i in range(600):
            if i <= score_bar_idx:
                close = 100.0
            elif i >= score_bar_idx + 252:
                close = 150.0
            else:
                frac = (i - score_bar_idx) / 252
                close = 100.0 + frac * 50.0
            bars.append({"date": (start + timedelta(days=i)).isoformat(), "close": close})

        score_date = start + timedelta(days=score_bar_idx)  # exact match

        result = compute_historical_forward_returns(
            pit_prices={"AAPL": bars},
            score_date=score_date,
            horizon_days=252,
        )

        assert "AAPL" in result
        assert abs(result["AAPL"] - 0.50) < 1e-10

    def test_insufficient_future_data_excluded(self) -> None:
        """Too few bars after score_date -> ticker excluded (not defaulted to 0.0)."""
        start = date(2024, 1, 1)
        # Only 100 bars; score_date is near the start, so not enough future bars
        bars = _make_pit_prices(n_bars=100, start_date=start, start_price=100.0)

        score_date = date(2024, 1, 15)  # bar index ~14, only 85 future bars < 252

        result = compute_historical_forward_returns(
            pit_prices={"AAPL": bars},
            score_date=score_date,
            horizon_days=252,
        )

        assert "AAPL" not in result
        assert result == {}

    def test_multiple_tickers(self) -> None:
        """Two tickers each get their own forward return."""
        start = date(2024, 1, 1)
        score_bar_idx = 50

        # AAPL: 100 -> 120 over horizon
        bars_a: list[dict] = []
        for i in range(500):
            if i <= score_bar_idx:
                close = 100.0
            elif i >= score_bar_idx + 252:
                close = 120.0
            else:
                frac = (i - score_bar_idx) / 252
                close = 100.0 + frac * 20.0
            bars_a.append({"date": (start + timedelta(days=i)).isoformat(), "close": close})

        # MSFT: 200 -> 160 over horizon
        bars_b: list[dict] = []
        for i in range(500):
            if i <= score_bar_idx:
                close = 200.0
            elif i >= score_bar_idx + 252:
                close = 160.0
            else:
                frac = (i - score_bar_idx) / 252
                close = 200.0 + frac * (-40.0)
            bars_b.append({"date": (start + timedelta(days=i)).isoformat(), "close": close})

        score_date = start + timedelta(days=score_bar_idx)

        result = compute_historical_forward_returns(
            pit_prices={"AAPL": bars_a, "MSFT": bars_b},
            score_date=score_date,
            horizon_days=252,
        )

        assert len(result) == 2
        assert abs(result["AAPL"] - 0.20) < 1e-10
        assert abs(result["MSFT"] - (-0.20)) < 1e-10

    def test_empty_prices_returns_empty(self) -> None:
        """No price data -> empty dict returned."""
        result = compute_historical_forward_returns(
            pit_prices={},
            score_date=date(2024, 3, 31),
        )
        assert result == {}

    def test_no_price_at_score_date_excluded(self) -> None:
        """Prices start well after score_date (gap > max_date_gap) -> excluded."""
        # Bars start 2024-06-01; score_date is 2024-01-01 -> gap > 5 days
        start = date(2024, 6, 1)
        bars = _make_pit_prices(n_bars=500, start_date=start, start_price=100.0)

        result = compute_historical_forward_returns(
            pit_prices={"AAPL": bars},
            score_date=date(2024, 1, 1),
            horizon_days=252,
        )

        assert "AAPL" not in result
        assert result == {}

    def test_max_date_gap_boundary(self) -> None:
        """Ticker is included when gap equals max_date_gap and excluded when exceeds it."""
        # First bar is on 2024-01-06 (5 calendar days from score_date 2024-01-01)
        bars = _make_pit_prices(
            n_bars=500,
            start_date=date(2024, 1, 6),
            start_price=100.0,
            end_price=130.0,
        )

        score_date = date(2024, 1, 1)

        # Exactly 5 days gap -> should be included (gap == max_date_gap)
        result_included = compute_historical_forward_returns(
            pit_prices={"AAPL": bars},
            score_date=score_date,
            horizon_days=252,
            max_date_gap=5,
        )
        assert "AAPL" in result_included

        # Gap is 5 but max_date_gap=4 -> excluded
        result_excluded = compute_historical_forward_returns(
            pit_prices={"AAPL": bars},
            score_date=score_date,
            horizon_days=252,
            max_date_gap=4,
        )
        assert "AAPL" not in result_excluded

    def test_zero_score_price_excluded(self) -> None:
        """score_price <= 0 -> ticker excluded to avoid division by zero."""
        start = date(2024, 1, 1)
        bars = _make_pit_prices(n_bars=500, start_date=start, start_price=0.0, end_price=100.0)
        # score_price at index 0 is 0.0

        result = compute_historical_forward_returns(
            pit_prices={"AAPL": bars},
            score_date=start,
            horizon_days=252,
        )

        assert "AAPL" not in result

    def test_empty_bars_list_excluded(self) -> None:
        """Empty bar list for a ticker -> excluded."""
        result = compute_historical_forward_returns(
            pit_prices={"AAPL": []},
            score_date=date(2024, 1, 1),
        )
        assert "AAPL" not in result

    def test_partial_tickers_with_sufficient_data(self) -> None:
        """Only tickers with sufficient data appear in the result."""
        start = date(2024, 1, 1)
        score_date = date(2024, 1, 10)  # bar index ~9

        # GOOD: 500 bars, enough future data
        bars_good = _make_pit_prices(
            n_bars=500, start_date=start, start_price=100.0, end_price=110.0
        )

        # BAD: only 50 bars total
        bars_bad = _make_pit_prices(n_bars=50, start_date=start, start_price=200.0, end_price=250.0)

        result = compute_historical_forward_returns(
            pit_prices={"GOOD": bars_good, "BAD": bars_bad},
            score_date=score_date,
            horizon_days=252,
        )

        assert "GOOD" in result
        assert "BAD" not in result

    def test_negative_return_computed(self) -> None:
        """Negative returns are computed correctly."""
        start = date(2024, 1, 1)
        score_bar_idx = 50

        bars: list[dict] = []
        for i in range(500):
            if i <= score_bar_idx:
                close = 200.0
            elif i >= score_bar_idx + 252:
                close = 100.0
            else:
                frac = (i - score_bar_idx) / 252
                close = 200.0 + frac * (-100.0)
            bars.append({"date": (start + timedelta(days=i)).isoformat(), "close": close})

        score_date = start + timedelta(days=score_bar_idx)

        result = compute_historical_forward_returns(
            pit_prices={"AAPL": bars},
            score_date=score_date,
            horizon_days=252,
        )

        assert "AAPL" in result
        assert abs(result["AAPL"] - (-0.50)) < 1e-10
