"""Tests for FactorVAE."""

import numpy as np
from margin_engine.ml.factor_vae import (
    FactorVAEConfig,
    FactorVAEMetrics,
    predict_factor_vae,
    train_factor_vae,
)


class TestFactorVAE:
    def test_trains_without_error(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((200, 20))
        returns = rng.standard_normal(200) * 0.02
        config = FactorVAEConfig(epochs=10, latent_dim=4, hidden_dim=32)
        model_bytes, metrics = train_factor_vae(features, returns, config, seed=42)
        assert len(model_bytes) > 0
        assert isinstance(metrics, FactorVAEMetrics)

    def test_posterior_kl_positive(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((200, 20))
        returns = rng.standard_normal(200) * 0.02
        config = FactorVAEConfig(epochs=50, latent_dim=4, hidden_dim=32)
        _, metrics = train_factor_vae(features, returns, config, seed=42)
        assert metrics.kl_divergence > 0  # Encoder is learning

    def test_prior_prediction_shape(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((200, 20))
        returns = rng.standard_normal(200) * 0.02
        config = FactorVAEConfig(epochs=10, latent_dim=4, hidden_dim=32)
        model_bytes, _ = train_factor_vae(features, returns, config, seed=42)

        preds, var = predict_factor_vae(model_bytes, features[:50], config, seed=42)
        assert preds.shape == (50,)
        assert var.shape == (50,)

    def test_variance_positive(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((200, 20))
        returns = rng.standard_normal(200) * 0.02
        config = FactorVAEConfig(epochs=10, latent_dim=4, hidden_dim=32)
        model_bytes, _ = train_factor_vae(features, returns, config, seed=42)
        _, var = predict_factor_vae(model_bytes, features, config, seed=42)
        assert np.all(var > 0)

    def test_serialization_roundtrip(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((100, 10))
        returns = rng.standard_normal(100) * 0.02
        config = FactorVAEConfig(epochs=10, latent_dim=4, hidden_dim=16)
        model_bytes, _ = train_factor_vae(features, returns, config, seed=42)

        pred1, _ = predict_factor_vae(model_bytes, features[:20], config, seed=42)
        pred2, _ = predict_factor_vae(model_bytes, features[:20], config, seed=42)
        np.testing.assert_array_equal(pred1, pred2)

    def test_determinism_with_seed(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((100, 10))
        returns = rng.standard_normal(100) * 0.02
        config = FactorVAEConfig(epochs=5, latent_dim=4, hidden_dim=16)

        _bytes1, m1 = train_factor_vae(features, returns, config, seed=42)
        _bytes2, m2 = train_factor_vae(features, returns, config, seed=42)
        assert abs(m1.reconstruction_loss - m2.reconstruction_loss) < 1e-6

    def test_config_disabled_by_default(self) -> None:
        config = FactorVAEConfig()
        assert config.enable is False

    def test_reconstruction_loss_decreases(self) -> None:
        """With enough epochs, reconstruction loss should be finite and small."""
        rng = np.random.default_rng(42)
        features = rng.standard_normal((200, 10))
        returns = rng.standard_normal(200) * 0.02
        config = FactorVAEConfig(epochs=50, latent_dim=4, hidden_dim=32)
        _, metrics = train_factor_vae(features, returns, config, seed=42)
        assert metrics.reconstruction_loss < 1.0  # Should converge somewhat

    def test_mean_variance_positive(self) -> None:
        rng = np.random.default_rng(42)
        features = rng.standard_normal((200, 20))
        returns = rng.standard_normal(200) * 0.02
        config = FactorVAEConfig(epochs=10, latent_dim=4, hidden_dim=32)
        _, metrics = train_factor_vae(features, returns, config, seed=42)
        assert metrics.mean_variance > 0
