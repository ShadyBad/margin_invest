"""SUE (Standardized Unexpected Earnings) momentum factor.

Measures earnings momentum by normalizing the most recent earnings
surprise against the historical variability of surprises. Consistent
positive surprises yield a high SUE, indicating strong earnings momentum.

Academic reference: Latane & Jones (1977), "Standardized Unexpected
Earnings — a Progress Report."

Formula: SUE = most_recent_surprise / pstdev(all_surprises)
"""

from __future__ import annotations

from statistics import pstdev

from margin_engine.models.financial import EarningsSurprise
from margin_engine.models.scoring import FactorScore


def sue_score(surprises: list[EarningsSurprise]) -> FactorScore:
    """Compute the SUE (Standardized Unexpected Earnings) score.

    Sorts surprises by quarter, computes each quarterly surprise
    (actual_eps - expected_eps), then divides the most recent surprise
    by the population standard deviation of all surprises.

    Returns a FactorScore with:
    - raw_value: the SUE score, or 0.0 for edge cases
    - percentile_rank: 0.0 (placeholder — filled by composite scorer in Phase 6)
    - name: "sue"

    Edge cases:
    - Empty list or fewer than 2 surprises: raw_value=0.0
    - Zero stddev (all surprises identical): raw_value=0.0
    """
    if len(surprises) < 2:
        return FactorScore(
            name="sue",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"insufficient data: {len(surprises)} quarter(s), need at least 2",
        )

    # Sort by quarter string (YYYY-QN format sorts chronologically)
    sorted_surprises = sorted(surprises, key=lambda s: s.quarter)

    # Compute surprise values as floats
    surprise_values = [float(s.surprise) for s in sorted_surprises]

    # Population standard deviation (we have all the data points)
    stddev = pstdev(surprise_values)

    if stddev == 0.0:
        return FactorScore(
            name="sue",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"stddev=0 (all surprises identical at {surprise_values[0]:.4f}); "
                f"quarters={[s.quarter for s in sorted_surprises]}"
            ),
        )

    most_recent_surprise = surprise_values[-1]
    sue = most_recent_surprise / stddev

    return FactorScore(
        name="sue",
        raw_value=sue,
        percentile_rank=0.0,
        detail=(
            f"SUE={sue:.4f}; "
            f"most_recent_surprise={most_recent_surprise:.4f} / "
            f"pstdev={stddev:.4f}; "
            f"surprises={[f'{v:.4f}' for v in surprise_values]}; "
            f"quarters={[s.quarter for s in sorted_surprises]}"
        ),
    )
