"""Schemas for sector list and champion endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class SectorSummary(BaseModel):
    sector: str
    asset_count: int
    avg_composite_score: float
    top_ticker: str
    top_score: float


class SectorChampionDetail(BaseModel):
    """Named SectorChampionDetail to avoid collision with SectorChampionResponse in scores.py."""

    ticker: str
    sector: str
    composite_score: float
    composite_tier: str
    signal: str
    market_cap: float | None
