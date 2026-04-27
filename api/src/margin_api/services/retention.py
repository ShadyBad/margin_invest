"""Database retention policies — purge old operational rows.

Each policy is a pure async function that takes an AsyncSession and a cutoff
in days, returns the number of rows deleted, and does NOT commit. The caller
(the purge_stale_data worker) is responsible for the transaction boundary.

This split exists so that policies can be tested independently and so that
a transient failure in one policy aborts the whole sweep cleanly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import (
    FilingText,
    JobRun,
    RiskFactorAnalysis,
    WebhookDelivery,
)


async def purge_job_runs(session: AsyncSession, days: int = 30) -> int:
    """Delete JobRun rows older than `days`. Returns rowcount."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(delete(JobRun).where(JobRun.started_at < cutoff))
    return result.rowcount or 0


async def purge_webhook_deliveries(session: AsyncSession, days: int = 30) -> int:
    """Delete WebhookDelivery rows with status='delivered' older than `days`.

    Retains 'pending', 'dead_letter', and any other non-success rows indefinitely
    so postmortem and replay tooling can inspect them.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(
        delete(WebhookDelivery).where(
            WebhookDelivery.delivered_at < cutoff,
            WebhookDelivery.status == "delivered",
        )
    )
    return result.rowcount or 0


async def blank_diffed_risk_factor_text(session: AsyncSession) -> int:
    """Null out `risk_factors_text` for FilingTexts that have a RiskFactorAnalysis row.

    Once a filing has been diffed and the analysis committed, the raw text is
    redundant — the analysis output captures the material changes. The hash
    (`raw_html_hash`) is preserved so re-diffing can detect upstream changes.

    No age cutoff: this is the only retention policy that runs purely on
    completion state, not time. Idempotent via `is_not(None)` predicate.
    """
    diffed_ids = select(RiskFactorAnalysis.filing_text_id).distinct().scalar_subquery()
    result = await session.execute(
        update(FilingText)
        .where(
            FilingText.id.in_(diffed_ids),
            FilingText.risk_factors_text.is_not(None),
        )
        .values(risk_factors_text=None)
    )
    return result.rowcount or 0
