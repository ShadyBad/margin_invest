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


class TestIngestionStatusResponse:
    def test_status_response_model(self):
        from margin_api.routes.ingestion import IngestionStatusResponse

        resp = IngestionStatusResponse(
            universe_version="1.0",
            total_tickers=8000,
            fresh_tickers=7600,
            quarantined_tickers=50,
            coverage_pct=95.0,
            last_run=None,
        )
        assert resp.coverage_pct == 95.0
        assert resp.quarantined_tickers == 50

    def test_status_response_with_no_universe(self):
        from margin_api.routes.ingestion import IngestionStatusResponse

        resp = IngestionStatusResponse(
            universe_version=None,
            total_tickers=0,
            fresh_tickers=0,
            quarantined_tickers=0,
            coverage_pct=0.0,
            last_run=None,
        )
        assert resp.universe_version is None


class TestCompletenessResponse:
    def test_ready_response(self):
        from margin_api.routes.ingestion import CompletenessResponse

        resp = CompletenessResponse(
            ready=True,
            coverage_pct=95.2,
            scored_tickers=7616,
            total_tickers=8000,
            reason=None,
            message=None,
        )
        assert resp.ready is True

    def test_not_ready_response(self):
        from margin_api.routes.ingestion import CompletenessResponse

        resp = CompletenessResponse(
            ready=False,
            coverage_pct=52.5,
            scored_tickers=4200,
            total_tickers=8000,
            reason="incomplete_ingestion",
            message="Only 4200/8000 tickers scored. Need 90% coverage.",
        )
        assert resp.ready is False
        assert resp.reason == "incomplete_ingestion"
