"""Tests for post-composite score modifiers."""

import pytest
from margin_engine.scoring.score_modifiers import (
    apply_all_modifiers,
    insider_signal_modifier,
    liquidity_modifier,
)


class TestApplyAllModifiers:
    def test_neutral_modifiers_no_change(self):
        score, breakdown = apply_all_modifiers(0.75, 1.0, 1.0, 1.0)
        assert score == pytest.approx(0.75)
        assert breakdown["combined"] == pytest.approx(1.0)

    def test_combined_product_clamped_floor(self):
        # 0.80 * 0.85 * 1.0 = 0.68 -> clamped to 0.75
        score, breakdown = apply_all_modifiers(1.0, 0.80, 0.85, 1.0)
        assert breakdown["combined"] == pytest.approx(0.75)
        assert score == pytest.approx(0.75)

    def test_combined_product_clamped_ceiling(self):
        # 1.15 * 1.0 * 1.15 = 1.3225 -> clamped to 1.25
        score, breakdown = apply_all_modifiers(1.0, 1.15, 1.0, 1.15)
        assert breakdown["combined"] == pytest.approx(1.25)
        assert score == pytest.approx(1.25)

    def test_breakdown_contains_all_keys(self):
        _, breakdown = apply_all_modifiers(0.5, 1.05, 0.95, 1.10)
        assert set(breakdown.keys()) == {"anti_consensus", "liquidity", "insider", "combined"}

    def test_score_multiplied_by_combined(self):
        score, breakdown = apply_all_modifiers(0.8, 1.10, 0.90, 1.05)
        expected_combined = 1.10 * 0.90 * 1.05
        assert breakdown["combined"] == pytest.approx(expected_combined)
        assert score == pytest.approx(0.8 * expected_combined)

    def test_zero_score_stays_zero(self):
        score, _ = apply_all_modifiers(0.0, 1.15, 0.90, 1.10)
        assert score == pytest.approx(0.0)


class TestLiquidityModifier:
    def test_mega_cap_high_volume_neutral(self):
        result = liquidity_modifier(200_000_000_000, 500_000_000, 1.2)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_small_cap_low_volume_penalized(self):
        result = liquidity_modifier(500_000_000, 2_000_000, 2.0)
        assert 0.85 <= result < 0.96

    def test_micro_cap_floor(self):
        # cap_score=0.0 (log10(1e8)=8, threshold), turnover=0.5% -> 1.0, stability=0.5
        # avg=0.5 -> 0.85 + 0.15*0.5 = 0.925
        result = liquidity_modifier(100_000_000, 500_000, 3.5)
        assert result == pytest.approx(0.925, abs=0.01)

    def test_high_divergence_penalized(self):
        result = liquidity_modifier(10_000_000_000, 50_000_000, 4.0)
        assert result < 1.0

    def test_none_divergence_mild_penalty(self):
        result = liquidity_modifier(10_000_000_000, 50_000_000, None)
        assert result < 1.0

    def test_never_boosts(self):
        result = liquidity_modifier(500_000_000_000, 1_000_000_000, 1.0)
        assert result <= 1.0

    def test_output_in_range(self):
        result = liquidity_modifier(100_000_000, 100_000, 5.0)
        assert 0.85 <= result <= 1.0

    def test_zero_market_cap(self):
        # cap=0, turnover=0, stability=0.7 -> avg=0.233 -> 0.85+0.15*0.233=0.885
        result = liquidity_modifier(0, 0, None)
        assert result == pytest.approx(0.885, abs=0.01)

    def test_absolute_floor_all_worst(self):
        # cap=0 -> 0.0, turnover=0 -> 0.0, divergence>=3.0 -> 0.5
        # avg=0.5/3=0.167 -> 0.85+0.15*0.167=0.875
        result = liquidity_modifier(0, 0, 5.0)
        assert result == pytest.approx(0.875, abs=0.01)
        assert result >= 0.85


class TestInsiderSignalModifier:
    def test_no_cluster_neutral(self):
        assert insider_signal_modifier(0.0, False, 0, None, False) == pytest.approx(1.0)

    def test_cluster_base_boost(self):
        assert insider_signal_modifier(5.0, True, 500_000, None, False) == pytest.approx(1.05)

    def test_cluster_with_drawdown(self):
        assert insider_signal_modifier(5.0, True, 500_000, -0.15, False) == pytest.approx(1.08)

    def test_cluster_with_high_magnitude(self):
        assert insider_signal_modifier(5.0, True, 6_000_000, None, False) == pytest.approx(1.08)

    def test_cluster_with_first_buy(self):
        assert insider_signal_modifier(5.0, True, 500_000, None, True) == pytest.approx(1.09)

    def test_max_modifier(self):
        assert insider_signal_modifier(10.0, True, 6_000_000, -0.20, True) == pytest.approx(1.15)

    def test_never_penalizes(self):
        assert insider_signal_modifier(0.0, False, 0, -0.50, False) >= 1.0

    def test_drawdown_threshold_boundary(self):
        # Exactly -10% should not trigger (need < -0.10)
        assert insider_signal_modifier(5.0, True, 500_000, -0.10, False) == pytest.approx(1.05)
