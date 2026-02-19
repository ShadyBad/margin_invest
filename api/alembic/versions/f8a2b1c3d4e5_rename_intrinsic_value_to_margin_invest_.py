"""rename intrinsic_value to margin_invest_value on scores

Revision ID: f8a2b1c3d4e5
Revises: 27dd7a410171
Create Date: 2026-02-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f8a2b1c3d4e5'
down_revision: Union[str, Sequence[str], None] = '27dd7a410171'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename scores.intrinsic_value -> scores.margin_invest_value."""
    op.alter_column("scores", "intrinsic_value", new_column_name="margin_invest_value")


def downgrade() -> None:
    """Revert scores.margin_invest_value -> scores.intrinsic_value."""
    op.alter_column("scores", "margin_invest_value", new_column_name="intrinsic_value")
