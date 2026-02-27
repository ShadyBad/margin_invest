"""Public governance transparency endpoint — no auth required."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import IngestionRun, PipelineApproval
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter
from margin_api.schemas.governance import TransparencyResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])

OVERSIGHT_LEVELS = {
    "in_the_loop": [
        "score_publication",
        "ml_model_deployment",
        "universe_activation",
        "filter_config",
    ],
    "on_the_loop": [
        "daily_scoring_pipeline",
        "13f_ingest",
        "backtest_replay",
    ],
    "out_of_the_loop": [
        "data_ingestion",
        "live_pricing",
        "data_quality",
        "accumulation_signals",
    ],
}

_GATE_TYPES = ["score_publish", "ml_model_deploy", "universe_activate"]


@router.get("/transparency")
@limiter.limit("60/minute")
async def get_transparency(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TransparencyResponse:
    """Public endpoint exposing oversight classification and pipeline health."""

    # --- last_approvals ---
    last_approvals: dict = {}
    for gate_type in _GATE_TYPES:
        result = await session.execute(
            select(PipelineApproval)
            .where(
                PipelineApproval.gate_type == gate_type,
                PipelineApproval.status.in_(["approved", "rejected"]),
            )
            .order_by(PipelineApproval.decided_at.desc())
            .limit(1)
        )
        approval = result.scalar_one_or_none()
        if approval is not None:
            last_approvals[gate_type] = {
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                "status": approval.status,
            }

    # --- pipeline_health ---
    result = await session.execute(
        select(IngestionRun)
        .where(IngestionRun.status == "completed")
        .order_by(IngestionRun.completed_at.desc())
        .limit(1)
    )
    last_run = result.scalar_one_or_none()
    pipeline_health: dict = {
        "status": "idle",
        "last_successful_run": (
            last_run.completed_at.isoformat() if last_run and last_run.completed_at else None
        ),
    }

    return TransparencyResponse(
        oversight_levels=OVERSIGHT_LEVELS,
        last_approvals=last_approvals,
        pipeline_health=pipeline_health,
    )
