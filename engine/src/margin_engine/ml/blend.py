"""Alpha blending: combine composite scores with ML predictions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from margin_engine.config.blend_config import BlendConfig


def blend_alpha(
    composite_alpha: float,
    ml_alpha: float,
    ml_weight: float = 0.30,
) -> float:
    """Linear blend: (1 - ml_weight) * composite + ml_weight * ml.

    Args:
        composite_alpha: Alpha from the composite scoring engine.
        ml_alpha: Alpha from the ML signal model.
        ml_weight: Weight given to the ML signal (0.0 to 1.0).

    Returns:
        Blended alpha value.
    """
    return (1.0 - ml_weight) * composite_alpha + ml_weight * ml_alpha


def blend_from_config(
    composite_alpha: float,
    gbm_alpha: float,
    vae_mean: float,
    vae_var: float,
    config: BlendConfig,
) -> tuple[float, float]:
    """Blend composite + GBM + VAE predictions using a BlendConfig.

    Args:
        composite_alpha: Alpha from the composite scoring engine.
        gbm_alpha: Alpha from the GBM signal model.
        vae_mean: Mean prediction from the FactorVAE.
        vae_var: Variance from the FactorVAE prior (passed through as uncertainty).
        config: BlendConfig specifying weights and VAE shadow mode.

    Returns:
        Tuple of (blended_alpha, uncertainty).
        When config.vae_shadow_mode is True, VAE weight is forced to 0 and
        the composite weight absorbs the remaining allocation.
    """
    if config.vae_shadow_mode:
        vae_w = 0.0
        composite_w = 1.0 - config.gbm_weight
    else:
        composite_w = config.composite_weight
        vae_w = config.vae_weight

    gbm_w = config.gbm_weight
    blended = composite_w * composite_alpha + gbm_w * gbm_alpha + vae_w * vae_mean
    return blended, vae_var


def blend_with_vae(
    composite_alpha: float,
    gbm_alpha: float,
    vae_mean: float,
    vae_var: float,
    gbm_weight: float = 0.30,
    vae_weight: float = 0.0,
) -> tuple[float, float]:
    """Blend composite + GBM + VAE predictions.

    Args:
        composite_alpha: Alpha from the composite scoring engine.
        gbm_alpha: Alpha from the GBM signal model.
        vae_mean: Mean prediction from the FactorVAE.
        vae_var: Variance from the FactorVAE prior.
        gbm_weight: Weight for the GBM signal.
        vae_weight: Weight for the VAE signal (0.0 disables VAE).

    Returns:
        Tuple of (blended_alpha, uncertainty).
        When vae_weight=0.0, falls back to GBM-only blend.
    """
    remaining = 1.0 - gbm_weight - vae_weight
    blended = remaining * composite_alpha + gbm_weight * gbm_alpha + vae_weight * vae_mean
    uncertainty = vae_var  # Pass through VAE variance as uncertainty signal
    return blended, uncertainty
