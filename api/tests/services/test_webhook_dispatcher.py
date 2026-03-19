"""Tests for WebhookDispatcher — HMAC signing, dispatch, and delivery."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from margin_api.db.base import Base
from margin_api.db.models import GovernanceEvent, WebhookDelivery, WebhookSubscription
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
def fernet_key() -> bytes:
    return Fernet.generate_key()


@pytest.fixture
def encryption_key_str(fernet_key) -> str:
    return fernet_key.decode()


@pytest.fixture
def hmac_key_plaintext() -> str:
    return "my-super-secret-hmac-key"


@pytest.fixture
def encrypted_hmac_key(fernet_key, hmac_key_plaintext) -> str:
    fernet = Fernet(fernet_key)
    return fernet.encrypt(hmac_key_plaintext.encode()).decode()


@pytest_asyncio.fixture
async def active_subscription(session, encrypted_hmac_key) -> WebhookSubscription:
    sub = WebhookSubscription(
        event_type="score.published",
        url="https://example.com/hooks/score",
        hmac_key_encrypted=encrypted_hmac_key,
        is_active=True,
        created_by=1,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


@pytest_asyncio.fixture
async def inactive_subscription(session, encrypted_hmac_key) -> WebhookSubscription:
    sub = WebhookSubscription(
        event_type="score.published",
        url="https://example.com/hooks/inactive",
        hmac_key_encrypted=encrypted_hmac_key,
        is_active=False,
        created_by=1,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


# ---------------------------------------------------------------------------
# _sign_payload tests
# ---------------------------------------------------------------------------


class TestSignPayload:
    def test_returns_64_char_hex(self):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        sig = dispatcher._sign_payload(b"hello world", "secret-key")
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_deterministic_same_inputs(self):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        payload = b'{"event": "test"}'
        sig1 = dispatcher._sign_payload(payload, "my-key")
        sig2 = dispatcher._sign_payload(payload, "my-key")
        assert sig1 == sig2

    def test_different_keys_produce_different_sigs(self):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        payload = b'{"event": "test"}'
        sig1 = dispatcher._sign_payload(payload, "key-one")
        sig2 = dispatcher._sign_payload(payload, "key-two")
        assert sig1 != sig2

    def test_different_payloads_produce_different_sigs(self):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        sig1 = dispatcher._sign_payload(b"payload-a", "same-key")
        sig2 = dispatcher._sign_payload(b"payload-b", "same-key")
        assert sig1 != sig2


# ---------------------------------------------------------------------------
# dispatch tests
# ---------------------------------------------------------------------------


class TestDispatch:
    @pytest.mark.asyncio
    async def test_creates_delivery_for_active_subscriber(self, session, active_subscription):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        payload = {"ticker": "AAPL", "score": 88}
        delivery_ids = await dispatcher.dispatch(session, "score.published", payload)

        assert len(delivery_ids) == 1
        delivery = await session.get(WebhookDelivery, delivery_ids[0])
        assert delivery is not None
        assert delivery.status == "pending"
        assert delivery.event_type == "score.published"
        assert delivery.subscription_id == active_subscription.id
        assert delivery.payload == payload

    @pytest.mark.asyncio
    async def test_skips_inactive_subscriber(self, session, inactive_subscription):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        delivery_ids = await dispatcher.dispatch(session, "score.published", {"x": 1})
        assert delivery_ids == []

    @pytest.mark.asyncio
    async def test_creates_deliveries_for_multiple_active_subscribers(
        self, session, encrypted_hmac_key
    ):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        for i in range(3):
            sub = WebhookSubscription(
                event_type="score.published",
                url=f"https://example.com/hook/{i}",
                hmac_key_encrypted=encrypted_hmac_key,
                is_active=True,
                created_by=1,
            )
            session.add(sub)
        await session.commit()

        dispatcher = WebhookDispatcher()
        delivery_ids = await dispatcher.dispatch(session, "score.published", {"x": 1})
        assert len(delivery_ids) == 3

    @pytest.mark.asyncio
    async def test_only_dispatches_matching_event_type(
        self, session, active_subscription, encrypted_hmac_key
    ):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        other_sub = WebhookSubscription(
            event_type="model.promoted",
            url="https://example.com/hook/model",
            hmac_key_encrypted=encrypted_hmac_key,
            is_active=True,
            created_by=1,
        )
        session.add(other_sub)
        await session.commit()

        dispatcher = WebhookDispatcher()
        delivery_ids = await dispatcher.dispatch(session, "score.published", {"x": 1})
        # Only the score.published subscription should get a delivery
        assert len(delivery_ids) == 1

        delivery = await session.get(WebhookDelivery, delivery_ids[0])
        assert delivery.subscription_id == active_subscription.id

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_subscribers(self, session):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        delivery_ids = await dispatcher.dispatch(session, "no.subscribers", {"x": 1})
        assert delivery_ids == []


# ---------------------------------------------------------------------------
# deliver tests
# ---------------------------------------------------------------------------


class TestDeliver:
    @pytest.mark.asyncio
    async def test_successful_delivery_updates_status(
        self, session, active_subscription, encryption_key_str
    ):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        payload = {"ticker": "AAPL"}
        delivery = WebhookDelivery(
            subscription_id=active_subscription.id,
            event_type="score.published",
            payload=payload,
            status="pending",
            attempts=0,
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await dispatcher.deliver(session, delivery.id, encryption_key_str)

        assert result is True
        await session.refresh(delivery)
        assert delivery.status == "delivered"
        assert delivery.delivered_at is not None
        assert delivery.attempts == 1

    @pytest.mark.asyncio
    async def test_failed_delivery_increments_attempts(
        self, session, active_subscription, encryption_key_str
    ):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        delivery = WebhookDelivery(
            subscription_id=active_subscription.id,
            event_type="score.published",
            payload={"x": 1},
            status="pending",
            attempts=0,
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value = mock_client

            result = await dispatcher.deliver(session, delivery.id, encryption_key_str)

        assert result is False
        await session.refresh(delivery)
        assert delivery.attempts == 1
        assert delivery.last_error is not None
        assert delivery.status == "pending"

    @pytest.mark.asyncio
    async def test_fifth_failure_sets_dead_letter(
        self, session, active_subscription, encryption_key_str
    ):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        delivery = WebhookDelivery(
            subscription_id=active_subscription.id,
            event_type="score.published",
            payload={"x": 1},
            status="pending",
            attempts=4,  # 4 previous failures, this is the 5th attempt
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value = mock_client

            result = await dispatcher.deliver(session, delivery.id, encryption_key_str)

        assert result is False
        await session.refresh(delivery)
        assert delivery.status == "dead_letter"
        assert delivery.attempts == 5

    @pytest.mark.asyncio
    async def test_dead_letter_creates_governance_event(
        self, session, active_subscription, encryption_key_str
    ):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        delivery = WebhookDelivery(
            subscription_id=active_subscription.id,
            event_type="score.published",
            payload={"x": 1},
            status="pending",
            attempts=4,
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value = mock_client

            await dispatcher.deliver(session, delivery.id, encryption_key_str)

        events = (await session.execute(select(GovernanceEvent))).scalars().all()
        assert len(events) == 1
        assert events[0].event_type == "webhook.dead_letter"

    @pytest.mark.asyncio
    async def test_skip_already_delivered(self, session, active_subscription, encryption_key_str):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        delivery = WebhookDelivery(
            subscription_id=active_subscription.id,
            event_type="score.published",
            payload={"x": 1},
            status="delivered",
            attempts=1,
            delivered_at=datetime.now(UTC),
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await dispatcher.deliver(session, delivery.id, encryption_key_str)

        # Should skip without making HTTP call
        assert result is False
        mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_dead_letter(self, session, active_subscription, encryption_key_str):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        delivery = WebhookDelivery(
            subscription_id=active_subscription.id,
            event_type="score.published",
            payload={"x": 1},
            status="dead_letter",
            attempts=5,
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock()
            mock_client_cls.return_value = mock_client

            result = await dispatcher.deliver(session, delivery.id, encryption_key_str)

        assert result is False
        mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_posts_correct_headers(self, session, active_subscription, encryption_key_str):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        payload = {"ticker": "MSFT", "score": 75}
        delivery = WebhookDelivery(
            subscription_id=active_subscription.id,
            event_type="score.published",
            payload=payload,
            status="pending",
            attempts=0,
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        captured_kwargs: dict = {}

        async def capture_post(url, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = capture_post
            mock_client_cls.return_value = mock_client

            await dispatcher.deliver(session, delivery.id, encryption_key_str)

        headers = captured_kwargs.get("headers", {})
        assert headers.get("Content-Type") == "application/json"
        assert "X-Margin-Signature" in headers
        assert headers.get("X-Margin-Event") == "score.published"
        # Signature should be a 64-char hex string
        assert len(headers["X-Margin-Signature"]) == 64

    @pytest.mark.asyncio
    async def test_records_last_status_code_on_http_error(
        self, session, active_subscription, encryption_key_str
    ):
        from margin_api.services.webhook_dispatcher import WebhookDispatcher

        dispatcher = WebhookDispatcher()
        delivery = WebhookDelivery(
            subscription_id=active_subscription.id,
            event_type="score.published",
            payload={"x": 1},
            status="pending",
            attempts=0,
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)

        mock_response = MagicMock()
        mock_response.status_code = 500

        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server Error",
                    request=MagicMock(),
                    response=mock_response,
                )
            )
            mock_client_cls.return_value = mock_client

            result = await dispatcher.deliver(session, delivery.id, encryption_key_str)

        assert result is False
        await session.refresh(delivery)
        assert delivery.last_status_code == 500
        assert delivery.last_error is not None
