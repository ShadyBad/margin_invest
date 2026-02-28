"""add PIT tables for backtesting

Revision ID: d839373360f3
Revises: e59128ff07fd
Create Date: 2026-02-27 17:50:03.684283

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d839373360f3"
down_revision: str | Sequence[str] | None = "e59128ff07fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Portable JSON type: JSONB on PostgreSQL, plain JSON elsewhere
JSONVariant = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # --- New tables (idempotent) ---

    if not inspector.has_table("pit_financial_snapshots"):
        op.create_table(
            "pit_financial_snapshots",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("cik", sa.String(length=10), nullable=False),
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("filing_date", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("form_type", sa.String(length=10), nullable=False),
            sa.Column("accession_number", sa.String(length=30), nullable=False),
            sa.Column("income_statement", JSONVariant, nullable=True),
            sa.Column("balance_sheet", JSONVariant, nullable=True),
            sa.Column("cash_flow", JSONVariant, nullable=True),
            sa.Column("shares_outstanding", sa.BigInteger(), nullable=True),
            sa.Column("fiscal_year", sa.Integer(), nullable=False),
            sa.Column("fiscal_quarter", sa.Integer(), nullable=True),
            sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("accession_number"),
        )
        op.create_index(
            op.f("ix_pit_financial_snapshots_cik"),
            "pit_financial_snapshots",
            ["cik"],
            unique=False,
        )
        op.create_index(
            op.f("ix_pit_financial_snapshots_ticker"),
            "pit_financial_snapshots",
            ["ticker"],
            unique=False,
        )
        op.create_index(
            op.f("ix_pit_financial_snapshots_filing_date"),
            "pit_financial_snapshots",
            ["filing_date"],
            unique=False,
        )
        op.create_index(
            "ix_pit_financial_ticker_filing_date",
            "pit_financial_snapshots",
            ["ticker", "filing_date"],
            unique=False,
        )

    if not inspector.has_table("pit_daily_prices"):
        op.create_table(
            "pit_daily_prices",
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("open", sa.Float(), nullable=False),
            sa.Column("high", sa.Float(), nullable=False),
            sa.Column("low", sa.Float(), nullable=False),
            sa.Column("close", sa.Float(), nullable=False),
            sa.Column("adj_close", sa.Float(), nullable=False),
            sa.Column("volume", sa.BigInteger(), nullable=False),
            sa.Column("source", sa.String(length=20), nullable=False),
            sa.PrimaryKeyConstraint("ticker", "date"),
        )

    if not inspector.has_table("pit_universe_memberships"):
        op.create_table(
            "pit_universe_memberships",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("cik", sa.String(length=10), nullable=False),
            sa.Column("quarter_date", sa.Date(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("market_cap", sa.Float(), nullable=True),
            sa.Column("last_filing_date", sa.Date(), nullable=True),
            sa.Column("delist_detected_at", sa.Date(), nullable=True),
            sa.Column("last_known_price", sa.Float(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("ticker", "quarter_date", name="uq_pit_universe_ticker_quarter"),
        )
        op.create_index(
            op.f("ix_pit_universe_memberships_ticker"),
            "pit_universe_memberships",
            ["ticker"],
            unique=False,
        )
        op.create_index(
            "ix_pit_universe_quarter_date",
            "pit_universe_memberships",
            ["quarter_date"],
            unique=False,
        )

    # --- New column on existing table (idempotent) ---

    existing_bt = [c["name"] for c in inspector.get_columns("backtest_runs")]
    if "pit_data_version" not in existing_bt:
        op.add_column(
            "backtest_runs",
            sa.Column("pit_data_version", sa.String(length=64), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("backtest_runs", "pit_data_version")

    op.drop_index("ix_pit_universe_quarter_date", table_name="pit_universe_memberships")
    op.drop_index(op.f("ix_pit_universe_memberships_ticker"), table_name="pit_universe_memberships")
    op.drop_table("pit_universe_memberships")

    op.drop_table("pit_daily_prices")

    op.drop_index("ix_pit_financial_ticker_filing_date", table_name="pit_financial_snapshots")
    op.drop_index(op.f("ix_pit_financial_snapshots_ticker"), table_name="pit_financial_snapshots")
    op.drop_index(
        op.f("ix_pit_financial_snapshots_filing_date"), table_name="pit_financial_snapshots"
    )
    op.drop_index(op.f("ix_pit_financial_snapshots_cik"), table_name="pit_financial_snapshots")
    op.drop_table("pit_financial_snapshots")
