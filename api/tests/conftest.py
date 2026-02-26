"""Shared test fixtures for the API test suite."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear the settings cache and rate limiter before each test for isolation."""
    from margin_api.middleware.rate_limit import reset_limiter

    get_settings.cache_clear()
    reset_limiter()
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
