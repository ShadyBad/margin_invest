"""Tests for dashboard endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.routes import scores as scores_module
from margin_api.schemas.scores import FactorBreakdownResponse, ScoreResponse


@pytest.fixture(autouse=True)
def clean_score_store():
    """Clear the in-memory score store before each test."""
    scores_module._score_store.clear()
    yield
    scores_module._score_store.clear()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _make_score(
    ticker: str,
    percentile: float,
    conviction: str,
    signal: str = "buy",
) -> ScoreResponse:
    """Create a ScoreResponse for testing."""
    breakdown = FactorBreakdownResponse(
        factor_name="test",
        weight=0.33,
        sub_scores=[],
        average_percentile=percentile,
    )
    return ScoreResponse(
        ticker=ticker,
        composite_percentile=percentile,
        conviction_level=conviction,
        signal=signal,
        quality=breakdown,
        value=breakdown,
        momentum=breakdown,
        filters_passed=[],
        data_coverage=1.0,
    )


def _populate_store(*scores: ScoreResponse):
    """Add scores directly to the in-memory store."""
    for score in scores:
        scores_module._score_store[score.ticker] = score


class TestDashboardEndpoint:
    def test_dashboard_empty(self, client):
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["picks"] == []
        assert data["watchlist"] == []
        assert data["total_scored"] == 0
        assert "last_updated" in data

    def test_dashboard_with_picks(self, client):
        _populate_store(
            _make_score("AAPL", 99.5, "exceptional"),
            _make_score("NVDA", 96.0, "high"),
        )
        response = client.get("/api/v1/dashboard")
        data = response.json()
        assert len(data["picks"]) == 2
        assert data["picks"][0]["ticker"] == "AAPL"  # Sorted by percentile
        assert data["picks"][1]["ticker"] == "NVDA"
        assert data["watchlist"] == []
        assert data["total_scored"] == 2

    def test_dashboard_with_watchlist(self, client):
        _populate_store(
            _make_score("XYZ", 92.0, "watchlist", "watch"),
        )
        response = client.get("/api/v1/dashboard")
        data = response.json()
        assert data["picks"] == []
        assert len(data["watchlist"]) == 1
        assert data["watchlist"][0]["ticker"] == "XYZ"
        assert data["watchlist"][0]["conviction_level"] == "watchlist"

    def test_dashboard_mixed(self, client):
        _populate_store(
            _make_score("AAPL", 99.5, "exceptional"),
            _make_score("XYZ", 92.0, "watchlist", "watch"),
            _make_score("BAD", 50.0, "none", "no_action"),
        )
        response = client.get("/api/v1/dashboard")
        data = response.json()
        assert len(data["picks"]) == 1
        assert len(data["watchlist"]) == 1
        assert data["total_scored"] == 3
        # "none" conviction shouldn't appear in either list

    def test_dashboard_pick_includes_factor_percentiles(self, client):
        _populate_store(_make_score("AAPL", 99.5, "exceptional"))
        response = client.get("/api/v1/dashboard")
        pick = response.json()["picks"][0]
        assert "quality_percentile" in pick
        assert "value_percentile" in pick
        assert "momentum_percentile" in pick

    def test_dashboard_picks_sorted_by_percentile(self, client):
        _populate_store(
            _make_score("NVDA", 96.0, "high"),
            _make_score("AAPL", 99.5, "exceptional"),
            _make_score("COST", 95.5, "high"),
        )
        response = client.get("/api/v1/dashboard")
        tickers = [p["ticker"] for p in response.json()["picks"]]
        assert tickers == ["AAPL", "NVDA", "COST"]
