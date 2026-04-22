"""add risk diffing tables

Revision ID: b8633f3bb979
Revises: a2b3c4d5e6f7
Create Date: 2026-04-21 21:22:30.440310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b8633f3bb979"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONVariant = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Create risk_factor_analyses, risk_factor_embeddings, and llm_call_log tables."""
    op.create_table(
        "risk_factor_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("filing_text_id", sa.Integer(), sa.ForeignKey("filing_texts.id"), nullable=False),
        sa.Column(
            "prior_filing_text_id",
            sa.Integer(),
            sa.ForeignKey("filing_texts.id"),
            nullable=False,
        ),
        sa.Column("filing_accession", sa.String(length=25), nullable=True),
        sa.Column("prior_filing_accession", sa.String(length=25), nullable=True),
        sa.Column("material_changes", JSONVariant, nullable=True),
        sa.Column("overall_risk_delta_score", sa.Float(), nullable=True),
        sa.Column("model_confidence", sa.Float(), nullable=True),
        sa.Column("analysis_tokens_used", sa.Integer(), nullable=True),
        sa.Column("analysis_cost_usd", sa.Float(), nullable=True),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("embedding_model", sa.String(length=50), nullable=True),
        sa.Column("analysis_model", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "ticker",
            "filing_text_id",
            "prompt_version",
            name="uq_risk_analysis_ticker_filing_version",
        ),
    )
    op.create_index(
        "ix_risk_factor_analyses_ticker", "risk_factor_analyses", ["ticker"], unique=False
    )
    op.create_index(
        "ix_risk_factor_analyses_filing_text_id",
        "risk_factor_analyses",
        ["filing_text_id"],
        unique=False,
    )

    op.create_table(
        "risk_factor_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filing_text_id", sa.Integer(), sa.ForeignKey("filing_texts.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", JSONVariant, nullable=False),
        sa.Column("embedding_model", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "filing_text_id",
            "chunk_index",
            name="uq_risk_embedding_filing_chunk",
        ),
    )
    op.create_index(
        "ix_risk_factor_embeddings_filing_text_id",
        "risk_factor_embeddings",
        ["filing_text_id"],
        unique=False,
    )

    op.create_table(
        "llm_call_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service", sa.String(length=50), nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=True),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("response_json", JSONVariant, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_llm_call_log_service_version_created",
        "llm_call_log",
        ["service", "prompt_version", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop risk_factor_analyses, risk_factor_embeddings, and llm_call_log tables."""
    op.drop_index("ix_llm_call_log_service_version_created", table_name="llm_call_log")
    op.drop_table("llm_call_log")
    op.drop_index(
        "ix_risk_factor_embeddings_filing_text_id", table_name="risk_factor_embeddings"
    )
    op.drop_table("risk_factor_embeddings")
    op.drop_index("ix_risk_factor_analyses_filing_text_id", table_name="risk_factor_analyses")
    op.drop_index("ix_risk_factor_analyses_ticker", table_name="risk_factor_analyses")
    op.drop_table("risk_factor_analyses")
