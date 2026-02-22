"""Tests for scenario-weighted intrinsic value."""

import pytest
from margin_engine.scoring.quantitative.scenario_iv import compute_scenario_iv


def test_basic_scenario_iv():
    """Bear/base/bull with known inputs produces expected weighted IV."""
    result = compute_scenario_iv(
        base_fcf=100.0,
        base_growth=0.08,
        wacc=0.10,
        terminal_growth=0.03,
        shares_outstanding=100,
        growth_spread=0.02,  # bear=0.06, bull=0.10
        wacc_spread=0.01,  # bear=0.11, bull=0.09
    )
    assert result.base_iv > 0
    assert result.bear_iv < result.base_iv < result.bull_iv
    assert result.weighted_iv == pytest.approx(
        0.25 * result.bear_iv + 0.50 * result.base_iv + 0.25 * result.bull_iv,
        rel=1e-6,
    )
    assert 0.0 <= result.confidence <= 1.0


def test_zero_fcf_returns_zero():
    result = compute_scenario_iv(
        base_fcf=0.0,
        base_growth=0.08,
        wacc=0.10,
        terminal_growth=0.03,
        shares_outstanding=100,
    )
    assert result.weighted_iv == 0.0
    assert result.confidence == 0.0


def test_negative_fcf_returns_zero():
    result = compute_scenario_iv(
        base_fcf=-50.0,
        base_growth=0.08,
        wacc=0.10,
        terminal_growth=0.03,
        shares_outstanding=100,
    )
    assert result.weighted_iv == 0.0


def test_confidence_decreases_with_wider_spread():
    """Wider growth/WACC spread should produce lower confidence."""
    narrow = compute_scenario_iv(
        base_fcf=100.0,
        base_growth=0.08,
        wacc=0.10,
        terminal_growth=0.03,
        shares_outstanding=100,
        growth_spread=0.01,
        wacc_spread=0.005,
    )
    wide = compute_scenario_iv(
        base_fcf=100.0,
        base_growth=0.08,
        wacc=0.10,
        terminal_growth=0.03,
        shares_outstanding=100,
        growth_spread=0.04,
        wacc_spread=0.02,
    )
    assert narrow.confidence > wide.confidence


def test_range_pct_calculation():
    result = compute_scenario_iv(
        base_fcf=100.0,
        base_growth=0.08,
        wacc=0.10,
        terminal_growth=0.03,
        shares_outstanding=100,
    )
    if result.base_iv > 0:
        expected_range = (result.bull_iv - result.bear_iv) / result.base_iv
        assert result.range_pct == pytest.approx(expected_range, rel=1e-6)
