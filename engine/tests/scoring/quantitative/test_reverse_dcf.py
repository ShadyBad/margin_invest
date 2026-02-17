"""Tests for reverse DCF — implied growth rate vs sustainable growth gap."""

import pytest
from margin_engine.scoring.quantitative.reverse_dcf import (
    reverse_dcf_growth_gap,
    solve_implied_growth_rate,
)


class TestSolveImpliedGrowthRate:
    def test_known_values(self):
        """Price=100, FCF=5, WACC=10%, terminal=2.5% -> solve for implied growth."""
        implied = solve_implied_growth_rate(
            current_price=100.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        # Implied growth should be between 0% and WACC
        assert 0.0 < implied < 0.10

    def test_expensive_stock_high_implied(self):
        """High price relative to FCF -> high implied growth."""
        implied = solve_implied_growth_rate(
            current_price=500.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        assert implied > 0.10  # Market expects very high growth

    def test_cheap_stock_low_implied(self):
        """Low price relative to FCF -> low implied growth."""
        implied = solve_implied_growth_rate(
            current_price=30.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        assert implied < 0.03

    def test_negative_fcf_returns_none(self):
        implied = solve_implied_growth_rate(
            current_price=100.0,
            current_fcf=-5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        assert implied is None

    def test_zero_price_returns_none(self):
        implied = solve_implied_growth_rate(
            current_price=0.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
        )
        assert implied is None


class TestReverseDcfGrowthGap:
    def test_positive_gap_undervalued(self):
        """Sustainable growth > implied growth -> positive gap (opportunity)."""
        result = reverse_dcf_growth_gap(
            current_price=100.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.15,
        )
        assert result.name == "reverse_dcf_growth_gap"
        assert result.raw_value > 0.0

    def test_negative_gap_overvalued(self):
        """Sustainable growth < implied growth -> negative gap (no opportunity)."""
        result = reverse_dcf_growth_gap(
            current_price=500.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.05,
        )
        assert result.raw_value < 0.0

    def test_negative_fcf_returns_zero(self):
        result = reverse_dcf_growth_gap(
            current_price=100.0,
            current_fcf=-5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.15,
        )
        assert result.raw_value == 0.0

    def test_percentile_rank_placeholder(self):
        result = reverse_dcf_growth_gap(
            current_price=100.0,
            current_fcf=5.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.15,
        )
        assert result.percentile_rank == 0.0
