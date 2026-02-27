"""Admin governance endpoints for approval management."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import PipelineApproval
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter
from margin_api.routes.admin import _verify_admin_key
from margin_api.schemas.governance import (
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["governance"])


def _approval_to_summary(approval: PipelineApproval) -> ApprovalSummary:
    """Convert a PipelineApproval ORM model to an ApprovalSummary schema."""
    return ApprovalSummary(
        id=approval.id,
        gate_type=approval.gate_type,
        status=approval.status,
        pipeline_id=approval.pipeline_id,
        payload_ref=approval.payload_ref,
        impact_summary=approval.impact_summary,
        submitted_at=approval.submitted_at,
        decided_at=approval.decided_at,
        decided_by=approval.decided_by,
        decision_reason=approval.decision_reason,
        expires_at=approval.expires_at,
    )


async def _enqueue_publish_job(approval: PipelineApproval) -> None:
    """Enqueue the appropriate worker job based on gate_type after approval."""
    settings = get_settings()
    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    try:
        redis: ArqRedis = await create_pool(redis_settings)

        if approval.gate_type == "score_publish":
            await redis.enqueue_job(
                "publish_scores",
                approval.id,
                approval.decided_by,
                approval.decision_reason,
                _job_id=f"publish_scores:{uuid.uuid4().hex[:8]}",
            )
            logger.info(
                "[governance] Enqueued publish_scores for approval %d", approval.id
            )
        elif approval.gate_type == "ml_model_deploy":
            await redis.enqueue_job(
                "publish_scores",
                approval.id,
                approval.decided_by,
                approval.decision_reason,
                _job_id=f"promote_ml:{uuid.uuid4().hex[:8]}",
            )
            logger.info(
                "[governance] Enqueued promote job for approval %d", approval.id
            )
        else:
            logger.warning(
                "[governance] No publish job mapping for gate_type=%s (approval=%d)",
                approval.gate_type,
                approval.id,
            )

        await redis.aclose()
    except Exception:
        logger.exception(
            "[governance] Failed to enqueue publish job for approval %d", approval.id
        )


@router.get("/approvals")
@limiter.limit("30/minute")
async def list_approvals(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
    status: str | None = None,
    gate_type: str | None = None,
) -> ApprovalListResponse:
    """List all pipeline approvals, optionally filtered by status or gate_type."""
    _verify_admin_key(x_admin_key)

    query = select(PipelineApproval).order_by(PipelineApproval.submitted_at.desc())

    if status is not None:
        query = query.where(PipelineApproval.status == status)
    if gate_type is not None:
        query = query.where(PipelineApproval.gate_type == gate_type)

    result = await session.execute(query)
    approvals = result.scalars().all()

    return ApprovalListResponse(
        approvals=[_approval_to_summary(a) for a in approvals]
    )


@router.get("/approvals/{approval_id}")
@limiter.limit("30/minute")
async def get_approval(
    approval_id: int,
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> ApprovalSummary:
    """Get a single pipeline approval by ID."""
    _verify_admin_key(x_admin_key)

    result = await session.execute(
        select(PipelineApproval).where(PipelineApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(404, "Approval not found")

    return _approval_to_summary(approval)


@router.post("/approvals/{approval_id}/approve")
@limiter.limit("10/minute")
async def approve_approval(
    approval_id: int,
    request: Request,
    body: ApprovalDecisionRequest,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a staged pipeline approval and enqueue the publish job."""
    _verify_admin_key(x_admin_key)

    result = await session.execute(
        select(PipelineApproval).where(PipelineApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(404, "Approval not found")
    if approval.status != "staged":
        raise HTTPException(409, "Approval is not in staged status")

    approval.status = "approved"
    approval.decided_at = datetime.now(UTC)
    approval.decision_reason = body.reason
    await session.commit()
    await session.refresh(approval)

    # Enqueue the appropriate publish job
    await _enqueue_publish_job(approval)

    return {"status": "approved", "approval_id": approval.id}


@router.post("/approvals/{approval_id}/reject")
@limiter.limit("10/minute")
async def reject_approval(
    approval_id: int,
    request: Request,
    body: ApprovalDecisionRequest,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reject a staged pipeline approval."""
    _verify_admin_key(x_admin_key)

    result = await session.execute(
        select(PipelineApproval).where(PipelineApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(404, "Approval not found")
    if approval.status != "staged":
        raise HTTPException(409, "Approval is not in staged status")

    approval.status = "rejected"
    approval.decided_at = datetime.now(UTC)
    approval.decision_reason = body.reason
    await session.commit()

    return {"status": "rejected", "approval_id": approval.id}
