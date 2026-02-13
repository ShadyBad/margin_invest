"""Liquidity filter — minimum market cap, volume, history, and sector eligibility.

Checks whether an asset meets minimum liquidity and coverage requirements
before it enters the scoring pipeline. This is a pre-scoring elimination
filter that uses static asset metadata (AssetProfile), not financial period data.

Criteria (all must pass):
- Market Cap >= $300M (sector-adjusted: Utilities >= $1B, Energy >= $500M)
- Average Daily Dollar Volume >= $1M
- Years of Trading History >= 5
- Sector not in {Financials, Real Estate} (v1 exclusion)
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import AssetProfile, GICSSector
from margin_engine.models.scoring import FilterResult

# Default thresholds
_DEFAULT_MARKET_CAP = Decimal("300_000_000")  # $300M
_MIN_AVG_DAILY_VOLUME = Decimal("1_000_000")  # $1M
_MIN_YEARS_OF_HISTORY = 5

# Sector-specific market cap overrides
_SECTOR_MARKET_CAP: dict[GICSSector, Decimal] = {
    GICSSector.UTILITIES: Decimal("1_000_000_000"),  # $1B
    GICSSector.ENERGY: Decimal("500_000_000"),  # $500M
}

# Excluded sectors (v1)
_EXCLUDED_SECTORS: frozenset[GICSSector] = frozenset({
    GICSSector.FINANCIALS,
    GICSSector.REAL_ESTATE,
})


def _market_cap_threshold(sector: GICSSector) -> Decimal:
    """Return the market cap threshold for a given sector."""
    return _SECTOR_MARKET_CAP.get(sector, _DEFAULT_MARKET_CAP)


def liquidity_check(profile: AssetProfile) -> FilterResult:
    """Check minimum liquidity and coverage requirements.

    Takes AssetProfile (not FinancialPeriod) since this uses static metadata.
    Returns FilterResult. If any criterion fails, the filter fails.
    The detail field lists all criteria checked and their status.

    Args:
        profile: Static asset metadata including sector, market cap, volume, history.

    Returns:
        FilterResult with passed=True only if all criteria pass.
    """
    name = "liquidity"
    criteria: list[str] = []
    all_passed = True

    # 1. Sector exclusion — checked first, overrides everything
    if profile.sector in _EXCLUDED_SECTORS:
        excluded_list = ", ".join(
            s.value for s in sorted(_EXCLUDED_SECTORS, key=lambda x: x.value)
        )
        detail = (
            f"Sector '{profile.sector.value}' is excluded in v1. "
            f"Excluded sectors: {excluded_list}"
        )
        return FilterResult(
            name=name,
            passed=False,
            detail=detail,
        )

    # 2. Market cap check (sector-adjusted)
    cap_threshold = _market_cap_threshold(profile.sector)
    cap_passed = profile.market_cap >= cap_threshold
    cap_label = "PASS" if cap_passed else "FAIL"
    override_note = (
        f" [{profile.sector.value} override]"
        if profile.sector in _SECTOR_MARKET_CAP
        else ""
    )
    criteria.append(
        f"market_cap=${float(profile.market_cap):,.0f} {cap_label} "
        f"(threshold=${float(cap_threshold):,.0f}{override_note})"
    )
    if not cap_passed:
        all_passed = False

    # 3. Average daily dollar volume check
    vol_passed = profile.avg_daily_volume >= _MIN_AVG_DAILY_VOLUME
    vol_label = "PASS" if vol_passed else "FAIL"
    criteria.append(
        f"avg_daily_volume=${float(profile.avg_daily_volume):,.0f} {vol_label} "
        f"(threshold=${float(_MIN_AVG_DAILY_VOLUME):,.0f})"
    )
    if not vol_passed:
        all_passed = False

    # 4. Years of history check
    hist_passed = profile.years_of_history >= _MIN_YEARS_OF_HISTORY
    hist_label = "PASS" if hist_passed else "FAIL"
    criteria.append(
        f"years_of_history={profile.years_of_history} {hist_label} "
        f"(threshold={_MIN_YEARS_OF_HISTORY})"
    )
    if not hist_passed:
        all_passed = False

    detail = "; ".join(criteria)

    return FilterResult(
        name=name,
        passed=all_passed,
        detail=detail,
    )
