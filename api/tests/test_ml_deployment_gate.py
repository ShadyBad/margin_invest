"""Tests for ML model deployment gate: _stage_ml_model_impl and _promote_ml_model_impl."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import MlModelRun, PipelineApproval
from margin_api.workers import _promote_ml_model_impl, _stage_ml_model_impl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


async def _create_ml_model_run(
    session: AsyncSession,
    deployment_status: str = "candidate",
    model_qualifies: bool = True,
    overall_rank_ic: float = 0.25,
    n_clusters: int = 5,
    n_features: int = 12,
    n_samples: int = 100,
) -> MlModelRun:
    """Create a test MlModelRun."""
    model = MlModelRun(
        model_type="lightgbm_cluster",
        n_clusters=n_clusters,
        n_features=n_features,
        n_samples=n_samples,
        model_qualifies=model_qualifies,
        overall_rank_ic=overall_rank_ic,
        deployment_status=deployment_status,
    )
    session.add(model)
    await session.flush()
    return model


class TestStageMlModelImpl:
    @pytest.mark.asyncio
    async def test_creates_approval_with_correct_gate_type_and_impact_summary(self, db_session):
        """_stage_ml_model_impl creates a PipelineApproval with ml_model_deploy gate."""
        model = await _create_ml_model_run(db_session)
        await db_session.commit()

        result = await _stage_ml_model_impl(db_session, model.id)

        assert result["status"] == "staged"
        assert "approval_id" in result

        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        assert len(approvals) == 1

        approval = approvals[0]
        assert approval.gate_type == "ml_model_deploy"
        assert approval.status == "staged"
        assert approval.payload_ref["ml_model_run_id"] == model.id

        # Verify impact_summary fields
        summary = approval.impact_summary
        assert summary["rank_ic"] == 0.25
        assert summary["model_qualifies"] is True
        assert summary["n_clusters"] == 5
        assert summary["n_features"] == 12
        assert summary["n_samples"] == 100

        # expires_at should be roughly 48 hours from now
        expires = (
            approval.expires_at.replace(tzinfo=None)
            if approval.expires_at.tzinfo
            else approval.expires_at
        )
        now_naive = datetime.now(UTC).replace(tzinfo=None)
        delta = expires - now_naive
        assert timedelta(hours=47) < delta < timedelta(hours=49)

    @pytest.mark.asyncio
    async def test_includes_comparison_to_active_model(self, db_session):
        """_stage_ml_model_impl includes previous_rank_ic and delta when active model exists."""
        # Create an existing active model
        await _create_ml_model_run(
            db_session,
            deployment_status="active",
            overall_rank_ic=0.20,
            n_clusters=4,
            n_features=10,
            n_samples=80,
        )
        await db_session.commit()

        # Create a new candidate model
        candidate = await _create_ml_model_run(
            db_session,
            deployment_status="candidate",
            overall_rank_ic=0.30,
            n_clusters=6,
            n_features=14,
            n_samples=120,
        )
        await db_session.commit()

        result = await _stage_ml_model_impl(db_session, candidate.id)

        assert result["status"] == "staged"

        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        assert len(approvals) == 1

        summary = approvals[0].impact_summary
        assert summary["rank_ic"] == 0.30
        assert summary["previous_rank_ic"] == 0.20
        assert abs(summary["rank_ic_delta"] - 0.10) < 1e-9

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_model(self, db_session):
        """_stage_ml_model_impl returns error when model_run_id does not exist."""
        result = await _stage_ml_model_impl(db_session, 99999)

        assert result["status"] == "error"
        assert "not found" in result["message"]


class TestPromoteMlModelImpl:
    @pytest.mark.asyncio
    async def test_promotes_candidate_to_active_and_retires_previous(self, db_session):
        """_promote_ml_model_impl sets candidate to active and retires the old active model."""
        # Create an active model
        active_model = await _create_ml_model_run(
            db_session, deployment_status="active", overall_rank_ic=0.20
        )
        await db_session.commit()

        # Create a candidate model
        candidate = await _create_ml_model_run(
            db_session, deployment_status="candidate", overall_rank_ic=0.30
        )
        await db_session.commit()

        # Stage the candidate
        stage_result = await _stage_ml_model_impl(db_session, candidate.id)
        approval_id = stage_result["approval_id"]

        # Promote it
        result = await _promote_ml_model_impl(
            db_session, approval_id, decided_by=42, decision_reason="Better IC"
        )

        assert result["status"] == "promoted"
        assert result["model_id"] == candidate.id
        assert result["approval_id"] == approval_id

        # Verify the candidate is now active
        refreshed_candidate = (
            await db_session.execute(select(MlModelRun).where(MlModelRun.id == candidate.id))
        ).scalar_one()
        assert refreshed_candidate.deployment_status == "active"

        # Verify the old active is now retired
        refreshed_active = (
            await db_session.execute(select(MlModelRun).where(MlModelRun.id == active_model.id))
        ).scalar_one()
        assert refreshed_active.deployment_status == "retired"

        # Verify approval is updated
        approval = (
            await db_session.execute(
                select(PipelineApproval).where(PipelineApproval.id == approval_id)
            )
        ).scalar_one()
        assert approval.status == "approved"
        assert approval.decided_by == 42
        assert approval.decision_reason == "Better IC"
        assert approval.decided_at is not None

    @pytest.mark.asyncio
    async def test_rejects_non_staged_approval(self, db_session):
        """_promote_ml_model_impl returns error for already-approved approvals."""
        candidate = await _create_ml_model_run(db_session)
        await db_session.commit()

        # Create an approval that's already approved
        approval = PipelineApproval(
            gate_type="ml_model_deploy",
            status="approved",
            payload_ref={"ml_model_run_id": candidate.id},
            impact_summary={"rank_ic": 0.25},
            expires_at=datetime.now(UTC) + timedelta(hours=48),
        )
        db_session.add(approval)
        await db_session.flush()
        await db_session.commit()

        result = await _promote_ml_model_impl(db_session, approval.id)

        assert result["status"] == "error"
        assert "not in staged status" in result["message"]

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_approval(self, db_session):
        """_promote_ml_model_impl returns error when approval_id does not exist."""
        result = await _promote_ml_model_impl(db_session, 99999)

        assert result["status"] == "error"
        assert "not found" in result["message"]
