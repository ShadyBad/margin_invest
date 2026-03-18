"""Tests for v3 scoring configuration models."""

import pytest
from margin_engine.config.v3_scoring_config import (
    ConvictionGateConfig,
    MediocracyTrajectoryConfig,
    TrackWeights,
    V3CompositeConfig,
)
from pydantic import ValidationError


class TestTrackWeights:
    """TrackWeights validator: weights must sum to 1.0."""

    def test_equal_weights_valid(self):
        tw = TrackWeights(weights={"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25})
        assert tw.weights == {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}

    def test_weights_not_summing_to_one_raises(self):
        with pytest.raises(ValidationError, match="sum to 1.0"):
            TrackWeights(weights={"a": 0.5, "b": 0.3})

    def test_custom_weights_valid(self):
        tw = TrackWeights(weights={"x": 0.4, "y": 0.6})
        assert tw.weights["x"] == 0.4
        assert tw.weights["y"] == 0.6

    def test_single_weight_of_one_valid(self):
        tw = TrackWeights(weights={"solo": 1.0})
        assert tw.weights == {"solo": 1.0}

    def test_tolerance_within_1e6(self):
        """Weights that sum to 1.0 within 1e-6 tolerance should pass."""
        tw = TrackWeights(weights={"a": 0.3333333, "b": 0.3333333, "c": 0.3333334})
        assert abs(sum(tw.weights.values()) - 1.0) < 1e-6


class TestV3CompositeConfig:
    """V3CompositeConfig defaults and overrides."""

    def test_defaults_correct(self):
        config = V3CompositeConfig()
        assert config.factor_floor == 0.05
        assert config.composite_floor == 0.01
        assert config.balance_bonus_multiplier == 1.0
        assert config.balance_bonus_threshold == 0.40

    def test_track_a_default_weights(self):
        config = V3CompositeConfig()
        expected = {
            "moat_durability": 0.25,
            "compounding_power": 0.25,
            "capital_allocation": 0.25,
            "growth_gap": 0.25,
        }
        assert config.track_a_weights.weights == expected
        assert len(config.track_a_weights.weights) == 4

    def test_track_b_default_weights(self):
        config = V3CompositeConfig()
        expected = {
            "asymmetry_ratio": 0.25,
            "catalyst_strength": 0.25,
            "quality_floor_factor": 0.25,
            "valuation_convergence": 0.25,
        }
        assert config.track_b_weights.weights == expected
        assert len(config.track_b_weights.weights) == 4

    def test_track_c_default_weights(self):
        config = V3CompositeConfig()
        expected = {
            "growth_efficiency": 0.25,
            "unit_economics": 0.25,
            "capital_efficiency": 0.25,
            "growth_durability": 0.25,
        }
        assert config.track_c_weights.weights == expected
        assert len(config.track_c_weights.weights) == 4

    def test_custom_floor_works(self):
        config = V3CompositeConfig(factor_floor=0.10, composite_floor=0.05)
        assert config.factor_floor == 0.10
        assert config.composite_floor == 0.05

    def test_custom_track_weights(self):
        custom = TrackWeights(weights={"alpha": 0.7, "beta": 0.3})
        config = V3CompositeConfig(track_a_weights=custom)
        assert config.track_a_weights.weights == {"alpha": 0.7, "beta": 0.3}


class TestConvictionGateConfig:
    """ConvictionGateConfig defaults and overrides."""

    def test_defaults_correct(self):
        config = ConvictionGateConfig()
        assert config.roic_exceptional == 0.25
        assert config.roic_strong == 0.15
        assert config.roic_adequate == 0.10
        assert config.roic_minimum == 0.08
        assert config.reinvestment_strong == 0.10
        assert config.reinvestment_adequate == 0.20
        assert config.reinvestment_minimum == 0.30
        assert config.trajectory_min_delta == 0.02
        assert config.trajectory_min_periods == 3
        assert config.track_b_roic_hard_floor == 0.06
        assert config.track_b_improving_min_delta == 0.02
        assert config.track_b_improving_min_periods == 2

    def test_custom_values_work(self):
        config = ConvictionGateConfig(
            roic_exceptional=0.30,
            roic_strong=0.20,
            trajectory_min_periods=5,
            track_b_roic_hard_floor=0.08,
        )
        assert config.roic_exceptional == 0.30
        assert config.roic_strong == 0.20
        assert config.trajectory_min_periods == 5
        assert config.track_b_roic_hard_floor == 0.08
        # Other defaults preserved
        assert config.roic_adequate == 0.10
        assert config.reinvestment_minimum == 0.30


class TestMediocracyTrajectoryConfig:
    """MediocracyTrajectoryConfig defaults and overrides."""

    def test_defaults_correct(self):
        config = MediocracyTrajectoryConfig()
        assert config.roic_min_delta_per_quarter == 0.02
        assert config.roic_min_consecutive == 3
        assert config.gm_approaching_distance == 0.03
        assert config.gm_min_annual_expansion == 0.03
        assert config.fcf_positive_recent_quarters == 2
        assert config.fcf_lookback_quarters == 6
        assert config.trajectory_stages == ["turnaround", "high_growth"]
        assert config.conditional_score_multiplier == 0.90

    def test_custom_stages(self):
        config = MediocracyTrajectoryConfig(
            trajectory_stages=["turnaround", "high_growth", "recovery"]
        )
        assert len(config.trajectory_stages) == 3
        assert "recovery" in config.trajectory_stages

    def test_custom_multiplier(self):
        config = MediocracyTrajectoryConfig(conditional_score_multiplier=0.85)
        assert config.conditional_score_multiplier == 0.85
