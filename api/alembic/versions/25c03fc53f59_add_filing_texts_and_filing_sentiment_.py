"""add filing_texts and filing_sentiment_cache

Revision ID: 25c03fc53f59
Revises: ed87a3253818
Create Date: 2026-03-19 07:03:27.273963

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "25c03fc53f59"
down_revision: Union[str, Sequence[str], None] = "ed87a3253818"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONVariant = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Upgrade schema — create filing_texts and filing_sentiment_cache tables if not exists."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing = inspector.get_table_names()

    if "filing_texts" not in existing:
        op.create_table(
            "filing_texts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("cik", sa.String(length=20), nullable=False),
            sa.Column("filing_type", sa.String(length=10), nullable=False),
            sa.Column("filing_date", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("business_text", sa.Text(), nullable=True),
            sa.Column("risk_factors_text", sa.Text(), nullable=True),
            sa.Column("mda_text", sa.Text(), nullable=True),
            sa.Column("raw_html_hash", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "ticker",
                "filing_type",
                "period_end",
                name="uq_filing_text_ticker_type_period",
            ),
        )
        op.create_index(
            op.f("ix_filing_texts_ticker"), "filing_texts", ["ticker"], unique=False
        )

    if "filing_sentiment_cache" not in existing:
        op.create_table(
            "filing_sentiment_cache",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("filing_text_id", sa.Integer(), nullable=False),
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("analysis_version", sa.String(length=10), nullable=False),
            sa.Column("prompt_hash", sa.String(length=64), nullable=False),
            sa.Column("sentiment_value", sa.Float(), nullable=True),
            sa.Column("moat_signals", JSONVariant, nullable=True),
            sa.Column("risk_flags", JSONVariant, nullable=True),
            sa.Column("management_quality", JSONVariant, nullable=True),
            sa.Column("competitive_position", JSONVariant, nullable=True),
            sa.Column("segment_revenue", JSONVariant, nullable=True),
            sa.Column("model_used", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["filing_text_id"],
                ["filing_texts.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "filing_text_id",
                "analysis_version",
                name="uq_filing_sentiment_filing_version",
            ),
        )
        op.create_index(
            op.f("ix_filing_sentiment_cache_filing_text_id"),
            "filing_sentiment_cache",
            ["filing_text_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_filing_sentiment_cache_ticker"),
            "filing_sentiment_cache",
            ["ticker"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema — drop filing_sentiment_cache and filing_texts tables."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing = inspector.get_table_names()

    if "filing_sentiment_cache" in existing:
        op.drop_index(
            op.f("ix_filing_sentiment_cache_ticker"), table_name="filing_sentiment_cache"
        )
        op.drop_index(
            op.f("ix_filing_sentiment_cache_filing_text_id"),
            table_name="filing_sentiment_cache",
        )
        op.drop_table("filing_sentiment_cache")

    if "filing_texts" in existing:
        op.drop_index(op.f("ix_filing_texts_ticker"), table_name="filing_texts")
        op.drop_table("filing_texts")
