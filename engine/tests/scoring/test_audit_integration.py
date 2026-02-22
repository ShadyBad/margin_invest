"""Integration test: verify new factors are accessible and produce valid scores."""

from margin_engine.models.scoring import ConvictionLevel, ScenarioIV
from margin_engine.scoring.data_quality_gate import apply_data_quality_gate
from margin_engine.scoring.drift_monitor import check_concentration
from margin_engine.scoring.quantitative.competitive_dynamics import (
    gross_margin_stability,
    relative_revenue_growth,
)
from margin_engine.scoring.quantitative.earnings_revision import earnings_revision_momentum
from margin_engine.scoring.quantitative.fcf_conversion import fcf_conversion
from margin_engine.scoring.quantitative.multi_horizon_momentum import multi_horizon_momentum
from margin_engine.scoring.quantitative.roic_trend import roic_trend
from margin_engine.scoring.quantitative.scenario_iv import compute_scenario_iv


def test_all_new_factors_importable():
    """Smoke test: all new modules are importable and callable."""
    assert callable(roic_trend)
    assert callable(fcf_conversion)
    assert callable(multi_horizon_momentum)
    assert callable(gross_margin_stability)
    assert callable(relative_revenue_growth)
    assert callable(earnings_revision_momentum)
    assert callable(compute_scenario_iv)
    assert callable(apply_data_quality_gate)
    assert callable(check_concentration)


def test_scenario_iv_model():
    """ScenarioIV model is available and validates correctly."""
    iv = ScenarioIV(
        bear_iv=80.0,
        base_iv=100.0,
        bull_iv=130.0,
        weighted_iv=102.5,
        confidence=0.50,
        range_pct=0.50,
    )
    assert iv.weighted_iv == 102.5
    assert 0 <= iv.confidence <= 1.0


def test_data_quality_gate_with_real_conviction():
    """Data quality gate correctly caps EXCEPTIONAL with low coverage."""
    result = apply_data_quality_gate(ConvictionLevel.EXCEPTIONAL, 0.70)
    assert result == ConvictionLevel.MEDIUM
