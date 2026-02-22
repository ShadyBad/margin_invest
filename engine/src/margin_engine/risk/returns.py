"""Shared return utilities for risk analytics."""

from __future__ import annotations

import math

import numpy as np

from margin_engine.models.financial import PriceBar


def returns_from_price_bars(
    price_data: dict[str, list[PriceBar]],
    window_days: int = 252,
) -> tuple[np.ndarray, list[str]]:
    """Convert price bar data to a (T, N) log-return matrix.

    Uses adj_close (fallback to close) for log returns: log(curr/prev).
    Only includes tickers with >= 10 bars after windowing.
    Missing dates are filled with 0.0.

    Args:
        price_data: Mapping of ticker -> list of PriceBar (sorted by date).
        window_days: Maximum number of trailing bars to use.

    Returns:
        Tuple of (returns_matrix with shape (T, N), sorted_ticker_list).
        Returns (empty 2D array, empty list) if no valid tickers.
    """
    min_bars = 10

    # Compute log returns per ticker, keyed by date
    returns_by_ticker: dict[str, dict[str, float]] = {}
    for ticker, bars in price_data.items():
        windowed = bars[-window_days:]
        if len(windowed) < min_bars:
            continue
        daily: dict[str, float] = {}
        for i in range(1, len(windowed)):
            prev_close = float(windowed[i - 1].adj_close or windowed[i - 1].close)
            curr_close = float(windowed[i].adj_close or windowed[i].close)
            if prev_close > 0 and curr_close > 0:
                daily[windowed[i].date] = math.log(curr_close / prev_close)
        returns_by_ticker[ticker] = daily

    if not returns_by_ticker:
        return np.empty((0, 0)), []

    # Sorted tickers for deterministic column ordering
    tickers = sorted(returns_by_ticker.keys())

    # Union of all dates across tickers
    all_dates: set[str] = set()
    for daily in returns_by_ticker.values():
        all_dates.update(daily.keys())
    sorted_dates = sorted(all_dates)

    t_obs = len(sorted_dates)
    n_assets = len(tickers)
    matrix = np.zeros((t_obs, n_assets), dtype=np.float64)

    for j, ticker in enumerate(tickers):
        daily = returns_by_ticker[ticker]
        for i, date in enumerate(sorted_dates):
            matrix[i, j] = daily.get(date, 0.0)

    return matrix, tickers
