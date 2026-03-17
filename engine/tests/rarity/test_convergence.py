"""Golden-value tests for cross-factor convergence scoring."""

from margin_engine.rarity.convergence import compute_convergence


def test_perfect_high_convergence():
    result = compute_convergence([90.0, 90.0, 90.0, 90.0])
    assert result == 75.0


def test_divergent_profile():
    result = compute_convergence([95.0, 45.0, 90.0, 50.0])
    assert result == 0.0


def test_moderate_convergence():
    result = compute_convergence([85.0, 80.0, 75.0, 82.0])
    assert result == 33.09


def test_three_pillars_track_b():
    result = compute_convergence([88.0, 84.0, 80.0])
    assert result == 45.45


def test_all_zeros_returns_zero():
    result = compute_convergence([0.0, 0.0, 0.0, 0.0])
    assert result == 0.0


def test_single_pillar():
    result = compute_convergence([85.0])
    assert result == 62.5
