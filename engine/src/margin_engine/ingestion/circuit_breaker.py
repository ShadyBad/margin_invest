"""Circuit breaker for provider health tracking.

Prevents wasting API calls on a provider that is consistently failing
(e.g., IP-blocked, outage).  Implements the standard three-state model:

- **CLOSED** (normal): requests flow through.
- **OPEN** (tripped): all requests are blocked after *N* consecutive failures.
- **HALF_OPEN**: after a cooldown period, one probe request is allowed.
  If it succeeds the breaker closes; if it fails the breaker re-opens.
"""

import enum
import threading
import time


class CircuitState(enum.StrEnum):
    """State of a :class:`CircuitBreaker`."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-provider circuit breaker.

    Thread-safe via :class:`threading.Lock`.

    Args:
        failure_threshold: Number of consecutive failures before the breaker
            trips from CLOSED to OPEN.  Default ``10``.
        cooldown_seconds: Seconds the breaker stays OPEN before transitioning
            to HALF_OPEN and allowing a single probe request.  Default ``900.0``
            (15 minutes).
    """

    def __init__(
        self,
        failure_threshold: int = 10,
        cooldown_seconds: float = 900.0,
    ) -> None:
        self.failure_threshold: int = failure_threshold
        self.cooldown_seconds: float = cooldown_seconds

        self._state: CircuitState = CircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._opened_at: float = 0.0
        self._probe_sent: bool = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Current circuit breaker state.

        If the breaker is OPEN and the cooldown has elapsed, the state
        automatically transitions to HALF_OPEN.
        """
        with self._lock:
            return self._effective_state()

    def allow_request(self) -> bool:
        """Check whether a request should be allowed through the breaker.

        Returns:
            ``True`` if the request is allowed, ``False`` otherwise.
        """
        with self._lock:
            effective = self._effective_state()
            if effective == CircuitState.CLOSED:
                return True
            if effective == CircuitState.HALF_OPEN:
                if not self._probe_sent:
                    self._probe_sent = True
                    return True
                return False
            # OPEN
            return False

    def record_success(self) -> None:
        """Record a successful request.

        Resets the consecutive failure counter.  If the breaker is in
        HALF_OPEN state the probe succeeded, so transition back to CLOSED.
        """
        with self._lock:
            self._consecutive_failures = 0
            if self._effective_state() in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                self._state = CircuitState.CLOSED
                self._probe_sent = False

    def record_failure(self) -> None:
        """Record a failed request.

        Increments the consecutive failure counter and may trip the breaker.
        If the breaker is in HALF_OPEN state the probe failed, so
        transition back to OPEN with a fresh cooldown.
        """
        with self._lock:
            effective = self._effective_state()
            if effective == CircuitState.HALF_OPEN:
                # Probe failed -- re-open with fresh cooldown
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                self._probe_sent = False
                return
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                self._probe_sent = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _effective_state(self) -> CircuitState:
        """Return the effective state, promoting OPEN -> HALF_OPEN when due.

        Must be called while holding ``self._lock``.
        """
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
                self._probe_sent = False
        return self._state
