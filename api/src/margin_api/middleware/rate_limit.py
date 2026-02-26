"""Rate limiting middleware using slowapi + Redis.

The module-level ``limiter`` starts **disabled** so that route modules can
safely import and decorate endpoints without triggering a Redis connection.

Call ``configure_limiter(settings)`` from the app factory to enable it with
the real Redis backend when the app starts.
"""

from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Shared limiter instance -- route modules import this directly.
# Starts disabled; ``configure_limiter`` enables it at app startup.
limiter = Limiter(key_func=get_remote_address, enabled=False)


def configure_limiter(*, redis_url: str = "", enabled: bool = True) -> None:
    """Re-configure the global limiter in-place.

    Called from ``create_app()`` after settings are loaded.  When *enabled*
    is ``False`` or *redis_url* is empty the limiter stays disabled (no-op).

    If Redis is unreachable at startup the limiter degrades to disabled
    rather than crashing the app.
    """
    if not enabled or not redis_url:
        limiter.enabled = False
        return

    try:
        from limits.storage import storage_from_string

        storage = storage_from_string(redis_url)
        # Probe connectivity -- storage_from_string doesn't connect eagerly.
        # check() returns False (no exception) when Redis is unreachable.
        if not storage.check():
            limiter.enabled = False
            logger.warning(
                "Rate limiting disabled -- Redis not reachable at %s",
                redis_url.split("@")[-1],
            )
            return
        limiter._storage = storage  # type: ignore[attr-defined]
        limiter.enabled = True
        logger.info("Rate limiting enabled (Redis: %s)", redis_url.split("@")[-1])
    except Exception:
        limiter.enabled = False
        logger.warning(
            "Rate limiting disabled -- Redis not reachable at %s",
            redis_url.split("@")[-1],
            exc_info=True,
        )


def reset_limiter() -> None:
    """Disable the limiter (useful in tests after clearing settings)."""
    limiter.enabled = False
