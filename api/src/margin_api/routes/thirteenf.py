"""13F institutional holdings API routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path, Query
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
from margin_api.deps import require_plan
from margin_api.schemas.thirteenf import (
    ChangesSummary,
    ClonePosition,
    CloneResponse,
    CrowdedTrade,
    HolderResponse,
    HoldingsHistoryQuarter,
    HoldingsHistoryResponse,
    HoldingsResponse,
    HoldingsSummary,
    ManagerPortfolioResponse,
    ManagerResponse,
    NewPositionResponse,
    OverlapEntry,
    OverlapResponse,
    PortfolioHolding,
)

router = APIRouter(prefix="/api/v1/13f", tags=["13f"])


# ---------------------------------------------------------------------------
# Holdings endpoints (Task 11)
# ---------------------------------------------------------------------------


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
            latest_period_q2 = select(func.max(InstitutionalHolding.period_of_report)).where(
                InstitutionalHolding.cusip == cusip
            )
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


# ---------------------------------------------------------------------------
# Manager endpoints (Task 12)
# ---------------------------------------------------------------------------


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
    user_id: int = Depends(require_plan("institutional")),
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


# ---------------------------------------------------------------------------
# Analytics endpoints (Task 13)
# ---------------------------------------------------------------------------


@router.get("/analytics/overlap", response_model=OverlapResponse)
async def get_overlap(
    user_id: int = Depends(require_plan("institutional")),
    db: AsyncSession = Depends(get_db),
) -> OverlapResponse:
    """Get most commonly held tickers and crowded trades across all tracked managers."""
    # Find the latest period
    latest_q = select(func.max(InstitutionalHolding.period_of_report))
    result = await db.execute(latest_q)
    latest_period = result.scalar_one_or_none()
    if latest_period is None:
        return OverlapResponse(period_of_report=date.today(), most_held=[], crowded_trades=[])

    # Most held: count distinct managers per ticker
    overlap_q = (
        select(
            SecurityMaster.ticker,
            func.count(func.distinct(InstitutionalHolding.manager_id)).label("holder_count"),
        )
        .join(SecurityMaster, InstitutionalHolding.security_master_id == SecurityMaster.id)
        .where(InstitutionalHolding.period_of_report == latest_period)
        .group_by(SecurityMaster.ticker)
        .order_by(func.count(func.distinct(InstitutionalHolding.manager_id)).desc())
        .limit(50)
    )
    overlap_result = await db.execute(overlap_q)
    most_held = []
    for row in overlap_result.all():
        if row.ticker is None:
            continue
        # Count curated holders
        curated_q = (
            select(func.count(func.distinct(InstitutionalHolding.manager_id)))
            .join(Manager, InstitutionalHolding.manager_id == Manager.id)
            .join(SecurityMaster, InstitutionalHolding.security_master_id == SecurityMaster.id)
            .where(
                SecurityMaster.ticker == row.ticker,
                InstitutionalHolding.period_of_report == latest_period,
                Manager.tier == "curated",
            )
        )
        curated_result = await db.execute(curated_q)
        curated_count = curated_result.scalar() or 0
        most_held.append(
            OverlapEntry(
                ticker=row.ticker,
                holder_count=row.holder_count,
                curated_count=curated_count,
            )
        )

    # Crowded trades: tickers with most new positions (holders not present in previous quarter)
    # For now, return empty -- requires prev quarter comparison
    crowded_trades: list[CrowdedTrade] = []

    return OverlapResponse(
        period_of_report=latest_period,
        most_held=most_held,
        crowded_trades=crowded_trades,
    )


@router.get("/analytics/new-positions", response_model=NewPositionResponse)
async def get_new_positions(
    user_id: int = Depends(require_plan("institutional")),
    db: AsyncSession = Depends(get_db),
) -> NewPositionResponse:
    """Get tickers with the most new institutional positions this quarter."""
    latest_q = select(func.max(InstitutionalHolding.period_of_report))
    result = await db.execute(latest_q)
    latest_period = result.scalar_one_or_none()
    if latest_period is None:
        return NewPositionResponse(period_of_report=date.today(), new_positions=[])

    # For now return empty list -- proper new position detection requires
    # comparing current quarter holdings to previous quarter
    return NewPositionResponse(
        period_of_report=latest_period,
        new_positions=[],
    )


@router.get("/analytics/clone/{manager_id}", response_model=CloneResponse)
async def get_clone_portfolio(
    manager_id: int,
    strategy: str = Query(default="equal_weight_top_20"),
    user_id: int = Depends(require_plan("institutional")),
    db: AsyncSession = Depends(get_db),
) -> CloneResponse:
    """Generate a clone portfolio from a manager's latest holdings."""
    mgr = await db.get(Manager, manager_id)
    if mgr is None:
        raise HTTPException(status_code=404, detail="Manager not found")

    # Get latest filing
    filing_q = (
        select(FilingMetadata)
        .where(FilingMetadata.manager_id == manager_id)
        .order_by(FilingMetadata.period_of_report.desc())
        .limit(1)
    )
    filing_result = await db.execute(filing_q)
    filing = filing_result.scalar_one_or_none()
    if filing is None:
        raise HTTPException(status_code=404, detail="No filing found")

    # Get top N holdings by value
    n = 20 if "20" in strategy else 10
    holdings_q = (
        select(SecurityMaster.ticker, InstitutionalHolding.value_thousands)
        .join(SecurityMaster, InstitutionalHolding.security_master_id == SecurityMaster.id)
        .where(InstitutionalHolding.filing_id == filing.id)
        .order_by(InstitutionalHolding.value_thousands.desc())
        .limit(n)
    )
    holdings_result = await db.execute(holdings_q)
    rows = holdings_result.all()

    if "equal_weight" in strategy:
        weight = round(100.0 / len(rows), 2) if rows else 0
        positions = [
            ClonePosition(ticker=row.ticker or "UNKNOWN", target_weight=weight) for row in rows
        ]
    else:
        # Value-weighted
        total = sum(r.value_thousands for r in rows) or 1
        positions = [
            ClonePosition(
                ticker=row.ticker or "UNKNOWN",
                target_weight=round((row.value_thousands / total) * 100, 2),
            )
            for row in rows
        ]

    return CloneResponse(
        manager=mgr.short_name or mgr.name,
        strategy=strategy,
        period_of_report=filing.period_of_report,
        positions=positions,
        historical_performance=None,  # requires price data computation
    )
