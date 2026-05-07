"""add score_components, scoring_run_manifest, and run_id columns

Component-level sub-score logging — see
docs/superpowers/specs/2026-05-02-component-subscore-logging-design.md.

This is the FIRST of two revisions. It is fully transactional:
  - Adds nullable run_id column to v3_scores and v4_scores (metadata-only in PG11+, instant)
  - Creates score_components and scoring_run_manifest tables
  - Creates indexes on the new tables (small/empty, regular CREATE INDEX OK)

It does NOT create indexes on v3_scores.run_id / v4_scores.run_id — those tables
hold millions of rows and a blocking CREATE INDEX would cascade ARQ 120s timeouts
during deploy. The follow-up revision (transactional_ddl=False) handles those
with CREATE INDEX CONCURRENTLY.

Race-safety on Railway double-container boot:
  - inspector.has_table / inspector.get_columns guards primary safety
  - try/except ProgrammingError catches CREATE TABLE / ADD COLUMN duplicates
    via PG SQLSTATE codes (42P07 DuplicateTable, 42701 DuplicateColumn) — NOT
    string match (locale-fragile)

Revision ID: c2d3e4f5a6b7
Revises: cd6c9c3cd56a
Create Date: 2026-05-02

NOTE: chained after the existing risk_diffing+experiment_signups merge
(cd6c9c3cd56a) to avoid a parallel mergepoint. Adds new tables only — no
schema overlap with either upstream branch.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: str | Sequence[str] | None = "cd6c9c3cd56a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# PG SQLSTATE codes for race-safe error handling
_PG_DUPLICATE_TABLE = "42P07"
_PG_DUPLICATE_COLUMN = "42701"
_PG_DUPLICATE_OBJECT = "42710"  # for indexes / constraints created in race


def _is_duplicate_error(exc: Exception, *codes: str) -> bool:
    """Return True if the wrapped DBAPI exception is one of the given pgcodes.

    Falls back to string match for non-PG dialects (SQLite tests) where
    pgcode isn't available — these races don't realistically happen on
    SQLite-in-memory test setups.
    """
    orig = getattr(exc, "orig", None)
    pgcode = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
    if pgcode and pgcode in codes:
        return True
    msg = str(exc).lower()
    return any(token in msg for token in ("already exists", "duplicate"))


def upgrade() -> None:
    """Forward migration — transactional, idempotent, race-safe."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Add run_id column to v3_scores and v4_scores (metadata-only in PG11+).
    #    Index creation is deferred to the next revision to use CREATE INDEX CONCURRENTLY.
    for table_name in ("v3_scores", "v4_scores"):
        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        if "run_id" not in existing_cols:
            try:
                op.add_column(
                    table_name,
                    sa.Column("run_id", sa.String(36), nullable=True),
                )
            except sa.exc.ProgrammingError as exc:
                if not _is_duplicate_error(exc, _PG_DUPLICATE_COLUMN):
                    raise

    # 2) score_components — primary audit table.
    if not inspector.has_table("score_components"):
        try:
            op.create_table(
                "score_components",
                sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
                sa.Column(
                    "asset_id",
                    sa.Integer(),
                    sa.ForeignKey("assets.id", ondelete="CASCADE"),
                    nullable=False,
                ),
                sa.Column("ticker", sa.String(20), nullable=False),
                sa.Column("run_id", sa.String(36), nullable=False),
                sa.Column("scoring_version", sa.String(20), nullable=False),
                sa.Column("component_type", sa.String(30), nullable=False),
                sa.Column("component_name", sa.String(80), nullable=False),
                sa.Column("value", sa.Float(), nullable=True),
                sa.Column("passed", sa.Boolean(), nullable=True),
                sa.Column("threshold", sa.Float(), nullable=True),
                sa.Column("observed", sa.Float(), nullable=True),
                sa.Column(
                    "metadata_json",
                    sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
                    nullable=False,
                    server_default=sa.text("'{}'"),
                ),
                sa.Column(
                    "computed_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
                sa.UniqueConstraint(
                    "asset_id",
                    "run_id",
                    "scoring_version",
                    "component_type",
                    "component_name",
                    name="uq_score_components_identity",
                ),
                sa.CheckConstraint(
                    "component_type IN ('factor','cascade_gate','conviction_gate',"
                    "'filter','adjustment','ml_contribution','composite_output')",
                    name="ck_score_components_type",
                ),
            )
        except sa.exc.ProgrammingError as exc:
            if not _is_duplicate_error(exc, _PG_DUPLICATE_TABLE):
                raise

    # 3) scoring_run_manifest — denominator for reconciliation cron.
    if not inspector.has_table("scoring_run_manifest"):
        try:
            op.create_table(
                "scoring_run_manifest",
                sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
                sa.Column("run_id", sa.String(36), nullable=False),
                sa.Column(
                    "asset_id",
                    sa.Integer(),
                    sa.ForeignKey("assets.id", ondelete="CASCADE"),
                    nullable=False,
                ),
                sa.Column("ticker", sa.String(20), nullable=False),
                sa.Column("scoring_version", sa.String(20), nullable=False),
                sa.Column(
                    "dispatched_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
                sa.Column(
                    "run_kind",
                    sa.String(20),
                    nullable=False,
                    server_default=sa.text("'orchestrate_ingest'"),
                ),
                sa.UniqueConstraint(
                    "run_id",
                    "asset_id",
                    "scoring_version",
                    name="uq_scoring_run_manifest_identity",
                ),
                sa.CheckConstraint(
                    "run_kind IN ('orchestrate_ingest','cli_rerun','manual')",
                    name="ck_scoring_run_manifest_kind",
                ),
            )
        except sa.exc.ProgrammingError as exc:
            if not _is_duplicate_error(exc, _PG_DUPLICATE_TABLE):
                raise

    # 4) Indexes on the two new tables. Both are empty/fresh, so regular
    #    CREATE INDEX is non-blocking. Idempotent via inspector check.
    def _ensure_index(table: str, name: str, cols: list[str]) -> None:
        if not inspector.has_table(table):
            return
        existing = {i["name"] for i in inspector.get_indexes(table)}
        if name not in existing:
            try:
                op.create_index(name, table, cols)
            except sa.exc.ProgrammingError as exc:
                if not _is_duplicate_error(exc, _PG_DUPLICATE_TABLE, _PG_DUPLICATE_OBJECT):
                    raise

    _ensure_index("score_components", "ix_score_components_asset_id", ["asset_id"])
    _ensure_index("score_components", "ix_score_components_run_type", ["run_id", "component_type"])
    _ensure_index(
        "score_components",
        "ix_score_components_lookup",
        ["component_type", "component_name", "computed_at"],
    )
    _ensure_index(
        "score_components",
        "ix_score_components_version_name",
        ["scoring_version", "component_name"],
    )
    _ensure_index("scoring_run_manifest", "ix_scoring_run_manifest_run_id", ["run_id"])
    _ensure_index("scoring_run_manifest", "ix_scoring_run_manifest_asset_id", ["asset_id"])


def downgrade() -> None:
    """Reverse migration. Drops both new tables and the run_id columns.

    NOTE: dropping the v3_scores/v4_scores indexes added by the follow-up
    revision is the responsibility of THAT revision's downgrade — alembic
    runs them in reverse order.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("scoring_run_manifest"):
        op.drop_table("scoring_run_manifest")
    if inspector.has_table("score_components"):
        op.drop_table("score_components")

    for table_name in ("v3_scores", "v4_scores"):
        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        if "run_id" in existing_cols:
            op.drop_column(table_name, "run_id")
