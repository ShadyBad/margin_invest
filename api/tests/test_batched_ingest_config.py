"""Tests for batched ingest configuration variables."""

from __future__ import annotations

from margin_api.config import Settings


class TestBatchedIngestConfig:
    def test_default_batch_size(self):
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            _env_file=None,
        )
        assert s.ingest_batch_size == 50

    def test_default_rate_limit(self):
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            _env_file=None,
        )
        assert s.ingest_rate_limit == 36

    def test_default_ingest_concurrency(self):
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            _env_file=None,
        )
        assert s.ingest_concurrency == 3

    def test_default_worker_max_jobs(self):
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            _env_file=None,
        )
        assert s.worker_max_jobs == 2

    def test_custom_values(self, monkeypatch):
        monkeypatch.setenv("MARGIN_INGEST_BATCH_SIZE", "100")
        monkeypatch.setenv("MARGIN_INGEST_RATE_LIMIT", "24")
        monkeypatch.setenv("MARGIN_INGEST_CONCURRENCY", "2")
        monkeypatch.setenv("MARGIN_WORKER_MAX_JOBS", "1")
        s = Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            _env_file=None,
        )
        assert s.ingest_batch_size == 100
        assert s.ingest_rate_limit == 24
        assert s.ingest_concurrency == 2
        assert s.worker_max_jobs == 1
