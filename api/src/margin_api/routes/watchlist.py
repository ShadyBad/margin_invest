"""Watchlist and Score Alert CRUD endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, ScoreAlert, V4Score, Watchlist
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.middleware.rate_limit import limiter
from margin_api.schemas.watchlist import (
    AlertCreateRequest,
    AlertListResponse,
    AlertResponse,
    WatchlistItemResponse,
    WatchlistResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/me", tags=["watchlist"])

_WATCHLIST_LIMIT = 100
_ALERT_LIMIT = 20


# ---------------------------------------------------------------------------
# Watchlist endpoints
# ---------------------------------------------------------------------------


@router.get("/watchlist", response_model=WatchlistResponse)
@limiter.limit("60/minute")
async def get_watchlist(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> WatchlistResponse:
    """Return the authenticated user's watchlist with latest score data."""
    # Subquery: latest V4Score id per asset
    latest_v4_subq = (
        select(func.max(V4Score.id).label("max_id"))
        .where(V4Score.asset_id == Asset.id)
        .correlate(Asset)
        .scalar_subquery()
    )

    stmt = (
        select(
            Watchlist.ticker,
            Watchlist.added_at,
            Asset.name,
            Asset.sector,
            V4Score.composite_score,
            V4Score.conviction,
        )
        .join(Asset, Asset.ticker == Watchlist.ticker, isouter=True)
        .outerjoin(V4Score, V4Score.id == latest_v4_subq)
        .where(Watchlist.user_id == user_id)
        .order_by(Watchlist.added_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        WatchlistItemResponse(
            ticker=row.ticker,
            added_at=row.added_at,
            name=row.name,
            sector=row.sector,
            composite_score=row.composite_score,
            composite_tier=row.conviction,
            signal=None,
        )
        for row in rows
    ]
    return WatchlistResponse(items=items, count=len(items))


@router.post("/watchlist/{ticker}", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def add_to_watchlist(
    ticker: str,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add a ticker to the user's watchlist (max 100 entries)."""
    ticker = ticker.upper().strip()

    # Enforce per-user limit
    count_result = await db.execute(
        select(func.count()).select_from(Watchlist).where(Watchlist.user_id == user_id)
    )
    current_count = count_result.scalar_one()
    if current_count >= _WATCHLIST_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Watchlist limit of {_WATCHLIST_LIMIT} reached",
        )

    entry = Watchlist(user_id=user_id, ticker=ticker)
    db.add(entry)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{ticker} is already in your watchlist",
        )

    return {"ticker": ticker, "added": True}


@router.delete("/watchlist/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def remove_from_watchlist(
    ticker: str,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a ticker from the user's watchlist."""
    ticker = ticker.upper().strip()

    result = await db.execute(
        delete(Watchlist).where(
            Watchlist.user_id == user_id,
            Watchlist.ticker == ticker,
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{ticker} not found in your watchlist",
        )


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------


@router.get("/alerts", response_model=AlertListResponse)
@limiter.limit("60/minute")
async def get_alerts(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """Return the authenticated user's score alerts."""
    stmt = (
        select(ScoreAlert)
        .where(ScoreAlert.user_id == user_id)
        .order_by(ScoreAlert.created_at.desc())
    )
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    items = [AlertResponse.model_validate(a) for a in alerts]
    return AlertListResponse(items=items, count=len(items))


@router.post("/alerts", status_code=status.HTTP_201_CREATED, response_model=AlertResponse)
@limiter.limit("20/minute")
async def create_alert(
    body: AlertCreateRequest,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Create a new score alert (max 20 per user)."""
    # Enforce per-user limit
    count_result = await db.execute(
        select(func.count()).select_from(ScoreAlert).where(ScoreAlert.user_id == user_id)
    )
    current_count = count_result.scalar_one()
    if current_count >= _ALERT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alert limit of {_ALERT_LIMIT} reached",
        )

    ticker = body.ticker.upper().strip()
    threshold = None if body.alert_type == "survivor" else body.threshold

    alert = ScoreAlert(
        user_id=user_id,
        ticker=ticker,
        alert_type=body.alert_type,
        threshold=threshold,
    )
    db.add(alert)
    try:
        await db.commit()
        await db.refresh(alert)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alert for {ticker} ({body.alert_type}) already exists",
        )

    return AlertResponse.model_validate(alert)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_alert(
    alert_id: int,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a score alert belonging to the authenticated user."""
    result = await db.execute(
        delete(ScoreAlert).where(
            ScoreAlert.id == alert_id,
            ScoreAlert.user_id == user_id,
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
