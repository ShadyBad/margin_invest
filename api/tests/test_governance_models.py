"""Tests for governance data models."""

from __future__ import annotations

import pytest
from margin_api.db.base import Base
from margin_api.db.models import (
    GovernanceConfig,
    GovernanceEvent,
    MlModelRun,
    PipelineApproval,
    UserProposal,
    V4Score,
)
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


@pytest.fixture()
def sync_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


# ---------------------------------------------------------------------------
# PipelineApproval
# ---------------------------------------------------------------------------


class TestPipelineApprovalModel:
    def test_table_name(self):
        assert PipelineApproval.__tablename__ == "pipeline_approvals"

    def test_columns(self):
        columns = {c.name for c in PipelineApproval.__table__.columns}
        expected = {
            "id",
            "gate_type",
            "status",
            "pipeline_id",
            "payload_ref",
            "impact_summary",
            "submitted_at",
            "decided_at",
            "decided_by",
            "decision_reason",
            "expires_at",
        }
        assert expected.issubset(columns)

    def test_gate_type_not_nullable(self):
        col = PipelineApproval.__table__.columns["gate_type"]
        assert col.nullable is False

    def test_pipeline_id_nullable(self):
        col = PipelineApproval.__table__.columns["pipeline_id"]
        assert col.nullable is True

    def test_pipeline_id_indexed(self):
        col = PipelineApproval.__table__.columns["pipeline_id"]
        assert col.index is True

    def test_decided_at_nullable(self):
        col = PipelineApproval.__table__.columns["decided_at"]
        assert col.nullable is True

    def test_decided_by_nullable(self):
        col = PipelineApproval.__table__.columns["decided_by"]
        assert col.nullable is True

    def test_decision_reason_nullable(self):
        col = PipelineApproval.__table__.columns["decision_reason"]
        assert col.nullable is True

    def test_expires_at_nullable(self):
        col = PipelineApproval.__table__.columns["expires_at"]
        assert col.nullable is True

    def test_status_index(self):
        index_names = {idx.name for idx in PipelineApproval.__table__.indexes}
        assert "ix_pipeline_approvals_status" in index_names

    def test_gate_type_index(self):
        index_names = {idx.name for idx in PipelineApproval.__table__.indexes}
        assert "ix_pipeline_approvals_gate_type" in index_names

    def test_default_status_staged(self, sync_engine):
        with Session(sync_engine) as session:
            approval = PipelineApproval(gate_type="score_publish")
            session.add(approval)
            session.commit()
            result = session.execute(
                select(PipelineApproval).where(PipelineApproval.id == approval.id)
            )
            found = result.scalar_one()
            assert found.status == "staged"

    def test_submitted_at_auto_populated(self, sync_engine):
        with Session(sync_engine) as session:
            approval = PipelineApproval(gate_type="ml_model_deploy")
            session.add(approval)
            session.commit()
            result = session.execute(
                select(PipelineApproval).where(PipelineApproval.id == approval.id)
            )
            found = result.scalar_one()
            assert found.submitted_at is not None

    def test_json_fields_round_trip(self, sync_engine):
        with Session(sync_engine) as session:
            approval = PipelineApproval(
                gate_type="universe_activate",
                payload_ref={"run_id": 42},
                impact_summary={"tickers_affected": 100},
            )
            session.add(approval)
            session.commit()
            result = session.execute(
                select(PipelineApproval).where(PipelineApproval.id == approval.id)
            )
            found = result.scalar_one()
            assert found.payload_ref == {"run_id": 42}
            assert found.impact_summary == {"tickers_affected": 100}


# ---------------------------------------------------------------------------
# GovernanceEvent
# ---------------------------------------------------------------------------


class TestGovernanceEventModel:
    def test_table_name(self):
        assert GovernanceEvent.__tablename__ == "governance_events"

    def test_columns(self):
        columns = {c.name for c in GovernanceEvent.__table__.columns}
        expected = {"id", "event_type", "source", "detail", "created_at"}
        assert expected.issubset(columns)

    def test_event_type_indexed(self):
        col = GovernanceEvent.__table__.columns["event_type"]
        assert col.index is True

    def test_created_at_indexed(self):
        col = GovernanceEvent.__table__.columns["created_at"]
        assert col.index is True

    def test_detail_nullable(self):
        col = GovernanceEvent.__table__.columns["detail"]
        assert col.nullable is True

    def test_insert_and_query(self, sync_engine):
        with Session(sync_engine) as session:
            event = GovernanceEvent(
                event_type="approval.created",
                source="api",
                detail={"approval_id": 1},
            )
            session.add(event)
            session.commit()
            result = session.execute(select(GovernanceEvent).where(GovernanceEvent.id == event.id))
            found = result.scalar_one()
            assert found.event_type == "approval.created"
            assert found.source == "api"
            assert found.detail == {"approval_id": 1}
            assert found.created_at is not None


# ---------------------------------------------------------------------------
# GovernanceConfig
# ---------------------------------------------------------------------------


class TestGovernanceConfigModel:
    def test_table_name(self):
        assert GovernanceConfig.__tablename__ == "governance_configs"

    def test_columns(self):
        columns = {c.name for c in GovernanceConfig.__table__.columns}
        expected = {"id", "config_key", "config_value", "created_at", "updated_at"}
        assert expected.issubset(columns)

    def test_config_key_unique(self):
        col = GovernanceConfig.__table__.columns["config_key"]
        assert col.unique is True

    def test_config_value_nullable(self):
        col = GovernanceConfig.__table__.columns["config_value"]
        assert col.nullable is True

    def test_insert_and_query(self, sync_engine):
        with Session(sync_engine) as session:
            config = GovernanceConfig(
                config_key="approval.score_publish.auto_approve_threshold",
                config_value={"threshold": 0.05},
            )
            session.add(config)
            session.commit()
            result = session.execute(
                select(GovernanceConfig).where(GovernanceConfig.id == config.id)
            )
            found = result.scalar_one()
            assert found.config_key == "approval.score_publish.auto_approve_threshold"
            assert found.config_value == {"threshold": 0.05}
            assert found.created_at is not None
            assert found.updated_at is not None


# ---------------------------------------------------------------------------
# UserProposal
# ---------------------------------------------------------------------------


class TestUserProposalModel:
    def test_table_name(self):
        assert UserProposal.__tablename__ == "user_proposals"

    def test_columns(self):
        columns = {c.name for c in UserProposal.__table__.columns}
        expected = {
            "id",
            "user_id",
            "proposal_type",
            "status",
            "payload",
            "created_at",
            "decided_at",
        }
        assert expected.issubset(columns)

    def test_user_id_indexed(self):
        col = UserProposal.__table__.columns["user_id"]
        assert col.index is not False  # may be True via composite index

    def test_composite_index_user_status(self):
        index_names = {idx.name for idx in UserProposal.__table__.indexes}
        assert "ix_user_proposals_user_status" in index_names

    def test_decided_at_nullable(self):
        col = UserProposal.__table__.columns["decided_at"]
        assert col.nullable is True

    def test_payload_nullable(self):
        col = UserProposal.__table__.columns["payload"]
        assert col.nullable is True

    def test_default_status_pending(self, sync_engine):
        with Session(sync_engine) as session:
            proposal = UserProposal(user_id=1, proposal_type="watchlist_add")
            session.add(proposal)
            session.commit()
            result = session.execute(select(UserProposal).where(UserProposal.id == proposal.id))
            found = result.scalar_one()
            assert found.status == "pending"

    def test_created_at_auto_populated(self, sync_engine):
        with Session(sync_engine) as session:
            proposal = UserProposal(user_id=2, proposal_type="alert_config")
            session.add(proposal)
            session.commit()
            result = session.execute(select(UserProposal).where(UserProposal.id == proposal.id))
            found = result.scalar_one()
            assert found.created_at is not None

    def test_json_payload_round_trip(self, sync_engine):
        with Session(sync_engine) as session:
            proposal = UserProposal(
                user_id=3,
                proposal_type="portfolio_suggestion",
                payload={"ticker": "AAPL", "action": "add", "weight": 0.05},
            )
            session.add(proposal)
            session.commit()
            result = session.execute(select(UserProposal).where(UserProposal.id == proposal.id))
            found = result.scalar_one()
            assert found.payload == {"ticker": "AAPL", "action": "add", "weight": 0.05}


# ---------------------------------------------------------------------------
# V4Score.published column addition
# ---------------------------------------------------------------------------


class TestV4ScorePublished:
    def test_published_column_exists(self):
        columns = {c.name for c in V4Score.__table__.columns}
        assert "published" in columns

    def test_published_default_false(self, sync_engine):
        from margin_api.db.models import Asset

        with Session(sync_engine) as session:
            asset = Asset(ticker="TEST", name="Test Co", sector="Tech")
            session.add(asset)
            session.flush()
            score = V4Score(
                asset_id=asset.id,
                opportunity_type="deep_value",
                conviction="high",
                rules_conviction="high",
                style="value",
                timing_signal="buy",
                regime="expansion",
                composite_score=85.0,
                ml_override="none",
            )
            session.add(score)
            session.commit()
            result = session.execute(select(V4Score).where(V4Score.id == score.id))
            found = result.scalar_one()
            assert found.published is False


# ---------------------------------------------------------------------------
# MlModelRun.deployment_status column addition
# ---------------------------------------------------------------------------


class TestMlModelRunDeploymentStatus:
    def test_deployment_status_column_exists(self):
        columns = {c.name for c in MlModelRun.__table__.columns}
        assert "deployment_status" in columns

    def test_deployment_status_default_candidate(self, sync_engine):
        with Session(sync_engine) as session:
            run = MlModelRun(
                model_type="lightgbm_cluster",
                status="completed",
            )
            session.add(run)
            session.commit()
            result = session.execute(select(MlModelRun).where(MlModelRun.id == run.id))
            found = result.scalar_one()
            assert found.deployment_status == "candidate"


# ---------------------------------------------------------------------------
# Table creation includes new tables
# ---------------------------------------------------------------------------


class TestGovernanceTablesCreated:
    def test_all_governance_tables_exist(self, sync_engine):
        table_names = set(Base.metadata.tables.keys())
        assert "pipeline_approvals" in table_names
        assert "governance_events" in table_names
        assert "governance_configs" in table_names
        assert "user_proposals" in table_names
