"""Pydantic schemas for watchlist and alert endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class WatchlistItemResponse(BaseModel):
    """A single watchlist entry with latest score data."""

    ticker: str
    name: str | None = None
    sector: str | None = None
    composite_score: float | None = None
    composite_tier: str | None = None
    signal: str | None = None
    added_at: datetime

    model_config = {"from_attributes": True}


class WatchlistResponse(BaseModel):
    """List of user's watchlist items."""

    items: list[WatchlistItemResponse]
    count: int


class AlertCreateRequest(BaseModel):
    """Request body for creating a score alert."""

    ticker: str = Field(..., min_length=1, max_length=20)
    alert_type: str = Field(..., pattern="^(above|below|survivor)$")
    threshold: float | None = None

    @model_validator(mode="after")
    def threshold_required_for_score_alerts(self) -> AlertCreateRequest:
        if self.alert_type in ("above", "below") and self.threshold is None:
            msg = "threshold is required for 'above' and 'below' alert types"
            raise ValueError(msg)
        if self.alert_type == "survivor" and self.threshold is not None:
            self.threshold = None
        return self


class AlertResponse(BaseModel):
    """A single alert entry."""

    id: int
    ticker: str
    alert_type: str
    threshold: float | None = None
    is_active: bool
    last_triggered_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """List of user's alerts."""

    items: list[AlertResponse]
    count: int
