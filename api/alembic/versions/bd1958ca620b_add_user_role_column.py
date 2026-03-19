"""add_user_role_column

Revision ID: bd1958ca620b
Revises: e656ec878529
Create Date: 2026-03-19 07:47:08.714163

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "bd1958ca620b"
down_revision: str | Sequence[str] | None = "e656ec878529"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = [col["name"] for col in inspector.get_columns("users")]
    if "role" not in existing_columns:
        op.add_column(
            "users",
            sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = [col["name"] for col in inspector.get_columns("users")]
    if "role" in existing_columns:
        op.drop_column("users", "role")
