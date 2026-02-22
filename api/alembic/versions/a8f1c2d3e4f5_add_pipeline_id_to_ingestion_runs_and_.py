"""add pipeline_id to ingestion_runs and job_runs

Revision ID: a8f1c2d3e4f5
Revises: 7516b4926f73
Create Date: 2026-02-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8f1c2d3e4f5"
down_revision: str | Sequence[str] | None = "7516b4926f73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("ingestion_runs", sa.Column("pipeline_id", sa.String(40), nullable=True))
    op.create_index("ix_ingestion_runs_pipeline_id", "ingestion_runs", ["pipeline_id"])

    op.add_column("job_runs", sa.Column("pipeline_id", sa.String(40), nullable=True))
    op.create_index("ix_job_runs_pipeline_id", "job_runs", ["pipeline_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_job_runs_pipeline_id", table_name="job_runs")
    op.drop_column("job_runs", "pipeline_id")

    op.drop_index("ix_ingestion_runs_pipeline_id", table_name="ingestion_runs")
    op.drop_column("ingestion_runs", "pipeline_id")
