"""WebSocket modules for real-time communication."""

from __future__ import annotations

from margin_api.ws.scores import (
    ConnectionManager,
    ScoreChangeMessage,
    manager,
    router as ws_router,
)

__all__ = [
    "ConnectionManager",
    "ScoreChangeMessage",
    "manager",
    "ws_router",
]
