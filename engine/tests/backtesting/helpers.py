"""Test helpers for building synthetic PIT data for backtesting tests.

Provides factory functions that produce InMemoryPITProvider instances pre-loaded
with realistic financial data.  Every ticker's data is designed to pass all 6
elimination filters (liquidity, Beneish M-Score, Altman Z'', FCF distress,
interest coverage, current ratio) so that backtesting tests can focus on
scoring and ablation logic rather than filter thresholds.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from margin_engine.backtesting.pit_provider import InMemoryPITProvider
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)

# ---------------------------------------------------------------------------
# Ticker -> sector mapping.  Unknown tickers default to TECHNOLOGY.
# ---------------------------------------------------------------------------
TICKER_SECTORS: dict[str, GICSSector] = {
    "AAPL": GICSSector.TECHNOLOGY,
    "MSFT": GICSSector.TECHNOLOGY,
    "GOOGL": GICSSector.TECHNOLOGY,
    "META": GICSSector.TECHNOLOGY,
    "AMZN": GICSSector.CONSUMER_DISCRETIONARY,
    "JNJ": GICSSector.HEALTHCARE,
    "XOM": GICSSector.ENERGY,
    "PG": GICSSector.CONSUMER_STAPLES,
}

TICKER_NAMES: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corp.",
    "GOOGL": "Alphabet Inc.",
    "META": "Meta Platforms Inc.",
    "AMZN": "Amazon.com Inc.",
    "JNJ": "Johnson & Johnson",
    "XOM": "Exxon Mobil Corp.",
    "PG": "Procter & Gamble Co.",
}


def _sector_for(ticker: str) -> GICSSector:
    return TICKER_SECTORS.get(ticker, GICSSector.TECHNOLOGY)


def _name_for(ticker: str) -> str:
    return TICKER_NAMES.get(ticker, f"{ticker} Inc.")


# ---------------------------------------------------------------------------
# Synthetic financial data builders.
#
# Values are chosen so that *every* elimination filter passes:
#   - market_cap > $10B, years_of_history > 5   (liquidity)
#   - EBIT positive, revenue stable              (Beneish safe -> M-Score << -1.78)
#   - Working capital positive, equity >> 0      (Altman Z'' > 1.1)
#   - FCF positive                               (FCF distress)
#   - EBIT / interest_expense >> 5               (interest coverage, even for IT sector)
#   - current_assets / current_liabilities > 1.5 (current ratio)
# ---------------------------------------------------------------------------

_BASE_REVENUE = Decimal("50_000_000_000")  # $50B
_BASE_PRICE = 150.0


def _build_income(*, revenue: Decimal) -> IncomeStatement:
    gross_profit = revenue * Decimal("0.45")
    sga = revenue * Decimal("0.10")
    rd = revenue * Decimal("0.08")
    depreciation = revenue * Decimal("0.03")
    ebit = gross_profit - sga - rd - depreciation
    interest_expense = revenue * Decimal("0.005")
    tax_provision = ebit * Decimal("0.21")
    net_income = ebit - interest_expense - tax_provision
    return IncomeStatement(
        revenue=revenue,
        cost_of_revenue=revenue - gross_profit,
        gross_profit=gross_profit,
        sga_expense=sga,
        rd_expense=rd,
        depreciation=depreciation,
        ebit=ebit,
        interest_expense=interest_expense,
        tax_provision=tax_provision,
        net_income=net_income,
        shares_outstanding=1_000_000_000,
    )


def _build_balance(*, total_assets: Decimal) -> BalanceSheet:
    current_assets = total_assets * Decimal("0.40")
    current_liabilities = total_assets * Decimal("0.15")
    long_term_debt = total_assets * Decimal("0.10")
    total_equity = total_assets * Decimal("0.55")
    total_liabilities = total_assets - total_equity
    return BalanceSheet(
        total_assets=total_assets,
        current_assets=current_assets,
        cash_and_equivalents=current_assets * Decimal("0.30"),
        receivables=current_assets * Decimal("0.25"),
        total_liabilities=total_liabilities,
        current_liabilities=current_liabilities,
        long_term_debt=long_term_debt,
        short_term_debt=Decimal("0"),
        total_equity=total_equity,
        retained_earnings=total_equity * Decimal("0.60"),
        pp_and_e=total_assets * Decimal("0.20"),
        shares_outstanding=1_000_000_000,
    )


def _build_cash_flow(*, revenue: Decimal) -> CashFlowStatement:
    operating_cf = revenue * Decimal("0.20")
    capex = -(revenue * Decimal("0.05"))
    return CashFlowStatement(
        operating_cash_flow=operating_cf,
        capital_expenditures=capex,
        dividends_paid=-(revenue * Decimal("0.02")),
        share_repurchases=-(revenue * Decimal("0.03")),
        share_issuance=Decimal("0"),
    )


def _build_period(*, period_end: str, revenue: Decimal) -> FinancialPeriod:
    """Build a FinancialPeriod with current and prior data (identical prior)."""
    income = _build_income(revenue=revenue)
    balance = _build_balance(total_assets=revenue * Decimal("2.0"))
    cash_flow = _build_cash_flow(revenue=revenue)
    return FinancialPeriod(
        period_end=period_end,
        filing_date=period_end,  # Simplified: same day
        current_income=income,
        prior_income=income,  # Stable YoY -> benign Beneish
        current_balance=balance,
        prior_balance=balance,
        current_cash_flow=cash_flow,
        prior_cash_flow=cash_flow,
    )


def _build_profile(ticker: str) -> AssetProfile:
    sector = _sector_for(ticker)
    return AssetProfile(
        ticker=ticker,
        name=_name_for(ticker),
        sector=sector,
        sub_industry=None,
        market_cap=Decimal("50_000_000_000"),  # $50B — well above $300M minimum
        avg_daily_volume=Decimal("20_000_000"),
        shares_outstanding=1_000_000_000,
        years_of_history=10,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_pit_provider_with_tickers(
    tickers: list[str],
    start: date,
    end: date,
    monthly_return: float = 0.005,
) -> InMemoryPITProvider:
    """Build an InMemoryPITProvider with synthetic data for backtesting.

    For each ticker and each month in [start, end], a PITSnapshot is added
    with realistic financial data that passes all 6 elimination filters.

    Args:
        tickers: List of ticker symbols. Known tickers (AAPL, MSFT, GOOGL,
            AMZN, META, JNJ, XOM, PG) get their real sector; unknown tickers
            default to Information Technology.
        start: First month (inclusive).
        end: Last month (inclusive).
        monthly_return: Price growth rate per month (default 0.5%).

    Returns:
        A populated InMemoryPITProvider.
    """
    provider = InMemoryPITProvider()

    for ticker in tickers:
        profile = _build_profile(ticker)
        price = _BASE_PRICE
        current = date(start.year, start.month, 1)
        end_first = date(end.year, end.month, 1)

        while current <= end_first:
            # Revenue grows slightly each month so data isn't perfectly static
            month_offset = (current.year - start.year) * 12 + (current.month - start.month)
            revenue = _BASE_REVENUE * (1 + Decimal(str(monthly_return))) ** month_offset

            period_end_str = current.isoformat()
            period = _build_period(period_end=period_end_str, revenue=revenue)

            provider.add_snapshot(
                as_of_date=current,
                ticker=ticker,
                profile=profile,
                period=period,
                price=price,
            )

            price *= 1 + monthly_return
            # Advance to next month (stdlib-only, no dateutil)
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

    return provider
