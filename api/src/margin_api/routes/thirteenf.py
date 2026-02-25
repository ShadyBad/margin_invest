"""13F institutional holdings API routes."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import (
    AccumulationSignal,
    Asset,
    FilingMetadata,
    InstitutionalHolding,
    Manager,
    SecurityMaster,
)
from margin_api.db.session import get_db
from margin_api.schemas.thirteenf import (
    HolderResponse,
    HoldingsHistoryQuarter,
    HoldingsHistoryResponse,
    HoldingsResponse,
    HoldingsSummary,
)

router = APIRouter(prefix="/api/v1/13f", tags=["13f"])


@router.get("/holdings/{ticker}", response_model=HoldingsResponse)
async def get_holdings(
    ticker: str = Path(pattern=r"^[A-Z0-9.]{1,10}$"),
    db: AsyncSession = Depends(get_db),
) -> HoldingsResponse:
    """Get current institutional holders for a ticker."""
    # Find the latest period with data for this ticker via SecurityMaster
    latest_period_q = (
        select(func.max(InstitutionalHolding.period_of_report))
        .join(SecurityMaster, InstitutionalHolding.security_master_id == SecurityMaster.id)
        .where(SecurityMaster.ticker == ticker)
    )
    result = await db.execute(latest_period_q)
    latest_period = result.scalar_one_or_none()

    if latest_period is None:
        # Fallback: try matching via Asset.cusip -> InstitutionalHolding.cusip
        cusip_q = select(Asset.cusip).where(Asset.ticker == ticker)
        cusip_result = await db.execute(cusip_q)
        cusip = cusip_result.scalar_one_or_none()
        if cusip:
            latest_period_q2 = select(
                func.max(InstitutionalHolding.period_of_report)
            ).where(InstitutionalHolding.cusip == cusip)
            result2 = await db.execute(latest_period_q2)
            latest_period = result2.scalar_one_or_none()

    if latest_period is None:
        return HoldingsResponse(
            ticker=ticker,
            period_of_report=date.today(),
            curated_holders=[],
            other_holders=[],
            summary=HoldingsSummary(
                total_holders=0,
                curated_holders=0,
                net_shares_changed=0,
                signal_score=0.0,
            ),
        )

    # Fetch holdings for this period
    holdings_q = (
        select(InstitutionalHolding, Manager)
        .join(Manager, InstitutionalHolding.manager_id == Manager.id)
        .join(SecurityMaster, InstitutionalHolding.security_master_id == SecurityMaster.id)
        .where(
            SecurityMaster.ticker == ticker,
            InstitutionalHolding.period_of_report == latest_period,
        )
    )
    holdings_result = await db.execute(holdings_q)
    rows = holdings_result.all()

    curated_holders: list[HolderResponse] = []
    other_holders: list[HolderResponse] = []
    for holding, mgr in rows:
        holder = HolderResponse(
            manager_name=mgr.short_name or mgr.name,
            tier=mgr.tier,
            shares_held=holding.shares_held,
            value_millions=round(holding.value_thousands / 1000, 2),
            shares_changed=0,  # requires previous quarter comparison
        )
        if mgr.tier == "curated":
            curated_holders.append(holder)
        else:
            other_holders.append(holder)

    # Get signal score from AccumulationSignal
    signal_score = 0.0
    asset_q = select(Asset.id).where(Asset.ticker == ticker)
    asset_result = await db.execute(asset_q)
    asset_id = asset_result.scalar_one_or_none()
    if asset_id:
        signal_q = select(AccumulationSignal.signal_score).where(
            AccumulationSignal.asset_id == asset_id,
            AccumulationSignal.period_of_report == latest_period,
        )
        signal_result = await db.execute(signal_q)
        score = signal_result.scalar_one_or_none()
        if score is not None:
            signal_score = score

    return HoldingsResponse(
        ticker=ticker,
        period_of_report=latest_period,
        curated_holders=curated_holders,
        other_holders=other_holders,
        summary=HoldingsSummary(
            total_holders=len(curated_holders) + len(other_holders),
            curated_holders=len(curated_holders),
            net_shares_changed=0,
            signal_score=signal_score,
        ),
    )


@router.get("/holdings/{ticker}/history", response_model=HoldingsHistoryResponse)
async def get_holdings_history(
    ticker: str = Path(pattern=r"^[A-Z0-9.]{1,10}$"),
    limit: int = Query(default=10, le=40),
    db: AsyncSession = Depends(get_db),
) -> HoldingsHistoryResponse:
    """Get historical quarterly holdings data for a ticker."""
    quarters_q = (
        select(
            InstitutionalHolding.period_of_report,
            func.count(InstitutionalHolding.id).label("total_holders"),
            func.sum(InstitutionalHolding.shares_held).label("total_shares"),
        )
        .join(SecurityMaster, InstitutionalHolding.security_master_id == SecurityMaster.id)
        .where(SecurityMaster.ticker == ticker)
        .group_by(InstitutionalHolding.period_of_report)
        .order_by(InstitutionalHolding.period_of_report.desc())
        .limit(limit)
    )
    result = await db.execute(quarters_q)
    rows = result.all()

    quarters: list[HoldingsHistoryQuarter] = []
    for row in rows:
        # Count curated holders for this quarter
        curated_q = (
            select(func.count(InstitutionalHolding.id))
            .join(Manager, InstitutionalHolding.manager_id == Manager.id)
            .join(SecurityMaster, InstitutionalHolding.security_master_id == SecurityMaster.id)
            .where(
                SecurityMaster.ticker == ticker,
                InstitutionalHolding.period_of_report == row.period_of_report,
                Manager.tier == "curated",
            )
        )
        curated_result = await db.execute(curated_q)
        curated_count = curated_result.scalar() or 0

        quarters.append(
            HoldingsHistoryQuarter(
                period=row.period_of_report.isoformat(),
                curated_holders=curated_count,
                total_holders=row.total_holders,
                total_shares=row.total_shares or 0,
                net_change=0,  # requires adjacent quarter comparison
            )
        )

    return HoldingsHistoryResponse(ticker=ticker, quarters=quarters)
