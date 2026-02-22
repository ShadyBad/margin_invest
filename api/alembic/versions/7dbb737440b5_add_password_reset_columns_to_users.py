"""add password reset columns to users

Revision ID: 7dbb737440b5
Revises: f8a2b1c3d4e5
Create Date: 2026-02-21 16:23:53.283536

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7dbb737440b5"
down_revision: str | Sequence[str] | None = "f8a2b1c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add credential/MFA columns to unified users table."""
    # Add credential columns to users (nullable for OAuth-only users)
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "mfa_grace_deadline",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_totp_counter", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Create linked_providers table
    op.create_table(
        "linked_providers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("oauth_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=320), nullable=True),
        sa.Column(
            "linked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "oauth_id",
            name="uq_linked_providers_provider_oauth_id",
        ),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            name="uq_linked_providers_user_id_provider",
        ),
    )

    # Create recovery_codes table
    op.create_table(
        "recovery_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Drop the old provider column from users (replaced by linked_providers)
    op.drop_column("users", "provider")

    # Make name nullable (OAuth users may not have a name)
    op.alter_column("users", "name", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    """Remove credential/MFA columns from users table."""
    op.alter_column("users", "name", existing_type=sa.String(255), nullable=False)
    op.add_column("users", sa.Column("provider", sa.String(length=50), nullable=True))
    op.drop_table("recovery_codes")
    op.drop_table("linked_providers")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "last_totp_counter")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "mfa_grace_deadline")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "password_hash")
