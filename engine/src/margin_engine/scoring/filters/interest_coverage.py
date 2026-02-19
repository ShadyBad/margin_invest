"""Interest Coverage Ratio financial health filter.

The Interest Coverage Ratio (ICR) measures a company's ability to pay
interest on its outstanding debt. Companies that cannot cover their
interest obligations are at high risk of default.

Formula:
    ICR = EBIT / Interest Expense

Sector-adjusted thresholds:
    Technology:  > 5.0  (high-margin, low-debt expected)
    Utilities:   > 1.2  (capital-intensive, regulated)
    All others:  > 1.5  (default minimum)
"""

from __future__ import annotations

from statistics import median

from margin_engine.config.filter_config import InterestCoverageConfig
from margin_engine.models.financial import FinancialHistory, FinancialPeriod, GICSSector
from margin_engine.models.scoring import FilterResult

# Sector-adjusted minimum ICR thresholds
_SECTOR_THRESHOLDS: dict[GICSSector, float] = {
    GICSSector.TECHNOLOGY: 5.0,
    GICSSector.UTILITIES: 1.2,
}
_DEFAULT_THRESHOLD = 1.5


def _get_threshold(sector: GICSSector | None) -> float:
    """Return the ICR threshold for the given sector (legacy hardcoded)."""
    if sector is None:
        return _DEFAULT_THRESHOLD
    return _SECTOR_THRESHOLDS.get(sector, _DEFAULT_THRESHOLD)


def _get_config_threshold(sector: GICSSector | None, config: InterestCoverageConfig) -> float:
    """Return the ICR threshold for the given sector using config values."""
    if sector is not None:
        sector_key = sector.value.lower()
        override = config.sector_overrides.get(sector_key)
        if override is not None:
            return override
    return config.default


def interest_coverage_check(
    period: FinancialPeriod,
    sector: GICSSector | None = None,
    config: InterestCoverageConfig | None = None,
) -> FilterResult:
    """Check interest coverage ratio against sector-adjusted thresholds.

    If interest_expense is None or 0, assume no debt service -> PASS.

    Args:
        period: Financial data with current income statement.
        sector: GICS sector for sector-adjusted thresholds.
        config: Optional InterestCoverageConfig. When provided, thresholds
            are read from config.default and config.sector_overrides.
            When None, hardcoded constants are used.
    """
    name = "interest_coverage"
    threshold = _get_config_threshold(sector, config) if config else _get_threshold(sector)
    interest_expense = period.current_income.interest_expense

    # No interest expense means no debt service -> automatically passes
    if interest_expense is None or interest_expense == 0:
        return FilterResult(
            name=name,
            passed=True,
            threshold=threshold,
            detail="No interest expense; no debt service obligation",
        )

    ebit = float(period.current_income.ebit)
    ie = float(interest_expense)

    icr = ebit / ie
    icr_rounded = round(icr, 4)
    passed = icr > threshold

    sector_label = sector.value if sector else "default"
    detail = (
        f"ICR={icr_rounded:.4f} ({'PASS' if passed else 'FAIL'}, "
        f"threshold>{threshold} for {sector_label})"
    )

    return FilterResult(
        name=name,
        passed=passed,
        value=icr_rounded,
        threshold=threshold,
        detail=detail,
    )


def _compute_icr(period: FinancialPeriod) -> float | None:
    """Compute ICR for a single period. Returns None if no interest expense."""
    ie = period.current_income.interest_expense
    if ie is None or ie == 0:
        return None
    return float(period.current_income.ebit) / float(ie)


def interest_coverage_check_v2(
    data: FinancialHistory | FinancialPeriod,
    sector: GICSSector | None = None,
    config: InterestCoverageConfig | None = None,
) -> FilterResult:
    """Check interest coverage ratio using multi-year median with trend guard.

    When *data* is a :class:`FinancialHistory`, the function computes ICR for
    each period, takes the median over ``config.median_lookback_years`` most
    recent periods, and compares against the sector threshold.  A **trend
    guard** triggers a warning when the most recent ICR is >20% below the
    median.  If the most recent period has negative EBIT with positive interest
    expense, the result is an automatic FAIL.

    When *data* is a single :class:`FinancialPeriod`, behavior falls back to
    the existing single-period logic via :func:`interest_coverage_check`.

    Args:
        data: Multi-year history or a single financial period.
        sector: GICS sector for sector-adjusted thresholds.
        config: Optional configuration (defaults used if None).
    """
    # --- Single-period fallback ---
    if isinstance(data, FinancialPeriod):
        return interest_coverage_check(data, sector=sector, config=config)

    # --- Multi-year path ---
    name = "interest_coverage"
    cfg = config or InterestCoverageConfig()
    threshold = _get_config_threshold(sector, cfg)

    # Compute ICR for each period, skipping those with no interest expense.
    lookback = cfg.median_lookback_years
    recent_periods = data.periods[-lookback:]

    icr_values: list[float] = []
    for period in recent_periods:
        icr = _compute_icr(period)
        if icr is not None:
            icr_values.append(icr)

    # If all periods lack interest expense => no debt service => PASS
    if not icr_values:
        return FilterResult(
            name=name,
            passed=True,
            threshold=threshold,
            detail="No interest expense in any period; no debt service obligation",
            computed_metrics={},
        )

    # Median ICR
    median_icr = median(icr_values)
    current_icr = _compute_icr(data.periods[-1])

    # --- Negative EBIT auto-fail ---
    most_recent = data.periods[-1]
    most_recent_ie = most_recent.current_income.interest_expense
    most_recent_ebit = float(most_recent.current_income.ebit)
    if most_recent_ebit < 0 and most_recent_ie is not None and most_recent_ie > 0:
        metrics: dict[str, float] = {
            "median_icr": round(median_icr, 4),
        }
        if current_icr is not None:
            metrics["current_icr"] = round(current_icr, 4)
        return FilterResult(
            name=name,
            passed=False,
            value=round(median_icr, 4),
            threshold=threshold,
            detail="Auto FAIL: negative EBIT with interest expense in most recent period",
            computed_metrics=metrics,
        )

    # --- Median vs threshold ---
    passed = median_icr > threshold
    median_rounded = round(median_icr, 4)

    metrics = {
        "median_icr": median_rounded,
        "periods_used": float(len(icr_values)),
    }
    if current_icr is not None:
        metrics["current_icr"] = round(current_icr, 4)

    # --- Trend guard ---
    warning = False
    warning_reason: str | None = None
    if current_icr is not None and median_icr > 0:
        decline_pct = (median_icr - current_icr) / median_icr
        metrics["decline_pct"] = round(decline_pct, 4)
        if decline_pct > 0.20:
            warning = True
            warning_reason = "ICR deteriorating"

    sector_label = sector.value if sector else "default"
    detail = (
        f"Median ICR={median_rounded:.4f} ({'PASS' if passed else 'FAIL'}, "
        f"threshold>{threshold} for {sector_label})"
    )

    return FilterResult(
        name=name,
        passed=passed,
        value=median_rounded,
        threshold=threshold,
        detail=detail,
        computed_metrics=metrics,
        warning=warning,
        warning_reason=warning_reason,
    )
