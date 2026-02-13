"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from margin_api import __version__
from margin_api.config import get_settings
from margin_api.routes.dashboard import router as dashboard_router
from margin_api.routes.health import router as health_router
from margin_api.routes.scores import router as scores_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Margin Invest API",
        version=__version__,
        description="Deterministic investment analysis platform",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health_router)
    app.include_router(scores_router)
    app.include_router(dashboard_router)

    return app
