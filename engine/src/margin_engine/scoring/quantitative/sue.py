"""SUE (Standardized Unexpected Earnings) momentum factor.

Measures earnings momentum by normalizing the most recent earnings
surprise against the historical variability of surprises. Consistent
positive surprises yield a high SUE, indicating strong earnings momentum.

Academic reference: Latane & Jones (1977), "Standardized Unexpected
Earnings — a Progress Report."

When a reference_date is provided, applies PEAD (Post-Earnings Announcement
Drift) exponential time decay per Ball & Brown (1968) and Bernard & Thomas
(1990). Half-life is 6 months (~2 quarters).

Formula (standard): SUE = most_recent_surprise / pstdev(all_surprises)
Formula (PEAD):     SUE = weighted_recent_surprise / weighted_stddev
"""

from __future__ import annotations

from datetime import datetime
from statistics import pstdev

from margin_engine.models.financial import EarningsSurprise
from margin_engine.models.scoring import FactorScore

_MIN_QUARTERS = 4
_PEAD_HALF_LIFE_MONTHS = 6.0
_PEAD_DECAY_FLOOR = 0.05
_DAYS_PER_MONTH = 30.44


def _quarter_end_date(quarter_str: str) -> datetime:
    """Convert a quarter string like '2024-Q4' to its approximate end date.

    Returns the last day of the quarter:
    - Q1 -> March 31
    - Q2 -> June 30
    - Q3 -> September 30
    - Q4 -> December 31
    """
    year_str, q_str = quarter_str.split("-")
    year = int(year_str)
    q_num = int(q_str[1])

    end_dates = {
        1: datetime(year, 3, 31),
        2: datetime(year, 6, 30),
        3: datetime(year, 9, 30),
        4: datetime(year, 12, 31),
    }
    return end_dates[q_num]


def _pead_decay(quarter_str: str, reference_date: datetime) -> float:
    """Compute PEAD exponential decay weight for a given quarter.

    decay = max(0.05, 0.5 ^ (elapsed_months / 6.0))

    Recent quarters get weight ~1.0, quarters 6+ months old get
    progressively less weight, floored at 0.05.
    """
    quarter_end = _quarter_end_date(quarter_str)
    elapsed_days = (reference_date - quarter_end).days
    elapsed_months = max(0.0, elapsed_days / _DAYS_PER_MONTH)
    raw_decay = 0.5 ** (elapsed_months / _PEAD_HALF_LIFE_MONTHS)
    return max(_PEAD_DECAY_FLOOR, raw_decay)


def sue_score(
    surprises: list[EarningsSurprise],
    *,
    reference_date: datetime | None = None,
) -> FactorScore:
    """Compute the SUE (Standardized Unexpected Earnings) score.

    Sorts surprises by quarter, computes each quarterly surprise
    (actual_eps - expected_eps), then divides the most recent surprise
    by the population standard deviation of all surprises.

    When reference_date is provided, applies PEAD exponential time decay
    so that more recent earnings surprises are weighted more heavily.

    Returns a FactorScore with:
    - raw_value: the SUE score, or 0.0 for edge cases
    - percentile_rank: 0.0 (placeholder — filled by composite scorer in Phase 6)
    - name: "sue"

    Edge cases:
    - Empty list or fewer than 4 surprises: raw_value=0.0
    - Zero stddev (all surprises identical): raw_value=0.0
    """
    if len(surprises) < _MIN_QUARTERS:
        return FactorScore(
            name="sue",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"insufficient data: {len(surprises)} quarter(s), need at least {_MIN_QUARTERS}",
        )

    # Sort by quarter string (YYYY-QN format sorts chronologically)
    sorted_surprises = sorted(surprises, key=lambda s: s.quarter)

    # Compute surprise values as floats
    surprise_values = [float(s.surprise) for s in sorted_surprises]

    # --- PEAD time-decay path ---
    # Per Ball & Brown (1968) and Bernard & Thomas (1990), the drift signal
    # fades over time.  We apply exponential decay to the most recent surprise
    # (numerator) while keeping the historical variability (denominator)
    # unweighted.  This ensures that evaluating the *same* earnings history
    # from a later reference date produces a lower-magnitude SUE.
    if reference_date is not None:
        weights = [_pead_decay(s.quarter, reference_date) for s in sorted_surprises]

        # The drift signal: most recent surprise attenuated by its decay weight
        most_recent_decay = weights[-1]
        most_recent_surprise = surprise_values[-1]
        decayed_surprise = most_recent_surprise * most_recent_decay

        # Denominator: unweighted historical variability (same as standard SUE)
        stddev = pstdev(surprise_values)

        if stddev == 0.0:
            return FactorScore(
                name="sue",
                raw_value=0.0,
                percentile_rank=0.0,
                detail=(
                    f"PEAD stddev=0 (all surprises identical); "
                    f"quarters={[s.quarter for s in sorted_surprises]}"
                ),
            )

        sue = decayed_surprise / stddev

        return FactorScore(
            name="sue",
            raw_value=sue,
            percentile_rank=0.0,
            detail=(
                f"SUE={sue:.4f} (PEAD decay, half-life={_PEAD_HALF_LIFE_MONTHS:.0f}mo); "
                f"decayed_surprise={decayed_surprise:.4f} "
                f"(raw={most_recent_surprise:.4f} * decay={most_recent_decay:.3f}) / "
                f"pstdev={stddev:.4f}; "
                f"weights={[f'{w:.3f}' for w in weights]}; "
                f"surprises={[f'{v:.4f}' for v in surprise_values]}; "
                f"quarters={[s.quarter for s in sorted_surprises]}"
            ),
        )

    # --- Original (non-PEAD) path ---
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
