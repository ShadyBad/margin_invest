"""Unit tests for compute_sector_distribution() and compute_all_sector_distributions().

Tests cover:
- 10 values: P10, P50, P90 approximately correct
- 5 values: percentiles verified
- Single value: all percentiles equal that value
- Empty list: returns None
- Batch computation with mock RawScoringResult-like objects
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from margin_api.services.sector_stats import (
    compute_all_sector_distributions,
    compute_sector_distribution,
)


class TestComputeSectorDistribution:
    """Tests for the single-factor distribution computation."""

    def test_ten_values(self):
        """P10/P50/P90 of [1..10] should be close to known percentiles."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        result = compute_sector_distribution(values)

        assert result is not None
        assert result["count"] == 10
        # P10 of [1..10]: index = 9 * 0.1 = 0.9 -> 1 + 0.9 * (2-1) = 1.9
        assert result["p10"] == pytest.approx(1.9, abs=0.01)
        # P50 of [1..10]: index = 9 * 0.5 = 4.5 -> 5 + 0.5 * (6-5) = 5.5
        assert result["p50"] == pytest.approx(5.5, abs=0.01)
        # P90 of [1..10]: index = 9 * 0.9 = 8.1 -> 9 + 0.1 * (10-9) = 9.1
        assert result["p90"] == pytest.approx(9.1, abs=0.01)

    def test_five_values(self):
        """P10/P50/P90 with 5 values."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = compute_sector_distribution(values)

        assert result is not None
        assert result["count"] == 5
        # P10: index = 4 * 0.1 = 0.4 -> 10 + 0.4 * (20-10) = 14.0
        assert result["p10"] == pytest.approx(14.0, abs=0.01)
        # P50: index = 4 * 0.5 = 2.0 -> 30.0 (exact)
        assert result["p50"] == pytest.approx(30.0, abs=0.01)
        # P90: index = 4 * 0.9 = 3.6 -> 40 + 0.6 * (50-40) = 46.0
        assert result["p90"] == pytest.approx(46.0, abs=0.01)

    def test_single_value(self):
        """Single value: all percentiles should equal that value."""
        result = compute_sector_distribution([42.0])

        assert result is not None
        assert result["p10"] == 42.0
        assert result["p50"] == 42.0
        assert result["p90"] == 42.0
        assert result["count"] == 1

    def test_empty_returns_none(self):
        """Empty list should return None."""
        result = compute_sector_distribution([])
        assert result is None

    def test_two_values(self):
        """Two values: interpolation should work correctly."""
        result = compute_sector_distribution([0.0, 100.0])

        assert result is not None
        assert result["count"] == 2
        # P10: index = 1 * 0.1 = 0.1 -> 0 + 0.1 * (100-0) = 10.0
        assert result["p10"] == pytest.approx(10.0, abs=0.01)
        # P50: index = 1 * 0.5 = 0.5 -> 0 + 0.5 * 100 = 50.0
        assert result["p50"] == pytest.approx(50.0, abs=0.01)
        # P90: index = 1 * 0.9 = 0.9 -> 0 + 0.9 * 100 = 90.0
        assert result["p90"] == pytest.approx(90.0, abs=0.01)

    def test_unsorted_input(self):
        """Input need not be pre-sorted; function sorts internally."""
        values = [50.0, 10.0, 30.0, 40.0, 20.0]
        result = compute_sector_distribution(values)

        assert result is not None
        assert result["count"] == 5
        # Should produce the same result as sorted input
        sorted_result = compute_sector_distribution(sorted(values))
        assert result == sorted_result

    def test_rounding(self):
        """Values should be rounded to 4 decimal places."""
        values = [1.0, 2.0, 3.0]
        result = compute_sector_distribution(values)

        assert result is not None
        # All values should have at most 4 decimal places
        for key in ("p10", "p50", "p90"):
            str_val = str(result[key])
            if "." in str_val:
                decimal_places = len(str_val.split(".")[1])
                assert decimal_places <= 4


# ---------------------------------------------------------------------------
# Mock objects for compute_all_sector_distributions
# ---------------------------------------------------------------------------


@dataclass
class MockFactorScore:
    """Lightweight stand-in for engine FactorScore."""

    name: str
    raw_value: float
    percentile_rank: float = 0.0


@dataclass
class MockRawScoringResult:
    """Lightweight stand-in for RawScoringResult."""

    ticker: str
    sector: str
    quality_scores: list[MockFactorScore] = field(default_factory=list)
    value_scores: list[MockFactorScore] = field(default_factory=list)
    momentum_scores: list[MockFactorScore] = field(default_factory=list)


class TestComputeAllSectorDistributions:
    """Tests for the batch sector distribution computation."""

    def test_single_sector_single_factor(self):
        """One sector, one quality sub-factor, two tickers."""
        raw_results = [
            MockRawScoringResult(
                ticker="AAPL",
                sector="Information Technology",
                quality_scores=[MockFactorScore(name="roe", raw_value=0.25)],
            ),
            MockRawScoringResult(
                ticker="MSFT",
                sector="Information Technology",
                quality_scores=[MockFactorScore(name="roe", raw_value=0.35)],
            ),
        ]

        result = compute_all_sector_distributions(raw_results)

        assert "Information Technology" in result
        assert "roe" in result["Information Technology"]
        dist = result["Information Technology"]["roe"]
        assert dist["count"] == 2
        assert dist["p50"] == pytest.approx(0.30, abs=0.01)

    def test_multiple_sectors(self):
        """Two different sectors should produce separate distributions."""
        raw_results = [
            MockRawScoringResult(
                ticker="AAPL",
                sector="Information Technology",
                quality_scores=[MockFactorScore(name="roe", raw_value=0.25)],
            ),
            MockRawScoringResult(
                ticker="JNJ",
                sector="Health Care",
                quality_scores=[MockFactorScore(name="roe", raw_value=0.15)],
            ),
        ]

        result = compute_all_sector_distributions(raw_results)

        assert "Information Technology" in result
        assert "Health Care" in result
        assert result["Information Technology"]["roe"]["count"] == 1
        assert result["Health Care"]["roe"]["count"] == 1

    def test_multiple_factor_categories(self):
        """Quality, value, and momentum sub-factors should all appear."""
        raw_results = [
            MockRawScoringResult(
                ticker="AAPL",
                sector="Information Technology",
                quality_scores=[MockFactorScore(name="roe", raw_value=0.25)],
                value_scores=[MockFactorScore(name="ev_fcf", raw_value=15.0)],
                momentum_scores=[MockFactorScore(name="price_mom", raw_value=0.10)],
            ),
            MockRawScoringResult(
                ticker="MSFT",
                sector="Information Technology",
                quality_scores=[MockFactorScore(name="roe", raw_value=0.35)],
                value_scores=[MockFactorScore(name="ev_fcf", raw_value=20.0)],
                momentum_scores=[MockFactorScore(name="price_mom", raw_value=0.05)],
            ),
        ]

        result = compute_all_sector_distributions(raw_results)
        sector = result["Information Technology"]

        assert "roe" in sector
        assert "ev_fcf" in sector
        assert "price_mom" in sector
        assert sector["roe"]["count"] == 2
        assert sector["ev_fcf"]["count"] == 2
        assert sector["price_mom"]["count"] == 2

    def test_empty_raw_results(self):
        """Empty input should produce empty output."""
        result = compute_all_sector_distributions([])
        assert result == {}

    def test_no_scores_on_result(self):
        """Result with empty score lists should produce nothing."""
        raw_results = [
            MockRawScoringResult(
                ticker="AAPL",
                sector="Information Technology",
            ),
        ]
        result = compute_all_sector_distributions(raw_results)
        assert result == {}
