"""Multi-factor intrinsic value and price target computation.

Synthesizes four valuation methods into a consensus intrinsic value:
- DCF (35% weight) -- Two-stage DCF intrinsic value per share
- EV/FCF (25% weight) -- Implied price from 15x target EV/FCF multiple
- Acquirer's Multiple (20% weight) -- Implied price from 12x target EV/EBIT multiple
- Shareholder Yield (20% weight) -- Implied price from 4% target yield

Only methods with valid data contribute; weights renormalize when a method
returns None.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from margin_engine.models.financial import AssetProfile, FinancialPeriod, PriceBar
from margin_engine.models.scoring import ConvictionLevel

# Method weights (must sum to 1.0)
_METHOD_WEIGHTS: dict[str, float] = {
    "dcf": 0.35,
    "ev_fcf": 0.25,
    "acquirers_multiple": 0.20,
    "shareholder_yield": 0.20,
}

# Margin of safety by conviction level
_MARGIN_OF_SAFETY: dict[ConvictionLevel, float] = {
    ConvictionLevel.EXCEPTIONAL: 0.15,
    ConvictionLevel.HIGH: 0.20,
    ConvictionLevel.WATCHLIST: 0.25,
    ConvictionLevel.NONE: 0.30,
}


class PriceTargets(BaseModel):
    """Multi-method intrinsic value and price target result."""

    intrinsic_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    price_upside: float | None = None
    valuation_methods: dict[str, float] | None = None


def compute_price_targets(
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars: list[PriceBar],
    conviction_level: ConvictionLevel,
    growth_rate: float = 0.05,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.025,
    projection_years: int = 10,
) -> PriceTargets:
    """Compute consensus price targets from multiple valuation methods.

    Returns a PriceTargets model with intrinsic value, buy/sell prices,
    and the per-method implied prices. If shares_outstanding is missing or
    non-positive, returns PriceTargets with only actual_price populated.
    """
    actual_price = _latest_close(price_bars)
    shares = profile.shares_outstanding

    if shares is None or shares <= 0:
        return PriceTargets(actual_price=actual_price)

    market_cap = profile.market_cap

    # Compute each valuation method (returns None if data is invalid)
    methods: dict[str, float | None] = {
        "dcf": _dcf_intrinsic_per_share(
            period=period,
            shares=shares,
            growth_rate=growth_rate,
            discount_rate=discount_rate,
            terminal_growth_rate=terminal_growth_rate,
            projection_years=projection_years,
        ),
        "ev_fcf": _ev_fcf_implied_per_share(
            period=period,
            market_cap=market_cap,
            shares=shares,
        ),
        "acquirers_multiple": _acquirers_implied_per_share(
            period=period,
            market_cap=market_cap,
            shares=shares,
        ),
        "shareholder_yield": _shareholder_yield_implied_per_share(
            period=period,
            market_cap=market_cap,
            shares=shares,
        ),
    }

    # Filter to valid methods only
    valid_methods: dict[str, float] = {
        k: v for k, v in methods.items() if v is not None
    }

    if not valid_methods:
        return PriceTargets(actual_price=actual_price)

    # Renormalize weights for valid methods
    total_weight = sum(_METHOD_WEIGHTS[k] for k in valid_methods)
    intrinsic_value = sum(
        _METHOD_WEIGHTS[k] / total_weight * v for k, v in valid_methods.items()
    )

    mos = _MARGIN_OF_SAFETY[conviction_level]
    buy_price = intrinsic_value * (1 - mos)
    sell_price = intrinsic_value  # Fair value

    price_upside: float | None = None
    if actual_price is not None and actual_price > 0:
        price_upside = round((intrinsic_value - actual_price) / actual_price, 4)

    return PriceTargets(
        intrinsic_value=round(intrinsic_value, 2),
        buy_price=round(buy_price, 2),
        sell_price=round(sell_price, 2),
        actual_price=actual_price,
        price_upside=price_upside,
        valuation_methods=valid_methods,
    )


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
) -> float | None:
    """Two-stage DCF intrinsic value per share.

    Returns None if FCF <= 0 or discount_rate <= terminal_growth_rate.
    """
    fcf = period.current_cash_flow.free_cash_flow
    if fcf <= 0:
        return None

    if discount_rate <= terminal_growth_rate:
        return None

    fcf_float = float(fcf)

    # Stage 1: PV of projected free cash flows
    pv_sum = 0.0
    for t in range(1, projection_years + 1):
        projected = fcf_float * (1 + growth_rate) ** t
        pv_sum += projected / (1 + discount_rate) ** t

    # Stage 2: Terminal value
    final_fcf = fcf_float * (1 + growth_rate) ** projection_years
    terminal_value = final_fcf * (1 + terminal_growth_rate) / (
        discount_rate - terminal_growth_rate
    )
    pv_terminal = terminal_value / (1 + discount_rate) ** projection_years

    intrinsic_total = pv_sum + pv_terminal
    if intrinsic_total <= 0:
        return None

    return intrinsic_total / shares


def _ev_fcf_implied_per_share(
    period: FinancialPeriod,
    market_cap: Decimal,
    shares: int,
    target_multiple: float = 15.0,
) -> float | None:
    """Implied price from target EV/FCF multiple.

    implied_ev = target_multiple * FCF
    implied_equity = implied_ev - debt + cash
    price = implied_equity / shares

    Returns None if FCF <= 0.
    """
    fcf = period.current_cash_flow.free_cash_flow
    if fcf <= 0:
        return None

    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")

    implied_ev = target_multiple * float(fcf)
    implied_equity = implied_ev - float(total_debt) + float(cash)

    if implied_equity <= 0:
        return None

    return implied_equity / shares


def _acquirers_implied_per_share(
    period: FinancialPeriod,
    market_cap: Decimal,
    shares: int,
    target_multiple: float = 12.0,
) -> float | None:
    """Implied price from target EV/EBIT (Acquirer's Multiple).

    implied_ev = target_multiple * EBIT
    implied_equity = implied_ev - debt + cash
    price = implied_equity / shares

    Returns None if EBIT <= 0.
    """
    ebit = period.current_income.ebit
    if ebit <= 0:
        return None

    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")

    implied_ev = target_multiple * float(ebit)
    implied_equity = implied_ev - float(total_debt) + float(cash)

    if implied_equity <= 0:
        return None

    return implied_equity / shares


def _shareholder_yield_implied_per_share(
    period: FinancialPeriod,
    market_cap: Decimal,
    shares: int,
    target_yield: float = 0.04,
) -> float | None:
    """Implied price from target shareholder yield.

    total_return = abs(dividends_paid) + net_buybacks
    implied_market_cap = total_return / target_yield
    price = implied_market_cap / shares

    Returns None if total_return <= 0.
    """
    dividends = abs(period.current_cash_flow.dividends_paid or Decimal("0"))
    net_buybacks = period.current_cash_flow.net_buybacks

    total_return = dividends + net_buybacks
    if total_return <= 0:
        return None

    implied_market_cap = float(total_return) / target_yield

    return implied_market_cap / shares
