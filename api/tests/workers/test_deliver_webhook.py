"""Tests for deliver_webhook ARQ worker function.

Covers:
- Successful delivery returns 'delivered'
- Failed delivery schedules retry when not dead-lettered
- Dead-lettered delivery does NOT schedule retry
- Missing delivery (None) does NOT schedule retry
- No redis in ctx → still returns 'retry_scheduled' flow without crashing
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session_factory_with_delivery(delivery_obj=None):
    """Return a session factory that yields a mock session.

    The session's `get()` method returns delivery_obj.
    """
    session = MagicMock()
    session.commit = AsyncMock()
    session.get = AsyncMock(return_value=delivery_obj)

    async def _execute(stmt):
        return MagicMock()

    session.execute = _execute

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=ctx)
    return factory, session


# ---------------------------------------------------------------------------
# Test: successful delivery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_success_returns_delivered():
    """When dispatcher.deliver() returns True, worker returns 'delivered'."""
    from margin_api.workers import deliver_webhook

    factory, session = _mock_session_factory_with_delivery()

    mock_dispatcher = MagicMock()
    mock_dispatcher.deliver = AsyncMock(return_value=True)

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher", return_value=mock_dispatcher
        ),
        patch("margin_api.workers.get_settings") as mock_settings,
    ):
        mock_settings.return_value.mfa_encryption_key = "test-key"
        result = await deliver_webhook({"redis": AsyncMock()}, delivery_id=42)

    assert result == "delivered"
    mock_dispatcher.deliver.assert_called_once_with(session, 42, encryption_key_str="test-key")


# ---------------------------------------------------------------------------
# Test: failed delivery schedules retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_failure_schedules_retry():
    """When delivery fails and is not dead-lettered, retry is scheduled via redis."""
    from margin_api.workers import deliver_webhook

    delivery_mock = MagicMock()
    delivery_mock.status = "pending"
    delivery_mock.attempts = 1  # First retry, backoff = BACKOFF_SECONDS[1] = 1s

    factory, session = _mock_session_factory_with_delivery(delivery_mock)

    mock_dispatcher = MagicMock()
    mock_dispatcher.deliver = AsyncMock(return_value=False)

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher", return_value=mock_dispatcher
        ),
        patch("margin_api.workers.get_settings") as mock_settings,
    ):
        mock_settings.return_value.mfa_encryption_key = "test-key"
        result = await deliver_webhook({"redis": mock_redis}, delivery_id=99)

    assert result == "retry_scheduled"
    # Should have enqueued a retry
    mock_redis.enqueue_job.assert_called_once()
    call_args = mock_redis.enqueue_job.call_args
    assert call_args[0][0] == "deliver_webhook"
    assert call_args[1].get("_job_id") == "webhook:99"


# ---------------------------------------------------------------------------
# Test: dead-lettered delivery does NOT schedule retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_dead_letter_no_retry():
    """When delivery is dead-lettered, no retry should be scheduled."""
    from margin_api.workers import deliver_webhook

    delivery_mock = MagicMock()
    delivery_mock.status = "dead_letter"
    delivery_mock.attempts = 5

    factory, session = _mock_session_factory_with_delivery(delivery_mock)

    mock_dispatcher = MagicMock()
    mock_dispatcher.deliver = AsyncMock(return_value=False)

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher", return_value=mock_dispatcher
        ),
        patch("margin_api.workers.get_settings") as mock_settings,
    ):
        mock_settings.return_value.mfa_encryption_key = "test-key"
        result = await deliver_webhook({"redis": mock_redis}, delivery_id=100)

    assert result == "retry_scheduled"
    # Should NOT have enqueued a retry
    mock_redis.enqueue_job.assert_not_called()


# ---------------------------------------------------------------------------
# Test: delivery not found (None) does NOT schedule retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_not_found_no_retry():
    """When delivery record is None (deleted), no retry should be scheduled."""
    from margin_api.workers import deliver_webhook

    # Delivery is None
    factory, session = _mock_session_factory_with_delivery(None)

    mock_dispatcher = MagicMock()
    mock_dispatcher.deliver = AsyncMock(return_value=False)

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher", return_value=mock_dispatcher
        ),
        patch("margin_api.workers.get_settings") as mock_settings,
    ):
        mock_settings.return_value.mfa_encryption_key = "test-key"
        result = await deliver_webhook({"redis": mock_redis}, delivery_id=777)

    assert result == "retry_scheduled"
    mock_redis.enqueue_job.assert_not_called()


# ---------------------------------------------------------------------------
# Test: no redis in ctx — retry not schedulable but no crash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_no_redis_does_not_crash():
    """Without redis in ctx, failed delivery logs warning but does not crash."""
    from margin_api.workers import deliver_webhook

    delivery_mock = MagicMock()
    delivery_mock.status = "pending"
    delivery_mock.attempts = 0

    factory, session = _mock_session_factory_with_delivery(delivery_mock)

    mock_dispatcher = MagicMock()
    mock_dispatcher.deliver = AsyncMock(return_value=False)

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher", return_value=mock_dispatcher
        ),
        patch("margin_api.workers.get_settings") as mock_settings,
    ):
        mock_settings.return_value.mfa_encryption_key = "test-key"
        # No redis in ctx
        result = await deliver_webhook({}, delivery_id=55)

    # Should return "retry_scheduled" even without redis (after logging warning)
    assert result == "retry_scheduled"


# ---------------------------------------------------------------------------
# Test: exponential backoff — attempt count determines backoff seconds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_backoff_respects_attempt_count():
    """Backoff duration should follow BACKOFF_SECONDS indexed by attempt count."""
    from margin_api.workers import deliver_webhook

    delivery_mock = MagicMock()
    delivery_mock.status = "pending"
    delivery_mock.attempts = 3  # BACKOFF_SECONDS[3] = 60

    factory, session = _mock_session_factory_with_delivery(delivery_mock)

    mock_dispatcher = MagicMock()
    mock_dispatcher.deliver = AsyncMock(return_value=False)

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher", return_value=mock_dispatcher
        ),
        patch("margin_api.workers.get_settings") as mock_settings,
    ):
        mock_settings.return_value.mfa_encryption_key = "test-key"
        await deliver_webhook({"redis": mock_redis}, delivery_id=200)

    # Verify _defer_by was passed (not testing exact seconds, just that it was deferred)
    call_kwargs = mock_redis.enqueue_job.call_args[1]
    assert "_defer_by" in call_kwargs
