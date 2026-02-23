"""add missing columns tickers_partial circuit_breaker_trips provider_stats to ingestion_runs

Revision ID: 401504d7e26d
Revises: a8f1c2d3e4f5
Create Date: 2026-02-22 19:49:39.625578

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "401504d7e26d"
down_revision: str | Sequence[str] | None = "a8f1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {c["name"] for c in inspector.get_columns("ingestion_runs")}

    if "tickers_partial" not in existing:
        op.add_column(
            "ingestion_runs",
            sa.Column("tickers_partial", sa.Integer(), nullable=False, server_default="0"),
        )
    if "circuit_breaker_trips" not in existing:
        op.add_column(
            "ingestion_runs",
            sa.Column("circuit_breaker_trips", sa.Integer(), nullable=False, server_default="0"),
        )
    if "provider_stats" not in existing:
        op.add_column(
            "ingestion_runs",
            sa.Column("provider_stats", JSONB(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("ingestion_runs", "provider_stats")
    op.drop_column("ingestion_runs", "circuit_breaker_trips")
    op.drop_column("ingestion_runs", "tickers_partial")
