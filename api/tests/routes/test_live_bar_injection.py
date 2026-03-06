"""Tests for live bar injection into price_history response."""

from __future__ import annotations


class TestInjectLiveBar:
    """Unit tests for the _inject_live_bar helper."""

    def test_append_bar_new_day(self):
        """Live bar on a new date is appended to the list."""
        from margin_api.routes.scores import _inject_live_bar

        existing = [
            {"date": "2026-03-04", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
            {"date": "2026-03-05", "open": 1.5, "high": 2.5, "low": 1, "close": 2, "volume": 200},
        ]
        live_bar = {
            "date": "2026-03-06",
            "open": 2,
            "high": 3,
            "low": 1.5,
            "close": 2.5,
            "volume": 300,
            "updated_at": "2026-03-06T15:00:00Z",
        }
        result = _inject_live_bar(existing, live_bar)
        assert len(result) == 3
        assert result[-1]["date"] == "2026-03-06"
        assert result[-1]["close"] == 2.5

    def test_replace_bar_same_day(self):
        """Live bar on the same date as last bar replaces it."""
        from margin_api.routes.scores import _inject_live_bar

        existing = [
            {"date": "2026-03-05", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
            {"date": "2026-03-06", "open": 2, "high": 2.8, "low": 1.9, "close": 2.3, "volume": 250},
        ]
        live_bar = {
            "date": "2026-03-06",
            "open": 2,
            "high": 3.1,
            "low": 1.8,
            "close": 2.7,
            "volume": 400,
            "updated_at": "2026-03-06T15:30:00Z",
        }
        result = _inject_live_bar(existing, live_bar)
        assert len(result) == 2  # replaced, not appended
        assert result[-1]["close"] == 2.7
        assert result[-1]["volume"] == 400

    def test_no_injection_when_live_bar_is_none(self):
        """Returns existing bars unchanged when live bar is None."""
        from margin_api.routes.scores import _inject_live_bar

        existing = [
            {"date": "2026-03-05", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
        ]
        result = _inject_live_bar(existing, None)
        assert len(result) == 1
        assert result is existing

    def test_injection_into_empty_list(self):
        """Live bar is appended even when existing list is empty."""
        from margin_api.routes.scores import _inject_live_bar

        live_bar = {
            "date": "2026-03-06",
            "open": 2,
            "high": 3,
            "low": 1.5,
            "close": 2.5,
            "volume": 300,
            "updated_at": "2026-03-06T15:00:00Z",
        }
        result = _inject_live_bar([], live_bar)
        assert len(result) == 1
        assert result[0]["date"] == "2026-03-06"

    def test_updated_at_stripped_from_result(self):
        """The updated_at metadata key is not passed to chart bars."""
        from margin_api.routes.scores import _inject_live_bar

        live_bar = {
            "date": "2026-03-06",
            "open": 2,
            "high": 3,
            "low": 1.5,
            "close": 2.5,
            "volume": 300,
            "updated_at": "2026-03-06T15:00:00Z",
        }
        result = _inject_live_bar([], live_bar)
        assert "updated_at" not in result[0]
