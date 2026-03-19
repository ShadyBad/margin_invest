"""Admin CRUD endpoints for webhook subscriptions."""

from __future__ import annotations

import logging
import secrets

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import Settings, get_settings
from margin_api.db.models import User, WebhookDelivery, WebhookSubscription
from margin_api.db.session import get_db
from margin_api.deps import get_admin_user
from margin_api.schemas.webhooks import (
    DeliveryListResponse,
    DeliveryResponse,
    WebhookCreateRequest,
    WebhookCreateResponse,
    WebhookListResponse,
    WebhookSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/webhooks", tags=["admin-webhooks"])


def _get_fernet(settings: Settings) -> Fernet:
    """Return a Fernet instance using the MFA encryption key."""
    key = settings.mfa_encryption_key
    if not key:
        raise HTTPException(status_code=500, detail="Encryption key not configured")
    return Fernet(key.encode())


@router.get("", response_model=WebhookListResponse)
async def list_subscriptions(
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db),
) -> WebhookListResponse:
    """List all webhook subscriptions."""
    result = await session.execute(
        select(WebhookSubscription).order_by(WebhookSubscription.created_at.desc())
    )
    subscriptions = result.scalars().all()
    return WebhookListResponse(
        subscriptions=[
            WebhookSummary(
                id=sub.id,
                event_type=sub.event_type,
                url=sub.url,
                is_active=sub.is_active,
                created_at=sub.created_at,
            )
            for sub in subscriptions
        ]
    )


@router.post("", response_model=WebhookCreateResponse, status_code=201)
async def create_subscription(
    body: WebhookCreateRequest,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> WebhookCreateResponse:
    """Create a webhook subscription.

    Generates a random HMAC key, encrypts it with Fernet, and stores
    only the encrypted form. The plaintext key is returned once in this
    response and cannot be retrieved again.
    """
    # Check for duplicate (event_type + url)
    existing_stmt = select(WebhookSubscription).where(
        WebhookSubscription.event_type == body.event_type,
        WebhookSubscription.url == body.url,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Subscription for event_type={body.event_type!r}"
                f" and url={body.url!r} already exists"
            ),
        )

    # Generate and encrypt HMAC key
    hmac_key_plaintext = secrets.token_hex(32)
    fernet = _get_fernet(settings)
    hmac_key_encrypted = fernet.encrypt(hmac_key_plaintext.encode()).decode()

    sub = WebhookSubscription(
        event_type=body.event_type,
        url=body.url,
        hmac_key_encrypted=hmac_key_encrypted,
        is_active=True,
        created_by=admin.id,
    )
    session.add(sub)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                f"Subscription for event_type={body.event_type!r}"
                f" and url={body.url!r} already exists"
            ),
        )

    await session.refresh(sub)

    logger.info(
        "[webhooks] Created subscription id=%d event_type=%r url=%r by admin=%d",
        sub.id,
        sub.event_type,
        sub.url,
        admin.id,
    )

    return WebhookCreateResponse(
        id=sub.id,
        event_type=sub.event_type,
        url=sub.url,
        hmac_key_plaintext=hmac_key_plaintext,
        is_active=sub.is_active,
        created_at=sub.created_at,
    )


@router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: int,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a webhook subscription by ID."""
    sub = await session.get(WebhookSubscription, subscription_id)
    if sub is None:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")

    await session.delete(sub)
    await session.commit()

    logger.info(
        "[webhooks] Deleted subscription id=%d by admin=%d",
        subscription_id,
        admin.id,
    )


@router.get("/{subscription_id}/deliveries", response_model=DeliveryListResponse)
async def list_deliveries(
    subscription_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db),
) -> DeliveryListResponse:
    """Paginated delivery history for a subscription."""
    # Verify subscription exists
    sub = await session.get(WebhookSubscription, subscription_id)
    if sub is None:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found")

    # Count total
    count_stmt = select(func.count()).where(WebhookDelivery.subscription_id == subscription_id)
    total = (await session.execute(count_stmt)).scalar_one()

    # Fetch page
    stmt = (
        select(WebhookDelivery)
        .where(WebhookDelivery.subscription_id == subscription_id)
        .order_by(WebhookDelivery.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    deliveries = (await session.execute(stmt)).scalars().all()

    return DeliveryListResponse(
        deliveries=[
            DeliveryResponse(
                id=d.id,
                event_type=d.event_type,
                status=d.status,
                attempts=d.attempts,
                last_status_code=d.last_status_code,
                last_error=d.last_error,
                created_at=d.created_at,
                delivered_at=d.delivered_at,
            )
            for d in deliveries
        ],
        total=total,
    )
