"""Smart money convergence scoring.

Combines institutional accumulation and insider cluster buying signals.
Uses FactorScore.metadata for intermediate signals when available.
"""

from __future__ import annotations


def compute_smart_money_convergence(
    accumulation_percentile: float,
    insider_cluster_percentile: float,
    accumulation_metadata: dict | None,
    insider_metadata: dict | None,
) -> float:
    """Compute smart money convergence score (0-100).

    Tiered scoring:
    - Institutional accumulation alone: max 60
    - + insider buying: max 80
    - + 3+ quality institutions: max 90
    - + 2+ consecutive quarters: max 100
    """
    base = accumulation_percentile * 0.6 + insider_cluster_percentile * 0.4
    score = base * 0.6

    insider_active = False
    if insider_metadata is not None:
        insider_active = insider_metadata.get("cluster_buy_detected", False)
    elif insider_cluster_percentile >= 70:
        insider_active = True

    if insider_active:
        score += 20 * (min(insider_cluster_percentile, 100) / 100)

    if accumulation_metadata is not None:
        n_quality = accumulation_metadata.get("n_quality_institutions_adding", 0)
        if n_quality >= 3:
            score += 10.0
        elif n_quality >= 1:
            score += 5.0

    if accumulation_metadata is not None:
        n_consecutive = accumulation_metadata.get("n_consecutive_quarters_accumulated", 0)
        if n_consecutive >= 2:
            score += 10.0

    return round(min(max(score, 0.0), 100.0), 2)
