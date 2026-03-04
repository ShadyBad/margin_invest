"""add edgar_index_cache table

Revision ID: 16e71339a83e
Revises: d839373360f3
Create Date: 2026-03-03 20:43:57.213648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '16e71339a83e'
down_revision: Union[str, Sequence[str], None] = 'd839373360f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('edgar_index_cache',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('quarter', sa.Integer(), nullable=False),
    sa.Column('cache_key', sa.String(length=20), nullable=False),
    sa.Column('entries_json', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('entry_count', sa.Integer(), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cache_key')
    )
    op.create_index('ix_edgar_index_cache_year_quarter', 'edgar_index_cache', ['year', 'quarter'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_edgar_index_cache_year_quarter', table_name='edgar_index_cache')
    op.drop_table('edgar_index_cache')
