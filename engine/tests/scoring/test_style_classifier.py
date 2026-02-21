"""Tests for investment style classification (Value/Blend/Growth)."""

import pytest
from decimal import Decimal

from margin_engine.models.scoring import InvestmentStyle


class TestInvestmentStyleEnum:
    def test_enum_values(self):
        assert InvestmentStyle.VALUE == "value"
        assert InvestmentStyle.BLEND == "blend"
        assert InvestmentStyle.GROWTH == "growth"


class TestClassifyStyle:
    """Test majority-vote style classification across 4 signals."""

    def test_clear_value_all_signals(self):
        """Low EV/FCF percentile, low CAGR, flat earnings, low reinvestment."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=20.0,
            revenue_cagr_3yr=0.03,
            earnings_growth_accelerating=False,
            rd_capex_to_revenue=0.05,
        )
        assert style == InvestmentStyle.VALUE

    def test_clear_growth_all_signals(self):
        """High EV/FCF percentile, high CAGR, accelerating earnings, high reinvestment."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=80.0,
            revenue_cagr_3yr=0.25,
            earnings_growth_accelerating=True,
            rd_capex_to_revenue=0.20,
        )
        assert style == InvestmentStyle.GROWTH

    def test_clear_blend_middle_signals(self):
        """Middle percentile, moderate CAGR, moderate reinvestment."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=50.0,
            revenue_cagr_3yr=0.12,
            earnings_growth_accelerating=False,
            rd_capex_to_revenue=0.10,
        )
        assert style == InvestmentStyle.BLEND

    def test_non_vg_tie_defaults_to_blend(self):
        """Value/Blend tie (no pure VALUE/GROWTH split) = Blend."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        # ev_fcf=50 -> BLEND vote
        # revenue_cagr=0.03 -> VALUE vote
        # earnings_accelerating=None -> excluded
        # rd_capex=None -> excluded
        # Result: 1V, 1B -> tie with BLEND in winners -> BLEND
        style = classify_investment_style(
            ev_fcf_sector_percentile=50.0,
            revenue_cagr_3yr=0.03,
            earnings_growth_accelerating=None,
            rd_capex_to_revenue=None,
        )
        assert style == InvestmentStyle.BLEND

    def test_three_value_one_growth(self):
        """Majority Value wins."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=20.0,
            revenue_cagr_3yr=0.03,
            earnings_growth_accelerating=False,
            rd_capex_to_revenue=0.20,
        )
        assert style == InvestmentStyle.VALUE

    def test_missing_cagr_uses_three_signals(self):
        """When CAGR is None, classify from remaining 3 signals."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=80.0,
            revenue_cagr_3yr=None,
            earnings_growth_accelerating=True,
            rd_capex_to_revenue=0.20,
        )
        assert style == InvestmentStyle.GROWTH

    def test_all_none_defaults_to_blend(self):
        """When all signals are None/unknown, default to Blend."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=None,
            revenue_cagr_3yr=None,
            earnings_growth_accelerating=None,
            rd_capex_to_revenue=None,
        )
        assert style == InvestmentStyle.BLEND


class TestValueGrowthTieBreaking:
    """Test VALUE/GROWTH tie-breaking using valuation signal."""

    def test_value_growth_tie_low_valuation_breaks_to_value(self):
        """VALUE/GROWTH 2-2 split with cheap valuation -> VALUE."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        # ev_fcf=20 -> VALUE vote (and below _VALUATION_LOW=33.33)
        # revenue_cagr=0.25 -> GROWTH vote
        # earnings_accelerating=True -> GROWTH vote
        # rd_capex=0.05 -> VALUE vote
        # Result: 2V, 0B, 2G tie; ev_fcf=20 <= 33.33 -> break to VALUE
        style = classify_investment_style(
            ev_fcf_sector_percentile=20.0,
            revenue_cagr_3yr=0.25,
            earnings_growth_accelerating=True,
            rd_capex_to_revenue=0.05,
        )
        assert style == InvestmentStyle.VALUE

    def test_value_growth_tie_high_valuation_breaks_to_growth(self):
        """VALUE/GROWTH 2-2 split with expensive valuation -> GROWTH."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        # ev_fcf=80 -> GROWTH vote (and above _VALUATION_HIGH=66.67)
        # revenue_cagr=0.03 -> VALUE vote
        # earnings_accelerating=False -> VALUE vote
        # rd_capex=0.20 -> GROWTH vote
        # Result: 2V, 0B, 2G tie; ev_fcf=80 >= 66.67 -> break to GROWTH
        style = classify_investment_style(
            ev_fcf_sector_percentile=80.0,
            revenue_cagr_3yr=0.03,
            earnings_growth_accelerating=False,
            rd_capex_to_revenue=0.20,
        )
        assert style == InvestmentStyle.GROWTH

    def test_value_growth_tie_mid_valuation_stays_blend(self):
        """VALUE/GROWTH 2-2 split with mid valuation -> BLEND (no signal)."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        # ev_fcf=50 -> BLEND vote (mid-range, not a V/G-only tie)
        # revenue_cagr=0.25 -> GROWTH vote
        # earnings_accelerating=False -> VALUE vote
        # rd_capex=None -> excluded
        # Result: 1V, 1B, 1G three-way tie; BLEND in winners -> stays BLEND
        style = classify_investment_style(
            ev_fcf_sector_percentile=50.0,
            revenue_cagr_3yr=0.25,
            earnings_growth_accelerating=False,
            rd_capex_to_revenue=None,
        )
        assert style == InvestmentStyle.BLEND

    def test_value_growth_tie_no_valuation_stays_blend(self):
        """VALUE/GROWTH tie with valuation=None -> BLEND."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        # ev_fcf=None -> excluded (no vote, no tie-break data)
        # revenue_cagr=0.03 -> VALUE vote
        # earnings_accelerating=True -> GROWTH vote
        # rd_capex=None -> excluded
        # Result: 1V, 0B, 1G tie; ev_fcf is None -> can't break tie -> BLEND
        style = classify_investment_style(
            ev_fcf_sector_percentile=None,
            revenue_cagr_3yr=0.03,
            earnings_growth_accelerating=True,
            rd_capex_to_revenue=None,
        )
        assert style == InvestmentStyle.BLEND
