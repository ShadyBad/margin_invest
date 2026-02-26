"""add events and notifications tables

Revision ID: 51e51cbdf62c
Revises: b7c3d4e5f6a7
Create Date: 2026-02-23 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "51e51cbdf62c"
down_revision: str | Sequence[str] | None = "b7c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create events and notifications tables."""
    jsonb_variant = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

    # -- events ---------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("payload", jsonb_variant, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_events_event_id"), "events", ["event_id"], unique=True)
    op.create_index(op.f("ix_events_ticker"), "events", ["ticker"], unique=False)
    op.create_index(
        "ix_events_ticker_timestamp",
        "events",
        ["ticker", "timestamp"],
        unique=False,
    )

    # -- notifications --------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_id"),
    )
    op.create_index(
        op.f("ix_notifications_notification_id"),
        "notifications",
        ["notification_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_notifications_event_id"),
        "notifications",
        ["event_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop notifications and events tables."""
    op.drop_index(
        op.f("ix_notifications_event_id"),
        table_name="notifications",
    )
    op.drop_index(
        op.f("ix_notifications_notification_id"),
        table_name="notifications",
    )
    op.drop_table("notifications")

    op.drop_index("ix_events_ticker_timestamp", table_name="events")
    op.drop_index(op.f("ix_events_ticker"), table_name="events")
    op.drop_index(op.f("ix_events_event_id"), table_name="events")
    op.drop_table("events")
