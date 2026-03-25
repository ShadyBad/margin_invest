"""Tests for _is_market_hours() helper and live_price_poll market-hours gating."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from margin_api.workers import _is_market_hours

_ET = ZoneInfo("America/New_York")


class TestIsMarketHours:
    """Unit tests for the _is_market_hours helper."""

    def test_weekday_during_market_hours(self):
        """Monday 10:30 ET should be market hours."""
        fake_now = datetime(2026, 3, 23, 10, 30, tzinfo=_ET)  # Monday
        with patch("margin_api.workers.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert _is_market_hours() is True

    def test_weekday_before_market_open(self):
        """Monday 08:00 ET should NOT be market hours (before 09:15)."""
        fake_now = datetime(2026, 3, 23, 8, 0, tzinfo=_ET)  # Monday
        with patch("margin_api.workers.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert _is_market_hours() is False

    def test_weekday_after_market_close(self):
        """Monday 17:00 ET should NOT be market hours (after 16:15)."""
        fake_now = datetime(2026, 3, 23, 17, 0, tzinfo=_ET)  # Monday
        with patch("margin_api.workers.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert _is_market_hours() is False

    def test_saturday_midday(self):
        """Saturday 12:00 ET should NOT be market hours."""
        fake_now = datetime(2026, 3, 28, 12, 0, tzinfo=_ET)  # Saturday
        with patch("margin_api.workers.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert _is_market_hours() is False

    def test_sunday_midday(self):
        """Sunday 12:00 ET should NOT be market hours."""
        fake_now = datetime(2026, 3, 29, 12, 0, tzinfo=_ET)  # Sunday
        with patch("margin_api.workers.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert _is_market_hours() is False

    def test_exact_market_open_boundary(self):
        """Monday 09:15:00 ET is the inclusive lower bound — should be market hours."""
        fake_now = datetime(2026, 3, 23, 9, 15, 0, tzinfo=_ET)
        with patch("margin_api.workers.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert _is_market_hours() is True

    def test_exact_market_close_boundary(self):
        """Monday 16:15:00 ET is the inclusive upper bound — should be market hours."""
        fake_now = datetime(2026, 3, 23, 16, 15, 0, tzinfo=_ET)
        with patch("margin_api.workers.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert _is_market_hours() is True

    def test_one_minute_before_open(self):
        """Monday 09:14 ET should NOT be market hours."""
        fake_now = datetime(2026, 3, 23, 9, 14, tzinfo=_ET)
        with patch("margin_api.workers.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            assert _is_market_hours() is False
