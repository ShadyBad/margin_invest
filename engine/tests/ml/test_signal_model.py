"""Tests for the LightGBM signal model."""

import numpy as np
from margin_engine.ml.signal_model import (
    compute_feature_importance,
    predict_alpha,
    train_cluster_models,
)


class TestTrainClusterModels:
    def test_train_and_predict(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((100, 10))
        returns = rng.standard_normal(100) * 0.02
        clusters = {0: list(range(50)), 1: list(range(50, 100))}

        models = train_cluster_models(features, returns, clusters)
        assert len(models) == 2
        assert all(isinstance(v, bytes) for v in models.values())

    def test_predict_correct_shape(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((100, 10))
        returns = rng.standard_normal(100) * 0.02
        clusters = {0: list(range(100))}

        models = train_cluster_models(features, returns, clusters)
        preds = predict_alpha(models[0], features[:10])
        assert preds.shape == (10,)

    def test_feature_importance(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((100, 5))
        returns = rng.standard_normal(100) * 0.02
        clusters = {0: list(range(100))}

        models = train_cluster_models(features, returns, clusters)
        imp = compute_feature_importance(models[0])
        assert len(imp) == 5

    def test_feature_importance_values_positive(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((100, 5))
        returns = rng.standard_normal(100) * 0.02
        clusters = {0: list(range(100))}

        models = train_cluster_models(features, returns, clusters)
        imp = compute_feature_importance(models[0])
        assert all(v >= 0.0 for v in imp.values())

    def test_serialization_roundtrip(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((100, 10))
        returns = rng.standard_normal(100) * 0.02
        clusters = {0: list(range(100))}

        models = train_cluster_models(features, returns, clusters, seed=42)
        preds1 = predict_alpha(models[0], features[:20])
        preds2 = predict_alpha(models[0], features[:20])
        np.testing.assert_array_equal(preds1, preds2)

    def test_small_cluster_trains(self) -> None:
        """Clusters with < 50 samples should still train (no CV)."""
        rng = np.random.default_rng(42)
        features = rng.standard_normal((30, 5))
        returns = rng.standard_normal(30) * 0.02
        clusters = {0: list(range(30))}

        models = train_cluster_models(features, returns, clusters)
        assert len(models) == 1
        preds = predict_alpha(models[0], features)
        assert preds.shape == (30,)

    def test_single_sample_cluster_skipped(self) -> None:
        """Clusters with < 2 samples are skipped (LightGBM requires >= 2)."""
        rng = np.random.default_rng(42)
        features = rng.standard_normal((101, 5))
        returns = rng.standard_normal(101) * 0.02
        clusters = {
            0: list(range(100)),  # big cluster — trains normally
            1: [100],             # single sample — should be skipped
        }

        models = train_cluster_models(features, returns, clusters)
        assert 0 in models
        assert 1 not in models  # skipped

    def test_multiple_clusters(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((200, 8))
        returns = rng.standard_normal(200) * 0.02
        clusters = {
            0: list(range(0, 70)),
            1: list(range(70, 140)),
            2: list(range(140, 200)),
        }

        models = train_cluster_models(features, returns, clusters)
        assert len(models) == 3
        for cluster_id in clusters:
            assert cluster_id in models
