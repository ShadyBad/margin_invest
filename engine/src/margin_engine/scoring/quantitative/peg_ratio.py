"""PEG Ratio (Price/Earnings-to-Growth) growth-adjusted value factor.

Measures whether a stock's PE ratio is justified by its earnings growth.
Lower PEG indicates cheaper growth (inverted percentile at scoring phase).

Formula:
    PEG = PE / (earnings_growth_rate * 100)

Where earnings_growth_rate is expressed as a decimal (e.g. 0.20 for 20%).
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore


def peg_ratio(pe_ratio: float, earnings_growth_rate: float) -> FactorScore:
    """Compute PEG ratio from PE and earnings growth rate.

    Returns a FactorScore with:
    - raw_value: PEG ratio, or 0.0 sentinel when PE <= 0 or growth <= 0
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer)
    - name: "peg_ratio"

    Args:
        pe_ratio: Price-to-earnings ratio (must be positive for meaningful PEG).
        earnings_growth_rate: Earnings growth as a decimal (0.20 = 20%).
    """
    if pe_ratio <= 0:
        return FactorScore(
            name="peg_ratio",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"PE={pe_ratio}; negative/zero PE, PEG undefined",
        )

    if earnings_growth_rate <= 0:
        return FactorScore(
            name="peg_ratio",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"earnings_growth_rate={earnings_growth_rate}; negative/zero growth, PEG undefined"
            ),
        )

    growth_pct = earnings_growth_rate * 100
    peg = pe_ratio / growth_pct

    return FactorScore(
        name="peg_ratio",
        raw_value=peg,
        percentile_rank=0.0,
        detail=(
            f"PE = {pe_ratio}"
            f"; growth = {earnings_growth_rate:.4f} ({growth_pct:.2f}%)"
            f"; PEG = {pe_ratio} / {growth_pct:.2f} = {peg:.4f}"
        ),
    )
