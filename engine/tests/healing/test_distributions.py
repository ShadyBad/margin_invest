"""Tests for compute_sector_distributions() and _compute_mad().

Covers:
- Basic computation: 5 tickers, verify median and MAD > 0
- Multiple fields: 2 tickers with 2 fields -> 2 distributions
- Single ticker: MAD is 0.0
- Empty input: returns []
- Values used as-is (contract test for raw data assumption)
"""

from __future__ import annotations

import statistics

import pytest
from margin_engine.healing.distributions import (
    _compute_mad,
    compute_sector_distributions,
)
from margin_engine.healing.models import SectorDistribution


class TestComputeMad:
    """Tests for the _compute_mad helper."""

    def test_basic_mad(self):
        """MAD of [1, 2, 3, 4, 5] = median of [2, 1, 0, 1, 2] = 1.0."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _compute_mad(values)
        assert result == 1.0

    def test_single_value_returns_zero(self):
        """Single value has no dispersion, MAD should be 0.0."""
        assert _compute_mad([42.0]) == 0.0

    def test_empty_returns_zero(self):
        """Empty list should return 0.0."""
        assert _compute_mad([]) == 0.0

    def test_two_values(self):
        """MAD of [10, 20] = median of [5, 5] = 5.0."""
        values = [10.0, 20.0]
        result = _compute_mad(values)
        # median = 15.0, abs deviations = [5.0, 5.0], median of those = 5.0
        assert result == 5.0

    def test_identical_values(self):
        """All same values should produce MAD of 0.0."""
        values = [7.0, 7.0, 7.0, 7.0]
        assert _compute_mad(values) == 0.0


class TestComputeSectorDistributions:
    """Tests for compute_sector_distributions()."""

    def test_basic_five_tickers(self):
        """5 tickers with one field: verify median, MAD > 0, and n_observations."""
        ticker_field_values = {
            "AAPL": {"roe": 0.25},
            "MSFT": {"roe": 0.30},
            "GOOG": {"roe": 0.20},
            "AMZN": {"roe": 0.15},
            "META": {"roe": 0.35},
        }
        result = compute_sector_distributions(
            ticker_field_values, sector="Information Technology", period="2026-Q1"
        )

        assert len(result) == 1
        dist = result[0]
        assert isinstance(dist, SectorDistribution)
        assert dist.sector == "Information Technology"
        assert dist.field_path == "roe"
        assert dist.period == "2026-Q1"
        assert dist.n_observations == 5

        # Median of [0.15, 0.20, 0.25, 0.30, 0.35] = 0.25
        assert dist.median == 0.25

        # MAD: abs deviations from 0.25 = [0.10, 0.05, 0.00, 0.05, 0.10]
        # Median of sorted [0.00, 0.05, 0.05, 0.10, 0.10] = 0.05
        assert dist.mad == pytest.approx(0.05)
        assert dist.mad > 0

    def test_multiple_fields_two_tickers(self):
        """2 tickers with 2 fields -> 2 SectorDistribution objects."""
        ticker_field_values = {
            "AAPL": {"roe": 0.25, "ev_fcf": 18.0},
            "MSFT": {"roe": 0.35, "ev_fcf": 22.0},
        }
        result = compute_sector_distributions(
            ticker_field_values, sector="Information Technology", period="2026-Q1"
        )

        assert len(result) == 2
        # Should be sorted by field_path
        assert result[0].field_path == "ev_fcf"
        assert result[1].field_path == "roe"

        # ev_fcf: median of [18.0, 22.0] = 20.0, MAD = median of [2.0, 2.0] = 2.0
        assert result[0].median == 20.0
        assert result[0].mad == 2.0
        assert result[0].n_observations == 2

        # roe: median of [0.25, 0.35] = 0.30, MAD = median of [0.05, 0.05] = 0.05
        assert result[1].median == pytest.approx(0.30)
        assert result[1].mad == pytest.approx(0.05)
        assert result[1].n_observations == 2

    def test_single_ticker_mad_is_zero(self):
        """Single ticker means only 1 observation, so MAD should be 0.0."""
        ticker_field_values = {
            "AAPL": {"roe": 0.25},
        }
        result = compute_sector_distributions(
            ticker_field_values, sector="Information Technology", period="2026-Q1"
        )

        assert len(result) == 1
        dist = result[0]
        assert dist.median == 0.25
        assert dist.mad == 0.0
        assert dist.n_observations == 1

    def test_empty_input_returns_empty_list(self):
        """Empty ticker_field_values should return an empty list."""
        result = compute_sector_distributions(
            {}, sector="Information Technology", period="2026-Q1"
        )
        assert result == []

    def test_values_used_as_is_raw_data_contract(self):
        """Values must be used as-is without any transformation.

        This is a contract test: the function must compute statistics
        on the exact values provided, assuming they are raw data.
        We verify by passing known values and checking exact results.
        """
        # Intentionally "extreme" values that should NOT be cleaned/clipped/transformed
        ticker_field_values = {
            "T1": {"metric": 1000.0},
            "T2": {"metric": -500.0},
            "T3": {"metric": 0.001},
        }
        result = compute_sector_distributions(
            ticker_field_values, sector="TestSector", period="2026-Q1"
        )

        assert len(result) == 1
        dist = result[0]
        # Median of [-500.0, 0.001, 1000.0] = 0.001
        assert dist.median == 0.001
        # MAD: abs deviations from 0.001 = [999.999, 0.0, 500.001]
        # sorted: [0.0, 500.001, 999.999], median = 500.001
        assert dist.mad == pytest.approx(500.001)
        assert dist.n_observations == 3

    def test_result_sorted_by_field_path(self):
        """Results must be sorted alphabetically by field_path."""
        ticker_field_values = {
            "AAPL": {"zebra": 1.0, "alpha": 2.0, "middle": 3.0},
        }
        result = compute_sector_distributions(
            ticker_field_values, sector="Test", period="2026-Q1"
        )

        field_paths = [d.field_path for d in result]
        assert field_paths == ["alpha", "middle", "zebra"]

    def test_sparse_fields_across_tickers(self):
        """Tickers may have different fields; each field uses only available values."""
        ticker_field_values = {
            "AAPL": {"roe": 0.25, "ev_fcf": 18.0},
            "MSFT": {"roe": 0.35},  # No ev_fcf
            "GOOG": {"ev_fcf": 22.0},  # No roe
        }
        result = compute_sector_distributions(
            ticker_field_values, sector="Tech", period="2026-Q1"
        )

        assert len(result) == 2
        ev_fcf_dist = next(d for d in result if d.field_path == "ev_fcf")
        roe_dist = next(d for d in result if d.field_path == "roe")

        # ev_fcf from AAPL (18.0) and GOOG (22.0)
        assert ev_fcf_dist.n_observations == 2
        assert ev_fcf_dist.median == 20.0

        # roe from AAPL (0.25) and MSFT (0.35)
        assert roe_dist.n_observations == 2
        assert roe_dist.median == pytest.approx(0.30)
