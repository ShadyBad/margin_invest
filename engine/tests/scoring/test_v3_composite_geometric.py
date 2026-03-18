"""Tests for v3 geometric-mean composite scoring.

Verifies the weighted geometric mean with floor replaces pure multiplication.
A zero factor no longer kills the entire score.
"""

from __future__ import annotations

import pytest
from margin_engine.config.v3_scoring_config import TrackWeights, V3CompositeConfig
from margin_engine.scoring.v3_composite import (
    compute_track_a_score,
    compute_track_b_score,
    compute_track_c_score,
)

# ---------------------------------------------------------------------------
# Track A — weighted geometric mean
# ---------------------------------------------------------------------------


class TestTrackAGeometricMean:
    def test_zero_factor_does_not_zero_score(self):
        """One factor at 0.0 should produce a score > 0.10, not zero."""
        score = compute_track_a_score(
            moat_durability=0.80,
            compounding_power=0.90,
            capital_allocation=0.0,
            growth_gap=0.70,
        )
        assert score > 0.10

    def test_amazon_meaningfully_scored(self):
        """Amazon-like profile (0.30, 0.90, 0.0, 0.95) -> between 0.30 and 0.40.

        Math: floor=0.05, equal weights 0.25
        floored = (0.30, 0.90, 0.05, 0.95)
        exp(0.25*(ln(0.30)+ln(0.90)+ln(0.05)+ln(0.95))) ~ 0.337
        """
        score = compute_track_a_score(
            moat_durability=0.30,
            compounding_power=0.90,
            capital_allocation=0.0,
            growth_gap=0.95,
        )
        assert 0.30 <= score <= 0.40

    def test_balanced_mediocrity(self):
        """All factors at 0.50 -> geometric mean is exactly 0.50."""
        score = compute_track_a_score(
            moat_durability=0.50,
            compounding_power=0.50,
            capital_allocation=0.50,
            growth_gap=0.50,
        )
        assert score == pytest.approx(0.50, abs=0.01)

    def test_balanced_excellence(self):
        """(0.80, 0.85, 0.70, 0.75) -> approximately 0.77."""
        score = compute_track_a_score(
            moat_durability=0.80,
            compounding_power=0.85,
            capital_allocation=0.70,
            growth_gap=0.75,
        )
        assert 0.75 <= score <= 0.80

    def test_ordering(self):
        """Excellent > mediocre > unbalanced-with-zero > all-zero."""
        excellent = compute_track_a_score(0.80, 0.85, 0.70, 0.75)
        mediocre = compute_track_a_score(0.50, 0.50, 0.50, 0.50)
        unbalanced = compute_track_a_score(0.30, 0.90, 0.0, 0.95)
        all_zero = compute_track_a_score(0.0, 0.0, 0.0, 0.0)

        assert excellent > mediocre > unbalanced > all_zero

    def test_composite_floor(self):
        """All-zero factors should hit the floor and return >= composite_floor."""
        score = compute_track_a_score(0.0, 0.0, 0.0, 0.0)
        assert score >= 0.01

    def test_custom_weights(self):
        """Heavier weight on a strong factor -> higher score than equal weights."""
        # Custom config: heavy weight on compounding_power (strongest factor)
        heavy_on_strong = V3CompositeConfig(
            track_a_weights=TrackWeights(
                weights={
                    "moat_durability": 0.10,
                    "compounding_power": 0.60,
                    "capital_allocation": 0.10,
                    "growth_gap": 0.20,
                }
            )
        )
        # Default config: equal weights
        default_config = V3CompositeConfig()

        # (weak, strong, weak, medium)
        score_heavy = compute_track_a_score(0.20, 0.90, 0.20, 0.50, config=heavy_on_strong)
        score_equal = compute_track_a_score(0.20, 0.90, 0.20, 0.50, config=default_config)
        assert score_heavy > score_equal

    def test_balance_bonus_stub(self):
        """Multiplier=1.0 is no-op; multiplier=1.15 increases score."""
        base_config = V3CompositeConfig(balance_bonus_multiplier=1.0)
        bonus_config = V3CompositeConfig(balance_bonus_multiplier=1.15)

        factors = (0.60, 0.65, 0.55, 0.70)  # all above default threshold 0.40
        score_base = compute_track_a_score(*factors, config=base_config)
        score_bonus = compute_track_a_score(*factors, config=bonus_config)

        assert score_bonus > score_base
        assert score_bonus == pytest.approx(score_base * 1.15, rel=0.001)

    def test_no_config_uses_defaults(self):
        """Calling without config produces the same result as explicit default config."""
        factors = (0.60, 0.70, 0.50, 0.80)
        score_no_config = compute_track_a_score(*factors)
        score_default = compute_track_a_score(*factors, config=V3CompositeConfig())
        assert score_no_config == pytest.approx(score_default)


# ---------------------------------------------------------------------------
# Track B — preserves asymmetry cap
# ---------------------------------------------------------------------------


class TestTrackBGeometricMean:
    def test_track_b_asymmetry_cap(self):
        """Asymmetry > 20 is capped at 20 before geometric mean."""
        score_100 = compute_track_b_score(
            asymmetry_ratio=100.0,
            catalyst_strength=0.80,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        score_20 = compute_track_b_score(
            asymmetry_ratio=20.0,
            catalyst_strength=0.80,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        assert score_100 == pytest.approx(score_20)

    def test_track_b_zero_nonzero(self):
        """Zero catalyst no longer kills score (floored)."""
        score = compute_track_b_score(
            asymmetry_ratio=5.0,
            catalyst_strength=0.0,
            quality_floor_factor=1.0,
            valuation_convergence=0.75,
        )
        assert score > 0

    def test_track_b_balanced(self):
        """Equal moderate factors produce moderate geometric mean."""
        score = compute_track_b_score(
            asymmetry_ratio=1.0,
            catalyst_strength=1.0,
            quality_floor_factor=1.0,
            valuation_convergence=1.0,
        )
        assert score == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# Track C — geometric mean
# ---------------------------------------------------------------------------


class TestTrackCGeometricMean:
    def test_track_c_zero_nonzero(self):
        """Zero in one Track C factor should not zero the score."""
        score = compute_track_c_score(
            growth_efficiency=0.80,
            unit_economics=0.0,
            capital_efficiency=0.70,
            growth_durability=0.90,
        )
        assert score > 0

    def test_track_c_balanced(self):
        """All factors at 1.0 should produce ~1.0."""
        score = compute_track_c_score(
            growth_efficiency=1.0,
            unit_economics=1.0,
            capital_efficiency=1.0,
            growth_durability=1.0,
        )
        assert score == pytest.approx(1.0, abs=0.01)

    def test_track_c_ordering(self):
        """Higher factors produce higher scores."""
        strong = compute_track_c_score(0.90, 0.85, 0.80, 0.95)
        weak = compute_track_c_score(0.30, 0.25, 0.20, 0.35)
        assert strong > weak
