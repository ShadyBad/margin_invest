"""merge experiment_signups and risk_diffing heads

Revision ID: cd6c9c3cd56a
Revises: b1c2d3e4f5a6, b8633f3bb979
Create Date: 2026-04-26 23:49:48.325727

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "cd6c9c3cd56a"
down_revision: str | Sequence[str] | None = ("b1c2d3e4f5a6", "b8633f3bb979")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
