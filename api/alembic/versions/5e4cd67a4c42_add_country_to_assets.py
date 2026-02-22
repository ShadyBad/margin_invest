"""add country to assets

Revision ID: 5e4cd67a4c42
Revises: ad3f8bd4da04
Create Date: 2026-02-17 23:04:20.452716

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5e4cd67a4c42'
down_revision: str | Sequence[str] | None = 'ad3f8bd4da04'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('assets', sa.Column('country', sa.String(100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('assets', 'country')
