"""Schemas for the $10 list experiment."""

from __future__ import annotations

from pydantic import BaseModel


class ExperimentCheckoutResponse(BaseModel):
    """Response with Stripe Checkout URL for the experiment."""

    checkout_url: str


class ExperimentWebhookResponse(BaseModel):
    """Response from the experiment webhook handler."""

    status: str
