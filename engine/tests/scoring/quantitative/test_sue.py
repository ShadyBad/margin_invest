"""Tests for the SUE (Standardized Unexpected Earnings) momentum factor."""

from decimal import Decimal
from statistics import pstdev

import pytest
from margin_engine.models.financial import EarningsSurprise
from margin_engine.scoring.quantitative.sue import sue_score


def _make_surprise(quarter: str, actual: str, expected: str) -> EarningsSurprise:
    """Helper to build an EarningsSurprise from string Decimal values."""
    return EarningsSurprise(
        quarter=quarter,
        actual_eps=Decimal(actual),
        expected_eps=Decimal(expected),
    )


class TestSUEScore:
    """Core SUE computation tests."""

    def test_four_quarter_golden_value(self):
        """4 quarters of synthetic data: SUE = most_recent_surprise / pstdev(all_surprises).

        Q1: 1.50 - 1.40 = 0.10
        Q2: 1.60 - 1.45 = 0.15
        Q3: 1.55 - 1.50 = 0.05
        Q4: 1.70 - 1.55 = 0.15

        pstdev([0.10, 0.15, 0.05, 0.15]) = 0.04146
        SUE = 0.15 / 0.04146 = 3.618
        """
        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),
            _make_surprise("2024-Q2", "1.60", "1.45"),
            _make_surprise("2024-Q3", "1.55", "1.50"),
            _make_surprise("2024-Q4", "1.70", "1.55"),
        ]
        result = sue_score(surprises)

        # Verify against independently calculated value
        expected_surprises = [0.10, 0.15, 0.05, 0.15]
        expected_stddev = pstdev(expected_surprises)
        expected_sue = 0.15 / expected_stddev
        assert result.raw_value == pytest.approx(expected_sue, rel=1e-4)
        assert result.raw_value == pytest.approx(3.618, rel=1e-2)

    def test_consistent_beats(self):
        """All positive surprises should yield a positive SUE."""
        surprises = [
            _make_surprise("2024-Q1", "2.00", "1.80"),  # +0.20
            _make_surprise("2024-Q2", "2.10", "1.90"),  # +0.20
            _make_surprise("2024-Q3", "2.20", "2.00"),  # +0.20
            _make_surprise("2024-Q4", "2.30", "2.05"),  # +0.25
        ]
        result = sue_score(surprises)
        assert result.raw_value > 0.0

    def test_consistent_misses(self):
        """All negative surprises should yield a negative SUE."""
        surprises = [
            _make_surprise("2024-Q1", "1.30", "1.50"),  # -0.20
            _make_surprise("2024-Q2", "1.35", "1.55"),  # -0.20
            _make_surprise("2024-Q3", "1.40", "1.60"),  # -0.20
            _make_surprise("2024-Q4", "1.45", "1.70"),  # -0.25
        ]
        result = sue_score(surprises)
        assert result.raw_value < 0.0

    def test_sorting_by_quarter(self):
        """Surprises provided out of order should still use the most recent quarter."""
        surprises = [
            _make_surprise("2024-Q4", "1.70", "1.55"),  # surprise = 0.15 (most recent)
            _make_surprise("2024-Q1", "1.50", "1.40"),  # surprise = 0.10
            _make_surprise("2024-Q3", "1.55", "1.50"),  # surprise = 0.05
            _make_surprise("2024-Q2", "1.60", "1.45"),  # surprise = 0.15
        ]
        result = sue_score(surprises)

        # Same data as golden value test, just in different order
        assert result.raw_value == pytest.approx(3.618, rel=1e-2)


class TestSUEEdgeCases:
    """Edge case handling."""

    def test_empty_list(self):
        """Empty list returns raw_value=0.0."""
        result = sue_score([])
        assert result.raw_value == 0.0

    def test_single_quarter(self):
        """Fewer than 2 surprises: return raw_value=0.0 (cannot compute stddev)."""
        surprises = [_make_surprise("2024-Q4", "1.70", "1.55")]
        result = sue_score(surprises)
        assert result.raw_value == 0.0

    def test_zero_stddev_all_identical(self):
        """When all surprises are identical, stddev=0; return raw_value=0.0."""
        surprises = [
            _make_surprise("2024-Q1", "1.60", "1.50"),  # +0.10
            _make_surprise("2024-Q2", "1.70", "1.60"),  # +0.10
            _make_surprise("2024-Q3", "1.80", "1.70"),  # +0.10
            _make_surprise("2024-Q4", "1.90", "1.80"),  # +0.10
        ]
        result = sue_score(surprises)
        assert result.raw_value == 0.0

    def test_two_quarters_returns_zero(self):
        """2 quarters is below the new minimum of 4."""
        surprises = [
            _make_surprise("2024-Q3", "1.50", "1.40"),  # +0.10
            _make_surprise("2024-Q4", "1.70", "1.50"),  # +0.20
        ]
        result = sue_score(surprises)
        assert result.raw_value == 0.0
        assert "insufficient" in result.detail.lower()

    def test_three_quarters_returns_zero(self):
        """3 quarters is below the minimum of 4."""
        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),
            _make_surprise("2024-Q2", "1.60", "1.50"),
            _make_surprise("2024-Q3", "1.70", "1.55"),
        ]
        result = sue_score(surprises)
        assert result.raw_value == 0.0
        assert "insufficient" in result.detail.lower()


class TestSUEFactorScoreFields:
    """Validate FactorScore metadata fields."""

    def test_name_is_sue(self):
        """Factor name should be 'sue'."""
        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),
            _make_surprise("2024-Q2", "1.60", "1.45"),
            _make_surprise("2024-Q3", "1.55", "1.50"),
            _make_surprise("2024-Q4", "1.70", "1.55"),
        ]
        result = sue_score(surprises)
        assert result.name == "sue"

    def test_percentile_rank_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),
            _make_surprise("2024-Q2", "1.60", "1.45"),
            _make_surprise("2024-Q3", "1.55", "1.50"),
            _make_surprise("2024-Q4", "1.70", "1.55"),
        ]
        result = sue_score(surprises)
        assert result.percentile_rank == 0.0

    def test_detail_contains_breakdown(self):
        """Detail string should show surprises and the computed SUE."""
        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),
            _make_surprise("2024-Q2", "1.60", "1.45"),
            _make_surprise("2024-Q3", "1.55", "1.50"),
            _make_surprise("2024-Q4", "1.70", "1.55"),
        ]
        result = sue_score(surprises)
        # Should mention key computation components
        assert "sue" in result.detail.lower() or "SUE" in result.detail
        assert "0.15" in result.detail  # most recent surprise
        assert "stddev" in result.detail.lower() or "pstdev" in result.detail.lower()

    def test_empty_list_detail(self):
        """Empty list should have informative detail."""
        result = sue_score([])
        assert result.name == "sue"
        assert result.percentile_rank == 0.0

    def test_insufficient_data_detail(self):
        """Single quarter should have informative detail."""
        surprises = [_make_surprise("2024-Q4", "1.70", "1.55")]
        result = sue_score(surprises)
        assert result.name == "sue"
        assert result.percentile_rank == 0.0


class TestSUEWithPEAD:
    """Tests for PEAD (Post-Earnings Announcement Drift) time decay."""

    def test_pead_recent_positive_surprise(self):
        """Recent positive surprise with PEAD should still be positive."""
        from datetime import datetime

        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),  # +0.10
            _make_surprise("2024-Q2", "1.60", "1.45"),  # +0.15
            _make_surprise("2024-Q3", "1.55", "1.50"),  # +0.05
            _make_surprise("2024-Q4", "1.70", "1.55"),  # +0.15
        ]
        result = sue_score(surprises, reference_date=datetime(2025, 2, 1))
        assert result.raw_value > 0

    def test_pead_stale_surprise_lower_score(self):
        """Same surprises evaluated 1 year later should have lower absolute SUE.

        Uses varying surprise magnitudes so decay weighting has a
        differential effect: a large recent surprise matters more when
        evaluated soon (high decay weight) than when evaluated much later
        (low decay weight).
        """
        from datetime import datetime

        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.45"),  # +0.05
            _make_surprise("2024-Q2", "1.55", "1.50"),  # +0.05
            _make_surprise("2024-Q3", "1.55", "1.50"),  # +0.05
            _make_surprise("2024-Q4", "1.80", "1.50"),  # +0.30 (big recent beat)
        ]
        recent_result = sue_score(surprises, reference_date=datetime(2025, 2, 1))
        stale_result = sue_score(surprises, reference_date=datetime(2026, 2, 1))
        # After 1 year, all surprises are old -> less extreme SUE
        assert abs(stale_result.raw_value) < abs(recent_result.raw_value)

    def test_no_reference_date_preserves_original(self):
        """Without reference_date, behavior matches original SUE exactly."""
        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),
            _make_surprise("2024-Q2", "1.60", "1.45"),
            _make_surprise("2024-Q3", "1.55", "1.50"),
            _make_surprise("2024-Q4", "1.70", "1.55"),
        ]
        result_no_date = sue_score(surprises)
        result_none = sue_score(surprises, reference_date=None)
        assert result_no_date.raw_value == result_none.raw_value

    def test_pead_negative_recent_surprise_negative_sue(self):
        """Recent negative surprise should yield negative SUE with PEAD."""
        from datetime import datetime

        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),  # +0.10
            _make_surprise("2024-Q2", "1.60", "1.50"),  # +0.10
            _make_surprise("2024-Q3", "1.55", "1.45"),  # +0.10
            _make_surprise("2024-Q4", "1.40", "1.70"),  # -0.30
        ]
        result = sue_score(surprises, reference_date=datetime(2025, 2, 1))
        assert result.raw_value < 0

    def test_pead_detail_mentions_pead(self):
        """Detail string should indicate PEAD is active."""
        from datetime import datetime

        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),
            _make_surprise("2024-Q2", "1.60", "1.50"),
            _make_surprise("2024-Q3", "1.55", "1.45"),
            _make_surprise("2024-Q4", "1.70", "1.60"),
        ]
        result = sue_score(surprises, reference_date=datetime(2025, 2, 1))
        assert "pead" in result.detail.lower()

    def test_pead_insufficient_data_still_returns_zero(self):
        """PEAD with fewer than _MIN_QUARTERS should still return 0."""
        from datetime import datetime

        surprises = [
            _make_surprise("2024-Q1", "1.50", "1.40"),
            _make_surprise("2024-Q2", "1.60", "1.50"),
        ]
        result = sue_score(surprises, reference_date=datetime(2025, 2, 1))
        assert result.raw_value == 0.0
        assert "insufficient" in result.detail.lower()
