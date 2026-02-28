"""Tests for v3 position sizing — track-specific with portfolio cap."""

from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.v3_position_sizing import (
    MAX_POSITIONS,
    compute_v3_position_size,
)


class TestV3PositionSizing:
    def test_track_a_exceptional(self):
        assert compute_v3_position_size("compounder", CompositeTier.EXCEPTIONAL) == 15.0

    def test_track_a_high(self):
        assert compute_v3_position_size("compounder", CompositeTier.HIGH) == 8.0

    def test_track_a_medium_starter(self):
        assert compute_v3_position_size("compounder", CompositeTier.MEDIUM) == 4.0

    def test_track_b_exceptional(self):
        assert compute_v3_position_size("mispricing", CompositeTier.EXCEPTIONAL) == 12.0

    def test_track_b_high(self):
        assert compute_v3_position_size("mispricing", CompositeTier.HIGH) == 6.0

    def test_both_exceptional(self):
        assert compute_v3_position_size("both", CompositeTier.EXCEPTIONAL) == 20.0

    def test_none_always_zero(self):
        assert compute_v3_position_size("compounder", CompositeTier.NONE) == 0.0

    def test_medium_compounder(self):
        """MEDIUM conviction compounders get 4% starter position."""
        assert compute_v3_position_size("compounder", CompositeTier.MEDIUM) == 4.0

    def test_medium_mispricing(self):
        """MEDIUM conviction mispricings get 3% starter position."""
        assert compute_v3_position_size("mispricing", CompositeTier.MEDIUM) == 3.0

    def test_medium_efficient_growth(self):
        """MEDIUM conviction efficient_growth gets 3% starter position."""
        assert compute_v3_position_size("efficient_growth", CompositeTier.MEDIUM) == 3.0

    def test_medium_both(self):
        """MEDIUM conviction both gets 5% starter position."""
        assert compute_v3_position_size("both", CompositeTier.MEDIUM) == 5.0

    def test_medium_compounder_growth(self):
        """MEDIUM conviction compounder_growth gets 5% starter position."""
        assert compute_v3_position_size("compounder_growth", CompositeTier.MEDIUM) == 5.0

    def test_medium_all_three(self):
        """MEDIUM conviction all_three gets 5% starter position."""
        assert compute_v3_position_size("all_three", CompositeTier.MEDIUM) == 5.0

    def test_none_still_zero_all_types(self):
        """NONE conviction returns 0.0 for every opportunity type."""
        for track in (
            "compounder",
            "mispricing",
            "efficient_growth",
            "both",
            "compounder_growth",
            "all_three",
        ):
            assert compute_v3_position_size(track, CompositeTier.NONE) == 0.0

    def test_efficient_growth_exceptional_matches_compounder(self):
        """Track C EXCEPTIONAL should match compounder at 15%."""
        assert compute_v3_position_size("efficient_growth", CompositeTier.EXCEPTIONAL) == 15.0

    def test_efficient_growth_high_matches_compounder(self):
        """Track C HIGH should match compounder at 8%."""
        assert compute_v3_position_size("efficient_growth", CompositeTier.HIGH) == 8.0

    def test_exceptional_and_high_unchanged(self):
        """Verify EXCEPTIONAL and HIGH values were not modified."""
        assert compute_v3_position_size("compounder", CompositeTier.EXCEPTIONAL) == 15.0
        assert compute_v3_position_size("compounder", CompositeTier.HIGH) == 8.0
        assert compute_v3_position_size("mispricing", CompositeTier.EXCEPTIONAL) == 12.0
        assert compute_v3_position_size("mispricing", CompositeTier.HIGH) == 6.0

    def test_portfolio_cap_is_10(self):
        assert MAX_POSITIONS == 10
