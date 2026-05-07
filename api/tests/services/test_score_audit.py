"""Tests for the score audit persistence service.

The service flushes a `ScoreAuditTrace` (engine dataclass) into the
`score_components` table, plus tracks dispatched runs in `scoring_run_manifest`.

Design spec: docs/superpowers/specs/2026-05-02-component-subscore-logging-design.md.

Failure-mode contract: persist_audit_trace MAY raise. The worker is expected
to wrap the call so a DB hiccup never blocks the scoring chain.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, ScoreComponent, ScoringRunManifest
from margin_api.services.score_audit import (
    ManifestEntry,
    persist_audit_trace,
    persist_run_manifest_batch,
)
from margin_engine.scoring.audit_trace import (
    NULL_TRACE,
    ScoreAuditTrace,
    _NullTrace,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeded_asset(session_factory):
    """Insert a single Asset and return its id — FK target for audit rows."""
    async with session_factory() as session:
        asset = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(asset)
        await session.flush()
        await session.commit()
        return asset.id


def _make_trace(asset_id: int, ticker: str = "AAPL") -> ScoreAuditTrace:
    return ScoreAuditTrace(
        run_id=uuid4(),
        asset_id=asset_id,
        ticker=ticker,
        scoring_version="v3",
    )


# ---------------------------------------------------------------------------
# persist_audit_trace — bulk insert
# ---------------------------------------------------------------------------


class TestPersistAuditTrace:
    @pytest.mark.asyncio
    async def test_inserts_all_entries(self, session_factory, seeded_asset):
        trace = _make_trace(seeded_asset)
        trace.record_factor("quality", 87.4, sector_neutral_rank=92.1)
        trace.record_gate("filter", "beneish_m_score", passed=True, threshold=-1.78, observed=-2.31)
        trace.record_gate("cascade", "gate_2", passed=True, threshold=0.15, observed=0.21)
        trace.record_composite("composite_score", 72.5)

        async with session_factory() as session:
            inserted = await persist_audit_trace(session, trace)
            await session.commit()

            assert inserted == 4

            rows = (await session.execute(select(ScoreComponent))).scalars().all()
            names = {r.component_name for r in rows}
            assert names == {"quality", "beneish_m_score", "gate_2", "composite_score"}

    @pytest.mark.asyncio
    async def test_filter_reject_path_persists(self, session_factory, seeded_asset):
        """Filter-rejected ticker — trace contains only the failing filter row.

        Critical contract: this is what makes the audit valuable. Without it,
        we only know about survivors, not what got eliminated and why.
        """
        trace = _make_trace(seeded_asset, ticker="ENRN")
        trace.record_gate("filter", "beneish_m_score", passed=False, threshold=-1.78, observed=0.5)

        async with session_factory() as session:
            inserted = await persist_audit_trace(session, trace)
            await session.commit()

            assert inserted == 1
            row = (await session.execute(select(ScoreComponent))).scalar_one()
            assert row.passed is False
            assert row.observed == 0.5

    @pytest.mark.asyncio
    async def test_null_trace_short_circuits(self, session_factory):
        """_NullTrace bypasses the DB entirely — no INSERT issued, no rows produced."""
        async with session_factory() as session:
            inserted = await persist_audit_trace(session, NULL_TRACE)  # type: ignore[arg-type]
            await session.commit()
            assert inserted == 0

            rows = (await session.execute(select(ScoreComponent))).scalars().all()
            assert rows == []

    @pytest.mark.asyncio
    async def test_null_trace_instance_short_circuits(self, session_factory):
        """A fresh _NullTrace() instance also short-circuits (not just the singleton)."""
        async with session_factory() as session:
            inserted = await persist_audit_trace(session, _NullTrace())  # type: ignore[arg-type]
            assert inserted == 0

    @pytest.mark.asyncio
    async def test_empty_trace_returns_zero(self, session_factory, seeded_asset):
        """Trace with no recorded entries is a valid no-op."""
        trace = _make_trace(seeded_asset)
        async with session_factory() as session:
            inserted = await persist_audit_trace(session, trace)
            assert inserted == 0

    @pytest.mark.asyncio
    async def test_idempotent_via_unique_constraint(self, session_factory, seeded_asset):
        """Re-running same trace must not error or duplicate rows.

        The unique constraint (asset_id, run_id, scoring_version, component_type,
        component_name) drives ON CONFLICT DO NOTHING dispatch.
        """
        trace = _make_trace(seeded_asset)
        trace.record_factor("quality", 87.4)
        trace.record_factor("value", 65.0)

        async with session_factory() as session:
            first = await persist_audit_trace(session, trace)
            await session.commit()
            second = await persist_audit_trace(session, trace)
            await session.commit()

            assert first == 2
            # ON CONFLICT DO NOTHING — second call inserts 0 (or returns the
            # rowcount the dialect reports for skipped rows). Either way: total
            # row count in DB stays at 2.
            assert second in (0, 2)

            rows = (await session.execute(select(ScoreComponent))).scalars().all()
            assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_metadata_serializes_correctly(self, session_factory, seeded_asset):
        trace = _make_trace(seeded_asset)
        trace.record_gate(
            "conviction",
            "roic_trajectory_override",
            passed=True,
            tier="compounder",
            override_fired=True,
            quarters_window=3,
        )

        async with session_factory() as session:
            await persist_audit_trace(session, trace)
            await session.commit()

            row = (await session.execute(select(ScoreComponent))).scalar_one()
            assert row.metadata_json["override_fired"] is True
            assert row.metadata_json["quarters_window"] == 3
            assert row.metadata_json["tier"] == "compounder"

    @pytest.mark.asyncio
    async def test_run_id_stored_as_string(self, session_factory, seeded_asset):
        """trace.run_id is UUID; row.run_id is String(36) for SQLite compat."""
        trace = _make_trace(seeded_asset)
        trace.record_factor("quality", 87.4)

        async with session_factory() as session:
            await persist_audit_trace(session, trace)
            await session.commit()

            row = (await session.execute(select(ScoreComponent))).scalar_one()
            # Stored as canonical string form
            assert row.run_id == str(trace.run_id)
            # And it round-trips back to a UUID
            assert UUID(row.run_id) == trace.run_id


# ---------------------------------------------------------------------------
# persist_run_manifest_batch — atomic batch write before any dispatch
# ---------------------------------------------------------------------------


class TestPersistRunManifestBatch:
    @pytest.mark.asyncio
    async def test_batch_insert_writes_all_rows(self, session_factory, seeded_asset):
        run_id = str(uuid4())
        entries = [
            ManifestEntry(
                run_id=run_id,
                asset_id=seeded_asset,
                ticker="AAPL",
                scoring_version="v3",
            ),
            ManifestEntry(
                run_id=run_id,
                asset_id=seeded_asset,
                ticker="AAPL",
                scoring_version="v4",
            ),
        ]

        async with session_factory() as session:
            inserted = await persist_run_manifest_batch(session, entries)
            await session.commit()
            assert inserted == 2

            rows = (await session.execute(select(ScoringRunManifest))).scalars().all()
            assert len(rows) == 2
            assert {r.scoring_version for r in rows} == {"v3", "v4"}
            assert all(r.run_kind == "orchestrate_ingest" for r in rows)

    @pytest.mark.asyncio
    async def test_batch_insert_supports_run_kind(self, session_factory, seeded_asset):
        """CLI re-runs and manual triggers tag run_kind so reconciliation skips them."""
        entries = [
            ManifestEntry(
                run_id=str(uuid4()),
                asset_id=seeded_asset,
                ticker="AAPL",
                scoring_version="v3",
                run_kind="cli_rerun",
            ),
        ]

        async with session_factory() as session:
            await persist_run_manifest_batch(session, entries)
            await session.commit()
            row = (await session.execute(select(ScoringRunManifest))).scalar_one()
            assert row.run_kind == "cli_rerun"

    @pytest.mark.asyncio
    async def test_batch_insert_atomic_failure_rolls_back(self, session_factory, seeded_asset):
        """If ANY row in the batch fails (CHECK constraint violation), NO rows persist.

        This is the B-MANIFEST atomicity contract: orchestrate_ingest writes
        the whole run's manifest in one shot before dispatching ARQ jobs. If
        the batch write fails, no dispatches happen, so coverage_ratio
        reconciliation reports 0/0 (no false positives).

        We trigger failure via the CHECK constraint on run_kind — FK
        enforcement is off by default on SQLite, but CHECK is always on.
        """
        run_id = str(uuid4())
        entries = [
            ManifestEntry(
                run_id=run_id,
                asset_id=seeded_asset,
                ticker="AAPL",
                scoring_version="v3",
            ),
            # Invalid run_kind — fails ck_scoring_run_manifest_kind CHECK constraint
            ManifestEntry(
                run_id=run_id,
                asset_id=seeded_asset,
                ticker="AAPL",
                scoring_version="v4",
                run_kind="INVALID_KIND",
            ),
        ]

        async with session_factory() as session:
            with pytest.raises(Exception):  # noqa: BLE001 — IntegrityError shape varies
                await persist_run_manifest_batch(session, entries)
                await session.commit()
            await session.rollback()

            rows = (await session.execute(select(ScoringRunManifest))).scalars().all()
            assert rows == [], "partial-batch write violated atomicity contract"

    @pytest.mark.asyncio
    async def test_batch_insert_empty_returns_zero(self, session_factory):
        async with session_factory() as session:
            inserted = await persist_run_manifest_batch(session, [])
            assert inserted == 0

    @pytest.mark.asyncio
    async def test_batch_insert_idempotent_on_unique_constraint(
        self, session_factory, seeded_asset
    ):
        """ON CONFLICT DO NOTHING — re-running orchestrate_ingest with the same
        run_id (which should not happen per contract, but defended at the DB
        level anyway) must not error or duplicate.
        """
        run_id = str(uuid4())
        entries = [
            ManifestEntry(
                run_id=run_id,
                asset_id=seeded_asset,
                ticker="AAPL",
                scoring_version="v3",
            ),
        ]

        async with session_factory() as session:
            await persist_run_manifest_batch(session, entries)
            await session.commit()
            await persist_run_manifest_batch(session, entries)
            await session.commit()

            rows = (await session.execute(select(ScoringRunManifest))).scalars().all()
            assert len(rows) == 1
