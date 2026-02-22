"""Alpha blending: combine composite scores with ML predictions."""

from __future__ import annotations


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
