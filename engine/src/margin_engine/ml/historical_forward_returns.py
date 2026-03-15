"""Compute historical forward returns from PIT price data for ML training labels."""

from __future__ import annotations

from datetime import date


def _to_date(val: object) -> date:
    """Parse a date from an ISO date string or full ISO timestamp."""
    s = str(val)[:10]  # Take YYYY-MM-DD prefix
    return date.fromisoformat(s)


def _find_closest_bar_index(bars: list[dict], target: date) -> int:
    """Return the index of the bar whose date is closest to target."""
    best_idx = 0
    best_delta = abs((_to_date(bars[0]["date"]) - target).days)

    for i in range(1, len(bars)):
        delta = abs((_to_date(bars[i]["date"]) - target).days)
        if delta < best_delta:
            best_delta = delta
            best_idx = i

    return best_idx


def compute_historical_forward_returns(
    pit_prices: dict[str, list[dict]],
    score_date: date,
    horizon_days: int = 252,
    max_date_gap: int = 5,
) -> dict[str, float]:
    """Compute forward returns from PIT price data for a given score date.

    For each ticker in pit_prices:
    1. Find the price bar closest to score_date.
    2. If the closest bar is more than max_date_gap calendar days away, exclude ticker.
    3. Look ahead horizon_days bars (trading days).
    4. If not enough future bars exist, exclude ticker.
    5. Compute return: (future_price / score_price) - 1.0.
    6. If score_price <= 0, exclude ticker.

    Args:
        pit_prices: Dict mapping ticker -> list of price bar dicts. Each bar must
            have 'date' (ISO string) and 'close' (float) keys.
        score_date: The date at which scores were computed.
        horizon_days: Number of trading-day bars to look ahead. Defaults to 252.
        max_date_gap: Maximum allowed calendar-day gap between score_date and the
            closest available bar. Tickers with a larger gap are excluded.

    Returns:
        Dict mapping ticker -> forward return as a decimal (e.g. 0.20 for 20%).
        Tickers without sufficient data are excluded entirely — never defaulted to 0.0.
    """
    results: dict[str, float] = {}

    for ticker, bars in pit_prices.items():
        if not bars:
            continue

        # Find bar closest to score_date
        score_idx = _find_closest_bar_index(bars, score_date)

        # Check calendar-day gap
        bar_date = _to_date(bars[score_idx]["date"])
        gap = abs((bar_date - score_date).days)
        if gap > max_date_gap:
            continue

        # Check that we have enough future bars
        future_idx = score_idx + horizon_days
        if future_idx >= len(bars):
            continue

        score_price = float(bars[score_idx]["close"])
        if score_price <= 0.0:
            continue

        future_price = float(bars[future_idx]["close"])
        results[ticker] = (future_price / score_price) - 1.0

    return results
