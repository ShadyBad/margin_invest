"""add audit log table

Revision ID: 63424f126852
Revises: 213b952d6813
Create Date: 2026-02-26 00:27:19.751148

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '63424f126852'
down_revision: str | Sequence[str] | None = '213b952d6813'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create audit_log table for security event tracking."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("audit_log"):
        op.create_table(
            "audit_log",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("user_id", sa.Integer, nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.Text, nullable=True),
            sa.Column("detail", sa.JSON, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])
        op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
        op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    """Drop audit_log table."""
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_user_id", table_name="audit_log")
    op.drop_index("ix_audit_log_event_type", table_name="audit_log")
    op.drop_table("audit_log")
