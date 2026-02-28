"""Tests for data quality gating."""

from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.data_quality_gate import apply_data_quality_gate


def test_high_coverage_no_cap():
    """data_coverage >= 0.8 should not cap conviction."""
    result = apply_data_quality_gate(
        conviction=CompositeTier.EXCEPTIONAL,
        data_coverage=0.95,
    )
    assert result == CompositeTier.EXCEPTIONAL


def test_low_coverage_caps_exceptional():
    """data_coverage < 0.8 should cap EXCEPTIONAL to MEDIUM."""
    result = apply_data_quality_gate(
        conviction=CompositeTier.EXCEPTIONAL,
        data_coverage=0.70,
    )
    assert result == CompositeTier.MEDIUM


def test_very_low_coverage_caps_to_none():
    """data_coverage < 0.6 should force NONE."""
    result = apply_data_quality_gate(
        conviction=CompositeTier.HIGH,
        data_coverage=0.50,
    )
    assert result == CompositeTier.NONE


def test_medium_coverage_caps_medium():
    """data_coverage between 0.6 and 0.8 caps at MEDIUM."""
    result = apply_data_quality_gate(
        conviction=CompositeTier.HIGH,
        data_coverage=0.65,
    )
    assert result == CompositeTier.MEDIUM


def test_none_stays_none():
    """NONE conviction is unchanged regardless of coverage."""
    result = apply_data_quality_gate(
        conviction=CompositeTier.NONE,
        data_coverage=1.0,
    )
    assert result == CompositeTier.NONE
