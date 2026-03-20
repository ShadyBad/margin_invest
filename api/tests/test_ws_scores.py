"""Tests for WebSocket score update endpoint."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from margin_api.ws.scores import ConnectionManager, ScoreChangeMessage, manager, router


def _create_test_app() -> FastAPI:
    """Create a minimal app with just the WebSocket router for testing."""
    app = FastAPI()
    app.include_router(router)
    return app


def _make_message(**overrides) -> ScoreChangeMessage:
    """Helper to build a ScoreChangeMessage with sensible defaults."""
    defaults = {
        "ticker": "AAPL",
        "old_score": 72.0,
        "new_score": 85.0,
        "delta": 13.0,
        "severity": "major",
    }
    defaults.update(overrides)
    return ScoreChangeMessage(**defaults)


class TestScoreChangeMessage:
    """ScoreChangeMessage serialisation and defaults."""

    def test_serializes_to_json(self):
        msg = _make_message()
        data = msg.model_dump(mode="json")
        assert data["ticker"] == "AAPL"
        assert data["old_score"] == 72.0
        assert data["new_score"] == 85.0
        assert data["delta"] == 13.0
        assert data["severity"] == "major"

    def test_auto_generates_event_id(self):
        msg = _make_message()
        assert msg.event_id is not None
        assert len(msg.event_id) > 0

    def test_auto_generates_timestamp(self):
        msg = _make_message()
        assert isinstance(msg.timestamp, datetime)

    def test_each_message_gets_unique_event_id(self):
        msg1 = _make_message()
        msg2 = _make_message()
        assert msg1.event_id != msg2.event_id

    def test_custom_fields_override_defaults(self):
        ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        msg = _make_message(
            ticker="MSFT",
            old_score=50.0,
            new_score=60.0,
            delta=10.0,
            severity="moderate",
            timestamp=ts,
            event_id="custom-id",
        )
        assert msg.ticker == "MSFT"
        assert msg.timestamp == ts
        assert msg.event_id == "custom-id"

    def test_timestamp_in_json_is_string(self):
        msg = _make_message()
        data = msg.model_dump(mode="json")
        assert isinstance(data["timestamp"], str)

    def test_all_fields_present_in_json(self):
        msg = _make_message()
        data = msg.model_dump(mode="json")
        expected_keys = {
            "ticker",
            "old_score",
            "new_score",
            "delta",
            "severity",
            "timestamp",
            "event_id",
        }
        assert set(data.keys()) == expected_keys


class TestConnectionManager:
    """ConnectionManager tracks and cleans up connections."""

    def test_starts_with_no_connections(self):
        mgr = ConnectionManager()
        assert mgr.active_connections == []

    def test_connect_accepts_and_adds(self):
        mgr = ConnectionManager()
        ws = AsyncMock()

        asyncio.run(mgr.connect(ws))
        ws.accept.assert_awaited_once()
        assert ws in mgr.active_connections

    def test_disconnect_removes_connection(self):
        mgr = ConnectionManager()
        sentinel = object()
        mgr.active_connections.append(sentinel)
        assert len(mgr.active_connections) == 1
        mgr.disconnect(sentinel)
        assert mgr.active_connections == []

    def test_disconnect_ignores_unknown_connection(self):
        mgr = ConnectionManager()
        sentinel = object()
        mgr.disconnect(sentinel)  # should not raise
        assert mgr.active_connections == []

    def test_broadcast_sends_to_all_connections(self):
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        mgr.active_connections = [ws1, ws2]

        msg = _make_message(ticker="GOOG")
        expected_data = msg.model_dump(mode="json")

        asyncio.run(mgr.broadcast(msg))

        ws1.send_json.assert_awaited_once_with(expected_data)
        ws2.send_json.assert_awaited_once_with(expected_data)

    def test_send_personal_sends_to_single_connection(self):
        mgr = ConnectionManager()
        ws = AsyncMock()

        msg = _make_message(ticker="TSLA")
        expected_data = msg.model_dump(mode="json")

        asyncio.run(mgr.send_personal(msg, ws))

        ws.send_json.assert_awaited_once_with(expected_data)


class TestWebSocketEndpoint:
    """Integration tests for the /ws/scores endpoint."""

    def test_websocket_connects_successfully(self):
        app = _create_test_app()
        client = TestClient(app)
        with client.websocket_connect("/ws/scores") as ws:
            # Connection accepted -- send a ping to verify it's alive
            ws.send_text("ping")
            reply = ws.receive_text()
            assert reply == "pong"

    def test_websocket_heartbeat_ping_pong(self):
        app = _create_test_app()
        client = TestClient(app)
        with client.websocket_connect("/ws/scores") as ws:
            for _ in range(3):
                ws.send_text("ping")
                assert ws.receive_text() == "pong"

    def test_manager_tracks_active_connections(self):
        app = _create_test_app()
        client = TestClient(app)

        assert len(manager.active_connections) == 0

        with client.websocket_connect("/ws/scores"):
            assert len(manager.active_connections) == 1

    def test_manager_removes_disconnected_clients(self):
        app = _create_test_app()
        client = TestClient(app)

        with client.websocket_connect("/ws/scores"):
            assert len(manager.active_connections) == 1

        # After the context manager exits, the client disconnects
        assert len(manager.active_connections) == 0

    def test_non_ping_message_does_not_echo(self):
        """Sending non-ping text doesn't cause an error (loop continues)."""
        app = _create_test_app()
        client = TestClient(app)
        with client.websocket_connect("/ws/scores") as ws:
            # Send a non-ping message; endpoint should not crash
            ws.send_text("heartbeat")
            # Follow up with ping to verify connection is still alive
            ws.send_text("ping")
            reply = ws.receive_text()
            assert reply == "pong"


class TestBroadcastDisconnectCleanup:
    """Tests for broadcast removing disconnected clients."""

    def test_broadcast_removes_failed_connection(self):
        """When send_json raises RuntimeError, the connection is removed."""
        from margin_api.ws.scores import ConnectionManager, ScoreChangeMessage

        mgr = ConnectionManager()
        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send_json = AsyncMock(side_effect=RuntimeError("Connection broken"))

        mgr.active_connections = [bad_ws, good_ws]

        msg = ScoreChangeMessage(
            ticker="AAPL",
            old_score=70.0,
            new_score=80.0,
            delta=10.0,
            severity="moderate",
        )

        asyncio.run(mgr.broadcast(msg))

        # Bad connection should have been removed
        assert bad_ws not in mgr.active_connections
        assert good_ws in mgr.active_connections
        # Good connection should still have received the message
        good_ws.send_json.assert_awaited_once()

    def test_broadcast_removes_websocket_disconnect(self):
        """When send_json raises WebSocketDisconnect, connection is removed."""
        from fastapi import WebSocketDisconnect
        from margin_api.ws.scores import ConnectionManager, ScoreChangeMessage

        mgr = ConnectionManager()
        disconnected_ws = AsyncMock()
        disconnected_ws.send_json = AsyncMock(
            side_effect=WebSocketDisconnect(code=1001, reason="Going away")
        )

        mgr.active_connections = [disconnected_ws]

        msg = ScoreChangeMessage(
            ticker="MSFT",
            old_score=60.0,
            new_score=75.0,
            delta=15.0,
            severity="major",
        )

        asyncio.run(mgr.broadcast(msg))

        # Disconnected WS should be cleaned up
        assert disconnected_ws not in mgr.active_connections
