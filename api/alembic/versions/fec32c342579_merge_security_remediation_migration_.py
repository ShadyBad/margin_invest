"""merge security remediation migration heads

Revision ID: fec32c342579
Revises: 63424f126852, 644c974fd652
Create Date: 2026-02-26 00:32:49.036454

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "fec32c342579"
down_revision: str | Sequence[str] | None = ("63424f126852", "644c974fd652")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
