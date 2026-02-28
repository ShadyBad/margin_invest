"""Data Quality Gate — caps conviction based on data completeness.

Rules:
- data_coverage >= 0.8: no restriction
- data_coverage 0.6-0.8: cap at MEDIUM
- data_coverage < 0.6: force NONE
"""

from __future__ import annotations

from margin_engine.models.scoring import CompositeTier

_FULL_THRESHOLD = 0.80
_MIN_THRESHOLD = 0.60


def apply_data_quality_gate(
    conviction: CompositeTier,
    data_coverage: float,
) -> CompositeTier:
    """Apply data quality gate to conviction level."""
    if data_coverage < _MIN_THRESHOLD:
        return CompositeTier.NONE

    if data_coverage < _FULL_THRESHOLD:
        if conviction in (CompositeTier.EXCEPTIONAL, CompositeTier.HIGH):
            return CompositeTier.MEDIUM
        return conviction

    return conviction
