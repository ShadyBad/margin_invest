"""merge backtest error_message and rarity tables

Revision ID: 059d47ea33c5
Revises: 29c44530fc6f, 6b9ee008f974
Create Date: 2026-03-17 11:45:41.697235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '059d47ea33c5'
down_revision: Union[str, Sequence[str], None] = ('29c44530fc6f', '6b9ee008f974')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
