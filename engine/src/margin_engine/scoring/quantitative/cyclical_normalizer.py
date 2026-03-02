"""Cyclical normalization using 7-year median for valuation factors.

Cyclical businesses at peak/trough get systematically mispriced when
using trailing 12-month data. The 7-year median captures a full
business cycle, producing more stable valuation multiples.

Applicable sectors: Energy, Materials, Industrials, Consumer Discretionary.
"""

from __future__ import annotations

import statistics

_MIN_HISTORY = 3  # Minimum periods for meaningful median
_DEFAULT_LOOKBACK = 7  # 7-year median for full business cycle


def normalize_metric(
    current_value: float,
    historical_values: list[float],
    is_cyclical: bool,
    lookback: int = _DEFAULT_LOOKBACK,
) -> tuple[float, str]:
    """Normalize a metric for cyclical companies using lookback-year median.

    For cyclical companies, replaces current-period values with the median
    over the lookback window. For non-cyclical companies, returns current value.

    Args:
        current_value: The current-period metric value
        historical_values: Multi-year metric values (oldest first)
        is_cyclical: Whether the company is in a cyclical sector
        lookback: Number of years for median window (default 7)

    Returns:
        (normalized_value, detail_string)
    """
    if not is_cyclical or len(historical_values) < _MIN_HISTORY:
        return current_value, f"using_current={current_value:.4f}"

    window = (
        historical_values[-lookback:] if len(historical_values) >= lookback else historical_values
    )
    # Filter out zero/negative values for valuation metrics
    valid = [v for v in window if v > 0]
    if len(valid) < _MIN_HISTORY:
        return current_value, f"insufficient_valid_history={len(valid)}"

    median_val = statistics.median(valid)
    return median_val, (
        f"7yr_median={median_val:.4f}, current={current_value:.4f}, periods_used={len(valid)}"
    )
