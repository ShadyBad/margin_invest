"""Tests for the $10 list experiment endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import ExperimentSignup
from margin_api.db.session import get_db


_TEST_WEBHOOK_SECRET = "whsec_test_secret"


def _make_test_settings() -> MagicMock:
    """Create a mock Settings object for experiment tests."""
    settings = MagicMock()
    settings.stripe_secret_key = "sk_test_fake"
    settings.stripe_webhook_secret = _TEST_WEBHOOK_SECRET
    settings.resend_api_key = ""
    settings.stripe_portfolio_price_id = ""
    settings.stripe_institutional_price_id = ""
    settings.cors_origins = ["http://localhost:3000"]
    settings.debug = True
    settings.environment = "development"
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    settings.rate_limit_enabled = False
    settings.redis_url = "redis://localhost:6379"
    return settings


def _sign_payload(payload_bytes: bytes) -> str:
    """Build a Stripe-style webhook signature for testing."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload_bytes.decode()}"
    sig = hmac.new(
        _TEST_WEBHOOK_SECRET.encode(), signed_payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={sig}"


@pytest_asyncio.fixture()
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = _make_test_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, factory

    await engine.dispose()


@pytest.mark.asyncio
async def test_checkout_creates_stripe_session(setup):
    """POST /api/v1/experiment/checkout returns a Stripe Checkout URL."""
    client, _ = setup

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"

    with patch("margin_api.routes.experiment.stripe") as mock_stripe:
        mock_stripe.checkout.Session.create.return_value = mock_session
        response = await client.post(
            "/api/v1/experiment/checkout",
            json={"success_url": "http://localhost:3000/experiment/this-week?success=1",
                  "cancel_url": "http://localhost:3000/experiment/this-week"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"

    # Verify Stripe was called with payment mode and $10
    call_kwargs = mock_stripe.checkout.Session.create.call_args
    assert call_kwargs.kwargs["mode"] == "payment"
    line_items = call_kwargs.kwargs["line_items"]
    assert line_items[0]["price_data"]["unit_amount"] == 1000
    assert line_items[0]["price_data"]["currency"] == "usd"


@pytest.mark.asyncio
async def test_webhook_inserts_signup_and_sends_email(setup):
    """POST /api/v1/experiment/webhook records signup and triggers email."""
    client, factory = setup

    event_payload = {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_abc",
                "customer_details": {"email": "buyer@example.com"},
                "amount_total": 1000,
                "payment_status": "paid",
                "metadata": {"experiment": "ten_dollar_list"},
            }
        },
    }
    payload_bytes = json.dumps(event_payload).encode()
    stripe_signature = _sign_payload(payload_bytes)

    with patch("margin_api.routes.experiment.EmailService") as mock_email_cls:
        mock_email = MagicMock()
        mock_email.send_custom.return_value = True
        mock_email_cls.return_value = mock_email

        with patch("margin_api.routes.experiment.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = event_payload
            mock_stripe.SignatureVerificationError = Exception

            response = await client.post(
                "/api/v1/experiment/webhook",
                content=payload_bytes,
                headers={
                    "stripe-signature": stripe_signature,
                    "content-type": "application/json",
                },
            )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify the signup was recorded in the DB
    async with factory() as session:
        result = await session.execute(
            select(ExperimentSignup).where(
                ExperimentSignup.stripe_session_id == "cs_test_abc"
            )
        )
        signup = result.scalar_one()
        assert signup.email == "buyer@example.com"
        assert signup.amount_cents == 1000

    # Verify email was sent
    mock_email.send_custom.assert_called_once()
    call_args = mock_email.send_custom.call_args
    assert call_args.args[0] == "buyer@example.com"
    assert "survivor" in call_args.args[1].lower() or "list" in call_args.args[1].lower()


@pytest.mark.asyncio
async def test_webhook_idempotent_on_duplicate_session(setup):
    """Duplicate Stripe session IDs do not create duplicate signups."""
    client, factory = setup

    event_payload = {
        "id": "evt_test_456",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_dup",
                "customer_details": {"email": "dup@example.com"},
                "amount_total": 1000,
                "payment_status": "paid",
                "metadata": {"experiment": "ten_dollar_list"},
            }
        },
    }
    payload_bytes = json.dumps(event_payload).encode()
    stripe_signature = _sign_payload(payload_bytes)

    with patch("margin_api.routes.experiment.EmailService") as mock_email_cls:
        mock_email = MagicMock()
        mock_email.send_custom.return_value = True
        mock_email_cls.return_value = mock_email

        with patch("margin_api.routes.experiment.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = event_payload
            mock_stripe.SignatureVerificationError = Exception

            # First call — should succeed
            response1 = await client.post(
                "/api/v1/experiment/webhook",
                content=payload_bytes,
                headers={
                    "stripe-signature": stripe_signature,
                    "content-type": "application/json",
                },
            )
            assert response1.status_code == 200
            assert response1.json()["status"] == "ok"

            # Second call with same session ID — should be idempotent
            response2 = await client.post(
                "/api/v1/experiment/webhook",
                content=payload_bytes,
                headers={
                    "stripe-signature": stripe_signature,
                    "content-type": "application/json",
                },
            )
            assert response2.status_code == 200
            assert response2.json()["status"] == "already_processed"

    # Verify only one signup exists
    async with factory() as session:
        result = await session.execute(
            select(ExperimentSignup).where(
                ExperimentSignup.stripe_session_id == "cs_test_dup"
            )
        )
        signups = result.scalars().all()
        assert len(signups) == 1


@pytest.mark.asyncio
async def test_webhook_ignores_non_experiment_events(setup):
    """Webhook ignores checkout sessions without experiment metadata."""
    client, factory = setup

    event_payload = {
        "id": "evt_test_789",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_other",
                "customer_details": {"email": "other@example.com"},
                "amount_total": 2900,
                "payment_status": "paid",
                "metadata": {},
            }
        },
    }
    payload_bytes = json.dumps(event_payload).encode()
    stripe_signature = _sign_payload(payload_bytes)

    with patch("margin_api.routes.experiment.stripe") as mock_stripe:
        mock_stripe.Webhook.construct_event.return_value = event_payload
        mock_stripe.SignatureVerificationError = Exception

        response = await client.post(
            "/api/v1/experiment/webhook",
            content=payload_bytes,
            headers={
                "stripe-signature": stripe_signature,
                "content-type": "application/json",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

    # No signup created
    async with factory() as session:
        result = await session.execute(select(ExperimentSignup))
        assert result.scalars().all() == []
