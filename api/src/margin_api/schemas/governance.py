"""Pydantic schemas for governance admin endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ApprovalSummary(BaseModel):
    id: int
    gate_type: str
    status: str
    pipeline_id: str | None = None
    payload_ref: dict | None = None
    impact_summary: dict | None = None
    submitted_at: datetime | None = None
    decided_at: datetime | None = None
    decided_by: int | None = None
    decision_reason: str | None = None
    expires_at: datetime | None = None


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalSummary]


class ApprovalDecisionRequest(BaseModel):
    reason: str | None = None


class GovernanceEventResponse(BaseModel):
    id: int
    event_type: str
    source: str
    detail: dict | None = None
    created_at: datetime | None = None


class GovernanceEventListResponse(BaseModel):
    events: list[GovernanceEventResponse]
    total: int


class GovernanceDashboardResponse(BaseModel):
    pending_count: int
    avg_approval_latency_hours: float | None = None
    rejection_rate: float | None = None
    recent_anomalies: list[dict] = []


class TransparencyResponse(BaseModel):
    oversight_levels: dict
    last_approvals: dict
    pipeline_health: dict


class GovernanceConfigResponse(BaseModel):
    config_key: str
    config_value: dict
    description: str
    is_default: bool
    updated_at: datetime | None = None


class GovernanceConfigUpdate(BaseModel):
    config_value: dict


class GovernanceConfigListResponse(BaseModel):
    configs: list[GovernanceConfigResponse]
