"""Investment style classifier — Value / Blend / Growth.

Classifies assets using a majority-vote across 4 signals:
1. EV/FCF sector percentile (valuation relative to sector)
2. Revenue CAGR (3yr)
3. Earnings growth trajectory (accelerating or not)
4. R&D + CapEx / Revenue (reinvestment intensity)

Style is orthogonal to GrowthStage — a Mature company can be Growth-style
if it's expensive relative to peers with high reinvestment.
"""

from __future__ import annotations

from margin_engine.models.scoring import InvestmentStyle

# Tercile boundaries for EV/FCF percentile
_VALUATION_LOW = 33.33
_VALUATION_HIGH = 66.67

# Revenue CAGR boundaries
_CAGR_LOW = 0.08
_CAGR_HIGH = 0.18

# R&D + CapEx / Revenue boundaries
_REINVEST_LOW = 0.08
_REINVEST_HIGH = 0.15


def classify_investment_style(
    ev_fcf_sector_percentile: float | None,
    revenue_cagr_3yr: float | None,
    earnings_growth_accelerating: bool | None,
    rd_capex_to_revenue: float | None,
) -> InvestmentStyle:
    """Classify an asset's investment style using majority-vote.

    Each signal votes VALUE, BLEND, or GROWTH. Majority wins.
    Ties default to BLEND. None signals are excluded from the vote.
    """
    votes: list[InvestmentStyle] = []

    if ev_fcf_sector_percentile is not None:
        if ev_fcf_sector_percentile <= _VALUATION_LOW:
            votes.append(InvestmentStyle.VALUE)
        elif ev_fcf_sector_percentile >= _VALUATION_HIGH:
            votes.append(InvestmentStyle.GROWTH)
        else:
            votes.append(InvestmentStyle.BLEND)

    if revenue_cagr_3yr is not None:
        if revenue_cagr_3yr < _CAGR_LOW:
            votes.append(InvestmentStyle.VALUE)
        elif revenue_cagr_3yr > _CAGR_HIGH:
            votes.append(InvestmentStyle.GROWTH)
        else:
            votes.append(InvestmentStyle.BLEND)

    if earnings_growth_accelerating is not None:
        if earnings_growth_accelerating:
            votes.append(InvestmentStyle.GROWTH)
        else:
            votes.append(InvestmentStyle.VALUE)

    if rd_capex_to_revenue is not None:
        if rd_capex_to_revenue < _REINVEST_LOW:
            votes.append(InvestmentStyle.VALUE)
        elif rd_capex_to_revenue > _REINVEST_HIGH:
            votes.append(InvestmentStyle.GROWTH)
        else:
            votes.append(InvestmentStyle.BLEND)

    if not votes:
        return InvestmentStyle.BLEND

    counts = {
        InvestmentStyle.VALUE: votes.count(InvestmentStyle.VALUE),
        InvestmentStyle.BLEND: votes.count(InvestmentStyle.BLEND),
        InvestmentStyle.GROWTH: votes.count(InvestmentStyle.GROWTH),
    }

    max_count = max(counts.values())
    winners = [s for s, c in counts.items() if c == max_count]

    if len(winners) > 1:
        return InvestmentStyle.BLEND

    return winners[0]
