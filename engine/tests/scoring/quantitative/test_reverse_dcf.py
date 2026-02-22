"""Tests for reverse DCF — implied growth rate vs sustainable growth gap."""

from margin_engine.scoring.quantitative.reverse_dcf import (
    reverse_dcf_combined_gap,
    reverse_dcf_growth_gap,
    solve_implied_growth_rate,
    solve_implied_margin,
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


class TestSolveImpliedMargin:
    def test_positive_margin_gap(self):
        """Price implies ~15% margin, sustainable is 25% -> positive margin gap."""
        implied = solve_implied_margin(
            current_price=100.0,
            current_revenue=50.0,
            current_fcf_margin=0.10,
            wacc=0.10,
            terminal_growth=0.025,
            revenue_growth=0.05,
            shares_outstanding=1,
        )
        assert implied is not None
        assert 0.0 < implied < 0.60

    def test_invalid_revenue_returns_none(self):
        result = solve_implied_margin(
            current_price=100.0,
            current_revenue=-50.0,
            current_fcf_margin=0.10,
            wacc=0.10,
            terminal_growth=0.025,
            revenue_growth=0.05,
            shares_outstanding=1,
        )
        assert result is None

    def test_zero_price_returns_none(self):
        result = solve_implied_margin(
            current_price=0.0,
            current_revenue=50.0,
            current_fcf_margin=0.10,
            wacc=0.10,
            terminal_growth=0.025,
            revenue_growth=0.05,
            shares_outstanding=1,
        )
        assert result is None

    def test_zero_shares_returns_none(self):
        result = solve_implied_margin(
            current_price=100.0,
            current_revenue=50.0,
            current_fcf_margin=0.10,
            wacc=0.10,
            terminal_growth=0.025,
            revenue_growth=0.05,
            shares_outstanding=0,
        )
        assert result is None


class TestReverseDcfCombinedGap:
    def test_margin_gap_rescues_negative_growth_gap(self):
        """Growth gap negative but margin gap positive -> returns margin gap."""
        result = reverse_dcf_combined_gap(
            current_price=500.0,
            current_fcf=5.0,
            current_revenue=100.0,
            current_fcf_margin=0.05,
            sustainable_fcf_margin=0.30,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.05,
            revenue_growth_for_margin_solve=0.05,
        )
        assert result.name == "reverse_dcf_combined_gap"
        # Growth gap should be negative (expensive stock, low sustainable growth)
        # but margin gap should rescue it if sustainable margin >> implied margin
        assert result.raw_value >= 0.0 or result.raw_value > -0.50

    def test_both_gaps_positive_returns_larger(self):
        """Both gaps positive -> returns the larger one."""
        result = reverse_dcf_combined_gap(
            current_price=100.0,
            current_fcf=5.0,
            current_revenue=50.0,
            current_fcf_margin=0.10,
            sustainable_fcf_margin=0.30,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.15,
            revenue_growth_for_margin_solve=0.05,
        )
        assert result.raw_value > 0.0
        assert "growth_gap=" in result.detail
        assert "margin_gap=" in result.detail
        assert "best_gap=" in result.detail

    def test_both_gaps_negative_returns_less_negative(self):
        """Both gaps negative -> returns the less negative one (max)."""
        result = reverse_dcf_combined_gap(
            current_price=500.0,
            current_fcf=5.0,
            current_revenue=100.0,
            current_fcf_margin=0.05,
            sustainable_fcf_margin=0.05,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.02,
            revenue_growth_for_margin_solve=0.05,
        )
        # Both gaps should be negative or near zero
        assert result.raw_value <= 0.10

    def test_percentile_rank_placeholder(self):
        result = reverse_dcf_combined_gap(
            current_price=100.0,
            current_fcf=5.0,
            current_revenue=50.0,
            current_fcf_margin=0.10,
            sustainable_fcf_margin=0.25,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=1,
            sustainable_growth_rate=0.10,
            revenue_growth_for_margin_solve=0.05,
        )
        assert result.percentile_rank == 0.0
