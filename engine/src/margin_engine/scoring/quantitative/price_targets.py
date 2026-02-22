"""Multi-factor intrinsic value and price target computation.

Synthesizes four valuation methods into a consensus intrinsic value:
- DCF (35% weight) -- Two-stage DCF intrinsic value per share
- EV/FCF (25% weight) -- Implied price from 15x target EV/FCF multiple
- Acquirer's Multiple (20% weight) -- Implied price from 12x target EV/EBIT multiple
- Shareholder Yield (20% weight) -- Implied price from 4% target yield

Only methods with valid data contribute; weights renormalize when a method
returns None.

The intrinsic value IS the buy price (floor) — you buy at fair value.
The sell price applies the margin of safety upward: sell = intrinsic * (1 + MoS).
This protects against calculation error and caps expected upside.

Margin of safety uses a two-layer approach inspired by top value investors:
1. Quality tier base (Graham/Buffett/Klarman): business predictability sets the
   floor — steady businesses get 25%, turnarounds get 40%.
2. Dispersion adjustment: when valuation methods disagree (high coefficient of
   variation), MoS widens by up to 10%. When they agree, it tightens by up to 5%.
   This makes sell prices naturally adjust as fundamentals change.
"""

from __future__ import annotations

import logging
import math
import statistics
from decimal import Decimal

from pydantic import BaseModel, model_validator

from margin_engine.models.financial import AssetProfile, FinancialPeriod, PriceBar
from margin_engine.models.scoring import ConvictionLevel, GrowthStage
from margin_engine.models.valuation_audit import MethodAudit, ValuationAudit

logger = logging.getLogger(__name__)

# Method weights (must sum to 1.0)
_METHOD_WEIGHTS: dict[str, float] = {
    "dcf": 0.35,
    "ev_fcf": 0.25,
    "acquirers_multiple": 0.20,
    "shareholder_yield": 0.20,
}

# Quality-tier base margin of safety by growth stage.
# Informed by practitioner norms: Buffett ~25% for quality, Graham 33%+ for
# deep value, Klarman 30-50% for uncertain situations.
_BASE_MOS: dict[GrowthStage, float] = {
    GrowthStage.STEADY_GROWTH: 0.25,
    GrowthStage.MATURE: 0.25,
    GrowthStage.HIGH_GROWTH: 0.30,
    GrowthStage.CYCLICAL: 0.35,
    GrowthStage.TURNAROUND: 0.40,
}

_DEFAULT_BASE_MOS = 0.30  # When growth stage is unknown

# Dispersion adjustment bounds
_DISPERSION_TIGHTEN_MAX = 0.05  # Max reduction when methods agree closely
_DISPERSION_WIDEN_MAX = 0.10  # Max increase when methods diverge
_LOW_CV_THRESHOLD = 0.10  # CV below this = methods agree well
_HIGH_CV_THRESHOLD = 0.50  # CV above this = max widening

# Hard floor/ceiling regardless of adjustments
_MOS_FLOOR = 0.15
_MOS_CEILING = 0.50

# Input validation bounds
_MIN_SHARES = 100_000
_MAX_SHARES = 50_000_000_000
_MIN_IMPLIED_MARKET_CAP = 1_000_000
_MAX_IMPLIED_MARKET_CAP = 10_000_000_000_000

# Layer 2: Per-method output bounds
_MIN_PER_SHARE_PRICE = 0.01
_MAX_PRICE_MULTIPLE = 20.0

# Layer 3: Cross-method consistency bounds
_OUTLIER_LOW_RATIO = 0.1
_OUTLIER_HIGH_RATIO = 10.0

# Layer 1b: Currency mismatch detection
# If revenue-per-share exceeds this multiple of the stock price, financials are
# likely reported in a foreign currency while the stock trades in USD.
_CURRENCY_MISMATCH_RATIO = 10.0

# Layer 4: Final output validation bounds — clamp instead of reject
_MIN_PRICE_RATIO = 0.01  # Intrinsic value floor: 1% of actual_price
_MAX_PRICE_RATIO = 10.0  # Intrinsic value ceiling: 10x actual_price
_ABS_MIN_INTRINSIC = 0.10  # Absolute floor when no actual_price
_ABS_MAX_INTRINSIC = 1_000_000.0  # Absolute ceiling when no actual_price


class PriceTargets(BaseModel):
    """Multi-method intrinsic value and price target result."""

    margin_invest_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    margin_of_safety: float | None = None
    valuation_methods: dict[str, float] | None = None
    invalid_reason: str | None = None
    valuation_audit: ValuationAudit | None = None

    @model_validator(mode="after")
    def check_invalid_reason_consistency(self) -> PriceTargets:
        """If invalid_reason is set, all price fields must be None."""
        if self.invalid_reason is not None:
            price_fields = [
                self.margin_invest_value,
                self.buy_price,
                self.sell_price,
                self.price_upside,
            ]
            if any(f is not None for f in price_fields):
                raise ValueError("Price fields must be None when invalid_reason is set")
        return self

    @model_validator(mode="after")
    def check_positive_prices(self) -> PriceTargets:
        """margin_invest_value, buy_price, sell_price must be > 0 when present."""
        for field_name in ("margin_invest_value", "buy_price", "sell_price"):
            val = getattr(self, field_name)
            if val is not None and val <= 0:
                raise ValueError(f"{field_name} must be > 0 when set, got {val}")
        return self


def compute_price_targets(
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars: list[PriceBar],
    conviction_level: ConvictionLevel,
    growth_stage: GrowthStage | None = None,
    growth_rate: float = 0.05,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.025,
    projection_years: int = 10,
) -> PriceTargets:
    """Compute consensus price targets from multiple valuation methods.

    Margin of safety is dynamic:
    1. Quality-tier base from growth_stage (steady=25%, turnaround=40%)
    2. Adjusted ±based on valuation method dispersion (CV)

    Returns a PriceTargets model with intrinsic value, buy/sell prices,
    and the per-method implied prices. If shares_outstanding is missing or
    non-positive, returns PriceTargets with only actual_price populated.
    """
    actual_price = _latest_close(price_bars)
    shares = profile.shares_outstanding

    if shares is None or shares <= 0:
        return PriceTargets(
            actual_price=actual_price,
            invalid_reason="shares_outstanding_missing",
        )

    # Layer 1: Fixed share bounds
    if shares < _MIN_SHARES or shares > _MAX_SHARES:
        logger.warning(
            "Layer 1 reject: %s shares_outstanding=%d outside [%d, %d]",
            profile.ticker,
            shares,
            _MIN_SHARES,
            _MAX_SHARES,
        )
        return PriceTargets(
            actual_price=actual_price,
            invalid_reason="shares_outstanding_out_of_bounds",
        )

    # Layer 1: Market-cap cross-validation
    if actual_price is not None and actual_price > 0:
        implied_mcap = actual_price * shares
        if implied_mcap < _MIN_IMPLIED_MARKET_CAP or implied_mcap > _MAX_IMPLIED_MARKET_CAP:
            logger.warning(
                "Layer 1 reject: %s implied_market_cap=%.2f outside [%d, %d]",
                profile.ticker,
                implied_mcap,
                _MIN_IMPLIED_MARKET_CAP,
                _MAX_IMPLIED_MARKET_CAP,
            )
            return PriceTargets(
                actual_price=actual_price,
                invalid_reason="implied_market_cap_unreasonable",
            )

    # Layer 1b: Currency mismatch detection.
    # Detected mismatches are logged but no longer reject — the universe filter
    # ensures only exchange-listed stocks reach here, and Layer 4 clamping
    # provides a conservative cap if valuations are inflated by currency.
    currency_mismatch = _detect_currency_mismatch(period, shares, actual_price)
    if currency_mismatch:
        logger.info(
            "Layer 1b: %s likely currency mismatch — proceeding with clamped valuation",
            profile.ticker,
        )

    # Compute each valuation method (returns (result, inputs, intermediates, exclusion_reason))
    method_results: dict[
        str,
        tuple[float | None, dict[str, float], dict[str, float], str | None],
    ] = {
        "dcf": _dcf_intrinsic_per_share(
            period=period,
            shares=shares,
            growth_rate=growth_rate,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate,
            projection_years=projection_years,
            actual_price=actual_price,
        ),
        "ev_fcf": _ev_fcf_implied_per_share(
            period=period,
            shares=shares,
            actual_price=actual_price,
        ),
        "acquirers_multiple": _acquirers_implied_per_share(
            period=period,
            shares=shares,
            actual_price=actual_price,
        ),
        "shareholder_yield": _shareholder_yield_implied_per_share(
            period=period,
            shares=shares,
            actual_price=actual_price,
        ),
    }

    # Build initial MethodAudit objects for each method
    method_audits: dict[str, MethodAudit] = {}
    methods: dict[str, float | None] = {}
    for key, (result, inputs, intermediates, exclusion_reason) in method_results.items():
        methods[key] = result
        method_audits[key] = MethodAudit(
            method=key,
            result_per_share=result,
            weight=_METHOD_WEIGHTS[key],
            included=result is not None,
            exclusion_reason=exclusion_reason,
            inputs=inputs,
            intermediates=intermediates,
        )

    # Filter to valid methods only
    valid_methods: dict[str, float] = {k: v for k, v in methods.items() if v is not None}

    if not valid_methods:
        return PriceTargets(
            actual_price=actual_price,
            invalid_reason="insufficient_data",
        )

    # Layer 3: Cross-method consistency — exclude outlier methods
    pre_outlier_keys = set(valid_methods.keys())
    valid_methods = _filter_outlier_methods(valid_methods)
    # Mark methods removed by outlier filter
    for key in pre_outlier_keys - set(valid_methods.keys()):
        method_audits[key].included = False
        method_audits[key].exclusion_reason = "outlier_filtered"

    if not valid_methods:
        logger.warning("Layer 3 reject: %s all methods filtered as inconsistent", profile.ticker)
        return PriceTargets(
            actual_price=actual_price,
            invalid_reason="methods_inconsistent",
        )

    # Renormalize weights for valid methods
    total_weight = sum(_METHOD_WEIGHTS[k] for k in valid_methods)
    for key, audit in method_audits.items():
        if audit.included:
            audit.renormalized_weight = _METHOD_WEIGHTS[key] / total_weight

    intrinsic_value = sum(_METHOD_WEIGHTS[k] / total_weight * v for k, v in valid_methods.items())

    # Layer 4: Clamp intrinsic value to reasonable bounds instead of rejecting.
    # Deep-value stocks can genuinely trade at large discounts to intrinsic value.
    intrinsic_value, was_clamped = _clamp_intrinsic_value(intrinsic_value, actual_price)
    clamp_reason: str | None = None
    if was_clamped:
        logger.info(
            "Layer 4 clamp: %s intrinsic_value clamped to %.2f (actual_price=%s)",
            profile.ticker,
            intrinsic_value,
            actual_price,
        )
        if actual_price is not None and actual_price > 0:
            clamp_reason = "clamped_to_price_bounds"
        else:
            clamp_reason = "clamped_to_absolute_bounds"

    # Dual threshold margin of safety — MoS applied symmetrically.
    # Buy price is discounted below fair value (entry with safety margin).
    # Sell price is above fair value (exit when overvalued).
    mos, mos_base, mos_cv, mos_adjustment = _compute_margin_of_safety(
        valid_methods,
        intrinsic_value,
        growth_stage,
    )
    buy_price = intrinsic_value * (1 - mos)
    sell_price = intrinsic_value * (1 + mos)

    price_upside: float | None = None
    if actual_price is not None and actual_price > 0:
        price_upside = round((intrinsic_value - actual_price) / actual_price, 4)

    # Build the full ValuationAudit
    valuation_audit = ValuationAudit(
        margin_invest_value=round(intrinsic_value, 2),
        margin_of_safety=round(mos, 4),
        buy_price=round(buy_price, 2),
        sell_price=round(sell_price, 2),
        actual_price=actual_price,
        methods=list(method_audits.values()),
        mos_base=mos_base,
        mos_cv=mos_cv,
        mos_adjustment=mos_adjustment,
        was_clamped=was_clamped,
        clamp_reason=clamp_reason,
    )

    return PriceTargets(
        margin_invest_value=round(intrinsic_value, 2),
        buy_price=round(buy_price, 2),
        sell_price=round(sell_price, 2),
        actual_price=actual_price,
        price_upside=price_upside,
        margin_of_safety=round(mos, 4),
        valuation_methods={k: round(v, 2) for k, v in valid_methods.items()},
        valuation_audit=valuation_audit,
    )


def _compute_margin_of_safety(
    valid_methods: dict[str, float],
    intrinsic_value: float,
    growth_stage: GrowthStage | None,
) -> tuple[float, float, float | None, float]:
    """Compute dynamic margin of safety from quality tier + valuation dispersion.

    Returns (mos, base, cv, adjustment) for audit trail.

    Layer 1 — Quality tier base:
        Steady/Mature businesses (predictable cash flows) start at 25%.
        Turnarounds (high uncertainty) start at 40%.

    Layer 2 — Dispersion adjustment:
        Coefficient of variation (CV) across valuation methods measures how
        much they agree. Low CV tightens MoS (up to -5%), high CV widens
        (up to +10%). This makes buy/sell prices adjust naturally as the
        underlying fundamentals change day-to-day.
    """
    # Layer 1: Quality-tier base
    base = _BASE_MOS.get(growth_stage, _DEFAULT_BASE_MOS) if growth_stage else _DEFAULT_BASE_MOS

    # Layer 2: Dispersion adjustment (need 2+ methods to measure agreement)
    adjustment = 0.0
    cv: float | None = None
    if len(valid_methods) >= 2 and intrinsic_value > 0:
        values = list(valid_methods.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean if mean > 0 else 0.0

        if cv <= _LOW_CV_THRESHOLD:
            # Methods agree well — tighten proportionally
            adjustment = -_DISPERSION_TIGHTEN_MAX * (1 - cv / _LOW_CV_THRESHOLD)
        elif cv >= _HIGH_CV_THRESHOLD:
            # Methods diverge significantly — max widening
            adjustment = _DISPERSION_WIDEN_MAX
        else:
            # Linear interpolation between thresholds
            t = (cv - _LOW_CV_THRESHOLD) / (_HIGH_CV_THRESHOLD - _LOW_CV_THRESHOLD)
            adjustment = t * _DISPERSION_WIDEN_MAX

    mos = max(_MOS_FLOOR, min(_MOS_CEILING, base + adjustment))
    return mos, base, cv, adjustment


def _filter_outlier_methods(methods: dict[str, float]) -> dict[str, float]:
    """Remove methods whose value is < 0.1x or > 10x the median.

    Requires 2+ methods to filter. Returns the dict unchanged if < 2 methods.
    """
    if len(methods) < 2:
        return methods

    median = statistics.median(methods.values())
    if median <= 0:
        return methods

    return {
        k: v
        for k, v in methods.items()
        if _OUTLIER_LOW_RATIO * median <= v <= _OUTLIER_HIGH_RATIO * median
    }


def _detect_currency_mismatch(
    period: FinancialPeriod,
    shares: int,
    actual_price: float | None,
) -> bool:
    """Detect likely currency mismatch between financial data and stock price.

    Many OTC-traded foreign stocks report financials in their local currency
    (JPY, IDR, KRW, etc.) while trading in USD. This creates wildly inflated
    per-share metrics relative to the stock price.

    Heuristic: if revenue-per-share or OCF-per-share exceeds 10x the stock
    price, the financial data is almost certainly in a different currency.
    (Even the lowest-margin businesses rarely have P/S below 0.1.)
    """
    if actual_price is None or actual_price <= 0 or shares <= 0:
        return False

    threshold = _CURRENCY_MISMATCH_RATIO * actual_price

    revenue = period.current_income.revenue
    if revenue > 0:
        rev_per_share = float(revenue) / shares
        if rev_per_share > threshold:
            return True

    ocf = period.current_cash_flow.operating_cash_flow
    if ocf > 0:
        ocf_per_share = float(ocf) / shares
        if ocf_per_share > threshold:
            return True

    return False


def _clamp_intrinsic_value(
    intrinsic_value: float,
    actual_price: float | None,
) -> tuple[float, bool]:
    """Clamp intrinsic value to reasonable bounds. Returns (clamped_value, was_clamped)."""
    if actual_price is not None and actual_price > 0:
        floor = _MIN_PRICE_RATIO * actual_price
        ceiling = _MAX_PRICE_RATIO * actual_price
    else:
        floor = _ABS_MIN_INTRINSIC
        ceiling = _ABS_MAX_INTRINSIC

    if intrinsic_value < floor:
        return floor, True
    if intrinsic_value > ceiling:
        return ceiling, True
    return intrinsic_value, False


def _latest_close(bars: list[PriceBar]) -> float | None:
    """Return the close price of the latest-dated bar, or None if empty."""
    if not bars:
        return None
    latest = max(bars, key=lambda b: b.date)
    return float(latest.close)


def _dcf_intrinsic_per_share(
    period: FinancialPeriod,
    shares: int,
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    projection_years: int,
    actual_price: float | None = None,
) -> tuple[float | None, dict[str, float], dict[str, float], str | None]:
    """Two-stage DCF intrinsic value per share.

    Returns (result, inputs, intermediates, exclusion_reason).
    result is None if FCF <= 0 or discount_rate <= terminal_growth_rate.
    """
    inputs: dict[str, float] = {}
    intermediates: dict[str, float] = {}

    fcf = period.current_cash_flow.free_cash_flow
    inputs["fcf"] = float(fcf)
    inputs["growth_rate"] = growth_rate
    inputs["discount_rate"] = discount_rate
    inputs["terminal_growth_rate"] = terminal_growth_rate
    inputs["projection_years"] = float(projection_years)
    inputs["shares"] = float(shares)

    if fcf <= 0:
        return None, inputs, intermediates, "negative_fcf"

    if discount_rate <= terminal_growth_rate:
        return None, inputs, intermediates, "discount_rate_lte_terminal"

    fcf_float = float(fcf)

    # Stage 1: PV of projected free cash flows
    pv_sum = 0.0
    for t in range(1, projection_years + 1):
        projected = fcf_float * (1 + growth_rate) ** t
        pv_sum += projected / (1 + discount_rate) ** t

    # Stage 2: Terminal value
    final_fcf = fcf_float * (1 + growth_rate) ** projection_years
    terminal_value = final_fcf * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
    pv_terminal = terminal_value / (1 + discount_rate) ** projection_years

    intrinsic_total = pv_sum + pv_terminal
    intermediates["pv_stage1"] = pv_sum
    intermediates["pv_terminal"] = pv_terminal
    intermediates["intrinsic_total"] = intrinsic_total

    if intrinsic_total <= 0:
        return None, inputs, intermediates, "negative_intrinsic_total"

    result = intrinsic_total / shares
    if result < _MIN_PER_SHARE_PRICE:
        logger.debug(
            "Layer 2: %s result $%.4f < min $%.2f, excluding",
            "DCF",
            result,
            _MIN_PER_SHARE_PRICE,
        )
        return None, inputs, intermediates, "below_min_per_share"
    if (
        actual_price is not None
        and actual_price > 0
        and result > _MAX_PRICE_MULTIPLE * actual_price
    ):
        logger.debug(
            "Layer 2: %s result $%.2f > %.0fx actual $%.2f, excluding",
            "DCF",
            result,
            _MAX_PRICE_MULTIPLE,
            actual_price,
        )
        return None, inputs, intermediates, "exceeds_20x_price"
    return result, inputs, intermediates, None


def _ev_fcf_implied_per_share(
    period: FinancialPeriod,
    shares: int,
    target_multiple: float = 15.0,
    actual_price: float | None = None,
) -> tuple[float | None, dict[str, float], dict[str, float], str | None]:
    """Implied price from target EV/FCF multiple.

    Returns (result, inputs, intermediates, exclusion_reason).
    result is None if FCF <= 0.
    """
    inputs: dict[str, float] = {}
    intermediates: dict[str, float] = {}

    fcf = period.current_cash_flow.free_cash_flow
    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")

    inputs["fcf"] = float(fcf)
    inputs["target_multiple"] = target_multiple
    inputs["total_debt"] = float(total_debt)
    inputs["cash"] = float(cash)
    inputs["shares"] = float(shares)

    if fcf <= 0:
        return None, inputs, intermediates, "negative_fcf"

    implied_ev = target_multiple * float(fcf)
    implied_equity = implied_ev - float(total_debt) + float(cash)
    intermediates["implied_ev"] = implied_ev
    intermediates["implied_equity"] = implied_equity

    if implied_equity <= 0:
        return None, inputs, intermediates, "negative_implied_equity"

    result = implied_equity / shares
    if result < _MIN_PER_SHARE_PRICE:
        logger.debug(
            "Layer 2: %s result $%.4f < min $%.2f, excluding",
            "EV/FCF",
            result,
            _MIN_PER_SHARE_PRICE,
        )
        return None, inputs, intermediates, "below_min_per_share"
    if (
        actual_price is not None
        and actual_price > 0
        and result > _MAX_PRICE_MULTIPLE * actual_price
    ):
        logger.debug(
            "Layer 2: %s result $%.2f > %.0fx actual $%.2f, excluding",
            "EV/FCF",
            result,
            _MAX_PRICE_MULTIPLE,
            actual_price,
        )
        return None, inputs, intermediates, "exceeds_20x_price"
    return result, inputs, intermediates, None


def _acquirers_implied_per_share(
    period: FinancialPeriod,
    shares: int,
    target_multiple: float = 12.0,
    actual_price: float | None = None,
) -> tuple[float | None, dict[str, float], dict[str, float], str | None]:
    """Implied price from target EV/EBIT (Acquirer's Multiple).

    Returns (result, inputs, intermediates, exclusion_reason).
    result is None if EBIT <= 0.
    """
    inputs: dict[str, float] = {}
    intermediates: dict[str, float] = {}

    ebit = period.current_income.ebit
    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")

    inputs["ebit"] = float(ebit)
    inputs["target_multiple"] = target_multiple
    inputs["total_debt"] = float(total_debt)
    inputs["cash"] = float(cash)
    inputs["shares"] = float(shares)

    if ebit <= 0:
        return None, inputs, intermediates, "negative_ebit"

    implied_ev = target_multiple * float(ebit)
    implied_equity = implied_ev - float(total_debt) + float(cash)
    intermediates["implied_ev"] = implied_ev
    intermediates["implied_equity"] = implied_equity

    if implied_equity <= 0:
        return None, inputs, intermediates, "negative_implied_equity"

    result = implied_equity / shares
    if result < _MIN_PER_SHARE_PRICE:
        logger.debug(
            "Layer 2: %s result $%.4f < min $%.2f, excluding",
            "Acquirer's Multiple",
            result,
            _MIN_PER_SHARE_PRICE,
        )
        return None, inputs, intermediates, "below_min_per_share"
    if (
        actual_price is not None
        and actual_price > 0
        and result > _MAX_PRICE_MULTIPLE * actual_price
    ):
        logger.debug(
            "Layer 2: %s result $%.2f > %.0fx actual $%.2f, excluding",
            "Acquirer's Multiple",
            result,
            _MAX_PRICE_MULTIPLE,
            actual_price,
        )
        return None, inputs, intermediates, "exceeds_20x_price"
    return result, inputs, intermediates, None


def _shareholder_yield_implied_per_share(
    period: FinancialPeriod,
    shares: int,
    target_yield: float = 0.04,
    actual_price: float | None = None,
) -> tuple[float | None, dict[str, float], dict[str, float], str | None]:
    """Implied price from target shareholder yield.

    Returns (result, inputs, intermediates, exclusion_reason).
    result is None if total_return <= 0.
    """
    inputs: dict[str, float] = {}
    intermediates: dict[str, float] = {}

    dividends = abs(period.current_cash_flow.dividends_paid or Decimal("0"))
    net_buybacks = period.current_cash_flow.net_buybacks

    inputs["dividends"] = float(dividends)
    inputs["net_buybacks"] = float(net_buybacks)
    inputs["target_yield"] = target_yield
    inputs["shares"] = float(shares)

    total_return = dividends + net_buybacks
    intermediates["total_return"] = float(total_return)

    if total_return <= 0:
        return None, inputs, intermediates, "negative_total_return"

    implied_market_cap = float(total_return) / target_yield
    intermediates["implied_market_cap"] = implied_market_cap

    result = implied_market_cap / shares
    if result < _MIN_PER_SHARE_PRICE:
        logger.debug(
            "Layer 2: %s result $%.4f < min $%.2f, excluding",
            "Shareholder Yield",
            result,
            _MIN_PER_SHARE_PRICE,
        )
        return None, inputs, intermediates, "below_min_per_share"
    if (
        actual_price is not None
        and actual_price > 0
        and result > _MAX_PRICE_MULTIPLE * actual_price
    ):
        logger.debug(
            "Layer 2: %s result $%.2f > %.0fx actual $%.2f, excluding",
            "Shareholder Yield",
            result,
            _MAX_PRICE_MULTIPLE,
            actual_price,
        )
        return None, inputs, intermediates, "exceeds_20x_price"
    return result, inputs, intermediates, None
