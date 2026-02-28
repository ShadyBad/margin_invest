"""Tests for admin model validation routes."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.models import MlModelRun, SeedValidationReport
from margin_api.db.session import get_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_and_client(
    admin_key: str = "test-admin-key",
    db_override=None,
) -> tuple:
    """Create app and client with admin key and optional DB override."""
    get_settings.cache_clear()
    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": admin_key}):
        app = create_app()
        if db_override is not None:
            app.dependency_overrides[get_db] = db_override
        client = TestClient(app)
    return app, client


def _make_mock_db_override(mock_session):
    """Build a get_db dependency override that returns the given mock session."""

    async def _override():
        return mock_session

    return _override


def _make_report(
    run_group_id: str = "rg-abc-123",
    n_seeds: int = 5,
    gate_passed: bool = True,
    selected_seed: int = 42,
    created_at: datetime | None = None,
) -> MagicMock:
    """Create a mock SeedValidationReport."""
    report = MagicMock(spec=SeedValidationReport)
    report.id = 1
    report.run_group_id = run_group_id
    report.created_at = created_at or datetime(2026, 2, 27, 10, 0, 0, tzinfo=UTC)
    report.n_seeds = n_seeds
    report.gate_passed = gate_passed
    report.selected_seed = selected_seed
    report.metric_distributions = {
        "rank_ic": {
            "mean": 0.20,
            "median": 0.19,
            "std": 0.02,
            "min": 0.17,
            "max": 0.24,
            "ci_lower": 0.16,
            "ci_upper": 0.24,
            "cv": 0.10,
        },
    }
    report.gate_details = {
        "overall": {"passed": True},
        "median_rank_ic": {
            "value": 0.19,
            "threshold": 0.15,
            "passed": True,
        },
        "cv_rank_ic": {
            "value": 0.10,
            "threshold": 0.30,
            "passed": True,
        },
    }
    report.previous_comparison = None
    report.environment_snapshot = {
        "python_version": "3.13.5",
        "numpy_version": "1.26.0",
    }
    return report


def _make_ml_run(
    seed: int = 42,
    run_group_id: str = "rg-abc-123",
    rank_ic: float = 0.20,
    n_clusters: int = 3,
    n_samples: int = 100,
) -> MagicMock:
    """Create a mock MlModelRun."""
    run = MagicMock(spec=MlModelRun)
    run.seed = seed
    run.overall_rank_ic = rank_ic
    run.n_clusters = n_clusters
    run.n_samples = n_samples
    run.run_group_id = run_group_id
    return run


class _MockExecuteResult:
    """Flexible mock for session.execute() that handles both scalar and scalars queries."""

    def __init__(
        self,
        report: MagicMock | None = None,
        reports_list: list | None = None,
        runs_list: list | None = None,
        count: int | None = None,
    ):
        self._report = report
        self._reports_list = reports_list or []
        self._runs_list = runs_list or []
        self._count = count
        self._call_count = 0

    def build_responses(self) -> list:
        """Build a list of mock results in the order they'll be called."""
        responses: list = []

        if self._count is not None:
            # Count query comes first (for history endpoint)
            count_result = MagicMock()
            count_result.scalar.return_value = self._count
            responses.append(count_result)

        if self._report is not None:
            # Single report query
            report_result = MagicMock()
            report_result.scalar_one_or_none.return_value = self._report
            responses.append(report_result)
            # Seed details query follows
            runs_result = MagicMock()
            runs_result.scalars.return_value.all.return_value = self._runs_list
            responses.append(runs_result)
        elif self._reports_list:
            # Multiple reports query (history)
            reports_result = MagicMock()
            reports_result.scalars.return_value.all.return_value = self._reports_list
            responses.append(reports_result)
            # Each report gets a seed details query
            for _ in self._reports_list:
                runs_result = MagicMock()
                runs_result.scalars.return_value.all.return_value = self._runs_list
                responses.append(runs_result)
        elif self._count is not None and not self._reports_list:
            # Empty history
            reports_result = MagicMock()
            reports_result.scalars.return_value.all.return_value = []
            responses.append(reports_result)

        return responses


def _build_mock_session(
    report: MagicMock | None = None,
    reports_list: list | None = None,
    runs_list: list | None = None,
    count: int | None = None,
) -> AsyncMock:
    """Build a mock AsyncSession with ordered execute responses."""
    builder = _MockExecuteResult(
        report=report,
        reports_list=reports_list,
        runs_list=runs_list,
        count=count,
    )
    responses = builder.build_responses()

    call_idx = {"i": 0}

    async def mock_execute(stmt):
        idx = call_idx["i"]
        call_idx["i"] += 1
        if idx < len(responses):
            return responses[idx]
        # Fallback: return empty
        fallback = MagicMock()
        fallback.scalar_one_or_none.return_value = None
        fallback.scalar.return_value = 0
        fallback.scalars.return_value.all.return_value = []
        return fallback

    session = AsyncMock()
    session.execute = mock_execute
    return session


# ---------------------------------------------------------------------------
# Tests: GET /latest
# ---------------------------------------------------------------------------


class TestGetLatestReport:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_latest_no_reports_returns_404(self):
        """GET /latest returns 404 when no validation reports exist."""
        mock_session = _build_mock_session(report=None)
        # Override to return None for scalar_one_or_none
        report_result = MagicMock()
        report_result.scalar_one_or_none.return_value = None

        async def mock_execute(stmt):
            return report_result

        mock_session.execute = mock_execute

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/model-validation/latest",
            headers={"X-Admin-Key": "test-key"},
        )
        assert response.status_code == 404

    def test_latest_returns_report(self):
        """GET /latest returns 200 with the most recent report."""
        report = _make_report()
        runs = [
            _make_ml_run(seed=1, rank_ic=0.18, n_clusters=3, n_samples=100),
            _make_ml_run(seed=42, rank_ic=0.22, n_clusters=4, n_samples=100),
        ]
        mock_session = _build_mock_session(report=report, runs_list=runs)

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/model-validation/latest",
            headers={"X-Admin-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["run_group_id"] == "rg-abc-123"
        assert data["n_seeds"] == 5
        assert data["gate_passed"] is True
        assert data["selected_seed"] == 42
        assert "rank_ic" in data["metric_distributions"]
        assert data["metric_distributions"]["rank_ic"]["mean"] == 0.20
        assert len(data["gate_checks"]) == 2  # overall is skipped
        assert data["gate_checks"][0]["name"] == "median_rank_ic"
        assert len(data["seed_details"]) == 2
        assert data["seed_details"][1]["selected"] is True  # seed=42

    def test_latest_with_comparison(self):
        """GET /latest includes comparison when previous_comparison is set."""
        report = _make_report()
        report.previous_comparison = {
            "p_value": 0.03,
            "effect_size": 0.45,
            "significant": True,
            "label": "candidate vs incumbent",
            "n_compared": 5,
            "mean_difference": 0.05,
        }
        runs = [_make_ml_run()]
        mock_session = _build_mock_session(report=report, runs_list=runs)

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/model-validation/latest",
            headers={"X-Admin-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["comparison"] is not None
        assert data["comparison"]["p_value"] == 0.03
        assert data["comparison"]["significant"] is True


# ---------------------------------------------------------------------------
# Tests: GET /history
# ---------------------------------------------------------------------------


class TestGetValidationHistory:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_history_returns_paginated_list(self):
        """GET /history returns paginated reports with total count."""
        report1 = _make_report(run_group_id="rg-1")
        report2 = _make_report(run_group_id="rg-2")
        runs = [_make_ml_run()]

        mock_session = _build_mock_session(
            reports_list=[report1, report2],
            runs_list=runs,
            count=2,
        )

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/model-validation/history",
            headers={"X-Admin-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["reports"]) == 2

    def test_history_empty(self):
        """GET /history returns empty list with total=0 when no reports."""
        mock_session = _build_mock_session(count=0)

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/model-validation/history",
            headers={"X-Admin-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["reports"] == []


# ---------------------------------------------------------------------------
# Tests: GET /{run_group_id}
# ---------------------------------------------------------------------------


class TestGetReportByRunGroupId:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_get_existing_report(self):
        """GET /{run_group_id} returns 200 for existing report."""
        report = _make_report(run_group_id="rg-specific")
        runs = [_make_ml_run(seed=42, run_group_id="rg-specific")]
        mock_session = _build_mock_session(report=report, runs_list=runs)

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/model-validation/rg-specific",
            headers={"X-Admin-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["run_group_id"] == "rg-specific"

    def test_get_nonexistent_report_returns_404(self):
        """GET /{run_group_id} returns 404 for nonexistent report."""
        report_result = MagicMock()
        report_result.scalar_one_or_none.return_value = None

        async def mock_execute(stmt):
            return report_result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        _, client = _make_app_and_client(
            admin_key="test-key",
            db_override=_make_mock_db_override(mock_session),
        )
        response = client.get(
            "/api/v1/admin/model-validation/nonexistent-id",
            headers={"X-Admin-Key": "test-key"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Authentication
# ---------------------------------------------------------------------------


class TestModelValidationAuth:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_latest_requires_admin_key(self):
        """GET /latest without X-Admin-Key returns 422."""
        _, client = _make_app_and_client(admin_key="test-key")
        response = client.get("/api/v1/admin/model-validation/latest")
        assert response.status_code == 422

    def test_latest_rejects_wrong_key(self):
        """GET /latest with wrong admin key returns 403."""
        _, client = _make_app_and_client(admin_key="correct-key")
        response = client.get(
            "/api/v1/admin/model-validation/latest",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 403

    def test_history_requires_admin_key(self):
        """GET /history without X-Admin-Key returns 422."""
        _, client = _make_app_and_client(admin_key="test-key")
        response = client.get("/api/v1/admin/model-validation/history")
        assert response.status_code == 422

    def test_history_rejects_wrong_key(self):
        """GET /history with wrong admin key returns 403."""
        _, client = _make_app_and_client(admin_key="correct-key")
        response = client.get(
            "/api/v1/admin/model-validation/history",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 403

    def test_specific_report_requires_admin_key(self):
        """GET /{run_group_id} without X-Admin-Key returns 422."""
        _, client = _make_app_and_client(admin_key="test-key")
        response = client.get("/api/v1/admin/model-validation/some-id")
        assert response.status_code == 422

    def test_specific_report_rejects_wrong_key(self):
        """GET /{run_group_id} with wrong admin key returns 403."""
        _, client = _make_app_and_client(admin_key="correct-key")
        response = client.get(
            "/api/v1/admin/model-validation/some-id",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 403
