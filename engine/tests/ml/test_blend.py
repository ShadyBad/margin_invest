"""Tests for alpha blending."""

from margin_engine.ml.blend import blend_alpha, blend_with_vae


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
        blended, unc = blend_with_vae(
            0.02, 0.04, 0.03, 0.5, gbm_weight=0.30, vae_weight=0.15
        )
        # 0.55 * 0.02 + 0.30 * 0.04 + 0.15 * 0.03 = 0.011 + 0.012 + 0.0045 = 0.0275
        assert abs(blended - 0.0275) < 1e-10

    def test_uncertainty_passthrough(self) -> None:
        _, unc = blend_with_vae(0.02, 0.04, 0.03, 0.75, gbm_weight=0.30, vae_weight=0.15)
        assert unc == 0.75

    def test_zero_weights(self) -> None:
        blended, _ = blend_with_vae(0.05, 0.10, 0.08, 0.5, gbm_weight=0.0, vae_weight=0.0)
        assert abs(blended - 0.05) < 1e-10
