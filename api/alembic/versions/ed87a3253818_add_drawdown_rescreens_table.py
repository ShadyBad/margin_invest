"""add drawdown_rescreens table

Revision ID: ed87a3253818
Revises: b19b2beed222
Create Date: 2026-03-19 06:49:29.930970

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "ed87a3253818"
down_revision: Union[str, Sequence[str], None] = "b19b2beed222"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — create drawdown_rescreens table if not exists."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    if "drawdown_rescreens" not in inspector.get_table_names():
        op.create_table(
            "drawdown_rescreens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("drawdown_pct", sa.Float(), nullable=False),
            sa.Column("high_price", sa.Float(), nullable=False),
            sa.Column("current_price", sa.Float(), nullable=False),
            sa.Column("trigger_date", sa.Date(), nullable=False),
            sa.Column("prior_conviction", sa.String(length=20), nullable=True),
            sa.Column("new_conviction", sa.String(length=20), nullable=True),
            sa.Column("outcome", sa.String(length=20), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_drawdown_rescreens_ticker"),
            "drawdown_rescreens",
            ["ticker"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema — drop drawdown_rescreens table."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    if "drawdown_rescreens" in inspector.get_table_names():
        op.drop_index(op.f("ix_drawdown_rescreens_ticker"), table_name="drawdown_rescreens")
        op.drop_table("drawdown_rescreens")
