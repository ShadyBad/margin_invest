"""13F filing ingestion service -- fetches, parses, stores institutional holdings."""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import (
    FilingMetadata,
    InstitutionalHolding,
    Manager,
    SecurityMaster,
)

logger = logging.getLogger(__name__)


class ThirteenFIngestService:
    """Service layer for ingesting 13F institutional filings into the database.

    Handles manager upsert, filing deduplication, security master lookups,
    and bulk holding storage.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_managers(self, funds: list[dict]) -> list[Manager]:
        """Insert or update manager records from a list of fund dicts.

        Each dict must contain at minimum ``cik`` and ``name``.
        Optional keys: ``short_name``, ``tier``.
        """
        managers: list[Manager] = []
        for f in funds:
            result = await self._session.execute(select(Manager).where(Manager.cik == f["cik"]))
            existing = result.scalar_one_or_none()
            if existing:
                existing.name = f["name"]
                existing.short_name = f.get("short_name")
                existing.tier = f.get("tier", "top_aum")
                managers.append(existing)
            else:
                mgr = Manager(
                    cik=f["cik"],
                    name=f["name"],
                    short_name=f.get("short_name"),
                    tier=f.get("tier", "top_aum"),
                )
                self._session.add(mgr)
                managers.append(mgr)
        await self._session.commit()
        return managers

    async def is_filing_new(self, accession_number: str) -> bool:
        """Check whether a filing with the given accession number already exists."""
        result = await self._session.execute(
            select(FilingMetadata.id).where(FilingMetadata.accession_number == accession_number)
        )
        return result.scalar_one_or_none() is None

    async def get_or_create_security(self, cusip: str, issuer_name: str) -> SecurityMaster:
        """Return existing SecurityMaster by CUSIP, or create a new unresolved entry."""
        result = await self._session.execute(
            select(SecurityMaster).where(SecurityMaster.cusip == cusip)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        sec = SecurityMaster(
            cusip=cusip,
            issuer_name=issuer_name,
            resolution_method="unresolved",
        )
        self._session.add(sec)
        await self._session.flush()
        return sec

    async def store_holdings(
        self,
        filing: FilingMetadata,
        manager: Manager,
        parsed_holdings: list[dict],
    ) -> int:
        """Store parsed holdings for a filing. Returns count inserted."""
        count = 0
        for h in parsed_holdings:
            sec = await self.get_or_create_security(h["cusip"], h["issuer_name"])
            holding = InstitutionalHolding(
                filing_id=filing.id,
                manager_id=manager.id,
                security_master_id=sec.id,
                cusip=h["cusip"],
                period_of_report=filing.period_of_report,
                shares_held=h["shares"],
                value_thousands=h["value_thousands"],
                put_call=h.get("put_call", "NONE"),
                investment_discretion=h.get("investment_discretion"),
                voting_authority_sole=h.get("voting_sole"),
                voting_authority_shared=h.get("voting_shared"),
                voting_authority_none=h.get("voting_none"),
            )
            self._session.add(holding)
            count += 1
        await self._session.commit()
        return count

    async def handle_amendment(
        self, manager: Manager, period_of_report: date, new_accession: str
    ) -> int | None:
        """Find original filing for an amendment.

        Returns the original filing id, or ``None`` if no non-amendment
        filing exists for that manager and period.
        """
        result = await self._session.execute(
            select(FilingMetadata)
            .where(
                FilingMetadata.manager_id == manager.id,
                FilingMetadata.period_of_report == period_of_report,
                FilingMetadata.is_amendment == False,  # noqa: E712
            )
            .order_by(FilingMetadata.filed_date.desc())
            .limit(1)
        )
        original = result.scalar_one_or_none()
        return original.id if original else None
