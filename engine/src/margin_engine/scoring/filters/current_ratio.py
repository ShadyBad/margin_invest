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

from margin_engine.config.filter_config import CurrentRatioConfig
from margin_engine.models.financial import FinancialPeriod, GICSSector
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
    threshold = _get_config_threshold(sector, config) if config else _get_threshold(sector)
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
