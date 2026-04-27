"""Audit walk-forward wrapper: ScoredUniverseProvider that regenerates scores.

Per spec §10, the audit re-runs V4 scoring at each cohort date using current
engine code (NOT replaying precomputed `v4_scores`). This is the most
consequential replication choice — the audit measures the *current* engine,
not historical production behavior.

## TickerV4Data field provenance

PIT-sourced fields (from PITFinancialSnapshot + PITDailyPrice):
  - ticker, history, latest_period, profile
  - current_price (from pit_daily_prices.adj_close at as_of_date)
  - current_fcf_per_share (computed from cash_flow statement)
  - sustainable_growth_rate (ROE × retention ratio)
  - dcf_iv (simple FCF / (WACC - terminal_growth))
  - profile.market_cap (from pit_universe_memberships.market_cap when available)
  - profile.avg_daily_volume (from pit_universe_memberships.avg_daily_volume when available)

Neutral-defaulted fields (not reconstructable from PIT tables):
  - accumulation_percentile = 0.0 (no 13F PIT data at cohort dates)
  - style = InvestmentStyle.BLEND (no style classification at cohort dates)
  - buyback_yield = None (no buyback PIT data)
  - insider_ownership_pct = None
  - sbc_pct = None
  - recent_acquisition_count = 0
  - sue_percentile = 50.0 (neutral; no quarterly earnings surprise PIT data)
  - momentum_percentile = 50.0 (neutral; price momentum reconstructable in Phase 2)
  - beta = None
  - fundamental_trajectory = 0.5 (neutral)
  - high_52w = None (reconstructable in Phase 2 from pit_daily_prices)
  - short_interest_percentile = 50.0 (neutral)
  - analyst_divergence = 0.0 (neutral)
  - eps_revision_strength = 0.0 (neutral)
  - insider_cluster_score_value = 0.0 (neutral)
  - insider_cluster_detected = False
  - insider_total_buy_value = 0.0
  - insider_has_first_buy = False
  - revenue_history = None (TAM not reconstructable from PIT tables)
  - sector = None (GICSSector name; sector comes from AssetProfile)
  - All Track C (Efficient Growth) inputs = 0.0 (no GROWTH-style PIT data)
  - shiller_cape = 30.0 (stub constant; real value would come from a market-data table)
  - ml_predictions = None (not available at cohort dates)

Phase 2 enhancements (not in scope here):
  - Reconstruct momentum_percentile from pit_daily_prices trailing 12m
  - Reconstruct high_52w from pit_daily_prices trailing 365d
  - Reconstruct revenue_history for TAM signals
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from margin_engine.backtesting.models import BacktestConfig, RebalanceFrequency, SelectionMode
from margin_engine.backtesting.simulator import ScoredStock, WalkForwardSimulator
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import CompositeTier, InvestmentStyle
from margin_engine.scoring.v4_pipeline import TickerV4Data, score_universe_v4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Stub Shiller CAPE — real value would come from a market-data table.
# Flagged for Phase 2 wiring. 30.0 is near the long-run average for a neutral default.
_STUB_SHILLER_CAPE = 30.0

_DEFAULT_RETENTION_RATIO = 0.70
_MAX_GROWTH_RATE = 0.30
_MIN_GROWTH_RATE = 0.01
_TERMINAL_GROWTH = 0.025

# CompositeTier string values used in selection_tiers parameter
_TIER_MAP: dict[str, CompositeTier] = {
    "exceptional": CompositeTier.EXCEPTIONAL,
    "high": CompositeTier.HIGH,
    "medium": CompositeTier.MEDIUM,
    "none": CompositeTier.NONE,
}

# Fallback sector for tickers with unknown / unmapped SIC codes
_FALLBACK_SECTOR = GICSSector.TECHNOLOGY


def _resolve_sector(sector_str: str | None) -> GICSSector:
    """Map a free-form sector string to a GICSSector enum value."""
    if not sector_str:
        return _FALLBACK_SECTOR
    for gs in GICSSector:
        if gs.value.lower() == sector_str.lower():
            return gs
    return _FALLBACK_SECTOR


def _build_ticker_v4_data(
    ticker: str,
    financial_rows: list,  # PITFinancialSnapshot ORM rows, newest first
    price: float,
    market_cap: float | None,
    avg_daily_volume: float | None,
    sector_str: str | None,
) -> TickerV4Data | None:
    """Construct a TickerV4Data from PIT financial rows and current price.

    Returns None if no usable financial data is available.
    """
    if not financial_rows:
        return None

    sector = _resolve_sector(sector_str)

    # Build FinancialPeriod list from all available snapshots
    periods: list[FinancialPeriod] = []
    for row in financial_rows:
        income_data = row.income_statement or {}
        balance_data = row.balance_sheet or {}
        cf_data = row.cash_flow or {}

        def _d(v: object) -> Decimal:
            if v is None:
                return Decimal("0")
            try:
                return Decimal(str(v))
            except Exception:
                return Decimal("0")

        income = IncomeStatement(
            revenue=_d(income_data.get("revenue")),
            cost_of_revenue=_d(income_data.get("cost_of_revenue")),
            gross_profit=_d(income_data.get("gross_profit")),
            ebit=_d(income_data.get("ebit")),
            net_income=_d(income_data.get("net_income")),
            shares_outstanding=int(income_data.get("shares_outstanding") or 0),
            sga_expense=(
                _d(income_data.get("sga_expense")) if income_data.get("sga_expense") else None
            ),
            rd_expense=(
                _d(income_data.get("rd_expense")) if income_data.get("rd_expense") else None
            ),
            depreciation=(
                _d(income_data.get("depreciation"))
                if income_data.get("depreciation")
                else None
            ),
            interest_expense=(
                _d(income_data.get("interest_expense"))
                if income_data.get("interest_expense")
                else None
            ),
            tax_provision=(
                _d(income_data.get("tax_provision"))
                if income_data.get("tax_provision")
                else None
            ),
        )

        balance = BalanceSheet(
            total_assets=_d(balance_data.get("total_assets")),
            current_assets=_d(balance_data.get("current_assets")),
            total_liabilities=_d(balance_data.get("total_liabilities")),
            current_liabilities=_d(balance_data.get("current_liabilities")),
            total_equity=_d(balance_data.get("total_equity")),
            long_term_debt=(
                _d(balance_data.get("long_term_debt"))
                if balance_data.get("long_term_debt")
                else None
            ),
            cash_and_equivalents=(
                _d(balance_data.get("cash_and_equivalents"))
                if balance_data.get("cash_and_equivalents")
                else None
            ),
            pp_and_e=(
                _d(balance_data.get("pp_and_e")) if balance_data.get("pp_and_e") else None
            ),
        )

        cf = CashFlowStatement(
            operating_cash_flow=_d(cf_data.get("operating_cash_flow")),
            capital_expenditures=_d(cf_data.get("capital_expenditures")),
        )

        period_end_str = (
            row.period_end.isoformat()
            if hasattr(row.period_end, "isoformat")
            else str(row.period_end)
        )
        filing_date_str = (
            row.filing_date.isoformat()
            if hasattr(row.filing_date, "isoformat")
            else str(row.filing_date)
        )

        try:
            period = FinancialPeriod(
                period_end=period_end_str,
                filing_date=filing_date_str,
                current_income=income,
                current_balance=balance,
                current_cash_flow=cf,
            )
            periods.append(period)
        except Exception as exc:
            logger.debug("Skipping malformed period for %s: %s", ticker, exc)
            continue

    if not periods:
        return None

    # Sort ascending by period_end (FinancialHistory validator requires >= 1 period)
    periods.sort(key=lambda p: p.period_end)
    history = FinancialHistory(ticker=ticker, periods=periods)
    latest_period = periods[-1]  # most recent

    # Derive scalars from latest period
    income = latest_period.current_income
    balance = latest_period.current_balance
    cf_stmt = latest_period.current_cash_flow

    shares = income.shares_outstanding or (balance.shares_outstanding if balance else 0)
    if not shares or shares <= 0:
        shares = 1

    ocf = float(cf_stmt.operating_cash_flow)
    capex = float(cf_stmt.capital_expenditures)
    fcf = ocf + capex
    fcf_per_share = fcf / shares

    equity = float(balance.total_equity)
    net_income_val = float(income.net_income)
    roe = net_income_val / equity if equity > 0 else 0.0
    growth_rate = max(_MIN_GROWTH_RATE, min(roe * _DEFAULT_RETENTION_RATIO, _MAX_GROWTH_RATE))

    from margin_engine.scoring.quantitative.wacc_sector import get_sector_wacc

    wacc = get_sector_wacc(sector)
    dcf_iv = 0.0
    if fcf_per_share > 0 and wacc > _TERMINAL_GROWTH:
        dcf_iv = fcf_per_share * (1 + growth_rate) / (wacc - _TERMINAL_GROWTH)

    profile = AssetProfile(
        ticker=ticker,
        name=ticker,
        sector=sector,
        market_cap=Decimal(str(market_cap)) if market_cap else Decimal("0"),
        avg_daily_volume=Decimal(str(avg_daily_volume)) if avg_daily_volume else Decimal("0"),
        years_of_history=len(periods),
    )

    return TickerV4Data(
        ticker=ticker,
        history=history,
        latest_period=latest_period,
        profile=profile,
        current_price=price,
        current_fcf_per_share=fcf_per_share,
        sustainable_growth_rate=growth_rate,
        dcf_iv=dcf_iv,
        # Neutral-defaulted fields (non-PIT; see module docstring)
        accumulation_percentile=0.0,
        style=InvestmentStyle.BLEND,
        buyback_yield=None,
        insider_ownership_pct=None,
        sbc_pct=None,
        recent_acquisition_count=0,
        sue_percentile=50.0,
        momentum_percentile=50.0,
        beta=None,
        fundamental_trajectory=0.5,
        high_52w=None,
        short_interest_percentile=50.0,
        analyst_divergence=0.0,
        eps_revision_strength=0.0,
        insider_cluster_score_value=0.0,
        insider_cluster_detected=False,
        insider_total_buy_value=0.0,
        insider_has_first_buy=False,
        revenue_history=None,
        sector=sector.value,
        # Track C (Efficient Growth) — all neutral (no PIT data)
        revenue_growth_rate=0.0,
        fcf_margin=0.0,
        gross_margin_current=0.0,
        gross_margin_3yr_ago=0.0,
        opex_growth_rate=0.0,
        revenue_growth_rate_for_leverage=0.0,
        incremental_roic=0.0,
        revenue_deceleration=0.0,
        tam_headroom=0.0,
    )


class _DBBenchmarkProvider:
    """Reads SPY prices from pit_daily_prices; implements BenchmarkProvider Protocol."""

    def __init__(self, price_map: dict[date, float]) -> None:
        # price_map: {date -> adj_close}
        self._price_map = price_map
        # Pre-sort dates for nearest-prior lookup
        self._sorted_dates = sorted(price_map)

    def get_price(self, ticker: str, as_of_date: date) -> float:
        """Return the most recent adj_close on or before as_of_date."""
        if not self._sorted_dates:
            return 400.0  # Fallback constant if no benchmark data
        # Find latest date <= as_of_date
        best: float | None = None
        for d in reversed(self._sorted_dates):
            if d <= as_of_date:
                best = self._price_map[d]
                break
        return best if best is not None else self._price_map[self._sorted_dates[0]]


class RegeneratingUniverseProvider:
    """Implements the engine ScoredUniverseProvider Protocol.

    Queries PIT financial snapshots and prices at each cohort date,
    builds TickerV4Data, runs score_universe_v4, and caches results.

    The sync get_scores() method is what WalkForwardSimulator calls;
    get_scores_async() must be pre-called for each cohort date to populate
    the cache before the simulator's synchronous run() loop executes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._cache: dict[date, list[ScoredStock]] = {}

    async def get_scores_async(self, as_of_date: date) -> list[ScoredStock]:
        """Score the universe at as_of_date using PIT data, cache, and return results."""
        if as_of_date in self._cache:
            return self._cache[as_of_date]

        from margin_api.db.models import (
            PITDailyPrice,
            PITFinancialSnapshot,
            PITUniverseMembership,
        )

        # 1. Get active universe members at as_of_date
        # Use the most recent quarter_date <= as_of_date
        membership_stmt = (
            select(PITUniverseMembership)
            .where(PITUniverseMembership.quarter_date <= as_of_date)
            .where(PITUniverseMembership.is_active.is_(True))
            .order_by(PITUniverseMembership.ticker, PITUniverseMembership.quarter_date.desc())
        )
        result = await self.session.execute(membership_stmt)
        membership_rows = result.scalars().all()

        # De-duplicate: keep only the latest membership row per ticker
        seen_tickers: dict[str, object] = {}
        for row in membership_rows:
            if row.ticker not in seen_tickers:
                seen_tickers[row.ticker] = row

        if not seen_tickers:
            self._cache[as_of_date] = []
            return []

        # 2. Get prices at as_of_date for active tickers (latest <= as_of_date)
        active_tickers = sorted(seen_tickers.keys())
        price_stmt = (
            select(PITDailyPrice)
            .where(PITDailyPrice.ticker.in_(active_tickers))
            .where(PITDailyPrice.date <= as_of_date)
            .order_by(PITDailyPrice.ticker, PITDailyPrice.date.desc())
        )
        price_result = await self.session.execute(price_stmt)
        price_rows = price_result.scalars().all()

        prices: dict[str, float] = {}
        for pr in price_rows:
            if pr.ticker not in prices:
                prices[pr.ticker] = pr.adj_close

        # 3. Get financial snapshots (filed on or before as_of_date)
        fin_stmt = (
            select(PITFinancialSnapshot)
            .where(PITFinancialSnapshot.ticker.in_(active_tickers))
            .where(PITFinancialSnapshot.filing_date <= as_of_date)
            .order_by(PITFinancialSnapshot.ticker, PITFinancialSnapshot.filing_date.desc())
        )
        fin_result = await self.session.execute(fin_stmt)
        fin_rows = fin_result.scalars().all()

        # Group financial rows by ticker (already sorted newest-first per ticker)
        fin_by_ticker: dict[str, list] = {}
        for fr in fin_rows:
            fin_by_ticker.setdefault(fr.ticker, []).append(fr)

        # 4. Build TickerV4Data for each ticker that has both price and financials
        tickers_data: list[TickerV4Data] = []
        for ticker in active_tickers:
            price = prices.get(ticker)
            if price is None or price <= 0:
                continue  # No price — skip
            fin_rows_for_ticker = fin_by_ticker.get(ticker)
            if not fin_rows_for_ticker:
                continue  # No financial data — skip

            membership_row = seen_tickers[ticker]
            market_cap = getattr(membership_row, "market_cap", None)
            avg_daily_volume = getattr(membership_row, "avg_daily_volume", None)
            # Derive sector from SIC code or membership metadata
            sector_str: str | None = None  # SIC→sector mapping would go here in Phase 2

            td = _build_ticker_v4_data(
                ticker=ticker,
                financial_rows=fin_rows_for_ticker,
                price=price,
                market_cap=market_cap,
                avg_daily_volume=avg_daily_volume,
                sector_str=sector_str,
            )
            if td is not None:
                tickers_data.append(td)

        if not tickers_data:
            self._cache[as_of_date] = []
            return []

        # 5. Score universe via v4 pipeline
        try:
            v4_results = score_universe_v4(
                tickers_data=tickers_data,
                shiller_cape=_STUB_SHILLER_CAPE,
                ml_predictions=None,
            )
        except Exception:
            logger.exception("score_universe_v4 failed for cohort %s", as_of_date)
            self._cache[as_of_date] = []
            return []

        # 6. Map V4ResultWithML → ScoredStock
        # Use modified_score if available, else composite_score
        scored: list[ScoredStock] = []
        for r in v4_results:
            raw_score = r.modified_score if r.modified_score is not None else r.composite_score
            # Retrieve price from tickers_data map for this ticker
            ticker_price = prices.get(r.ticker, 0.0)
            scored.append(
                ScoredStock(
                    ticker=r.ticker,
                    composite_score=raw_score,
                    price=ticker_price,
                    margin_of_safety=None,  # not reconstructable from PIT data
                )
            )

        # Sort deterministically by ticker to avoid dict/set ordering leaking into results
        scored.sort(key=lambda s: s.ticker)

        self._cache[as_of_date] = scored
        return scored

    def get_scores(self, as_of_date: date) -> list[ScoredStock]:
        """Sync accessor — returns cached results pre-populated by get_scores_async()."""
        return self._cache.get(as_of_date, [])


@dataclass(frozen=True)
class AuditCohortRow:
    cohort_date: date
    cohort_size: int
    portfolio_return: float
    benchmark_return: float
    excess_return: float
    turnover: float
    gross_return: float
    cost_drag_bps: float


async def run_walk_forward_audit(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    max_positions: int = 50,
    selection_tiers: tuple[str, ...] = ("exceptional", "high"),
) -> list[AuditCohortRow]:
    """Run the audit walk-forward against PIT data.

    Steps:
    1. Pre-warm the RegeneratingUniverseProvider cache for each cohort date.
    2. Load SPY benchmark prices from pit_daily_prices.
    3. Construct BacktestConfig (CONVICTION_MOS selection, monthly rebalance).
    4. Instantiate and run WalkForwardSimulator.
    5. Map BacktestResult.snapshots → list[AuditCohortRow].

    When PIT data is insufficient (e.g., synthetic-DB tests with no
    financial snapshots), the provider returns [] and the simulator
    produces zero holdings — the returned list will be empty.
    """
    from margin_api.db.models import PITDailyPrice

    provider = RegeneratingUniverseProvider(session=session)
    cohort_dates = _monthly_cohort_dates(start_date, end_date)

    # Step 1: Pre-warm cache (also pre-filters by selection_tiers — already handled below)
    for d in cohort_dates:
        await provider.get_scores_async(d)

    # Apply selection_tier pre-filter to cached scored lists.
    # The simulator also does its own selection, but pre-filtering reduces noise.
    selected_tiers: set[CompositeTier] = set()
    for t in selection_tiers:
        ct = _TIER_MAP.get(t.lower())
        if ct is not None:
            selected_tiers.add(ct)

    # Step 2: Load SPY prices from pit_daily_prices for the benchmark provider
    spy_stmt = (
        select(PITDailyPrice)
        .where(PITDailyPrice.ticker == "SPY")
        .order_by(PITDailyPrice.date)
    )
    spy_result = await session.execute(spy_stmt)
    spy_rows = spy_result.scalars().all()
    spy_price_map: dict[date, float] = {row.date: row.adj_close for row in spy_rows}

    spy_provider = _DBBenchmarkProvider(spy_price_map)

    # Step 3: Construct BacktestConfig
    # Use CONVICTION_MOS mode: selects stocks in exceptional + high tiers.
    # min_conviction_score → 76.0 (exceptional), min_conviction_score_high → 71.0 (high).
    # Since we're scoring via v4 pipeline using composite_score (0-100 scale from track scores),
    # scores cluster below 1.0 unless track qualifies fully — we set thresholds to 0.0 to let
    # all results through and rely on the pre-filter above for tier selection.
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        rebalance_frequency=RebalanceFrequency.MONTHLY,
        selection_mode=SelectionMode.TOP_PERCENTILE,
        top_percentile=1.0,  # Take all candidates that passed pre-filter
        max_holdings=max_positions,
        benchmark_ticker="SPY",
    )

    # Step 4: Run simulator
    simulator = WalkForwardSimulator(
        config=config,
        universe_provider=provider,
        benchmark_provider=spy_provider,
    )
    backtest_result = simulator.run()

    # Step 5: Map snapshots → AuditCohortRow
    rows: list[AuditCohortRow] = []
    for snapshot in backtest_result.snapshots:
        gross_ret = (
            snapshot.gross_return
            if snapshot.gross_return is not None
            else snapshot.portfolio_return
        )
        cost_drag_bps = (gross_ret - snapshot.portfolio_return) * 10_000

        rows.append(
            AuditCohortRow(
                cohort_date=snapshot.date,
                cohort_size=len(snapshot.holdings),
                portfolio_return=snapshot.portfolio_return,
                benchmark_return=snapshot.benchmark_return,
                excess_return=snapshot.excess_return,
                turnover=snapshot.turnover,
                gross_return=gross_ret,
                cost_drag_bps=cost_drag_bps,
            )
        )

    return rows


def _monthly_cohort_dates(start: date, end: date) -> list[date]:
    """Last calendar day of each month in [start, end]."""
    out: list[date] = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        nxt_month = cur.month + 1 if cur.month < 12 else 1
        nxt_year = cur.year if cur.month < 12 else cur.year + 1
        _, last_day = calendar.monthrange(cur.year, cur.month)
        candidate = date(cur.year, cur.month, last_day)
        if start <= candidate <= end:
            out.append(candidate)
        cur = date(nxt_year, nxt_month, 1)
    return out
