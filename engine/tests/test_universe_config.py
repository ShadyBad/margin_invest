"""Tests for universe config loading and validation."""
from __future__ import annotations

from textwrap import dedent

import pytest
from margin_engine.universe.config import load_universe_config


class TestLoadUniverseConfig:
    def test_load_valid_yaml(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        config_file.write_text(dedent("""\
            version: "2026.02.15"
            description: "Test universe"
            source: "manual"
            generated_at: "2026-02-15T12:00:00Z"
            exclusions:
              sectors:
                - "Financial Services"
                - "Real Estate"
              min_market_cap: 300000000
              min_avg_volume: 1000000
            tickers:
              - AAPL
              - MSFT
              - NVDA
        """))
        config = load_universe_config(config_file)
        assert config.version == "2026.02.15"
        assert config.ticker_count == 3
        assert "AAPL" in config.tickers
        assert "Financial Services" in config.exclusions.sectors

    def test_config_hash_deterministic(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        content = "version: '1'\ntickers:\n  - AAPL\n"
        config_file.write_text(content)
        c1 = load_universe_config(config_file)
        c2 = load_universe_config(config_file)
        assert c1.config_hash == c2.config_hash
        assert len(c1.config_hash) == 64

    def test_empty_tickers_raises(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        config_file.write_text("version: '1'\ntickers: []\n")
        with pytest.raises(ValueError, match="tickers"):
            load_universe_config(config_file)

    def test_missing_version_raises(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        config_file.write_text("tickers:\n  - AAPL\n")
        with pytest.raises(ValueError, match="version"):
            load_universe_config(config_file)

    def test_duplicate_tickers_deduplicated(self, tmp_path):
        config_file = tmp_path / "universe.yaml"
        config_file.write_text("version: '1'\ntickers:\n  - AAPL\n  - AAPL\n  - MSFT\n")
        config = load_universe_config(config_file)
        assert config.ticker_count == 2
