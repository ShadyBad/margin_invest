"""Token bucket rate limiter for API call throttling.

Provides per-provider rate limiting with configurable requests-per-minute
and thread-safe token bucket implementation.
"""

import math
import threading
import time


class RateLimiter:
    """Token bucket rate limiter.

    Allows up to ``requests_per_minute`` API calls per minute, refilling
    tokens at a steady rate.  Thread-safe via :class:`threading.Lock`.
    """

    def __init__(self, requests_per_minute: int) -> None:
        """Create a rate limiter with the given requests/minute limit.

        Args:
            requests_per_minute: Maximum number of requests allowed per minute.
        """
        self._max_tokens: float = float(requests_per_minute)
        self._tokens: float = self._max_tokens
        self._refill_rate: float = requests_per_minute / 60.0  # tokens per second
        self._last_refill: float = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill.

        Must be called while holding ``self._lock``.
        """
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self._refill_rate
        self._tokens = min(self._max_tokens, self._tokens + new_tokens)
        self._last_refill = now

    def acquire(self) -> bool:
        """Try to acquire a token.

        Returns:
            True if a token was acquired, False if rate limited.
        """
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def wait_and_acquire(self) -> None:
        """Block until a token is available, then acquire it."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                # Calculate how long until at least 1 token is available
                deficit = 1.0 - self._tokens
                wait_seconds = deficit / self._refill_rate
            time.sleep(wait_seconds)

    @property
    def tokens_available(self) -> int:
        """Current number of available tokens (rounded down)."""
        with self._lock:
            self._refill()
            return math.floor(self._tokens)


class RateLimiterRegistry:
    """Registry of :class:`RateLimiter` instances keyed by provider name.

    Thread-safe: the internal dict is protected by a lock so that
    concurrent ``register`` / ``get`` / ``acquire`` calls are safe.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._limiters: dict[str, RateLimiter] = {}
        self._lock = threading.Lock()

    def register(self, provider_name: str, requests_per_minute: int) -> None:
        """Register (or replace) a rate limiter for *provider_name*.

        Args:
            provider_name: Identifier for the data provider.
            requests_per_minute: Maximum requests per minute for this provider.
        """
        limiter = RateLimiter(requests_per_minute)
        with self._lock:
            self._limiters[provider_name] = limiter

    def get(self, provider_name: str) -> RateLimiter:
        """Return the rate limiter for *provider_name*.

        Raises:
            KeyError: If the provider has not been registered.
        """
        with self._lock:
            try:
                return self._limiters[provider_name]
            except KeyError:
                raise KeyError(provider_name) from None

    def acquire(self, provider_name: str) -> bool:
        """Try to acquire a token for *provider_name*.

        Delegates to :meth:`RateLimiter.acquire` on the corresponding limiter.

        Raises:
            KeyError: If the provider has not been registered.
        """
        return self.get(provider_name).acquire()
