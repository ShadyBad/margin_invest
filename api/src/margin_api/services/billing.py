"""Billing service — wraps Stripe SDK for subscription management."""

from __future__ import annotations

from datetime import UTC, datetime

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User

_ACTIVE_STATUSES = {"active", "trialing"}


class BillingService:
    """Manages Stripe Checkout, Customer Portal, and subscription state."""

    def __init__(
        self,
        stripe_secret_key: str,
        stripe_operator_price_id: str,
        stripe_allocator_price_id: str,
        stripe_webhook_secret: str,
    ) -> None:
        self._stripe = stripe.StripeClient(api_key=stripe_secret_key)
        self._webhook_secret = stripe_webhook_secret
        self._price_to_plan = {
            stripe_operator_price_id: "operator",
            stripe_allocator_price_id: "allocator",
        }
        self._plan_to_price = {v: k for k, v in self._price_to_plan.items()}

    async def create_checkout_session(
        self,
        session: AsyncSession,
        user_id: int,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout Session. Returns the checkout URL."""
        price_id = self._plan_to_price.get(plan)
        if not price_id:
            raise ValueError(f"Unknown plan: {plan}")

        user = await self._get_user(session, user_id)

        if not user.stripe_customer_id:
            customer = self._stripe.v1.customers.create(
                params={
                    "email": user.email,
                    "name": user.name,
                    "metadata": {"user_id": str(user.id)},
                }
            )
            user.stripe_customer_id = customer.id
            await session.commit()

        checkout = self._stripe.v1.checkout.sessions.create(
            params={
                "customer": user.stripe_customer_id,
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
        )
        return checkout.url

    async def create_portal_session(
        self,
        session: AsyncSession,
        user_id: int,
        return_url: str,
    ) -> str:
        """Create a Stripe Customer Portal session. Returns the portal URL."""
        user = await self._get_user(session, user_id)
        if not user.stripe_customer_id:
            raise ValueError("User has no Stripe customer ID")

        portal = self._stripe.v1.billing_portal.sessions.create(
            params={
                "customer": user.stripe_customer_id,
                "return_url": return_url,
            }
        )
        return portal.url

    def construct_webhook_event(self, payload: bytes, signature: str) -> stripe.Event:
        """Verify and construct a Stripe webhook event."""
        return stripe.Webhook.construct_event(
            payload.decode("utf-8"),
            signature,
            self._webhook_secret,
        )

    async def handle_subscription_change(
        self,
        session: AsyncSession,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        status: str,
        price_id: str | None = None,
        current_period_end: int | None = None,
    ) -> None:
        """Update user subscription based on Stripe webhook data."""
        stmt = select(User).where(User.stripe_customer_id == stripe_customer_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return

        user.subscription_status = status
        user.stripe_subscription_id = stripe_subscription_id

        if current_period_end:
            user.current_period_end = datetime.fromtimestamp(
                current_period_end, tz=UTC
            )

        if status in _ACTIVE_STATUSES:
            plan = self._price_to_plan.get(price_id or "", "operator")
            user.subscription_plan = plan
        else:
            user.subscription_plan = "scout"

        await session.commit()

    async def _get_user(self, session: AsyncSession, user_id: int) -> User:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"User {user_id} not found")
        return user
