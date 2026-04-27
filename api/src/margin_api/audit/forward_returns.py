"""Part A: forward-return alpha measurement on legacy `scores` candidates.

Per spec §8.1, all returns use `pit_daily_prices.adj_close` (dividend-adjusted).
Missing endpoints are NEVER substituted with neighboring days.
"""

from __future__ import annotations

from datetime import date


def compute_total_return(
    prices: dict[date, float],
    start: date,
    end: date,
) -> float | None:
    """Compute total return between two dates.

    Args:
        prices: Dictionary mapping dates to adjusted closing prices.
        start: Start date for return calculation.
        end: End date for return calculation.

    Returns:
        Total return as a float (e.g., 0.10 for 10% return), or None if:
        - Either endpoint price is missing
        - Start price is zero (division by zero protection)
    """
    start_price = prices.get(start)
    end_price = prices.get(end)
    if start_price is None or end_price is None:
        return None
    if start_price == 0:
        return None
    return (end_price / start_price) - 1.0
