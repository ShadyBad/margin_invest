"""add v4_scores table and ml_model_runs columns

Revision ID: 5953a89f8035
Revises: 401504d7e26d
Create Date: 2026-02-22 22:38:02.970836

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5953a89f8035"
down_revision: str | Sequence[str] | None = "401504d7e26d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create v4_scores table
    jsonb_variant = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()), "postgresql"
    )
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
        "ix_v4_scores_asset_scored",
        "v4_scores",
        ["asset_id", "scored_at"],
        unique=False,
    )
    op.create_index(
        "ix_v4_scores_scored_at", "v4_scores", ["scored_at"], unique=False
    )

    # Add new columns to ml_model_runs
    op.add_column(
        "ml_model_runs",
        sa.Column(
            "model_qualifies",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "ml_model_runs",
        sa.Column("overall_rank_ic", sa.Float(), nullable=True),
    )
    op.add_column(
        "ml_model_runs",
        sa.Column("vae_rank_ic", sa.Float(), nullable=True),
    )
    op.add_column(
        "ml_model_runs",
        sa.Column("vae_artifact_path", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns from ml_model_runs
    op.drop_column("ml_model_runs", "vae_artifact_path")
    op.drop_column("ml_model_runs", "vae_rank_ic")
    op.drop_column("ml_model_runs", "overall_rank_ic")
    op.drop_column("ml_model_runs", "model_qualifies")

    # Drop v4_scores table
    op.drop_index("ix_v4_scores_scored_at", table_name="v4_scores")
    op.drop_index("ix_v4_scores_asset_scored", table_name="v4_scores")
    op.drop_index(op.f("ix_v4_scores_asset_id"), table_name="v4_scores")
    op.drop_table("v4_scores")
