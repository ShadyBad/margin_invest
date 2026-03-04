"""add edgar_no_xbrl_cache table

Revision ID: fa52c5bcca08
Revises: 16e71339a83e
Create Date: 2026-03-04 13:07:43.401118

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fa52c5bcca08"
down_revision: str | Sequence[str] | None = "16e71339a83e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("edgar_no_xbrl_cache"):
        op.create_table(
            "edgar_no_xbrl_cache",
            sa.Column("accession_number", sa.String(length=30), nullable=False),
            sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("accession_number"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("edgar_no_xbrl_cache")
