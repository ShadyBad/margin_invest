"""Adapter: convert PITSnapshot -> TickerV3Data for scoring pipeline.

Bridges point-in-time historical data to the v3 scoring pipeline so the
replay orchestrator can use real scoring instead of simplified proxies.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.backtesting.pit_provider import PITSnapshot
from margin_engine.models.financial import FinancialHistory
from margin_engine.scoring.quantitative.wacc_sector import get_sector_wacc
from margin_engine.scoring.v3_pipeline import TickerV3Data

_DEFAULT_RETENTION_RATIO = 0.70
_MAX_GROWTH_RATE = 0.30
_MIN_GROWTH_RATE = 0.01
_TERMINAL_GROWTH = 0.025


def build_ticker_data_from_pit(
    snapshot: PITSnapshot,
    prior_snapshots: list[PITSnapshot] | None = None,
) -> TickerV3Data:
    """Convert a PITSnapshot into TickerV3Data for the v3 scoring pipeline.

    Args:
        snapshot: The current point-in-time snapshot to convert.
        prior_snapshots: Optional earlier snapshots for the same ticker,
            used to build a multi-period FinancialHistory.

    Returns:
        A fully populated TickerV3Data ready for v3 pipeline scoring.
    """
    period = snapshot.period
    profile = snapshot.profile
    income = period.current_income
    cf = period.current_cash_flow
    balance = period.current_balance

    shares = income.shares_outstanding or (balance.shares_outstanding if balance else 0)
    if not shares or shares <= 0:
        shares = 1  # avoid division by zero

    # FCF per share
    ocf = float(cf.operating_cash_flow or Decimal("0"))
    capex = float(cf.capital_expenditures or Decimal("0"))
    fcf = ocf + capex  # capex is typically negative
    fcf_per_share = fcf / shares

    # Sustainable growth rate: g = ROE * retention ratio
    equity = float(balance.total_equity or Decimal("0"))
    net_income_val = float(income.net_income or Decimal("0"))
    roe = net_income_val / equity if equity > 0 else 0.0
    growth_rate = max(_MIN_GROWTH_RATE, min(roe * _DEFAULT_RETENTION_RATIO, _MAX_GROWTH_RATE))

    # Simple DCF intrinsic value: FCF_per_share * (1 + g) / (WACC - terminal_growth)
    wacc = get_sector_wacc(profile.sector)
    dcf_iv = 0.0
    if fcf_per_share > 0 and wacc > _TERMINAL_GROWTH:
        dcf_iv = fcf_per_share * (1 + growth_rate) / (wacc - _TERMINAL_GROWTH)

    # Build financial history from current + prior snapshots
    periods = [snapshot.period]
    if prior_snapshots:
        for ps in prior_snapshots:
            periods.append(ps.period)
        periods.sort(key=lambda p: p.period_end)

    history = FinancialHistory(ticker=snapshot.ticker, periods=periods)

    return TickerV3Data(
        ticker=snapshot.ticker,
        history=history,
        latest_period=period,
        profile=profile,
        current_price=snapshot.price,
        current_fcf_per_share=fcf_per_share,
        sustainable_growth_rate=growth_rate,
        dcf_iv=dcf_iv,
        buyback_yield=None,
        insider_ownership_pct=None,
        sbc_pct=None,
        recent_acquisition_count=0,
        sue_percentile=50.0,
        momentum_percentile=50.0,
        beta=None,
    )
