"""Price Momentum (12-1 month) factor (Jegadeesh & Titman).

Measures the trailing 12-month return excluding the most recent month.
The last month is excluded because short-term returns exhibit mean
reversion rather than momentum.

Academic reference: Jegadeesh & Titman (1993), "Returns to Buying Winners
and Selling Losers: Implications for Stock Market Efficiency."

Formula: momentum = (price at T-1 month / price at T-12 months) - 1
"""

from __future__ import annotations

import datetime

from margin_engine.models.financial import PriceBar
from margin_engine.models.scoring import FactorScore

# Minimum span in calendar days to consider the data as having 12 months of history.
# ~10 months of data is the floor to allow some tolerance.
_MIN_HISTORY_DAYS = 300

# Target lookback offsets in calendar days.
_T1_OFFSET_DAYS = 30  # ~1 month ago
_T12_OFFSET_DAYS = 365  # ~12 months ago


def price_momentum(price_bars: list[PriceBar]) -> FactorScore:
    """Compute the Jegadeesh & Titman 12-1 month price momentum.

    Returns a FactorScore with:
    - raw_value: (close_T-1mo / close_T-12mo) - 1, or 0.0 for edge cases
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer in Phase 6)
    - name: "price_momentum"
    """
    if len(price_bars) < 2:
        return FactorScore(
            name="price_momentum",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"Insufficient data: {len(price_bars)} bar(s) provided",
        )

    # 1. Sort by date ascending.
    sorted_bars = sorted(price_bars, key=lambda b: b.date)

    # 2. Parse all dates once.
    dates = [datetime.date.fromisoformat(b.date) for b in sorted_bars]

    most_recent_date = dates[-1]
    earliest_date = dates[0]
    span = (most_recent_date - earliest_date).days

    if span < _MIN_HISTORY_DAYS:
        return FactorScore(
            name="price_momentum",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"Insufficient history: span={span} days"
                f" (need >= {_MIN_HISTORY_DAYS})"
            ),
        )

    # 3. Find the bar closest to T-1 month (~30 calendar days ago).
    target_t1 = most_recent_date - datetime.timedelta(days=_T1_OFFSET_DAYS)
    idx_t1 = _closest_index(dates, target_t1)
    price_t1 = float(sorted_bars[idx_t1].close)

    # 4. Find the bar closest to T-12 months (~365 calendar days ago).
    target_t12 = most_recent_date - datetime.timedelta(days=_T12_OFFSET_DAYS)
    idx_t12 = _closest_index(dates, target_t12)
    price_t12 = float(sorted_bars[idx_t12].close)

    # 5. Guard against division by zero.
    if price_t12 == 0.0:
        return FactorScore(
            name="price_momentum",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"Zero price at T-12 ({sorted_bars[idx_t12].date}):"
                f" price_t12={price_t12}"
            ),
        )

    # 6. Compute momentum.
    momentum = (price_t1 / price_t12) - 1.0

    return FactorScore(
        name="price_momentum",
        raw_value=momentum,
        percentile_rank=0.0,
        detail=(
            f"price_t1={price_t1:.2f} ({sorted_bars[idx_t1].date})"
            f" / price_t12={price_t12:.2f} ({sorted_bars[idx_t12].date})"
            f" - 1 = {momentum:.4f}"
        ),
    )


def _closest_index(dates: list[datetime.date], target: datetime.date) -> int:
    """Return the index of the date in *dates* closest to *target*.

    *dates* must be sorted ascending.
    """
    best_idx = 0
    best_diff = abs((dates[0] - target).days)
    for i, d in enumerate(dates):
        diff = abs((d - target).days)
        if diff < best_diff:
            best_diff = diff
            best_idx = i
    return best_idx
