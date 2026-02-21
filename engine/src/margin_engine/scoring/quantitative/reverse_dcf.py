"""Reverse DCF — solve for implied growth rate and compute growth gap.

Instead of "what is this business worth?", asks "what growth is the market pricing in?"

implied_growth = solve_for_g where: price = sum(FCF*(1+g)^t / (1+WACC)^t) + terminal
growth_gap = sustainable_growth_rate - implied_growth_rate

Positive gap = market underestimates growth (opportunity).
Negative gap = market overestimates growth (no edge).
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore

_PROJECTION_YEARS = 10
_MAX_GROWTH = 0.50  # Cap solver at 50%
_MIN_GROWTH = -0.10  # Floor solver at -10%
_SOLVER_TOLERANCE = 0.0001
_SOLVER_MAX_ITER = 100


def _dcf_value(
    fcf: float, growth: float, wacc: float, terminal_growth: float, years: int
) -> float:
    """Compute DCF intrinsic value for a given growth rate."""
    pv_sum = 0.0
    for t in range(1, years + 1):
        projected = fcf * (1 + growth) ** t
        pv_sum += projected / (1 + wacc) ** t
    final_fcf = fcf * (1 + growth) ** years
    if wacc <= terminal_growth:
        return pv_sum  # No valid terminal value
    terminal = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal / (1 + wacc) ** years
    return pv_sum + pv_terminal


def solve_implied_growth_rate(
    current_price: float,
    current_fcf: float,
    wacc: float,
    terminal_growth: float,
    shares_outstanding: int,
    projection_years: int = _PROJECTION_YEARS,
) -> float | None:
    """Solve for the growth rate implied by the current market price.

    Uses bisection method to find g where DCF(g) / shares = current_price.

    Returns None if FCF <= 0 or price <= 0 (unsolvable).
    """
    if current_fcf <= 0 or current_price <= 0 or shares_outstanding <= 0:
        return None

    target = current_price * shares_outstanding  # Total market cap

    lo, hi = _MIN_GROWTH, _MAX_GROWTH

    for _ in range(_SOLVER_MAX_ITER):
        mid = (lo + hi) / 2.0
        val = _dcf_value(current_fcf, mid, wacc, terminal_growth, projection_years)
        if abs(val - target) / max(target, 1.0) < _SOLVER_TOLERANCE:
            return mid
        if val < target:
            lo = mid
        else:
            hi = mid

    return (lo + hi) / 2.0  # Best approximation


def reverse_dcf_growth_gap(
    current_price: float,
    current_fcf: float,
    wacc: float,
    terminal_growth: float,
    shares_outstanding: int,
    sustainable_growth_rate: float,
    projection_years: int = _PROJECTION_YEARS,
) -> FactorScore:
    """Compute growth gap between sustainable and implied growth rates.

    Returns a FactorScore with:
    - raw_value: growth_gap (positive = opportunity, negative = no edge)
    - percentile_rank: 0.0 (placeholder)
    """
    implied = solve_implied_growth_rate(
        current_price,
        current_fcf,
        wacc,
        terminal_growth,
        shares_outstanding,
        projection_years,
    )

    if implied is None:
        return FactorScore(
            name="reverse_dcf_growth_gap",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Cannot solve implied growth (negative FCF or invalid price)",
        )

    gap = sustainable_growth_rate - implied

    return FactorScore(
        name="reverse_dcf_growth_gap",
        raw_value=gap,
        percentile_rank=0.0,
        detail=(
            f"implied_growth={implied:.4f}, sustainable_growth={sustainable_growth_rate:.4f}, "
            f"gap={gap:.4f}"
        ),
    )


def solve_implied_margin(
    current_price: float,
    current_revenue: float,
    current_fcf_margin: float,
    wacc: float,
    terminal_growth: float,
    revenue_growth: float,
    shares_outstanding: int,
    projection_years: int = _PROJECTION_YEARS,
) -> float | None:
    """Solve for the FCF margin implied by the current market price.

    Holds revenue growth constant and solves for the margin that would
    produce the current price.

    Returns None if inputs are invalid.
    """
    if current_revenue <= 0 or current_price <= 0 or shares_outstanding <= 0:
        return None

    target = current_price * shares_outstanding

    lo, hi = -0.10, 0.60  # margin range

    for _ in range(_SOLVER_MAX_ITER):
        mid = (lo + hi) / 2.0
        pv_sum = 0.0
        for t in range(1, projection_years + 1):
            projected_rev = current_revenue * (1 + revenue_growth) ** t
            projected_fcf = projected_rev * mid
            pv_sum += projected_fcf / (1 + wacc) ** t

        final_rev = current_revenue * (1 + revenue_growth) ** projection_years
        final_fcf = final_rev * mid
        if wacc > terminal_growth:
            terminal = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
            pv_sum += terminal / (1 + wacc) ** projection_years

        if abs(pv_sum - target) / max(target, 1.0) < _SOLVER_TOLERANCE:
            return mid
        if pv_sum < target:
            lo = mid
        else:
            hi = mid

    return (lo + hi) / 2.0


def reverse_dcf_combined_gap(
    current_price: float,
    current_fcf: float,
    current_revenue: float,
    current_fcf_margin: float,
    sustainable_fcf_margin: float,
    wacc: float,
    terminal_growth: float,
    shares_outstanding: int,
    sustainable_growth_rate: float,
    revenue_growth_for_margin_solve: float,
    projection_years: int = _PROJECTION_YEARS,
) -> FactorScore:
    """Compute combined growth gap and margin gap.

    Returns the MORE FAVORABLE of the two gaps as raw_value.
    If the market is pricing in less growth than sustainable OR less
    margin expansion than achievable, the opportunity exists.
    """
    growth_gap_result = reverse_dcf_growth_gap(
        current_price, current_fcf, wacc, terminal_growth,
        shares_outstanding, sustainable_growth_rate, projection_years,
    )
    growth_gap = growth_gap_result.raw_value

    implied_margin = solve_implied_margin(
        current_price, current_revenue, current_fcf_margin,
        wacc, terminal_growth, revenue_growth_for_margin_solve,
        shares_outstanding, projection_years,
    )
    margin_gap = (sustainable_fcf_margin - implied_margin) if implied_margin is not None else 0.0

    best_gap = max(growth_gap, margin_gap)

    return FactorScore(
        name="reverse_dcf_combined_gap",
        raw_value=best_gap,
        percentile_rank=0.0,
        detail=f"growth_gap={growth_gap:.4f}, margin_gap={margin_gap:.4f}, best_gap={best_gap:.4f}",
    )
