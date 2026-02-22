"""Tests for retry logic."""

from __future__ import annotations

import pytest
from margin_api.services.retry import with_retry


class TestWithRetry:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        call_count = 0

        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await with_retry(succeed, ticker="TEST")
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        call_count = 0

        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "recovered"

        result = await with_retry(fail_then_succeed, ticker="TEST", retries=3, base_delay=0.01)
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        def always_fail():
            raise ValueError("permanent error")

        with pytest.raises(ValueError, match="permanent error"):
            await with_retry(always_fail, ticker="TEST", retries=2, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_delay_is_exponential(self):
        """Verify delay doubles between retries."""
        import time

        call_times = []

        def track_and_fail():
            call_times.append(time.monotonic())
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await with_retry(track_and_fail, ticker="TEST", retries=3, base_delay=0.05)

        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        assert delay2 > delay1 * 1.5  # allow tolerance
