"""Tests for correlation endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestShowcaseEndpoint:
    def test_returns_200_without_auth(self, client: TestClient):
        resp = client.get("/api/v1/correlations/showcase")
        assert resp.status_code == 200

    def test_response_has_expected_shape(self, client: TestClient):
        resp = client.get("/api/v1/correlations/showcase")
        data = resp.json()
        assert "tickers" in data
        assert "matrix" in data
        assert "sample_sizes" in data
        assert "method" in data
        n = len(data["tickers"])
        assert len(data["matrix"]) == n
        assert all(len(row) == n for row in data["matrix"])

    def test_fallback_values_present(self, client: TestClient):
        resp = client.get("/api/v1/correlations/showcase")
        data = resp.json()
        assert data["method"] == "returns"
        assert len(data["tickers"]) >= 2

    def test_showcase_route_registered(self, client: TestClient):
        routes = [r.path for r in client.app.routes]
        assert "/api/v1/correlations/showcase" in routes


from unittest.mock import AsyncMock, patch
from datetime import UTC, datetime


class TestShowcaseLiveComputation:
    """Tests for live correlation computation on cache miss."""

    @patch("margin_api.routes.correlations._get_redis_cached", new_callable=AsyncMock, return_value=None)
    @patch("margin_api.routes.correlations._cache_to_redis", new_callable=AsyncMock)
    @patch("margin_api.routes.correlations._compute_live_showcase", new_callable=AsyncMock)
    def test_calls_live_computation_on_cache_miss(
        self, mock_compute, mock_cache, mock_redis, client: TestClient
    ):
        """When Redis returns None, endpoint should attempt live computation."""
        mock_compute.return_value = None  # Simulate not enough tickers
        resp = client.get("/api/v1/correlations/showcase")
        assert resp.status_code == 200
        mock_compute.assert_called_once()
        # Falls back to static since live returned None
        data = resp.json()
        assert data["tickers"] == ["AAPL", "MSFT", "JNJ", "COST", "V"]

    @patch("margin_api.routes.correlations._get_redis_cached", new_callable=AsyncMock, return_value=None)
    @patch("margin_api.routes.correlations._cache_to_redis", new_callable=AsyncMock)
    @patch("margin_api.routes.correlations._compute_live_showcase", new_callable=AsyncMock)
    def test_returns_live_data_when_available(
        self, mock_compute, mock_cache, mock_redis, client: TestClient
    ):
        """When live computation succeeds, return that data and cache it."""
        from margin_api.schemas.correlations import CorrelationResponse

        live_result = CorrelationResponse(
            tickers=["NVDA", "AVGO", "PLTR", "APP", "CRWD"],
            method="returns",
            matrix=[
                [1.0, 0.7, 0.3, 0.2, 0.5],
                [0.7, 1.0, 0.4, 0.3, 0.6],
                [0.3, 0.4, 1.0, 0.5, 0.4],
                [0.2, 0.3, 0.5, 1.0, 0.3],
                [0.5, 0.6, 0.4, 0.3, 1.0],
            ],
            sample_sizes=[[252] * 5 for _ in range(5)],
            excluded=[],
            window_days=252,
            computed_at=datetime(2026, 2, 21, tzinfo=UTC),
        )
        mock_compute.return_value = live_result
        resp = client.get("/api/v1/correlations/showcase")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tickers"] == ["NVDA", "AVGO", "PLTR", "APP", "CRWD"]
        mock_cache.assert_called_once()
