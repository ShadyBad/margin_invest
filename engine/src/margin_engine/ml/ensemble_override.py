"""ML ensemble override: promote or demote conviction by one level."""

from __future__ import annotations

from pydantic import BaseModel, Field

from margin_engine.ml.blend import blend_with_vae
from margin_engine.models.scoring import CompositeTier

# Ordered from lowest to highest conviction.
_CONVICTION_ORDER: list[CompositeTier] = [
    CompositeTier.NONE,
    CompositeTier.MEDIUM,
    CompositeTier.HIGH,
    CompositeTier.EXCEPTIONAL,
]

_CONVICTION_INDEX: dict[CompositeTier, int] = {
    level: idx for idx, level in enumerate(_CONVICTION_ORDER)
}


class OverrideConfig(BaseModel):
    """Configuration thresholds for ML conviction override logic."""

    top_1_percentile: float = Field(default=85.0, gt=0.0, lt=100.0)
    bottom_1_percentile: float = Field(default=15.0, gt=0.0, lt=100.0)
    min_confidence_1: float = Field(default=0.75, ge=0.0, le=1.0)
    top_2_percentile: float = Field(default=95.0, gt=0.0, lt=100.0)
    bottom_2_percentile: float = Field(default=5.0, gt=0.0, lt=100.0)
    min_confidence_2: float = Field(default=0.80, ge=0.0, le=1.0)
    max_override_levels: int = Field(default=1, ge=1, le=2)
    early_exit_confidence: float = Field(default=0.60, ge=0.0, le=1.0)


def promote(tier: CompositeTier, levels: int) -> CompositeTier:
    """Promote *tier* by *levels* steps, capped at EXCEPTIONAL.

    If *tier* is not in the conviction index (unknown tier), it is returned
    unchanged.
    """
    if tier not in _CONVICTION_INDEX:
        return tier
    idx = _CONVICTION_INDEX[tier]
    return _CONVICTION_ORDER[min(idx + levels, len(_CONVICTION_ORDER) - 1)]


def demote(tier: CompositeTier, levels: int) -> CompositeTier:
    """Demote *tier* by *levels* steps, floored at NONE.

    If *tier* is not in the conviction index (unknown tier), it is returned
    unchanged.
    """
    if tier not in _CONVICTION_INDEX:
        return tier
    idx = _CONVICTION_INDEX[tier]
    return _CONVICTION_ORDER[max(idx - levels, 0)]


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))


def apply_ml_override(
    rules_conviction: CompositeTier,
    ml_alpha: float,
    vae_mean: float,
    vae_variance: float,
    model_qualifies: bool,
    universe_ml_alphas: list[float],
    config: OverrideConfig | None = None,
) -> tuple[CompositeTier, str]:
    """Optionally promote or demote *rules_conviction* by up to two levels.

    The ML ensemble signal is computed by blending the GBM and VAE
    predictions.  If the blended signal lands in the top or bottom tail
    of the universe distribution AND uncertainty is low, the conviction
    is adjusted by one or two levels depending on the signal strength
    and confidence level.

    Args:
        rules_conviction: Conviction assigned by the rules-based engine.
        ml_alpha: LightGBM predicted alpha.
        vae_mean: FactorVAE predicted mean.
        vae_variance: FactorVAE predicted variance (uncertainty).
        model_qualifies: Whether the model's rank IC exceeds 0.15.
        universe_ml_alphas: All ML alpha values in the universe for
            percentile ranking.
        config: Override configuration thresholds. Uses defaults if None.

    Returns:
        Tuple of (final_conviction, override_type) where override_type
        is one of ``"none"``, ``"promoted"``, or ``"demoted"``.
    """
    # 1. Backward-compat: use default config when not provided.
    if config is None:
        config = OverrideConfig()

    # 2. Gate: model must qualify (rank IC > 0.15 in training).
    if not model_qualifies:
        return rules_conviction, "none"

    # 3. Compute blended ML signal (composite=0 so only ML contributes).
    #    NOTE: gbm_weight=0.60 / vae_weight=0.40 are the internal GBM-vs-VAE
    #    blend weights and must NOT be changed to BlendConfig values.
    ml_signal, _ = blend_with_vae(
        composite_alpha=0.0,
        gbm_alpha=ml_alpha,
        vae_mean=vae_mean,
        vae_var=vae_variance,
        gbm_weight=0.60,
        vae_weight=0.40,
    )

    # 4. Confidence is inversely proportional to variance.
    confidence = 1.0 - _clamp(vae_variance, 0.0, 1.0)

    # 5. Early-exit low-confidence gate.
    if confidence < config.early_exit_confidence:
        return rules_conviction, "none"

    # 6. Compute percentile rank of ml_signal within the universe.
    n = len(universe_ml_alphas)
    if n == 0:
        return rules_conviction, "none"
    count_below = sum(1 for v in universe_ml_alphas if v < ml_signal)
    ml_percentile = count_below / n * 100.0

    # 7. 2-level override check (stricter thresholds, checked first).
    if config.max_override_levels >= 2 and confidence >= config.min_confidence_2:
        if ml_percentile >= config.top_2_percentile:
            new_tier = promote(rules_conviction, 2)
            if new_tier != rules_conviction:
                return new_tier, "promoted"
            return rules_conviction, "none"
        if ml_percentile <= config.bottom_2_percentile:
            new_tier = demote(rules_conviction, 2)
            if new_tier != rules_conviction:
                return new_tier, "demoted"
            return rules_conviction, "none"

    # 8. 1-level override check.
    if confidence >= config.min_confidence_1:
        if ml_percentile >= config.top_1_percentile:
            new_tier = promote(rules_conviction, 1)
            if new_tier != rules_conviction:
                return new_tier, "promoted"
            return rules_conviction, "none"
        if ml_percentile <= config.bottom_1_percentile:
            new_tier = demote(rules_conviction, 1)
            if new_tier != rules_conviction:
                return new_tier, "demoted"
            return rules_conviction, "none"

    # 9. Mid-range percentile or insufficient confidence -> no change.
    return rules_conviction, "none"
