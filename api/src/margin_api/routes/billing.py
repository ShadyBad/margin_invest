"""Billing API routes — Stripe Checkout, portal, webhooks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import SignatureVerificationError

from margin_api.config import Settings, get_settings
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.schemas.billing import (
    BillingStatusResponse,
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
)
from margin_api.services.billing import BillingService

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


def _get_billing_service(settings: Settings = Depends(get_settings)) -> BillingService:
    return BillingService(
        stripe_secret_key=settings.stripe_secret_key,
        stripe_operator_price_id=settings.stripe_operator_price_id,
        stripe_allocator_price_id=settings.stripe_allocator_price_id,
        stripe_webhook_secret=settings.stripe_webhook_secret,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    billing: BillingService = Depends(_get_billing_service),
) -> CheckoutResponse:
    """Create a Stripe Checkout Session for the selected plan."""
    settings = get_settings()
    origin = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    url = await billing.create_checkout_session(
        db,
        user_id=user_id,
        plan=body.plan,
        success_url=f"{origin}/account?subscription=active",
        cancel_url=f"{origin}/account",
    )
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    billing: BillingService = Depends(_get_billing_service),
) -> PortalResponse:
    """Create a Stripe Customer Portal session for subscription management."""
    settings = get_settings()
    origin = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    try:
        url = await billing.create_portal_session(
            db, user_id=user_id, return_url=f"{origin}/account"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PortalResponse(portal_url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    billing: BillingService = Depends(_get_billing_service),
) -> dict:
    """Receive and process Stripe webhook events."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        event = billing.construct_webhook_event(payload, signature)
    except (ValueError, SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event.type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        subscription = event.data.object

        # Extract price_id from subscription items
        price_id = None
        if hasattr(subscription, "items") and subscription.items:
            items_data = subscription.items.get("data", [])
            if items_data:
                price_id = items_data[0].get("price", {}).get("id")

        # Extract current_period_end
        current_period_end = getattr(subscription, "current_period_end", None)

        await billing.handle_subscription_change(
            db,
            stripe_customer_id=subscription.customer,
            stripe_subscription_id=subscription.id,
            status=subscription.status,
            price_id=price_id,
            current_period_end=current_period_end,
        )

    return {"received": True}


@router.get("/status", response_model=BillingStatusResponse)
async def billing_status(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> BillingStatusResponse:
    """Return the current subscription plan and status."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    is_active = user.subscription_plan in ("operator", "allocator")
    return BillingStatusResponse(
        plan=user.subscription_plan,
        status=user.subscription_status,
        current_period_end=user.current_period_end,
        is_active=is_active,
    )
