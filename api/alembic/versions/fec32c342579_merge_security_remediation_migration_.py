"""merge security remediation migration heads

Revision ID: fec32c342579
Revises: 63424f126852, 644c974fd652
Create Date: 2026-02-26 00:32:49.036454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fec32c342579'
down_revision: Union[str, Sequence[str], None] = ('63424f126852', '644c974fd652')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
