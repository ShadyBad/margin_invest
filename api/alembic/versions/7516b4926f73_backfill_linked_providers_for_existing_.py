"""backfill linked providers for existing oauth users

Revision ID: 7516b4926f73
Revises: 7dbb737440b5
Create Date: 2026-02-21 16:39:00.076582

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7516b4926f73'
down_revision: Union[str, Sequence[str], None] = '7dbb737440b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill linked_providers for users who signed up via OAuth."""
    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT INTO linked_providers (user_id, provider, oauth_id, provider_email, linked_at)
        SELECT u.id, 'google', u.oauth_id, u.email, u.created_at
        FROM users u
        WHERE u.oauth_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM linked_providers lp
              WHERE lp.user_id = u.id AND lp.provider = 'google'
          )
    """))


def downgrade() -> None:
    """Remove only the backfilled linked_providers rows."""
    conn = op.get_bind()
    conn.execute(sa.text("""
        DELETE FROM linked_providers lp
        USING users u
        WHERE lp.user_id = u.id
          AND lp.provider = 'google'
          AND lp.oauth_id = u.oauth_id
    """))
