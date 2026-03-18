"""Current Ratio financial health filter.

The Current Ratio (CR) measures a company's ability to meet short-term
obligations with its current assets. A ratio below sector-adjusted
thresholds indicates potential liquidity stress.

Formula:
    CR = Current Assets / Current Liabilities

Sector-adjusted thresholds:
    Technology:  > 0.8  (calibrated: Apple CR=0.87 due to buyback programs)
    Utilities:   > 0.6  (capital-intensive, regulated)
    All others:  > 0.8  (default minimum)

Calibration note:
    The original design had Technology at > 1.0, but Apple (the world's
    most valuable tech company) has CR = 0.8673 which would fail > 1.0.
    Since our design principles say "no human judgment" and we want the
    best returns, we lower the Technology threshold to > 0.8 to avoid
    excluding fundamentally strong mega-caps that use aggressive share
    buyback programs.
"""

from __future__ import annotations

from statistics import median

from margin_engine.config.filter_config import CurrentRatioConfig
from margin_engine.models.financial import FinancialHistory, FinancialPeriod, GICSSector
from margin_engine.models.scoring import FilterResult

# Sector-adjusted minimum CR thresholds
_SECTOR_THRESHOLDS: dict[GICSSector, float] = {
    GICSSector.TECHNOLOGY: 0.8,
    GICSSector.UTILITIES: 0.6,
}
_DEFAULT_THRESHOLD = 0.8


def _get_threshold(sector: GICSSector | None) -> float:
    """Return the CR threshold for the given sector (legacy hardcoded)."""
    if sector is None:
        return _DEFAULT_THRESHOLD
    return _SECTOR_THRESHOLDS.get(sector, _DEFAULT_THRESHOLD)


def _get_config_threshold(sector: GICSSector | None, config: CurrentRatioConfig) -> float:
    """Return the CR threshold for the given sector using config values."""
    if sector is not None:
        sector_key = sector.value.lower()
        override = config.sector_overrides.get(sector_key)
        if override is not None:
            return override
    return config.default


def current_ratio_check(
    period: FinancialPeriod,
    sector: GICSSector | None = None,
    config: CurrentRatioConfig | None = None,
) -> FilterResult:
    """Check current ratio against sector-adjusted thresholds.

    If current_liabilities is 0, the ratio is infinite -> PASS.

    Args:
        period: Financial data with current balance sheet.
        sector: GICS sector for sector-adjusted thresholds.
        config: Optional CurrentRatioConfig. When provided, thresholds
            are read from config.default and config.sector_overrides.
            When None, hardcoded constants are used.
    """
    name = "current_ratio"
    cfg = config or CurrentRatioConfig()
    threshold = _get_config_threshold(sector, cfg) if config else _get_threshold(sector)

    # Sector exemption check
    sector_value = sector.value if sector is not None else None
    if sector_value in cfg.exempt_sectors:
        return FilterResult(
            name=name,
            passed=True,
            threshold=threshold,
            detail=f"Sector '{sector_value}' is exempt from {name}",
        )

    current_assets = period.current_balance.current_assets
    current_liabilities = period.current_balance.current_liabilities

    # Zero current liabilities means infinite ratio -> automatically passes
    if current_liabilities == 0:
        return FilterResult(
            name=name,
            passed=True,
            threshold=threshold,
            detail="No current liabilities; infinite current ratio",
        )

    cr = float(current_assets / current_liabilities)
    cr_rounded = round(cr, 4)
    passed = cr > threshold

    sector_label = sector.value if sector else "default"
    detail = (
        f"CR={cr_rounded:.4f} ({'PASS' if passed else 'FAIL'}, "
        f"threshold>{threshold} for {sector_label})"
    )

    return FilterResult(
        name=name,
        passed=passed,
        value=cr_rounded,
        threshold=threshold,
        detail=detail,
    )


def _compute_cr(period: FinancialPeriod) -> float | None:
    """Compute current ratio for a single period. Returns None if zero liabilities."""
    current_liabilities = period.current_balance.current_liabilities
    if current_liabilities == 0:
        return None
    return float(period.current_balance.current_assets / current_liabilities)


def _compute_quick_ratio(period: FinancialPeriod) -> float:
    """Compute quick ratio for a single period.

    Quick ratio = (cash_and_equivalents + receivables) / current_liabilities.
    Treats None values as 0. Returns 0.0 if current_liabilities is 0.
    """
    bs = period.current_balance
    if bs.current_liabilities == 0:
        return 0.0
    cash = float(bs.cash_and_equivalents or 0)
    recv = float(bs.receivables or 0)
    return (cash + recv) / float(bs.current_liabilities)


def current_ratio_check_v2(
    data: FinancialHistory | FinancialPeriod,
    sector: GICSSector | None = None,
    config: CurrentRatioConfig | None = None,
) -> FilterResult:
    """Check current ratio using 3-year median with quick ratio rescue and decline guard.

    When *data* is a :class:`FinancialHistory`, the function computes CR for
    each period, takes the median over the 3 most recent periods (or fewer if
    less data is available), and compares against the sector threshold.

    **Quick ratio rescue**: If median CR < threshold but the most recent period's
    quick ratio > ``config.quick_ratio_rescue`` (default 0.5), the result is a
    PASS with ``warning=True``.

    **Decline guard**: If CR declined more than ``config.max_3yr_decline_pct``
    (default 30%) from the oldest to newest period in the lookback window,
    ``warning=True`` is set with an explanatory reason.

    When *data* is a single :class:`FinancialPeriod`, behavior falls back to
    the existing single-period logic via :func:`current_ratio_check`.

    Args:
        data: Multi-year history or a single financial period.
        sector: GICS sector for sector-adjusted thresholds.
        config: Optional configuration (defaults used if None).
    """
    # --- Single-period fallback ---
    if isinstance(data, FinancialPeriod):
        return current_ratio_check(data, sector=sector, config=config)

    # --- Multi-year path ---
    name = "current_ratio"
    cfg = config or CurrentRatioConfig()
    threshold = _get_config_threshold(sector, cfg)

    # Sector exemption check
    sector_value = sector.value if sector is not None else None
    if sector_value in cfg.exempt_sectors:
        return FilterResult(
            name=name,
            passed=True,
            threshold=threshold,
            detail=f"Sector '{sector_value}' is exempt from {name}",
        )

    # Use 3 most recent periods (or fewer if less data)
    lookback = 3
    recent_periods = data.periods[-lookback:]

    cr_values: list[float] = []
    for period in recent_periods:
        cr = _compute_cr(period)
        if cr is not None:
            cr_values.append(cr)

    # If all periods have zero liabilities => infinite ratio => PASS
    if not cr_values:
        return FilterResult(
            name=name,
            passed=True,
            threshold=threshold,
            detail="No current liabilities in any period; infinite current ratio",
            computed_metrics={},
        )

    # Median CR
    median_cr = median(cr_values)
    current_cr = _compute_cr(data.periods[-1])

    # Quick ratio of the most recent period
    quick_ratio = _compute_quick_ratio(data.periods[-1])

    metrics: dict[str, float] = {
        "median_cr": round(median_cr, 4),
        "periods_used": float(len(cr_values)),
        "quick_ratio": round(quick_ratio, 4),
    }
    if current_cr is not None:
        metrics["current_cr"] = round(current_cr, 4)

    # --- Median vs threshold ---
    passed = median_cr > threshold

    # --- Quick ratio rescue ---
    rescued = False
    if not passed and quick_ratio > cfg.quick_ratio_rescue:
        passed = True
        rescued = True

    # --- Decline guard ---
    warning = False
    warning_reason: str | None = None

    # Compute decline from oldest to newest CR in the lookback window
    if len(cr_values) >= 2:
        oldest_cr = cr_values[0]
        newest_cr = cr_values[-1]
        if oldest_cr > 0:
            decline_pct = ((oldest_cr - newest_cr) / oldest_cr) * 100.0
            metrics["decline_pct"] = round(decline_pct, 2)
            if decline_pct > cfg.max_3yr_decline_pct:
                warning = True
                warning_reason = (
                    f"CR declined {decline_pct:.1f}% from {oldest_cr:.2f} to "
                    f"{newest_cr:.2f} over {len(cr_values)} periods"
                )

    # Quick ratio rescue also triggers warning
    if rescued:
        warning = True
        rescue_reason = (
            f"Quick ratio rescue: CR below threshold but quick ratio "
            f"{quick_ratio:.2f} > {cfg.quick_ratio_rescue}"
        )
        if warning_reason:
            warning_reason = f"{warning_reason}; {rescue_reason}"
        else:
            warning_reason = rescue_reason

    median_rounded = round(median_cr, 4)
    sector_label = sector.value if sector else "default"
    rescue_note = " (quick ratio rescue)" if rescued else ""
    detail = (
        f"Median CR={median_rounded:.4f} ({'PASS' if passed else 'FAIL'}{rescue_note}, "
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
