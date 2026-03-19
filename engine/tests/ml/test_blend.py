"""Tests for alpha blending."""

from margin_engine.config.blend_config import BlendConfig
from margin_engine.ml.blend import blend_alpha, blend_from_config, blend_with_vae


class TestBlendAlpha:
    def test_basic_blend(self) -> None:
        assert abs(blend_alpha(0.02, 0.04, ml_weight=0.30) - 0.026) < 1e-10

    def test_zero_ml_weight(self) -> None:
        assert blend_alpha(0.02, 0.04, ml_weight=0.0) == 0.02

    def test_full_ml_weight(self) -> None:
        assert blend_alpha(0.02, 0.04, ml_weight=1.0) == 0.04

    def test_half_weight(self) -> None:
        result = blend_alpha(0.10, 0.20, ml_weight=0.50)
        assert abs(result - 0.15) < 1e-10

    def test_negative_values(self) -> None:
        result = blend_alpha(-0.02, 0.04, ml_weight=0.30)
        expected = 0.70 * (-0.02) + 0.30 * 0.04
        assert abs(result - expected) < 1e-10


class TestBlendWithVAE:
    def test_vae_disabled(self) -> None:
        blended, unc = blend_with_vae(0.02, 0.04, 0.01, 0.5, vae_weight=0.0)
        assert abs(blended - blend_alpha(0.02, 0.04, 0.30)) < 1e-10
        assert unc == 0.5

    def test_vae_enabled(self) -> None:
        blended, unc = blend_with_vae(0.02, 0.04, 0.03, 0.5, gbm_weight=0.30, vae_weight=0.15)
        # 0.55 * 0.02 + 0.30 * 0.04 + 0.15 * 0.03 = 0.011 + 0.012 + 0.0045 = 0.0275
        assert abs(blended - 0.0275) < 1e-10

    def test_uncertainty_passthrough(self) -> None:
        _, unc = blend_with_vae(0.02, 0.04, 0.03, 0.75, gbm_weight=0.30, vae_weight=0.15)
        assert unc == 0.75

    def test_zero_weights(self) -> None:
        blended, _ = blend_with_vae(0.05, 0.10, 0.08, 0.5, gbm_weight=0.0, vae_weight=0.0)
        assert abs(blended - 0.05) < 1e-10


class TestBlendFromConfig:
    def test_default_config_matches_old_default(self) -> None:
        """BlendConfig() defaults (70/30) match blend_alpha(ml_weight=0.30)."""
        config = BlendConfig()
        blended, _ = blend_from_config(0.02, 0.04, 0.0, 0.0, config)
        assert abs(blended - 0.026) < 1e-10

    def test_fifty_fifty_config(self) -> None:
        """50/50 composite/GBM split."""
        config = BlendConfig(composite_weight=0.50, gbm_weight=0.50)
        blended, _ = blend_from_config(0.10, 0.20, 0.0, 0.0, config)
        assert abs(blended - 0.15) < 1e-10

    def test_vae_enabled(self) -> None:
        """VAE signal included when shadow_mode=False."""
        config = BlendConfig(
            composite_weight=0.60,
            gbm_weight=0.30,
            vae_weight=0.10,
            vae_shadow_mode=False,
        )
        blended, _ = blend_from_config(0.02, 0.04, 0.03, 0.0, config)
        # 0.60*0.02 + 0.30*0.04 + 0.10*0.03 = 0.012 + 0.012 + 0.003 = 0.027
        assert abs(blended - 0.027) < 1e-10

    def test_shadow_mode_ignores_vae(self) -> None:
        """When vae_shadow_mode=True, VAE weight forced to 0; composite gets remainder."""
        config = BlendConfig(
            composite_weight=0.60,
            gbm_weight=0.30,
            vae_weight=0.10,
            vae_shadow_mode=True,
        )
        blended, _ = blend_from_config(0.02, 0.04, 0.03, 0.0, config)
        # vae_w=0, composite_w = 1.0 - 0.30 = 0.70
        # 0.70*0.02 + 0.30*0.04 = 0.014 + 0.012 = 0.026
        assert abs(blended - 0.026) < 1e-10

    def test_uncertainty_passthrough(self) -> None:
        """vae_var is returned unchanged as the uncertainty value."""
        config = BlendConfig()
        _, uncertainty = blend_from_config(0.02, 0.04, 0.03, 0.75, config)
        assert uncertainty == 0.75
