"""merge experiment_signups and risk_diffing heads

Revision ID: cd6c9c3cd56a
Revises: b1c2d3e4f5a6, b8633f3bb979
Create Date: 2026-04-26 23:49:48.325727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd6c9c3cd56a'
down_revision: Union[str, Sequence[str], None] = ('b1c2d3e4f5a6', 'b8633f3bb979')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
