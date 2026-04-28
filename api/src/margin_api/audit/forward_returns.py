"""Part A: forward-return alpha measurement on legacy `scores` candidates.

Per spec §8.1, all returns use `pit_daily_prices.adj_close` (dividend-adjusted).

Trading-day alignment: scored_at and window endpoints may fall on weekends or
holidays where pit_daily_prices has no row. We snap to the nearest preceding
NYSE trading day (via pandas_market_calendars), then look up that exact date.
A 7-day lookback fallback handles the edge case where the calendar says a
day is a trading day but pit_daily_prices doesn't have a row (e.g., a recent
ingest gap). This is the realistic semantics — an investor checking on a
Saturday sees Friday's close — and it's calendar-aware (handles holidays
correctly, not just weekends).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.audit.schema import CandidatePartARow, DataStatus
from margin_api.db.models import Asset, PITDailyPrice, Score

_TRADING_DAY_LOOKBACK = 7


@lru_cache(maxsize=1)
def _nyse_calendar():  # type: ignore[no-untyped-def]
    """Lazy-load the NYSE calendar; importing pandas_market_calendars is slow."""
    import pandas_market_calendars as mcal

    return mcal.get_calendar("NYSE")


def _snap_to_trading_day(target: date) -> date:
    """Return `target` if it's an NYSE trading day, else the most recent prior one.

    Walks the calendar back up to 14 days; covers weekends + standard holidays.
    """
    calendar = _nyse_calendar()
    days = calendar.valid_days(start_date=target - timedelta(days=14), end_date=target)
    if len(days) == 0:
        return target
    return days[-1].date()


def _nearest_preceding_price(
    prices: dict[date, float], target: date, lookback: int = _TRADING_DAY_LOOKBACK
) -> float | None:
    """Return price on the trading day at/before `target`, with PIT-gap fallback."""
    snapped = _snap_to_trading_day(target)
    if snapped in prices:
        return prices[snapped]
    # Trading day per calendar, but no PIT row — fall back to walk-back.
    for delta in range(lookback + 1):
        d = snapped - timedelta(days=delta)
        if d in prices:
            return prices[d]
    return None


def compute_total_return(
    prices: dict[date, float],
    start: date,
    end: date,
) -> float | None:
    """Compute total return between two dates with trading-day snap-back.

    Args:
        prices: Dictionary mapping dates to adjusted closing prices.
        start: Start date for return calculation.
        end: End date for return calculation.

    Returns:
        Total return as a float (e.g., 0.10 for 10% return), or None if:
        - Either endpoint has no price within 7 calendar days preceding it
        - Start price is zero (division by zero protection)
    """
    start_price = _nearest_preceding_price(prices, start)
    end_price = _nearest_preceding_price(prices, end)
    if start_price is None or end_price is None:
        return None
    if start_price == 0:
        return None
    return (end_price / start_price) - 1.0


async def _load_prices(
    session: AsyncSession, tickers: Iterable[str]
) -> dict[str, dict[date, float]]:
    """Load all adj_close prices for given tickers from database.

    Args:
        session: Async SQLAlchemy session.
        tickers: List of ticker symbols to load.

    Returns:
        Dictionary mapping ticker to dict[date -> adj_close].
    """
    stmt = select(PITDailyPrice.ticker, PITDailyPrice.date, PITDailyPrice.adj_close).where(
        PITDailyPrice.ticker.in_(list(tickers))
    )
    result: dict[str, dict[date, float]] = {}
    for ticker, day, adj_close in (await session.execute(stmt)).all():
        result.setdefault(ticker, {})[day] = float(adj_close)
    return result


async def _load_candidates(session: AsyncSession) -> list[tuple[Score, str]]:
    """Load all scored candidates (Score + ticker).

    Filters to conviction_level in ["exceptional", "high", "medium"].

    Returns:
        List of (Score, ticker) tuples.
    """
    stmt = (
        select(Score, Asset.ticker)
        .join(Asset, Asset.id == Score.asset_id)
        .where(Score.conviction_level.in_(["exceptional", "high", "medium"]))
    )
    return [(s, t) for s, t in (await session.execute(stmt)).all()]


def _is_window_closed(scored_at: date, window_days: int, report_date: date) -> bool:
    """Check if a forward-return window has fully elapsed.

    Window is closed if end_date <= report_date.

    Args:
        scored_at: Score date.
        window_days: Window length in days.
        report_date: Reference report date.

    Returns:
        True if scored_at + window_days <= report_date.
    """
    return scored_at + timedelta(days=window_days) <= report_date


async def compute_part_a(
    session: AsyncSession,
    report_date: date,
    windows: tuple[int, ...] = (30, 60, 63),
) -> list[CandidatePartARow]:
    """Compute Part A forward-return rows for all scored candidates.

    Loads all candidates with conviction_level in (exceptional, high, medium),
    then emits one row per candidate with returns computed for all windows
    whose endpoints exist in PIT price data.

    Data status logic:
    - OK: all expected windows have data
    - PARTIAL: some windows have data, some missing
    - DATA_UNAVAILABLE: no windows have data (candidate prices entirely missing)

    Args:
        session: Async SQLAlchemy session.
        report_date: Report cutoff date.
        windows: Window lengths in days. Defaults to (30, 60, 63).

    Returns:
        List of CandidatePartARow, one per candidate.
    """
    candidates = await _load_candidates(session)
    tickers = {ticker for _, ticker in candidates} | {"SPY"}
    prices = await _load_prices(session, tickers)
    spy_prices = prices.get("SPY", {})

    rows: list[CandidatePartARow] = []
    for score, ticker in candidates:
        scored_at_date = score.scored_at.date()
        candidate_prices = prices.get(ticker, {})

        returns: dict[str, float | None] = {}
        for w in windows:
            end = scored_at_date + timedelta(days=w)
            if not _is_window_closed(scored_at_date, w, report_date):
                returns[f"candidate_return_{w}d"] = None
                returns[f"spy_return_{w}d"] = None
                returns[f"alpha_{w}d"] = None
                continue
            cand_ret = compute_total_return(candidate_prices, scored_at_date, end)
            spy_ret = compute_total_return(spy_prices, scored_at_date, end)
            returns[f"candidate_return_{w}d"] = cand_ret
            returns[f"spy_return_{w}d"] = spy_ret
            returns[f"alpha_{w}d"] = (
                None if cand_ret is None or spy_ret is None else cand_ret - spy_ret
            )

        # Determine data status
        cand_present = sum(1 for w in windows if returns[f"candidate_return_{w}d"] is not None)
        cand_expected = sum(1 for w in windows if _is_window_closed(scored_at_date, w, report_date))
        if cand_expected == 0:
            status = DataStatus.OK
        elif cand_present == 0:
            status = DataStatus.DATA_UNAVAILABLE
        elif cand_present < cand_expected:
            status = DataStatus.PARTIAL
        else:
            status = DataStatus.OK

        row = CandidatePartARow(
            ticker=ticker,
            scored_at=scored_at_date,
            conviction_level=score.conviction_level,
            composite_percentile=float(score.composite_percentile),
            opportunity_type=score.opportunity_type,
            asymmetry_ratio=score.asymmetry_ratio,
            data_status=status,
            **{
                k: v
                for k, v in returns.items()
                if k.startswith(("candidate_return_", "spy_return_", "alpha_"))
            },
            **{
                f"hit_{w}d": (
                    (returns[f"alpha_{w}d"] > 0) if returns[f"alpha_{w}d"] is not None else None
                )
                for w in windows
            },
        )
        rows.append(row)
    return rows
