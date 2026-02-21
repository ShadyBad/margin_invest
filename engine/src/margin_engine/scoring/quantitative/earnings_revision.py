"""Earnings Revision Momentum — consensus estimate change signal.

Measures the direction and magnitude of FY1/FY2 EPS estimate revisions
over the past 90 days. Positive revisions = upward momentum.

NOTE: Requires analyst consensus estimates data. Currently a stub
that accepts pre-computed estimate values.
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore


def earnings_revision_momentum(
    fy1_estimate_current: float | None = None,
    fy1_estimate_90d_ago: float | None = None,
    fy2_estimate_current: float | None = None,
    fy2_estimate_90d_ago: float | None = None,
) -> FactorScore:
    """Compute earnings revision momentum from FY1/FY2 estimate changes.

    Returns weighted average of FY1 (60%) and FY2 (40%) revision rates.
    """
    if fy1_estimate_current is None or fy1_estimate_90d_ago is None:
        return FactorScore(
            name="earnings_revision",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="No estimates available",
        )

    revisions: list[tuple[float, float]] = []

    if fy1_estimate_90d_ago != 0:
        fy1_rev = (fy1_estimate_current - fy1_estimate_90d_ago) / abs(fy1_estimate_90d_ago)
        revisions.append((0.60, fy1_rev))

    if (
        fy2_estimate_current is not None
        and fy2_estimate_90d_ago is not None
        and fy2_estimate_90d_ago != 0
    ):
        fy2_rev = (fy2_estimate_current - fy2_estimate_90d_ago) / abs(fy2_estimate_90d_ago)
        revisions.append((0.40, fy2_rev))

    if not revisions:
        return FactorScore(
            name="earnings_revision",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Zero base estimates",
        )

    total_weight = sum(w for w, _ in revisions)
    blended = sum(w * r / total_weight for w, r in revisions)

    return FactorScore(
        name="earnings_revision",
        raw_value=blended,
        percentile_rank=0.0,
        detail=f"blended_revision={blended:.4f}, components={len(revisions)}",
    )
