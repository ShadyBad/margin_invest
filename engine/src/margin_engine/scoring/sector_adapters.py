"""Sector-specific profitability adapters and percentile normalization.

Different GICS sectors use different profitability metrics:
- Financials: ROE (net_income / total_equity)
- Real Estate: FFO proxy ((net_income + depreciation) / total_equity)
- All others: ROIC (NOPAT / invested_capital)

For Financials and Real Estate, conviction gates use sector-relative percentile
ranks instead of absolute thresholds. This module provides:
- ``SectorAdapter`` — selects the correct metric for a sector
- ``sector_percentile_rank()`` — computes percentile within a sector universe
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod, GICSSector

_PERCENTILE_SECTORS = frozenset({GICSSector.FINANCIALS, GICSSector.REAL_ESTATE})


def _compute_roe(period: FinancialPeriod) -> float:
    """ROE = net_income / total_equity. Returns 0.0 when equity is zero."""
    equity = period.current_balance.total_equity
    if equity == Decimal("0"):
        return 0.0
    return float(period.current_income.net_income / equity)


def _compute_ffo_proxy(period: FinancialPeriod) -> float:
    """FFO proxy = (net_income + depreciation) / total_equity.

    Treats ``None`` depreciation as zero. Returns 0.0 when equity is zero.
    """
    equity = period.current_balance.total_equity
    if equity == Decimal("0"):
        return 0.0
    depreciation = period.current_income.depreciation or Decimal("0")
    return float((period.current_income.net_income + depreciation) / equity)


def _compute_roic(period: FinancialPeriod) -> float:
    """ROIC = NOPAT / invested_capital.

    NOPAT = EBIT * (1 - effective_tax_rate)
    Invested capital = total_equity + total_debt - cash

    Returns 0.0 when invested capital is zero or negative.
    """
    tax_rate = period.current_income.effective_tax_rate
    nopat = float(period.current_income.ebit) * (1.0 - tax_rate)

    equity = period.current_balance.total_equity
    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")
    invested_capital = float(equity + total_debt - cash)

    if invested_capital <= 0:
        return 0.0
    return nopat / invested_capital


class SectorAdapter:
    """Selects the appropriate profitability metric for a GICS sector."""

    @staticmethod
    def profitability_metric(period: FinancialPeriod, sector: GICSSector) -> float:
        """Return the sector-appropriate profitability metric value.

        - Financials -> ROE
        - Real Estate -> FFO proxy
        - All others -> ROIC
        """
        if sector == GICSSector.FINANCIALS:
            return _compute_roe(period)
        if sector == GICSSector.REAL_ESTATE:
            return _compute_ffo_proxy(period)
        return _compute_roic(period)

    @staticmethod
    def metric_name(sector: GICSSector) -> str:
        """Return human-readable label for the sector's profitability metric."""
        if sector == GICSSector.FINANCIALS:
            return "ROE"
        if sector == GICSSector.REAL_ESTATE:
            return "FFO Proxy"
        return "ROIC"

    @staticmethod
    def needs_percentile_gates(sector: GICSSector) -> bool:
        """True if this sector uses percentile-based conviction gates.

        Only Financials and Real Estate use sector-relative percentiles;
        all other sectors keep absolute ROIC thresholds.
        """
        return sector in _PERCENTILE_SECTORS


def sector_percentile_rank(
    ticker_metric: float,
    sector: GICSSector,
    universe_metrics: list[float],
) -> float:
    """Compute the percentile rank of *ticker_metric* within *universe_metrics*.

    For non-percentile sectors (anything except Financials and Real Estate),
    returns 50.0 as a neutral default.

    For percentile sectors:
    - Empty universe -> 50.0
    - Percentile = (count of universe values <= ticker_metric) / len(universe) * 100

    Returns a float in [0.0, 100.0].
    """
    if not SectorAdapter.needs_percentile_gates(sector):
        return 50.0

    if not universe_metrics:
        return 50.0

    n = len(universe_metrics)
    count_le = sum(1 for v in universe_metrics if v <= ticker_metric)
    return (count_le / n) * 100.0
