"""Stock clustering via KMeans on z-scored features."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def cluster_stocks(
    feature_matrix: np.ndarray,
    tickers: list[str],
    n_clusters: int = 5,
    seed: int = 42,
) -> dict[int, list[str]]:
    """Cluster stocks by factor similarity.

    Z-scores features, runs KMeans, returns cluster -> tickers mapping.
    NaN values are imputed with column median before clustering.

    Args:
        feature_matrix: (N, F) array of factor values.
        tickers: List of ticker symbols, length N.
        n_clusters: Number of clusters.
        seed: Random seed for reproducibility.

    Returns:
        Dict mapping cluster_id to list of ticker symbols.
    """
    imputed = _impute_nan(feature_matrix.copy())

    scaler = StandardScaler()
    scaled = scaler.fit_transform(imputed)

    kmeans = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    labels = kmeans.fit_predict(scaled)

    clusters: dict[int, list[str]] = {}
    for idx, label in enumerate(labels):
        cluster_id = int(label)
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(tickers[idx])

    return clusters


def _impute_nan(matrix: np.ndarray) -> np.ndarray:
    """Replace NaN values with column median, or 0 if entire column is NaN."""
    for col in range(matrix.shape[1]):
        column = matrix[:, col]
        mask = np.isnan(column)
        if mask.all():
            matrix[:, col] = 0.0
        elif mask.any():
            median = np.nanmedian(column)
            matrix[mask, col] = median
    return matrix
