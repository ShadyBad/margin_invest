"""Database retention policies — purge old operational rows.

Each policy is a pure async function that takes an AsyncSession and a cutoff
in days, returns the number of rows deleted, and does NOT commit. The caller
(the purge_stale_data worker) is responsible for the transaction boundary.

This split exists so that policies can be tested independently and so that
a transient failure in one policy aborts the whole sweep cleanly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import JobRun, WebhookDelivery


async def purge_job_runs(session: AsyncSession, days: int = 30) -> int:
    """Delete JobRun rows older than `days`. Returns rowcount."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(delete(JobRun).where(JobRun.started_at < cutoff))
    return result.rowcount or 0


async def purge_webhook_deliveries(session: AsyncSession, days: int = 30) -> int:
    """Delete WebhookDelivery rows with status='success' older than `days`.

    Failed deliveries are retained indefinitely for postmortem.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(
        delete(WebhookDelivery).where(
            WebhookDelivery.delivered_at < cutoff,
            WebhookDelivery.status == "success",
        )
    )
    return result.rowcount or 0
