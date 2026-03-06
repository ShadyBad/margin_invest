"""Tests for PostHog analytics wrapper."""

from unittest.mock import patch

from margin_api.services import analytics
from margin_api.services.analytics import shutdown, track_event


def test_track_event_noop_without_env_var():
    """track_event is a no-op when POSTHOG_API_KEY is not set."""
    analytics._client = None
    with patch.dict("os.environ", {}, clear=True):
        # Should not raise
        track_event("user-1", "test_event", {"key": "value"})


def test_shutdown_noop_without_client():
    """shutdown is safe to call even if client was never initialized."""
    analytics._client = None
    shutdown()  # Should not raise
