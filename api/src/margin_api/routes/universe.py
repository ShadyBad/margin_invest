"""Universe status API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.session import get_db
from margin_api.schemas.universe import UniverseStatusResponse
from margin_api.services.universe import get_active_snapshot

router = APIRouter(prefix="/api/v1", tags=["universe"])


@router.get("/universe/status", response_model=UniverseStatusResponse)
async def get_universe_status(db: AsyncSession = Depends(get_db)):
    """Return full universe completeness status."""
    snapshot = await get_active_snapshot(db)
    if snapshot is None:
        return UniverseStatusResponse(
            universe_version="none",
            universe_size=0,
            assets_ingested=0,
            assets_scored=0,
            assets_fresh=0,
            assets_stale=0,
            assets_expired=0,
            assets_quarantined=0,
            assets_permanently_skipped=0,
            ingestion_coverage=0.0,
            scoring_coverage=0.0,
            last_ingestion_run=None,
            last_scoring_run=None,
            is_complete=False,
        )
    return UniverseStatusResponse(
        universe_version=snapshot.version,
        universe_size=snapshot.ticker_count,
        assets_ingested=0,
        assets_scored=0,
        assets_fresh=0,
        assets_stale=0,
        assets_expired=0,
        assets_quarantined=0,
        assets_permanently_skipped=0,
        ingestion_coverage=0.0,
        scoring_coverage=0.0,
        last_ingestion_run=None,
        last_scoring_run=None,
        is_complete=False,
    )
