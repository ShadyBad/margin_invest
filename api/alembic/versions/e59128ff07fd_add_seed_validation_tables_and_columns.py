"""add seed validation tables and columns

Revision ID: e59128ff07fd
Revises: a6ad87bfa838
Create Date: 2026-02-27 17:27:22.806215

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e59128ff07fd"
down_revision: str | Sequence[str] | None = "a6ad87bfa838"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Portable JSON type: JSONB on PostgreSQL, plain JSON elsewhere
JSONVariant = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # --- New tables (idempotent) ---

    if not inspector.has_table("seed_validation_reports"):
        op.create_table(
            "seed_validation_reports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("run_group_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("n_seeds", sa.Integer(), nullable=False),
            sa.Column("metric_distributions", JSONVariant, nullable=False),
            sa.Column("gate_passed", sa.Boolean(), nullable=False),
            sa.Column("gate_details", JSONVariant, nullable=False),
            sa.Column("selected_seed", sa.Integer(), nullable=True),
            sa.Column("previous_comparison", JSONVariant, nullable=True),
            sa.Column("environment_snapshot", JSONVariant, nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_seed_validation_reports_run_group_id"),
            "seed_validation_reports",
            ["run_group_id"],
            unique=True,
        )

    if not inspector.has_table("reproducibility_audits"):
        op.create_table(
            "reproducibility_audits",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pipeline_stage", sa.String(length=50), nullable=False),
            sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("config_hash", sa.String(length=64), nullable=False),
            sa.Column("environment_snapshot", JSONVariant, nullable=False),
            sa.Column("input_data_hash", sa.String(length=64), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_reproducibility_audits_pipeline_stage"),
            "reproducibility_audits",
            ["pipeline_stage"],
            unique=False,
        )

    # --- New columns on existing tables (idempotent) ---

    existing_ml = [c["name"] for c in inspector.get_columns("ml_model_runs")]
    if "seed" not in existing_ml:
        op.add_column(
            "ml_model_runs",
            sa.Column("seed", sa.Integer(), nullable=False, server_default="42"),
        )
    if "run_group_id" not in existing_ml:
        op.add_column(
            "ml_model_runs",
            sa.Column("run_group_id", sa.String(length=36), nullable=True),
        )
        op.create_index(
            op.f("ix_ml_model_runs_run_group_id"),
            "ml_model_runs",
            ["run_group_id"],
            unique=False,
        )

    existing_bt = [c["name"] for c in inspector.get_columns("backtest_runs")]
    if "seed" not in existing_bt:
        op.add_column(
            "backtest_runs",
            sa.Column("seed", sa.Integer(), nullable=True),
        )
    if "environment_snapshot" not in existing_bt:
        op.add_column(
            "backtest_runs",
            sa.Column("environment_snapshot", JSONVariant, nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("backtest_runs", "environment_snapshot")
    op.drop_column("backtest_runs", "seed")
    op.drop_index(op.f("ix_ml_model_runs_run_group_id"), table_name="ml_model_runs")
    op.drop_column("ml_model_runs", "run_group_id")
    op.drop_column("ml_model_runs", "seed")
    op.drop_index(
        op.f("ix_seed_validation_reports_run_group_id"),
        table_name="seed_validation_reports",
    )
    op.drop_table("seed_validation_reports")
    op.drop_index(
        op.f("ix_reproducibility_audits_pipeline_stage"),
        table_name="reproducibility_audits",
    )
    op.drop_table("reproducibility_audits")
