"""index v3_scores.run_id and v4_scores.run_id non-blocking

Component-level sub-score logging — follow-up to c2d3e4f5a6b7. See
docs/superpowers/specs/2026-05-02-component-subscore-logging-design.md.

This revision creates indexes on the v3_scores.run_id and v4_scores.run_id
columns added by the previous revision. Those tables hold millions of rows;
a blocking CREATE INDEX would lock writes during Railway deploy and cascade
ARQ 120s per-ticker timeouts.

Uses PostgreSQL's CREATE INDEX CONCURRENTLY (non-blocking) — requires running
OUTSIDE a transaction, which is why this revision sets transactional_ddl=False.

On SQLite (test environments) we fall back to plain CREATE INDEX, which is
fine for an in-memory test DB.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: str | Sequence[str] | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# CRITICAL: CREATE INDEX CONCURRENTLY is forbidden inside a transaction.
# This revision must run outside the per-revision auto-transaction.
transactional_ddl = False


def upgrade() -> None:
    """Create run_id indexes without blocking writers."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_pg = bind.dialect.name == "postgresql"

    for table_name in ("v3_scores", "v4_scores"):
        idx_name = f"ix_{table_name}_run_id"
        existing_idx = {i["name"] for i in inspector.get_indexes(table_name)}
        if idx_name in existing_idx:
            continue
        if is_pg:
            # IF NOT EXISTS is supported on CREATE INDEX in PG 9.5+ and is
            # the canonical race-safe form. CONCURRENTLY required for non-blocking.
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {idx_name} ON {table_name} (run_id)"
            )
        else:
            # SQLite test environment — plain CREATE INDEX is fine.
            op.create_index(idx_name, table_name, ["run_id"])


def downgrade() -> None:
    """Drop the run_id indexes. CONCURRENTLY again on PG to avoid blocking."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    for table_name in ("v3_scores", "v4_scores"):
        idx_name = f"ix_{table_name}_run_id"
        if is_pg:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {idx_name}")
        else:
            try:
                op.drop_index(idx_name, table_name=table_name)
            except sa.exc.OperationalError:
                pass  # SQLite no-such-index is benign on rollback
