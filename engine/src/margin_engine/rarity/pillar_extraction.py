"""Extract meaningful pillar percentiles from a CompositeScore.

Track A (compounder): quality, value, momentum, growth (4 pillars)
Track B (mispricing): quality, value, catalyst (3 pillars — dummy momentum excluded)
"""

from __future__ import annotations

from margin_engine.models.scoring import CompositeScore


def extract_pillar_percentiles(composite: CompositeScore) -> dict[str, float]:
    """Return {pillar_name: average_percentile} for meaningful pillars only."""
    pillars: dict[str, float] = {}

    pillars["quality"] = composite.quality.average_percentile
    pillars["value"] = composite.value.average_percentile

    if composite.momentum.sub_scores:
        pillars["momentum"] = composite.momentum.average_percentile

    if composite.growth is not None:
        pillars["growth"] = composite.growth.average_percentile

    if not composite.momentum.sub_scores and composite.catalyst is not None:
        pillars["catalyst"] = composite.catalyst.average_percentile

    return pillars
