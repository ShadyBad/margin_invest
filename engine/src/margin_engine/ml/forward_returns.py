"""Compute real forward returns from price history for ML training labels."""

from __future__ import annotations

from datetime import date


def _find_scored_at_index(bars: list[dict], scored_at: str) -> int:
    """Find the bar index closest to the scored_at date.

    Args:
        bars: List of price bar dicts, each with a 'date' key (ISO format string).
        scored_at: Target date as ISO format string (YYYY-MM-DD).

    Returns:
        Index of the bar whose date is closest to scored_at.
    """
    target = date.fromisoformat(scored_at)
    best_idx = 0
    best_delta = abs((date.fromisoformat(bars[0]["date"]) - target).days)

    for i in range(1, len(bars)):
        delta = abs((date.fromisoformat(bars[i]["date"]) - target).days)
        if delta < best_delta:
            best_delta = delta
            best_idx = i

    return best_idx


def compute_forward_returns(
    scored_tickers: list[dict],
    price_data: dict[str, list[dict]],
    horizon_days: int = 252,
) -> dict[str, float]:
    """Compute forward returns for scored tickers.

    For each scored ticker, finds the price at scored_at date and the price
    horizon_days trading days later, then computes the return.

    Args:
        scored_tickers: List of dicts, each with 'ticker' and 'scored_at' keys.
            scored_at is an ISO date string (YYYY-MM-DD).
        price_data: Dict mapping ticker -> list of price bar dicts.
            Each bar must have 'close' (float) and 'date' (ISO string) keys.
        horizon_days: Number of trading days for the forward return window.
            Defaults to 252 (~12 months).

    Returns:
        Dict mapping ticker -> forward return as a decimal (e.g. 0.20 for 20%).
        Tickers without sufficient future data or not in price_data are excluded.
    """
    results: dict[str, float] = {}

    for entry in scored_tickers:
        ticker = entry["ticker"]
        scored_at = entry["scored_at"]

        # Skip tickers not in price data
        if ticker not in price_data:
            continue

        bars = price_data[ticker]

        if len(bars) == 0:
            continue

        scored_idx = _find_scored_at_index(bars, scored_at)
        future_idx = scored_idx + horizon_days

        # Check if we have enough future data
        if future_idx >= len(bars):
            continue

        score_date_price = bars[scored_idx]["close"]
        future_price = bars[future_idx]["close"]

        # Avoid division by zero
        if score_date_price == 0:
            continue

        forward_return = (future_price / score_date_price) - 1.0
        results[ticker] = forward_return

    return results
