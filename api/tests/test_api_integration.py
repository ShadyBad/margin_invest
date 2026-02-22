"""End-to-end API integration tests.

NOTE: The TestScoreThenRetrieveWorkflow tests were removed because the scores
route no longer has POST/DELETE endpoints (scores are now written by a background
worker, not user-submitted). Full DB-backed integration tests will be added in
Task 11.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app


@pytest.fixture()
def client():
    """Fresh test client for each test."""
    app = create_app()
    return TestClient(app)


class TestAppStartup:
    """Verify app starts correctly with all routes."""

    def test_health_endpoint_responds(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert "version" in data

    def test_all_routes_registered(self, client: TestClient):
        """Verify all expected route prefixes are registered."""
        routes = [route.path for route in client.app.routes]
        assert "/health" in routes
        assert "/api/v1/scores/{ticker}" in routes
        assert "/api/v1/scores" in routes
        assert "/api/v1/dashboard" in routes

    def test_cors_headers_present(self, client: TestClient):
        """Verify CORS headers are returned for cross-origin requests."""
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in resp.headers
