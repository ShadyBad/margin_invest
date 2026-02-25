"""FastAPI application factory."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from margin_api import __version__
from margin_api.config import get_settings
from margin_api.routes.admin import router as admin_router
from margin_api.routes.auth import router as auth_router
from margin_api.routes.avatar import router as avatar_router
from margin_api.routes.backtest import router as backtest_router
from margin_api.routes.billing import router as billing_router
from margin_api.routes.correlations import router as correlations_router
from margin_api.routes.dashboard import router as dashboard_router
from margin_api.routes.dna import router as dna_router
from margin_api.routes.events import router as events_router
from margin_api.routes.health import router as health_router
from margin_api.routes.ingestion import router as ingestion_router
from margin_api.routes.jobs import router as jobs_router
from margin_api.routes.keys import router as keys_router
from margin_api.routes.metrics import router as metrics_router
from margin_api.routes.scores import router as scores_router
from margin_api.routes.thirteenf import router as thirteenf_router
from margin_api.routes.universe import router as universe_router
from margin_api.routes.v3_scores import router as v3_scores_router
from margin_api.schemas.errors import ErrorResponse
from margin_api.ws.scores import router as ws_router

logger = logging.getLogger(__name__)


class RequestIdMiddleware:
    """Attach a unique request ID to every request/response.

    Implemented as a pure ASGI middleware (not BaseHTTPMiddleware)
    to avoid the task-context issues that BaseHTTPMiddleware causes
    with asyncpg and other async database drivers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_request_id)


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

    # Request ID
    app.add_middleware(RequestIdMiddleware)

    # Routes
    app.include_router(admin_router)
    app.include_router(auth_router)
    app.include_router(avatar_router)
    app.include_router(billing_router)
    app.include_router(health_router)
    app.include_router(keys_router)
    app.include_router(metrics_router)
    app.include_router(scores_router)
    app.include_router(v3_scores_router)
    app.include_router(dashboard_router)
    app.include_router(dna_router)
    app.include_router(events_router)
    app.include_router(ingestion_router)
    app.include_router(jobs_router)
    app.include_router(backtest_router)
    app.include_router(thirteenf_router)
    app.include_router(universe_router)
    app.include_router(correlations_router)
    app.include_router(thirteenf_router)
    app.include_router(ws_router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=(
                    detail.upper().replace(" ", "_") if exc.status_code == 404 else "HTTP_ERROR"
                ),
                message=detail,
                request_id=request_id,
                status_code=exc.status_code,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error("[%s] Unhandled exception: %s", request_id, exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
                request_id=request_id,
                status_code=500,
            ).model_dump(),
        )

    return app
