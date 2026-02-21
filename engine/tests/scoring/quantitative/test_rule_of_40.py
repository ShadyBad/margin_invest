"""Tests for Rule of 40 factor."""

import pytest
from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40


class TestRuleOf40:
    def test_balanced(self):
        """20% growth + 20% margin = 40.0."""
        result = rule_of_40(revenue_growth_rate=0.20, fcf_margin=0.20)
        assert result.raw_value == pytest.approx(40.0, rel=1e-6)
        assert result.name == "rule_of_40"
        assert result.percentile_rank == 0.0

    def test_high_growth_low_profit(self):
        """40% growth + (-5%) margin = 35.0."""
        result = rule_of_40(revenue_growth_rate=0.40, fcf_margin=-0.05)
        assert result.raw_value == pytest.approx(35.0, rel=1e-6)

    def test_low_growth_high_profit(self):
        """5% growth + 30% margin = 35.0."""
        result = rule_of_40(revenue_growth_rate=0.05, fcf_margin=0.30)
        assert result.raw_value == pytest.approx(35.0, rel=1e-6)

    def test_exceptional(self):
        """30% growth + 25% margin = 55.0."""
        result = rule_of_40(revenue_growth_rate=0.30, fcf_margin=0.25)
        assert result.raw_value == pytest.approx(55.0, rel=1e-6)

    def test_negative(self):
        """-10% growth + (-5%) margin = -15.0."""
        result = rule_of_40(revenue_growth_rate=-0.10, fcf_margin=-0.05)
        assert result.raw_value == pytest.approx(-15.0, rel=1e-6)
