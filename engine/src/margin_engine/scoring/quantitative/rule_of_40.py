"""Rule of 40 — SaaS/growth quality factor.

Measures the trade-off between growth and profitability.
A combined score >= 40 is considered healthy for growth companies.

Formula:
    Rule of 40 = revenue_growth% + fcf_margin%

Higher values indicate a better growth-profitability balance.
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore


def rule_of_40(revenue_growth_rate: float, fcf_margin: float) -> FactorScore:
    """Compute Rule of 40 score from revenue growth and FCF margin.

    Returns a FactorScore with:
    - raw_value: revenue_growth% + fcf_margin% (as percentage points)
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer)
    - name: "rule_of_40"

    Args:
        revenue_growth_rate: Revenue growth as a decimal (0.20 = 20%).
        fcf_margin: Free cash flow margin as a decimal (0.15 = 15%).
    """
    growth_pct = revenue_growth_rate * 100
    margin_pct = fcf_margin * 100
    score = growth_pct + margin_pct

    return FactorScore(
        name="rule_of_40",
        raw_value=score,
        percentile_rank=0.0,
        detail=(
            f"revenue_growth = {revenue_growth_rate:.4f} ({growth_pct:.2f}%)"
            f"; fcf_margin = {fcf_margin:.4f} ({margin_pct:.2f}%)"
            f"; Rule of 40 = {growth_pct:.2f} + {margin_pct:.2f} = {score:.2f}"
        ),
    )
