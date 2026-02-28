"""Tests for gate hysteresis — conviction stability buffer."""

from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.v3_thresholds import assess_track_a_conviction


class TestHysteresisPreventsNeedlessDemotion:
    """Hysteresis keeps prior conviction when values dip only slightly."""

    def test_no_demotion_with_hysteresis(self):
        """A stock currently at EXCEPTIONAL should not demote to HIGH
        if it's only slightly below EXCEPTIONAL thresholds.

        EXCEPTIONAL thresholds: power > 0.15, moat >= 3, gap > 0.08
        Buffered (90%):         power > 0.135, moat >= 3, gap > 0.072
        """
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.14,  # below 0.15, above 0.135 buffer
            moat_durability=3,
            growth_gap=0.075,  # below 0.08, above 0.072 buffer
            prior_conviction=CompositeTier.EXCEPTIONAL,
        )
        assert conviction == CompositeTier.EXCEPTIONAL

    def test_high_not_demoted_to_medium(self):
        """A stock at HIGH should stay HIGH if just slightly below thresholds.

        HIGH thresholds: power > 0.08, moat >= 2, gap > 0.03
        Buffered (90%):  power > 0.072, moat >= 2, gap > 0.027
        """
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.075,  # below 0.08, above 0.072 buffer
            moat_durability=2,
            growth_gap=0.028,  # below 0.03, above 0.027 buffer
            prior_conviction=CompositeTier.HIGH,
        )
        assert conviction == CompositeTier.HIGH


class TestDemotionBelowBuffer:
    """Hysteresis does not protect stocks that drop significantly."""

    def test_demotion_when_well_below_exceptional(self):
        """A stock that drops significantly below EXCEPTIONAL should demote."""
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.09,  # well below 0.135 buffer
            moat_durability=2,  # below moat 3 threshold
            growth_gap=0.04,  # well below 0.072 buffer
            prior_conviction=CompositeTier.EXCEPTIONAL,
        )
        assert conviction == CompositeTier.HIGH

    def test_demotion_when_one_metric_below_buffer(self):
        """If any single metric falls below the buffer, demotion proceeds."""
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.14,  # within buffer (> 0.135)
            moat_durability=3,  # meets threshold
            growth_gap=0.06,  # below 0.072 buffer — fails
            prior_conviction=CompositeTier.EXCEPTIONAL,
        )
        # growth_gap outside buffer => demote to HIGH
        assert conviction == CompositeTier.HIGH

    def test_demotion_when_moat_below_threshold(self):
        """Moat is an integer threshold — no fractional buffer applies."""
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.14,  # within buffer
            moat_durability=2,  # below EXCEPTIONAL moat of 3
            growth_gap=0.075,  # within buffer
            prior_conviction=CompositeTier.EXCEPTIONAL,
        )
        assert conviction == CompositeTier.HIGH


class TestNoHysteresisWithoutPrior:
    """Without prior conviction, standard thresholds apply unchanged."""

    def test_no_prior_defaults_to_standard(self):
        """Values slightly below EXCEPTIONAL get HIGH without hysteresis."""
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.14,
            moat_durability=3,
            growth_gap=0.075,
        )
        assert conviction == CompositeTier.HIGH

    def test_explicit_none_prior_same_as_default(self):
        """Passing prior_conviction=None behaves identically to omitting it."""
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.14,
            moat_durability=3,
            growth_gap=0.075,
            prior_conviction=None,
        )
        assert conviction == CompositeTier.HIGH


class TestNoUpwardHysteresis:
    """Hysteresis never prevents promotion — only prevents demotion."""

    def test_promotion_from_medium_to_high(self):
        """A MEDIUM stock that now qualifies for HIGH should promote."""
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.10,
            moat_durability=2,
            growth_gap=0.05,
            prior_conviction=CompositeTier.MEDIUM,
        )
        assert conviction == CompositeTier.HIGH

    def test_promotion_from_high_to_exceptional(self):
        """A HIGH stock that now qualifies for EXCEPTIONAL should promote."""
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.20,
            moat_durability=3,
            growth_gap=0.10,
            prior_conviction=CompositeTier.HIGH,
        )
        assert conviction == CompositeTier.EXCEPTIONAL

    def test_promotion_from_none_to_medium(self):
        """A NONE stock that qualifies for MEDIUM should promote."""
        conviction = assess_track_a_conviction(
            gates_passed=3,
            total_gates=4,
            compounding_power=0.06,
            moat_durability=2,
            growth_gap=0.01,
            prior_conviction=CompositeTier.NONE,
        )
        assert conviction == CompositeTier.MEDIUM


class TestHysteresisWithRegimeAdjustment:
    """Hysteresis interacts correctly with growth_gap_adjustment."""

    def test_hysteresis_uses_adjusted_thresholds(self):
        """Buffer applies on top of regime-adjusted thresholds.

        With growth_gap_adjustment=+0.02:
            EXCEPTIONAL gap threshold = 0.08 + 0.02 = 0.10
            Buffered gap threshold = 0.10 * 0.9 = 0.09

        growth_gap=0.095 > 0.09 buffer => stays EXCEPTIONAL
        """
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.14,  # within buffer of 0.135
            moat_durability=3,
            growth_gap=0.095,  # below 0.10, above 0.09 buffer
            growth_gap_adjustment=0.02,
            prior_conviction=CompositeTier.EXCEPTIONAL,
        )
        assert conviction == CompositeTier.EXCEPTIONAL


class TestSameLevelPrior:
    """When prior equals computed, hysteresis is irrelevant."""

    def test_same_level_no_change(self):
        """Prior HIGH, computed HIGH => returns HIGH (no demotion to prevent)."""
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.10,
            moat_durability=2,
            growth_gap=0.05,
            prior_conviction=CompositeTier.HIGH,
        )
        assert conviction == CompositeTier.HIGH
