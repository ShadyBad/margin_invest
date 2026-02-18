"""Institutional metrics API response schema."""

from __future__ import annotations

from pydantic import BaseModel


class InstitutionalMetricsResponse(BaseModel):
    """Pre-computed institutional-grade metrics for a single ticker."""

    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    volatility: float | None = None
    avg_profit_margin: float | None = None
    risk_classification: str = "Unknown"
    allocation_weight: float | None = None
    margin_of_safety: float | None = None
