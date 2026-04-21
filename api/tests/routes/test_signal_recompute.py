"""Tests for _recompute_signal() in scores route."""

from margin_api.routes.scores import _recompute_signal


class TestRecomputeSignal:
    def test_exceptional_with_positive_margin(self):
        assert _recompute_signal("exceptional", 0.15) == "strong"

    def test_high_with_positive_margin(self):
        assert _recompute_signal("high", 0.05) == "strong"

    def test_exceptional_with_negative_margin(self):
        assert _recompute_signal("exceptional", -0.10) == "stable"

    def test_high_with_zero_margin(self):
        assert _recompute_signal("high", 0.0) == "stable"

    def test_medium_tier(self):
        assert _recompute_signal("medium", 0.20) == "emerging"

    def test_none_tier(self):
        assert _recompute_signal("none", None) == "neutral"

    def test_none_tier_with_margin(self):
        assert _recompute_signal("none", 0.30) == "neutral"

    def test_null_tier(self):
        assert _recompute_signal(None, None) == "neutral"

    def test_high_with_none_margin(self):
        """High tier but no margin data -- defaults to strong."""
        assert _recompute_signal("high", None) == "strong"
