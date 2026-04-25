"""Risk factor diffing API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import FilingText, RiskFactorAnalysis
from margin_api.db.session import get_db
from margin_api.schemas.risk_diffing import MaterialChangeResponse, RiskFactorAnalysisResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/risk_factors/{ticker}", response_model=RiskFactorAnalysisResponse)
async def get_risk_factor_analysis(
    ticker: str,
    include_verbatim: bool = False,
    db: AsyncSession = Depends(get_db),
) -> RiskFactorAnalysisResponse:
    """Return the most recent risk factor diff analysis for a ticker.

    Raises 404 if no analysis has been run for the given ticker.
    """
    stmt = (
        select(RiskFactorAnalysis)
        .where(RiskFactorAnalysis.ticker == ticker.upper())
        .order_by(RiskFactorAnalysis.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail=f"No risk factor analysis found for ticker '{ticker.upper()}'",
        )

    current_filing = await db.get(FilingText, analysis.filing_text_id)
    prior_filing = await db.get(FilingText, analysis.prior_filing_text_id)

    raw_changes: list[dict] = analysis.material_changes or []
    material_changes: list[MaterialChangeResponse] = []
    for change in raw_changes:
        mc = MaterialChangeResponse(
            change_type=change.get("change_type", ""),
            topic=change.get("topic", ""),
            severity=change.get("severity", 0),
            summary_50_words=change.get("summary_50_words", ""),
            verbatim_new_text=change.get("verbatim_new_text") if include_verbatim else None,
            verbatim_old_text=change.get("verbatim_old_text") if include_verbatim else None,
        )
        material_changes.append(mc)

    return RiskFactorAnalysisResponse(
        ticker=analysis.ticker,
        current_period=current_filing.period_end if current_filing else None,
        prior_period=prior_filing.period_end if prior_filing else None,
        overall_risk_delta_score=analysis.overall_risk_delta_score or 0.0,
        model_confidence=analysis.model_confidence or 0.0,
        material_changes=material_changes,
        prompt_version=analysis.prompt_version,
        analyzed_at=analysis.created_at,
    )
