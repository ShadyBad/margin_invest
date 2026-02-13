"""End-to-end API integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app


@pytest.fixture()
def client():
    """Fresh test client for each test."""
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_score_store():
    """Clear the in-memory score store before and after each test."""
    from margin_api.routes.scores import _score_store

    _score_store.clear()
    yield
    _score_store.clear()


def _make_score_payload(
    ticker: str = "AAPL",
    percentile: float = 82.5,
    conviction: str = "high",
    signal: str = "buy",
    quality_percentile: float = 85.0,
    value_percentile: float = 78.0,
    momentum_percentile: float = 80.0,
    growth_stage: str | None = "mature",
) -> dict:
    """Build a minimal valid ScoreResponse-compatible payload."""
    return {
        "ticker": ticker,
        "composite_percentile": percentile,
        "conviction_level": conviction,
        "signal": signal,
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [
                {
                    "name": "gross_profitability",
                    "raw_value": 0.45,
                    "percentile_rank": quality_percentile,
                },
            ],
            "average_percentile": quality_percentile,
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [
                {
                    "name": "ev_fcf",
                    "raw_value": 15.2,
                    "percentile_rank": value_percentile,
                },
            ],
            "average_percentile": value_percentile,
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [
                {
                    "name": "price_momentum",
                    "raw_value": 0.12,
                    "percentile_rank": momentum_percentile,
                },
            ],
            "average_percentile": momentum_percentile,
        },
        "filters_passed": [],
        "data_coverage": 1.0,
        "growth_stage": growth_stage,
    }


class TestAppStartup:
    """Verify app starts correctly with all routes."""

    def test_health_endpoint_responds(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
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


class TestScoreThenRetrieveWorkflow:
    """End-to-end: score a ticker, retrieve it, see it on dashboard."""

    def test_score_store_and_retrieve(self, client: TestClient):
        """POST a score, GET it back, verify round-trip."""
        payload = _make_score_payload("MSFT")
        # Store
        resp = client.post("/api/v1/scores/MSFT", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "MSFT"
        assert data["composite_percentile"] == 82.5

        # Retrieve
        resp = client.get("/api/v1/scores/MSFT")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "MSFT"
        assert data["conviction_level"] == "high"

    def test_score_appears_on_dashboard(self, client: TestClient):
        """POST a high-conviction score, verify it shows as a pick on dashboard."""
        payload = _make_score_payload("GOOGL")
        client.post("/api/v1/scores/GOOGL", json=payload)

        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_scored"] == 1
        assert len(data["picks"]) == 1
        assert data["picks"][0]["ticker"] == "GOOGL"
        assert data["picks"][0]["conviction_level"] == "high"

    def test_watchlist_ticker_not_in_picks(self, client: TestClient):
        """POST a watchlist-conviction score, verify it's in watchlist not picks."""
        payload = _make_score_payload(
            "TSLA", percentile=55.0, conviction="watchlist", signal="watch",
        )
        client.post("/api/v1/scores/TSLA", json=payload)

        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["picks"]) == 0
        assert len(data["watchlist"]) == 1
        assert data["watchlist"][0]["ticker"] == "TSLA"

    def test_delete_removes_from_dashboard(self, client: TestClient):
        """POST a score, DELETE it, verify dashboard is empty."""
        payload = _make_score_payload("NVDA")
        client.post("/api/v1/scores/NVDA", json=payload)

        # Verify it's there
        resp = client.get("/api/v1/dashboard")
        assert resp.json()["total_scored"] == 1

        # Delete
        resp = client.delete("/api/v1/scores/NVDA")
        assert resp.status_code == 204

        # Verify gone
        resp = client.get("/api/v1/dashboard")
        assert resp.json()["total_scored"] == 0
        assert len(resp.json()["picks"]) == 0

    def test_multi_ticker_dashboard(self, client: TestClient):
        """Multiple scores with different conviction levels sort correctly."""
        # Exceptional conviction
        p1 = _make_score_payload("AAPL", percentile=90.0, conviction="exceptional")
        client.post("/api/v1/scores/AAPL", json=p1)

        # High conviction, lower percentile
        p2 = _make_score_payload("MSFT", percentile=75.0, conviction="high")
        client.post("/api/v1/scores/MSFT", json=p2)

        # Watchlist
        p3 = _make_score_payload(
            "TSLA", percentile=50.0, conviction="watchlist", signal="watch",
        )
        client.post("/api/v1/scores/TSLA", json=p3)

        # None conviction (excluded from picks and watchlist)
        p4 = _make_score_payload(
            "GME", percentile=20.0, conviction="none", signal="no_action",
        )
        client.post("/api/v1/scores/GME", json=p4)

        resp = client.get("/api/v1/dashboard")
        data = resp.json()
        assert data["total_scored"] == 4
        assert len(data["picks"]) == 2
        assert len(data["watchlist"]) == 1
        # Picks sorted by composite_percentile desc
        assert data["picks"][0]["ticker"] == "AAPL"
        assert data["picks"][1]["ticker"] == "MSFT"
        assert data["watchlist"][0]["ticker"] == "TSLA"
