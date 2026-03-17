"""Cross-factor convergence scoring.

Measures how aligned pillar percentiles are at HIGH levels.
Convergence on mediocrity (below 60th percentile) scores zero.
"""

from __future__ import annotations


def compute_convergence(pillar_percentiles: list[float]) -> float:
    """Score 0-100 measuring pillar alignment at high levels."""
    if not pillar_percentiles:
        return 0.0

    floor = min(pillar_percentiles)
    ceiling = max(pillar_percentiles)
    ratio = floor / ceiling if ceiling > 0 else 0.0
    floor_penalty = max(0.0, (floor - 60) / 40)
    convergence = ratio * floor_penalty * 100
    return round(convergence, 2)
