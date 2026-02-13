"""Tests for backtest API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.routes import backtest as backtest_module


@pytest.fixture(autouse=True)
def clean_backtest_store():
    """Clear the in-memory backtest store before each test."""
    backtest_module._backtest_store.clear()
    yield
    backtest_module._backtest_store.clear()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _run_backtest(client: TestClient, config: dict | None = None) -> dict:
    """Run a backtest via the API and return the response JSON."""
    response = client.post("/api/v1/backtest/run", json=config or {})
    assert response.status_code == 201
    return response.json()


def _get_backtest_id(client: TestClient, config: dict | None = None) -> str:
    """Run a backtest and return the ID from the in-memory store."""
    _run_backtest(client, config)
    # The store should have exactly one entry after a single run
    ids = list(backtest_module._backtest_store.keys())
    return ids[-1]


class TestRunBacktest:
    def test_run_backtest_returns_201(self, client):
        response = client.post("/api/v1/backtest/run", json={})
        assert response.status_code == 201

    def test_run_backtest_returns_result(self, client):
        data = _run_backtest(client)
        assert "config" in data
        assert "metrics" in data
        assert "validation" in data
        assert "num_snapshots" in data
        assert "run_at" in data
        assert "duration_seconds" in data

    def test_run_backtest_default_config(self, client):
        data = _run_backtest(client)
        config = data["config"]
        assert config["start_date"] == "2015-01-01"
        assert config["rebalance_frequency"] == "monthly"
        assert config["top_percentile"] == 0.05
        assert config["transaction_cost_bps"] == 10.0
        assert config["slippage_bps"] == 5.0
        assert config["benchmark_ticker"] == "SPY"

    def test_run_backtest_custom_config(self, client):
        custom = {
            "start_date": "2018-06-01",
            "end_date": "2023-12-31",
            "rebalance_frequency": "quarterly",
            "top_percentile": 0.10,
            "transaction_cost_bps": 15.0,
            "slippage_bps": 8.0,
            "benchmark_ticker": "QQQ",
        }
        data = _run_backtest(client, custom)
        config = data["config"]
        assert config["start_date"] == "2018-06-01"
        assert config["end_date"] == "2023-12-31"
        assert config["rebalance_frequency"] == "quarterly"
        assert config["top_percentile"] == 0.10
        assert config["transaction_cost_bps"] == 15.0
        assert config["slippage_bps"] == 8.0
        assert config["benchmark_ticker"] == "QQQ"

    def test_run_backtest_metrics_are_reasonable(self, client):
        data = _run_backtest(client)
        metrics = data["metrics"]
        assert metrics["cagr"] > 0
        assert metrics["sharpe_ratio"] > 0
        assert 0 < metrics["max_drawdown"] < 1
        assert 0 <= metrics["win_rate"] <= 1
        assert metrics["num_months"] > 0
        assert metrics["avg_turnover"] >= 0

    def test_run_backtest_stores_result(self, client):
        _run_backtest(client)
        assert len(backtest_module._backtest_store) == 1


class TestListResults:
    def test_list_results_empty(self, client):
        response = client.get("/api/v1/backtest/results")
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total"] == 0

    def test_list_results_after_run(self, client):
        _run_backtest(client)
        response = client.get("/api/v1/backtest/results")
        data = response.json()
        assert data["total"] == 1
        assert len(data["results"]) == 1
        summary = data["results"][0]
        assert "id" in summary
        assert "run_at" in summary
        assert "config" in summary
        assert "overall_pass" in summary
        assert "excess_cagr" in summary
        assert "sharpe_ratio" in summary

    def test_list_results_sorted_by_run_at_desc(self, client):
        _run_backtest(client)
        _run_backtest(client, {"start_date": "2020-01-01"})
        _run_backtest(client, {"start_date": "2018-01-01"})
        response = client.get("/api/v1/backtest/results")
        data = response.json()
        assert data["total"] == 3
        run_ats = [r["run_at"] for r in data["results"]]
        assert run_ats == sorted(run_ats, reverse=True)


class TestGetResult:
    def test_get_result_by_id(self, client):
        backtest_id = _get_backtest_id(client)
        response = client.get(f"/api/v1/backtest/results/{backtest_id}")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "metrics" in data
        assert "validation" in data

    def test_get_result_not_found(self, client):
        response = client.get("/api/v1/backtest/results/nonexistent-id")
        assert response.status_code == 404

    def test_get_result_matches_run_output(self, client):
        run_data = _run_backtest(client)
        backtest_id = list(backtest_module._backtest_store.keys())[0]
        response = client.get(f"/api/v1/backtest/results/{backtest_id}")
        get_data = response.json()
        assert get_data["metrics"] == run_data["metrics"]
        assert get_data["config"] == run_data["config"]


class TestGetMetrics:
    def test_get_metrics_by_id(self, client):
        backtest_id = _get_backtest_id(client)
        response = client.get(f"/api/v1/backtest/metrics/{backtest_id}")
        assert response.status_code == 200
        data = response.json()
        assert "cagr" in data
        assert "excess_cagr" in data
        assert "sharpe_ratio" in data
        assert "sortino_ratio" in data
        assert "max_drawdown" in data
        assert "win_rate" in data
        assert "information_ratio" in data
        assert "total_return" in data
        assert "benchmark_total_return" in data
        assert "num_months" in data
        assert "avg_turnover" in data

    def test_get_metrics_not_found(self, client):
        response = client.get("/api/v1/backtest/metrics/nonexistent-id")
        assert response.status_code == 404

    def test_get_metrics_matches_result(self, client):
        backtest_id = _get_backtest_id(client)
        result_resp = client.get(f"/api/v1/backtest/results/{backtest_id}")
        metrics_resp = client.get(f"/api/v1/backtest/metrics/{backtest_id}")
        assert result_resp.json()["metrics"] == metrics_resp.json()


class TestValidation:
    def test_result_has_validation_data(self, client):
        data = _run_backtest(client)
        validation = data["validation"]
        assert validation is not None
        assert "overall_pass" in validation
        assert "passed_count" in validation
        assert "total_checks" in validation
        assert "checks" in validation
        assert validation["total_checks"] == 6
        assert len(validation["checks"]) == 6

    def test_validation_checks_have_correct_fields(self, client):
        data = _run_backtest(client)
        for check in data["validation"]["checks"]:
            assert "name" in check
            assert "threshold" in check
            assert "actual" in check
            assert "passed" in check

    def test_validation_check_names(self, client):
        data = _run_backtest(client)
        names = {c["name"] for c in data["validation"]["checks"]}
        expected = {
            "excess_cagr",
            "sharpe_ratio",
            "sortino_ratio",
            "max_drawdown",
            "win_rate",
            "information_ratio",
        }
        assert names == expected

    def test_synthetic_metrics_pass_default_thresholds(self, client):
        """The synthetic mock metrics should pass all default thresholds."""
        data = _run_backtest(client)
        validation = data["validation"]
        assert validation["overall_pass"] is True
        assert validation["passed_count"] == validation["total_checks"]


class TestTimestamps:
    def test_result_has_run_at(self, client):
        data = _run_backtest(client)
        assert data["run_at"] is not None
        # Should be a valid ISO datetime string
        assert "T" in data["run_at"]

    def test_result_has_duration(self, client):
        data = _run_backtest(client)
        assert data["duration_seconds"] >= 0


class TestMultipleBacktests:
    def test_multiple_backtests_stored_independently(self, client):
        _run_backtest(client)
        _run_backtest(client, {"start_date": "2020-01-01"})
        assert len(backtest_module._backtest_store) == 2

        response = client.get("/api/v1/backtest/results")
        data = response.json()
        assert data["total"] == 2

        # Each should have a unique ID
        ids = {r["id"] for r in data["results"]}
        assert len(ids) == 2

    def test_multiple_backtests_retrievable_by_id(self, client):
        _run_backtest(client)
        _run_backtest(client, {"start_date": "2020-01-01"})
        ids = list(backtest_module._backtest_store.keys())
        assert len(ids) == 2

        for backtest_id in ids:
            response = client.get(f"/api/v1/backtest/results/{backtest_id}")
            assert response.status_code == 200

    def test_different_configs_produce_different_snapshots(self, client):
        data1 = _run_backtest(client, {"start_date": "2015-01-01"})
        data2 = _run_backtest(client, {"start_date": "2020-01-01"})
        # Different start dates should produce different num_snapshots
        assert data1["num_snapshots"] != data2["num_snapshots"]
