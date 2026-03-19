"""Tests for BlendConfig — unified ML blend weight management."""

import pytest
from margin_engine.config.blend_config import BlendConfig
from pydantic import ValidationError


class TestBlendConfig:
    """BlendConfig: defaults, validators, and valid configurations."""

    def test_default_values(self):
        """All defaults match the design spec."""
        config = BlendConfig()
        assert config.composite_weight == 0.70
        assert config.gbm_weight == 0.30
        assert config.vae_weight == 0.0
        assert config.vae_shadow_mode is True
        assert config.horizon_weights == {252: 1.0}

    def test_weights_sum_to_one(self):
        """Valid 50/50/0 split is accepted."""
        config = BlendConfig(composite_weight=0.50, gbm_weight=0.50, vae_weight=0.0)
        assert config.composite_weight == 0.50
        assert config.gbm_weight == 0.50
        assert config.vae_weight == 0.0

    def test_weights_must_sum_to_one(self):
        """Invalid weight sum raises ValidationError matching 'must sum to 1.0'."""
        with pytest.raises(ValidationError, match="must sum to 1.0"):
            BlendConfig(composite_weight=0.50, gbm_weight=0.40, vae_weight=0.0)

    def test_horizon_weights_must_sum_to_one(self):
        """Invalid horizon weight sum raises ValidationError matching horizon message."""
        with pytest.raises(ValidationError, match="Horizon weights must sum to 1.0"):
            BlendConfig(horizon_weights={252: 0.6, 126: 0.2})

    def test_vae_enabled_weights(self):
        """60/30/10 split with VAE enabled and shadow_mode=False is accepted."""
        config = BlendConfig(
            composite_weight=0.60,
            gbm_weight=0.30,
            vae_weight=0.10,
            vae_shadow_mode=False,
        )
        assert config.composite_weight == 0.60
        assert config.gbm_weight == 0.30
        assert config.vae_weight == 0.10
        assert config.vae_shadow_mode is False

    def test_fifty_fifty_blend(self):
        """50/50 composite/GBM split with zero VAE is accepted."""
        config = BlendConfig(composite_weight=0.50, gbm_weight=0.50, vae_weight=0.0)
        total = config.composite_weight + config.gbm_weight + config.vae_weight
        assert abs(total - 1.0) < 1e-6

    def test_multi_horizon_weights(self):
        """Four-horizon configuration (63, 126, 252, 504) is accepted."""
        config = BlendConfig(horizon_weights={63: 0.15, 126: 0.25, 252: 0.40, 504: 0.20})
        assert config.horizon_weights == {63: 0.15, 126: 0.25, 252: 0.40, 504: 0.20}
        total = sum(config.horizon_weights.values())
        assert abs(total - 1.0) < 1e-6

    def test_negative_weight_rejected(self):
        """Negative weights are rejected even if they sum to 1.0."""
        with pytest.raises(ValidationError):
            BlendConfig(composite_weight=-0.5, gbm_weight=1.5, vae_weight=0.0)

    def test_empty_horizon_weights_rejected(self):
        """Empty horizon_weights dict is rejected."""
        with pytest.raises(ValidationError, match="must not be empty"):
            BlendConfig(horizon_weights={})

    def test_negative_horizon_weight_rejected(self):
        """Negative horizon weight values are rejected."""
        with pytest.raises(ValidationError, match="non-negative"):
            BlendConfig(horizon_weights={252: 1.5, 126: -0.5})
