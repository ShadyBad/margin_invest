"""Unit tests for compute_sector_filter_pass_rates()."""

from __future__ import annotations

from margin_api.services.sector_stats import compute_sector_filter_pass_rates


class TestComputeSectorFilterPassRates:
    def test_two_tickers_same_sector_both_pass(self):
        """Two tickers in same sector both pass a filter -> rate 1.0."""
        data = [
            ("Information Technology", [{"name": "liquidity", "passed": True}]),
            ("Information Technology", [{"name": "liquidity", "passed": True}]),
        ]
        result = compute_sector_filter_pass_rates(data)
        assert result == {"Information Technology": {"liquidity": 1.0}}

    def test_one_pass_one_fail_gives_half(self):
        """One pass + one fail in same sector -> rate 0.5."""
        data = [
            ("Financials", [{"name": "market_cap", "passed": True}]),
            ("Financials", [{"name": "market_cap", "passed": False}]),
        ]
        result = compute_sector_filter_pass_rates(data)
        assert result == {"Financials": {"market_cap": 0.5}}

    def test_different_sectors_dont_mix(self):
        """Filters from different sectors are tracked independently."""
        data = [
            ("Information Technology", [{"name": "liquidity", "passed": True}]),
            ("Health Care", [{"name": "liquidity", "passed": False}]),
        ]
        result = compute_sector_filter_pass_rates(data)
        assert result["Information Technology"]["liquidity"] == 1.0
        assert result["Health Care"]["liquidity"] == 0.0

    def test_empty_input_returns_empty(self):
        """Empty input -> empty dict."""
        result = compute_sector_filter_pass_rates([])
        assert result == {}

    def test_multiple_filters_per_ticker(self):
        """Multiple filters per ticker are tracked separately."""
        data = [
            (
                "Energy",
                [
                    {"name": "liquidity", "passed": True},
                    {"name": "market_cap", "passed": False},
                ],
            ),
            (
                "Energy",
                [
                    {"name": "liquidity", "passed": True},
                    {"name": "market_cap", "passed": True},
                ],
            ),
        ]
        result = compute_sector_filter_pass_rates(data)
        assert result["Energy"]["liquidity"] == 1.0
        assert result["Energy"]["market_cap"] == 0.5

    def test_missing_passed_key_treated_as_false(self):
        """If 'passed' key is missing, treat as False."""
        data = [
            ("Financials", [{"name": "volume"}]),
        ]
        result = compute_sector_filter_pass_rates(data)
        assert result["Financials"]["volume"] == 0.0
