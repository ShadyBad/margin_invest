"""Tests for universe screener — yfinance-based ticker discovery."""
from __future__ import annotations

import pytest

from margin_engine.universe.screener import (
    filter_universe,
    generate_universe_yaml,
)


class TestFilterUniverse:
    def test_excludes_financial_services(self):
        tickers = [
            {"ticker": "AAPL", "sector": "Technology", "market_cap": 3e12, "avg_volume_dollar": 5e9},
            {"ticker": "JPM", "sector": "Financial Services", "market_cap": 5e11, "avg_volume_dollar": 2e9},
        ]
        result = filter_universe(tickers, excluded_sectors=["Financial Services", "Real Estate"])
        assert len(result) == 1
        assert result[0] == "AAPL"

    def test_excludes_below_market_cap(self):
        tickers = [
            {"ticker": "AAPL", "sector": "Technology", "market_cap": 3e12, "avg_volume_dollar": 5e9},
            {"ticker": "TINY", "sector": "Technology", "market_cap": 1e8, "avg_volume_dollar": 5e6},
        ]
        result = filter_universe(tickers, min_market_cap=300_000_000)
        assert result == ["AAPL"]

    def test_excludes_below_volume(self):
        tickers = [
            {"ticker": "AAPL", "sector": "Technology", "market_cap": 3e12, "avg_volume_dollar": 5e9},
            {"ticker": "ILLIQ", "sector": "Technology", "market_cap": 1e9, "avg_volume_dollar": 500_000},
        ]
        result = filter_universe(tickers, min_avg_volume=1_000_000)
        assert result == ["AAPL"]


class TestGenerateUniverseYaml:
    def test_generates_valid_yaml(self):
        tickers = ["AAPL", "MSFT", "NVDA"]
        yaml_str = generate_universe_yaml(
            tickers=tickers,
            excluded_sectors=["Financial Services", "Real Estate"],
            min_market_cap=300_000_000,
            min_avg_volume=1_000_000,
        )
        assert "version:" in yaml_str
        assert "AAPL" in yaml_str
        assert "MSFT" in yaml_str
        assert "Financial Services" in yaml_str
