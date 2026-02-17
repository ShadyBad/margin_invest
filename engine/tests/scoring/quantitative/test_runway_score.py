"""Tests for runway score factor (revenue penetration of sub-industry)."""

from decimal import Decimal

import pytest
from margin_engine.scoring.quantitative.runway_score import runway_score


class TestRunwayScore:
    def test_small_fish_big_pond(self):
        """1% penetration → low raw_value (lots of runway)."""
        score = runway_score(
            company_revenue=Decimal("100"),
            sub_industry_revenue=Decimal("10000"),
        )
        assert score.name == "runway_score"
        assert score.raw_value == pytest.approx(0.01, abs=1e-4)

    def test_big_fish_small_pond(self):
        """83% penetration → high raw_value (little runway)."""
        score = runway_score(
            company_revenue=Decimal("8300"),
            sub_industry_revenue=Decimal("10000"),
        )
        assert score.raw_value == pytest.approx(0.83, abs=1e-4)

    def test_zero_industry_revenue(self):
        """Zero industry revenue → 1.0 (saturated)."""
        score = runway_score(
            company_revenue=Decimal("100"),
            sub_industry_revenue=Decimal("0"),
        )
        assert score.raw_value == 1.0

    def test_missing_industry_data(self):
        """None sub_industry_revenue → 0.5 (neutral)."""
        score = runway_score(
            company_revenue=Decimal("100"),
            sub_industry_revenue=None,
        )
        assert score.raw_value == 0.5

    def test_percentile_rank_always_zero(self):
        """Percentile rank is always 0.0 (placeholder)."""
        score = runway_score(
            company_revenue=Decimal("100"),
            sub_industry_revenue=Decimal("10000"),
        )
        assert score.percentile_rank == 0.0
