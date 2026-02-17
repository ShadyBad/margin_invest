"""Tests for v3 multiplicative composite scoring."""

import pytest
from margin_engine.scoring.v3_composite import (
    compute_track_a_score,
    compute_track_b_score,
)


class TestTrackAScore:
    def test_multiplicative_product(self):
        """Score = moat * compounding * cap_alloc * growth_gap."""
        score = compute_track_a_score(
            moat_durability=3.0,
            compounding_power=0.20,
            capital_allocation=0.80,
            growth_gap=0.10,
        )
        expected = 3.0 * 0.20 * 0.80 * 0.10
        assert score == pytest.approx(expected)

    def test_zero_in_any_factor_kills_score(self):
        """A zero moat -> zero score, regardless of other factors."""
        score = compute_track_a_score(
            moat_durability=0.0,
            compounding_power=0.20,
            capital_allocation=0.80,
            growth_gap=0.10,
        )
        assert score == 0.0

    def test_magnitude_preserved(self):
        """5x better inputs produce ~5x better score (not 1.3x like averaging)."""
        weak = compute_track_a_score(
            moat_durability=2.0,
            compounding_power=0.05,
            capital_allocation=0.50,
            growth_gap=0.03,
        )
        strong = compute_track_a_score(
            moat_durability=4.0,
            compounding_power=0.25,
            capital_allocation=0.90,
            growth_gap=0.12,
        )
        ratio = strong / weak if weak > 0 else float("inf")
        assert ratio > 10.0  # Massive gap preserved

    def test_negative_growth_gap(self):
        """Negative growth gap -> negative score (overvalued)."""
        score = compute_track_a_score(
            moat_durability=3.0,
            compounding_power=0.20,
            capital_allocation=0.80,
            growth_gap=-0.05,
        )
        assert score < 0.0


class TestTrackBScore:
    def test_multiplicative_product(self):
        score = compute_track_b_score(
            asymmetry_ratio=5.0,
            catalyst_strength=0.80,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        expected = 5.0 * 0.80 * 1.0 * 0.75
        assert score == pytest.approx(expected)

    def test_zero_catalyst_kills_score(self):
        score = compute_track_b_score(
            asymmetry_ratio=5.0,
            catalyst_strength=0.0,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        assert score == 0.0

    def test_asymmetry_capped_at_20(self):
        """Asymmetry ratio capped at 20 to prevent distortion."""
        score = compute_track_b_score(
            asymmetry_ratio=100.0,
            catalyst_strength=0.80,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        expected = 20.0 * 0.80 * 1.0 * 0.75
        assert score == pytest.approx(expected)
