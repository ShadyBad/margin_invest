"""Tests for score endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.routes import scores as scores_module


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


def _sample_score(
    ticker: str = "AAPL",
    percentile: float = 99.5,
    conviction: str = "exceptional",
    signal: str = "buy",
) -> dict:
    """Create a minimal valid score payload."""
    return {
        "ticker": ticker,
        "composite_percentile": percentile,
        "conviction_level": conviction,
        "signal": signal,
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 0.0,
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [],
            "average_percentile": 0.0,
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 0.0,
        },
        "filters_passed": [],
        "data_coverage": 1.0,
        "growth_stage": None,
    }


class TestCreateScore:
    def test_create_score_success(self, client):
        payload = _sample_score("AAPL")
        response = client.post("/api/v1/scores/AAPL", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["composite_percentile"] == 99.5

    def test_create_score_normalizes_ticker(self, client):
        payload = _sample_score("aapl")
        response = client.post("/api/v1/scores/aapl", json=payload)
        assert response.status_code == 201

    def test_create_score_ticker_mismatch(self, client):
        payload = _sample_score("NVDA")
        response = client.post("/api/v1/scores/AAPL", json=payload)
        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"].lower()


class TestGetScore:
    def test_get_score_success(self, client):
        payload = _sample_score("AAPL")
        client.post("/api/v1/scores/AAPL", json=payload)
        response = client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        assert response.json()["ticker"] == "AAPL"

    def test_get_score_not_found(self, client):
        response = client.get("/api/v1/scores/UNKNOWN")
        assert response.status_code == 404

    def test_get_score_case_insensitive(self, client):
        payload = _sample_score("AAPL")
        client.post("/api/v1/scores/AAPL", json=payload)
        response = client.get("/api/v1/scores/aapl")
        assert response.status_code == 200


class TestListScores:
    def test_list_scores_empty(self, client):
        response = client.get("/api/v1/scores")
        assert response.status_code == 200
        data = response.json()
        assert data["scores"] == []
        assert data["total"] == 0

    def test_list_scores_with_data(self, client):
        client.post("/api/v1/scores/AAPL", json=_sample_score("AAPL", 99.5))
        client.post("/api/v1/scores/NVDA", json=_sample_score("NVDA", 98.0))
        response = client.get("/api/v1/scores")
        data = response.json()
        assert data["total"] == 2
        # Should be sorted by percentile descending
        assert data["scores"][0]["ticker"] == "AAPL"
        assert data["scores"][1]["ticker"] == "NVDA"

    def test_list_scores_filter_by_percentile(self, client):
        client.post("/api/v1/scores/AAPL", json=_sample_score("AAPL", 99.5))
        client.post(
            "/api/v1/scores/BAD",
            json=_sample_score("BAD", 50.0, "none", "no_action"),
        )
        response = client.get("/api/v1/scores?min_percentile=90")
        data = response.json()
        assert data["total"] == 1
        assert data["scores"][0]["ticker"] == "AAPL"

    def test_list_scores_filter_by_conviction(self, client):
        client.post(
            "/api/v1/scores/AAPL",
            json=_sample_score("AAPL", 99.5, "exceptional"),
        )
        client.post(
            "/api/v1/scores/NVDA",
            json=_sample_score("NVDA", 96.0, "high"),
        )
        response = client.get("/api/v1/scores?conviction=exceptional")
        data = response.json()
        assert data["total"] == 1
        assert data["scores"][0]["ticker"] == "AAPL"

    def test_list_scores_pagination(self, client):
        for i in range(5):
            ticker = f"T{i:03d}"
            client.post(
                f"/api/v1/scores/{ticker}",
                json=_sample_score(ticker, 90.0 + i),
            )
        response = client.get("/api/v1/scores?page=1&page_size=2")
        data = response.json()
        assert data["total"] == 5
        assert len(data["scores"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2


class TestDeleteScore:
    def test_delete_score_success(self, client):
        client.post("/api/v1/scores/AAPL", json=_sample_score("AAPL"))
        response = client.delete("/api/v1/scores/AAPL")
        assert response.status_code == 204
        # Verify it's gone
        response = client.get("/api/v1/scores/AAPL")
        assert response.status_code == 404

    def test_delete_score_not_found(self, client):
        response = client.delete("/api/v1/scores/UNKNOWN")
        assert response.status_code == 404
