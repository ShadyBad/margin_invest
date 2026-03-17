"""Macro data client — fetches market regime indicators from FRED and yfinance.

Provides:
- Shiller CAPE ratio (market valuation)
- 10Y-2Y Treasury yield curve slope (rate environment)
- Baa-10Y credit spread (credit risk environment)
- VIX (volatility regime)

FRED data requires FRED_API_KEY environment variable.
All functions fall back to sensible defaults if data is unavailable.
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


async def fetch_yield_curve_slope() -> float:
    """Fetch 10Y-2Y Treasury yield curve slope from FRED.
    Returns spread in percentage points. Falls back to 1.0 if unavailable.
    """
    cache_key = "yield_curve_slope"
    now = time.time()
    if cache_key in _cache:
        value, expiry = _cache[cache_key]
        if now < expiry:
            return value

    try:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            raise ValueError("FRED_API_KEY not set")

        async with httpx.AsyncClient(timeout=10.0) as client:
            dgs10_resp = await client.get(
                _FRED_BASE_URL,
                params={
                    "series_id": "DGS10",
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
            )
            dgs10_resp.raise_for_status()
            dgs10 = float(dgs10_resp.json()["observations"][0]["value"])

            dgs2_resp = await client.get(
                _FRED_BASE_URL,
                params={
                    "series_id": "DGS2",
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
            )
            dgs2_resp.raise_for_status()
            dgs2 = float(dgs2_resp.json()["observations"][0]["value"])

        value = dgs10 - dgs2
        _cache[cache_key] = (value, now + _CACHE_TTL_SECONDS)
        return value
    except Exception:
        logger.warning("FRED API unavailable for yield curve, using default slope=1.0")
        return 1.0


async def fetch_credit_spread() -> float:
    """Fetch Baa-10Y Treasury credit spread from FRED (BAA10Y series).
    Returns spread in percentage points. Falls back to 2.0 if unavailable.
    """
    cache_key = "credit_spread"
    now = time.time()
    if cache_key in _cache:
        value, expiry = _cache[cache_key]
        if now < expiry:
            return value

    try:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            raise ValueError("FRED_API_KEY not set")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _FRED_BASE_URL,
                params={
                    "series_id": "BAA10Y",
                    "api_key": api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
            )
            resp.raise_for_status()
            value = float(resp.json()["observations"][0]["value"])

        _cache[cache_key] = (value, now + _CACHE_TTL_SECONDS)
        return value
    except Exception:
        logger.warning("FRED API unavailable for credit spread, using default=2.0")
        return 2.0


async def fetch_vix() -> float:
    """Fetch current VIX level from yfinance. Falls back to 20.0 if unavailable."""
    cache_key = "vix"
    now = time.time()
    if cache_key in _cache:
        value, expiry = _cache[cache_key]
        if now < expiry:
            return value

    try:
        import yfinance as yf

        ticker = yf.Ticker("^VIX")
        hist = ticker.history(period="1d")
        if hist.empty:
            raise ValueError("No VIX data returned")
        value = float(hist["Close"].iloc[-1])
        _cache[cache_key] = (value, now + _CACHE_TTL_SECONDS)
        return value
    except Exception:
        logger.warning("yfinance unavailable for VIX, using default=20.0")
        return 20.0
