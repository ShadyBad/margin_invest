"""add 13F institutional holdings tables

Revision ID: e10ea8524fbf
Revises: f59558225e67
Create Date: 2026-02-25 08:33:21.038757

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e10ea8524fbf"
down_revision: str | Sequence[str] | None = "f59558225e67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create 13F institutional holdings tables and add cusip to assets."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    jsonb_variant = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()), "postgresql"
    )

    # -- managers -------------------------------------------------------------
    if not inspector.has_table("managers"):
        op.create_table(
            "managers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cik", sa.String(length=10), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("short_name", sa.Text(), nullable=True),
            sa.Column("tier", sa.String(length=20), nullable=False),
            sa.Column("aum_latest", sa.BigInteger(), nullable=True),
            sa.Column(
                "active",
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=False,
            ),
            sa.Column("first_filing_date", sa.Date(), nullable=True),
            sa.Column("last_filing_date", sa.Date(), nullable=True),
            sa.Column("metadata", jsonb_variant, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_managers_cik"), "managers", ["cik"], unique=True)

    # -- security_master ------------------------------------------------------
    if not inspector.has_table("security_master"):
        op.create_table(
            "security_master",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cusip", sa.String(length=9), nullable=False),
            sa.Column("ticker", sa.String(length=10), nullable=True),
            sa.Column("figi", sa.String(length=12), nullable=True),
            sa.Column("issuer_name", sa.Text(), nullable=False),
            sa.Column("security_name", sa.Text(), nullable=True),
            sa.Column("asset_id", sa.Integer(), nullable=True),
            sa.Column("resolution_method", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_security_master_asset_id"),
            "security_master",
            ["asset_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_security_master_cusip"),
            "security_master",
            ["cusip"],
            unique=True,
        )
        op.create_index(
            op.f("ix_security_master_ticker"),
            "security_master",
            ["ticker"],
            unique=False,
        )

    # -- filing_metadata ------------------------------------------------------
    if not inspector.has_table("filing_metadata"):
        op.create_table(
            "filing_metadata",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("manager_id", sa.Integer(), nullable=False),
            sa.Column("accession_number", sa.String(length=25), nullable=False),
            sa.Column("filing_type", sa.String(length=15), nullable=False),
            sa.Column("period_of_report", sa.Date(), nullable=False),
            sa.Column("filed_date", sa.Date(), nullable=False),
            sa.Column("total_value", sa.BigInteger(), nullable=True),
            sa.Column("total_holdings", sa.Integer(), nullable=True),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("is_amendment", sa.Boolean(), nullable=False),
            sa.Column("supersedes_id", sa.Integer(), nullable=True),
            sa.Column("ingestion_run_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["ingestion_run_id"], ["job_runs.id"]),
            sa.ForeignKeyConstraint(["manager_id"], ["managers.id"]),
            sa.ForeignKeyConstraint(["supersedes_id"], ["filing_metadata.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("accession_number"),
        )
        op.create_index(
            "ix_filing_manager_period",
            "filing_metadata",
            ["manager_id", "period_of_report"],
            unique=False,
        )
        op.create_index(
            op.f("ix_filing_metadata_manager_id"),
            "filing_metadata",
            ["manager_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_filing_metadata_period_of_report"),
            "filing_metadata",
            ["period_of_report"],
            unique=False,
        )

    # -- institutional_holdings -----------------------------------------------
    if not inspector.has_table("institutional_holdings"):
        op.create_table(
            "institutional_holdings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("filing_id", sa.Integer(), nullable=False),
            sa.Column("manager_id", sa.Integer(), nullable=False),
            sa.Column("security_master_id", sa.Integer(), nullable=False),
            sa.Column("cusip", sa.String(length=9), nullable=False),
            sa.Column("period_of_report", sa.Date(), nullable=False),
            sa.Column("shares_held", sa.BigInteger(), nullable=False),
            sa.Column("value_thousands", sa.BigInteger(), nullable=False),
            sa.Column("put_call", sa.String(length=10), nullable=False),
            sa.Column("investment_discretion", sa.String(length=10), nullable=True),
            sa.Column("voting_authority_sole", sa.BigInteger(), nullable=True),
            sa.Column("voting_authority_shared", sa.BigInteger(), nullable=True),
            sa.Column("voting_authority_none", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["filing_id"], ["filing_metadata.id"]),
            sa.ForeignKeyConstraint(["manager_id"], ["managers.id"]),
            sa.ForeignKeyConstraint(["security_master_id"], ["security_master.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "filing_id", "cusip", "put_call", name="uq_holding_filing_cusip_putcall"
            ),
        )
        op.create_index(
            "ix_holding_cusip_period",
            "institutional_holdings",
            ["cusip", "period_of_report"],
            unique=False,
        )
        op.create_index(
            "ix_holding_manager_period",
            "institutional_holdings",
            ["manager_id", "period_of_report"],
            unique=False,
        )
        op.create_index(
            "ix_holding_secmaster_period",
            "institutional_holdings",
            ["security_master_id", "period_of_report"],
            unique=False,
        )
        op.create_index(
            op.f("ix_institutional_holdings_filing_id"),
            "institutional_holdings",
            ["filing_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_institutional_holdings_manager_id"),
            "institutional_holdings",
            ["manager_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_institutional_holdings_security_master_id"),
            "institutional_holdings",
            ["security_master_id"],
            unique=False,
        )

    # -- accumulation_signals -------------------------------------------------
    if not inspector.has_table("accumulation_signals"):
        op.create_table(
            "accumulation_signals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("asset_id", sa.Integer(), nullable=False),
            sa.Column("period_of_report", sa.Date(), nullable=False),
            sa.Column("curated_holders", sa.Integer(), nullable=False),
            sa.Column("total_holders", sa.Integer(), nullable=False),
            sa.Column("curated_new_positions", sa.Integer(), nullable=False),
            sa.Column("total_new_positions", sa.Integer(), nullable=False),
            sa.Column("curated_net_shares", sa.BigInteger(), nullable=False),
            sa.Column("total_net_shares", sa.BigInteger(), nullable=False),
            sa.Column("signal_score", sa.Float(), nullable=False),
            sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "asset_id", "period_of_report", name="uq_accumulation_asset_period"
            ),
        )
        op.create_index(
            op.f("ix_accumulation_signals_asset_id"),
            "accumulation_signals",
            ["asset_id"],
            unique=False,
        )

    # -- cusip column on assets -----------------------------------------------
    existing_columns = [c["name"] for c in inspector.get_columns("assets")]
    if "cusip" not in existing_columns:
        op.add_column("assets", sa.Column("cusip", sa.String(length=9), nullable=True))
        op.create_index(op.f("ix_assets_cusip"), "assets", ["cusip"], unique=False)


def downgrade() -> None:
    """Drop 13F tables and cusip column in reverse dependency order."""
    # -- cusip column on assets -----------------------------------------------
    op.drop_index(op.f("ix_assets_cusip"), table_name="assets")
    op.drop_column("assets", "cusip")

    # -- institutional_holdings (depends on filing_metadata, managers, security_master)
    op.drop_index(
        op.f("ix_institutional_holdings_security_master_id"),
        table_name="institutional_holdings",
    )
    op.drop_index(
        op.f("ix_institutional_holdings_manager_id"),
        table_name="institutional_holdings",
    )
    op.drop_index(
        op.f("ix_institutional_holdings_filing_id"),
        table_name="institutional_holdings",
    )
    op.drop_index("ix_holding_secmaster_period", table_name="institutional_holdings")
    op.drop_index("ix_holding_manager_period", table_name="institutional_holdings")
    op.drop_index("ix_holding_cusip_period", table_name="institutional_holdings")
    op.drop_table("institutional_holdings")

    # -- filing_metadata (depends on managers, job_runs) ----------------------
    op.drop_index(
        op.f("ix_filing_metadata_period_of_report"), table_name="filing_metadata"
    )
    op.drop_index(op.f("ix_filing_metadata_manager_id"), table_name="filing_metadata")
    op.drop_index("ix_filing_manager_period", table_name="filing_metadata")
    op.drop_table("filing_metadata")

    # -- security_master (depends on assets) ----------------------------------
    op.drop_index(op.f("ix_security_master_ticker"), table_name="security_master")
    op.drop_index(op.f("ix_security_master_cusip"), table_name="security_master")
    op.drop_index(op.f("ix_security_master_asset_id"), table_name="security_master")
    op.drop_table("security_master")

    # -- accumulation_signals (depends on assets) -----------------------------
    op.drop_index(
        op.f("ix_accumulation_signals_asset_id"), table_name="accumulation_signals"
    )
    op.drop_table("accumulation_signals")

    # -- managers (no dependencies) -------------------------------------------
    op.drop_index(op.f("ix_managers_cik"), table_name="managers")
    op.drop_table("managers")
