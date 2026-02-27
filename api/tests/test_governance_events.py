"""Tests for GovernanceEventEmitter — Redis stream audit telemetry."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from margin_api.services.governance_events import STREAM_KEY, GovernanceEventEmitter


@pytest.fixture()
def mock_redis():
    """Create a mock Redis client with async xadd."""
    redis = AsyncMock()
    redis.xadd = AsyncMock(return_value=b"1234567890-0")
    return redis


class TestGovernanceEventEmitter:
    @pytest.mark.asyncio
    async def test_emit_calls_xadd_with_correct_stream_key(self, mock_redis):
        emitter = GovernanceEventEmitter(mock_redis)
        await emitter.emit("filter.override", "worker:score")

        mock_redis.xadd.assert_called_once()
        call_args = mock_redis.xadd.call_args
        assert call_args[0][0] == STREAM_KEY

    @pytest.mark.asyncio
    async def test_emit_calls_xadd_with_correct_fields(self, mock_redis):
        emitter = GovernanceEventEmitter(mock_redis)
        detail = {"ticker": "AAPL", "reason": "manual override"}
        await emitter.emit("filter.override", "worker:score", detail=detail)

        call_args = mock_redis.xadd.call_args
        fields = call_args[0][1]
        assert fields["event_type"] == "filter.override"
        assert fields["source"] == "worker:score"
        assert json.loads(fields["detail"]) == detail
        assert "created_at" in fields

    @pytest.mark.asyncio
    async def test_emit_returns_entry_id_on_success(self, mock_redis):
        emitter = GovernanceEventEmitter(mock_redis)
        result = await emitter.emit("score.complete", "worker:v4")

        assert result == b"1234567890-0"

    @pytest.mark.asyncio
    async def test_emit_returns_none_and_logs_warning_on_failure(self, mock_redis):
        mock_redis.xadd.side_effect = ConnectionError("Redis down")
        emitter = GovernanceEventEmitter(mock_redis)

        with patch("margin_api.services.governance_events.logger") as mock_logger:
            result = await emitter.emit("score.complete", "worker:v4")

        assert result is None
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_serializes_detail_dict_to_json_string(self, mock_redis):
        emitter = GovernanceEventEmitter(mock_redis)
        detail = {"count": 42, "nested": {"key": "value"}}
        await emitter.emit("ingest.batch", "worker:ingest", detail=detail)

        call_args = mock_redis.xadd.call_args
        fields = call_args[0][1]
        # Must be a string, not a dict
        assert isinstance(fields["detail"], str)
        assert json.loads(fields["detail"]) == detail

    @pytest.mark.asyncio
    async def test_emit_with_no_detail_sends_null_json(self, mock_redis):
        emitter = GovernanceEventEmitter(mock_redis)
        await emitter.emit("heartbeat", "scheduler")

        call_args = mock_redis.xadd.call_args
        fields = call_args[0][1]
        assert fields["detail"] == "null"

    @pytest.mark.asyncio
    async def test_emit_created_at_is_iso_format(self, mock_redis):
        emitter = GovernanceEventEmitter(mock_redis)
        await emitter.emit("test.event", "test")

        call_args = mock_redis.xadd.call_args
        fields = call_args[0][1]
        # Should be parseable as ISO datetime
        from datetime import datetime

        dt = datetime.fromisoformat(fields["created_at"])
        assert dt.tzinfo is not None  # Should be timezone-aware

    @pytest.mark.asyncio
    async def test_stream_key_constant(self):
        assert STREAM_KEY == "governance:events"
