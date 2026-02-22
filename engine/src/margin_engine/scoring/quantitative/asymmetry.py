"""Asymmetry Ratio factor — upside/downside risk structure.

Ratio = (Intrinsic Value - Price) / (Price - Floor)

Where Floor = max(net_cash_per_share, tangible_book_per_share, 0).

A ratio > 1 means the upside potential exceeds the downside risk,
creating a favorable asymmetric bet. Capped at 100.0 to avoid
infinite ratios when the floor equals or exceeds the current price.

Edge cases:
    - Overvalued (intrinsic < price) → 0.0
    - Floor >= price → ratio = 100.0 (capped — effectively no downside)
    - Negative floor → uses 0
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore


def asymmetry_ratio(
    intrinsic_value: float,
    current_price: float,
    net_cash_per_share: float,
    tangible_book_per_share: float,
) -> FactorScore:
    """Compute asymmetry ratio (upside/downside structure).

    Returns a FactorScore with percentile_rank=0.0 (placeholder).
    """
    upside = intrinsic_value - current_price

    if upside <= 0:
        return FactorScore(
            name="asymmetry_ratio",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"IV={intrinsic_value:.2f}, Price={current_price:.2f}, overvalued (IV <= Price)"
            ),
        )

    floor = max(net_cash_per_share, tangible_book_per_share, 0.0)
    downside = current_price - floor

    if downside <= 0:
        # Floor >= price: effectively no downside risk → cap at 100.0
        return FactorScore(
            name="asymmetry_ratio",
            raw_value=100.0,
            percentile_rank=0.0,
            detail=(
                f"IV={intrinsic_value:.2f}, Price={current_price:.2f}, "
                f"Floor={floor:.2f} (floor >= price, capped at 100)"
            ),
        )

    ratio = min(upside / downside, 100.0)

    detail = (
        f"IV={intrinsic_value:.2f}, Price={current_price:.2f}, "
        f"Floor={floor:.2f}, Upside={upside:.2f}, "
        f"Downside={downside:.2f}, Ratio={ratio:.4f}"
    )

    return FactorScore(
        name="asymmetry_ratio",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=detail,
    )
