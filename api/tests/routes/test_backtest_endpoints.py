"""Tests for new backtest API endpoints (teaser, default, replay)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestBacktestTeaser:
    def test_get_teaser_returns_200(self, client):
        response = client.get("/api/v1/backtest/teaser/AAPL")
        assert response.status_code == 200

    def test_teaser_has_required_fields(self, client):
        response = client.get("/api/v1/backtest/teaser/AAPL")
        data = response.json()
        assert "model_return" in data
        assert "benchmark_return" in data
        assert "max_drawdown" in data
        assert "benchmark_max_drawdown" in data
        assert "start_date" in data
        assert "end_date" in data

    def test_teaser_includes_ticker(self, client):
        response = client.get("/api/v1/backtest/teaser/MSFT")
        data = response.json()
        assert data["ticker"] == "MSFT"


class TestDefaultBacktest:
    def test_get_default_returns_200(self, client):
        response = client.get("/api/v1/backtest/default")
        assert response.status_code == 200

    def test_default_has_full_response_fields(self, client):
        response = client.get("/api/v1/backtest/default")
        data = response.json()
        assert "metrics" in data
        assert "regime_segments" in data
        assert "config" in data
        assert "audit_log" in data
        assert "factor_timeline" in data
        assert "failure_audit" in data
        assert "equity_curve" in data
        assert "walk_forward_note" in data
        assert "honesty_disclosure" in data

    def test_default_metrics_are_reasonable(self, client):
        response = client.get("/api/v1/backtest/default")
        data = response.json()
        metrics = data["metrics"]
        assert metrics["cagr"] > 0
        assert metrics["sharpe_ratio"] > 0
        assert 0 < metrics["max_drawdown"] < 1

    def test_default_has_honesty_disclosure(self, client):
        response = client.get("/api/v1/backtest/default")
        data = response.json()
        assert len(data["honesty_disclosure"]) > 0
        assert (
            "out-of-sample" in data["walk_forward_note"].lower()
            or "out of sample" in data["walk_forward_note"].lower()
        )


class TestReplayEndpoint:
    def test_replay_validates_sector_exclusions_max_2(self, client):
        response = client.post(
            "/api/v1/backtest/replay",
            json={
                "sector_exclusions": [
                    "Technology",
                    "Healthcare",
                    "Energy",
                ],
            },
        )
        assert response.status_code == 422

    def test_replay_accepts_valid_config(self, client):
        response = client.post(
            "/api/v1/backtest/replay",
            json={
                "rebalance_frequency": "quarterly",
                "conviction_threshold": 0.20,
            },
        )
        assert response.status_code in (200, 201, 202)

    def test_replay_accepts_empty_config(self, client):
        response = client.post(
            "/api/v1/backtest/replay",
            json={},
        )
        assert response.status_code in (200, 201, 202)

    def test_replay_returns_full_response(self, client):
        response = client.post(
            "/api/v1/backtest/replay",
            json={},
        )
        data = response.json()
        assert "metrics" in data
        assert "regime_segments" in data
        assert "config" in data

    def test_replay_rejects_invalid_frequency(self, client):
        response = client.post(
            "/api/v1/backtest/replay",
            json={"rebalance_frequency": "daily"},
        )
        assert response.status_code == 422

    def test_replay_rejects_invalid_weighting(self, client):
        response = client.post(
            "/api/v1/backtest/replay",
            json={"weighting": "market_cap"},
        )
        assert response.status_code == 422


class TestConfigHash:
    def test_hash_is_deterministic(self):
        from margin_api.services.backtest import compute_config_hash
        from margin_engine.backtesting.replay_orchestrator import (
            ReplayConfig,
        )

        c1 = ReplayConfig(
            conviction_threshold=0.10,
            rebalance_frequency="monthly",
        )
        c2 = ReplayConfig(
            conviction_threshold=0.10,
            rebalance_frequency="monthly",
        )
        c3 = ReplayConfig(
            conviction_threshold=0.20,
            rebalance_frequency="monthly",
        )

        assert compute_config_hash(c1) == compute_config_hash(c2)
        assert compute_config_hash(c1) != compute_config_hash(c3)

    def test_hash_changes_with_sector_exclusions(self):
        from margin_api.services.backtest import compute_config_hash
        from margin_engine.backtesting.replay_orchestrator import (
            ReplayConfig,
        )

        c1 = ReplayConfig(sector_exclusions=[])
        c2 = ReplayConfig(sector_exclusions=["Energy"])
        assert compute_config_hash(c1) != compute_config_hash(c2)


class TestBackwardCompatibility:
    """Ensure existing endpoints still work after adding new ones."""

    def test_old_run_endpoint_still_works(self, client):
        response = client.post("/api/v1/backtest/run", json={})
        assert response.status_code == 201

    def test_old_results_endpoint_still_works(self, client):
        response = client.get("/api/v1/backtest/results")
        assert response.status_code == 200

    def test_old_results_not_found(self, client):
        response = client.get("/api/v1/backtest/results/nonexistent-id")
        assert response.status_code == 404
