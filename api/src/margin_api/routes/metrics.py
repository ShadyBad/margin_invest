"""Institutional metrics endpoint -- computes Sharpe, drawdown, volatility, etc."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_db
from margin_api.schemas.metrics import InstitutionalMetricsResponse
from margin_api.services.metrics import (
    classify_risk,
    compute_avg_profit_margin,
    compute_max_drawdown,
    compute_sharpe_ratio,
    compute_volatility,
)

router = APIRouter(prefix="/api/v1/scores", tags=["metrics"])


@router.get("/{ticker}/metrics", response_model=InstitutionalMetricsResponse)
async def get_metrics(
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> InstitutionalMetricsResponse:
    """Compute institutional metrics for a ticker from stored financial data."""
    ticker = ticker.upper()

    # Get the latest score for this ticker
    score_query = (
        select(Score, Asset.id.label("asset_id"))
        .join(Asset, Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(Score.scored_at.desc())
        .limit(1)
    )
    score_result = await db.execute(score_query)
    score_row = score_result.first()
    if score_row is None:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}")

    score = score_row.Score
    asset_id = score.asset_id

    # Get the latest financial data
    fd_query = (
        select(FinancialData)
        .where(FinancialData.asset_id == asset_id)
        .order_by(FinancialData.period_end.desc())
        .limit(1)
    )
    fd_result = await db.execute(fd_query)
    fin_data = fd_result.scalar()

    # Extract close prices from price_history
    closes: list[float] = []
    if fin_data and fin_data.price_history:
        ph = fin_data.price_history
        bars = ph.get("bars", []) if isinstance(ph, dict) else ph
        closes = [bar["close"] for bar in bars if "close" in bar]

    # Extract income statement periods for profit margin
    income_periods: list[dict] = []
    if fin_data and fin_data.income_statement:
        inc = fin_data.income_statement
        if isinstance(inc, list):
            income_periods = inc
        elif isinstance(inc, dict):
            income_periods = [inc]

    # Compute metrics — defensive against bad data
    try:
        sharpe = compute_sharpe_ratio(closes)
    except Exception:
        sharpe = None
    try:
        max_dd = compute_max_drawdown(closes) if closes else None
    except Exception:
        max_dd = None
    try:
        vol = compute_volatility(closes)
    except Exception:
        vol = None
    try:
        avg_pm = compute_avg_profit_margin(income_periods)
    except Exception:
        avg_pm = None

    # Margin of safety
    margin_of_safety: float | None = None
    intrinsic = getattr(score, "intrinsic_value", None)
    actual = getattr(score, "actual_price", None)
    if intrinsic and actual and intrinsic > 0:
        margin_of_safety = round((intrinsic - actual) / intrinsic, 4)

    return InstitutionalMetricsResponse(
        sharpe_ratio=sharpe,
        max_drawdown=max_dd,
        volatility=vol,
        avg_profit_margin=avg_pm,
        risk_classification=classify_risk(vol),
        allocation_weight=getattr(score, "max_position_pct", None),
        margin_of_safety=margin_of_safety,
    )
