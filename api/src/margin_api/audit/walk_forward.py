"""Audit walk-forward wrapper: ScoredUniverseProvider that regenerates scores.

Per spec §10, the audit re-runs V4 scoring at each cohort date using current
engine code (NOT replaying precomputed `v4_scores`). This is the most
consequential replication choice — the audit measures the *current* engine,
not historical production behavior.

Implementation note: TickerV4Data construction at a historical cohort date is
fundamentally limited by what's reconstructable from PIT tables. Modifiers
that require non-PIT inputs (insider buys, short interest, analyst data,
risk-factor diffs, ML predictions) get neutral defaults at cohort dates
earlier than their data source's coverage. For Phase 1 MVP, only PIT
financials + PIT prices feed scoring; modifier inputs default to neutral.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession


class RegeneratingUniverseProvider:
    """Implements the engine ScoredUniverseProvider Protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._cache: dict[date, list[object]] = {}

    async def get_scores_async(self, as_of_date: date) -> list[object]:
        if as_of_date in self._cache:
            return self._cache[as_of_date]
        # MVP placeholder: until TickerV4Data construction is wired (Task 1.10),
        # return an empty list for synthetic-DB tests.
        scored: list[object] = []
        self._cache[as_of_date] = scored
        return scored

    def get_scores(self, as_of_date: date) -> list[object]:
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

    MVP scope: this returns an empty list when PIT data is insufficient
    (synthetic-DB tests). Full WalkForwardSimulator wiring lands in Phase 3
    against Railway PIT data.
    """
    provider = RegeneratingUniverseProvider(session=session)
    cohort_dates = _monthly_cohort_dates(start_date, end_date)
    for d in cohort_dates:
        await provider.get_scores_async(d)
    return []


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
