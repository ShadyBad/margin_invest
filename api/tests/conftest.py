"""Shared test fixtures for the API test suite."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache(monkeypatch):
    """Clear the settings cache and rate limiter before each test for isolation.

    The limiter is a global singleton that ``create_app()`` re-enables when Redis
    is reachable.  We force ``rate_limit_enabled=False`` so ``create_app()`` calls
    ``configure_limiter(enabled=False)`` and the limiter stays disabled. Tests that
    explicitly test rate limiting can call ``configure_limiter`` directly.
    """
    from margin_api.middleware.rate_limit import reset_limiter

    get_settings.cache_clear()
    reset_limiter()
    monkeypatch.setenv("MARGIN_RATE_LIMIT_ENABLED", "false")
    yield
    get_settings.cache_clear()
    reset_limiter()


@pytest.fixture(autouse=True)
def _clear_backtest_store():
    """Clear the in-memory backtest store before and after each test."""
    from margin_api.routes.backtest import _backtest_store

    _backtest_store.clear()
    yield
    _backtest_store.clear()


@pytest.fixture
def app():
    """Create a fresh app instance for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)
