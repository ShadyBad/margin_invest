"""Request and response schemas for ops endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class DailySummaryResponse(BaseModel):
    """Daily operational summary metrics."""

    mrr_by_plan: dict[str, float]
    total_users: int
    active_subscribers: int
    signups_24h: int
    active_pipeline_jobs: int
    sentry_error_count: int | None


class ChurnRiskUser(BaseModel):
    """User at risk of churn."""

    id: int
    email: str
    name: str | None
    subscription_plan: str
    last_login_at: str | None


class ChurnRiskResponse(BaseModel):
    """Response with users at churn risk."""

    users: list[ChurnRiskUser]
    total: int


class RevenueMetricsResponse(BaseModel):
    """Revenue and financial metrics."""

    mrr_total: float
    mrr_by_plan: dict[str, float]
    trials_expiring_3d: int
    payment_failed_users: int


class SendEmailRequest(BaseModel):
    """Request to send an email."""

    type: str
    to_email: str
    data: dict = {}


class SendEmailResponse(BaseModel):
    """Response confirming email send."""

    sent: bool
