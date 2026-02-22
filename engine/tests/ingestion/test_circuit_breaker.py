"""Tests for circuit breaker provider health tracking."""

import time
from unittest.mock import patch

from margin_engine.ingestion.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitState:
    def test_closed_value(self):
        assert CircuitState.CLOSED == "closed"

    def test_open_value(self):
        assert CircuitState.OPEN == "open"

    def test_half_open_value(self):
        assert CircuitState.HALF_OPEN == "half_open"

    def test_is_str_enum(self):
        assert isinstance(CircuitState.CLOSED, str)


class TestCircuitBreakerInit:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_default_failure_threshold(self):
        cb = CircuitBreaker()
        assert cb.failure_threshold == 10

    def test_default_cooldown_seconds(self):
        cb = CircuitBreaker()
        assert cb.cooldown_seconds == 900.0

    def test_custom_failure_threshold(self):
        cb = CircuitBreaker(failure_threshold=5)
        assert cb.failure_threshold == 5

    def test_custom_cooldown_seconds(self):
        cb = CircuitBreaker(cooldown_seconds=60.0)
        assert cb.cooldown_seconds == 60.0


class TestAllowRequest:
    def test_allowed_when_closed(self):
        cb = CircuitBreaker()
        assert cb.allow_request() is True

    def test_blocked_when_open(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False


class TestRecordFailure:
    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_opens_at_threshold(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestRecordSuccess:
    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        cb.record_success()
        # After reset, we should need another full 5 failures to trip
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED


class TestHalfOpen:
    def test_half_open_after_cooldown(self):
        """After the cooldown period, the breaker transitions to HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_allows_one_probe(self):
        """In HALF_OPEN state, allow_request returns True for a single probe."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True

    def test_probe_success_closes_breaker(self):
        """A successful probe in HALF_OPEN transitions back to CLOSED."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.allow_request()  # probe allowed
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_probe_failure_reopens_breaker(self):
        """A failed probe in HALF_OPEN transitions back to OPEN."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.allow_request()  # probe allowed
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_blocks_second_request(self):
        """In HALF_OPEN, only the first probe is allowed; further requests are blocked."""
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()

        time.sleep(0.15)
        assert cb.allow_request() is True  # first probe
        assert cb.allow_request() is False  # second should be blocked


class TestHalfOpenMocked:
    def test_half_open_after_cooldown_mocked(self):
        """Use mocked time to verify half-open transition without real sleeps."""
        with patch("margin_engine.ingestion.circuit_breaker.time.monotonic") as mock_mono:
            mock_mono.return_value = 1000.0
            cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=900.0)

            for _ in range(3):
                cb.record_failure()
            assert cb.state == CircuitState.OPEN

            # Advance time past cooldown
            mock_mono.return_value = 1901.0
            assert cb.state == CircuitState.HALF_OPEN


class TestThreadSafety:
    def test_concurrent_failures_trip_exactly_once(self):
        """Many threads recording failures should trip the breaker deterministically."""
        import threading

        cb = CircuitBreaker(failure_threshold=10)
        barrier = threading.Barrier(20)

        def record():
            barrier.wait()
            cb.record_failure()

        threads = [threading.Thread(target=record) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should be open after 20 failures (well past threshold of 10)
        assert cb.state == CircuitState.OPEN

    def test_concurrent_allow_request_when_closed(self):
        """All threads should be allowed when breaker is closed."""
        import threading

        cb = CircuitBreaker(failure_threshold=10)
        results = []
        lock = threading.Lock()

        def check():
            result = cb.allow_request()
            with lock:
                results.append(result)

        threads = [threading.Thread(target=check) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)
        assert len(results) == 50
