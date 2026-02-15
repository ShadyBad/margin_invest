"""API route modules."""

from __future__ import annotations

from margin_api.routes.auth import router as auth_router
from margin_api.routes.backtest import router as backtest_router
from margin_api.routes.billing import router as billing_router
from margin_api.routes.dashboard import router as dashboard_router
from margin_api.routes.events import router as events_router
from margin_api.routes.health import router as health_router
from margin_api.routes.scores import router as scores_router

__all__ = [
    "auth_router",
    "backtest_router",
    "billing_router",
    "dashboard_router",
    "events_router",
    "health_router",
    "scores_router",
]
