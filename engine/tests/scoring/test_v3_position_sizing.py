"""Tests for v3 position sizing — track-specific with portfolio cap."""

import pytest
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_position_sizing import (
    compute_v3_position_size,
    MAX_POSITIONS,
)


class TestV3PositionSizing:
    def test_track_a_exceptional(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.EXCEPTIONAL) == 15.0

    def test_track_a_high(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.HIGH) == 8.0

    def test_track_a_medium_starter(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.MEDIUM) == 4.0

    def test_track_b_exceptional(self):
        assert compute_v3_position_size("mispricing", ConvictionLevel.EXCEPTIONAL) == 12.0

    def test_track_b_high(self):
        assert compute_v3_position_size("mispricing", ConvictionLevel.HIGH) == 6.0

    def test_both_exceptional(self):
        assert compute_v3_position_size("both", ConvictionLevel.EXCEPTIONAL) == 20.0

    def test_none_always_zero(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.NONE) == 0.0

    def test_medium_compounder(self):
        """MEDIUM conviction compounders get 4% starter position."""
        assert compute_v3_position_size("compounder", ConvictionLevel.MEDIUM) == 4.0

    def test_medium_mispricing(self):
        """MEDIUM conviction mispricings get 3% starter position."""
        assert compute_v3_position_size("mispricing", ConvictionLevel.MEDIUM) == 3.0

    def test_medium_efficient_growth(self):
        """MEDIUM conviction efficient_growth gets 3% starter position."""
        assert compute_v3_position_size("efficient_growth", ConvictionLevel.MEDIUM) == 3.0

    def test_medium_both(self):
        """MEDIUM conviction both gets 5% starter position."""
        assert compute_v3_position_size("both", ConvictionLevel.MEDIUM) == 5.0

    def test_medium_compounder_growth(self):
        """MEDIUM conviction compounder_growth gets 5% starter position."""
        assert compute_v3_position_size("compounder_growth", ConvictionLevel.MEDIUM) == 5.0

    def test_medium_all_three(self):
        """MEDIUM conviction all_three gets 5% starter position."""
        assert compute_v3_position_size("all_three", ConvictionLevel.MEDIUM) == 5.0

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
            assert compute_v3_position_size(track, ConvictionLevel.NONE) == 0.0

    def test_exceptional_and_high_unchanged(self):
        """Verify EXCEPTIONAL and HIGH values were not modified."""
        assert compute_v3_position_size("compounder", ConvictionLevel.EXCEPTIONAL) == 15.0
        assert compute_v3_position_size("compounder", ConvictionLevel.HIGH) == 8.0
        assert compute_v3_position_size("mispricing", ConvictionLevel.EXCEPTIONAL) == 12.0
        assert compute_v3_position_size("mispricing", ConvictionLevel.HIGH) == 6.0

    def test_portfolio_cap_is_10(self):
        assert MAX_POSITIONS == 10
