"""Tests for token bucket rate limiter."""

import threading
import time
from unittest.mock import patch

import pytest
from margin_engine.ingestion.rate_limiter import RateLimiter, RateLimiterRegistry


class TestRateLimiterInit:
    def test_initial_tokens_equal_requests_per_minute(self):
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.tokens_available == 60

    def test_initial_tokens_custom_value(self):
        limiter = RateLimiter(requests_per_minute=120)
        assert limiter.tokens_available == 120


class TestRateLimiterAcquire:
    def test_acquire_succeeds_when_tokens_available(self):
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.acquire() is True

    def test_acquire_decrements_tokens(self):
        limiter = RateLimiter(requests_per_minute=60)
        limiter.acquire()
        assert limiter.tokens_available == 59

    def test_acquire_fails_when_tokens_exhausted(self):
        limiter = RateLimiter(requests_per_minute=2)
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        assert limiter.acquire() is False

    def test_acquire_returns_false_not_raises(self):
        limiter = RateLimiter(requests_per_minute=1)
        limiter.acquire()
        result = limiter.acquire()
        assert result is False


class TestTokensAvailable:
    def test_tokens_available_reflects_current_state(self):
        limiter = RateLimiter(requests_per_minute=5)
        assert limiter.tokens_available == 5
        limiter.acquire()
        assert limiter.tokens_available == 4
        limiter.acquire()
        assert limiter.tokens_available == 3

    def test_tokens_available_never_negative(self):
        limiter = RateLimiter(requests_per_minute=1)
        limiter.acquire()
        limiter.acquire()  # Should fail, but tokens should not go negative
        assert limiter.tokens_available >= 0


class TestTokenRefill:
    def test_tokens_refill_over_time(self):
        """Use a high rate so refill is observable over a short sleep."""
        limiter = RateLimiter(requests_per_minute=6000)
        # Drain all tokens
        for _ in range(6000):
            limiter.acquire()
        assert limiter.tokens_available == 0

        # At 6000/min = 100/sec, sleeping 0.05s should refill ~5 tokens
        time.sleep(0.05)
        # Access triggers refill calculation
        available = limiter.tokens_available
        assert available >= 3  # Allow some timing slack
        assert available <= 10  # But not too many

    def test_tokens_refill_capped_at_max(self):
        """Tokens should never exceed requests_per_minute."""
        limiter = RateLimiter(requests_per_minute=10)
        # Don't acquire anything, just wait
        time.sleep(0.1)
        assert limiter.tokens_available == 10  # Capped at max

    def test_refill_uses_monotonic_time(self):
        """Verify the limiter uses time.monotonic, not time.time."""
        with patch("margin_engine.ingestion.rate_limiter.time.monotonic") as mock_mono:
            mock_mono.return_value = 1000.0
            limiter = RateLimiter(requests_per_minute=60)

            # Drain one token
            limiter.acquire()
            assert limiter.tokens_available == 59

            # Advance mock time by 1 second (should refill 1 token at 60/min)
            mock_mono.return_value = 1001.0
            assert limiter.tokens_available == 60  # Refilled to max


class TestWaitAndAcquire:
    def test_wait_and_acquire_returns_immediately_when_available(self):
        limiter = RateLimiter(requests_per_minute=60)
        start = time.monotonic()
        limiter.wait_and_acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # Should be near-instant

    def test_wait_and_acquire_blocks_until_token_available(self):
        """Mock time to verify wait_and_acquire sleeps then acquires."""
        with patch("margin_engine.ingestion.rate_limiter.time") as mock_time:
            clock = 1000.0

            def monotonic():
                return clock

            mock_time.monotonic = monotonic
            mock_time.sleep = lambda _secs: None  # no-op during init

            limiter = RateLimiter(requests_per_minute=60)  # 1 token/sec

            # Drain all tokens
            for _ in range(60):
                limiter.acquire()
            assert limiter.tokens_available == 0

            sleep_calls: list[float] = []

            def fake_sleep(secs: float) -> None:
                nonlocal clock
                sleep_calls.append(secs)
                # Advance the mock clock by the sleep duration
                clock += secs

            mock_time.sleep = fake_sleep

            limiter.wait_and_acquire()

            # Should have slept at least once
            assert len(sleep_calls) >= 1
            # The total sleep should be ~1 second (1 token / 1 token-per-sec)
            assert sum(sleep_calls) == pytest.approx(1.0, abs=0.1)
            # Token was consumed: still at 0 after acquiring the single refilled token
            assert limiter.tokens_available == 0

    def test_wait_and_acquire_consumes_token(self):
        limiter = RateLimiter(requests_per_minute=10)
        initial = limiter.tokens_available
        limiter.wait_and_acquire()
        assert limiter.tokens_available == initial - 1


class TestThreadSafety:
    def test_concurrent_acquire_does_not_over_allocate(self):
        """Multiple threads acquiring should not exceed the token limit."""
        limiter = RateLimiter(requests_per_minute=100)
        successes = []
        lock = threading.Lock()

        def try_acquire():
            result = limiter.acquire()
            with lock:
                successes.append(result)

        threads = [threading.Thread(target=try_acquire) for _ in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 100 should succeed (the initial token count)
        success_count = sum(1 for s in successes if s)
        assert success_count == 100
        fail_count = sum(1 for s in successes if not s)
        assert fail_count == 100


class TestRateLimiterRegistry:
    def test_register_and_get(self):
        registry = RateLimiterRegistry()
        registry.register("polygon", 300)
        limiter = registry.get("polygon")
        assert isinstance(limiter, RateLimiter)
        assert limiter.tokens_available == 300

    def test_get_unknown_provider_raises_key_error(self):
        registry = RateLimiterRegistry()
        with pytest.raises(KeyError, match="unknown_provider"):
            registry.get("unknown_provider")

    def test_acquire_delegates_to_provider_limiter(self):
        registry = RateLimiterRegistry()
        registry.register("sec_edgar", 10)
        assert registry.acquire("sec_edgar") is True
        # Verify token was consumed
        limiter = registry.get("sec_edgar")
        assert limiter.tokens_available == 9

    def test_acquire_unknown_provider_raises_key_error(self):
        registry = RateLimiterRegistry()
        with pytest.raises(KeyError):
            registry.acquire("nonexistent")

    def test_multiple_providers_independent(self):
        registry = RateLimiterRegistry()
        registry.register("provider_a", 5)
        registry.register("provider_b", 10)

        # Exhaust provider_a
        for _ in range(5):
            registry.acquire("provider_a")
        assert registry.acquire("provider_a") is False

        # provider_b should still have tokens
        assert registry.acquire("provider_b") is True
        assert registry.get("provider_b").tokens_available == 9

    def test_register_overwrites_existing(self):
        registry = RateLimiterRegistry()
        registry.register("polygon", 100)
        registry.acquire("polygon")  # consume one
        assert registry.get("polygon").tokens_available == 99

        # Re-register should create a fresh limiter
        registry.register("polygon", 200)
        assert registry.get("polygon").tokens_available == 200
