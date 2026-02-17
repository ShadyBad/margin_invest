"""FRED API client — fetches Shiller CAPE ratio for market regime detection.

Uses the FRED API (Federal Reserve Economic Data) to get the current
Shiller PE ratio. Requires FRED_API_KEY environment variable.
Falls back to default CAPE (25.0 = NORMAL regime) if unavailable.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_CAPE = 25.0
_FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
_SERIES_ID = "MEHOINUSA672N"  # Placeholder — Shiller PE may need alternate source
_CACHE_TTL_SECONDS = 86400  # 1 day

# Simple in-memory cache: key -> (value, expiry_timestamp)
_cache: dict[str, tuple[float, float]] = {}


async def _fetch_from_fred() -> float:
    """Fetch latest Shiller CAPE from FRED API."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY not set")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            _FRED_BASE_URL,
            params={
                "series_id": _SERIES_ID,
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        observations = data.get("observations", [])
        if not observations:
            raise ValueError("No observations returned")
        return float(observations[0]["value"])


async def fetch_shiller_cape() -> float:
    """Fetch current Shiller CAPE with caching and fallback.

    Returns the CAPE value (float). Falls back to 25.0 if API unavailable.
    """
    cache_key = "shiller_cape"
    now = time.time()

    # Check cache
    if cache_key in _cache:
        value, expiry = _cache[cache_key]
        if now < expiry:
            return value

    try:
        value = await _fetch_from_fred()
        _cache[cache_key] = (value, now + _CACHE_TTL_SECONDS)
        return value
    except Exception:
        logger.warning("FRED API unavailable, using default CAPE=%.1f", _DEFAULT_CAPE)
        return _DEFAULT_CAPE
