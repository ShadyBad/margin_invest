"""Tests for human-readable combination signature generation."""

from margin_engine.rarity.combination_signature import build_signature


def test_track_a_signature():
    pillars = {"quality": 92.3, "value": 85.7, "momentum": 78.1, "growth": 88.4}
    sig = build_signature(pillars)
    assert sig == "Q90+V85+M80+G90"


def test_track_b_signature():
    pillars = {"quality": 87.0, "value": 73.5, "catalyst": 81.2}
    sig = build_signature(pillars)
    assert sig == "Q85+V75+Cat80"


def test_rounds_to_nearest_5():
    pillars = {"quality": 62.0, "value": 68.0, "momentum": 53.0, "growth": 47.0}
    sig = build_signature(pillars)
    assert sig == "Q60+V70+M55+G45"


def test_boundary_rounding():
    # Python banker's rounding: 72.5/5=14.5 → round→14 → 70; 77.4/5=15.48 → 15 → 75
    pillars = {"quality": 72.5, "value": 77.4}
    sig = build_signature(pillars)
    assert sig == "Q70+V75"
