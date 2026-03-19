"""add_webhook_tables

Revision ID: f0d4d4376360
Revises: bd1958ca620b
Create Date: 2026-03-19 08:51:33.174984

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "f0d4d4376360"
down_revision: str | Sequence[str] | None = "bd1958ca620b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()

    if "webhook_subscriptions" not in existing_tables:
        op.create_table(
            "webhook_subscriptions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("url", sa.String(length=2048), nullable=False),
            sa.Column("hmac_key_encrypted", sa.String(length=512), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["created_by"],
                ["users.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("event_type", "url"),
        )
        op.create_index(
            op.f("ix_webhook_subscriptions_event_type"),
            "webhook_subscriptions",
            ["event_type"],
            unique=False,
        )

    if "webhook_deliveries" not in existing_tables:
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("subscription_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column(
                "payload",
                sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
                nullable=False,
            ),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_status_code", sa.Integer(), nullable=True),
            sa.Column("last_error", sa.String(length=1000), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["subscription_id"],
                ["webhook_subscriptions.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_webhook_deliveries_subscription_id"),
            "webhook_deliveries",
            ["subscription_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()

    if "webhook_deliveries" in existing_tables:
        op.drop_index(
            op.f("ix_webhook_deliveries_subscription_id"),
            table_name="webhook_deliveries",
        )
        op.drop_table("webhook_deliveries")

    if "webhook_subscriptions" in existing_tables:
        op.drop_index(
            op.f("ix_webhook_subscriptions_event_type"),
            table_name="webhook_subscriptions",
        )
        op.drop_table("webhook_subscriptions")
