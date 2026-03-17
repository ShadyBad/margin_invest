"""Empirical joint CDF computation for factor rarity."""

from __future__ import annotations

import numpy as np


def compute_joint_rarity(
    factor_matrix: np.ndarray,
    target_idx: int,
) -> float:
    """Compute rarity percentile for a single stock.
    Returns 0-100 (higher = rarer combination).
    """
    target = factor_matrix[target_idx]
    nan_mask = np.isnan(target)

    if nan_mask.all():
        return 0.0

    if nan_mask.any():
        valid_cols = ~nan_mask
        comparison = factor_matrix[:, valid_cols] >= target[valid_cols]
    else:
        comparison = factor_matrix >= target

    dominated = comparison.all(axis=1)
    frac_dominating = dominated.sum() / len(factor_matrix)
    return round((1 - frac_dominating) * 100, 2)


def compute_all_joint_rarities(factor_matrix: np.ndarray) -> list[float]:
    """Compute joint rarity for every stock in the matrix."""
    return [compute_joint_rarity(factor_matrix, i) for i in range(len(factor_matrix))]
