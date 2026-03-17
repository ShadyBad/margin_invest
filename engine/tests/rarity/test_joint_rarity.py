"""Golden-value tests for empirical joint CDF rarity computation."""

import numpy as np
from margin_engine.rarity.joint_rarity import compute_all_joint_rarities, compute_joint_rarity


def test_unique_best_stock():
    matrix = np.array(
        [
            [95.0, 90.0, 88.0, 92.0],
            [70.0, 65.0, 60.0, 55.0],
            [80.0, 75.0, 70.0, 65.0],
        ]
    )
    rarity = compute_joint_rarity(matrix, target_idx=0)
    assert rarity == 66.67


def test_worst_stock_has_low_rarity():
    matrix = np.array(
        [
            [95.0, 90.0, 88.0, 92.0],
            [70.0, 65.0, 60.0, 55.0],
            [80.0, 75.0, 70.0, 65.0],
        ]
    )
    rarity = compute_joint_rarity(matrix, target_idx=1)
    assert rarity == 0.0


def test_all_identical_stocks():
    matrix = np.array(
        [
            [80.0, 75.0, 70.0, 65.0],
            [80.0, 75.0, 70.0, 65.0],
            [80.0, 75.0, 70.0, 65.0],
        ]
    )
    rarity = compute_joint_rarity(matrix, target_idx=0)
    assert rarity == 0.0


def test_compute_all_returns_correct_length():
    matrix = np.array(
        [
            [95.0, 90.0],
            [70.0, 65.0],
            [80.0, 75.0],
            [60.0, 85.0],
        ]
    )
    rarities = compute_all_joint_rarities(matrix)
    assert len(rarities) == 4
    assert all(0 <= r <= 100 for r in rarities)


def test_masked_nan_columns():
    matrix = np.array(
        [
            [95.0, 90.0, 88.0, 92.0],
            [80.0, 75.0, 70.0, 65.0],
            [85.0, 80.0, 75.0, float("nan")],
        ]
    )
    rarity = compute_joint_rarity(matrix, target_idx=2)
    assert rarity == 33.33
