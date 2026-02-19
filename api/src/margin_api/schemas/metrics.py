"""Institutional metrics API response schema."""

from __future__ import annotations

from pydantic import BaseModel


class MetricStatus(BaseModel):
    """A metric value with optional unavailability reason."""

    value: float | None = None
    unavailable_reason: str | None = None


class InstitutionalMetricsResponse(BaseModel):
    """Pre-computed institutional-grade metrics for a single ticker."""

    sharpe_ratio: MetricStatus = MetricStatus()
    max_drawdown: MetricStatus = MetricStatus()
    volatility: MetricStatus = MetricStatus()
    avg_profit_margin: MetricStatus = MetricStatus()
    risk_classification: str = "Unknown"
    allocation_weight: MetricStatus = MetricStatus()
    margin_of_safety: MetricStatus = MetricStatus()
