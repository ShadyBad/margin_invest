"""Ingestion run API endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import IngestionRun
from margin_api.db.session import get_db

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


class IngestionRunResponse(BaseModel):
    id: int
    snapshot_id: int
    run_type: str
    tickers_requested: int
    tickers_succeeded: int
    tickers_failed: int
    tickers_skipped: int
    status: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None


class LastRunInfo(BaseModel):
    status: str
    succeeded: int
    failed: int
    started_at: str
    duration_seconds: float | None


class IngestionStatusResponse(BaseModel):
    universe_version: str | None
    total_tickers: int
    fresh_tickers: int
    quarantined_tickers: int
    coverage_pct: float
    last_run: LastRunInfo | None


class CompletenessResponse(BaseModel):
    ready: bool
    coverage_pct: float
    scored_tickers: int
    total_tickers: int
    reason: str | None = None
    message: str | None = None


MINIMUM_COVERAGE = 0.90


@router.get("/ingestion/runs", response_model=list[IngestionRunResponse])
async def get_ingestion_runs(
    limit: int = 10,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """Return ingestion runs with pagination."""
    result = await session.execute(
        select(IngestionRun).order_by(IngestionRun.id.desc()).offset(offset).limit(limit)
    )
    runs = result.scalars().all()
    return [
        IngestionRunResponse(
            id=r.id,
            snapshot_id=r.snapshot_id,
            run_type=r.run_type,
            tickers_requested=r.tickers_requested,
            tickers_succeeded=r.tickers_succeeded,
            tickers_failed=r.tickers_failed,
            tickers_skipped=r.tickers_skipped,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            duration_seconds=r.duration_seconds,
        )
        for r in runs
    ]
