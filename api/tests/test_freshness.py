"""Tests for data freshness computation."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from margin_api.services.freshness import compute_freshness


class TestComputeFreshness:
    def test_fresh_within_18_hours(self):
        scored_at = datetime.now(UTC) - timedelta(hours=1)
        assert compute_freshness(scored_at) == "fresh"

    def test_stale_between_18h_and_3d(self):
        scored_at = datetime.now(UTC) - timedelta(hours=24)
        assert compute_freshness(scored_at) == "stale"

    def test_stale_at_2_days(self):
        scored_at = datetime.now(UTC) - timedelta(days=2)
        assert compute_freshness(scored_at) == "stale"

    def test_expired_after_3_days(self):
        scored_at = datetime.now(UTC) - timedelta(days=4)
        assert compute_freshness(scored_at) == "expired"

    def test_exactly_18_hours_is_stale(self):
        scored_at = datetime.now(UTC) - timedelta(hours=18)
        assert compute_freshness(scored_at) == "stale"

    def test_exactly_3_days_is_expired(self):
        scored_at = datetime.now(UTC) - timedelta(days=3)
        assert compute_freshness(scored_at) == "expired"

    def test_none_scored_at_is_expired(self):
        assert compute_freshness(None) == "expired"
