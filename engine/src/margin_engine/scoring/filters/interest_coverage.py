"""Interest Coverage Ratio financial health filter.

The Interest Coverage Ratio (ICR) measures a company's ability to pay
interest on its outstanding debt. Companies that cannot cover their
interest obligations are at high risk of default.

Formula:
    ICR = EBIT / Interest Expense

Sector-adjusted thresholds:
    Technology:  > 3.0  (high-margin, low-debt expected)
    Utilities:   > 1.2  (capital-intensive, regulated)
    All others:  > 1.5  (default minimum)
"""

from __future__ import annotations

from margin_engine.config.filter_config import InterestCoverageConfig
from margin_engine.models.financial import FinancialPeriod, GICSSector
from margin_engine.models.scoring import FilterResult

# Sector-adjusted minimum ICR thresholds
_SECTOR_THRESHOLDS: dict[GICSSector, float] = {
    GICSSector.TECHNOLOGY: 3.0,
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
