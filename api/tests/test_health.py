"""Tests for health check endpoint."""

from __future__ import annotations


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_includes_version(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "0.1.0"
