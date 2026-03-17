"""add error_message to backtest_runs

Revision ID: 29c44530fc6f
Revises: 30f977239bf3
Create Date: 2026-03-16 23:27:24.552678

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '29c44530fc6f'
down_revision: Union[str, Sequence[str], None] = '30f977239bf3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add error_message column to backtest_runs (idempotent)."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = [c["name"] for c in inspector.get_columns("backtest_runs")]
    if "error_message" not in existing:
        op.add_column("backtest_runs", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove error_message column from backtest_runs."""
    op.drop_column("backtest_runs", "error_message")
