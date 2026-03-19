"""TAM Expansion Velocity factor.

Measures how fast a company is growing its revenue relative to the
industry growth rate. A velocity > 1 means the company is gaining
market share; < 1 means losing share.

Formula:
    company_segment_cagr = (last_revenue / first_revenue)^(1/years) - 1
    velocity = company_segment_cagr / max(industry_rate, 0.01)
    score = min(velocity / 2.0, 1.0) * 10

Score range: 0 – 10 (mapped to FactorScore.raw_value).
Returns None when fewer than 2 data points are available.
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore

_VELOCITY_SCALE = 2.0  # velocity=2.0 maps to max score 10
_MIN_INDUSTRY_RATE = 0.01  # floor to prevent division-by-zero


def tam_expansion_velocity(
    segment_revenues: list[dict],
    industry_growth_rate: float,
    lookback_years: int = 3,
) -> FactorScore | None:
    """Compute TAM expansion velocity score.

    Args:
        segment_revenues: List of dicts with keys "revenue" (float) and "year" (int),
            sorted in any order. At least 2 points required.
        industry_growth_rate: Expected annual growth rate for the industry (e.g. 0.10 = 10%).
        lookback_years: Maximum number of years between first and last data points.
            Only the first and last points after sorting by year are used.

    Returns:
        FactorScore with raw_value = score (0–10), or None if < 2 data points.
    """
    if len(segment_revenues) < 2:
        return None

    # Sort by year ascending; use first and last within lookback window
    sorted_pts = sorted(segment_revenues, key=lambda p: p["year"])

    # Use only the most recent `lookback_years + 1` points
    usable = sorted_pts[-(lookback_years + 1) :]
    if len(usable) < 2:
        return None

    first = usable[0]
    last = usable[-1]
    years = last["year"] - first["year"]
    if years <= 0:
        years = 1  # safety: treat as 1-year comparison

    first_rev = float(first["revenue"])
    last_rev = float(last["revenue"])

    if first_rev <= 0:
        company_cagr = 0.0
    elif last_rev <= 0:
        company_cagr = -1.0
    else:
        company_cagr = (last_rev / first_rev) ** (1.0 / years) - 1.0

    effective_industry_rate = max(industry_growth_rate, _MIN_INDUSTRY_RATE)
    velocity = company_cagr / effective_industry_rate

    # Normalize: velocity=2.0 -> score=10, capped at 10
    score = min(velocity / _VELOCITY_SCALE, 1.0) * 10.0
    # Floor at 0 (negative velocities score 0)
    score = max(score, 0.0)

    return FactorScore(
        name="tam_expansion_velocity",
        raw_value=score,
        percentile_rank=0.0,
        detail=(
            f"company_cagr={company_cagr:.4f}"
            f"; industry_growth_rate={industry_growth_rate:.4f}"
            f"; velocity={velocity:.4f}"
            f"; years={years}"
            f"; score={score:.2f}"
        ),
        metadata={
            "company_cagr": company_cagr,
            "industry_growth_rate": industry_growth_rate,
            "velocity": velocity,
            "years": years,
        },
    )
