"""Tests for earnings revision momentum (stub for future data source)."""

from margin_engine.scoring.quantitative.earnings_revision import (
    earnings_revision_momentum,
)


def test_positive_revisions():
    """Upward revisions should produce positive score."""
    result = earnings_revision_momentum(
        fy1_estimate_current=5.00,
        fy1_estimate_90d_ago=4.50,
        fy2_estimate_current=6.00,
        fy2_estimate_90d_ago=5.50,
    )
    assert result.raw_value > 0
    assert result.name == "earnings_revision"


def test_negative_revisions():
    result = earnings_revision_momentum(
        fy1_estimate_current=4.00,
        fy1_estimate_90d_ago=5.00,
        fy2_estimate_current=5.00,
        fy2_estimate_90d_ago=6.00,
    )
    assert result.raw_value < 0


def test_missing_data_returns_zero():
    """When no estimates available, return 0."""
    result = earnings_revision_momentum()
    assert result.raw_value == 0.0
    assert "no estimates" in result.detail.lower()
