"""Temporal quality momentum — rate of change in fundamental quality.

Compares current pillar percentiles vs trailing quarters.
Returns 0-100 (>50 = improving, 50 = stable, <50 = deteriorating).
"""

from __future__ import annotations

import statistics


def compute_quality_momentum(
    current_pillars: dict[str, float],
    historical_pillars: list[dict[str, float]],
) -> float:
    """Compute quality momentum score (0-100)."""
    if len(historical_pillars) < 2:
        return 50.0

    def _avg(pillars: dict[str, float]) -> float:
        vals = list(pillars.values())
        return statistics.mean(vals) if vals else 0.0

    current_avg = _avg(current_pillars)
    series = [_avg(h) for h in historical_pillars] + [current_avg]
    deltas = [series[i] - series[i - 1] for i in range(1, len(series))]

    if not deltas:
        return 50.0

    avg_delta = statistics.mean(deltas)

    consecutive_improving = 0
    for d in reversed(deltas):
        if d > 0:
            consecutive_improving += 1
        else:
            break

    delta_contribution = min(max(avg_delta * 4, -30), 30)
    consecutive_bonus = min(consecutive_improving * 5, 20) if consecutive_improving >= 2 else 0

    score = 50.0 + delta_contribution + consecutive_bonus
    return round(min(max(score, 0.0), 100.0), 2)
