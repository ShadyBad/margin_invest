"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from margin_api import __version__
from margin_api.config import get_settings
from margin_api.routes.auth import router as auth_router
from margin_api.routes.avatar import router as avatar_router
from margin_api.routes.backtest import router as backtest_router
from margin_api.routes.billing import router as billing_router
from margin_api.routes.dashboard import router as dashboard_router
from margin_api.routes.events import router as events_router
from margin_api.routes.health import router as health_router
from margin_api.routes.ingestion import router as ingestion_router
from margin_api.routes.jobs import router as jobs_router
from margin_api.routes.keys import router as keys_router
from margin_api.routes.scores import router as scores_router
from margin_api.routes.universe import router as universe_router
from margin_api.routes.v3_scores import router as v3_scores_router
from margin_api.ws.scores import router as ws_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    _local_hosts = ("localhost", "127.0.0.1", "0.0.0.0")
    if settings.environment == "production" and any(
        h in settings.database_url for h in _local_hosts
    ):
        raise RuntimeError(
            "MARGIN_DATABASE_URL points to a local address in production mode. "
            "Set MARGIN_DATABASE_URL to your Timescale Cloud connection string."
        )

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
    app.include_router(auth_router)
    app.include_router(avatar_router)
    app.include_router(billing_router)
    app.include_router(health_router)
    app.include_router(keys_router)
    app.include_router(scores_router)
    app.include_router(v3_scores_router)
    app.include_router(dashboard_router)
    app.include_router(events_router)
    app.include_router(ingestion_router)
    app.include_router(jobs_router)
    app.include_router(backtest_router)
    app.include_router(universe_router)
    app.include_router(ws_router)

    return app
