"""add historical_scores table

Revision ID: 30f977239bf3
Revises: 19217ac20a10
Create Date: 2026-03-15 12:16:17.391375

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from margin_api.db.models import JSONVariant

# revision identifiers, used by Alembic.
revision: str = "30f977239bf3"
down_revision: str | Sequence[str] | None = "19217ac20a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(bind, table: str) -> bool:
    """Check if a table exists (idempotent guard)."""
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :table AND table_schema = 'public'"
        ),
        {"table": table},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if _has_table(bind, "historical_scores"):
        return

    op.create_table(
        "historical_scores",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("score_date", sa.Date(), nullable=False),
        sa.Column("composite_score", sa.Float(), nullable=False),
        sa.Column("composite_tier", sa.String(length=20), nullable=False),
        sa.Column("sub_scores", JSONVariant, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "score_date", name="uq_historical_score_ticker_date"),
    )
    op.create_index("ix_historical_scores_ticker", "historical_scores", ["ticker"])
    op.create_index("ix_historical_scores_score_date", "historical_scores", ["score_date"])


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    if not _has_table(bind, "historical_scores"):
        return

    op.drop_index("ix_historical_scores_score_date", table_name="historical_scores")
    op.drop_index("ix_historical_scores_ticker", table_name="historical_scores")
    op.drop_table("historical_scores")
