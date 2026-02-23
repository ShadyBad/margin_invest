"""add data_categories_present to financial_data

Revision ID: b7c3d4e5f6a7
Revises: 401504d7e26d
Create Date: 2026-02-23 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'b7c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = '401504d7e26d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add data_categories_present column to financial_data."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns("financial_data")}

    if "data_categories_present" not in existing:
        op.add_column(
            "financial_data",
            sa.Column("data_categories_present", JSONB(), nullable=True),
        )


def downgrade() -> None:
    """Remove data_categories_present column from financial_data."""
    op.drop_column("financial_data", "data_categories_present")
