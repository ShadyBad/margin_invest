"""Ops endpoints for n8n workflows and Paperclip agent consumption."""

from __future__ import annotations

import hmac
import logging
import os
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import JobRun, User
from margin_api.db.session import get_db
from margin_api.schemas.ops import (
    ChurnRiskResponse,
    ChurnRiskUser,
    DailySummaryResponse,
    RevenueMetricsResponse,
    SendEmailRequest,
    SendEmailResponse,
)
from margin_api.services.email import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])

_PLAN_PRICES: dict[str, float] = {
    "portfolio": 29.0,
    "institutional": 99.0,
    "operator": 299.0,
}


def _verify_admin_key(
    x_admin_key: str = Header(),
    settings=Depends(get_settings),
) -> None:
    """Verify the admin API key from the X-Admin-Key header."""
    if not settings.admin_key:
        raise HTTPException(503, "Admin key not configured")
    if not hmac.compare_digest(x_admin_key or "", settings.admin_key):
        raise HTTPException(403, "Invalid admin key")


async def _fetch_sentry_error_count() -> int | None:
    """Fetch recent error count from Sentry API. Returns None on failure."""
    auth_token = os.environ.get("SENTRY_AUTH_TOKEN")
    org = os.environ.get("SENTRY_ORG")
    project = os.environ.get("SENTRY_PROJECT")

    if not all([auth_token, org, project]):
        return None

    try:
        import httpx

        url = f"https://sentry.io/api/0/projects/{org}/{project}/issues/"
        params = {"statsPeriod": "24h", "query": "is:unresolved"}
        headers = {"Authorization": f"Bearer {auth_token}"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return len(resp.json())
    except Exception:
        logger.exception("Failed to fetch Sentry error count")
        return None


_EMAIL_TYPE_MAP: dict[str, str] = {
    "welcome": "send_welcome",
    "onboarding_tips": "send_onboarding_tips",
    "payment_received": "send_payment_received",
    "payment_failed": "send_payment_failed",
    "trial_ending": "send_trial_ending",
    "subscription_cancelled": "send_subscription_cancelled",
    "weekly_digest": "send_weekly_digest",
    "custom": "send_custom",
}


@router.get("/daily-summary", response_model=DailySummaryResponse)
async def daily_summary(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_admin_key),
) -> DailySummaryResponse:
    """Daily operational summary: MRR, users, signups, jobs, errors."""
    now = datetime.now(UTC)
    day_ago = now - timedelta(days=1)

    # Total users
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # Active subscribers (status = 'active')
    active_subs = (
        await db.execute(
            select(func.count(User.id)).where(User.subscription_status == "active")
        )
    ).scalar() or 0

    # Signups in last 24h
    signups_24h = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= day_ago)
        )
    ).scalar() or 0

    # Active pipeline jobs (status in running, queued)
    active_jobs = (
        await db.execute(
            select(func.count(JobRun.id)).where(
                JobRun.status.in_(["running", "queued"])
            )
        )
    ).scalar() or 0

    # MRR by plan
    mrr_by_plan: dict[str, float] = {}
    for plan, price in _PLAN_PRICES.items():
        count = (
            await db.execute(
                select(func.count(User.id)).where(
                    User.subscription_plan == plan,
                    User.subscription_status == "active",
                )
            )
        ).scalar() or 0
        mrr_by_plan[plan] = price * count

    # Sentry errors
    sentry_count = await _fetch_sentry_error_count()

    return DailySummaryResponse(
        mrr_by_plan=mrr_by_plan,
        total_users=total_users,
        active_subscribers=active_subs,
        signups_24h=signups_24h,
        active_pipeline_jobs=active_jobs,
        sentry_error_count=sentry_count,
    )


@router.get("/churn-risk-users", response_model=ChurnRiskResponse)
async def churn_risk_users(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_admin_key),
) -> ChurnRiskResponse:
    """Active subscribers with no login in 14+ days."""
    cutoff = datetime.now(UTC) - timedelta(days=14)

    stmt = select(User).where(
        User.subscription_status.in_(["active", "trialing"]),
        or_(User.last_login_at < cutoff, User.last_login_at.is_(None)),
    )
    result = await db.execute(stmt)
    users = result.scalars().all()

    risk_users = [
        ChurnRiskUser(
            id=u.id,
            email=u.email,
            name=u.name,
            subscription_plan=u.subscription_plan,
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        )
        for u in users
    ]

    return ChurnRiskResponse(users=risk_users, total=len(risk_users))


@router.get("/revenue-metrics", response_model=RevenueMetricsResponse)
async def revenue_metrics(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_admin_key),
) -> RevenueMetricsResponse:
    """Revenue breakdown: MRR, expiring trials, failed payments."""
    now = datetime.now(UTC)
    three_days = now + timedelta(days=3)

    # MRR by plan
    mrr_by_plan: dict[str, float] = {}
    mrr_total = 0.0
    for plan, price in _PLAN_PRICES.items():
        count = (
            await db.execute(
                select(func.count(User.id)).where(
                    User.subscription_plan == plan,
                    User.subscription_status == "active",
                )
            )
        ).scalar() or 0
        amount = price * count
        mrr_by_plan[plan] = amount
        mrr_total += amount

    # Trials expiring within 3 days
    trials_expiring = (
        await db.execute(
            select(func.count(User.id)).where(
                User.subscription_status == "trialing",
                User.current_period_end <= three_days,
                User.current_period_end >= now,
            )
        )
    ).scalar() or 0

    # Payment failed users (past_due status)
    payment_failed = (
        await db.execute(
            select(func.count(User.id)).where(
                User.subscription_status == "past_due",
            )
        )
    ).scalar() or 0

    return RevenueMetricsResponse(
        mrr_total=mrr_total,
        mrr_by_plan=mrr_by_plan,
        trials_expiring_3d=trials_expiring,
        payment_failed_users=payment_failed,
    )


@router.post("/send-email", response_model=SendEmailResponse)
async def send_email(
    body: SendEmailRequest,
    _: None = Depends(_verify_admin_key),
) -> SendEmailResponse:
    """Dispatch an email by type via EmailService."""
    method_name = _EMAIL_TYPE_MAP.get(body.type)
    if not method_name:
        raise HTTPException(
            400,
            f"Unknown email type: {body.type}. "
            f"Valid types: {', '.join(sorted(_EMAIL_TYPE_MAP.keys()))}",
        )

    settings = get_settings()
    svc = EmailService(api_key=settings.resend_api_key)
    method = getattr(svc, method_name)

    # Merge to_email into kwargs
    kwargs = {"to_email": body.to_email, **body.data}
    sent = method(**kwargs)

    return SendEmailResponse(sent=sent)
