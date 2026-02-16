"""Tests for universe API endpoints."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest


class TestUniverseStatusSchema:
    def test_universe_status_model(self):
        from margin_api.schemas.universe import UniverseStatusResponse

        status = UniverseStatusResponse(
            universe_version="2026.02.15",
            universe_size=4847,
            assets_ingested=4812,
            assets_scored=4790,
            assets_fresh=4780,
            assets_stale=10,
            assets_expired=0,
            assets_quarantined=8,
            assets_permanently_skipped=3,
            ingestion_coverage=0.993,
            scoring_coverage=0.988,
            last_ingestion_run=datetime.now(UTC),
            last_scoring_run=datetime.now(UTC),
            is_complete=True,
        )
        assert status.is_complete is True
        assert status.ingestion_coverage == 0.993


class TestUniverseSummarySchema:
    def test_universe_summary_model(self):
        from margin_api.schemas.universe import UniverseSummary

        summary = UniverseSummary(
            version="2026.02.15",
            size=4847,
            scoring_coverage=0.988,
            is_complete=True,
            last_scoring_run=datetime.now(UTC),
        )
        data = summary.model_dump()
        assert data["version"] == "2026.02.15"
        assert data["is_complete"] is True


class TestWarningSchema:
    def test_warning_model(self):
        from margin_api.schemas.universe import Warning

        w = Warning(code="LOW_COVERAGE", message="Only 30% scored", severity="error")
        assert w.code == "LOW_COVERAGE"
        assert w.severity == "error"
