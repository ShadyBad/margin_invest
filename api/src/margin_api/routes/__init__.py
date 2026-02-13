"""API route modules."""

from __future__ import annotations

from margin_api.routes.dashboard import router as dashboard_router
from margin_api.routes.health import router as health_router
from margin_api.routes.scores import router as scores_router

__all__ = [
    "dashboard_router",
    "health_router",
    "scores_router",
]
