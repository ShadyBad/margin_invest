"""Universe status API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, IngestionRun, Score
from margin_api.db.session import get_db
from margin_api.schemas.universe import UniverseStatusResponse
from margin_api.services.freshness import FRESH_THRESHOLD, STALE_THRESHOLD
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

    now = datetime.now(UTC)
    fresh_cutoff = now - FRESH_THRESHOLD
    stale_cutoff = now - STALE_THRESHOLD

    # Count assets with financial data (ingested)
    ingested_result = await db.execute(
        select(func.count(func.distinct(Asset.id)))
        .select_from(Asset)
        .join(Score, Score.asset_id == Asset.id, isouter=False)
    )
    assets_ingested = ingested_result.scalar() or 0

    # Count scored assets (those with at least one score)
    scored_result = await db.execute(select(func.count(func.distinct(Score.asset_id))))
    assets_scored = scored_result.scalar() or 0

    # Freshness breakdown — count by latest score age
    # Fresh: scored_at > fresh_cutoff
    fresh_result = await db.execute(
        select(func.count(func.distinct(Score.asset_id))).where(Score.scored_at > fresh_cutoff)
    )
    assets_fresh = fresh_result.scalar() or 0

    # Expired: scored_at <= stale_cutoff
    expired_result = await db.execute(
        select(func.count(func.distinct(Score.asset_id))).where(Score.scored_at <= stale_cutoff)
    )
    assets_expired = expired_result.scalar() or 0

    # Stale: everything scored minus fresh minus expired
    assets_stale = max(0, assets_scored - assets_fresh - assets_expired)

    # Asset status counts
    quarantined_result = await db.execute(
        select(func.count()).where(Asset.ingestion_status == "quarantined")
    )
    assets_quarantined = quarantined_result.scalar() or 0

    skipped_result = await db.execute(
        select(func.count()).where(Asset.ingestion_status == "permanently_skipped")
    )
    assets_permanently_skipped = skipped_result.scalar() or 0

    # Last runs
    last_ingest_result = await db.execute(select(func.max(IngestionRun.started_at)))
    last_ingestion_run = last_ingest_result.scalar()

    last_score_result = await db.execute(select(func.max(Score.scored_at)))
    last_scoring_run = last_score_result.scalar()

    # Coverage
    universe_size = snapshot.ticker_count
    ingestion_coverage = assets_ingested / universe_size if universe_size > 0 else 0.0
    scoring_coverage = assets_scored / universe_size if universe_size > 0 else 0.0
    is_complete = ingestion_coverage >= 0.95 and scoring_coverage >= 0.95

    return UniverseStatusResponse(
        universe_version=snapshot.version,
        universe_size=universe_size,
        assets_ingested=assets_ingested,
        assets_scored=assets_scored,
        assets_fresh=assets_fresh,
        assets_stale=assets_stale,
        assets_expired=assets_expired,
        assets_quarantined=assets_quarantined,
        assets_permanently_skipped=assets_permanently_skipped,
        ingestion_coverage=round(ingestion_coverage, 4),
        scoring_coverage=round(scoring_coverage, 4),
        last_ingestion_run=last_ingestion_run,
        last_scoring_run=last_scoring_run,
        is_complete=is_complete,
    )
