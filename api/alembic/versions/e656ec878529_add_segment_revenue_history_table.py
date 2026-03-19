"""add_segment_revenue_history_table

Revision ID: e656ec878529
Revises: 25c03fc53f59
Create Date: 2026-03-19 07:22:43.218495

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "e656ec878529"
down_revision: str | Sequence[str] | None = "25c03fc53f59"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema — create segment_revenue_history table if not exists."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing = inspector.get_table_names()

    if "segment_revenue_history" not in existing:
        op.create_table(
            "segment_revenue_history",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("filing_date", sa.Date(), nullable=False),
            sa.Column("segment_name", sa.String(length=200), nullable=False),
            sa.Column("segment_type", sa.String(length=20), nullable=False),
            sa.Column("revenue", sa.Float(), nullable=False),
            sa.Column("source", sa.String(length=10), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "ticker",
                "filing_date",
                "segment_name",
                name="uq_segment_revenue_ticker_date_segment",
            ),
        )
        op.create_index(
            op.f("ix_segment_revenue_history_ticker"),
            "segment_revenue_history",
            ["ticker"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema — drop segment_revenue_history table."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing = inspector.get_table_names()

    if "segment_revenue_history" in existing:
        op.drop_index(
            op.f("ix_segment_revenue_history_ticker"),
            table_name="segment_revenue_history",
        )
        op.drop_table("segment_revenue_history")
