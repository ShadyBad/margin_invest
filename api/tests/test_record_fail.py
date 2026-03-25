"""Tests for _record_fail tiered logging and MAX_PRICE_FAIL_COUNT constant."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest
from margin_api.workers import MAX_PRICE_FAIL_COUNT, _record_fail


class TestMaxPriceFailCount:
    """Verify the module-level constant is 3."""

    def test_constant_value(self):
        assert MAX_PRICE_FAIL_COUNT == 3


class TestRecordFailTieredLogging:
    """Verify _record_fail uses WARNING on first failure and at threshold, DEBUG in between."""

    @pytest.mark.asyncio
    async def test_first_failure_logs_warning(self, caplog):
        """First failure (count=1) should log at WARNING level."""
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=1)
        redis.expire = AsyncMock()

        with caplog.at_level(logging.DEBUG, logger="margin_api.workers"):
            await _record_fail(redis, "AAPL")

        warning_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("AAPL" in m.message and "count=1" in m.message for m in warning_msgs)

    @pytest.mark.asyncio
    async def test_intermediate_failure_logs_debug(self, caplog):
        """Intermediate failure (1 < count < threshold) should log at DEBUG level."""
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=2)
        redis.ttl = AsyncMock(return_value=86000)

        with caplog.at_level(logging.DEBUG, logger="margin_api.workers"):
            await _record_fail(redis, "TGNA")

        debug_msgs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        warning_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("TGNA" in m.message for m in debug_msgs)
        assert not any("TGNA" in m.message for m in warning_msgs)

    @pytest.mark.asyncio
    async def test_threshold_failure_logs_warning(self, caplog):
        """Failure at quarantine threshold should log at WARNING level."""
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=MAX_PRICE_FAIL_COUNT)
        redis.ttl = AsyncMock(return_value=86000)

        with caplog.at_level(logging.DEBUG, logger="margin_api.workers"):
            await _record_fail(redis, "RAPT")

        warning_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("RAPT" in m.message and "quarantine" in m.message for m in warning_msgs)
