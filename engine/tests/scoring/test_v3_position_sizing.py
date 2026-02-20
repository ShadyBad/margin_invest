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

    def test_track_a_medium_zero(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.MEDIUM) == 0.0

    def test_track_b_exceptional(self):
        assert compute_v3_position_size("mispricing", ConvictionLevel.EXCEPTIONAL) == 12.0

    def test_track_b_high(self):
        assert compute_v3_position_size("mispricing", ConvictionLevel.HIGH) == 6.0

    def test_both_exceptional(self):
        assert compute_v3_position_size("both", ConvictionLevel.EXCEPTIONAL) == 20.0

    def test_none_always_zero(self):
        assert compute_v3_position_size("compounder", ConvictionLevel.NONE) == 0.0

    def test_portfolio_cap_is_10(self):
        assert MAX_POSITIONS == 10
