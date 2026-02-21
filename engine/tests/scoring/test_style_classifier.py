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

    def test_tie_defaults_to_blend(self):
        """2 Value signals + 2 Growth signals = Blend."""
        from margin_engine.scoring.style_classifier import classify_investment_style

        style = classify_investment_style(
            ev_fcf_sector_percentile=20.0,
            revenue_cagr_3yr=0.25,
            earnings_growth_accelerating=True,
            rd_capex_to_revenue=0.05,
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
