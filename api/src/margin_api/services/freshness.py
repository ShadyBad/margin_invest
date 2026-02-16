"""Data freshness tier computation."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

FRESH_THRESHOLD = timedelta(hours=18)
STALE_THRESHOLD = timedelta(days=3)


def compute_freshness(scored_at: datetime | None) -> str:
    """Compute freshness tier from scored_at timestamp.

    Returns: "fresh" | "stale" | "expired"
    """
    if scored_at is None:
        return "expired"

    age = datetime.now(UTC) - scored_at

    if age < FRESH_THRESHOLD:
        return "fresh"
    if age < STALE_THRESHOLD:
        return "stale"
    return "expired"
