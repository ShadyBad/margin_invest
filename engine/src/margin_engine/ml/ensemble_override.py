"""ML ensemble override: promote or demote conviction by one level."""

from __future__ import annotations

from margin_engine.ml.blend import blend_with_vae
from margin_engine.models.scoring import ConvictionLevel

# Ordered from lowest to highest conviction.
_CONVICTION_ORDER: list[ConvictionLevel] = [
    ConvictionLevel.NONE,
    ConvictionLevel.MEDIUM,
    ConvictionLevel.HIGH,
    ConvictionLevel.EXCEPTIONAL,
]

_CONVICTION_INDEX: dict[ConvictionLevel, int] = {
    level: idx for idx, level in enumerate(_CONVICTION_ORDER)
}


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))


def apply_ml_override(
    rules_conviction: ConvictionLevel,
    ml_alpha: float,
    vae_mean: float,
    vae_variance: float,
    model_qualifies: bool,
    universe_ml_alphas: list[float],
) -> tuple[ConvictionLevel, str]:
    """Optionally promote or demote *rules_conviction* by one level.

    The ML ensemble signal is computed by blending the GBM and VAE
    predictions.  If the blended signal lands in the top or bottom tail
    of the universe distribution AND uncertainty is low, the conviction
    is adjusted by exactly one level.

    Args:
        rules_conviction: Conviction assigned by the rules-based engine.
        ml_alpha: LightGBM predicted alpha.
        vae_mean: FactorVAE predicted mean.
        vae_variance: FactorVAE predicted variance (uncertainty).
        model_qualifies: Whether the model's rank IC exceeds 0.15.
        universe_ml_alphas: All ML alpha values in the universe for
            percentile ranking.

    Returns:
        Tuple of (final_conviction, override_type) where override_type
        is one of ``"none"``, ``"promoted"``, or ``"demoted"``.
    """
    # 1. Gate: model must qualify (rank IC > 0.15 in training).
    if not model_qualifies:
        return rules_conviction, "none"

    # 2. Compute blended ML signal (composite=0 so only ML contributes).
    ml_signal, _ = blend_with_vae(
        composite_alpha=0.0,
        gbm_alpha=ml_alpha,
        vae_mean=vae_mean,
        vae_var=vae_variance,
        gbm_weight=0.60,
        vae_weight=0.40,
    )

    # 3. Confidence is inversely proportional to variance.
    confidence = 1.0 - _clamp(vae_variance, 0.0, 1.0)

    # 4. Low-confidence gate.
    if confidence < 0.60:
        return rules_conviction, "none"

    # 5. Compute percentile rank of ml_signal within the universe.
    n = len(universe_ml_alphas)
    if n == 0:
        return rules_conviction, "none"
    count_below = sum(1 for v in universe_ml_alphas if v < ml_signal)
    ml_percentile = count_below / n * 100.0

    # 6. Override decision.
    idx = _CONVICTION_INDEX[rules_conviction]

    if ml_percentile >= 85.0 and confidence >= 0.75:
        # Promote by one level (cannot exceed EXCEPTIONAL).
        if idx < len(_CONVICTION_ORDER) - 1:
            return _CONVICTION_ORDER[idx + 1], "promoted"
        return rules_conviction, "none"

    if ml_percentile <= 15.0 and confidence >= 0.75:
        # Demote by one level (cannot go below NONE).
        if idx > 0:
            return _CONVICTION_ORDER[idx - 1], "demoted"
        return rules_conviction, "none"

    # 7. Mid-range percentile or insufficient confidence -> no change.
    return rules_conviction, "none"
