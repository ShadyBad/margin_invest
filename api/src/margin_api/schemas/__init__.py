"""API response schemas."""

from margin_api.schemas.correlations import CorrelationResponse, ExcludedTickerResponse
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
from margin_api.schemas.universe import (
    UniverseStatusResponse,
    UniverseSummary,
    Warning,
)

__all__ = [
    "BacktestConfigRequest",
    "CorrelationResponse",
    "ExcludedTickerResponse",
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
    "UniverseStatusResponse",
    "UniverseSummary",
    "ValidationCheckResponse",
    "ValidationResponse",
    "Warning",
    "WatchlistItem",
]
