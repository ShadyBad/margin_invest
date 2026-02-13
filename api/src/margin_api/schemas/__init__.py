"""API response schemas."""

from margin_api.schemas.backtest import (
    BacktestConfigRequest,
    BacktestListResponse,
    BacktestResultResponse,
    BacktestSummaryResponse,
    MetricsResponse,
    ValidationCheckResponse,
    ValidationResponse,
)
from margin_api.schemas.dashboard import DashboardResponse, PickSummary, WatchlistItem
from margin_api.schemas.events import (
    EventListResponse,
    EventResponse,
    NotificationListResponse,
    NotificationResponse,
)
from margin_api.schemas.scores import (
    FactorBreakdownResponse,
    FactorScoreResponse,
    FilterResultResponse,
    ScoreListResponse,
    ScoreResponse,
)

__all__ = [
    "BacktestConfigRequest",
    "BacktestListResponse",
    "BacktestResultResponse",
    "BacktestSummaryResponse",
    "DashboardResponse",
    "EventListResponse",
    "EventResponse",
    "FactorBreakdownResponse",
    "FactorScoreResponse",
    "FilterResultResponse",
    "MetricsResponse",
    "NotificationListResponse",
    "NotificationResponse",
    "PickSummary",
    "ScoreListResponse",
    "ScoreResponse",
    "ValidationCheckResponse",
    "ValidationResponse",
    "WatchlistItem",
]
