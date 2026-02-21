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


class TestCorrelationEndpoint:
    def test_invalid_method_returns_422(self, client: TestClient):
        resp = client.get("/api/v1/correlations?method=invalid")
        assert resp.status_code == 422

    def test_method_required(self, client: TestClient):
        resp = client.get("/api/v1/correlations")
        assert resp.status_code == 422

    def test_window_bounds(self, client: TestClient):
        resp = client.get("/api/v1/correlations?method=returns&window=5")
        assert resp.status_code == 422
        resp = client.get("/api/v1/correlations?method=returns&window=1000")
        assert resp.status_code == 422

    def test_route_registered(self, client: TestClient):
        routes = [r.path for r in client.app.routes]
        assert "/api/v1/correlations" in routes
        assert "/api/v1/correlations/showcase" in routes
