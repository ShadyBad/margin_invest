"""SIC code to GICS sector mapping."""

from __future__ import annotations

from margin_engine.models.financial import GICSSector
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import SICSectorMap

# Map GICS sector string values to enum members
_SECTOR_LOOKUP: dict[str, GICSSector] = {s.value: s for s in GICSSector}


class SICMapper:
    """In-memory cache of SIC->GICS mappings loaded from the database."""

    def __init__(self, mapping: dict[int, GICSSector]) -> None:
        self._mapping = mapping

    @classmethod
    async def load(cls, session: AsyncSession) -> SICMapper:
        """Load all SIC->GICS mappings from sic_sector_map table."""
        result = await session.execute(select(SICSectorMap))
        rows = result.scalars().all()

        mapping: dict[int, GICSSector] = {}
        for row in rows:
            sector = _SECTOR_LOOKUP.get(row.gics_sector)
            if sector is not None:
                mapping[row.sic_code] = sector

        return cls(mapping)

    def to_gics(self, sic_code: int | None) -> GICSSector:
        """Map a SIC code to a GICS sector. Falls back to INDUSTRIALS."""
        if sic_code is None:
            return GICSSector.INDUSTRIALS
        return self._mapping.get(sic_code, GICSSector.INDUSTRIALS)
