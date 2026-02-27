"""add correction_events and sector_distribution_snapshots

Revision ID: 874a8844567a
Revises: 7085e0ad6ae4
Create Date: 2026-02-27 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "874a8844567a"
down_revision: str | Sequence[str] | None = "7085e0ad6ae4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create correction_events and sector_distribution_snapshots tables."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    jsonb_variant = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

    # -- correction_events ----------------------------------------------------
    if not inspector.has_table("correction_events"):
        op.create_table(
            "correction_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("correction_id", sa.String(length=36), nullable=False),
            sa.Column("asset_id", sa.Integer(), nullable=False),
            sa.Column("period_end", sa.String(length=10), nullable=False),
            sa.Column("field_path", sa.String(length=100), nullable=False),
            sa.Column("detection_tier", sa.String(length=20), nullable=False),
            sa.Column("detection_detail", sa.String(length=500), nullable=False),
            sa.Column("original_value", sa.Float(), nullable=True),
            sa.Column("corrected_value", sa.Float(), nullable=False),
            sa.Column("correction_method", sa.String(length=30), nullable=False),
            sa.Column("correction_source", sa.String(length=100), nullable=False),
            sa.Column("correction_confidence", sa.Float(), nullable=False),
            sa.Column("correction_config_version", sa.String(length=20), nullable=False),
            sa.Column("sector_distribution_snapshot", jsonb_variant, nullable=True),
            sa.Column("scoring_run_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("correction_id"),
        )
        op.create_index(
            op.f("ix_correction_events_correction_id"),
            "correction_events",
            ["correction_id"],
            unique=True,
        )
        op.create_index(
            op.f("ix_correction_events_asset_id"),
            "correction_events",
            ["asset_id"],
            unique=False,
        )

    # -- sector_distribution_snapshots ----------------------------------------
    if not inspector.has_table("sector_distribution_snapshots"):
        op.create_table(
            "sector_distribution_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("scoring_run_id", sa.String(length=36), nullable=False),
            sa.Column("sector", sa.String(length=50), nullable=False),
            sa.Column("field_path", sa.String(length=100), nullable=False),
            sa.Column("median", sa.Float(), nullable=False),
            sa.Column("mad", sa.Float(), nullable=False),
            sa.Column("n_observations", sa.Integer(), nullable=False),
            sa.Column("period", sa.String(length=10), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_sector_distribution_snapshots_scoring_run_id"),
            "sector_distribution_snapshots",
            ["scoring_run_id"],
            unique=False,
        )


def downgrade() -> None:
    """Drop correction_events and sector_distribution_snapshots tables."""
    op.drop_index(
        op.f("ix_sector_distribution_snapshots_scoring_run_id"),
        table_name="sector_distribution_snapshots",
    )
    op.drop_table("sector_distribution_snapshots")

    op.drop_index(
        op.f("ix_correction_events_asset_id"),
        table_name="correction_events",
    )
    op.drop_index(
        op.f("ix_correction_events_correction_id"),
        table_name="correction_events",
    )
    op.drop_table("correction_events")
