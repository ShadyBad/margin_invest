"""Correlation endpoint schemas."""

from datetime import datetime

from pydantic import BaseModel


class ExcludedTickerResponse(BaseModel):
    ticker: str
    reason: str


class CorrelationResponse(BaseModel):
    tickers: list[str]
    method: str
    matrix: list[list[float | None]]
    sample_sizes: list[list[int]]
    excluded: list[ExcludedTickerResponse]
    window_days: int
    computed_at: datetime
