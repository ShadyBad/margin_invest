"""add consistency_flags to financial_data

Revision ID: 7085e0ad6ae4
Revises: fec32c342579
Create Date: 2026-02-27 06:39:02.883194

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7085e0ad6ae4"
down_revision: str | Sequence[str] | None = "fec32c342579"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add consistency_flags JSONB column to financial_data."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table("financial_data"):
        existing = [c["name"] for c in inspector.get_columns("financial_data")]
        if "consistency_flags" not in existing:
            op.add_column(
                "financial_data",
                sa.Column("consistency_flags", sa.JSON(), nullable=True),
            )


def downgrade() -> None:
    """Remove consistency_flags column from financial_data."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table("financial_data"):
        existing = [c["name"] for c in inspector.get_columns("financial_data")]
        if "consistency_flags" in existing:
            op.drop_column("financial_data", "consistency_flags")
