"""Tests for turnover constraint enforcement."""

from __future__ import annotations

from margin_engine.backtesting.turnover import enforce_turnover_limit


class TestEnforceTurnoverLimit:
    def test_within_limit_unchanged(self):
        """Weights within turnover limit are returned unchanged."""
        old = {"A": 0.5, "B": 0.5}
        new = {"A": 0.6, "B": 0.4}
        result = enforce_turnover_limit(old, new, max_turnover=0.30)
        assert result == new

    def test_exceeds_limit_blended(self):
        """Complete portfolio rebalance gets blended back."""
        old = {"A": 1.0}
        new = {"B": 1.0}
        result = enforce_turnover_limit(old, new, max_turnover=0.30)
        # Full swap = 100% turnover, should be blended to 30%
        assert "A" in result
        assert "B" in result
        total = sum(result.values())
        assert abs(total - 1.0) < 1e-6

    def test_weights_sum_to_one(self):
        """Adjusted weights always sum to 1.0."""
        old = {"A": 0.3, "B": 0.3, "C": 0.4}
        new = {"D": 0.5, "E": 0.5}
        result = enforce_turnover_limit(old, new, max_turnover=0.20)
        assert abs(sum(result.values()) - 1.0) < 1e-6

    def test_empty_old_weights(self):
        """First rebalance (no previous holdings)."""
        old: dict[str, float] = {}
        new = {"A": 0.5, "B": 0.5}
        result = enforce_turnover_limit(old, new, max_turnover=0.30)
        # Initial buy: turnover = 0.5 * (0.5 + 0.5) = 0.5, exceeds 0.30
        # But after blending and renormalization, should still sum to 1.0
        total = sum(result.values())
        assert abs(total - 1.0) < 1e-6

    def test_tiny_weights_removed(self):
        """Weights below 1e-6 are removed."""
        old = {"A": 0.5, "B": 0.5}
        new = {"A": 0.5, "B": 0.5}  # same = 0 turnover
        result = enforce_turnover_limit(old, new, max_turnover=0.30)
        assert all(v >= 1e-6 for v in result.values())

    def test_high_max_turnover_allows_anything(self):
        """max_turnover=1.0 allows full rebalance."""
        old = {"A": 1.0}
        new = {"B": 1.0}
        result = enforce_turnover_limit(old, new, max_turnover=1.0)
        assert result == new

    def test_empty_portfolios(self):
        """Both empty returns empty dict."""
        result = enforce_turnover_limit({}, {}, max_turnover=0.30)
        assert result == {}

    def test_blended_turnover_respects_limit(self):
        """After blending, actual turnover should be at or below the limit."""
        old = {"A": 0.8, "B": 0.2}
        new = {"A": 0.2, "B": 0.8}
        max_to = 0.15
        result = enforce_turnover_limit(old, new, max_turnover=max_to)
        all_tickers = set(old) | set(result)
        actual_turnover = 0.5 * sum(abs(result.get(t, 0.0) - old.get(t, 0.0)) for t in all_tickers)
        assert actual_turnover <= max_to + 1e-6
