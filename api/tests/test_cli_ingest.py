"""Tests for the ingest CLI command enforcement logic."""

from __future__ import annotations

import pytest


class TestIngestEnforcement:
    def test_ingest_requires_active_snapshot(self):
        from margin_api.cli import validate_ingest_preconditions

        with pytest.raises(SystemExit, match="No active universe snapshot"):
            validate_ingest_preconditions(active_snapshot=None, tickers_override=None)

    def test_ingest_with_tickers_override_skips_snapshot_check(self):
        from margin_api.cli import validate_ingest_preconditions

        # Should not raise
        validate_ingest_preconditions(active_snapshot=None, tickers_override=["AAPL", "MSFT"])

    def test_ingest_determines_full_run_type(self):
        from margin_api.cli import determine_run_type

        assert determine_run_type(tickers_override=None) == "full"

    def test_ingest_determines_subset_run_type(self):
        from margin_api.cli import determine_run_type

        assert determine_run_type(tickers_override=["AAPL"]) == "subset"
