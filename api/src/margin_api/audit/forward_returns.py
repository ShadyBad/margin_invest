"""Part A: forward-return alpha measurement on legacy `scores` candidates.

Per spec §8.1, all returns use `pit_daily_prices.adj_close` (dividend-adjusted).
Missing endpoints are NEVER substituted with neighboring days.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.audit.schema import CandidatePartARow, DataStatus
from margin_api.db.models import Asset, PITDailyPrice, Score


def compute_total_return(
    prices: dict[date, float],
    start: date,
    end: date,
) -> float | None:
    """Compute total return between two dates.

    Args:
        prices: Dictionary mapping dates to adjusted closing prices.
        start: Start date for return calculation.
        end: End date for return calculation.

    Returns:
        Total return as a float (e.g., 0.10 for 10% return), or None if:
        - Either endpoint price is missing
        - Start price is zero (division by zero protection)
    """
    start_price = prices.get(start)
    end_price = prices.get(end)
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
    stmt = select(
        PITDailyPrice.ticker, PITDailyPrice.date, PITDailyPrice.adj_close
    ).where(PITDailyPrice.ticker.in_(list(tickers)))
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
        cand_present = sum(
            1 for w in windows if returns[f"candidate_return_{w}d"] is not None
        )
        cand_expected = sum(
            1 for w in windows if _is_window_closed(scored_at_date, w, report_date)
        )
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
                    (returns[f"alpha_{w}d"] > 0)
                    if returns[f"alpha_{w}d"] is not None
                    else None
                )
                for w in windows
            },
        )
        rows.append(row)
    return rows
