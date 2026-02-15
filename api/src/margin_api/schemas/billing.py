"""Billing API request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class CheckoutResponse(BaseModel):
    """Response with Stripe Checkout URL."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Response with Stripe Customer Portal URL."""

    portal_url: str


class BillingStatusResponse(BaseModel):
    """Current subscription status."""

    subscription_plan: str  # "free" | "margin_invest"
    stripe_subscription_id: str | None = None
    is_active: bool
