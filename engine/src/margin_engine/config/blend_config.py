"""BlendConfig — single source of truth for all ML blend weights.

Pydantic model controlling how rules-based composite scores are blended with
ML signals (GBM and VAE). All fields have defaults matching the design spec so
``BlendConfig()`` produces a working configuration out of the box.

Usage:
    from margin_engine.config.blend_config import BlendConfig

    config = BlendConfig()                     # defaults: 70/30 composite/GBM
    config = BlendConfig(                      # VAE enabled
        composite_weight=0.60,
        gbm_weight=0.30,
        vae_weight=0.10,
        vae_shadow_mode=False,
    )
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, model_validator


class BlendConfig(BaseModel):
    """Configuration for blending rules-based and ML signals.

    The three signal weights (``composite_weight``, ``gbm_weight``,
    ``vae_weight``) must sum to 1.0. When ``vae_shadow_mode`` is True the VAE
    trains normally but its weight is ignored at inference time — set
    ``vae_weight=0.0`` in that case (the default).

    ``horizon_weights`` maps prediction horizons (in trading days) to their
    blending weights. All horizon weights must also sum to 1.0.
    """

    composite_weight: float = Field(default=0.70, ge=0.0, le=1.0)
    gbm_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    vae_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    vae_shadow_mode: bool = True
    horizon_weights: dict[int, float] = Field(default_factory=lambda: {252: 1.0})

    @model_validator(mode="after")
    def _weights_must_sum_to_one(self) -> Self:
        total = self.composite_weight + self.gbm_weight + self.vae_weight
        if abs(total - 1.0) > 1e-6:
            msg = f"composite_weight + gbm_weight + vae_weight must sum to 1.0, got {total}"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _horizon_weights_must_sum_to_one(self) -> Self:
        if not self.horizon_weights:
            raise ValueError("horizon_weights must not be empty")
        if any(v < 0.0 for v in self.horizon_weights.values()):
            raise ValueError("horizon_weights values must be non-negative")
        total = sum(self.horizon_weights.values())
        if abs(total - 1.0) > 1e-6:
            msg = f"Horizon weights must sum to 1.0, got {total}"
            raise ValueError(msg)
        return self
