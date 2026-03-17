"""Historical frequency rarity scoring.

Computes how often a given factor signature has appeared historically.
Returns 50 (neutral) until >= 4 quarters of data accumulate.
Uses exponential decay (half-life 20 quarters) to weight recent history.
"""

from __future__ import annotations

import math

_MIN_QUARTERS = 4
_HALF_LIFE = 20


def compute_historical_frequency(
    current_signature: str,
    historical_snapshots: list[dict],
    lookback_quarters: int = 40,
) -> float:
    """Compute historical rarity score (0-100).

    Higher score = rarer (never seen = 100, always seen = 0).
    Returns 50.0 if fewer than _MIN_QUARTERS of history exist.
    """
    if len(historical_snapshots) < _MIN_QUARTERS:
        return 50.0

    snapshots = historical_snapshots[-lookback_quarters:]
    total_snapshots = len(snapshots)
    decay_rate = math.log(2) / _HALF_LIFE
    weighted_matches = 0.0
    total_weight = 0.0

    for i, snap in enumerate(snapshots):
        quarters_ago = total_snapshots - 1 - i
        weight = math.exp(-decay_rate * quarters_ago)
        total_weight += weight
        if snap["signature"] == current_signature:
            weighted_matches += weight

    if total_weight == 0:
        return 50.0

    frequency = weighted_matches / total_weight
    rarity_score = (1.0 - frequency) * 100
    return round(min(max(rarity_score, 0.0), 100.0), 2)
