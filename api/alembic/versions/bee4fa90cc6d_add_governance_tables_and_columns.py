"""add governance tables and columns

Revision ID: bee4fa90cc6d
Revises: 7085e0ad6ae4
Create Date: 2026-02-27 12:00:27.179760

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "bee4fa90cc6d"
down_revision: str | Sequence[str] | None = "7085e0ad6ae4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add governance tables, shadow portfolio snapshots, and new columns."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # -- pipeline_approvals --------------------------------------------------
    if not inspector.has_table("pipeline_approvals"):
        op.create_table(
            "pipeline_approvals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("gate_type", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("pipeline_id", sa.String(length=40), nullable=True),
            sa.Column(
                "payload_ref",
                sa.JSON().with_variant(
                    postgresql.JSONB(astext_type=sa.Text()), "postgresql"
                ),
                nullable=True,
            ),
            sa.Column(
                "impact_summary",
                sa.JSON().with_variant(
                    postgresql.JSONB(astext_type=sa.Text()), "postgresql"
                ),
                nullable=True,
            ),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decided_by", sa.Integer(), nullable=True),
            sa.Column("decision_reason", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_pipeline_approvals_status", "pipeline_approvals", ["status"]
        )
        op.create_index(
            "ix_pipeline_approvals_gate_type", "pipeline_approvals", ["gate_type"]
        )
        op.create_index(
            op.f("ix_pipeline_approvals_pipeline_id"),
            "pipeline_approvals",
            ["pipeline_id"],
        )

    # -- governance_events ----------------------------------------------------
    if not inspector.has_table("governance_events"):
        op.create_table(
            "governance_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("source", sa.String(length=50), nullable=False),
            sa.Column(
                "detail",
                sa.JSON().with_variant(
                    postgresql.JSONB(astext_type=sa.Text()), "postgresql"
                ),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_governance_events_event_type"),
            "governance_events",
            ["event_type"],
        )
        op.create_index(
            op.f("ix_governance_events_created_at"),
            "governance_events",
            ["created_at"],
        )

    # -- governance_configs ---------------------------------------------------
    if not inspector.has_table("governance_configs"):
        op.create_table(
            "governance_configs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("config_key", sa.String(length=100), nullable=False),
            sa.Column(
                "config_value",
                sa.JSON().with_variant(
                    postgresql.JSONB(astext_type=sa.Text()), "postgresql"
                ),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("config_key"),
        )

    # -- user_proposals -------------------------------------------------------
    if not inspector.has_table("user_proposals"):
        op.create_table(
            "user_proposals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("proposal_type", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column(
                "payload",
                sa.JSON().with_variant(
                    postgresql.JSONB(astext_type=sa.Text()), "postgresql"
                ),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_user_proposals_user_id"), "user_proposals", ["user_id"]
        )
        op.create_index(
            "ix_user_proposals_user_status",
            "user_proposals",
            ["user_id", "status"],
        )

    # -- shadow_portfolio_snapshots -------------------------------------------
    if not inspector.has_table("shadow_portfolio_snapshots"):
        op.create_table(
            "shadow_portfolio_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("as_of_date", sa.String(length=10), nullable=False),
            sa.Column("portfolio_value", sa.Float(), nullable=False),
            sa.Column("total_return", sa.Float(), nullable=True),
            sa.Column("num_positions", sa.Integer(), nullable=False),
            sa.Column(
                "positions_json",
                sa.JSON().with_variant(
                    postgresql.JSONB(astext_type=sa.Text()), "postgresql"
                ),
                nullable=True,
            ),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("as_of_date", name="uq_shadow_snapshot_date"),
        )
        op.create_index(
            "ix_shadow_snapshot_date", "shadow_portfolio_snapshots", ["as_of_date"]
        )

    # -- v4_scores.published --------------------------------------------------
    if inspector.has_table("v4_scores"):
        existing_v4 = [c["name"] for c in inspector.get_columns("v4_scores")]
        if "published" not in existing_v4:
            op.add_column(
                "v4_scores",
                sa.Column(
                    "published",
                    sa.Boolean(),
                    server_default=sa.text("false"),
                    nullable=False,
                ),
            )

    # -- ml_model_runs.deployment_status --------------------------------------
    if inspector.has_table("ml_model_runs"):
        existing_ml = [c["name"] for c in inspector.get_columns("ml_model_runs")]
        if "deployment_status" not in existing_ml:
            op.add_column(
                "ml_model_runs",
                sa.Column(
                    "deployment_status",
                    sa.String(length=20),
                    server_default=sa.text("'candidate'"),
                    nullable=False,
                ),
            )


def downgrade() -> None:
    """Remove governance tables, shadow portfolio snapshots, and new columns."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # -- ml_model_runs.deployment_status --------------------------------------
    if inspector.has_table("ml_model_runs"):
        existing_ml = [c["name"] for c in inspector.get_columns("ml_model_runs")]
        if "deployment_status" in existing_ml:
            op.drop_column("ml_model_runs", "deployment_status")

    # -- v4_scores.published --------------------------------------------------
    if inspector.has_table("v4_scores"):
        existing_v4 = [c["name"] for c in inspector.get_columns("v4_scores")]
        if "published" in existing_v4:
            op.drop_column("v4_scores", "published")

    # -- shadow_portfolio_snapshots -------------------------------------------
    if inspector.has_table("shadow_portfolio_snapshots"):
        op.drop_index("ix_shadow_snapshot_date", table_name="shadow_portfolio_snapshots")
        op.drop_table("shadow_portfolio_snapshots")

    # -- user_proposals -------------------------------------------------------
    if inspector.has_table("user_proposals"):
        op.drop_index(
            "ix_user_proposals_user_status", table_name="user_proposals"
        )
        op.drop_index(
            op.f("ix_user_proposals_user_id"), table_name="user_proposals"
        )
        op.drop_table("user_proposals")

    # -- governance_configs ---------------------------------------------------
    if inspector.has_table("governance_configs"):
        op.drop_table("governance_configs")

    # -- governance_events ----------------------------------------------------
    if inspector.has_table("governance_events"):
        op.drop_index(
            op.f("ix_governance_events_created_at"),
            table_name="governance_events",
        )
        op.drop_index(
            op.f("ix_governance_events_event_type"),
            table_name="governance_events",
        )
        op.drop_table("governance_events")

    # -- pipeline_approvals ---------------------------------------------------
    if inspector.has_table("pipeline_approvals"):
        op.drop_index(
            "ix_pipeline_approvals_status", table_name="pipeline_approvals"
        )
        op.drop_index(
            "ix_pipeline_approvals_gate_type", table_name="pipeline_approvals"
        )
        op.drop_index(
            op.f("ix_pipeline_approvals_pipeline_id"),
            table_name="pipeline_approvals",
        )
        op.drop_table("pipeline_approvals")
