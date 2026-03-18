"""add sentiment_signals table

Revision ID: e6b3b726a431
Revises: 059d47ea33c5
Create Date: 2026-03-18 14:48:31.160491

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e6b3b726a431"
down_revision: str | Sequence[str] | None = "059d47ea33c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sentiment_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("signal_date", sa.Date(), nullable=False),
        sa.Column("short_interest_pct", sa.Float(), nullable=True),
        sa.Column(
            "analyst_consensus",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("eps_revision_direction", sa.Float(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "signal_date", name="uq_sentiment_ticker_date"),
    )
    op.create_index(
        op.f("ix_sentiment_signals_ticker"), "sentiment_signals", ["ticker"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_sentiment_signals_ticker"), table_name="sentiment_signals")
    op.drop_table("sentiment_signals")
