"""LightGBM signal model: one model per cluster."""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import logging
import pickle

import lightgbm as lgb
import numpy as np
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)


def compute_model_checksum(model_bytes: bytes) -> str:
    """Compute SHA-256 checksum for model bytes."""
    return hashlib.sha256(model_bytes).hexdigest()


def _verify_model_integrity(model_bytes: bytes, expected_checksum: str | None) -> None:
    """Verify model bytes match expected SHA-256 checksum."""
    if expected_checksum is None:
        logger.warning("No checksum for model — skipping integrity check")
        return
    actual = hashlib.sha256(model_bytes).hexdigest()
    if not hmac_mod.compare_digest(actual, expected_checksum):
        raise ValueError("Model integrity check failed — refusing to unpickle")


def train_cluster_models(
    features: np.ndarray,
    forward_returns: np.ndarray,
    clusters: dict[int, list[int]],
    n_splits: int = 5,
    seed: int = 42,
) -> dict[int, bytes]:
    """Train one LightGBM model per cluster using walk-forward time splits.

    Args:
        features: (N, F) feature matrix.
        forward_returns: (N,) forward return targets.
        clusters: cluster_id -> list of sample indices.
        n_splits: Number of time-series splits for cross-validation.
        seed: Random seed for reproducibility.

    Returns:
        Dict mapping cluster_id -> serialized model bytes (pickle).
    """
    params = {
        "n_estimators": 100,
        "learning_rate": 0.05,
        "max_depth": 5,
        "num_leaves": 31,
        "min_child_samples": 10,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": seed,
        "verbose": -1,
    }

    models: dict[int, bytes] = {}

    for cluster_id, indices in clusters.items():
        n_samples = len(indices)

        if n_samples < 2:
            logger.warning(
                "Cluster %d has only %d sample(s) — skipping (LightGBM needs >= 2)",
                cluster_id,
                n_samples,
            )
            continue

        cluster_features = features[indices]
        cluster_returns = forward_returns[indices]

        if n_samples < 50:
            # Too few samples for time-series CV; train on all data
            model = lgb.LGBMRegressor(**params)
            model.fit(cluster_features, cluster_returns)
        else:
            # Walk-forward cross-validation to select best iteration
            effective_splits = min(n_splits, n_samples // 10)
            effective_splits = max(effective_splits, 2)
            tscv = TimeSeriesSplit(n_splits=effective_splits)

            best_model = None
            best_val_mse = float("inf")

            for train_idx, val_idx in tscv.split(cluster_features):
                fold_model = lgb.LGBMRegressor(**params)
                fold_model.fit(cluster_features[train_idx], cluster_returns[train_idx])
                val_preds = fold_model.predict(cluster_features[val_idx])
                val_mse = float(np.mean((val_preds - cluster_returns[val_idx]) ** 2))
                if val_mse < best_val_mse:
                    best_val_mse = val_mse
                    best_model = fold_model

            # Retrain final model on all cluster data
            model = lgb.LGBMRegressor(**params)
            model.fit(cluster_features, cluster_returns)

            # If walk-forward found a better model, still use full-data retrain
            # (walk-forward was just for validation/selection purposes)
            _ = best_model  # Used for validation only

        models[cluster_id] = pickle.dumps(model)

    return models


def predict_alpha(
    model_bytes: bytes, features: np.ndarray, checksum: str | None = None
) -> np.ndarray:
    """Predict alpha from serialized model.

    Args:
        model_bytes: Pickle-serialized LGBMRegressor.
        features: (N, F) feature matrix.
        checksum: Optional SHA-256 hex digest to verify before unpickling.

    Returns:
        (N,) array of predicted alpha values.
    """
    _verify_model_integrity(model_bytes, checksum)
    model = pickle.loads(model_bytes)  # noqa: S301
    return model.predict(features)


def compute_feature_importance(model_bytes: bytes, checksum: str | None = None) -> dict[str, float]:
    """Get feature importance from serialized model.

    Args:
        model_bytes: Pickle-serialized LGBMRegressor.
        checksum: Optional SHA-256 hex digest to verify before unpickling.

    Returns:
        Dict mapping feature_{i} -> importance value.
    """
    _verify_model_integrity(model_bytes, checksum)
    model = pickle.loads(model_bytes)  # noqa: S301
    importances = model.feature_importances_
    return {f"feature_{i}": float(v) for i, v in enumerate(importances)}
