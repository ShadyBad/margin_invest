"""Pydantic schemas for webhook subscription admin CRUD."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

VALID_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "score.staged",
        "score.approved",
        "score.published",
        "model.promoted",
        "circuit_breaker.tripped",
        "config.updated",
    }
)


class WebhookCreateRequest(BaseModel):
    event_type: str
    url: str

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type {v!r}. Must be one of: {sorted(VALID_EVENT_TYPES)}"
            )
        return v


class WebhookCreateResponse(BaseModel):
    id: int
    event_type: str
    url: str
    hmac_key_plaintext: str
    is_active: bool
    created_at: datetime


class WebhookSummary(BaseModel):
    id: int
    event_type: str
    url: str
    is_active: bool
    created_at: datetime


class WebhookListResponse(BaseModel):
    subscriptions: list[WebhookSummary]


class DeliveryResponse(BaseModel):
    id: int
    event_type: str
    status: str
    attempts: int
    last_status_code: int | None
    last_error: str | None
    created_at: datetime
    delivered_at: datetime | None


class DeliveryListResponse(BaseModel):
    deliveries: list[DeliveryResponse]
    total: int
