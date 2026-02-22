"""Score history response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ScoreHistoryPoint(BaseModel):
    scored_at: datetime
    composite_percentile: float
    composite_raw_score: float | None = None
    quality_percentile: float | None = None
    value_percentile: float | None = None
    momentum_percentile: float | None = None
    conviction_level: str
    signal: str
    margin_invest_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    delta: float | None = None


class ScoreHistoryResponse(BaseModel):
    ticker: str
    points: list[ScoreHistoryPoint]
    total_runs: int
