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
