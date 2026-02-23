"""add model bytes columns to ml_model_runs

Revision ID: c8d9e0f1a2b3
Revises: b7c3d4e5f6a7
Create Date: 2026-02-23 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'b7c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cluster_model_data and vae_model_data to ml_model_runs."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns("ml_model_runs")}

    if "cluster_model_data" not in existing:
        op.add_column(
            "ml_model_runs",
            sa.Column("cluster_model_data", sa.LargeBinary(), nullable=True),
        )
    if "vae_model_data" not in existing:
        op.add_column(
            "ml_model_runs",
            sa.Column("vae_model_data", sa.LargeBinary(), nullable=True),
        )


def downgrade() -> None:
    """Remove model bytes columns from ml_model_runs."""
    op.drop_column("ml_model_runs", "vae_model_data")
    op.drop_column("ml_model_runs", "cluster_model_data")
