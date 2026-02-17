"""Tests for v3 absolute conviction thresholds."""

import pytest
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_thresholds import (
    assess_track_a_conviction,
    assess_track_b_conviction,
)


class TestTrackAConviction:
    def test_exceptional(self):
        level = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.20,
            moat_durability=3,
            growth_gap=0.10,
        )
        assert level == ConvictionLevel.EXCEPTIONAL

    def test_high(self):
        level = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.10,
            moat_durability=2,
            growth_gap=0.05,
        )
        assert level == ConvictionLevel.HIGH

    def test_watchlist(self):
        level = assess_track_a_conviction(
            gates_passed=3,
            total_gates=4,
            compounding_power=0.06,
            moat_durability=2,
            growth_gap=0.01,
        )
        assert level == ConvictionLevel.WATCHLIST

    def test_none_insufficient_gates(self):
        level = assess_track_a_conviction(
            gates_passed=2,
            total_gates=4,
            compounding_power=0.20,
            moat_durability=3,
            growth_gap=0.10,
        )
        assert level == ConvictionLevel.NONE

    def test_none_low_moat(self):
        level = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.20,
            moat_durability=1,
            growth_gap=0.10,
        )
        assert level == ConvictionLevel.NONE


class TestTrackBConviction:
    def test_exceptional(self):
        level = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=6.0,
            catalyst_percentile=85.0,
            converging_methods=4,
        )
        assert level == ConvictionLevel.EXCEPTIONAL

    def test_high(self):
        level = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=4.0,
            catalyst_percentile=65.0,
            converging_methods=3,
        )
        assert level == ConvictionLevel.HIGH

    def test_watchlist(self):
        level = assess_track_b_conviction(
            gates_passed=3,
            total_gates=4,
            asymmetry_ratio=2.0,
            catalyst_percentile=50.0,
            converging_methods=2,
        )
        assert level == ConvictionLevel.WATCHLIST

    def test_none_low_asymmetry(self):
        level = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=1.0,
            catalyst_percentile=85.0,
            converging_methods=4,
        )
        assert level == ConvictionLevel.NONE
