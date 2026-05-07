"""Score audit persistence service.

Bridges the engine's `ScoreAuditTrace` dataclass to the api's `score_components`
and `scoring_run_manifest` tables.

Design spec: docs/superpowers/specs/2026-05-02-component-subscore-logging-design.md.

Failure-mode contract:
  - persist_audit_trace MAY raise. The worker is expected to wrap calls in
    asyncio.shield + try/except so a DB hiccup never blocks the scoring chain.
  - persist_run_manifest_batch MUST be atomic — orchestrate_ingest writes the
    full run's manifest before any ARQ dispatch. Partial writes would create
    a silent gap (B-MANIFEST in the design spec).

Dialect dispatch:
  - PostgreSQL → postgresql.insert(...).on_conflict_do_nothing(...)
  - SQLite     → sqlite.insert(...).on_conflict_do_nothing(...)  (3.24+)
  Pattern matches services/price_ingestion.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from margin_engine.scoring.audit_trace import (
    ComponentEntry,
    ScoreAuditTrace,
    _NullTrace,
)

from margin_api.db.models import ScoreComponent, ScoringRunManifest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Trace persistence
# ---------------------------------------------------------------------------


def _entry_to_row_values(
    trace: ScoreAuditTrace, entry: ComponentEntry, computed_at: datetime
) -> dict:
    """Project one ComponentEntry into a score_components INSERT row."""
    return {
        "asset_id": trace.asset_id,
        "ticker": trace.ticker,
        "run_id": str(trace.run_id),
        "scoring_version": trace.scoring_version,
        "component_type": entry.component_type,
        "component_name": entry.component_name,
        "value": entry.value,
        "passed": entry.passed,
        "threshold": entry.threshold,
        "observed": entry.observed,
        "metadata_json": entry.metadata or {},
        "computed_at": computed_at,
    }


async def persist_audit_trace(
    session: AsyncSession,
    trace: ScoreAuditTrace | _NullTrace,
) -> int:
    """Bulk-insert a `ScoreAuditTrace`'s entries into `score_components`.

    Returns the number of entries the trace contained (target row count).
    Re-runs of the same `(asset_id, run_id, scoring_version, component_type,
    component_name)` are silently skipped via ON CONFLICT DO NOTHING.

    The caller is responsible for `await session.commit()` — this function
    only stages the INSERT in the session.

    `_NullTrace` short-circuits before touching the DB.
    """
    # Null-object short-circuit — engine call sites use NULL_TRACE by default.
    if isinstance(trace, _NullTrace):
        return 0

    if not trace.entries:
        return 0

    computed_at = datetime.now(UTC)
    values = [_entry_to_row_values(trace, entry, computed_at) for entry in trace.entries]

    dialect = session.bind.dialect.name if session.bind else "unknown"

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        stmt = (
            insert(ScoreComponent)
            .values(values)
            .on_conflict_do_nothing(constraint="uq_score_components_identity")
        )
        await session.execute(stmt)
    else:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        stmt = (
            sqlite_insert(ScoreComponent)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[
                    "asset_id",
                    "run_id",
                    "scoring_version",
                    "component_type",
                    "component_name",
                ]
            )
        )
        await session.execute(stmt)

    return len(values)


# ---------------------------------------------------------------------------
# Run manifest persistence (batch — atomic per orchestrate_ingest run)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """One (run_id, asset_id, scoring_version) tuple for the manifest batch.

    `run_kind` defaults to 'orchestrate_ingest' so reconciliation cron picks
    the row up. CLI re-runs and manual triggers should pass 'cli_rerun' or
    'manual' to opt out of coverage alerting.
    """

    run_id: str
    asset_id: int
    ticker: str
    scoring_version: str
    run_kind: str = "orchestrate_ingest"


async def persist_run_manifest_batch(
    session: AsyncSession,
    entries: list[ManifestEntry],
) -> int:
    """Atomic batch write — used by orchestrate_ingest BEFORE ARQ dispatch.

    Critical contract (B-MANIFEST in design spec): if ANY row fails, NO rows
    persist. orchestrate_ingest must only dispatch jobs once this returns
    successfully. Otherwise a partial-batch crash silently hides missing
    tickers (50/50 = 100% coverage looks fine while 50 tickers are missing).

    ON CONFLICT DO NOTHING on the unique constraint
    `(run_id, asset_id, scoring_version)` makes re-running orchestrate_ingest
    with the same run_id a no-op rather than an error — defends against the
    "ARQ retried orchestrate_ingest itself" edge case.

    Caller is responsible for `await session.commit()`.
    """
    if not entries:
        return 0

    dispatched_at = datetime.now(UTC)
    values = [
        {
            "run_id": e.run_id,
            "asset_id": e.asset_id,
            "ticker": e.ticker,
            "scoring_version": e.scoring_version,
            "dispatched_at": dispatched_at,
            "run_kind": e.run_kind,
        }
        for e in entries
    ]

    dialect = session.bind.dialect.name if session.bind else "unknown"

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        stmt = (
            insert(ScoringRunManifest)
            .values(values)
            .on_conflict_do_nothing(constraint="uq_scoring_run_manifest_identity")
        )
        await session.execute(stmt)
    else:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        stmt = (
            sqlite_insert(ScoringRunManifest)
            .values(values)
            .on_conflict_do_nothing(index_elements=["run_id", "asset_id", "scoring_version"])
        )
        await session.execute(stmt)

    return len(values)
