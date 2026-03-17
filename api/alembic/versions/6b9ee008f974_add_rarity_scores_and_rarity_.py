"""add rarity_scores and rarity_distribution_snapshots tables

Revision ID: 6b9ee008f974
Revises: 30f977239bf3
Create Date: 2026-03-16 23:21:42.575049

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6b9ee008f974"
down_revision: str | Sequence[str] | None = "30f977239bf3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "rarity_distribution_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False),
        sa.Column("factor_name", sa.String(length=50), nullable=False),
        sa.Column("n_obs", sa.Integer(), nullable=False),
        sa.Column(
            "percentiles",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("mean", sa.Float(), nullable=False),
        sa.Column("std", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_rarity_distribution_snapshots_scored_at"),
        "rarity_distribution_snapshots",
        ["scored_at"],
        unique=False,
    )
    op.create_table(
        "rarity_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rarity_score", sa.Float(), nullable=False),
        sa.Column("joint_rarity_pctl", sa.Float(), nullable=False),
        sa.Column("convergence_score", sa.Float(), nullable=False),
        sa.Column("historical_frequency", sa.Float(), nullable=False),
        sa.Column("quality_momentum", sa.Float(), nullable=False),
        sa.Column("smart_money_score", sa.Float(), nullable=False),
        sa.Column("regime_alignment", sa.Float(), nullable=False),
        sa.Column("combination_signature", sa.String(length=30), nullable=False),
        sa.Column("regime", sa.String(length=20), nullable=False),
        sa.Column("conviction_score", sa.Float(), nullable=False),
        sa.Column("is_generational", sa.Boolean(), nullable=False),
        sa.Column(
            "detail",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("universe_size", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rarity_scores_asset_id"), "rarity_scores", ["asset_id"], unique=False)
    op.create_index(
        "ix_rarity_scores_asset_scored",
        "rarity_scores",
        ["asset_id", "scored_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rarity_scores_scored_at"), "rarity_scores", ["scored_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_rarity_scores_scored_at"), table_name="rarity_scores")
    op.drop_index("ix_rarity_scores_asset_scored", table_name="rarity_scores")
    op.drop_index(op.f("ix_rarity_scores_asset_id"), table_name="rarity_scores")
    op.drop_table("rarity_scores")
    op.drop_index(
        op.f("ix_rarity_distribution_snapshots_scored_at"),
        table_name="rarity_distribution_snapshots",
    )
    op.drop_table("rarity_distribution_snapshots")
