"""Unit tests for _inject_sector_stats helper in cli.py.

Verifies that both sector_filter_pass_rates and sector_distribution
are injected into the V4Score detail JSONB blob during the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from margin_api.cli import _inject_sector_stats
from margin_engine.models.financial import AssetProfile, GICSSector


@dataclass
class FakeTickerData:
    """Minimal stand-in for TickerV4Data (only needs .ticker and .profile.sector)."""

    ticker: str
    profile: AssetProfile


def _make_td(ticker: str, sector: GICSSector) -> FakeTickerData:
    return FakeTickerData(
        ticker=ticker,
        profile=AssetProfile(
            ticker=ticker,
            name=f"{ticker} Inc.",
            sector=sector,
            market_cap=Decimal("1000000000"),
        ),
    )


class TestInjectSectorStats:
    """Tests for _inject_sector_stats helper."""

    def test_injects_both_pass_rates_and_distributions(self):
        """Both sector_filter_pass_rates and sector_distribution should be set."""
        detail = {"ticker": "AAPL", "quality": {}}
        td_list = [_make_td("AAPL", GICSSector.TECHNOLOGY)]
        pass_rates = {"Information Technology": {"market_cap": 0.8}}
        distributions = {
            "Information Technology": {
                "roe": {"p10": 0.1, "p50": 0.2, "p90": 0.3, "count": 10},
            }
        }

        result = _inject_sector_stats(detail, "AAPL", td_list, pass_rates, distributions)

        assert result["sector_filter_pass_rates"] == pass_rates
        assert result["sector_distribution"] == distributions["Information Technology"]

    def test_distribution_keyed_by_ticker_sector(self):
        """Should inject distribution for the ticker's sector, not all sectors."""
        detail = {"ticker": "JNJ"}
        td_list = [
            _make_td("AAPL", GICSSector.TECHNOLOGY),
            _make_td("JNJ", GICSSector.HEALTHCARE),
        ]
        pass_rates = {}
        distributions = {
            "Information Technology": {
                "roe": {"p10": 0.1, "p50": 0.2, "p90": 0.3, "count": 10},
            },
            "Health Care": {
                "roe": {"p10": 0.05, "p50": 0.15, "p90": 0.25, "count": 8},
            },
        }

        result = _inject_sector_stats(detail, "JNJ", td_list, pass_rates, distributions)

        assert result["sector_distribution"] == distributions["Health Care"]
        assert result["sector_distribution"]["roe"]["p50"] == 0.15

    def test_missing_sector_gives_empty_distribution(self):
        """If the sector has no distribution data, should inject empty dict."""
        detail = {"ticker": "XOM"}
        td_list = [_make_td("XOM", GICSSector.ENERGY)]
        pass_rates = {}
        distributions = {
            "Information Technology": {
                "roe": {"p10": 0.1, "p50": 0.2, "p90": 0.3, "count": 10},
            },
        }

        result = _inject_sector_stats(detail, "XOM", td_list, pass_rates, distributions)

        assert result["sector_distribution"] == {}

    def test_ticker_not_found_in_list(self):
        """If ticker is not in ticker_data_list, detail is returned unchanged."""
        detail = {"ticker": "GHOST"}
        td_list = [_make_td("AAPL", GICSSector.TECHNOLOGY)]
        pass_rates = {"Information Technology": {"market_cap": 0.9}}
        distributions = {"Information Technology": {"roe": {"p10": 0.1}}}

        result = _inject_sector_stats(detail, "GHOST", td_list, pass_rates, distributions)

        assert "sector_filter_pass_rates" not in result
        assert "sector_distribution" not in result
