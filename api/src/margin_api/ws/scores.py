"""WebSocket endpoint for live score change notifications."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

router = APIRouter()


class ScoreChangeMessage(BaseModel):
    """Message sent when a score changes by more than 5 points."""

    ticker: str
    old_score: float
    new_score: float
    delta: float
    severity: str  # "minor", "moderate", "major"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ConnectionManager:
    """Manages active WebSocket connections for score updates."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a WebSocket connection and track it."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: ScoreChangeMessage) -> None:
        """Send a score change message to all active connections."""
        data = message.model_dump(mode="json")
        disconnected: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except (WebSocketDisconnect, RuntimeError):
                disconnected.append(connection)
        # Clean up any connections that failed during broadcast
        for connection in disconnected:
            self.disconnect(connection)

    async def send_personal(
        self, message: ScoreChangeMessage, websocket: WebSocket
    ) -> None:
        """Send a score change message to a specific connection."""
        data = message.model_dump(mode="json")
        await websocket.send_json(data)


# Module-level singleton used across the application
manager = ConnectionManager()


@router.websocket("/ws/scores")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for live score update notifications.

    Accepts the connection, then enters a keep-alive loop that listens
    for client messages (heartbeats / pings). The connection is removed
    from the manager on disconnect.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Wait for any client message (heartbeat / ping / pong)
            data = await websocket.receive_text()
            # Echo pong for heartbeat pings
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
