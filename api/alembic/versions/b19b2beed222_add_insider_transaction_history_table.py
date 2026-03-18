"""add insider_transaction_history table

Revision ID: b19b2beed222
Revises: e6b3b726a431
Create Date: 2026-03-18 14:50:22.101846

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = "b19b2beed222"
down_revision: str | Sequence[str] | None = "e6b3b726a431"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create insider_transaction_history table."""
    conn = op.get_bind()
    inspector = sa_inspect(conn)

    if not inspector.has_table("insider_transaction_history"):
        op.create_table(
            "insider_transaction_history",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("cik", sa.String(length=10), nullable=False),
            sa.Column("insider_cik", sa.String(length=10), nullable=False),
            sa.Column("insider_name", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("transaction_type", sa.String(length=10), nullable=False),
            sa.Column("transaction_date", sa.Date(), nullable=False),
            sa.Column("shares", sa.BigInteger(), nullable=False),
            sa.Column("price_per_share", sa.Float(), nullable=True),
            sa.Column("total_value", sa.Float(), nullable=True),
            sa.Column("accession_number", sa.String(length=30), nullable=False),
            sa.Column("filing_date", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "accession_number",
                "insider_cik",
                "transaction_date",
                name="uq_insider_accession_cik_date",
            ),
        )
        op.create_index(
            op.f("ix_insider_transaction_history_ticker"),
            "insider_transaction_history",
            ["ticker"],
            unique=False,
        )
        op.create_index(
            "ix_insider_hist_insider",
            "insider_transaction_history",
            ["insider_cik", "ticker"],
            unique=False,
        )


def downgrade() -> None:
    """Drop insider_transaction_history table."""
    op.drop_index(
        "ix_insider_hist_insider",
        table_name="insider_transaction_history",
    )
    op.drop_index(
        op.f("ix_insider_transaction_history_ticker"),
        table_name="insider_transaction_history",
    )
    op.drop_table("insider_transaction_history")
