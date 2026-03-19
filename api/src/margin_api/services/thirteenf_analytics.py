"""13F analytics service — quarter resolution, new positions, and crowded trades."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import HTTPException
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import InstitutionalHolding, Manager, SecurityMaster

logger = logging.getLogger(__name__)

# Quarter-end dates by quarter number (1-indexed)
_QUARTER_END_MONTH_DAY: dict[int, tuple[int, int]] = {
    1: (3, 31),
    2: (6, 30),
    3: (9, 30),
    4: (12, 31),
}


def _quarter_str_to_date(quarter_str: str) -> date:
    """Parse 'YYYY-QN' into the quarter-end date."""
    try:
        year_part, q_part = quarter_str.split("-Q")
        year = int(year_part)
        q = int(q_part)
    except (ValueError, AttributeError) as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid quarter format: {quarter_str!r}"
        ) from e
    if q not in _QUARTER_END_MONTH_DAY:
        raise HTTPException(status_code=400, detail=f"Quarter must be 1-4, got {q}")
    month, day = _QUARTER_END_MONTH_DAY[q]
    return date(year, month, day)


def _preceding_quarter_date(d: date) -> date:
    """Return the last day of the quarter immediately before the one containing d."""
    # Map a quarter-end date to the previous quarter's end date
    if d.month == 3:
        return date(d.year - 1, 12, 31)
    if d.month == 6:
        return date(d.year, 3, 31)
    if d.month == 9:
        return date(d.year, 6, 30)
    # December
    return date(d.year, 9, 30)


async def get_available_quarters(session: AsyncSession) -> list[date]:
    """Return distinct period_of_report values from institutional_holdings, most recent first."""
    stmt = select(distinct(InstitutionalHolding.period_of_report)).order_by(
        InstitutionalHolding.period_of_report.desc()
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def resolve_quarter(
    session: AsyncSession,
    quarter_str: str | None,
) -> tuple[date, date]:
    """Resolve a quarter string (or None) to (current_quarter, prev_quarter).

    - None: auto-detect from the 2 most recent available quarters.
    - "YYYY-QN": parse to quarter-end, then look up the preceding quarter in the DB.

    Raises HTTPException(404) if fewer than 2 quarters are available or if the
    requested quarter's predecessor is not present in the DB.
    """
    available = await get_available_quarters(session)

    if quarter_str is None:
        if len(available) < 2:
            raise HTTPException(
                status_code=404,
                detail="Fewer than 2 quarters of data available; cannot compute new positions.",
            )
        return available[0], available[1]

    # Explicit quarter requested
    target = _quarter_str_to_date(quarter_str)
    if target not in available:
        raise HTTPException(
            status_code=404,
            detail=f"No holdings data found for quarter {quarter_str} ({target}).",
        )
    preceding = _preceding_quarter_date(target)
    if preceding not in available:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Preceding quarter {preceding} not in DB — cannot compute new positions "
                f"for {quarter_str}."
            ),
        )
    return target, preceding


async def compute_new_positions(
    session: AsyncSession,
    current_q: date,
    prev_q: date,
) -> list[dict]:
    """Compute new positions: securities held in current_q but not prev_q, per manager.

    Returns a list of dicts (up to 50), sorted by total_new_funds descending:
      - ticker: str
      - managers: list[str]  (up to 10 names)
      - total_new_funds: int
      - curated_new_funds: int  (always 0 for now)
      - total_value_millions: float
    """
    # Query (manager_id, security_master_id) for current quarter
    curr_stmt = select(
        InstitutionalHolding.manager_id,
        InstitutionalHolding.security_master_id,
        InstitutionalHolding.value_thousands,
    ).where(InstitutionalHolding.period_of_report == current_q)
    curr_result = await session.execute(curr_stmt)
    curr_rows = curr_result.all()

    if not curr_rows:
        return []

    # Query (manager_id, security_master_id) for previous quarter
    prev_stmt = select(
        InstitutionalHolding.manager_id,
        InstitutionalHolding.security_master_id,
    ).where(InstitutionalHolding.period_of_report == prev_q)
    prev_result = await session.execute(prev_stmt)
    prev_set: set[tuple[int, int]] = {
        (row.manager_id, row.security_master_id) for row in prev_result.all()
    }

    # Find new (manager_id, security_master_id) pairs
    # Accumulate by security_master_id: list of (manager_id, value_thousands)
    new_by_sec: dict[int, list[tuple[int, int]]] = {}
    for row in curr_rows:
        key = (row.manager_id, row.security_master_id)
        if key not in prev_set:
            new_by_sec.setdefault(row.security_master_id, []).append(
                (row.manager_id, row.value_thousands)
            )

    if not new_by_sec:
        return []

    # Resolve security_master_id -> ticker
    sec_ids = list(new_by_sec.keys())
    sec_stmt = select(SecurityMaster.id, SecurityMaster.ticker).where(
        SecurityMaster.id.in_(sec_ids)
    )
    sec_result = await session.execute(sec_stmt)
    sec_map: dict[int, str | None] = {row.id: row.ticker for row in sec_result.all()}

    # Resolve manager_id -> name
    manager_ids: set[int] = set()
    for entries in new_by_sec.values():
        for mgr_id, _ in entries:
            manager_ids.add(mgr_id)
    mgr_stmt = select(Manager.id, Manager.name).where(Manager.id.in_(manager_ids))
    mgr_result = await session.execute(mgr_stmt)
    mgr_map: dict[int, str] = {row.id: row.name for row in mgr_result.all()}

    # Build result list
    results: list[dict] = []
    for sec_id, entries in new_by_sec.items():
        ticker = sec_map.get(sec_id)
        if ticker is None:
            continue  # skip securities with no ticker

        mgr_names = [mgr_map[mgr_id] for mgr_id, _ in entries if mgr_id in mgr_map]
        total_value_thousands = sum(val for _, val in entries)

        results.append(
            {
                "ticker": ticker,
                "managers": mgr_names[:10],
                "total_new_funds": len(entries),
                "curated_new_funds": 0,
                "total_value_millions": total_value_thousands / 1000.0,
            }
        )

    # Sort by total_new_funds descending, limit 50
    results.sort(key=lambda x: x["total_new_funds"], reverse=True)
    return results[:50]


async def compute_crowded_trades(
    session: AsyncSession,
    quarter: date,
) -> tuple[list[dict], list[dict]]:
    """Compute most-held and crowded-trades for the given quarter.

    Returns (most_held, crowded_trades) where each is a list of up to 20 dicts.

    most_held dicts: {ticker, holder_count, curated_count}
    crowded_trades dicts: {ticker, holder_count, concentration_pct, total_value_millions}
    """
    # Count distinct managers per security + sum value
    stmt = (
        select(
            InstitutionalHolding.security_master_id,
            func.count(distinct(InstitutionalHolding.manager_id)).label("holder_count"),
            func.sum(InstitutionalHolding.value_thousands).label("total_value_thousands"),
        )
        .where(InstitutionalHolding.period_of_report == quarter)
        .group_by(InstitutionalHolding.security_master_id)
        .order_by(func.count(distinct(InstitutionalHolding.manager_id)).desc())
    )
    rows = (await session.execute(stmt)).all()

    if not rows:
        return [], []

    # Total distinct managers for the quarter
    total_mgr_stmt = select(func.count(distinct(InstitutionalHolding.manager_id))).where(
        InstitutionalHolding.period_of_report == quarter
    )
    total_managers: int = (await session.execute(total_mgr_stmt)).scalar_one()

    # Resolve security_master_id -> ticker
    sec_ids = [row.security_master_id for row in rows]
    sec_stmt = select(SecurityMaster.id, SecurityMaster.ticker).where(
        SecurityMaster.id.in_(sec_ids)
    )
    sec_map: dict[int, str | None] = {
        row.id: row.ticker for row in (await session.execute(sec_stmt)).all()
    }

    most_held: list[dict] = []
    crowded_trades: list[dict] = []

    for row in rows:
        ticker = sec_map.get(row.security_master_id)
        if ticker is None:
            continue

        holder_count: int = row.holder_count
        total_val_thousands: int = row.total_value_thousands or 0
        concentration = holder_count / total_managers if total_managers > 0 else 0.0

        if len(most_held) < 20:
            most_held.append(
                {
                    "ticker": ticker,
                    "holder_count": holder_count,
                    "curated_count": 0,
                }
            )
        if len(crowded_trades) < 20:
            crowded_trades.append(
                {
                    "ticker": ticker,
                    "holder_count": holder_count,
                    "concentration_pct": concentration,
                    "total_value_millions": total_val_thousands / 1000.0,
                }
            )

        if len(most_held) >= 20 and len(crowded_trades) >= 20:
            break

    return most_held, crowded_trades
