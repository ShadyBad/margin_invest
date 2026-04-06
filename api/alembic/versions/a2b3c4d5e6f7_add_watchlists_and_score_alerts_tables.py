"""add_watchlists_and_score_alerts_tables

Revision ID: a2b3c4d5e6f7
Revises: 3bffc383b6f9
Create Date: 2026-04-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: str | Sequence[str] | None = "3bffc383b6f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema — create watchlists and score_alerts tables if not exists."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing = inspector.get_table_names()

    if "watchlists" not in existing:
        op.create_table(
            "watchlists",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("ticker", sa.String(length=20), nullable=False),
            sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "ticker", name="uq_watchlists_user_ticker"),
        )
        op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"], unique=False)

    if "score_alerts" not in existing:
        op.create_table(
            "score_alerts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("ticker", sa.String(length=20), nullable=False),
            sa.Column("alert_type", sa.String(length=20), nullable=False),
            sa.Column("threshold", sa.Float(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id", "ticker", "alert_type", name="uq_score_alerts_user_ticker_type"
            ),
        )
        op.create_index("ix_score_alerts_user_id", "score_alerts", ["user_id"], unique=False)
        op.create_index(
            "ix_score_alerts_active",
            "score_alerts",
            ["is_active"],
            unique=False,
            postgresql_where=sa.text("is_active = true"),
        )


def downgrade() -> None:
    """Downgrade schema — drop score_alerts and watchlists tables."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing = inspector.get_table_names()

    if "score_alerts" in existing:
        op.drop_index("ix_score_alerts_active", table_name="score_alerts")
        op.drop_index("ix_score_alerts_user_id", table_name="score_alerts")
        op.drop_table("score_alerts")

    if "watchlists" in existing:
        op.drop_index("ix_watchlists_user_id", table_name="watchlists")
        op.drop_table("watchlists")
