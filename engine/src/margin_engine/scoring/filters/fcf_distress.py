"""Free Cash Flow distress check filter.

Checks whether a company has negative free cash flow, which indicates
potential financial distress or unsustainable operations.

FCF = operating_cash_flow + capital_expenditures (capex is already negative).

A negative FCF means the company is burning cash and may not be able to
sustain operations without external financing.

v1 (``fcf_distress_check``): Single-period FCF >= 0 check.
v2 (``fcf_distress_check_v2``): Multi-year analysis using FinancialHistory with:
    - Configurable positive-year threshold (default 3-of-5)
    - Cyclical sector relaxation (2-of-5 for Energy/Materials/Industrials/Cons. Disc.)
    - Positive trend rescue (improving FCF for 2+ consecutive years)
    - FCF margin floor (median FCF/revenue >= -5%)
"""

from __future__ import annotations

import statistics

from margin_engine.config.filter_config import FcfDistressConfig
from margin_engine.models.financial import (
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
)
from margin_engine.models.scoring import FilterResult, InvestmentStyle

_THRESHOLD = 0.0
_FILTER_NAME = "fcf_distress"

# Cyclical sectors get a relaxed positive-year requirement (threshold - 1)
_CYCLICAL_RELAXATION = 1


def fcf_distress_check(
    period: FinancialPeriod,
    config: FcfDistressConfig | None = None,
    sector: GICSSector | None = None,
) -> FilterResult:
    """Check if free cash flow indicates financial distress (single-period).

    FAIL if current period FCF is negative.
    Uses annual data: FCF = operating_cash_flow + capital_expenditures.

    This is the legacy v1 function preserved for backward compatibility.
    Prefer ``fcf_distress_check_v2`` for new code.

    Args:
        period: Financial data with current cash flow statement.
        config: Optional FcfDistressConfig. Accepted for API consistency
            but only the single-period check is performed.
        sector: Optional GICSSector for sector exemption.

    Returns:
        FilterResult with passed=True if FCF >= 0, False otherwise.
    """
    if config is None:
        config = FcfDistressConfig()

    # Sector exemption check
    sector_value = sector.value if sector is not None else None
    if sector_value in config.exempt_sectors:
        return FilterResult(
            name=_FILTER_NAME,
            passed=True,
            detail=f"Sector '{sector_value}' is exempt from {_FILTER_NAME}",
        )

    threshold = _THRESHOLD

    fcf = period.current_cash_flow.free_cash_flow
    fcf_float = float(fcf)

    passed = fcf_float >= threshold

    detail = (
        f"FCF={fcf_float:,.0f} ({'PASS' if passed else 'FAIL'}, "
        f"threshold={threshold}). "
        f"operating_cf={float(period.current_cash_flow.operating_cash_flow):,.0f}, "
        f"capex={float(period.current_cash_flow.capital_expenditures):,.0f}"
    )

    return FilterResult(
        name=_FILTER_NAME,
        passed=passed,
        value=fcf_float,
        threshold=threshold,
        detail=detail,
    )


def fcf_distress_check_v2(
    history_or_period: FinancialHistory | FinancialPeriod,
    config: FcfDistressConfig | None = None,
    sector: GICSSector | None = None,
    style: InvestmentStyle | None = None,
) -> FilterResult:
    """Check if free cash flow indicates financial distress (multi-year).

    When given a ``FinancialHistory`` with multiple periods, performs multi-year
    analysis including positive-year counting, cyclical relaxation, positive
    trend rescue, and FCF margin floor checks.

    When given a single ``FinancialPeriod``, falls back to the v1 single-period
    behavior for backward compatibility.

    Args:
        history_or_period: Either a multi-year FinancialHistory or a single
            FinancialPeriod for backward-compatible single-period check.
        config: Optional FcfDistressConfig controlling thresholds.
        sector: Optional GICSSector for cyclical relaxation. Cyclical sectors
            (Energy, Materials, Industrials, Consumer Discretionary) use a
            relaxed positive-year threshold.
        style: Optional InvestmentStyle for style-aware adjustments. Growth
            stocks use a relaxed positive-year threshold and an additional
            OCF + gross margin rescue path.

    Returns:
        FilterResult with computed_metrics, warning, and warning_reason
        populated when applicable.
    """
    if config is None:
        config = FcfDistressConfig()

    # Sector-specific FCF margin floor lookup
    sector_value = sector.value if sector is not None else None

    # Sector exemption check
    if sector_value in config.exempt_sectors:
        return FilterResult(
            name=_FILTER_NAME,
            passed=True,
            detail=f"Sector '{sector_value}' is exempt from {_FILTER_NAME}",
        )

    margin_floor = config.get_min_fcf_margin(sector_value)
    sector_name = sector.value if sector is not None else ""

    # --- Single-period fallback ---
    if isinstance(history_or_period, FinancialPeriod):
        return fcf_distress_check(history_or_period, config=config, sector=sector)

    history = history_or_period

    # --- Multi-year analysis ---
    # Truncate to lookback_years (use most recent periods)
    periods = history.periods[-config.lookback_years :]
    total_years = len(periods)

    # Extract FCF and revenue per period
    fcf_values = [float(p.current_cash_flow.free_cash_flow) for p in periods]
    revenue_values = [float(p.current_income.revenue) for p in periods]

    # 1. Count positive FCF years
    positive_years = sum(1 for fcf in fcf_values if fcf >= 0)

    # 2. Determine required positive years (with cyclical/style relaxation)
    is_growth = style == InvestmentStyle.GROWTH
    if is_growth:
        required = config.growth_positive_years_required
    else:
        required = config.positive_years_required
    is_cyclical = sector is not None and sector.is_cyclical
    if is_cyclical:
        required = max(1, required - _CYCLICAL_RELAXATION)

    # 3. Compute FCF margins and median
    fcf_margins = []
    for fcf, rev in zip(fcf_values, revenue_values):
        if rev != 0:
            fcf_margins.append(fcf / rev)
        else:
            fcf_margins.append(0.0)
    median_fcf_margin = statistics.median(fcf_margins) if fcf_margins else 0.0

    # 4. Compute consecutive improving years (for positive trend rescue)
    consecutive_improving = _consecutive_improving_years(fcf_values)

    # --- Decision logic ---
    warning = False
    warning_reason: str | None = None

    # Check 1: FCF margin floor (sector-specific)
    margin_floor_passed = median_fcf_margin >= margin_floor
    if not margin_floor_passed:
        sector_label = f" ({sector_name})" if sector_name else ""
        detail = (
            f"FAIL: median FCF margin {median_fcf_margin:.1%} < "
            f"floor {margin_floor:.1%}{sector_label}. "
            f"positive_years={positive_years}/{total_years}, "
            f"required={required}"
        )
        return FilterResult(
            name=_FILTER_NAME,
            passed=False,
            value=median_fcf_margin,
            threshold=margin_floor,
            detail=detail,
            computed_metrics={
                "positive_years": float(positive_years),
                "total_years": float(total_years),
                "positive_years_required": float(required),
                "median_fcf_margin": median_fcf_margin,
                "consecutive_improving_years": float(consecutive_improving),
                "sector_fcf_margin_floor": margin_floor,
                "sector_name": sector_name,
            },
        )

    # Check 2: Positive year count
    count_passed = positive_years >= required

    if not count_passed:
        # Check 3: Positive trend rescue
        if config.allow_positive_trend_rescue and consecutive_improving >= 2:
            count_passed = True
            warning = True
            warning_reason = (
                f"FCF positive trend rescue: {consecutive_improving} consecutive "
                f"improving years despite only {positive_years}/{total_years} "
                f"positive years (required {required})"
            )

    if not count_passed and is_growth:
        # Check 4: Growth OCF + gross margin rescue
        # If the latest period has positive operating CF and the median gross
        # margin across all periods exceeds the threshold, allow a pass with warning.
        latest_period = periods[-1]
        latest_ocf = float(latest_period.current_cash_flow.operating_cash_flow)
        gross_margins = [p.current_income.gross_margin for p in periods]
        median_gross_margin = statistics.median(gross_margins) if gross_margins else 0.0
        if latest_ocf > 0 and median_gross_margin > config.growth_ocf_rescue_min_gross_margin:
            count_passed = True
            warning = True
            warning_reason = (
                f"Growth OCF rescue: latest OCF={latest_ocf:,.0f} (positive), "
                f"median gross margin={median_gross_margin:.1%} > "
                f"{config.growth_ocf_rescue_min_gross_margin:.0%} threshold, "
                f"despite only {positive_years}/{total_years} positive FCF years "
                f"(required {required})"
            )

    # Build detail string
    status = "PASS" if count_passed else "FAIL"
    if warning:
        status = "PASS (warning)"
    cyclical_note = f" (cyclical relaxation: {required} required)" if is_cyclical else ""
    sector_label = f" ({sector_name})" if sector_name else ""
    detail = (
        f"{status}: {positive_years}/{total_years} positive FCF years "
        f"(required {required}{cyclical_note}). "
        f"median_fcf_margin={median_fcf_margin:.1%}, "
        f"floor={margin_floor:.1%}{sector_label}, "
        f"improving_streak={consecutive_improving}"
    )

    return FilterResult(
        name=_FILTER_NAME,
        passed=count_passed,
        value=float(positive_years),
        threshold=float(required),
        detail=detail,
        warning=warning,
        warning_reason=warning_reason,
        computed_metrics={
            "positive_years": float(positive_years),
            "total_years": float(total_years),
            "positive_years_required": float(required),
            "median_fcf_margin": median_fcf_margin,
            "consecutive_improving_years": float(consecutive_improving),
            "sector_fcf_margin_floor": margin_floor,
            "sector_name": sector_name,
        },
    )


def _consecutive_improving_years(fcf_values: list[float]) -> int:
    """Count the longest trailing streak of consecutive FCF improvement.

    Looks backward from the most recent period. Each year where FCF improved
    (became less negative or more positive) compared to the prior year counts.

    Returns:
        Number of consecutive improving years ending at the most recent period.
        Returns 0 if fewer than 2 values or no improvement streak.
    """
    if len(fcf_values) < 2:
        return 0

    streak = 0
    # Walk backward from the end
    for i in range(len(fcf_values) - 1, 0, -1):
        if fcf_values[i] > fcf_values[i - 1]:
            streak += 1
        else:
            break

    return streak
