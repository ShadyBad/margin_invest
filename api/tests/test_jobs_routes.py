"""Tests for jobs API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.db.models import IngestionRun, JobRun
from margin_api.db.session import get_db


class TestJobRunResponse:
    def test_job_run_response_model(self):
        from margin_api.routes.jobs import JobRunResponse

        job = JobRunResponse(
            id=1,
            job_type="full_ingest",
            status="completed",
            progress=1.0,
            progress_detail="Done",
            triggered_by="schedule",
            parent_job_id=None,
            pipeline_id="abc123",
            error_message=None,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        assert job.job_type == "full_ingest"
        assert job.progress == 1.0
        assert job.pipeline_id == "abc123"


class TestPipelineStatusEndpoint:
    def _make_client(self, mock_session):
        app = create_app()

        async def mock_get_db():
            return mock_session

        app.dependency_overrides[get_db] = mock_get_db
        return TestClient(app)

    def test_pipeline_status_returns_all_stages(self):
        """GET /jobs/pipeline/{id} returns ingest + scoring stages."""
        now = datetime.now(UTC)

        mock_ingest = MagicMock(spec=IngestionRun)
        mock_ingest.status = "completed"
        mock_ingest.started_at = now
        mock_ingest.completed_at = now

        mock_v2 = MagicMock(spec=JobRun)
        mock_v2.job_type = "score_v2"
        mock_v2.status = "completed"
        mock_v2.started_at = now
        mock_v2.completed_at = now
        mock_v2.error_message = None

        mock_v3 = MagicMock(spec=JobRun)
        mock_v3.job_type = "score_v3"
        mock_v3.status = "completed"
        mock_v3.started_at = now
        mock_v3.completed_at = now
        mock_v3.error_message = None

        # Mock session with two different queries
        mock_session = AsyncMock()
        ingest_result = MagicMock()
        ingest_result.scalar_one_or_none.return_value = mock_ingest
        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = [mock_v2, mock_v3]

        mock_session.execute = AsyncMock(side_effect=[ingest_result, jobs_result])

        client = self._make_client(mock_session)
        response = client.get("/api/v1/jobs/pipeline/pipe-123")

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline_id"] == "pipe-123"
        assert data["status"] == "completed"
        assert len(data["stages"]) == 3
        assert data["stages"][0]["stage"] == "ingest"
        assert data["stages"][1]["stage"] == "score_v2"
        assert data["stages"][2]["stage"] == "score_v3"

    def test_pipeline_status_shows_running_when_stage_running(self):
        """Pipeline status is 'running' when any stage is still running."""
        now = datetime.now(UTC)

        mock_ingest = MagicMock(spec=IngestionRun)
        mock_ingest.status = "completed"
        mock_ingest.started_at = now
        mock_ingest.completed_at = now

        mock_v2 = MagicMock(spec=JobRun)
        mock_v2.job_type = "score_v2"
        mock_v2.status = "running"
        mock_v2.started_at = now
        mock_v2.completed_at = None
        mock_v2.error_message = None

        mock_session = AsyncMock()
        ingest_result = MagicMock()
        ingest_result.scalar_one_or_none.return_value = mock_ingest
        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = [mock_v2]

        mock_session.execute = AsyncMock(side_effect=[ingest_result, jobs_result])

        client = self._make_client(mock_session)
        response = client.get("/api/v1/jobs/pipeline/pipe-running")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_pipeline_status_shows_failed_when_stage_failed(self):
        """Pipeline status is 'failed' when any stage has failed."""
        now = datetime.now(UTC)

        mock_ingest = MagicMock(spec=IngestionRun)
        mock_ingest.status = "completed"
        mock_ingest.started_at = now
        mock_ingest.completed_at = now

        mock_v2 = MagicMock(spec=JobRun)
        mock_v2.job_type = "score_v2"
        mock_v2.status = "failed"
        mock_v2.started_at = now
        mock_v2.completed_at = now
        mock_v2.error_message = "Something broke"

        mock_v3 = MagicMock(spec=JobRun)
        mock_v3.job_type = "score_v3"
        mock_v3.status = "completed"
        mock_v3.started_at = now
        mock_v3.completed_at = now
        mock_v3.error_message = None

        mock_session = AsyncMock()
        ingest_result = MagicMock()
        ingest_result.scalar_one_or_none.return_value = mock_ingest
        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = [mock_v2, mock_v3]

        mock_session.execute = AsyncMock(side_effect=[ingest_result, jobs_result])

        client = self._make_client(mock_session)
        response = client.get("/api/v1/jobs/pipeline/pipe-fail")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["stages"][1]["error_message"] == "Something broke"

    def test_pipeline_status_404_for_unknown_pipeline(self):
        """Returns 404 when no pipeline matches the ID."""
        mock_session = AsyncMock()
        ingest_result = MagicMock()
        ingest_result.scalar_one_or_none.return_value = None
        jobs_result = MagicMock()
        jobs_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[ingest_result, jobs_result])

        client = self._make_client(mock_session)
        response = client.get("/api/v1/jobs/pipeline/nonexistent")

        assert response.status_code == 404
