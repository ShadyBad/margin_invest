"""Sector list and champion API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.session import get_db
from margin_api.schemas.sectors import SectorChampionDetail, SectorSummary
from margin_api.services.sector_stats import get_sector_champion_detail, list_sector_summaries

router = APIRouter(prefix="/api/v1/sectors", tags=["sectors"])


@router.get("", response_model=list[SectorSummary])
async def list_sectors(db: AsyncSession = Depends(get_db)) -> list[SectorSummary]:
    """Return a summary for every sector that has at least one published V4 score."""
    rows = await list_sector_summaries(db)
    return [SectorSummary(**row) for row in rows]


@router.get("/{sector}/champion", response_model=SectorChampionDetail)
async def get_champion(sector: str, db: AsyncSession = Depends(get_db)) -> SectorChampionDetail:
    """Return the highest-scored published ticker in a sector.

    Raises 404 if the sector has no published scores.
    """
    detail = await get_sector_champion_detail(db, sector)
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"No published scores found for sector '{sector}'",
        )
    return SectorChampionDetail(**detail)
