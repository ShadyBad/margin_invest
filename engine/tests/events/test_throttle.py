"""Tests for the notification throttle."""

from __future__ import annotations

from datetime import datetime, timedelta

from margin_engine.events.models import EventSeverity
from margin_engine.events.throttle import NotificationThrottle


class TestNotificationThrottle:
    def setup_method(self):
        self.throttle = NotificationThrottle()
        self.now = datetime(2026, 2, 10, 12, 0, 0)

    # --- Basic behaviour ---

    def test_first_notification_always_allowed(self):
        assert self.throttle.should_notify("AAPL", EventSeverity.MINOR, self.now) is True

    def test_second_notification_within_hour_blocked(self):
        self.throttle.record_notification("AAPL", self.now)
        later = self.now + timedelta(minutes=30)
        assert self.throttle.should_notify("AAPL", EventSeverity.MINOR, later) is False

    def test_second_notification_after_hour_allowed(self):
        self.throttle.record_notification("AAPL", self.now)
        later = self.now + timedelta(hours=1)
        assert self.throttle.should_notify("AAPL", EventSeverity.MINOR, later) is True

    def test_second_notification_just_before_hour_blocked(self):
        self.throttle.record_notification("AAPL", self.now)
        later = self.now + timedelta(minutes=59, seconds=59)
        assert self.throttle.should_notify("AAPL", EventSeverity.MINOR, later) is False

    # --- MAJOR bypass ---

    def test_major_severity_bypasses_throttle(self):
        self.throttle.record_notification("AAPL", self.now)
        one_second_later = self.now + timedelta(seconds=1)
        assert self.throttle.should_notify("AAPL", EventSeverity.MAJOR, one_second_later) is True

    def test_major_bypasses_even_immediately_after(self):
        self.throttle.record_notification("AAPL", self.now)
        assert self.throttle.should_notify("AAPL", EventSeverity.MAJOR, self.now) is True

    # --- Ticker isolation ---

    def test_different_tickers_dont_interfere(self):
        self.throttle.record_notification("AAPL", self.now)
        later = self.now + timedelta(minutes=5)
        # GOOG has no prior notification, so it should be allowed
        assert self.throttle.should_notify("GOOG", EventSeverity.MINOR, later) is True

    def test_throttle_tracks_per_ticker(self):
        self.throttle.record_notification("AAPL", self.now)
        self.throttle.record_notification("GOOG", self.now + timedelta(minutes=30))

        check_time = self.now + timedelta(minutes=45)
        # AAPL: 45 minutes since notification -> blocked
        assert self.throttle.should_notify("AAPL", EventSeverity.MINOR, check_time) is False
        # GOOG: 15 minutes since notification -> blocked
        assert self.throttle.should_notify("GOOG", EventSeverity.MINOR, check_time) is False

        # After 1 hour from AAPL's notification, AAPL should be allowed
        aapl_ok_time = self.now + timedelta(hours=1)
        assert self.throttle.should_notify("AAPL", EventSeverity.MINOR, aapl_ok_time) is True

    # --- MODERATE severity respects throttle ---

    def test_moderate_severity_respects_throttle(self):
        self.throttle.record_notification("AAPL", self.now)
        later = self.now + timedelta(minutes=30)
        assert self.throttle.should_notify("AAPL", EventSeverity.MODERATE, later) is False

    # --- record_notification updates state ---

    def test_record_notification_updates_timestamp(self):
        self.throttle.record_notification("AAPL", self.now)
        # First check at 30 min: blocked
        t1 = self.now + timedelta(minutes=30)
        assert self.throttle.should_notify("AAPL", EventSeverity.MINOR, t1) is False

        # Record a new notification at 30 min (e.g. from a MAJOR event)
        self.throttle.record_notification("AAPL", t1)

        # Check at original +60 min: should be blocked because last notification was at +30 min
        t2 = self.now + timedelta(hours=1)
        assert self.throttle.should_notify("AAPL", EventSeverity.MINOR, t2) is False

        # Check at +90 min from original (60 min from last notification): allowed
        t3 = self.now + timedelta(hours=1, minutes=30)
        assert self.throttle.should_notify("AAPL", EventSeverity.MINOR, t3) is True
