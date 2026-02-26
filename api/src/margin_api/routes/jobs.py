"""Job status API endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import IngestionRun, JobRun
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
    pipeline_id: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class PipelineStageResponse(BaseModel):
    stage: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class PipelineStatusResponse(BaseModel):
    pipeline_id: str
    status: str  # running | completed | failed
    stages: list[PipelineStageResponse]


@router.get("/jobs/latest", response_model=list[JobRunResponse])
async def get_latest_jobs(
    limit: int = 10,
    session: AsyncSession = Depends(get_db),
):
    """Return the most recent job runs."""
    result = await session.execute(select(JobRun).order_by(JobRun.id.desc()).limit(limit))
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
            pipeline_id=j.pipeline_id,
            error_message=j.error_message,
            started_at=j.started_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]


@router.get("/jobs/pipeline/{pipeline_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    pipeline_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Return the end-to-end status of a pipeline run.

    Aggregates the IngestionRun and all JobRuns sharing the same pipeline_id
    into a single view with per-stage status and an overall pipeline status.
    """
    stages: list[PipelineStageResponse] = []

    # Ingestion stage
    ingest_result = await session.execute(
        select(IngestionRun)
        .where(IngestionRun.pipeline_id == pipeline_id)
        .order_by(IngestionRun.id.desc())
        .limit(1)
    )
    ingest_run = ingest_result.scalar_one_or_none()
    if ingest_run:
        stages.append(
            PipelineStageResponse(
                stage="ingest",
                status=ingest_run.status,
                started_at=ingest_run.started_at,
                completed_at=ingest_run.completed_at,
                error_message=None,
            )
        )

    # Scoring stages (v2, v3)
    job_result = await session.execute(
        select(JobRun).where(JobRun.pipeline_id == pipeline_id).order_by(JobRun.id.asc())
    )
    job_runs = job_result.scalars().all()
    for j in job_runs:
        stages.append(
            PipelineStageResponse(
                stage=j.job_type,
                status=j.status,
                started_at=j.started_at,
                completed_at=j.completed_at,
                error_message=j.error_message,
            )
        )

    if not stages:
        raise HTTPException(404, f"No pipeline found with id: {pipeline_id}")

    # Derive overall status: running if any stage running, failed if any failed,
    # completed only if all stages completed
    all_statuses = [s.status for s in stages]
    if any(s == "running" for s in all_statuses):
        overall = "running"
    elif any(s == "failed" for s in all_statuses):
        overall = "failed"
    else:
        overall = "completed"

    return PipelineStatusResponse(
        pipeline_id=pipeline_id,
        status=overall,
        stages=stages,
    )
