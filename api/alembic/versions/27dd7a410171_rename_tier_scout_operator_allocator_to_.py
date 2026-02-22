"""rename_tier_scout_operator_allocator_to_analyst_portfolio_institutional

Revision ID: 27dd7a410171
Revises: d0853ea65359
Create Date: 2026-02-18 00:27:56.309626

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '27dd7a410171'
down_revision: str | Sequence[str] | None = 'd0853ea65359'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE users SET subscription_plan = 'analyst'"
        " WHERE subscription_plan = 'scout'"
    )
    op.execute(
        "UPDATE users SET subscription_plan = 'portfolio'"
        " WHERE subscription_plan = 'operator'"
    )
    op.execute(
        "UPDATE users SET subscription_plan = 'institutional'"
        " WHERE subscription_plan = 'allocator'"
    )
    op.execute(
        "UPDATE credential_users SET subscription_plan = 'analyst'"
        " WHERE subscription_plan = 'scout'"
    )
    op.execute(
        "UPDATE credential_users SET subscription_plan = 'portfolio'"
        " WHERE subscription_plan = 'operator'"
    )
    op.execute(
        "UPDATE credential_users SET subscription_plan = 'institutional'"
        " WHERE subscription_plan = 'allocator'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users SET subscription_plan = 'scout'"
        " WHERE subscription_plan = 'analyst'"
    )
    op.execute(
        "UPDATE users SET subscription_plan = 'operator'"
        " WHERE subscription_plan = 'portfolio'"
    )
    op.execute(
        "UPDATE users SET subscription_plan = 'allocator'"
        " WHERE subscription_plan = 'institutional'"
    )
    op.execute(
        "UPDATE credential_users SET subscription_plan = 'scout'"
        " WHERE subscription_plan = 'analyst'"
    )
    op.execute(
        "UPDATE credential_users SET subscription_plan = 'operator'"
        " WHERE subscription_plan = 'portfolio'"
    )
    op.execute(
        "UPDATE credential_users SET subscription_plan = 'allocator'"
        " WHERE subscription_plan = 'institutional'"
    )
