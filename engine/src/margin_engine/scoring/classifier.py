"""Growth stage classifier — algorithmic classification of company lifecycle stage.

Classifies companies into one of five growth stages based on financial metrics.
The growth stage determines factor weight adjustments in the composite scoring engine.

Priority order (first match wins):
1. Turnaround — 2+ negative NI quarters, sequential margin improvement, positive CFO
2. High Growth — Revenue CAGR > 20%, Gross Margin > 40%, Market Cap > $2B
3. Cyclical — Revenue StdDev > 15% OR cyclical sector
4. Mature/Cash Cow — Revenue CAGR < 5%, FCF Yield > 4%
5. Steady Growth — Revenue CAGR 5-20%, positive FCF
6. Default — Steady Growth
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import AssetProfile, FinancialPeriod
from margin_engine.models.scoring import GrowthStage

# Thresholds
_HIGH_GROWTH_CAGR = 0.20
_HIGH_GROWTH_GROSS_MARGIN = 0.40
_HIGH_GROWTH_MARKET_CAP = Decimal("2_000_000_000")

_CYCLICAL_STDDEV = 0.15

_MATURE_CAGR = 0.05
_MATURE_FCF_YIELD = 0.04

_STEADY_CAGR_LOW = 0.05
_STEADY_CAGR_HIGH = 0.20

_TURNAROUND_MIN_NEGATIVE_QUARTERS = 2
_TURNAROUND_MIN_MARGIN_IMPROVEMENTS = 2


def classify_growth_stage(
    period: FinancialPeriod,
    profile: AssetProfile,
    revenue_cagr_3yr: float | None = None,
    fcf_yield: float | None = None,
    revenue_stddev_5yr: float | None = None,
    quarterly_net_incomes: list[float] | None = None,
    quarterly_margins: list[float] | None = None,
) -> GrowthStage:
    """Classify a company's growth stage based on financial metrics.

    Checks rules in priority order; first match wins.

    Args:
        period: Current FinancialPeriod (provides FCF, CFO, gross margin).
        profile: AssetProfile (provides market_cap, sector).
        revenue_cagr_3yr: Pre-computed 3-year revenue CAGR. None if unavailable.
        fcf_yield: Pre-computed FCF / Market Cap. If None, computed from period + profile.
        revenue_stddev_5yr: Pre-computed 5-year revenue standard deviation. None if unavailable.
        quarterly_net_incomes: Last 4 quarters of net income for turnaround detection.
        quarterly_margins: Last 4+ quarters of gross/operating margin for improvement check.

    Returns:
        The classified GrowthStage.
    """
    # 1. Turnaround (most specific condition)
    if _is_turnaround(period, quarterly_net_incomes, quarterly_margins):
        return GrowthStage.TURNAROUND

    # 2. High Growth
    if _is_high_growth(period, profile, revenue_cagr_3yr):
        return GrowthStage.HIGH_GROWTH

    # 3. Cyclical (sector-based takes priority over generic growth)
    if _is_cyclical(profile, revenue_stddev_5yr):
        return GrowthStage.CYCLICAL

    # 4. Mature / Cash Cow
    if _is_mature(period, profile, revenue_cagr_3yr, fcf_yield):
        return GrowthStage.MATURE

    # 5. Steady Growth (explicit rule)
    if _is_steady_growth(period, revenue_cagr_3yr):
        return GrowthStage.STEADY_GROWTH

    # 6. Default
    return GrowthStage.STEADY_GROWTH


def _is_turnaround(
    period: FinancialPeriod,
    quarterly_net_incomes: list[float] | None,
    quarterly_margins: list[float] | None,
) -> bool:
    """Check turnaround criteria.

    Requires:
    - 2+ negative net income quarters out of last 4
    - 2+ sequential margin improvements
    - Positive operating cash flow in the most recent period
    """
    if quarterly_net_incomes is None or quarterly_margins is None:
        return False

    if len(quarterly_net_incomes) < 4 or len(quarterly_margins) < 3:
        return False

    # Count negative NI quarters (use last 4)
    recent_ni = quarterly_net_incomes[-4:]
    negative_count = sum(1 for ni in recent_ni if ni < 0)
    if negative_count < _TURNAROUND_MIN_NEGATIVE_QUARTERS:
        return False

    # Check sequential margin improvements (2+ consecutive increases)
    improvements = _count_sequential_improvements(quarterly_margins)
    if improvements < _TURNAROUND_MIN_MARGIN_IMPROVEMENTS:
        return False

    # Positive CFO in most recent quarter
    if period.current_cash_flow.operating_cash_flow <= 0:
        return False

    return True


def _count_sequential_improvements(margins: list[float]) -> int:
    """Count the maximum number of consecutive sequential margin improvements."""
    if len(margins) < 2:
        return 0

    max_streak = 0
    current_streak = 0

    for i in range(1, len(margins)):
        if margins[i] > margins[i - 1]:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return max_streak


def _is_high_growth(
    period: FinancialPeriod,
    profile: AssetProfile,
    revenue_cagr_3yr: float | None,
) -> bool:
    """Check high growth criteria.

    Requires all three:
    - Revenue CAGR (3yr) > 20%
    - Gross Margin > 40%
    - Market Cap > $2B
    """
    if revenue_cagr_3yr is None:
        return False

    if revenue_cagr_3yr <= _HIGH_GROWTH_CAGR:
        return False

    gross_margin = period.current_income.gross_margin
    if gross_margin <= _HIGH_GROWTH_GROSS_MARGIN:
        return False

    if profile.market_cap <= _HIGH_GROWTH_MARKET_CAP:
        return False

    return True


def _is_cyclical(
    profile: AssetProfile,
    revenue_stddev_5yr: float | None,
) -> bool:
    """Check cyclical criteria.

    Either:
    - Revenue StdDev (5yr) > 15%, OR
    - Sector is cyclical (Energy, Materials, Industrials, Consumer Discretionary)
    """
    if profile.sector.is_cyclical:
        return True

    if revenue_stddev_5yr is not None and revenue_stddev_5yr > _CYCLICAL_STDDEV:
        return True

    return False


def _is_mature(
    period: FinancialPeriod,
    profile: AssetProfile,
    revenue_cagr_3yr: float | None,
    fcf_yield: float | None,
) -> bool:
    """Check mature/cash cow criteria.

    Requires both:
    - Revenue CAGR (3yr) < 5%
    - FCF Yield > 4%
    """
    if revenue_cagr_3yr is None:
        return False

    if revenue_cagr_3yr >= _MATURE_CAGR:
        return False

    # Compute FCF yield if not provided
    effective_fcf_yield = fcf_yield
    if effective_fcf_yield is None:
        if profile.market_cap > 0:
            fcf = period.current_cash_flow.free_cash_flow
            effective_fcf_yield = float(fcf / profile.market_cap)
        else:
            return False

    if effective_fcf_yield <= _MATURE_FCF_YIELD:
        return False

    return True


def _is_steady_growth(
    period: FinancialPeriod,
    revenue_cagr_3yr: float | None,
) -> bool:
    """Check steady growth criteria.

    Requires both:
    - Revenue CAGR (3yr) between 5% and 20%
    - Positive free cash flow
    """
    if revenue_cagr_3yr is None:
        return False

    if not (_STEADY_CAGR_LOW <= revenue_cagr_3yr <= _STEADY_CAGR_HIGH):
        return False

    fcf = period.current_cash_flow.free_cash_flow
    if fcf <= 0:
        return False

    return True
