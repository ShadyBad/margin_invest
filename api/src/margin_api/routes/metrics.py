"""Institutional metrics endpoint -- computes Sharpe, drawdown, volatility, etc."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from margin_engine.models.financial import PriceBar
from margin_engine.scoring.risk_metrics import RiskMetrics, compute_risk_metrics
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_db
from margin_api.schemas.metrics import InstitutionalMetricsResponse, MetricStatus
from margin_api.services.metrics import (
    classify_risk,
    compute_avg_profit_margin,
)

router = APIRouter(prefix="/api/v1/scores", tags=["metrics"])


def _metric(value: float | None, reason: str) -> MetricStatus:
    """Wrap a metric value with an unavailability reason when None."""
    if value is not None:
        return MetricStatus(value=value)
    return MetricStatus(unavailable_reason=reason)


def _build_price_bars(raw_bars: list[dict]) -> list[PriceBar]:
    """Convert raw JSON bar dicts into engine PriceBar objects.

    Handles both lowercase (legacy) and capitalized (yfinance) key formats.
    """
    result: list[PriceBar] = []
    for bar in raw_bars:
        close_val = bar.get("close") or bar.get("Close")
        date_val = bar.get("date") or bar.get("Date")
        if close_val is None or date_val is None:
            continue
        # Trim datetime to date-only if needed (yfinance: "2025-02-14T00:00:00-05:00")
        date_str = str(date_val)[:10] if len(str(date_val)) > 10 else str(date_val)
        try:
            result.append(
                PriceBar(
                    date=date_str,
                    open=Decimal(str(bar.get("open") or bar.get("Open") or 0)),
                    high=Decimal(str(bar.get("high") or bar.get("High") or 0)),
                    low=Decimal(str(bar.get("low") or bar.get("Low") or 0)),
                    close=Decimal(str(close_val)),
                    volume=int(bar.get("volume") or bar.get("Volume") or 0),
                )
            )
        except (ValueError, TypeError, ArithmeticError):
            continue
    return result


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

    # Build PriceBar objects from price_history
    price_bars: list[PriceBar] = []
    no_price_reason = "No price history available"
    if fin_data and fin_data.price_history:
        ph = fin_data.price_history
        raw_bars = ph.get("bars", []) if isinstance(ph, dict) else ph
        price_bars = _build_price_bars(raw_bars)
        if len(price_bars) < 5:
            no_price_reason = f"Insufficient price history ({len(price_bars)} bars, need 5+)"

    # Compute risk metrics via engine
    risk_metrics: RiskMetrics | None = None
    try:
        if len(price_bars) >= 5:
            risk_metrics = compute_risk_metrics(price_bars, risk_free_rate=0.05)
    except Exception:
        risk_metrics = None

    # Extract 1Y metrics
    sharpe = risk_metrics.sharpe_1y if risk_metrics else None
    max_dd = risk_metrics.max_drawdown_1y if risk_metrics else None
    vol_decimal = risk_metrics.volatility_1y if risk_metrics else None

    # Extract 3Y metrics
    sharpe_3y = risk_metrics.sharpe_3y if risk_metrics else None
    max_dd_3y = risk_metrics.max_drawdown_3y if risk_metrics else None
    vol_3y_decimal = risk_metrics.volatility_3y if risk_metrics else None

    # Unavailable reasons from engine
    sharpe_reason = (
        risk_metrics.sharpe_unavailable_reason if risk_metrics else None
    ) or no_price_reason
    dd_reason = (
        risk_metrics.drawdown_unavailable_reason if risk_metrics else None
    ) or no_price_reason
    vol_reason = (
        risk_metrics.volatility_unavailable_reason if risk_metrics else None
    ) or no_price_reason

    # 3Y unavailable reason: always needs ~757 bars
    reason_3y = "Insufficient data for 3-year metric"
    sharpe_3y_reason = sharpe_reason if sharpe is None else reason_3y
    dd_3y_reason = dd_reason if max_dd is None else reason_3y
    vol_3y_reason = vol_reason if vol_decimal is None else reason_3y

    # Convert engine volatility (decimal ratio) to percentage for classify_risk
    vol_pct = vol_decimal * 100 if vol_decimal is not None else None

    # Extract income statement periods for profit margin
    income_periods: list[dict] = []
    if fin_data and fin_data.income_statement:
        inc = fin_data.income_statement
        if isinstance(inc, list):
            income_periods = inc
        elif isinstance(inc, dict):
            income_periods = [inc]

    try:
        avg_pm = compute_avg_profit_margin(income_periods)
    except Exception:
        avg_pm = None

    # Margin of safety
    margin_of_safety: float | None = None
    mos_reason = "No intrinsic value or price available"
    intrinsic = getattr(score, "margin_invest_value", None)
    actual = getattr(score, "actual_price", None)
    if intrinsic and actual and intrinsic > 0:
        margin_of_safety = round((intrinsic - actual) / intrinsic, 4)
        mos_reason = ""

    # Delta: price upside = (margin_invest_value - actual_price) / actual_price
    delta: float | None = None
    delta_reason = "No margin_invest_value or actual_price available"
    if intrinsic and actual and actual > 0:
        delta = round((intrinsic - actual) / actual, 4)
        delta_reason = ""

    return InstitutionalMetricsResponse(
        sharpe_ratio=_metric(sharpe, sharpe_reason),
        sharpe_ratio_3y=_metric(sharpe_3y, sharpe_3y_reason),
        max_drawdown=_metric(max_dd, dd_reason),
        max_drawdown_3y=_metric(max_dd_3y, dd_3y_reason),
        volatility=_metric(vol_pct, vol_reason),
        volatility_3y=_metric(
            vol_3y_decimal * 100 if vol_3y_decimal is not None else None, vol_3y_reason
        ),
        avg_profit_margin=_metric(
            avg_pm,
            "No income statement data"
            if not income_periods
            else "Missing revenue or income fields",
        ),
        delta=_metric(delta, delta_reason) if delta_reason else MetricStatus(value=delta),
        risk_classification=classify_risk(vol_pct),
        margin_of_safety=(
            _metric(margin_of_safety, mos_reason)
            if mos_reason
            else MetricStatus(value=margin_of_safety)
        ),
    )
