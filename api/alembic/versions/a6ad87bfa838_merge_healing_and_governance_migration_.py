"""merge healing and governance migration heads

Revision ID: a6ad87bfa838
Revises: 874a8844567a, bee4fa90cc6d
Create Date: 2026-02-27 12:40:20.529376

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "a6ad87bfa838"
down_revision: str | Sequence[str] | None = ("874a8844567a", "bee4fa90cc6d")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
