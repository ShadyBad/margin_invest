"""PostHog server-side analytics client."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Lazily initialize the PostHog client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("POSTHOG_API_KEY")
    host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")

    if not api_key:
        return None

    from posthog import Posthog

    _client = Posthog(api_key, host=host)
    logger.info("[analytics] PostHog initialized (host=%s)", host)
    return _client


def track_event(distinct_id: str, event: str, properties: dict | None = None) -> None:
    """Track a server-side event. No-ops if PostHog is not configured."""
    client = _get_client()
    if client is None:
        return
    client.capture(distinct_id, event, properties=properties or {})


def shutdown() -> None:
    """Flush pending events and shut down the client."""
    global _client
    if _client is not None:
        _client.shutdown()
        _client = None
        logger.info("[analytics] PostHog shut down")
