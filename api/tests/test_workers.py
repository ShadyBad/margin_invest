"""Tests for ARQ worker configuration."""
from __future__ import annotations

from margin_api.workers import WorkerSettings


class TestWorkerSettings:
    def test_has_redis_settings(self):
        assert WorkerSettings.redis_settings is not None

    def test_has_functions(self):
        assert len(WorkerSettings.functions) >= 3

    def test_has_cron_jobs(self):
        assert len(WorkerSettings.cron_jobs) >= 2

    def test_function_names(self):
        names = [f.__name__ for f in WorkerSettings.functions]
        assert "full_ingest" in names
        assert "full_score" in names
        assert "backtest_validate" in names
        assert "live_price_poll" in names
        assert "retry_quarantined" in names
