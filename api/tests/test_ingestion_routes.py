"""Tests for ingestion runs API endpoints."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest


class TestIngestionRunResponse:
    def test_ingestion_run_response_model(self):
        from margin_api.routes.ingestion import IngestionRunResponse

        run = IngestionRunResponse(
            id=1,
            snapshot_id=1,
            run_type="full",
            tickers_requested=5000,
            tickers_succeeded=4800,
            tickers_failed=150,
            tickers_skipped=50,
            status="completed",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_seconds=3600.5,
        )
        assert run.run_type == "full"
        assert run.tickers_requested == 5000
