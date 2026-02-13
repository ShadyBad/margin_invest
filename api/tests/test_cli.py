"""Tests for the data seed CLI constants and structure."""

from __future__ import annotations

from margin_api.cli import SECTOR_MAP, SP500_TICKERS


class TestSP500Tickers:
    def test_nonempty_list(self):
        assert isinstance(SP500_TICKERS, list)
        assert len(SP500_TICKERS) > 0

    def test_all_uppercase_strings(self):
        for ticker in SP500_TICKERS:
            assert isinstance(ticker, str), f"{ticker} is not a string"
            assert ticker == ticker.upper(), f"{ticker} is not uppercase"

    def test_includes_known_tickers(self):
        known = {"AAPL", "MSFT", "GOOGL", "JPM", "XOM"}
        actual = set(SP500_TICKERS)
        missing = known - actual
        assert not missing, f"Missing known tickers: {missing}"

    def test_no_duplicates(self):
        assert len(SP500_TICKERS) == len(set(SP500_TICKERS))

    def test_roughly_50_tickers(self):
        # Task spec says ~50; ensure within a reasonable range.
        assert 40 <= len(SP500_TICKERS) <= 60


class TestSectorMap:
    def test_contains_all_expected_mappings(self):
        expected_keys = {
            "Technology",
            "Healthcare",
            "Financial Services",
            "Consumer Cyclical",
            "Consumer Defensive",
            "Energy",
            "Industrials",
            "Basic Materials",
            "Real Estate",
            "Utilities",
            "Communication Services",
        }
        assert set(SECTOR_MAP.keys()) == expected_keys

    def test_maps_to_gics_sector_values(self):
        expected_values = {
            "Information Technology",
            "Health Care",
            "Financials",
            "Consumer Discretionary",
            "Consumer Staples",
            "Energy",
            "Industrials",
            "Materials",
            "Real Estate",
            "Utilities",
            "Communication Services",
        }
        assert set(SECTOR_MAP.values()) == expected_values

    def test_technology_maps_to_information_technology(self):
        assert SECTOR_MAP["Technology"] == "Information Technology"

    def test_healthcare_maps_to_health_care(self):
        assert SECTOR_MAP["Healthcare"] == "Health Care"

    def test_financial_services_maps_to_financials(self):
        assert SECTOR_MAP["Financial Services"] == "Financials"

    def test_consumer_cyclical_maps_to_consumer_discretionary(self):
        assert SECTOR_MAP["Consumer Cyclical"] == "Consumer Discretionary"

    def test_consumer_defensive_maps_to_consumer_staples(self):
        assert SECTOR_MAP["Consumer Defensive"] == "Consumer Staples"
