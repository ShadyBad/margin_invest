"""add model bytes columns to ml_model_runs

Revision ID: c8d9e0f1a2b3
Revises: b7c3d4e5f6a7
Create Date: 2026-02-23 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'b7c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create missing tables and add model bytes columns.

    Migration 5953a89f8035 was skipped in production due to a branch fork,
    so we handle creating v4_scores and ml_model_runs here if they don't exist.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    jsonb_variant = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()), "postgresql"
    )

    # --- v4_scores table (from skipped 5953a89f8035) ---
    if "v4_scores" not in existing_tables:
        op.create_table(
            "v4_scores",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("asset_id", sa.Integer(), nullable=False),
            sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("opportunity_type", sa.String(length=30), nullable=False),
            sa.Column("conviction", sa.String(length=20), nullable=False),
            sa.Column("rules_conviction", sa.String(length=20), nullable=False),
            sa.Column("track_a", jsonb_variant, nullable=True),
            sa.Column("track_b", jsonb_variant, nullable=True),
            sa.Column("track_c", jsonb_variant, nullable=True),
            sa.Column("style", sa.String(length=10), nullable=False),
            sa.Column("timing_signal", sa.String(length=30), nullable=False),
            sa.Column("max_position_pct", sa.Float(), nullable=False),
            sa.Column("regime", sa.String(length=20), nullable=False),
            sa.Column("composite_score", sa.Float(), nullable=False),
            sa.Column("ml_alpha", sa.Float(), nullable=True),
            sa.Column("ml_confidence", sa.Float(), nullable=True),
            sa.Column("ml_override", sa.String(length=20), nullable=False),
            sa.Column("detail", jsonb_variant, nullable=True),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_v4_scores_asset_id"), "v4_scores", ["asset_id"], unique=False
        )
        op.create_index(
            "ix_v4_scores_asset_scored", "v4_scores", ["asset_id", "scored_at"], unique=False
        )
        op.create_index(
            "ix_v4_scores_scored_at", "v4_scores", ["scored_at"], unique=False
        )

    # --- ml_model_runs table (never had a CREATE TABLE migration) ---
    if "ml_model_runs" not in existing_tables:
        op.create_table(
            "ml_model_runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("model_type", sa.String(length=50), nullable=False),
            sa.Column("n_clusters", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("n_features", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("n_samples", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("train_metrics", jsonb_variant, nullable=True),
            sa.Column("artifact_path", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("model_qualifies", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("overall_rank_ic", sa.Float(), nullable=True),
            sa.Column("vae_rank_ic", sa.Float(), nullable=True),
            sa.Column("vae_artifact_path", sa.String(length=500), nullable=True),
            sa.Column("cluster_model_data", sa.LargeBinary(), nullable=True),
            sa.Column("vae_model_data", sa.LargeBinary(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        # Table exists — add any missing columns
        existing_cols = {c["name"] for c in inspector.get_columns("ml_model_runs")}

        # Columns from skipped 5953a89f8035
        if "model_qualifies" not in existing_cols:
            op.add_column(
                "ml_model_runs",
                sa.Column("model_qualifies", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
        if "overall_rank_ic" not in existing_cols:
            op.add_column("ml_model_runs", sa.Column("overall_rank_ic", sa.Float(), nullable=True))
        if "vae_rank_ic" not in existing_cols:
            op.add_column("ml_model_runs", sa.Column("vae_rank_ic", sa.Float(), nullable=True))
        if "vae_artifact_path" not in existing_cols:
            op.add_column("ml_model_runs", sa.Column("vae_artifact_path", sa.String(length=500), nullable=True))

        # New columns from this migration
        if "cluster_model_data" not in existing_cols:
            op.add_column("ml_model_runs", sa.Column("cluster_model_data", sa.LargeBinary(), nullable=True))
        if "vae_model_data" not in existing_cols:
            op.add_column("ml_model_runs", sa.Column("vae_model_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    """Remove model bytes columns and tables created by this migration."""
    op.drop_column("ml_model_runs", "vae_model_data")
    op.drop_column("ml_model_runs", "cluster_model_data")
