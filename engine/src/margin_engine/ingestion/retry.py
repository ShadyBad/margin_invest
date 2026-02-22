"""Retry decorator for transient provider failures.

Wraps provider fetch methods to automatically retry on transient errors
(timeouts, rate limits, server errors) with exponential backoff.
Non-transient errors (permanent, data unavailable) are returned immediately.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from margin_engine.ingestion.types import DataCategory, FetchResult

# Keywords in error messages that indicate transient failures (case-insensitive).
_TRANSIENT_KEYWORDS: tuple[str, ...] = (
    "429",
    "rate limit",
    "too many requests",
    "500",
    "502",
    "503",
    "timeout",
    "timed out",
)

# Exception types that are considered transient and should trigger a retry.
_TRANSIENT_EXCEPTIONS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
    OSError,
)


def _is_transient_error(error_message: str) -> bool:
    """Return True if the error message contains a transient keyword."""
    lowered = error_message.lower()
    return any(keyword in lowered for keyword in _TRANSIENT_KEYWORDS)


def retry_transient(
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> Callable[[Callable[..., FetchResult]], Callable[..., FetchResult]]:
    """Decorator that retries functions returning FetchResult on transient failures.

    Args:
        max_retries: Maximum number of retry attempts after the initial call.
        base_delay: Base delay in seconds for exponential backoff.
            Backoff formula: ``base_delay * (2 ** attempt)``.

    Returns:
        A decorator that wraps fetch functions with retry logic.
    """

    def decorator(fn: Callable[..., FetchResult]) -> Callable[..., FetchResult]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> FetchResult:
            last_result: FetchResult | None = None

            for attempt in range(max_retries + 1):
                # Sleep before retries (not before the first attempt).
                if attempt > 0 and base_delay > 0:
                    time.sleep(base_delay * (2 ** (attempt - 1)))

                try:
                    result = fn(*args, **kwargs)
                except _TRANSIENT_EXCEPTIONS as exc:
                    # Transient exception — build an error result and retry.
                    last_result = FetchResult(
                        provider_name="unknown",
                        category=DataCategory.FUNDAMENTALS,
                        ticker=args[0] if args else "",
                        raw_data={},
                        fetched_at="",
                        success=False,
                        error=str(exc),
                    )
                    continue
                except Exception as exc:
                    # Non-transient exception — return immediately, no retry.
                    return FetchResult(
                        provider_name="unknown",
                        category=DataCategory.FUNDAMENTALS,
                        ticker=args[0] if args else "",
                        raw_data={},
                        fetched_at="",
                        success=False,
                        error=str(exc),
                    )

                if result.success:
                    return result

                last_result = result

                # Non-transient error in the result — return immediately.
                if result.error and not _is_transient_error(result.error):
                    return result

                # Transient error — loop will retry.

            # Exhausted all retries — return the last failed result.
            assert last_result is not None
            return last_result

        return wrapper

    return decorator
