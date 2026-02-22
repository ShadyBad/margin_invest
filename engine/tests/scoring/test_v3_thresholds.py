"""Tests for v3 absolute conviction thresholds."""

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

    def test_medium(self):
        level = assess_track_a_conviction(
            gates_passed=3,
            total_gates=4,
            compounding_power=0.06,
            moat_durability=2,
            growth_gap=0.01,
        )
        assert level == ConvictionLevel.MEDIUM

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

    def test_medium(self):
        level = assess_track_b_conviction(
            gates_passed=3,
            total_gates=4,
            asymmetry_ratio=2.0,
            catalyst_percentile=50.0,
            converging_methods=2,
        )
        assert level == ConvictionLevel.MEDIUM

    def test_none_low_asymmetry(self):
        level = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=1.0,
            catalyst_percentile=85.0,
            converging_methods=4,
        )
        assert level == ConvictionLevel.NONE


class TestRegimeAdjustedTrackA:
    def test_expensive_regime_tightens_growth_gap(self):
        """In EXPENSIVE regime, growth_gap_adjustment=+0.02.
        A stock with growth_gap=0.04 would normally pass HIGH (> 0.03)
        but with +0.02 needs > 0.05, so drops to MEDIUM."""
        result = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.10,
            moat_durability=3,
            growth_gap=0.04,
            growth_gap_adjustment=0.02,
        )
        assert result == ConvictionLevel.MEDIUM

    def test_cheap_regime_relaxes_growth_gap(self):
        """In CHEAP regime, growth_gap_adjustment=-0.02.
        A stock with growth_gap=0.02 would normally fail HIGH (not > 0.03)
        but with -0.02 needs > 0.01, so passes HIGH."""
        result = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.10,
            moat_durability=3,
            growth_gap=0.02,
            growth_gap_adjustment=-0.02,
        )
        assert result == ConvictionLevel.HIGH

    def test_no_adjustment_default(self):
        """Without adjustment param, behavior unchanged from existing tests."""
        result = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.10,
            moat_durability=3,
            growth_gap=0.04,
        )
        assert result == ConvictionLevel.HIGH


class TestRegimeAdjustedTrackB:
    def test_cheap_relaxes_asymmetry(self):
        """CHEAP: asymmetry_adjustment=-1.0. Stock at 2.5 needs > 3.0 normally.
        With -1.0 offset needs > 2.0, so passes HIGH."""
        result = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=2.5,
            catalyst_percentile=70.0,
            converging_methods=3,
            asymmetry_adjustment=-1.0,
        )
        assert result == ConvictionLevel.HIGH

    def test_euphoria_catalyst_override(self):
        """EUPHORIA: catalyst_percentile_override=90.0.
        Stock at 75th percentile fails the 90 override for EXCEPTIONAL.
        But still passes default HIGH threshold (60)."""
        result = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=4.0,
            catalyst_percentile=75.0,
            converging_methods=3,
            catalyst_percentile_override=90.0,
        )
        # With override at 90: catalyst 75 < 90 fails EXCEPTIONAL.
        # Without override at HIGH level: catalyst 75 > 60 passes HIGH.
        assert result == ConvictionLevel.HIGH
