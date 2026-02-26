"""Rate limiting middleware using slowapi + Redis."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

_limiter: Limiter | None = None


def get_limiter() -> Limiter:
    """Return the singleton Limiter instance, creating it lazily.

    Disabled (no-op) when ``rate_limit_enabled`` is False or no Redis URL
    is configured.  This ensures tests that do not spin up Redis are never
    blocked by rate limits.
    """
    global _limiter
    if _limiter is None:
        from margin_api.config import get_settings

        settings = get_settings()
        if not settings.rate_limit_enabled or not settings.redis_url:
            _limiter = Limiter(key_func=get_remote_address, enabled=False)
        else:
            _limiter = Limiter(
                key_func=get_remote_address,
                storage_uri=settings.redis_url,
                strategy="fixed-window",
            )
    return _limiter


def reset_limiter() -> None:
    """Reset the cached limiter (useful in tests after clearing settings)."""
    global _limiter
    _limiter = None
