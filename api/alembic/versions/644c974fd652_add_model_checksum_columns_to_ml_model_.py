"""add model checksum columns to ml_model_runs

Revision ID: 644c974fd652
Revises: e10ea8524fbf
Create Date: 2026-02-26 00:22:29.852064

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "644c974fd652"
down_revision: str | Sequence[str] | None = "e10ea8524fbf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add SHA-256 checksum columns for model integrity verification."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table("ml_model_runs"):
        existing = [c["name"] for c in inspector.get_columns("ml_model_runs")]
        if "cluster_model_checksum" not in existing:
            op.add_column(
                "ml_model_runs",
                sa.Column("cluster_model_checksum", sa.String(64), nullable=True),
            )
        if "vae_model_checksum" not in existing:
            op.add_column(
                "ml_model_runs",
                sa.Column("vae_model_checksum", sa.String(64), nullable=True),
            )


def downgrade() -> None:
    """Remove checksum columns."""
    op.drop_column("ml_model_runs", "vae_model_checksum")
    op.drop_column("ml_model_runs", "cluster_model_checksum")
