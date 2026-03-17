"""Tests for temporal quality momentum scoring."""

from margin_engine.rarity.quality_momentum import compute_quality_momentum


def test_improving_trajectory():
    current = {"quality": 85.0, "value": 80.0, "momentum": 75.0, "growth": 82.0}
    history = [
        {"quality": 70.0, "value": 68.0, "momentum": 65.0, "growth": 70.0},
        {"quality": 73.0, "value": 71.0, "momentum": 68.0, "growth": 73.0},
        {"quality": 77.0, "value": 75.0, "momentum": 71.0, "growth": 77.0},
        {"quality": 81.0, "value": 78.0, "momentum": 73.0, "growth": 80.0},
    ]
    score = compute_quality_momentum(current, history)
    assert score > 70


def test_stable_trajectory():
    current = {"quality": 80.0, "value": 75.0}
    history = [
        {"quality": 79.0, "value": 74.0},
        {"quality": 80.0, "value": 76.0},
        {"quality": 81.0, "value": 75.0},
        {"quality": 80.0, "value": 75.0},
    ]
    score = compute_quality_momentum(current, history)
    assert 40 <= score <= 60


def test_deteriorating_trajectory():
    current = {"quality": 60.0, "value": 55.0}
    history = [
        {"quality": 80.0, "value": 75.0},
        {"quality": 75.0, "value": 70.0},
        {"quality": 70.0, "value": 65.0},
        {"quality": 65.0, "value": 60.0},
    ]
    score = compute_quality_momentum(current, history)
    assert score < 40


def test_insufficient_history_returns_neutral():
    current = {"quality": 85.0, "value": 80.0}
    history = [{"quality": 80.0, "value": 75.0}]
    score = compute_quality_momentum(current, history)
    assert score == 50.0


def test_empty_history_returns_neutral():
    current = {"quality": 85.0, "value": 80.0}
    score = compute_quality_momentum(current, [])
    assert score == 50.0
