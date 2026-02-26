"""add processed webhook events table

Revision ID: 213b952d6813
Revises: e10ea8524fbf
Create Date: 2026-02-26 00:23:43.093226

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "213b952d6813"
down_revision: str | Sequence[str] | None = "e10ea8524fbf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create processed_webhook_events table for Stripe webhook idempotency."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("processed_webhook_events"):
        op.create_table(
            "processed_webhook_events",
            sa.Column("event_id", sa.String(255), nullable=False),
            sa.Column("event_type", sa.String(100), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("event_id"),
        )


def downgrade() -> None:
    """Drop processed_webhook_events table."""
    op.drop_table("processed_webhook_events")
