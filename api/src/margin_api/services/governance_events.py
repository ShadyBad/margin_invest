"""Governance event emitter — writes audit events to a Redis stream.

This is a fire-and-forget telemetry service. Failures are logged as warnings
and never propagated to the caller. Events are consumed downstream by a
rollup worker that reads from the stream and inserts aggregated rows into
the database.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

STREAM_KEY = "governance:events"


class GovernanceEventEmitter:
    """Emit lightweight governance events to a Redis stream."""

    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def emit(
        self,
        event_type: str,
        source: str,
        detail: dict[str, Any] | None = None,
    ) -> bytes | str | None:
        """Write an event to the governance stream.

        Returns the stream entry ID on success, or None on any failure.
        Never raises — all exceptions are caught and logged as warnings.
        """
        fields = {
            "event_type": event_type,
            "source": source,
            "detail": json.dumps(detail),
            "created_at": datetime.now(UTC).isoformat(),
        }
        try:
            return await self._redis.xadd(STREAM_KEY, fields)
        except Exception:
            logger.warning(
                "Failed to emit governance event %s from %s",
                event_type,
                source,
                exc_info=True,
            )
            return None
