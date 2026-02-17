"""Tests for asymmetry ratio factor (upside/downside structure)."""

import pytest
from margin_engine.scoring.quantitative.asymmetry import asymmetry_ratio


class TestAsymmetryRatio:
    def test_strong_asymmetry(self):
        """Strong upside vs limited downside → high ratio (~4x)."""
        # IV=100, Price=50, Floor=max(10, 5, 0)=10
        # Ratio = (100 - 50) / (50 - 10) = 50 / 40 = 1.25
        score = asymmetry_ratio(
            intrinsic_value=100.0,
            current_price=50.0,
            net_cash_per_share=10.0,
            tangible_book_per_share=5.0,
        )
        assert score.name == "asymmetry_ratio"
        assert score.raw_value == pytest.approx(1.25, abs=0.01)

    def test_weak_asymmetry(self):
        """Small upside vs large downside → low ratio (< 1x)."""
        # IV=55, Price=50, Floor=max(5, 3, 0)=5
        # Ratio = (55 - 50) / (50 - 5) = 5 / 45 ≈ 0.111
        score = asymmetry_ratio(
            intrinsic_value=55.0,
            current_price=50.0,
            net_cash_per_share=5.0,
            tangible_book_per_share=3.0,
        )
        assert score.raw_value == pytest.approx(0.111, abs=0.01)

    def test_overvalued(self):
        """Intrinsic < price → 0.0."""
        score = asymmetry_ratio(
            intrinsic_value=40.0,
            current_price=50.0,
            net_cash_per_share=10.0,
            tangible_book_per_share=5.0,
        )
        assert score.raw_value == 0.0

    def test_negative_floor_uses_zero(self):
        """Negative net_cash and tangible_book → floor = 0."""
        # IV=100, Price=50, Floor=max(-10, -20, 0)=0
        # Ratio = (100 - 50) / (50 - 0) = 50 / 50 = 1.0
        score = asymmetry_ratio(
            intrinsic_value=100.0,
            current_price=50.0,
            net_cash_per_share=-10.0,
            tangible_book_per_share=-20.0,
        )
        assert score.raw_value == pytest.approx(1.0, abs=0.01)

    def test_floor_equals_price_capped(self):
        """Floor >= price → ratio = 100.0 (capped)."""
        # Floor = max(50, 60, 0) = 60 >= Price = 50
        # Downside = 0 or negative → cap at 100.0
        score = asymmetry_ratio(
            intrinsic_value=100.0,
            current_price=50.0,
            net_cash_per_share=50.0,
            tangible_book_per_share=60.0,
        )
        assert score.raw_value == 100.0

    def test_percentile_rank_always_zero(self):
        """Percentile rank is always 0.0 (placeholder)."""
        score = asymmetry_ratio(
            intrinsic_value=100.0,
            current_price=50.0,
            net_cash_per_share=10.0,
            tangible_book_per_share=5.0,
        )
        assert score.percentile_rank == 0.0
