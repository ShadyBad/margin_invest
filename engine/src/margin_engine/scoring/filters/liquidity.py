"""Liquidity filter — minimum market cap, volume, and history.

Checks whether an asset meets minimum liquidity and coverage requirements
before it enters the scoring pipeline. This is a pre-scoring elimination
filter that uses static asset metadata (AssetProfile), not financial period data.

**v1 criteria** (``liquidity_check``):
- Market Cap >= $100M (sector-adjusted: Utilities/RE >= $1B, Energy/Financials >= $500M)
- Average Daily Dollar Volume >= $1M (or tiered by market cap bucket with config)
- Years of Trading History >= 5

**v2 criteria** (``liquidity_check_v2``):
All v1 criteria plus:
- 90d median dollar volume vs tier threshold (from price bars)
- Position sizing: days_to_fill <= max_days
- Divergence ratio: 90d/20d <= max ratio (liquidity not evaporating)

When a ``LiquidityConfig`` is supplied, thresholds are read from the config
object instead of the module-level constants.  Without a config the original
hardcoded behaviour is preserved for backward compatibility.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.config.filter_config import LiquidityConfig
from margin_engine.models.financial import AssetProfile, GICSSector, PriceBar
from margin_engine.models.liquidity import (
    LiquidityProfile,
    compute_liquidity_profile,
    days_to_fill,
    liquidity_divergence_ratio,
    market_impact_estimate,
)
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
# Public API — v1 (deprecated)
# ---------------------------------------------------------------------------


def liquidity_check(
    profile: AssetProfile,
    config: LiquidityConfig | None = None,
) -> FilterResult:
    """Check minimum liquidity and coverage requirements (v1, deprecated).

    .. deprecated::
        Use :func:`liquidity_check_v2` which adds position sizing, divergence,
        and price-bar-derived volume checks.

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

    # 1. Market cap check (sector-adjusted)
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
    override_note = f" [{profile.sector.value} override]" if has_override else ""
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
        f"years_of_history={profile.years_of_history} {hist_label} (threshold={min_years})"
    )
    if not hist_passed:
        all_passed = False

    detail = "; ".join(criteria)

    return FilterResult(
        name=name,
        passed=all_passed,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Public API — v2
# ---------------------------------------------------------------------------


def liquidity_check_v2(
    profile: AssetProfile,
    price_bars: list[PriceBar] | None = None,
    config: LiquidityConfig | None = None,
) -> FilterResult:
    """Enhanced liquidity check with position sizing and divergence analysis.

    Runs all v1 checks (market cap, volume, history) plus:

    - **90d median dollar volume** vs tiered threshold (computed from price bars)
    - **Position sizing**: can a $500K position be filled in <= 5 days at 5%
      participation rate?
    - **Divergence ratio**: is 90d/20d volume ratio <= 3.0? (liquidity not
      evaporating)

    When ``price_bars`` is ``None``, falls back to v1 behavior using only
    ``profile.avg_daily_volume``.

    Args:
        profile: Static asset metadata including sector, market cap, volume, history.
        price_bars: Optional daily OHLCV bars for computing liquidity profile.
            When provided, enables position sizing and divergence checks.
        config: Optional ``LiquidityConfig``. When ``None``, default config is used.

    Returns:
        FilterResult with computed_metrics dict containing all derived values.
    """
    if config is None:
        config = LiquidityConfig()

    name = "liquidity"
    criteria: list[str] = []
    all_passed = True
    metrics: dict[str, float] = {}

    # 1. Market cap check (sector-adjusted)
    cap_threshold = _config_market_cap_threshold(profile.sector, config)
    sector_key = profile.sector.name.lower()
    has_override = getattr(config.market_cap_minimum, sector_key, None) is not None

    cap_passed = profile.market_cap >= cap_threshold
    cap_label = "PASS" if cap_passed else "FAIL"
    override_note = f" [{profile.sector.value} override]" if has_override else ""
    criteria.append(
        f"market_cap=${float(profile.market_cap):,.0f} {cap_label} "
        f"(threshold=${float(cap_threshold):,.0f}{override_note})"
    )
    metrics["market_cap"] = float(profile.market_cap)
    metrics["market_cap_threshold"] = float(cap_threshold)
    if not cap_passed:
        all_passed = False

    # 3. Years of history check
    min_years = config.min_years_of_history
    hist_passed = profile.years_of_history >= min_years
    hist_label = "PASS" if hist_passed else "FAIL"
    criteria.append(
        f"years_of_history={profile.years_of_history} {hist_label} (threshold={min_years})"
    )
    metrics["years_of_history"] = float(profile.years_of_history)
    if not hist_passed:
        all_passed = False

    # 4. Compute liquidity profile from price bars (or fall back to profile volume)
    liq_profile: LiquidityProfile | None = None
    if price_bars:
        liq_profile = compute_liquidity_profile(price_bars)

    # 5. 90d median dollar volume check
    bucket = _market_cap_bucket(profile.market_cap)
    vol_threshold = Decimal(str(getattr(config.dollar_volume, bucket)))

    if liq_profile is not None and liq_profile.median_dollar_volume_90d is not None:
        effective_volume = liq_profile.median_dollar_volume_90d
        vol_source = "90d_median"
    else:
        effective_volume = profile.avg_daily_volume
        vol_source = "profile_avg"

    vol_passed = effective_volume >= vol_threshold
    vol_label = "PASS" if vol_passed else "FAIL"
    criteria.append(
        f"dollar_volume({vol_source})=${float(effective_volume):,.0f} {vol_label} "
        f"(threshold=${float(vol_threshold):,.0f} [{bucket}])"
    )
    metrics["dollar_volume"] = float(effective_volume)
    metrics["dollar_volume_threshold"] = float(vol_threshold)
    if not vol_passed:
        all_passed = False

    # 6. Position sizing check (only when price bars available)
    if liq_profile is not None and liq_profile.median_dollar_volume_90d is not None:
        ps_config = config.position_sizing
        dtf = days_to_fill(
            position_size=float(ps_config.target_position),
            participation_rate=ps_config.max_participation_rate,
            median_dollar_volume=liq_profile.median_dollar_volume_90d,
        )
        impact_bps = market_impact_estimate(ps_config.max_participation_rate)

        dtf_passed = dtf <= ps_config.max_days_to_fill
        dtf_label = "PASS" if dtf_passed else "FAIL"
        criteria.append(f"days_to_fill={dtf:.1f} {dtf_label} (max={ps_config.max_days_to_fill})")
        metrics["days_to_fill"] = dtf
        metrics["market_impact_bps"] = impact_bps
        if not dtf_passed:
            all_passed = False

    # 7. Divergence ratio check (only when both windows available)
    if liq_profile is not None:
        div_ratio = liquidity_divergence_ratio(
            liq_profile.median_dollar_volume_20d,
            liq_profile.median_dollar_volume_90d,
        )
        if div_ratio is not None:
            div_passed = div_ratio <= config.divergence_max_ratio
            div_label = "PASS" if div_passed else "FAIL"
            criteria.append(
                f"divergence_ratio={div_ratio:.2f} {div_label} "
                f"(max={config.divergence_max_ratio:.1f})"
            )
            metrics["divergence_ratio"] = div_ratio
            if not div_passed:
                all_passed = False

    # Store 90d median if available
    if liq_profile is not None and liq_profile.median_dollar_volume_90d is not None:
        metrics["median_dollar_volume_90d"] = float(liq_profile.median_dollar_volume_90d)
    if liq_profile is not None and liq_profile.median_dollar_volume_20d is not None:
        metrics["median_dollar_volume_20d"] = float(liq_profile.median_dollar_volume_20d)

    detail = "; ".join(criteria)

    return FilterResult(
        name=name,
        passed=all_passed,
        detail=detail,
        computed_metrics=metrics if metrics else None,
    )
