"""Tests for rarity regime classification and alignment scoring."""

from margin_engine.rarity.models import RarityRegime
from margin_engine.rarity.regime import classify_regime, compute_regime_alignment


def test_crisis_regime():
    regime = classify_regime(vix=40.0, yield_curve_slope=-0.5, credit_spread=3.0)
    assert regime == RarityRegime.CRISIS


def test_contraction_inverted_curve():
    regime = classify_regime(vix=18.0, yield_curve_slope=-0.3, credit_spread=1.5)
    assert regime == RarityRegime.CONTRACTION


def test_contraction_high_vix():
    regime = classify_regime(vix=28.0, yield_curve_slope=0.5, credit_spread=1.5)
    assert regime == RarityRegime.CONTRACTION


def test_late_cycle():
    regime = classify_regime(vix=20.0, yield_curve_slope=0.3, credit_spread=1.5)
    assert regime == RarityRegime.LATE_CYCLE


def test_expansion_default():
    regime = classify_regime(vix=14.0, yield_curve_slope=1.5, credit_spread=1.0)
    assert regime == RarityRegime.EXPANSION


def test_crisis_needs_both_conditions():
    regime = classify_regime(vix=38.0, yield_curve_slope=0.5, credit_spread=2.0)
    assert regime == RarityRegime.CONTRACTION


def test_alignment_value_in_contraction():
    score = compute_regime_alignment(regime=RarityRegime.CONTRACTION, winning_track="mispricing")
    assert score > 70


def test_alignment_growth_in_expansion():
    score = compute_regime_alignment(regime=RarityRegime.EXPANSION, winning_track="compounder")
    assert score >= 50


def test_alignment_growth_in_crisis():
    score = compute_regime_alignment(regime=RarityRegime.CRISIS, winning_track="compounder")
    assert score < 50
