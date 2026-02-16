"""Ingestion service — universe-aware data pipeline orchestration."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset

_PERMANENT_KEYWORDS = {"not found", "delisted", "merged", "acquired", "no longer listed"}
_QUARANTINE_THRESHOLD = 3
_PERMANENT_THRESHOLD = 6


def classify_error(error: Exception) -> str:
    """Classify an ingestion error as transient, data_unavailable, or permanent."""
    msg = str(error).lower()

    if any(kw in msg for kw in _PERMANENT_KEYWORDS):
        return "permanent"

    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return "transient"

    if "429" in msg or "rate limit" in msg or "too many requests" in msg:
        return "transient"

    if "503" in msg or "502" in msg or "500" in msg:
        return "transient"

    return "data_unavailable"


def should_ingest_ticker(
    ingestion_status: str,
    consecutive_failures: int,
    last_retry_at: datetime | None,
) -> bool:
    """Determine whether a ticker should be ingested in the current run."""
    if ingestion_status == "permanently_skipped":
        return False

    if ingestion_status == "quarantined":
        if last_retry_at is None:
            return True
        return datetime.now(UTC) - last_retry_at > timedelta(days=7)

    return True


async def update_failure_status(
    session: AsyncSession,
    asset: Asset,
    error_type: str,
    error_message: str | None,
) -> None:
    """Update asset failure tracking based on error classification."""
    if error_type == "success":
        asset.consecutive_failures = 0
        asset.ingestion_status = "active"
        asset.last_failure_reason = None
        asset.quarantined_at = None
        asset.last_retry_at = None
        await session.commit()
        return

    if error_type == "transient":
        asset.last_failure_reason = error_message
        await session.commit()
        return

    if error_type == "permanent":
        asset.ingestion_status = "permanently_skipped"
        asset.last_failure_reason = error_message
        await session.commit()
        return

    # data_unavailable
    asset.consecutive_failures += 1
    asset.last_failure_reason = error_message

    if asset.consecutive_failures >= _PERMANENT_THRESHOLD:
        asset.ingestion_status = "permanently_skipped"
    elif asset.consecutive_failures >= _QUARANTINE_THRESHOLD:
        asset.ingestion_status = "quarantined"
        if asset.quarantined_at is None:
            asset.quarantined_at = datetime.now(UTC)
        asset.last_retry_at = datetime.now(UTC)

    await session.commit()
