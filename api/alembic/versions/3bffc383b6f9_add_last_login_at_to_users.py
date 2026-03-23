"""add_last_login_at_to_users

Revision ID: 3bffc383b6f9
Revises: f0d4d4376360
Create Date: 2026-03-22 20:27:00.965703

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3bffc383b6f9"
down_revision: str | Sequence[str] | None = "f0d4d4376360"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "last_login_at")
