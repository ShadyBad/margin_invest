"""Contrarian Signal — negative price momentum combined with strong fundamentals.

Signal = (100 - momentum_percentile) * (quality_percentile / 100)

Only fires when momentum_percentile < 50 (market is negative on the stock).
The worse the momentum + the better the quality = the stronger the contrarian signal.
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore

_MOMENTUM_THRESHOLD = 50.0  # Below this = negative momentum


def contrarian_signal(
    momentum_percentile: float,
    quality_percentile: float,
) -> FactorScore:
    """Compute contrarian signal strength."""
    if momentum_percentile >= _MOMENTUM_THRESHOLD:
        return FactorScore(
            name="contrarian_signal",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"momentum={momentum_percentile:.1f} (>= {_MOMENTUM_THRESHOLD}, not contrarian)",
            stub=True,
        )

    momentum_pain = 100.0 - momentum_percentile
    quality_factor = quality_percentile / 100.0
    signal = momentum_pain * quality_factor

    return FactorScore(
        name="contrarian_signal",
        raw_value=signal,
        percentile_rank=0.0,
        detail=(
            f"momentum={momentum_percentile:.1f}, quality={quality_percentile:.1f}, "
            f"pain={momentum_pain:.1f}, signal={signal:.1f}"
        ),
        stub=True,
    )
