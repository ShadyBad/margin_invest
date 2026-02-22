"""Turnover constraint enforcement for portfolio rebalancing."""

from __future__ import annotations


def enforce_turnover_limit(
    old_weights: dict[str, float],
    new_weights: dict[str, float],
    max_turnover: float = 0.30,
) -> dict[str, float]:
    """Clip proposed weights to enforce maximum turnover constraint.

    Turnover = 0.5 * sum(|new_w_i - old_w_i|) for all tickers in union.

    If turnover exceeds max_turnover, blend toward old weights:
    adjusted = old + scale * (new - old) where scale = max_turnover / turnover

    Then renormalize so weights sum to 1.0.

    Args:
        old_weights: Current portfolio weights (ticker -> weight).
        new_weights: Proposed new weights (ticker -> weight).
        max_turnover: Maximum allowed one-way turnover (default 0.30 = 30%).

    Returns:
        Adjusted weights dict that respects the turnover limit.
    """
    # Get union of all tickers
    all_tickers = set(old_weights) | set(new_weights)

    if not all_tickers:
        return {}

    # Compute one-way turnover
    turnover = 0.5 * sum(
        abs(new_weights.get(t, 0.0) - old_weights.get(t, 0.0)) for t in all_tickers
    )

    # If within limit, return new_weights unchanged
    if turnover <= max_turnover:
        return dict(new_weights)

    # Blend toward old weights
    scale = max_turnover / turnover
    adjusted: dict[str, float] = {}
    for t in all_tickers:
        old_w = old_weights.get(t, 0.0)
        new_w = new_weights.get(t, 0.0)
        adjusted[t] = old_w + scale * (new_w - old_w)

    # Remove essentially-zero weights
    adjusted = {t: w for t, w in adjusted.items() if w >= 1e-6}

    # Renormalize so weights sum to 1.0
    total = sum(adjusted.values())
    if total > 0:
        adjusted = {t: w / total for t, w in adjusted.items()}

    return adjusted
