"""add_composite_raw_score_to_scores

Revision ID: a1b2c3d4e5f6
Revises: 4c4fefbc50d3
Create Date: 2026-02-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '4c4fefbc50d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'scores',
        sa.Column('composite_raw_score', sa.Float(), nullable=False, server_default='0.0'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('scores', 'composite_raw_score')
