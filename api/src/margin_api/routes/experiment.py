"""Experiment API routes — $10 list one-shot Stripe Checkout."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import Settings, get_settings
from margin_api.db.models import ExperimentSignup
from margin_api.db.session import get_db
from margin_api.schemas.experiment import ExperimentCheckoutResponse, ExperimentWebhookResponse
from margin_api.services.email import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/experiment", tags=["experiment"])


@router.post("/checkout", response_model=ExperimentCheckoutResponse)
async def create_experiment_checkout(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ExperimentCheckoutResponse:
    """Create a one-shot Stripe Checkout session for the $10 list."""
    body = await request.json()
    success_url = body.get("success_url", "")
    cancel_url = body.get("cancel_url", "")

    if not success_url or not cancel_url:
        raise HTTPException(status_code=400, detail="success_url and cancel_url required")

    stripe.api_key = settings.stripe_secret_key

    checkout_session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": 1000,
                    "product_data": {
                        "name": "Margin Invest \u2014 This Week's 10 Survivors",
                        "description": "Forensic scorecard of this week's conviction-gated picks.",
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={"experiment": "ten_dollar_list"},
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return ExperimentCheckoutResponse(checkout_url=checkout_session.url)


@router.post("/webhook", response_model=ExperimentWebhookResponse)
async def experiment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ExperimentWebhookResponse:
    """Handle Stripe webhook for experiment checkout completions."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload.decode("utf-8"),
            signature,
            settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] != "checkout.session.completed":
        return ExperimentWebhookResponse(status="ignored")

    session_obj = event["data"]["object"]
    metadata = session_obj.get("metadata", {})

    if metadata.get("experiment") != "ten_dollar_list":
        return ExperimentWebhookResponse(status="ignored")

    stripe_session_id = session_obj["id"]
    email = session_obj.get("customer_details", {}).get("email", "")
    amount_cents = session_obj.get("amount_total", 0)

    # Idempotency: skip if already processed
    existing = await db.execute(
        select(ExperimentSignup).where(ExperimentSignup.stripe_session_id == stripe_session_id)
    )
    if existing.scalar_one_or_none():
        return ExperimentWebhookResponse(status="already_processed")

    signup = ExperimentSignup(
        email=email,
        paid_at=datetime.now(UTC),
        amount_cents=amount_cents,
        stripe_session_id=stripe_session_id,
    )
    db.add(signup)
    await db.commit()

    # Send confirmation email with placeholder PDF
    email_svc = EmailService(api_key=settings.resend_api_key)
    email_svc.send_custom(
        email,
        "Your Margin Invest Survivor List",
        (
            "<h2>Thank you for your purchase!</h2>"
            "<p>Your weekly survivor list is being prepared. "
            "You'll receive it within 24 hours of the next market close.</p>"
            "<p>This report contains the conviction-gated picks that survived "
            "our elimination pipeline \u2014 with factor decomposition and "
            "plain-English interpretation for each ticker.</p>"
            "<p>Questions? Reply to this email.</p>"
        ),
    )

    logger.info("Experiment signup recorded: %s (session %s)", email, stripe_session_id)
    return ExperimentWebhookResponse(status="ok")
