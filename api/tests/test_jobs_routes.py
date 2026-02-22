"""Tests for jobs API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime


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
            error_message=None,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        assert job.job_type == "full_ingest"
        assert job.progress == 1.0
