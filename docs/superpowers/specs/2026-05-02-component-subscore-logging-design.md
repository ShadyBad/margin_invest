# Component Sub-Score Logging — Design Spec

**Date:** 2026-05-02
**Status:** v3 Approved-with-Deferred-Issues (Brandon Option C, 2026-05-02). 5 known issues deferred to code-time — see `~/.claude/skills/shipwright/state/decisions.log` entry "subscore spec — Brandon picks Option C" for the explicit list. Implementation begins at engine `audit_trace.py`.
**Author:** Brandon + Claude
**Branch (proposed):** `feature/component-subscore-logging`

## Revision Log

### v3 (2026-05-02) — addresses qa re-review of v2 (dba + ai-engineer SHIP'd)
- **Q1 (CancelledError leak):** Worker rewritten to use `asyncio.shield(persist_audit_trace(fresh_session, trace))` with a new session from `sessionmaker`, plus `except (Exception, asyncio.CancelledError)` and explicit re-raise of `CancelledError` after logging. ARQ 120s timeout no longer drops traces.
- **Q2 (phantom `filter_reject_log`):** New `scoring_run_manifest` table tracks every `(run_id, asset_id)` that `orchestrate_ingest` dispatched. Reconciliation cron denominator now comes from the manifest. Also unblocks future "what tickers were in run X" queries.
- **Q5 (inspector race):** Migration wraps `op.create_table` in `try/except sa.exc.ProgrammingError` to handle `DuplicateTable` gracefully when two containers race the inspector check.
- **Q6 (blocking CREATE INDEX on hot tables):** `ix_v3_scores_run_id` and `ix_v4_scores_run_id` now use `CREATE INDEX CONCURRENTLY` via `op.execute(...)` outside the transaction. Migration revision sets `transactional_ddl = False`.
- **Q9 (`_NullTrace` violates dataclass type contract):** `_NullTrace` and `ScoreAuditTrace` now both implement an `AuditTraceProtocol` (PEP 544 Protocol). Recorder methods type-check structurally; `_NullTrace` does not need fake `run_id` / `asset_id`.
- **Decisions Log additions:** ARQ retry semantics (retry preserves `run_id`; post-hotpatch retries silently lose old-code rows — documented), and pre-migration NULL `run_id` permanence on score tables.
- **Decision (qa MINORs):** Q3 threshold relaxed to `< 0.95` over 24h; Q7 cron moved to 23:45 UTC (away from 23:00 `daily_pit_update` finishing window); Q8 conviction-gate registry promoted to a separate ship-blocking sub-task before AC #2 lands.

### v2 (2026-05-02) — addresses 7 blockers + 7 majors from initial judge panel
- **B1:** Add `run_id` column to `v3_scores` and `v4_scores` in the same migration. Original spec assumed it existed; it does not.
- **B2:** Run-id regeneration contract — every scoring run gets a fresh UUID. Any code-change re-run produces a new `run_id`. `ON CONFLICT DO NOTHING` is now safe and documented as the intended behavior.
- **B3:** Schema rewritten using SQLAlchemy types (`JSONVariant`, `BigInteger`, `DateTime(timezone=True)`, `UUID().with_variant(String(36), "sqlite")`) for SQLite test compat. Persistence layer dispatches on dialect for upsert.
- **B4:** Worker wraps `persist_audit_trace` in `try/finally` so trace survives `CancelledError` (ARQ 120s per-ticker timeout) and mid-pipeline exceptions.
- **B5:** Alerting wired explicitly: coverage gauge, daily reconciliation cron, Sentry alert rule, threshold contract.
- **B6:** AC #6 split into 6a (synthetic-fixture CI test, ship-blocking) and 6b (real-data audit, T+30d, non-blocking).
- **B7:** Migration body shows `inspector.has_table()` guard inline, not in a footnote.
- **M1:** Added `composite_output` to `component_type` enum.
- **M2:** Added `adjustment` to `component_type` enum.
- **M3:** Recorder verbs collapsed from 5 → 3: `record_factor`, `record_gate(kind=...)`, `record_ml`. Plus `record_adjustment` and `record_composite` for M1/M2.
- **M4:** Null Object pattern. Default `trace` is a `_NullTrace` singleton with no-op recorders. Call sites are unconditional.
- **M5:** Trace-completeness invariant — assert exact expected entry counts per `scoring_version` driven from registries, not hardcoded.
- **M6:** `CHECK (component_type IN (...))` constraint on the table.
- **M7:** Indexes revised — added `(component_type, component_name, computed_at DESC)`, dropped redundant `(ticker, run_id)`. `ticker` column kept for human queries; lookups go via `asset_id`.
- **Misc:** Sample audit query switched from `prices_intraday` to `pit_daily_prices` (correct PIT table). Metadata schema discipline added — per-component-type contract documented.

### v1 (2026-05-02 earlier) — initial draft
Forward-only, no backfill. New `score_components` table. 5-verb recorder. PG-only schema. (Superseded.)

## Mission

For every ticker scored — survivors **and** filter-rejects — persist component-level sub-scores at compute time so the validation audit can run component-vs-forward-return attribution.

This unblocks every future scoring formula change, which is currently gated by `.claude/shipwright.local.md` because sub-score logging does not exist. Today we have composites and a JSONB blob; we cannot answer "did the Beneish filter cost us alpha?" or "is the ROIC trajectory override actually firing on the right tickers?" without query-time component data.

## Architecture Overview

The pipeline extends the existing scoring chain. The engine continues to be pure (no DB / no web deps); a new `ScoreAuditTrace` dataclass collects component data as v3 / v4 pipelines execute and is returned alongside the existing `CompositeScore`. The API layer persists the trace to a new `score_components` table inside the same worker that runs scoring.

```
[Existing] orchestrate_ingest -> ingest_batch -> full_score_v3 / full_score_v4

[New]
  engine.scoring.audit_trace.ScoreAuditTrace
    populated as v3_orchestrator / v4_orchestrator runs
    returned alongside CompositeScore (no DB deps in engine)
    default value is _NullTrace singleton (no-op recorders)

  api.services.score_audit.persist_audit_trace(session, trace)
    dialect-dispatched bulk insert into score_components
    ON CONFLICT DO NOTHING (safe because run_id is regenerated per run)
    fail-closed-warn: log + counter + Sentry, do NOT block scoring chain
    called from worker inside try/finally — survives CancelledError

  reconcile_score_audit (new ARQ cron, daily 23:30 UTC)
    asserts coverage_ratio = rows_today / tickers_scored_today >= 0.99
    raises Sentry critical if breached

  GET /api/v1/admin/score-components/{ticker}?run_id=...&scoring_version=v3
    admin-gated via _verify_admin_jwt (jwt_secret)
    returns full trace for audit + debugging
```

## Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| When to log | Compute time (`full_score_v3` / `full_score_v4`) | Validation audit needs full distribution including filter-rejects, not just published survivors |
| Granularity | 5 factors + cascade gates + conviction gates + filter verdicts + adjustments + ML contribution + composite output | Anything less leaves audit questions unanswerable. Geometric-mean intermediates explicitly skipped |
| Persistence | New `score_components` table | Queryable beats fast-to-ship for audit-driven feature |
| Backfill | None — forward-only | Half-populated history would force every audit query to filter `metadata->>'backfill' = 'false'` forever |
| FK to score row | None | Three separate score tables make a clean FK ugly; filter-rejects have no parent row anyway. Join on `(asset_id, run_id, scoring_version)` |
| Run-ID lifecycle | **NEW IN v2, refined in v3.** Generated by `orchestrate_ingest` per run. **MUST be regenerated on every re-run** even if same date / same code. Re-runs after a code-change hotpatch are conceptually a new run; the audit table treats them as such. Documented in `orchestrate_ingest` docstring | Makes `ON CONFLICT DO NOTHING` safe. The "stale value silently kept" failure mode disappears because re-runs never collide on `run_id` |
| ARQ retry semantics | **v3 explicit.** ARQ retries replay the exact job kwargs — same `run_id` is reused on retry. This is fine: identical inputs → identical components → unique constraint no-ops the duplicates. **Risk acknowledged:** if a retry happens *after* a code hotpatch, the new code's component values silently lose to the existing `(asset_id, run_id, ...)` rows from the pre-patch run. Mitigation: any code change requires a manual `orchestrate_ingest` re-trigger with a fresh UUID — never rely on retry for new code | Documented to prevent silent audit drift |
| Pre-migration NULL `run_id` on score tables | **v3 explicit.** The nullable `run_id` columns added to `v3_scores` / `v4_scores` will be NULL forever for rows that existed before deploy. No backfill — the audit window starts at deploy date. Audit queries always filter `run_id IS NOT NULL` | Forward-only contract per Decisions Log; NULL rows are fossils, not data |
| Failure mode | Fail-closed-warn + observability | Audit MUST NOT block scoring chain. Coverage gauge + daily reconciliation cron detect silent rot within 24h |
| Engine purity | Preserved + enforced | `audit_trace.py` is a pure dataclass module. Zero DB / web deps. New AC #7 adds an `ast.parse` import-lint test |
| Recorder API | 5 verbs at the row-shape level: `record_factor`, `record_gate(kind="filter"|"cascade"|"conviction")`, `record_adjustment`, `record_ml`, `record_composite` | Avoids the dev-error trap of two verbs with identical signatures |
| Default trace | Null Object singleton (`_NullTrace`) | Eliminates `if trace is not None:` rot at every call site |

## Component Taxonomy (locked enum, 7 values)

The `component_type` enum is a one-way door. Pre-seeding all foreseeable values now while the door is open:

| `component_type` | `component_name` examples | `value` | `passed` |
|---|---|---|---|
| `factor` | `quality`, `value`, `growth`, `momentum`, `anti_consensus` | Percentile (0–100) | NULL |
| `cascade_gate` | `gate_1_data_quality`, `gate_2_compounding_power`, … | NULL | TRUE / FALSE |
| `conviction_gate` | `reinvestment_tier`, `roic_trajectory_override`, `mediocrity_trajectory_override` | NULL | TRUE / FALSE (passed; for overrides this means "fired and qualified the ticker") |
| `filter` | `beneish_m_score`, `altman_z_score`, `mediocrity`, `liquidity`, `data_consistency` | NULL | TRUE / FALSE (passed filter) |
| `adjustment` | `sector_adapter_cyclical`, `growth_stage_classification`, `dual_track_fusion_weight`, `market_regime` | Scalar (delta or weight) | NULL |
| `ml_contribution` | `rules_weight`, `ml_weight`, `ml_alpha`, `ml_confidence` | Scalar | NULL |
| `composite_output` | `composite_score`, `composite_tier`, `signal` | Scalar (or numeric encoding of categorical) | NULL |

Per-row `threshold` and `observed` columns capture the comparison used for gates / filters. The `metadata` JSONB column captures structured-but-variable detail per component type.

### Metadata schema discipline

Each `component_type` has a documented metadata contract. Drift is caught by an additional CI test (`test_audit_trace_metadata_contracts.py`):

| `component_type` | required `metadata` keys | optional |
|---|---|---|
| `factor` | (none) | `sector_neutral_rank`, `growth_stage_at_score` |
| `cascade_gate` | `gate_index` (int) | `capital_light_bypass` (bool), `bypass_reason` (str) |
| `conviction_gate` | `tier` (str), `override_fired` (bool) | `quarters_window`, `slope_bps_per_quarter` |
| `filter` | `filter_version` (str) | `raw_inputs` (dict — small only) |
| `adjustment` | `target` (str — what got adjusted) | `direction` (`+`/`-`), `delta` |
| `ml_contribution` | `model_run_id` (str/UUID) | (none) |
| `composite_output` | (none) | `regime`, `style` |

## Schema

### `score_components` (new table)

```python
# api/src/margin_api/db/models.py
class ScoreComponent(Base):
    __tablename__ = "score_components"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)  # denormalized
    run_id: Mapped[str] = mapped_column(
        String(36),  # UUID-as-string for SQLite compat; PG sees TEXT, queries unchanged
        nullable=False,
    )
    scoring_version: Mapped[str] = mapped_column(String(20), nullable=False)
    component_type: Mapped[str] = mapped_column(String(30), nullable=False)
    component_name: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "asset_id", "run_id", "scoring_version", "component_type", "component_name",
            name="uq_score_components_identity",
        ),
        CheckConstraint(
            "component_type IN ('factor','cascade_gate','conviction_gate',"
            "'filter','adjustment','ml_contribution','composite_output')",
            name="ck_score_components_type",
        ),
        Index("ix_score_components_run_type", "run_id", "component_type"),
        Index(
            "ix_score_components_lookup",
            "component_type", "component_name", "computed_at",
            # PG: DESC supported by index_postgresql_using; SQLite ignores the order hint
        ),
        Index("ix_score_components_version_name", "scoring_version", "component_name"),
    )
```

Notes:
- **Column named `metadata_json` not `metadata`** — `metadata` is reserved on SQLAlchemy `Base.metadata`.
- **`run_id` as `String(36)`** — UUID stored as string. Works on both PG and SQLite. PG queries can still cast as needed; perf cost is negligible at this scale.
- **No FK to `scores` / `v3_scores` / `v4_scores`.** Join on `(asset_id, run_id, scoring_version)`.
- **FK to `assets` is safe** with cascade — if an asset is deleted, audit rows go too.

### `v3_scores` / `v4_scores` (modified — add `run_id`)

```python
# add to V3Score and V4Score
run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
```

Nullable for backward compat with existing rows. New rows always populated. Audit queries that need to join filter on `run_id IS NOT NULL`.

### `scoring_run_manifest` (new table — v3)

Tracks every `(run_id, asset_id)` that `orchestrate_ingest` dispatched. Without this, the reconciliation cron has no honest denominator (qa Q2). Side benefit: future "what tickers were in run X" queries become trivial.

```python
# api/src/margin_api/db/models.py
class ScoringRunManifest(Base):
    __tablename__ = "scoring_run_manifest"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(20), nullable=False)
    dispatched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC),
    )
    run_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="orchestrate_ingest")
    # 'orchestrate_ingest' | 'cli_rerun' | 'manual' — used to scope reconciliation

    __table_args__ = (
        UniqueConstraint("run_id", "asset_id", "scoring_version",
                         name="uq_scoring_run_manifest_identity"),
    )
```

`orchestrate_ingest` writes one manifest row per `(run_id, asset_id, scoring_version)` BEFORE dispatching the `full_score_v*` job. The reconciliation cron then computes coverage as:

```
coverage_ratio = distinct(asset_id) in score_components for run_id
                / distinct(asset_id) in scoring_run_manifest for run_id
                where run_kind = 'orchestrate_ingest'
```

CLI re-runs and manual triggers are excluded from reconciliation by `run_kind` filter (qa Q3 fix — eliminates false positives from one-off backfills).

### Migration (idempotent, race-safe, non-blocking on hot tables)

```python
# api/alembic/versions/<rev>_score_components.py
revision = "..."
down_revision = "..."
branch_labels = None
depends_on = None

# v3: this revision touches CONCURRENT index creation, so it MUST run outside a txn.
# Alembic respects this opt-out per revision.
transactional_ddl = False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_pg = bind.dialect.name == "postgresql"

    # 1) Add run_id columns to existing score tables (metadata-only in PG11+)
    for table_name in ("v3_scores", "v4_scores"):
        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        if "run_id" not in existing_cols:
            op.add_column(
                table_name,
                sa.Column("run_id", sa.String(36), nullable=True),
            )

    # 2) Create indexes on the new run_id columns CONCURRENTLY (PG only — non-blocking)
    #    SQLite ignores the CONCURRENTLY hint and just does CREATE INDEX (fine for tests).
    for table_name in ("v3_scores", "v4_scores"):
        idx_name = f"ix_{table_name}_run_id"
        existing_idx = {i["name"] for i in inspector.get_indexes(table_name)}
        if idx_name not in existing_idx:
            if is_pg:
                op.execute(
                    f'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                    f'{idx_name} ON {table_name} (run_id)'
                )
            else:
                op.create_index(idx_name, table_name, ["run_id"])

    # 3) Create score_components — wrap in try/except DuplicateTable to handle
    #    inspector race when two Railway containers start simultaneously
    if not inspector.has_table("score_components"):
        try:
            op.create_table(
                "score_components",
                sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
                sa.Column("asset_id", sa.Integer(),
                          sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
                sa.Column("ticker", sa.String(20), nullable=False),
                sa.Column("run_id", sa.String(36), nullable=False),
                sa.Column("scoring_version", sa.String(20), nullable=False),
                sa.Column("component_type", sa.String(30), nullable=False),
                sa.Column("component_name", sa.String(80), nullable=False),
                sa.Column("value", sa.Float(), nullable=True),
                sa.Column("passed", sa.Boolean(), nullable=True),
                sa.Column("threshold", sa.Float(), nullable=True),
                sa.Column("observed", sa.Float(), nullable=True),
                sa.Column("metadata_json",
                          sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
                          nullable=False, server_default=sa.text("'{}'")),
                sa.Column("computed_at", sa.DateTime(timezone=True),
                          nullable=False, server_default=sa.func.now()),
                sa.UniqueConstraint("asset_id","run_id","scoring_version",
                                    "component_type","component_name",
                                    name="uq_score_components_identity"),
                sa.CheckConstraint(
                    "component_type IN ('factor','cascade_gate','conviction_gate',"
                    "'filter','adjustment','ml_contribution','composite_output')",
                    name="ck_score_components_type",
                ),
                sa.Index("ix_score_components_asset_id", "asset_id"),
            )
        except sa.exc.ProgrammingError as exc:
            # DuplicateTable from concurrent container — second container loses safely
            if "DuplicateTable" not in str(exc) and "already exists" not in str(exc):
                raise

    # 4) Create scoring_run_manifest with the same race guard
    if not inspector.has_table("scoring_run_manifest"):
        try:
            op.create_table(
                "scoring_run_manifest",
                sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
                sa.Column("run_id", sa.String(36), nullable=False),
                sa.Column("asset_id", sa.Integer(),
                          sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
                sa.Column("ticker", sa.String(20), nullable=False),
                sa.Column("scoring_version", sa.String(20), nullable=False),
                sa.Column("dispatched_at", sa.DateTime(timezone=True),
                          nullable=False, server_default=sa.func.now()),
                sa.Column("run_kind", sa.String(20),
                          nullable=False, server_default=sa.text("'orchestrate_ingest'")),
                sa.UniqueConstraint("run_id", "asset_id", "scoring_version",
                                    name="uq_scoring_run_manifest_identity"),
                sa.Index("ix_scoring_run_manifest_run_id", "run_id"),
                sa.Index("ix_scoring_run_manifest_asset_id", "asset_id"),
            )
        except sa.exc.ProgrammingError as exc:
            if "DuplicateTable" not in str(exc) and "already exists" not in str(exc):
                raise

    # 5) Remaining indexes on score_components (small table at first, regular CREATE INDEX OK)
    existing_idx = (
        {i["name"] for i in inspector.get_indexes("score_components")}
        if inspector.has_table("score_components") else set()
    )
    for name, cols in [
        ("ix_score_components_run_type", ["run_id", "component_type"]),
        ("ix_score_components_lookup", ["component_type", "component_name", "computed_at"]),
        ("ix_score_components_version_name", ["scoring_version", "component_name"]),
    ]:
        if name not in existing_idx:
            op.create_index(name, "score_components", cols)
```

Race-safety summary:
- **`v3_scores`/`v4_scores` index** — `CREATE INDEX CONCURRENTLY` does not block writes; in-flight scoring continues. Required because these tables already hold millions of rows.
- **`score_components` / `scoring_run_manifest`** — fresh empty tables; concurrent `CREATE TABLE` from two containers caught by `try/except ProgrammingError` (qa Q5).
- **`transactional_ddl = False`** is non-negotiable for this revision because PG forbids `CREATE INDEX CONCURRENTLY` inside a transaction. Down-side: partial failure mid-migration leaves columns/tables behind. Acceptable because every step is `IF NOT EXISTS`-style and re-running converges.

## Engine Contract — `ScoreAuditTrace` + `AuditTraceProtocol`

```python
# engine/src/margin_engine/scoring/audit_trace.py
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

ComponentType = Literal[
    "factor", "cascade_gate", "conviction_gate", "filter",
    "adjustment", "ml_contribution", "composite_output",
]
GateKind = Literal["cascade", "conviction", "filter"]

@dataclass
class ComponentEntry:
    component_type: ComponentType
    component_name: str
    value: float | None = None
    passed: bool | None = None
    threshold: float | None = None
    observed: float | None = None
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class AuditTraceProtocol(Protocol):
    """Structural type for trace recorders. Allows ScoreAuditTrace and _NullTrace
    to coexist without inheriting from a common base or sharing required dataclass
    fields (qa Q9 — _NullTrace must not be forced to fake run_id/asset_id)."""

    def record_factor(self, name: str, percentile: float, **metadata) -> None: ...
    def record_gate(
        self, kind: GateKind, name: str, passed: bool,
        threshold: float | None = None, observed: float | None = None,
        **metadata,
    ) -> None: ...
    def record_adjustment(self, name: str, value: float, **metadata) -> None: ...
    def record_ml(self, name: str, value: float, **metadata) -> None: ...
    def record_composite(self, name: str, value: float, **metadata) -> None: ...


@dataclass
class ScoreAuditTrace:
    """Real trace. Populated as v3/v4 pipelines execute. Persisted by api/services/score_audit."""
    run_id: UUID
    asset_id: int
    ticker: str
    scoring_version: Literal["v3", "v4", "v3_track_c"]
    entries: list[ComponentEntry] = field(default_factory=list)

    def record_factor(self, name: str, percentile: float, **metadata) -> None: ...
    def record_gate(self, kind: GateKind, name: str, passed: bool, threshold=None,
                    observed=None, **metadata) -> None: ...
    def record_adjustment(self, name: str, value: float, **metadata) -> None: ...
    def record_ml(self, name: str, value: float, **metadata) -> None: ...
    def record_composite(self, name: str, value: float, **metadata) -> None: ...


class _NullTrace:
    """Null Object — silently no-ops every recorder. Implements AuditTraceProtocol
    structurally; does NOT subclass ScoreAuditTrace, so it carries no fake fields."""

    def record_factor(self, *a, **k): pass
    def record_gate(self, *a, **k): pass
    def record_adjustment(self, *a, **k): pass
    def record_ml(self, *a, **k): pass
    def record_composite(self, *a, **k): pass


NULL_TRACE: AuditTraceProtocol = _NullTrace()
```

Pure module. Zero web / DB imports (only `dataclasses`, `typing`, `uuid` from stdlib). AC #7 enforces this via `ast.parse` test.

Orchestrator signatures use the Protocol:
```python
def score(..., trace: AuditTraceProtocol = NULL_TRACE) -> CompositeScore: ...
```

Call sites are **unconditional** (`trace.record_*(...)`) because `_NullTrace` no-ops. Persistence layer at `api/services/score_audit.py` does one `isinstance(trace, ScoreAuditTrace)` check at the boundary to short-circuit `_NullTrace` (avoids the structural-typing limitation that `_NullTrace` has no `entries` to flush).

## Persistence Contract

```python
# api/src/margin_api/services/score_audit.py
async def persist_audit_trace(
    session: AsyncSession,
    trace: ScoreAuditTrace,
) -> int:
    """
    Bulk insert components for one trace. Returns rows inserted.

    Fail-closed-warn: any exception is caught upstream by the worker.
    This function MAY raise; the worker's try/finally swallows + logs + counts.

    Dispatches insert dialect by bind.dialect.name:
      - postgresql -> postgresql.insert(...).on_conflict_do_nothing(...)
      - sqlite     -> sqlite.insert(...).on_conflict_do_nothing(...) (3.24+)
    """
```

- `_NullTrace` short-circuits — `if isinstance(trace, _NullTrace): return 0`.
- Dialect-aware upsert via `dialect.name`.
- Emits structured log + Prometheus counter on the worker side, not here.
- Idempotent by the unique constraint. Re-runs of the **same** `run_id` (which should not happen per contract) silently no-op duplicates.

## Worker Wiring (v3 — cancellation-safe)

The naive `try/finally` from v2 leaks traces under `asyncio.CancelledError` (qa Q1):
- In Python 3.11+ `CancelledError` inherits from `BaseException`, not `Exception` — slips past `except Exception`.
- Outer cancellation may have closed the worker's main session; calling `await session.execute(...)` inside `finally` raises `InterfaceError` immediately.

v3 fix: persist via `asyncio.shield` against a freshly-checked-out session, and explicitly handle `CancelledError`:

```python
# api/src/margin_api/workers.py
import asyncio
import sentry_sdk
import structlog

logger = structlog.get_logger()
# session_factory is the project's existing async_sessionmaker exposed on app state
from margin_api.db import session_factory


async def _flush_trace_safely(trace: ScoreAuditTrace) -> None:
    """Persist the trace using a NEW session, shielded from cancellation,
    so an in-flight ARQ timeout does not poison both the worker and the audit."""
    async with session_factory() as fresh_session:
        await persist_audit_trace(fresh_session, trace)
        await fresh_session.commit()


async def full_score_v3(ctx, asset_id: int, run_id: str) -> dict:
    trace = ScoreAuditTrace(
        run_id=UUID(run_id), asset_id=asset_id, ticker=ticker,
        scoring_version="v3",
    )
    cancelled: asyncio.CancelledError | None = None

    try:
        composite = v3_orchestrator.score(..., trace=trace)
        v3_score = V3Score(asset_id=asset_id, run_id=run_id, ...)
        session.add(v3_score)
        return {...}
    except asyncio.CancelledError as exc:
        cancelled = exc  # capture, re-raise after audit flush
    finally:
        # asyncio.shield prevents the flush itself from being cancelled mid-await.
        # Fresh session avoids the closed-session trap from outer cancellation.
        try:
            await asyncio.shield(_flush_trace_safely(trace))
        except (Exception, asyncio.CancelledError) as exc:
            logger.warning(
                "score_audit_persist_failed",
                asset_id=asset_id, run_id=run_id,
                outer_cancelled=cancelled is not None,
                exc_info=exc,
            )
            SCORE_AUDIT_PERSIST_FAILURES.inc()
            sentry_sdk.capture_exception(exc)
        if cancelled is not None:
            raise cancelled  # honor the original cancellation after audit attempt
```

Notes on the pattern:
- `asyncio.shield` wraps the awaited coroutine — if the outer task is cancelled, the shielded coroutine completes; only the *waiter* is cancelled. The persist runs to completion before the outer cancellation is re-raised.
- The fresh session ensures the audit write does not depend on the (possibly-closed) outer session's connection.
- `except (Exception, asyncio.CancelledError)` catches both the normal path and the case where `shield` itself is interrupted before the inner coroutine finishes (rare; possible during shutdown).
- `re-raise cancelled` after the flush preserves caller cancellation semantics — ARQ still sees the ticker as cancelled and accounts for it correctly.

**Run-id lifecycle:**
- `orchestrate_ingest` generates a fresh `uuid.uuid4()` at the start of each run.
- Before dispatching `full_score_v*` jobs, it writes one `ScoringRunManifest(run_id, asset_id, scoring_version, run_kind="orchestrate_ingest")` row per ticker.
- The UUID is propagated via job kwargs through every downstream worker.
- Manual re-runs (CLI, retry) MUST generate a new UUID and write fresh manifest rows with `run_kind="cli_rerun"` or `"manual"`. Documented in `orchestrate_ingest`'s docstring and enforced by `worker.py` request validation.
- **ARQ retries** preserve the same `run_id` (intentional — identical inputs produce identical components, unique constraint dedupes). The hotpatch retry edge case is documented in Decisions Log.

**Filter-reject path:** the orchestrator still populates `trace` with all components evaluated up to the point of rejection. The `try/finally` + `asyncio.shield` ensures the trace persists even when `v3_orchestrator.score()` raises a `FilterRejectedError` or the ticker hits the 120s timeout.

## Observability Contract (B5)

| Signal | Type | Threshold | Action |
|---|---|---|---|
| `score_audit_persist_failures_total` | Counter | > 5/hour | Sentry warning |
| `score_audit_coverage_ratio` | Gauge (computed by reconcile cron) | < 0.95 over a 24h window, scoped to `run_kind='orchestrate_ingest'` | Sentry critical, page on-call |
| `score_audit_rows_per_run` | Histogram | (observability only) | Anomaly detection |

### Reconciliation cron (new — v3, manifest-backed)

```python
# Daily 23:45 UTC — moved from 23:30 to clear daily_pit_update finishing window (qa Q7)
@cron("45 23 * * *")
async def reconcile_score_audit(ctx) -> None:
    """
    For yesterday's orchestrate_ingest run_id(s), assert:

      coverage_ratio =
        count(distinct asset_id in score_components for run_id)
        /
        count(distinct asset_id in scoring_run_manifest
              for run_id where run_kind='orchestrate_ingest')

    If coverage_ratio < 0.95, raise CRITICAL to Sentry. Daily cadence detects
    partial silent failure within 24h, not 30 days.

    CLI re-runs and manual triggers are excluded by the run_kind filter to
    eliminate false positives from one-off backfills (qa Q3).
    """
```

This becomes the **15th cron** (per MEMORY.md, currently 14 cron jobs in the system after `orchestrate_risk_diffing`).

The denominator now comes from `scoring_run_manifest` — a real table written synchronously by `orchestrate_ingest` before dispatch, not the phantom `filter_reject_log` from v2 (qa Q2). `v3_scores` and `v4_scores` are not used as the denominator because filter-rejects produce no rows there; `scoring_run_manifest` is the only honest "what was scheduled to be scored" record.

## Read Endpoint

```
GET /api/v1/admin/score-components/{ticker}?run_id=<uuid>&scoring_version=v3
```

- Auth: `_verify_admin_jwt` (uses `jwt_secret`, NOT `service_auth_secret`)
- 200: full component list for the ticker / run / version
- 400: malformed UUID or unknown `scoring_version`
- 401: missing / invalid admin JWT
- 403: valid JWT but role != admin/superadmin
- 404: no rows for `(ticker, run_id, scoring_version)`

Response shape unchanged from v1.

## Sample Audit Query (corrected to PIT prices)

```sql
-- "Did the Beneish M-Score filter improve risk-adjusted forward 30d return?"
WITH beneish_decisions AS (
  SELECT
    sc.run_id,
    sc.asset_id,
    sc.ticker,
    sc.passed AS beneish_passed,
    sc.observed AS beneish_score,
    sc.computed_at::date AS run_date
  FROM score_components sc
  WHERE sc.scoring_version = 'v3'
    AND sc.component_type  = 'filter'
    AND sc.component_name  = 'beneish_m_score'
    AND sc.computed_at >= now() - interval '90 days'
),
forward_returns AS (
  SELECT bd.*,
         (p_t1.close / p_t0.close) - 1.0 AS forward_30d_return
  FROM beneish_decisions bd
  JOIN pit_daily_prices p_t0
    ON p_t0.asset_id = bd.asset_id AND p_t0.price_date = bd.run_date
  JOIN pit_daily_prices p_t1
    ON p_t1.asset_id = bd.asset_id
   AND p_t1.price_date = bd.run_date + interval '30 days'
)
SELECT
  beneish_passed,
  count(*)                  AS n_tickers,
  avg(forward_30d_return)   AS mean_fwd_30d,
  stddev(forward_30d_return) AS sd_fwd_30d
FROM forward_returns
GROUP BY beneish_passed;
```

Same query shape works for every filter, gate, factor, adjustment, ML weight, composite output.

## Risk Flags

- **Irreversible:** alembic migration on prod (additive on `score_components`; nullable column add on `v3_scores`/`v4_scores`). Per `shipwright.local.md`, migrations on `scores`-adjacent tables are gated. **Apply step requires explicit Brandon approval.** Code merge is fine.
- **Touches prod:** yes — Railway runs migration on container start at deploy.
- **Data loss possible:** no — fully additive.
- **Financial / Legal / Security:** no.

## What This Spec Does Not Cover

- **Frontend surface.** No web UI. Admin endpoint is for SQL-level audit + debugging.
- **Geometric-mean intermediates.** Per Brandon's call. Enum is extendable additively if needed later.
- **Backfill.** Forward-only.
- **Scoring formula changes** unlocked by this audit data. Separate spec when the audit produces signal.

## Acceptance Criteria

1. `score_components`, `scoring_run_manifest` tables exist in prod after deploy. Migration is idempotent (re-run safe). `run_id` column added to `v3_scores` and `v4_scores` with `CREATE INDEX CONCURRENTLY`. Concurrent migration race tolerated via `try/except ProgrammingError` on table creation.
2. Every ticker that passes through `full_score_v3` and `full_score_v4` produces ≥ 1 row in `score_components` with the matching `run_id`. **Trace-completeness invariant test** asserts exact entry counts per scoring_version, driven from the gate/filter registries.
3. Filter-rejected tickers produce ≥ 1 row in `score_components`. **Verified by:** dedicated golden-trace test feeding a Beneish-failing fixture; assert row count > 0 for that asset_id and zero rows in `v3_scores`.
4. `component_type` enum holds all 7 values with no rename across implementation. `CHECK` constraint enforces the set at the DB level.
5. `persist_audit_trace` failure does not abort the scoring chain. Verified via three fault-injection tests:
   (a) force `Exception` in `session.execute` → confirm `v3_scores` row written, counter incremented.
   (b) cancel the worker mid-`v3_orchestrator.score()` (raise `asyncio.CancelledError`) → confirm trace flushed via `asyncio.shield`, original cancellation re-raised.
   (c) outer session closed before flush → confirm fresh session from `session_factory` succeeds independently.
6. **Split:**
   - **6a (ship-blocking):** Synthetic-fixture audit query test — write 50 fake `score_components` rows + 50 `pit_daily_prices` rows, run the Beneish sample query, assert it returns 2 buckets with expected means.
   - **6b (deferred, non-blocking, T+30d):** Real-data audit query executes cleanly against 30 days of forward returns. Tracked in `state/decisions.log` for follow-up — schedule a `/loop` reminder.
7. Engine purity preserved — `engine/src/margin_engine/scoring/audit_trace.py` imports nothing from `api/`, `sqlalchemy`, or any web framework. **Enforced by AC test:** `engine/tests/test_audit_trace_purity.py` parses the module AST and asserts no forbidden imports.
8. Admin endpoint returns 200/400/401/403/404 per the contract above (all four error paths covered).
9. Coverage gauge `score_audit_coverage_ratio` is wired to Sentry with a `< 0.95` threshold scoped to `run_kind='orchestrate_ingest'`. Reconciliation cron `reconcile_score_audit` is registered, runs daily at 23:45 UTC, and computes its denominator from `scoring_run_manifest` (not from any score table).
10. CI passes: ruff, mypy strict, engine tests (incl. SQLite compat), api tests.

## Test Plan

Engine-side (TDD, in `engine/tests/scoring/test_audit_trace.py`):
- Pass-through ticker (all gates/filters pass) → expect N factor + K cascade + M filter + 1 composite_output entries.
- Filter-rejected ticker (Beneish kill) → expect filter row with `passed=False`, no composite_output row.
- Conviction-gate-rejected → expect conviction_gate row with `passed=False`.
- ROIC trajectory override fires → expect `conviction_gate / roic_trajectory_override` row with `metadata.override_fired=True`.
- v4 ML-disabled fallback (rules-only) → expect `ml_contribution / ml_weight = 0.0`.
- Track C cascade path → expect `scoring_version="v3_track_c"` rows.
- **Trace-completeness invariant** — generic test parametrized by scoring_version, asserts exact expected entry counts pulled from the gate/filter registries (not hardcoded).

API-side (in `api/tests/services/test_score_audit.py`):
- Happy-path bulk insert.
- Filter-reject path (no parent row in `v3_scores`).
- Idempotency — same `(asset_id, run_id, ...)` insert twice, second is no-op.
- Dialect dispatch — same test under PG and SQLite, both pass.
- Fault injection — patch `session.execute` to raise; confirm worker continues, counter increments, Sentry called.
- `_NullTrace` short-circuit — no DB calls when null trace passed.

API endpoint (in `api/tests/routes/test_admin_score_components.py`):
- 200 with valid JWT + valid params.
- 400 with malformed UUID.
- 401 with no JWT.
- 403 with valid JWT but `role=user`.
- 404 with unknown ticker.

## Review Checklist (v3)

- [ ] Brandon redline of v3 changes
- [x] dba: SHIP'd v2 (re-review optional — v3 only touches DDL via CONCURRENTLY index + DuplicateTable handling, both within dba's prior accepted patterns)
- [x] ai_engineer: SHIP'd v2 (re-review optional — v3 only swaps `_NullTrace` to Protocol, accepted as MINOR in v2)
- [ ] qa: re-verify Q1 (CancelledError + asyncio.shield), Q2 (manifest-backed reconciliation), Q5 (DuplicateTable guard), Q6 (CONCURRENTLY index), Q9 (Protocol-based NullTrace). Plus residual risk on the new `scoring_run_manifest` write at orchestrate_ingest dispatch (what if manifest write fails mid-batch?)
