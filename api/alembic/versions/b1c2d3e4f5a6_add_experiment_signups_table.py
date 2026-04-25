"""add_experiment_signups_table

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-04-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create experiment_signups table."""
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = inspector.get_table_names()

    if "experiment_signups" not in existing_tables:
        op.create_table(
            "experiment_signups",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("amount_cents", sa.Integer(), nullable=False),
            sa.Column("stripe_session_id", sa.String(length=255), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("stripe_session_id"),
        )


def downgrade() -> None:
    """Drop experiment_signups table."""
    op.drop_table("experiment_signups")
