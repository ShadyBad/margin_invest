"""Billing API request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session."""

    plan: str  # "operator" | "allocator"


class CheckoutResponse(BaseModel):
    """Response with Stripe Checkout URL."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Response with Stripe Customer Portal URL."""

    portal_url: str


class BillingStatusResponse(BaseModel):
    """Current subscription status."""

    plan: str  # "scout" | "operator" | "allocator"
    status: str | None = None  # "active" | "trialing" | "past_due" | "canceled"
    current_period_end: datetime | None = None
    is_active: bool
