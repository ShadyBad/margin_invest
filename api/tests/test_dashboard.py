"""Tests for dashboard endpoint.

NOTE: These tests are minimal placeholders. The dashboard endpoint currently
returns empty data after the scores route was refactored to use DB queries.
Full DB-backed dashboard tests will be added when the dashboard route is
refactored (Task 8).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from margin_api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestDashboardEndpoint:
    def test_dashboard_returns_200(self, client):
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "picks" in data
        assert "watchlist" in data
        assert "total_scored" in data
        assert "last_updated" in data

    def test_dashboard_empty(self, client):
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["picks"] == []
        assert data["watchlist"] == []
        assert data["total_scored"] == 0
