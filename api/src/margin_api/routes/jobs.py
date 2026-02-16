"""Job status API endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import JobRun
from margin_api.db.session import get_db

router = APIRouter(prefix="/api/v1", tags=["jobs"])


class JobRunResponse(BaseModel):
    id: int
    job_type: str
    status: str
    progress: float
    progress_detail: str | None
    triggered_by: str
    parent_job_id: int | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


@router.get("/jobs/latest", response_model=list[JobRunResponse])
async def get_latest_jobs(
    limit: int = 10,
    session: AsyncSession = Depends(get_db),
):
    """Return the most recent job runs."""
    result = await session.execute(
        select(JobRun).order_by(JobRun.id.desc()).limit(limit)
    )
    jobs = result.scalars().all()
    return [
        JobRunResponse(
            id=j.id,
            job_type=j.job_type,
            status=j.status,
            progress=j.progress,
            progress_detail=j.progress_detail,
            triggered_by=j.triggered_by,
            parent_job_id=j.parent_job_id,
            error_message=j.error_message,
            started_at=j.started_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]
