"""Circuit breaker service for auto-escalating on-the-loop actions to in-the-loop.

Provides threshold-based checks for score drift, ingestion failure rates,
and ML model regression. Each check returns a CircuitBreakerResult indicating
whether the circuit breaker was triggered.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from margin_api.db.models import V4Score
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class CircuitBreakerResult:
    """Result of a circuit breaker check."""

    triggered: bool
    drift_pct: float
    detail: str


async def check_score_drift(
    session: AsyncSession,
    scored_at: datetime,
    threshold_pct: float = 0.30,
) -> CircuitBreakerResult:
    """Check whether conviction drift across the scoring universe exceeds a threshold.

    Queries unpublished V4Score rows at ``scored_at``, then for each finds the
    latest published V4Score for the same asset_id. Counts how many have a
    different ``conviction`` value.

    Args:
        session: Async database session.
        scored_at: Timestamp of the new (unpublished) scoring run.
        threshold_pct: Fraction of conviction changes that triggers the breaker.

    Returns:
        CircuitBreakerResult with triggered=True when drift_pct > threshold_pct.
    """
    # Fetch all unpublished scores at the given scored_at timestamp.
    new_scores_result = await session.execute(
        select(V4Score).where(
            and_(
                V4Score.scored_at == scored_at,
                V4Score.published == False,  # noqa: E712
            )
        )
    )
    new_scores = list(new_scores_result.scalars().all())

    if not new_scores:
        return CircuitBreakerResult(
            triggered=False,
            drift_pct=0.0,
            detail="No new scores found at the given scored_at timestamp.",
        )

    conviction_changes = 0
    total = len(new_scores)

    for new_score in new_scores:
        # Find the latest published score for the same asset.
        prev_result = await session.execute(
            select(V4Score)
            .where(
                and_(
                    V4Score.asset_id == new_score.asset_id,
                    V4Score.published == True,  # noqa: E712
                )
            )
            .order_by(V4Score.scored_at.desc())
            .limit(1)
        )
        prev_score = prev_result.scalar_one_or_none()

        if prev_score is not None and prev_score.conviction != new_score.conviction:
            conviction_changes += 1

    drift_pct = conviction_changes / total if total > 0 else 0.0
    triggered = drift_pct > threshold_pct

    return CircuitBreakerResult(
        triggered=triggered,
        drift_pct=drift_pct,
        detail=(
            f"{conviction_changes}/{total} scores changed conviction "
            f"({drift_pct:.1%} drift, threshold {threshold_pct:.1%})."
        ),
    )


def check_ingestion_failure_rate(
    failed_count: int,
    total_count: int,
    threshold_pct: float = 0.20,
) -> CircuitBreakerResult:
    """Check whether the ingestion failure rate exceeds a threshold.

    Args:
        failed_count: Number of failed ingestion attempts.
        total_count: Total number of ingestion attempts.
        threshold_pct: Fraction of failures that triggers the breaker.

    Returns:
        CircuitBreakerResult with triggered=True when rate > threshold_pct.
    """
    if total_count == 0:
        return CircuitBreakerResult(
            triggered=False,
            drift_pct=0.0,
            detail="No ingestion attempts to evaluate.",
        )

    rate = failed_count / total_count
    triggered = rate > threshold_pct

    return CircuitBreakerResult(
        triggered=triggered,
        drift_pct=rate,
        detail=(
            f"{failed_count}/{total_count} ingestion failures "
            f"({rate:.1%} rate, threshold {threshold_pct:.1%})."
        ),
    )


def check_ml_regression(
    new_rank_ic: float | None,
    active_rank_ic: float | None,
    threshold_pct: float = 0.50,
) -> CircuitBreakerResult:
    """Check whether a new ML model shows significant regression vs the active model.

    Args:
        new_rank_ic: Rank IC of the candidate model.
        active_rank_ic: Rank IC of the currently active model.
        threshold_pct: Fraction of IC regression that triggers the breaker.

    Returns:
        CircuitBreakerResult with triggered=True when regression_pct > threshold_pct.
    """
    if new_rank_ic is None or active_rank_ic is None or active_rank_ic == 0:
        return CircuitBreakerResult(
            triggered=False,
            drift_pct=0.0,
            detail="Insufficient data to evaluate ML regression (None or zero IC).",
        )

    regression_pct = (active_rank_ic - new_rank_ic) / active_rank_ic
    triggered = regression_pct > threshold_pct

    return CircuitBreakerResult(
        triggered=triggered,
        drift_pct=regression_pct,
        detail=(
            f"ML rank IC regression: {active_rank_ic:.4f} -> {new_rank_ic:.4f} "
            f"({regression_pct:.1%} change, threshold {threshold_pct:.1%})."
        ),
    )
