"""Integration tests for the backtest API endpoints.

Verifies end-to-end flows through the HTTP API: running backtests,
retrieving results, metrics, multiple backtests, and router exports.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.routes import backtest as backtest_module


@pytest.fixture(autouse=True)
def _clean_store():
    """Ensure the in-memory store is empty before and after each test."""
    backtest_module._backtest_store.clear()
    yield
    backtest_module._backtest_store.clear()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _run_backtest(client: TestClient, config: dict | None = None) -> dict:
    """POST a backtest run and return the JSON response."""
    resp = client.post("/api/v1/backtest/run", json=config or {})
    assert resp.status_code == 201
    return resp.json()


def _get_backtest_id() -> str:
    """Return the last inserted backtest ID from the in-memory store."""
    ids = list(backtest_module._backtest_store.keys())
    assert ids, "No backtest found in store"
    return ids[-1]


# ---------------------------------------------------------------------------
# 1. Run backtest and retrieve result
# ---------------------------------------------------------------------------


class TestRunAndRetrieve:
    """POST /run -> GET /results/{id} -> verify match."""

    def test_run_then_get_matches(self, client):
        run_data = _run_backtest(client)
        backtest_id = _get_backtest_id()

        resp = client.get(f"/api/v1/backtest/results/{backtest_id}")
        assert resp.status_code == 200
        get_data = resp.json()

        # Config should match
        assert get_data["config"] == run_data["config"]
        # Metrics should match
        assert get_data["metrics"] == run_data["metrics"]
        # Validation should match
        assert get_data["validation"] == run_data["validation"]

    def test_result_has_all_expected_fields(self, client):
        _run_backtest(client)
        backtest_id = _get_backtest_id()

        resp = client.get(f"/api/v1/backtest/results/{backtest_id}")
        data = resp.json()

        assert "config" in data
        assert "metrics" in data
        assert "validation" in data
        assert "num_snapshots" in data
        assert "run_at" in data
        assert "duration_seconds" in data

    def test_nonexistent_id_returns_404(self, client):
        resp = client.get("/api/v1/backtest/results/does-not-exist")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. Run backtest and get metrics
# ---------------------------------------------------------------------------


class TestRunAndGetMetrics:
    """POST /run -> GET /metrics/{id} -> verify metrics subset."""

    def test_metrics_match_result(self, client):
        run_data = _run_backtest(client)
        backtest_id = _get_backtest_id()

        resp = client.get(f"/api/v1/backtest/metrics/{backtest_id}")
        assert resp.status_code == 200
        metrics_data = resp.json()

        assert metrics_data == run_data["metrics"]

    def test_metrics_has_all_fields(self, client):
        _run_backtest(client)
        backtest_id = _get_backtest_id()

        resp = client.get(f"/api/v1/backtest/metrics/{backtest_id}")
        data = resp.json()

        expected_fields = {
            "cagr",
            "excess_cagr",
            "sharpe_ratio",
            "sortino_ratio",
            "max_drawdown",
            "win_rate",
            "information_ratio",
            "total_return",
            "benchmark_total_return",
            "num_months",
            "avg_turnover",
            "gross_cagr",
            "gross_sharpe",
            "gross_max_drawdown",
            "cost_drag_bps",
        }
        assert set(data.keys()) == expected_fields

    def test_metrics_nonexistent_returns_404(self, client):
        resp = client.get("/api/v1/backtest/metrics/no-such-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 3. Multiple backtests stored independently
# ---------------------------------------------------------------------------


class TestMultipleBacktests:
    """Run 2 backtests, list, verify both present."""

    def test_two_backtests_listed(self, client):
        _run_backtest(client, {"start_date": "2015-01-01"})
        _run_backtest(client, {"start_date": "2020-01-01"})

        resp = client.get("/api/v1/backtest/results")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] == 2
        assert len(data["results"]) == 2

    def test_unique_ids(self, client):
        _run_backtest(client)
        _run_backtest(client)

        resp = client.get("/api/v1/backtest/results")
        ids = {r["id"] for r in resp.json()["results"]}
        assert len(ids) == 2

    def test_each_retrievable_by_id(self, client):
        _run_backtest(client, {"start_date": "2015-01-01"})
        _run_backtest(client, {"start_date": "2020-01-01"})

        all_ids = list(backtest_module._backtest_store.keys())
        assert len(all_ids) == 2

        for bid in all_ids:
            resp = client.get(f"/api/v1/backtest/results/{bid}")
            assert resp.status_code == 200

    def test_list_sorted_by_run_at_descending(self, client):
        _run_backtest(client)
        _run_backtest(client, {"start_date": "2020-01-01"})
        _run_backtest(client, {"start_date": "2018-01-01"})

        resp = client.get("/api/v1/backtest/results")
        run_ats = [r["run_at"] for r in resp.json()["results"]]
        assert run_ats == sorted(run_ats, reverse=True)


# ---------------------------------------------------------------------------
# 4. Backtest with custom config
# ---------------------------------------------------------------------------


class TestCustomConfig:
    """POST with custom params, verify config echoed back."""

    def test_custom_config_echoed(self, client):
        custom = {
            "start_date": "2019-03-01",
            "end_date": "2023-06-30",
            "rebalance_frequency": "quarterly",
            "top_percentile": 0.10,
            "transaction_cost_bps": 20.0,
            "slippage_bps": 8.0,
            "benchmark_ticker": "QQQ",
        }
        data = _run_backtest(client, custom)
        config = data["config"]

        assert config["start_date"] == "2019-03-01"
        assert config["end_date"] == "2023-06-30"
        assert config["rebalance_frequency"] == "quarterly"
        assert config["top_percentile"] == 0.10
        assert config["transaction_cost_bps"] == 20.0
        assert config["slippage_bps"] == 8.0
        assert config["benchmark_ticker"] == "QQQ"

    def test_default_config_values(self, client):
        data = _run_backtest(client)
        config = data["config"]

        assert config["start_date"] == "2015-01-01"
        assert config["rebalance_frequency"] == "monthly"
        assert config["top_percentile"] == 0.05
        assert config["benchmark_ticker"] == "SPY"

    def test_different_configs_produce_different_months(self, client):
        data_long = _run_backtest(client, {"start_date": "2015-01-01"})
        data_short = _run_backtest(client, {"start_date": "2023-01-01"})

        assert data_long["num_snapshots"] != data_short["num_snapshots"]


# ---------------------------------------------------------------------------
# 5. Validation data included
# ---------------------------------------------------------------------------


class TestValidationIncluded:
    """POST /run, verify validation checks present."""

    def test_validation_present(self, client):
        data = _run_backtest(client)
        assert data["validation"] is not None

    def test_validation_structure(self, client):
        data = _run_backtest(client)
        v = data["validation"]

        assert "overall_pass" in v
        assert "passed_count" in v
        assert "total_checks" in v
        assert "checks" in v
        assert v["total_checks"] == 6
        assert len(v["checks"]) == 6

    def test_each_check_has_required_fields(self, client):
        data = _run_backtest(client)
        for check in data["validation"]["checks"]:
            assert "name" in check
            assert "threshold" in check
            assert "actual" in check
            assert "passed" in check

    def test_all_six_check_names_present(self, client):
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

    def test_synthetic_metrics_pass_all_checks(self, client):
        """The synthetic mock metrics are calibrated to pass default thresholds."""
        data = _run_backtest(client)
        v = data["validation"]
        assert v["overall_pass"] is True
        assert v["passed_count"] == 6


# ---------------------------------------------------------------------------
# 6. Router export verification
# ---------------------------------------------------------------------------


class TestRouterExport:
    """backtest_router importable from routes package."""

    def test_backtest_router_importable(self):
        from margin_api.routes import backtest_router

        assert backtest_router is not None

    def test_backtest_router_is_api_router(self):
        from fastapi import APIRouter
        from margin_api.routes import backtest_router

        assert isinstance(backtest_router, APIRouter)

    def test_backtest_router_in_all(self):
        import margin_api.routes as routes_pkg

        assert "backtest_router" in routes_pkg.__all__

    def test_schemas_importable(self):
        from margin_api.schemas import (
            BacktestConfigRequest,
            BacktestListResponse,
            BacktestResultResponse,
            BacktestSummaryResponse,
            MetricsResponse,
            ValidationCheckResponse,
            ValidationResponse,
        )

        assert BacktestConfigRequest is not None
        assert BacktestListResponse is not None
        assert BacktestResultResponse is not None
        assert BacktestSummaryResponse is not None
        assert MetricsResponse is not None
        assert ValidationCheckResponse is not None
        assert ValidationResponse is not None

    def test_schemas_in_all(self):
        import margin_api.schemas as schemas_pkg

        expected = {
            "BacktestConfigRequest",
            "BacktestListResponse",
            "BacktestResultResponse",
            "BacktestSummaryResponse",
            "MetricsResponse",
            "ValidationCheckResponse",
            "ValidationResponse",
        }
        assert expected.issubset(set(schemas_pkg.__all__))
