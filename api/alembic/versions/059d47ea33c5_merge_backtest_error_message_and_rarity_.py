"""merge backtest error_message and rarity tables

Revision ID: 059d47ea33c5
Revises: 29c44530fc6f, 6b9ee008f974
Create Date: 2026-03-17 11:45:41.697235

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "059d47ea33c5"
down_revision: str | Sequence[str] | None = ("29c44530fc6f", "6b9ee008f974")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
