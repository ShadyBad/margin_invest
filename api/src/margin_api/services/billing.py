"""Billing service — wraps Stripe SDK for subscription management."""

from __future__ import annotations

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User

# Statuses that grant access to the paid plan
_ACTIVE_STATUSES = {"active", "trialing"}


class BillingService:
    """Manages Stripe Checkout, Customer Portal, and subscription state."""

    def __init__(
        self,
        stripe_secret_key: str,
        stripe_price_id: str,
        stripe_webhook_secret: str,
    ) -> None:
        self._stripe = stripe.StripeClient(api_key=stripe_secret_key)
        self._price_id = stripe_price_id
        self._webhook_secret = stripe_webhook_secret

    async def create_checkout_session(
        self,
        session: AsyncSession,
        user_id: int,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout Session for the Margin Invest subscription.

        Returns the checkout URL.
        """
        user = await self._get_user(session, user_id)

        # Create Stripe customer if needed
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
                "line_items": [{"price": self._price_id, "quantity": 1}],
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
    ) -> None:
        """Update user's subscription plan based on Stripe subscription status."""
        stmt = select(User).where(User.stripe_customer_id == stripe_customer_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return

        if status in _ACTIVE_STATUSES:
            user.subscription_plan = "margin_invest"
            user.stripe_subscription_id = stripe_subscription_id
        else:
            user.subscription_plan = "free"
            user.stripe_subscription_id = None

        await session.commit()

    async def _get_user(self, session: AsyncSession, user_id: int) -> User:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"User {user_id} not found")
        return user
