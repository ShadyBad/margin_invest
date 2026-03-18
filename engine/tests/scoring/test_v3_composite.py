"""Tests for v3 weighted geometric mean composite scoring."""

import pytest
from margin_engine.scoring.v3_composite import (
    compute_track_a_score,
    compute_track_b_score,
)


class TestTrackAScore:
    def test_geometric_mean(self):
        """Score = exp(sum(w_i * ln(max(f_i, floor)))) with equal weights."""
        score = compute_track_a_score(
            moat_durability=3.0,
            compounding_power=0.20,
            capital_allocation=0.80,
            growth_gap=0.10,
        )
        # Geometric mean of (3.0, 0.20, 0.80, 0.10) with equal weights 0.25
        assert score == pytest.approx(0.4681, abs=0.001)

    def test_zero_factor_floored_not_killed(self):
        """A zero moat is floored (not killed) — score > 0."""
        score = compute_track_a_score(
            moat_durability=0.0,
            compounding_power=0.20,
            capital_allocation=0.80,
            growth_gap=0.10,
        )
        assert score > 0

    def test_magnitude_ordering_preserved(self):
        """Stronger inputs produce higher score (geometric mean compresses ratios)."""
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
        assert strong > weak

    def test_negative_growth_gap_floored(self):
        """Negative growth gap is floored to factor_floor — score stays positive."""
        score = compute_track_a_score(
            moat_durability=3.0,
            compounding_power=0.20,
            capital_allocation=0.80,
            growth_gap=-0.05,
        )
        assert score > 0


class TestTrackBScore:
    def test_geometric_mean(self):
        """Weighted geometric mean of Track B factors."""
        score = compute_track_b_score(
            asymmetry_ratio=5.0,
            catalyst_strength=0.80,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        # exp(0.25*(ln(5)+ln(0.80)+ln(1.0)+ln(0.75))) ~ 1.3161
        assert score == pytest.approx(1.3161, abs=0.001)

    def test_zero_catalyst_floored(self):
        """Zero catalyst is floored — score > 0."""
        score = compute_track_b_score(
            asymmetry_ratio=5.0,
            catalyst_strength=0.0,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        assert score > 0

    def test_asymmetry_capped_at_20(self):
        """Asymmetry ratio capped at 20 to prevent distortion."""
        score = compute_track_b_score(
            asymmetry_ratio=100.0,
            catalyst_strength=0.80,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        # Same as asymmetry=20: exp(0.25*(ln(20)+ln(0.80)+ln(1.0)+ln(0.75))) ~ 1.8612
        assert score == pytest.approx(1.8612, abs=0.001)
