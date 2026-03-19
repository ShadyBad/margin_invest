"""Webhook dispatcher service — HMAC signing, dispatch, and delivery."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import GovernanceEvent, WebhookDelivery, WebhookSubscription

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BACKOFF_SECONDS = [0, 1, 10, 60, 300]
DELIVERY_TIMEOUT = 10.0


class WebhookDispatcher:
    """Dispatch webhook events and manage delivery lifecycle."""

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    def _sign_payload(self, payload_bytes: bytes, key_str: str) -> str:
        """Return HMAC-SHA256 hex digest of *payload_bytes* using *key_str*."""
        return hmac.new(key_str.encode(), payload_bytes, hashlib.sha256).hexdigest()

    # ------------------------------------------------------------------
    # Dispatch — create pending delivery rows
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        session: AsyncSession,
        event_type: str,
        payload: dict,
    ) -> list[int]:
        """Create a WebhookDelivery row for every active subscriber of *event_type*.

        Returns the list of delivery IDs so the caller can enqueue ARQ jobs.
        """
        stmt = select(WebhookSubscription).where(
            WebhookSubscription.event_type == event_type,
            WebhookSubscription.is_active.is_(True),
        )
        subscriptions = (await session.execute(stmt)).scalars().all()

        delivery_ids: list[int] = []
        for sub in subscriptions:
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                event_type=event_type,
                payload=payload,
                status="pending",
                attempts=0,
            )
            session.add(delivery)
            await session.flush()  # populate delivery.id before refresh
            await session.refresh(delivery)
            delivery_ids.append(delivery.id)

        await session.commit()
        return delivery_ids

    # ------------------------------------------------------------------
    # Deliver — execute one HTTP delivery attempt
    # ------------------------------------------------------------------

    async def deliver(
        self,
        session: AsyncSession,
        delivery_id: int,
        encryption_key_str: str,
    ) -> bool:
        """Attempt to POST the webhook payload to the subscriber URL.

        Returns True if the request succeeded (2xx), False otherwise.
        Skips deliveries that are already *delivered* or *dead_letter*.
        After MAX_ATTEMPTS failures the delivery is moved to *dead_letter*
        and a GovernanceEvent is written to the database.
        """
        delivery = await session.get(WebhookDelivery, delivery_id)
        if delivery is None:
            logger.warning("WebhookDelivery %d not found", delivery_id)
            return False

        if delivery.status in ("delivered", "dead_letter"):
            logger.debug(
                "Skipping delivery %d with terminal status %r", delivery_id, delivery.status
            )
            return False

        subscription = await session.get(WebhookSubscription, delivery.subscription_id)
        if subscription is None:
            logger.warning(
                "WebhookSubscription %d not found for delivery %d",
                delivery.subscription_id,
                delivery_id,
            )
            return False

        # Decrypt HMAC key using the same Fernet pattern as TotpService
        fernet = Fernet(encryption_key_str.encode())
        hmac_key = fernet.decrypt(subscription.hmac_key_encrypted.encode()).decode()

        # Serialize payload deterministically
        payload_bytes = json.dumps(delivery.payload, sort_keys=True).encode()
        signature = self._sign_payload(payload_bytes, hmac_key)

        headers = {
            "Content-Type": "application/json",
            "X-Margin-Signature": signature,
            "X-Margin-Event": delivery.event_type,
        }

        now = datetime.now(UTC)
        delivery.attempts += 1
        delivery.last_attempt_at = now

        try:
            async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT) as client:
                response = await client.post(
                    subscription.url,
                    content=payload_bytes,
                    headers=headers,
                )
                response.raise_for_status()

            # Success
            delivery.status = "delivered"
            delivery.delivered_at = now
            delivery.last_status_code = response.status_code
            await session.commit()
            logger.info(
                "Webhook delivery %d succeeded (status=%d)",
                delivery_id,
                response.status_code,
            )
            return True

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            delivery.last_status_code = status_code
            delivery.last_error = f"HTTP {status_code}: {exc}"
            logger.warning("Webhook delivery %d failed with HTTP %s", delivery_id, status_code)
        except Exception as exc:
            delivery.last_error = str(exc)[:1000]
            logger.warning("Webhook delivery %d failed: %s", delivery_id, exc, exc_info=True)

        # Check if we've exhausted all attempts
        if delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = "dead_letter"
            gov_event = GovernanceEvent(
                event_type="webhook.dead_letter",
                source="webhook_dispatcher",
                detail={
                    "delivery_id": delivery_id,
                    "subscription_id": delivery.subscription_id,
                    "event_type": delivery.event_type,
                    "attempts": delivery.attempts,
                    "last_error": delivery.last_error,
                },
            )
            session.add(gov_event)
            logger.error(
                "Webhook delivery %d moved to dead_letter after %d attempts",
                delivery_id,
                delivery.attempts,
            )

        await session.commit()
        return False
