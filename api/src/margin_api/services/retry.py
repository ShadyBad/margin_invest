"""Exponential backoff retry wrapper for provider calls."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

MAX_RETRIES = 3
BASE_DELAY = 2.0
MAX_DELAY = 60.0


async def with_retry(
    fn: Callable[..., T],
    *args,
    ticker: str,
    retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    max_delay: float = MAX_DELAY,
    **kwargs,
) -> T:
    """Call a synchronous fn with exponential backoff on failure.

    Note: fn must be synchronous. Async callables are not awaited.
    """
    for attempt in range(1, retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt == retries:
                logger.error(
                    "Failed %s after %d attempts: %s", ticker, retries, e
                )
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(
                "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                attempt, retries, ticker, e, delay,
            )
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable")
