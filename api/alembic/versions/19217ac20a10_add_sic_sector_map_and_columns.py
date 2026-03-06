"""add sic_sector_map and columns

Revision ID: 19217ac20a10
Revises: fa52c5bcca08
Create Date: 2026-03-06 14:52:20.902147

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "19217ac20a10"
down_revision: str | Sequence[str] | None = "fa52c5bcca08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# SIC range → GICS sector mapping (start, end, gics_sector, sic_description)
SIC_RANGES = [
    (100, 999, "Consumer Staples", "Agriculture/Forestry/Fishing"),
    (1000, 1299, "Materials", "Mining"),
    (1300, 1399, "Energy", "Oil & Gas Extraction"),
    (1400, 1499, "Materials", "Mining & Quarrying"),
    (1500, 1799, "Industrials", "Construction"),
    (2000, 2111, "Consumer Staples", "Food/Tobacco Manufacturing"),
    (2200, 2599, "Consumer Discretionary", "Textiles/Apparel/Furniture"),
    (2600, 2899, "Materials", "Paper/Chemicals"),
    (2900, 3299, "Materials", "Rubber/Plastics/Stone/Metals"),
    (3300, 3499, "Industrials", "Primary Metals/Fabricated Metals"),
    (3500, 3599, "Industrials", "Industrial Machinery"),
    (3600, 3699, "Information Technology", "Electronic Equipment"),
    (3700, 3799, "Industrials", "Transportation Equipment"),
    (3800, 3841, "Health Care", "Medical Instruments"),
    (3842, 3851, "Health Care", "Medical Devices/Ophthalmic"),
    (3852, 3899, "Information Technology", "Instruments"),
    (3900, 3999, "Consumer Discretionary", "Misc Manufacturing"),
    (4000, 4799, "Industrials", "Transportation"),
    (4800, 4899, "Communication Services", "Communications"),
    (4900, 4999, "Utilities", "Electric/Gas/Sanitary Services"),
    (5000, 5199, "Industrials", "Wholesale Trade"),
    (5200, 5399, "Consumer Discretionary", "Retail - General"),
    (5400, 5499, "Consumer Staples", "Retail - Grocery"),
    (5500, 5699, "Consumer Discretionary", "Retail - Apparel/Auto"),
    (5700, 5799, "Consumer Discretionary", "Retail - Home"),
    (5800, 5899, "Consumer Discretionary", "Retail - Eating/Drinking"),
    (5900, 5999, "Consumer Staples", "Retail - Drug/Other"),
    (6000, 6199, "Financials", "Banking/Credit"),
    (6200, 6299, "Financials", "Security/Commodity Brokers"),
    (6300, 6499, "Financials", "Insurance"),
    (6500, 6553, "Real Estate", "Real Estate"),
    (6600, 6799, "Financials", "Other Finance"),
    (7000, 7299, "Consumer Discretionary", "Hotels/Personal Services"),
    (7300, 7369, "Industrials", "Business Services"),
    (7370, 7379, "Information Technology", "Computer Services/Software"),
    (7380, 7399, "Industrials", "Business Services"),
    (7400, 7499, "Industrials", "Misc Business Services"),
    (7500, 7699, "Consumer Discretionary", "Auto Repair/Misc Repair"),
    (7700, 7799, "Consumer Discretionary", "Recreation"),
    (7800, 7999, "Communication Services", "Amusement/Recreation"),
    (8000, 8099, "Health Care", "Health Services"),
    (8100, 8199, "Industrials", "Legal Services"),
    (8200, 8299, "Consumer Discretionary", "Educational Services"),
    (8300, 8399, "Health Care", "Social Services"),
    (8400, 8499, "Industrials", "Museums/Membership Orgs"),
    (8700, 8799, "Industrials", "Engineering/Management Services"),
    # Specific overrides (processed after ranges, so they win on conflict)
    (2830, 2836, "Health Care", "Pharmaceuticals"),
    (3674, 3674, "Information Technology", "Semiconductors"),
    (9000, 9999, "Industrials", "Public Administration"),
]


def _has_column(bind, table: str, column: str) -> bool:
    """Check if a column exists in a table (idempotent guard)."""
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


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

    # 1. Create sic_sector_map table
    if not _has_table(bind, "sic_sector_map"):
        op.create_table(
            "sic_sector_map",
            sa.Column("sic_code", sa.Integer(), nullable=False),
            sa.Column("gics_sector", sa.String(length=50), nullable=False),
            sa.Column("sic_description", sa.String(length=200), nullable=True),
            sa.PrimaryKeyConstraint("sic_code"),
        )

    # 2. Add sic_code to pit_financial_snapshots
    if not _has_column(bind, "pit_financial_snapshots", "sic_code"):
        op.add_column(
            "pit_financial_snapshots",
            sa.Column("sic_code", sa.Integer(), nullable=True),
        )

    # 3. Add sic_code and avg_daily_volume to pit_universe_memberships
    if not _has_column(bind, "pit_universe_memberships", "sic_code"):
        op.add_column(
            "pit_universe_memberships",
            sa.Column("sic_code", sa.Integer(), nullable=True),
        )

    if not _has_column(bind, "pit_universe_memberships", "avg_daily_volume"):
        op.add_column(
            "pit_universe_memberships",
            sa.Column("avg_daily_volume", sa.Float(), nullable=True),
        )

    # 4. Seed SIC → GICS mapping data
    # Build a dict keyed by sic_code; later ranges override earlier ones
    # (so the specific overrides like Pharmaceuticals 2830-2836 win).
    sic_map: dict[int, tuple[str, str]] = {}
    for start, end, gics_sector, description in SIC_RANGES:
        for code in range(start, end + 1):
            sic_map[code] = (gics_sector, description)

    # Check if seed data already exists
    count = bind.execute(sa.text("SELECT COUNT(*) FROM sic_sector_map")).scalar()
    if count == 0:
        # Insert in batches using raw SQL for performance
        batch_size = 500
        codes = sorted(sic_map.keys())
        for i in range(0, len(codes), batch_size):
            batch = codes[i : i + batch_size]
            values_parts = []
            for code in batch:
                gics_sector, description = sic_map[code]
                # Escape single quotes in description
                desc_escaped = description.replace("'", "''")
                gics_escaped = gics_sector.replace("'", "''")
                values_parts.append(f"({code}, '{gics_escaped}', '{desc_escaped}')")
            values_sql = ", ".join(values_parts)
            op.execute(
                sa.text(
                    f"INSERT INTO sic_sector_map (sic_code, gics_sector, sic_description) "
                    f"VALUES {values_sql} ON CONFLICT (sic_code) DO NOTHING"
                )
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    # Remove columns (with idempotent checks)
    if _has_column(bind, "pit_universe_memberships", "avg_daily_volume"):
        op.drop_column("pit_universe_memberships", "avg_daily_volume")

    if _has_column(bind, "pit_universe_memberships", "sic_code"):
        op.drop_column("pit_universe_memberships", "sic_code")

    if _has_column(bind, "pit_financial_snapshots", "sic_code"):
        op.drop_column("pit_financial_snapshots", "sic_code")

    # Drop sic_sector_map table (includes seed data)
    if _has_table(bind, "sic_sector_map"):
        op.drop_table("sic_sector_map")
