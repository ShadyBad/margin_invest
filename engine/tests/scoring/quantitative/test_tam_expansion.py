"""Tests for tam_expansion_velocity factor."""

from __future__ import annotations

import pytest
from margin_engine.scoring.quantitative.tam_expansion import tam_expansion_velocity


def _pts(*year_revenue_pairs: tuple[int, float]) -> list[dict]:
    """Build segment_revenues list from (year, revenue) pairs."""
    return [{"year": y, "revenue": r} for y, r in year_revenue_pairs]


class TestTAMExpansionVelocity:
    # ------------------------------------------------------------------
    # Spec: gaining share -> high score (>5)
    # ------------------------------------------------------------------
    def test_gaining_share_high_score(self):
        """Company 20% CAGR in 10% industry -> velocity=2.0 -> score=10."""
        pts = _pts((2021, 100.0), (2022, 120.0), (2023, 144.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10, lookback_years=3)
        assert result is not None
        assert result.raw_value > 5.0

    def test_gaining_share_exact_velocity_2(self):
        """Exactly 20% CAGR in 10% industry -> velocity=2.0 -> score=10.0."""
        # 2-year CAGR: (144/100)^(1/2) - 1 = 0.2 exactly
        pts = _pts((2021, 100.0), (2023, 144.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10, lookback_years=3)
        assert result is not None
        assert result.raw_value == pytest.approx(10.0)

    # ------------------------------------------------------------------
    # Spec: losing share -> low score (<5)
    # ------------------------------------------------------------------
    def test_losing_share_low_score(self):
        """Company 2% CAGR in 10% industry -> velocity=0.2 -> score=1.0."""
        # 3-year CAGR: (1.02)^3 - 1 ≈ 6.1% over 3 years. Use point approach.
        # first=100, last = 100 * 1.02^3 ≈ 106.12
        pts = _pts((2020, 100.0), (2023, 106.12))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10, lookback_years=3)
        assert result is not None
        assert result.raw_value < 5.0

    def test_losing_share_score_below_5(self):
        """2% CAGR vs 10% industry = velocity 0.2 -> score 1.0."""
        pts = _pts((2021, 100.0), (2022, 102.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10, lookback_years=3)
        assert result is not None
        # velocity = 0.02/0.10 = 0.2; score = 0.2/2.0 * 10 = 1.0
        assert result.raw_value == pytest.approx(1.0)

    # ------------------------------------------------------------------
    # Spec: insufficient data -> None
    # ------------------------------------------------------------------
    def test_empty_list_returns_none(self):
        result = tam_expansion_velocity([], industry_growth_rate=0.10)
        assert result is None

    def test_single_point_returns_none(self):
        result = tam_expansion_velocity(
            [{"year": 2023, "revenue": 100.0}], industry_growth_rate=0.10
        )
        assert result is None

    # ------------------------------------------------------------------
    # Spec: zero industry growth -> safe division -> valid result
    # ------------------------------------------------------------------
    def test_zero_industry_growth_safe_division(self):
        """industry_growth_rate=0.0 should not raise — uses floor 0.01."""
        pts = _pts((2021, 100.0), (2022, 110.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.0)
        assert result is not None
        # velocity = 0.10 / 0.01 = 10.0; score = min(10/2, 1)*10 = 10
        assert result.raw_value == pytest.approx(10.0)

    def test_negative_industry_growth_safe(self):
        """Negative industry rate uses floor 0.01 — no crash."""
        pts = _pts((2021, 100.0), (2022, 110.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=-0.05)
        assert result is not None
        assert 0.0 <= result.raw_value <= 10.0

    # ------------------------------------------------------------------
    # Spec: exactly at industry rate -> velocity=1.0 -> score=5.0
    # ------------------------------------------------------------------
    def test_at_industry_rate_score_5(self):
        """Company CAGR equals industry rate -> velocity=1.0 -> score=5.0."""
        # 10% 1-year growth in 10% industry
        pts = _pts((2022, 100.0), (2023, 110.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10, lookback_years=3)
        assert result is not None
        assert result.raw_value == pytest.approx(5.0)

    # ------------------------------------------------------------------
    # Additional edge cases
    # ------------------------------------------------------------------
    def test_metadata_keys_present(self):
        pts = _pts((2021, 100.0), (2022, 120.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10)
        assert result is not None
        assert result.metadata is not None
        assert "company_cagr" in result.metadata
        assert "industry_growth_rate" in result.metadata
        assert "velocity" in result.metadata
        assert "years" in result.metadata

    def test_factor_name(self):
        pts = _pts((2021, 100.0), (2022, 120.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10)
        assert result is not None
        assert result.name == "tam_expansion_velocity"

    def test_score_capped_at_10(self):
        """Very fast growing company -> score capped at 10."""
        pts = _pts((2020, 10.0), (2023, 1000.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.05)
        assert result is not None
        assert result.raw_value == pytest.approx(10.0)

    def test_score_floored_at_0(self):
        """Declining company -> score floored at 0, not negative."""
        pts = _pts((2021, 100.0), (2022, 50.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10)
        assert result is not None
        assert result.raw_value >= 0.0

    def test_unsorted_input_still_works(self):
        """Revenue points given out of year order are sorted internally."""
        pts = [
            {"year": 2023, "revenue": 144.0},
            {"year": 2021, "revenue": 100.0},
        ]
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10)
        assert result is not None
        assert result.raw_value == pytest.approx(10.0)

    def test_two_points_minimum(self):
        """Exactly 2 points returns a valid result."""
        pts = _pts((2022, 100.0), (2023, 110.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10)
        assert result is not None
        assert result.raw_value == pytest.approx(5.0)

    def test_percentile_rank_zero(self):
        """percentile_rank is always 0.0 (filled by composite scorer)."""
        pts = _pts((2022, 100.0), (2023, 120.0))
        result = tam_expansion_velocity(pts, industry_growth_rate=0.10)
        assert result is not None
        assert result.percentile_rank == pytest.approx(0.0)
