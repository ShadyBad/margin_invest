"""Liquidity filter — minimum market cap, volume, history, and sector eligibility.

Checks whether an asset meets minimum liquidity and coverage requirements
before it enters the scoring pipeline. This is a pre-scoring elimination
filter that uses static asset metadata (AssetProfile), not financial period data.

Criteria (all must pass):
- Market Cap >= $300M (sector-adjusted: Utilities >= $1B, Energy >= $500M)
- Average Daily Dollar Volume >= $1M (or tiered by market cap bucket with config)
- Years of Trading History >= 5
- Sector not in {Financials, Real Estate} (v1 exclusion)

When a ``LiquidityConfig`` is supplied, thresholds are read from the config
object instead of the module-level constants.  Without a config the original
hardcoded behaviour is preserved for backward compatibility.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.config.filter_config import LiquidityConfig
from margin_engine.models.financial import AssetProfile, GICSSector
from margin_engine.models.scoring import FilterResult

# ---------------------------------------------------------------------------
# Legacy hardcoded thresholds (used when config=None for backward compat)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _market_cap_threshold(sector: GICSSector) -> Decimal:
    """Return the legacy market cap threshold for a given sector."""
    return _SECTOR_MARKET_CAP.get(sector, _DEFAULT_MARKET_CAP)


def _market_cap_bucket(market_cap: Decimal) -> str:
    """Determine market cap bucket for tiered thresholds."""
    if market_cap >= Decimal("200_000_000_000"):
        return "mega"
    if market_cap >= Decimal("10_000_000_000"):
        return "large"
    if market_cap >= Decimal("2_000_000_000"):
        return "mid"
    return "small"


def _config_market_cap_threshold(sector: GICSSector, config: LiquidityConfig) -> Decimal:
    """Return the market cap threshold for a sector using config values.

    Looks up sector-specific overrides on ``config.market_cap_minimum``
    (e.g. ``utilities``, ``energy``) and falls back to the ``default`` field.
    """
    sector_key = sector.name.lower()  # e.g. "utilities", "energy"
    value = getattr(config.market_cap_minimum, sector_key, None)
    if value is not None:
        return Decimal(str(value))
    return Decimal(str(config.market_cap_minimum.default))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def liquidity_check(
    profile: AssetProfile,
    config: LiquidityConfig | None = None,
) -> FilterResult:
    """Check minimum liquidity and coverage requirements.

    Takes AssetProfile (not FinancialPeriod) since this uses static metadata.
    Returns FilterResult. If any criterion fails, the filter fails.
    The detail field lists all criteria checked and their status.

    Args:
        profile: Static asset metadata including sector, market cap, volume, history.
        config: Optional ``LiquidityConfig``. When provided, thresholds are
            read from the config. When ``None``, the original hardcoded
            constants are used (backward compatibility).

    Returns:
        FilterResult with passed=True only if all criteria pass.
    """
    name = "liquidity"
    criteria: list[str] = []
    all_passed = True

    # 1. Sector exclusion — checked first, overrides everything
    if config is not None:
        excluded_sector_values = set(config.excluded_sectors)
    else:
        excluded_sector_values = {s.value for s in _EXCLUDED_SECTORS}

    if profile.sector.value in excluded_sector_values:
        excluded_list = ", ".join(sorted(excluded_sector_values))
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
    if config is not None:
        cap_threshold = _config_market_cap_threshold(profile.sector, config)
        # Determine if this sector has a config override (not just the default)
        sector_key = profile.sector.name.lower()
        has_override = getattr(config.market_cap_minimum, sector_key, None) is not None
    else:
        cap_threshold = _market_cap_threshold(profile.sector)
        has_override = profile.sector in _SECTOR_MARKET_CAP

    cap_passed = profile.market_cap >= cap_threshold
    cap_label = "PASS" if cap_passed else "FAIL"
    override_note = (
        f" [{profile.sector.value} override]"
        if has_override
        else ""
    )
    criteria.append(
        f"market_cap=${float(profile.market_cap):,.0f} {cap_label} "
        f"(threshold=${float(cap_threshold):,.0f}{override_note})"
    )
    if not cap_passed:
        all_passed = False

    # 3. Average daily dollar volume check (tiered when config is provided)
    if config is not None:
        bucket = _market_cap_bucket(profile.market_cap)
        vol_threshold = Decimal(str(getattr(config.dollar_volume, bucket)))
    else:
        vol_threshold = _MIN_AVG_DAILY_VOLUME

    vol_passed = profile.avg_daily_volume >= vol_threshold
    vol_label = "PASS" if vol_passed else "FAIL"
    criteria.append(
        f"avg_daily_volume=${float(profile.avg_daily_volume):,.0f} {vol_label} "
        f"(threshold=${float(vol_threshold):,.0f})"
    )
    if not vol_passed:
        all_passed = False

    # 4. Years of history check
    min_years = config.min_years_of_history if config is not None else _MIN_YEARS_OF_HISTORY
    hist_passed = profile.years_of_history >= min_years
    hist_label = "PASS" if hist_passed else "FAIL"
    criteria.append(
        f"years_of_history={profile.years_of_history} {hist_label} "
        f"(threshold={min_years})"
    )
    if not hist_passed:
        all_passed = False

    detail = "; ".join(criteria)

    return FilterResult(
        name=name,
        passed=all_passed,
        detail=detail,
    )
