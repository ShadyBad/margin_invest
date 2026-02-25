"""13F institutional holdings API routes -- manager endpoints."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import (
    FilingMetadata,
    InstitutionalHolding,
    Manager,
    SecurityMaster,
)
from margin_api.db.session import get_db
from margin_api.schemas.thirteenf import (
    ChangesSummary,
    ManagerPortfolioResponse,
    ManagerResponse,
    PortfolioHolding,
)

router = APIRouter(prefix="/api/v1/13f", tags=["13f"])


@router.get("/managers", response_model=list[ManagerResponse])
async def list_managers(
    tier: str | None = Query(None, pattern="^(curated|top_aum)$"),
    db: AsyncSession = Depends(get_db),
) -> list[ManagerResponse]:
    """List tracked institutional managers."""
    q = select(Manager)
    if tier:
        q = q.where(Manager.tier == tier)
    result = await db.execute(q.order_by(Manager.name))
    managers = result.scalars().all()

    responses: list[ManagerResponse] = []
    for mgr in managers:
        # Get latest filing info
        filing_q = (
            select(FilingMetadata)
            .where(FilingMetadata.manager_id == mgr.id)
            .order_by(FilingMetadata.filed_date.desc())
            .limit(1)
        )
        filing_result = await db.execute(filing_q)
        latest_filing = filing_result.scalar_one_or_none()

        # Get top positions from latest filing
        top_positions: list[str] = []
        total_holdings = 0
        if latest_filing:
            total_holdings = latest_filing.total_holdings or 0
            top_q = (
                select(SecurityMaster.ticker)
                .join(
                    InstitutionalHolding,
                    InstitutionalHolding.security_master_id == SecurityMaster.id,
                )
                .where(InstitutionalHolding.filing_id == latest_filing.id)
                .order_by(InstitutionalHolding.value_thousands.desc())
                .limit(5)
            )
            top_result = await db.execute(top_q)
            top_positions = [t for t in top_result.scalars().all() if t is not None]

        aum: float | None = None
        if latest_filing and latest_filing.total_value:
            aum = round(latest_filing.total_value / 1000, 2)

        responses.append(
            ManagerResponse(
                id=mgr.id,
                name=mgr.short_name or mgr.name,
                tier=mgr.tier,
                aum_millions=aum,
                total_holdings=total_holdings,
                top_positions=top_positions,
                last_filing=latest_filing.filed_date if latest_filing else None,
                period_of_report=latest_filing.period_of_report if latest_filing else None,
            )
        )

    return responses


@router.get("/managers/{manager_id}/portfolio", response_model=ManagerPortfolioResponse)
async def get_manager_portfolio(
    manager_id: int,
    period: date | None = Query(None, description="Quarter end date, defaults to latest"),
    db: AsyncSession = Depends(get_db),
) -> ManagerPortfolioResponse:
    """Get a manager's full portfolio for a quarter."""
    mgr = await db.get(Manager, manager_id)
    if mgr is None:
        raise HTTPException(status_code=404, detail="Manager not found")

    # Find the filing for the requested period (or latest)
    filing_q = select(FilingMetadata).where(FilingMetadata.manager_id == manager_id)
    if period:
        filing_q = filing_q.where(FilingMetadata.period_of_report == period)
    filing_q = filing_q.order_by(FilingMetadata.period_of_report.desc()).limit(1)
    filing_result = await db.execute(filing_q)
    filing = filing_result.scalar_one_or_none()

    if filing is None:
        raise HTTPException(status_code=404, detail="No filing found for this manager")

    # Get all holdings for this filing
    holdings_q = (
        select(InstitutionalHolding, SecurityMaster)
        .join(
            SecurityMaster,
            InstitutionalHolding.security_master_id == SecurityMaster.id,
        )
        .where(InstitutionalHolding.filing_id == filing.id)
        .order_by(InstitutionalHolding.value_thousands.desc())
    )
    holdings_result = await db.execute(holdings_q)
    rows = holdings_result.all()

    total_value = sum(h.value_thousands for h, _ in rows) or 1  # avoid divide by zero

    holdings: list[PortfolioHolding] = []
    for holding, sec in rows:
        pct = round((holding.value_thousands / total_value) * 100, 2)
        holdings.append(
            PortfolioHolding(
                ticker=sec.ticker,
                cusip=holding.cusip,
                shares_held=holding.shares_held,
                value_millions=round(holding.value_thousands / 1000, 2),
                pct_portfolio=pct,
                shares_changed=0,  # requires previous quarter comparison
            )
        )

    aum = round(filing.total_value / 1000, 2) if filing.total_value else None

    return ManagerPortfolioResponse(
        manager=mgr.short_name or mgr.name,
        period_of_report=filing.period_of_report,
        aum_millions=aum,
        holdings=holdings,
        changes_summary=ChangesSummary(
            new_positions=[],
            exited_positions=[],
            increased=0,
            decreased=0,
            unchanged=len(holdings),
        ),
    )
