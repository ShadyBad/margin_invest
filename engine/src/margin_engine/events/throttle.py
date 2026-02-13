"""Notification throttle — enforces rate limits on per-asset notifications."""

from __future__ import annotations

from datetime import datetime, timedelta

from margin_engine.events.models import EventSeverity

# Default cooldown period between notifications for the same ticker.
_DEFAULT_COOLDOWN = timedelta(hours=1)


class NotificationThrottle:
    """Enforces max 1 notification per asset per hour, unless MAJOR severity.

    MAJOR events always bypass the throttle and are allowed through.
    For all other severities, a second notification for the same ticker
    within the cooldown window is suppressed.
    """

    def __init__(self, cooldown: timedelta = _DEFAULT_COOLDOWN) -> None:
        self._cooldown = cooldown
        self._last_notified: dict[str, datetime] = {}

    def should_notify(
        self, ticker: str, severity: EventSeverity, now: datetime
    ) -> bool:
        """Return True if a notification should be sent for this ticker.

        Rules:
        - MAJOR severity always returns True (bypasses throttle).
        - Otherwise, returns True only if the ticker has not been notified
          within the cooldown window.
        """
        if severity == EventSeverity.MAJOR:
            return True

        last = self._last_notified.get(ticker)
        if last is None:
            return True

        return (now - last) >= self._cooldown

    def record_notification(self, ticker: str, now: datetime) -> None:
        """Record that a notification was sent for the given ticker at the given time."""
        self._last_notified[ticker] = now
