"""DatabasePITProvider — AsyncPointInTimeProvider backed by PostgreSQL PIT tables.

Queries pit_financial_snapshots, pit_daily_prices, and pit_universe_membership
to supply point-in-time data for backtesting. All data returned reflects what was
publicly known at the as_of_date — no future data leakage.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from margin_engine.backtesting.pit_provider import DelistingEvent, DelistingType, PITSnapshot
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import PITDailyPrice, PITFinancialSnapshot, PITUniverseMembership


class DatabasePITProvider:
    """AsyncPointInTimeProvider backed by PostgreSQL PIT tables."""

    def __init__(self, session: AsyncSession, min_market_cap: float = 100_000_000):
        self._session = session
        self._min_market_cap = min_market_cap

    async def get_price(self, ticker: str, as_of_date: date) -> float | None:
        """Return closing price for a ticker at or before the given date.

        Queries pit_daily_prices with date <= as_of_date, ordered descending,
        returning the most recent close value. Returns None if no data.
        """
        stmt = (
            select(PITDailyPrice.close)
            .where(PITDailyPrice.ticker == ticker, PITDailyPrice.date <= as_of_date)
            .order_by(PITDailyPrice.date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return float(row) if row is not None else None

    async def get_snapshot(self, ticker: str, as_of_date: date) -> PITSnapshot | None:
        """Return point-in-time data for a specific ticker.

        Queries the 2 most recent filings where filing_date <= as_of_date
        (for YoY comparison), gets the price, builds FinancialPeriod and
        AssetProfile. Returns None if no filing or no price found.
        """
        # Get the 2 most recent filings where filing_date <= as_of_date
        stmt = (
            select(PITFinancialSnapshot)
            .where(
                PITFinancialSnapshot.ticker == ticker,
                PITFinancialSnapshot.filing_date <= as_of_date,
            )
            .order_by(PITFinancialSnapshot.filing_date.desc())
            .limit(2)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        if not rows:
            return None

        current_row = rows[0]
        prior_row = rows[1] if len(rows) > 1 else None

        # Get price
        price = await self.get_price(ticker, as_of_date)
        if price is None:
            return None

        period = _build_period(current_row, prior_row)
        profile = _build_profile(ticker, current_row, price)

        return PITSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            profile=profile,
            period=period,
            price=price,
            filing_date=current_row.filing_date,
        )

    async def get_universe(self, as_of_date: date) -> list[PITSnapshot]:
        """Return all tradeable stocks at the given date.

        Finds the nearest quarter_date <= as_of_date in pit_universe_memberships,
        filters by is_active=True and market_cap >= min_market_cap, then batch
        loads snapshots for all qualifying tickers.
        """
        from sqlalchemy import or_

        # Find the nearest quarter_date <= as_of_date
        nearest_q_stmt = (
            select(PITUniverseMembership.quarter_date)
            .where(PITUniverseMembership.quarter_date <= as_of_date)
            .order_by(PITUniverseMembership.quarter_date.desc())
            .limit(1)
        )
        nearest_q_result = await self._session.execute(nearest_q_stmt)
        nearest_quarter = nearest_q_result.scalar_one_or_none()

        if nearest_quarter is None:
            return []

        # Get all qualifying members for that quarter
        # Allow NULL market_cap (not yet computed) — treat as qualifying
        members_stmt = select(PITUniverseMembership.ticker).where(
            PITUniverseMembership.quarter_date == nearest_quarter,
            PITUniverseMembership.is_active.is_(True),
            or_(
                PITUniverseMembership.market_cap >= self._min_market_cap,
                PITUniverseMembership.market_cap.is_(None),
            ),
        )
        members_result = await self._session.execute(members_stmt)
        tickers = [row[0] for row in members_result.all()]

        if not tickers:
            return []

        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(
            "[pit_provider] get_universe(%s): quarter=%s, %d active tickers",
            as_of_date, nearest_quarter, len(tickers),
        )

        # Batch load: get the 2 most recent filings per ticker in one query
        # Uses a lateral join pattern: for each ticker, get rows ranked by filing_date
        from sqlalchemy import func as sa_func

        # Subquery: rank filings per ticker
        row_num = (
            sa_func.row_number()
            .over(
                partition_by=PITFinancialSnapshot.ticker,
                order_by=PITFinancialSnapshot.filing_date.desc(),
            )
            .label("rn")
        )
        sub = (
            select(PITFinancialSnapshot, row_num)
            .where(
                PITFinancialSnapshot.ticker.in_(tickers),
                PITFinancialSnapshot.filing_date <= as_of_date,
            )
            .subquery()
        )
        # Only keep top 2 per ticker
        ranked_stmt = select(sub).where(sub.c.rn <= 2)
        ranked_result = await self._session.execute(ranked_stmt)
        rows = ranked_result.all()

        # Group by ticker: {ticker: [current_row, prior_row]}
        from collections import defaultdict

        ticker_filings: dict[str, list] = defaultdict(list)
        for row in rows:
            ticker_filings[row.ticker].append(row)
        _logger.info(
            "[pit_provider] filings batch: %d rows, %d unique tickers",
            len(rows), len(ticker_filings),
        )

        # Batch load prices: get latest price per ticker in one query
        price_row_num = (
            sa_func.row_number()
            .over(
                partition_by=PITDailyPrice.ticker,
                order_by=PITDailyPrice.date.desc(),
            )
            .label("prn")
        )
        price_sub = (
            select(PITDailyPrice.ticker, PITDailyPrice.close, price_row_num)
            .where(
                PITDailyPrice.ticker.in_(tickers),
                PITDailyPrice.date <= as_of_date,
            )
            .subquery()
        )
        price_stmt = select(price_sub.c.ticker, price_sub.c.close).where(
            price_sub.c.prn == 1
        )
        price_result = await self._session.execute(price_stmt)
        ticker_prices: dict[str, float] = {
            row.ticker: float(row.close) for row in price_result.all()
        }
        _logger.info(
            "[pit_provider] prices batch: %d tickers with prices",
            len(ticker_prices),
        )

        # Build snapshots
        snapshots: list[PITSnapshot] = []
        for ticker in tickers:
            filings = ticker_filings.get(ticker, [])
            if not filings:
                continue

            price = ticker_prices.get(ticker)
            if price is None:
                continue

            # Sort by filing_date desc (should already be, but ensure)
            filings.sort(key=lambda r: r.filing_date, reverse=True)
            current_row = filings[0]
            prior_row = filings[1] if len(filings) > 1 else None

            # Build a lightweight object that has the same attributes
            period = _build_period_from_row(current_row, prior_row)
            profile = _build_profile_from_row(ticker, current_row, price)

            snapshots.append(
                PITSnapshot(
                    ticker=ticker,
                    as_of_date=as_of_date,
                    profile=profile,
                    period=period,
                    price=price,
                    filing_date=current_row.filing_date,
                )
            )

        return snapshots

    async def get_delisting(self, ticker: str) -> DelistingEvent | None:
        """Return delisting event for a ticker, or None if still listed.

        Queries pit_universe_memberships for the most recent record where
        delist_detected_at is not None.
        """
        stmt = (
            select(PITUniverseMembership)
            .where(
                PITUniverseMembership.ticker == ticker,
                PITUniverseMembership.delist_detected_at.isnot(None),
            )
            .order_by(PITUniverseMembership.quarter_date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return DelistingEvent(
            ticker=ticker,
            delist_date=row.delist_detected_at,
            delist_type=DelistingType.VOLUNTARY,
            last_price=row.last_known_price or 0.0,
        )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _build_period(
    current_row: PITFinancialSnapshot,
    prior_row: PITFinancialSnapshot | None,
) -> FinancialPeriod:
    """Convert PITFinancialSnapshot JSONB dicts to engine FinancialPeriod model."""
    shares = current_row.shares_outstanding or 0
    prior_shares = prior_row.shares_outstanding or 0 if prior_row else 0

    current_income = _build_income_statement(current_row.income_statement or {}, shares)
    current_balance = _build_balance_sheet(current_row.balance_sheet or {}, shares)
    current_cash_flow = _build_cash_flow_statement(current_row.cash_flow or {})

    prior_income: IncomeStatement | None = None
    prior_balance: BalanceSheet | None = None
    prior_cash_flow: CashFlowStatement | None = None

    if prior_row is not None:
        prior_income = _build_income_statement(prior_row.income_statement or {}, prior_shares)
        prior_balance = _build_balance_sheet(prior_row.balance_sheet or {}, prior_shares)
        prior_cash_flow = _build_cash_flow_statement(prior_row.cash_flow or {})

    return FinancialPeriod(
        period_end=current_row.period_end.isoformat(),
        filing_date=current_row.filing_date.isoformat(),
        current_income=current_income,
        prior_income=prior_income,
        current_balance=current_balance,
        prior_balance=prior_balance,
        current_cash_flow=current_cash_flow,
        prior_cash_flow=prior_cash_flow,
    )


def _build_income_statement(data: dict, shares_outstanding: int) -> IncomeStatement:
    """Map XBRL JSONB fields to engine IncomeStatement."""
    return IncomeStatement(
        revenue=Decimal(str(data.get("revenue", 0))),
        cost_of_revenue=Decimal(str(data.get("cost_of_revenue", 0))),
        gross_profit=Decimal(str(data.get("gross_profit", 0))),
        sga_expense=Decimal(str(data["sga_expense"]))
        if data.get("sga_expense") is not None
        else None,
        rd_expense=Decimal(str(data["rd_expense"])) if data.get("rd_expense") is not None else None,
        depreciation=Decimal(str(data["depreciation"]))
        if data.get("depreciation") is not None
        else None,
        ebit=Decimal(str(data.get("ebit", 0))),
        interest_expense=(
            Decimal(str(data["interest_expense"]))
            if data.get("interest_expense") is not None
            else None
        ),
        tax_provision=(
            Decimal(str(data["tax_provision"])) if data.get("tax_provision") is not None else None
        ),
        net_income=Decimal(str(data.get("net_income", 0))),
        shares_outstanding=shares_outstanding,
    )


def _build_balance_sheet(data: dict, shares_outstanding: int) -> BalanceSheet:
    """Map XBRL JSONB fields to engine BalanceSheet."""
    return BalanceSheet(
        total_assets=Decimal(str(data.get("total_assets", 0))),
        current_assets=Decimal(str(data.get("current_assets", 0))),
        cash_and_equivalents=(
            Decimal(str(data["cash_and_equivalents"]))
            if data.get("cash_and_equivalents") is not None
            else None
        ),
        receivables=(
            Decimal(str(data["receivables"])) if data.get("receivables") is not None else None
        ),
        total_liabilities=Decimal(str(data.get("total_liabilities", 0))),
        current_liabilities=Decimal(str(data.get("current_liabilities", 0))),
        long_term_debt=(
            Decimal(str(data["long_term_debt"])) if data.get("long_term_debt") is not None else None
        ),
        short_term_debt=Decimal(str(data.get("short_term_debt", 0))),
        total_equity=Decimal(str(data.get("total_equity", 0))),
        retained_earnings=(
            Decimal(str(data["retained_earnings"]))
            if data.get("retained_earnings") is not None
            else None
        ),
        pp_and_e=(Decimal(str(data["pp_and_e"])) if data.get("pp_and_e") is not None else None),
        shares_outstanding=shares_outstanding,
    )


def _build_cash_flow_statement(data: dict) -> CashFlowStatement:
    """Map XBRL JSONB fields to engine CashFlowStatement.

    Note: XBRL uses 'capex' which maps to engine's 'capital_expenditures'.
    """
    return CashFlowStatement(
        operating_cash_flow=Decimal(str(data.get("operating_cash_flow", 0))),
        capital_expenditures=Decimal(str(data.get("capex", 0))),
        dividends_paid=(
            Decimal(str(data["dividends_paid"])) if data.get("dividends_paid") is not None else None
        ),
        share_repurchases=(
            Decimal(str(data["share_repurchases"]))
            if data.get("share_repurchases") is not None
            else None
        ),
        share_issuance=None,
    )


def _build_profile(ticker: str, row: PITFinancialSnapshot, price: float) -> AssetProfile:
    """Build AssetProfile from filing data and current price."""
    shares = row.shares_outstanding or 0
    market_cap = Decimal(str(shares)) * Decimal(str(price))

    return AssetProfile(
        ticker=ticker,
        name=ticker,  # We don't have company name in PIT table
        sector=GICSSector.TECHNOLOGY,  # Default — will be refined later
        market_cap=market_cap,
        shares_outstanding=shares,
    )


# Aliases for batch-loaded subquery rows (same attribute interface)
_build_period_from_row = _build_period
_build_profile_from_row = _build_profile
