"""Admin API routes for seed validation reports."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import MlModelRun, SeedValidationReport
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter
from margin_api.routes.admin import _verify_admin_key
from margin_api.schemas.model_validation import (
    GateCheckResponse,
    MetricDistributionResponse,
    ModelComparisonResponse,
    SeedDetailResponse,
    SeedValidationHistoryResponse,
    SeedValidationReportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/model-validation", tags=["model-validation"])


async def _get_seed_details(
    session: AsyncSession, run_group_id: str, selected_seed: int | None
) -> list[SeedDetailResponse]:
    """Query MlModelRun rows matching run_group_id and build seed detail responses."""
    result = await session.execute(
        select(MlModelRun).where(MlModelRun.run_group_id == run_group_id).order_by(MlModelRun.seed)
    )
    runs = result.scalars().all()

    return [
        SeedDetailResponse(
            seed=run.seed,
            rank_ic=run.overall_rank_ic or 0.0,
            n_clusters=run.n_clusters,
            n_samples=run.n_samples,
            selected=run.seed == selected_seed if selected_seed is not None else False,
        )
        for run in runs
    ]


def _report_to_response(
    report: SeedValidationReport,
    seed_details: list[SeedDetailResponse],
) -> SeedValidationReportResponse:
    """Convert a SeedValidationReport ORM model to a response schema."""
    # Parse metric_distributions JSONB into MetricDistributionResponse objects
    metric_distributions: dict[str, MetricDistributionResponse] = {}
    if report.metric_distributions:
        for key, dist in report.metric_distributions.items():
            metric_distributions[key] = MetricDistributionResponse(**dist)

    # Parse gate_details JSONB into GateCheckResponse list, skipping "overall" key
    gate_checks: list[GateCheckResponse] = []
    if report.gate_details:
        for key, detail in report.gate_details.items():
            if key == "overall":
                continue
            gate_checks.append(
                GateCheckResponse(
                    name=key,
                    value=detail.get("value", 0.0),
                    threshold=detail.get("threshold", 0.0),
                    passed=detail.get("passed", False),
                )
            )

    # Parse previous_comparison JSONB into ModelComparisonResponse if present
    comparison: ModelComparisonResponse | None = None
    if report.previous_comparison:
        comparison = ModelComparisonResponse(**report.previous_comparison)

    return SeedValidationReportResponse(
        run_group_id=report.run_group_id,
        created_at=report.created_at.isoformat(),
        n_seeds=report.n_seeds,
        gate_passed=report.gate_passed,
        selected_seed=report.selected_seed,
        metric_distributions=metric_distributions,
        gate_checks=gate_checks,
        seed_details=seed_details,
        environment_snapshot=report.environment_snapshot or {},
        comparison=comparison,
    )


@router.get("/latest")
@limiter.limit("30/minute")
async def get_latest_validation_report(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> SeedValidationReportResponse:
    """Return the most recent seed validation report."""
    _verify_admin_key(x_admin_key)

    result = await session.execute(
        select(SeedValidationReport).order_by(SeedValidationReport.created_at.desc()).limit(1)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(404, "No validation reports found")

    seed_details = await _get_seed_details(session, report.run_group_id, report.selected_seed)
    return _report_to_response(report, seed_details)


@router.get("/history")
@limiter.limit("30/minute")
async def get_validation_history(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
) -> SeedValidationHistoryResponse:
    """Return paginated list of all seed validation reports."""
    _verify_admin_key(x_admin_key)

    # Total count
    count_result = await session.execute(select(func.count()).select_from(SeedValidationReport))
    total = count_result.scalar() or 0

    # Paginated reports
    result = await session.execute(
        select(SeedValidationReport)
        .order_by(SeedValidationReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    reports = result.scalars().all()

    report_responses = []
    for report in reports:
        seed_details = await _get_seed_details(session, report.run_group_id, report.selected_seed)
        report_responses.append(_report_to_response(report, seed_details))

    return SeedValidationHistoryResponse(reports=report_responses, total=total)


@router.get("/{run_group_id}")
@limiter.limit("30/minute")
async def get_validation_report(
    run_group_id: str,
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> SeedValidationReportResponse:
    """Return a specific seed validation report by run_group_id."""
    _verify_admin_key(x_admin_key)

    result = await session.execute(
        select(SeedValidationReport).where(SeedValidationReport.run_group_id == run_group_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(404, "Validation report not found")

    seed_details = await _get_seed_details(session, report.run_group_id, report.selected_seed)
    return _report_to_response(report, seed_details)
