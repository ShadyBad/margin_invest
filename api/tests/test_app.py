"""Tests for application factory."""

from __future__ import annotations

from fastapi import FastAPI
from margin_api.app import create_app


class TestCreateApp:
    def test_creates_fastapi_instance(self):
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_app_title(self):
        app = create_app()
        assert app.title == "Margin Invest API"

    def test_health_route_registered(self):
        app = create_app()
        routes = [r.path for r in app.routes]
        assert "/health" in routes

    def test_cors_middleware_added(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
