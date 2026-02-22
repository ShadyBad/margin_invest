"""Tests for Opportunity Type classifier."""

from margin_engine.models.scoring import OpportunityType
from margin_engine.scoring.opportunity_classifier import classify_opportunity_type


class TestClassifyOpportunityType:
    def test_compounder(self):
        """High stable ROIC + high reinvestment = Compounder."""
        result = classify_opportunity_type(
            roic_5yr_median=0.20,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_intrinsic_ratio=0.9,  # slightly below IV
            has_catalyst=False,
            roic_improving=False,
        )
        assert result == OpportunityType.COMPOUNDER

    def test_mispricing(self):
        """Deep discount + quality floor + catalyst = Mispricing."""
        result = classify_opportunity_type(
            roic_5yr_median=0.10,
            roic_cv=0.40,
            reinvestment_rate=0.15,
            price_to_intrinsic_ratio=0.5,  # 50% of IV
            has_catalyst=True,
            roic_improving=True,
        )
        assert result == OpportunityType.MISPRICING

    def test_both(self):
        """Meets both criteria = Both."""
        result = classify_opportunity_type(
            roic_5yr_median=0.25,
            roic_cv=0.10,
            reinvestment_rate=0.50,
            price_to_intrinsic_ratio=0.5,
            has_catalyst=True,
            roic_improving=False,
        )
        assert result == OpportunityType.BOTH

    def test_neither(self):
        """Meets neither = Neither."""
        result = classify_opportunity_type(
            roic_5yr_median=0.06,
            roic_cv=0.50,
            reinvestment_rate=0.10,
            price_to_intrinsic_ratio=0.8,
            has_catalyst=False,
            roic_improving=False,
        )
        assert result == OpportunityType.NEITHER
