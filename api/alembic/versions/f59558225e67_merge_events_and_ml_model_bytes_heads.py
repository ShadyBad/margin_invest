"""merge events and ml_model_bytes heads

Revision ID: f59558225e67
Revises: 51e51cbdf62c, c8d9e0f1a2b3
Create Date: 2026-02-23 16:00:57.748424

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'f59558225e67'
down_revision: str | Sequence[str] | None = ('51e51cbdf62c', 'c8d9e0f1a2b3')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
