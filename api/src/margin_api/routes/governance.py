"""Admin governance endpoints for approval management."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import GovernanceEvent, PipelineApproval
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter
from margin_api.routes.admin import _verify_admin_key
from margin_api.schemas.governance import (
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalSummary,
    GovernanceDashboardResponse,
    GovernanceEventListResponse,
    GovernanceEventResponse,
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

    redis: ArqRedis | None = None
    try:
        redis = await create_pool(redis_settings)

        if approval.gate_type == "score_publish":
            await redis.enqueue_job(
                "publish_scores",
                approval.id,
                approval.decided_by,
                approval.decision_reason,
                _job_id=f"publish_scores:{uuid.uuid4().hex[:8]}",
            )
            logger.info("[governance] Enqueued publish_scores for approval %d", approval.id)
        elif approval.gate_type == "ml_model_deploy":
            await redis.enqueue_job(
                "promote_ml_model",
                approval.id,
                approval.decided_by,
                approval.decision_reason,
                _job_id=f"promote_ml:{uuid.uuid4().hex[:8]}",
            )
            logger.info("[governance] Enqueued promote_ml_model for approval %d", approval.id)
        else:
            logger.warning(
                "[governance] No publish job mapping for gate_type=%s (approval=%d)",
                approval.gate_type,
                approval.id,
            )
    except Exception:
        logger.exception("[governance] Failed to enqueue publish job for approval %d", approval.id)
    finally:
        if redis is not None:
            await redis.aclose()


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

    return ApprovalListResponse(approvals=[_approval_to_summary(a) for a in approvals])


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


@router.get("/governance/dashboard")
@limiter.limit("30/minute")
async def governance_dashboard(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> GovernanceDashboardResponse:
    """Aggregated governance statistics dashboard."""
    _verify_admin_key(x_admin_key)

    # Count pending (staged) approvals
    pending_result = await session.execute(
        select(func.count())
        .select_from(PipelineApproval)
        .where(PipelineApproval.status == "staged")
    )
    pending_count = pending_result.scalar() or 0

    # Average approval latency in hours (last 30 days)
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    latency_result = await session.execute(
        select(
            PipelineApproval.submitted_at,
            PipelineApproval.decided_at,
        ).where(
            PipelineApproval.status == "approved",
            PipelineApproval.decided_at.isnot(None),
            PipelineApproval.submitted_at >= thirty_days_ago,
        )
    )
    latency_rows = latency_result.all()
    if latency_rows:
        total_hours = sum(
            (row.decided_at - row.submitted_at).total_seconds() / 3600.0 for row in latency_rows
        )
        avg_latency = round(total_hours / len(latency_rows), 2)
    else:
        avg_latency = None

    # Rejection rate: rejected / (approved + rejected)
    approved_count_result = await session.execute(
        select(func.count())
        .select_from(PipelineApproval)
        .where(PipelineApproval.status == "approved")
    )
    approved_count = approved_count_result.scalar() or 0

    rejected_count_result = await session.execute(
        select(func.count())
        .select_from(PipelineApproval)
        .where(PipelineApproval.status == "rejected")
    )
    rejected_count = rejected_count_result.scalar() or 0

    total_decided = approved_count + rejected_count
    rejection_rate = (rejected_count / total_decided) if total_decided > 0 else None

    return GovernanceDashboardResponse(
        pending_count=pending_count,
        avg_approval_latency_hours=round(avg_latency, 2) if avg_latency is not None else None,
        rejection_rate=round(rejection_rate, 4) if rejection_rate is not None else None,
        recent_anomalies=[],
    )


@router.get("/governance/events")
@limiter.limit("30/minute")
async def list_governance_events(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
    event_type: str | None = None,
    limit: int = Query(default=50, le=200, ge=1),
    offset: int = Query(default=0, ge=0),
) -> GovernanceEventListResponse:
    """Paginated governance event log."""
    _verify_admin_key(x_admin_key)

    # Base query for filtering
    base_filter = []
    if event_type is not None:
        base_filter.append(GovernanceEvent.event_type.like(f"{event_type}%"))

    # Total count
    count_query = select(func.count()).select_from(GovernanceEvent)
    if base_filter:
        count_query = count_query.where(*base_filter)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated events
    events_query = (
        select(GovernanceEvent)
        .order_by(GovernanceEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if base_filter:
        events_query = events_query.where(*base_filter)
    events_result = await session.execute(events_query)
    events = events_result.scalars().all()

    return GovernanceEventListResponse(
        events=[
            GovernanceEventResponse(
                id=e.id,
                event_type=e.event_type,
                source=e.source,
                detail=e.detail,
                created_at=e.created_at,
            )
            for e in events
        ],
        total=total,
    )
