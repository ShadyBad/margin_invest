"""Tests for Tier 2 MAD-based outlier detection."""

from __future__ import annotations

import pytest

from margin_engine.healing.detection import _get_threshold, _is_monotonic, detect_tier2
from margin_engine.healing.models import (
    DetectionSeverity,
    HealingConfig,
    SectorDistribution,
)


def _make_dist(
    field_path: str,
    median: float = 0.15,
    mad: float = 0.02,
    sector: str = "Technology",
    n_observations: int = 50,
    period: str = "2025-Q4",
) -> SectorDistribution:
    """Helper to build a SectorDistribution."""
    return SectorDistribution(
        sector=sector,
        field_path=field_path,
        median=median,
        mad=mad,
        n_observations=n_observations,
        period=period,
    )


class TestIsMonotonic:
    """Tests for the _is_monotonic helper."""

    def test_monotonic_increasing(self) -> None:
        assert _is_monotonic([1.0, 2.0, 3.0]) is True

    def test_monotonic_decreasing(self) -> None:
        assert _is_monotonic([3.0, 2.0, 1.0]) is True

    def test_not_monotonic(self) -> None:
        assert _is_monotonic([1.0, 3.0, 2.0]) is False

    def test_too_few_values(self) -> None:
        assert _is_monotonic([1.0, 2.0]) is False

    def test_empty_list(self) -> None:
        assert _is_monotonic([]) is False

    def test_constant_values_not_monotonic(self) -> None:
        assert _is_monotonic([2.0, 2.0, 2.0]) is False


class TestGetThreshold:
    """Tests for _get_threshold field class lookup."""

    def test_margins_field(self) -> None:
        config = HealingConfig()
        assert _get_threshold("income_statement.gross_margin", config) == 6.0

    def test_growth_rates_field(self) -> None:
        config = HealingConfig()
        assert _get_threshold("derived.revenue_growth", config) == 8.0

    def test_leverage_ratios_field(self) -> None:
        config = HealingConfig()
        assert _get_threshold("balance_sheet.debt_to_equity", config) == 7.0

    def test_unknown_field_defaults_to_growth_rates(self) -> None:
        config = HealingConfig()
        assert _get_threshold("some.unknown.field", config) == 8.0


class TestDetectTier2:
    """Tests for detect_tier2 MAD-based outlier detection."""

    def test_value_within_threshold_not_flagged(self) -> None:
        """Value at 3 MADs from median with threshold 6 should NOT be flagged."""
        config = HealingConfig()
        dist = _make_dist("income_statement.gross_margin", median=0.15, mad=0.02)
        # deviation = |0.21 - 0.15| / 0.02 = 3.0, threshold = 6.0
        results = detect_tier2(
            field_values={"income_statement.gross_margin": 0.21},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 0

    def test_value_beyond_threshold_flagged(self) -> None:
        """Value at 7 MADs from median with threshold 6 should be flagged."""
        config = HealingConfig()
        dist = _make_dist("income_statement.gross_margin", median=0.15, mad=0.02)
        # deviation = |0.29 - 0.15| / 0.02 = 7.0, threshold = 6.0
        results = detect_tier2(
            field_values={"income_statement.gross_margin": 0.29},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 1
        assert results[0].field_path == "income_statement.gross_margin"
        assert results[0].severity == DetectionSeverity.OUTLIER
        assert results[0].mad_deviation == pytest.approx(7.0)
        assert results[0].original_value == 0.29

    def test_negative_deviation_flagged(self) -> None:
        """Negative deviation (value below median) at 7 MADs should be flagged."""
        config = HealingConfig()
        dist = _make_dist("income_statement.gross_margin", median=0.15, mad=0.02)
        # deviation = |0.01 - 0.15| / 0.02 = 7.0, threshold = 6.0
        results = detect_tier2(
            field_values={"income_statement.gross_margin": 0.01},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 1
        assert results[0].severity == DetectionSeverity.OUTLIER
        assert results[0].mad_deviation == pytest.approx(7.0)

    def test_growth_rate_uses_higher_threshold(self) -> None:
        """Growth rate at 7 MADs should NOT be flagged (threshold is 8.0)."""
        config = HealingConfig()
        dist = _make_dist("derived.revenue_growth", median=0.10, mad=0.05)
        # deviation = |0.45 - 0.10| / 0.05 = 7.0, threshold = 8.0
        results = detect_tier2(
            field_values={"derived.revenue_growth": 0.45},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 0

    def test_growth_rate_at_9_mads_flagged(self) -> None:
        """Growth rate at 9 MADs should be flagged (threshold is 8.0)."""
        config = HealingConfig()
        dist = _make_dist("derived.revenue_growth", median=0.10, mad=0.05)
        # deviation = |0.55 - 0.10| / 0.05 = 9.0, threshold = 8.0
        results = detect_tier2(
            field_values={"derived.revenue_growth": 0.55},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 1
        assert results[0].mad_deviation == pytest.approx(9.0)

    def test_unknown_field_uses_growth_rate_threshold(self) -> None:
        """Unknown field should use growth_rates threshold (most conservative, 8.0)."""
        config = HealingConfig()
        dist = _make_dist("some.unknown.field", median=100.0, mad=10.0)
        # deviation = |170.0 - 100.0| / 10.0 = 7.0, threshold = 8.0 (growth_rates)
        results = detect_tier2(
            field_values={"some.unknown.field": 170.0},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 0

        # deviation = |190.0 - 100.0| / 10.0 = 9.0, threshold = 8.0
        results = detect_tier2(
            field_values={"some.unknown.field": 190.0},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 1

    def test_zero_mad_skips_field(self) -> None:
        """Field with MAD == 0.0 should be skipped (no division by zero)."""
        config = HealingConfig()
        dist = _make_dist("income_statement.gross_margin", median=0.15, mad=0.0)
        results = detect_tier2(
            field_values={"income_statement.gross_margin": 999.0},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 0

    def test_missing_distribution_skips_field(self) -> None:
        """Field with no matching distribution should be skipped."""
        config = HealingConfig()
        dist = _make_dist("income_statement.net_margin", median=0.10, mad=0.01)
        results = detect_tier2(
            field_values={"income_statement.gross_margin": 999.0},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 0

    def test_monotonic_trend_widens_threshold(self) -> None:
        """Monotonic trailing values should widen threshold by 1.5x.

        Margins threshold = 6.0, with 1.5x multiplier = 9.0.
        7 MADs should NOT be flagged.
        """
        config = HealingConfig()
        dist = _make_dist("income_statement.gross_margin", median=0.15, mad=0.02)
        # deviation = |0.29 - 0.15| / 0.02 = 7.0
        # Normal threshold = 6.0 → would flag
        # Monotonic trend threshold = 6.0 * 1.5 = 9.0 → not flagged
        results = detect_tier2(
            field_values={"income_statement.gross_margin": 0.29},
            sector_distributions=[dist],
            config=config,
            trailing_values={"income_statement.gross_margin": [0.20, 0.25, 0.29]},
        )
        assert len(results) == 0

    def test_non_monotonic_trend_uses_normal_threshold(self) -> None:
        """Non-monotonic trailing values should NOT widen threshold.

        Margins threshold = 6.0.
        7 MADs should still be flagged.
        """
        config = HealingConfig()
        dist = _make_dist("income_statement.gross_margin", median=0.15, mad=0.02)
        # deviation = |0.29 - 0.15| / 0.02 = 7.0, threshold = 6.0 (not widened)
        results = detect_tier2(
            field_values={"income_statement.gross_margin": 0.29},
            sector_distributions=[dist],
            config=config,
            trailing_values={"income_statement.gross_margin": [0.25, 0.20, 0.29]},
        )
        assert len(results) == 1
        assert results[0].mad_deviation == pytest.approx(7.0)

    def test_multiple_fields_independently_checked(self) -> None:
        """Each field is checked independently; one flagged, one not."""
        config = HealingConfig()
        dists = [
            _make_dist("income_statement.gross_margin", median=0.15, mad=0.02),
            _make_dist("derived.revenue_growth", median=0.10, mad=0.05),
        ]
        results = detect_tier2(
            field_values={
                "income_statement.gross_margin": 0.29,  # 7 MADs > 6.0 threshold
                "derived.revenue_growth": 0.45,  # 7 MADs < 8.0 threshold
            },
            sector_distributions=dists,
            config=config,
        )
        assert len(results) == 1
        assert results[0].field_path == "income_statement.gross_margin"

    def test_trailing_values_too_few_no_widening(self) -> None:
        """Trailing values with fewer than 3 entries should not widen threshold."""
        config = HealingConfig()
        dist = _make_dist("income_statement.gross_margin", median=0.15, mad=0.02)
        # 7 MADs, threshold 6.0 → flagged (no widening because only 2 trailing values)
        results = detect_tier2(
            field_values={"income_statement.gross_margin": 0.29},
            sector_distributions=[dist],
            config=config,
            trailing_values={"income_statement.gross_margin": [0.25, 0.29]},
        )
        assert len(results) == 1

    def test_detail_message_includes_useful_info(self) -> None:
        """Detection result detail should include deviation and threshold."""
        config = HealingConfig()
        dist = _make_dist("income_statement.gross_margin", median=0.15, mad=0.02)
        results = detect_tier2(
            field_values={"income_statement.gross_margin": 0.29},
            sector_distributions=[dist],
            config=config,
        )
        assert len(results) == 1
        assert "7.0" in results[0].detail or "7.00" in results[0].detail
        assert "6.0" in results[0].detail or "6.00" in results[0].detail
