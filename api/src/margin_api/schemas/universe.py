"""Universe-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UniverseSummary(BaseModel):
    """Lightweight universe metadata included in dashboard/score responses."""

    version: str
    size: int
    scoring_coverage: float
    is_complete: bool
    last_scoring_run: datetime | None


class UniverseStatusResponse(BaseModel):
    """Full universe status for the /universe/status endpoint."""

    universe_version: str
    universe_size: int
    assets_ingested: int
    assets_scored: int
    assets_fresh: int
    assets_stale: int
    assets_expired: int
    assets_quarantined: int
    assets_permanently_skipped: int
    ingestion_coverage: float
    scoring_coverage: float
    last_ingestion_run: datetime | None
    last_scoring_run: datetime | None
    is_complete: bool


class UniverseFunnelResponse(BaseModel):
    """Selectivity funnel for the landing page."""

    universe_size: int
    survived_filters: int
    exceptional_count: int
    high_count: int
    medium_count: int
    last_scored_at: datetime | None


class Warning(BaseModel):
    """Structured warning for incomplete universe coverage."""

    code: str
    message: str
    severity: str  # "warning" | "error"
