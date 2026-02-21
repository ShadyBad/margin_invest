"""Tests for V3 Track C (Efficient Growth) gate cascade."""

import pytest
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_track_c_cascade import TrackCInputs, run_track_c_cascade


class TestTrackCGates:
    def test_all_gates_pass_high_conviction(self):
        """Strong growth company passes all 4 gates."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=-0.02,
            tam_headroom=5.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.track == "efficient_growth"
        assert result.gates_passed == 4
        assert result.qualifies is True
        assert result.conviction in {ConvictionLevel.HIGH, ConvictionLevel.EXCEPTIONAL}

    def test_exceptional_conviction(self):
        """Exceptional: rule_of_40>=50, inc_ROIC>2*WACC, TAM>5x."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.35,
            fcf_margin=0.20,
            gross_margin_current=0.70,
            gross_margin_3yr_ago=0.65,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.35,
            incremental_roic=0.25,
            wacc=0.10,
            revenue_deceleration=-0.01,
            tam_headroom=8.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.conviction == ConvictionLevel.EXCEPTIONAL

    def test_fails_growth_efficiency_gate(self):
        """Low Rule of 40 and no alt rescue."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.05,
            fcf_margin=-0.10,
            gross_margin_current=0.40,
            gross_margin_3yr_ago=0.42,
            opex_growth_rate=0.10,
            revenue_growth_rate_for_leverage=0.05,
            incremental_roic=0.12,
            wacc=0.10,
            revenue_deceleration=-0.03,
            tam_headroom=4.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.gates_passed < 4

    def test_fails_unit_economics_declining_margin(self):
        """Gross margin declining > 2pp."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.55,
            gross_margin_3yr_ago=0.65,
            opex_growth_rate=0.35,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=-0.02,
            tam_headroom=5.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.gates_passed < 4

    def test_fails_capital_efficiency(self):
        """Inc ROIC below WACC."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.05,
            wacc=0.10,
            revenue_deceleration=-0.02,
            tam_headroom=5.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.gates_passed < 4

    def test_fails_growth_durability_decelerating(self):
        """Severe deceleration + low TAM."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=-0.10,
            tam_headroom=2.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.gates_passed < 4

    def test_none_conviction_when_few_gates(self):
        """< 3 gates -> NONE."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.05,
            fcf_margin=-0.10,
            gross_margin_current=0.40,
            gross_margin_3yr_ago=0.50,
            opex_growth_rate=0.20,
            revenue_growth_rate_for_leverage=0.05,
            incremental_roic=0.03,
            wacc=0.10,
            revenue_deceleration=-0.08,
            tam_headroom=1.5,
        )
        result = run_track_c_cascade(inputs)
        assert result.conviction == ConvictionLevel.NONE
        assert result.qualifies is False

    def test_score_is_positive_when_gates_pass(self):
        """Track C score is positive multiplicative product."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=-0.02,
            tam_headroom=5.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.score > 0

    def test_implausible_tam_not_exceptional(self):
        """TAM=100 is implausible (>50), should NOT be exceptional."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.35,
            fcf_margin=0.20,
            gross_margin_current=0.70,
            gross_margin_3yr_ago=0.65,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.35,
            incremental_roic=0.25,
            wacc=0.10,
            revenue_deceleration=-0.01,
            tam_headroom=100.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.conviction != ConvictionLevel.EXCEPTIONAL

    def test_reasonable_tam_exceptional_eligible(self):
        """TAM=8 is reasonable (<50), should be exceptional eligible."""
        inputs = TrackCInputs(
            revenue_growth_rate=0.35,
            fcf_margin=0.20,
            gross_margin_current=0.70,
            gross_margin_3yr_ago=0.65,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.35,
            incremental_roic=0.25,
            wacc=0.10,
            revenue_deceleration=-0.01,
            tam_headroom=8.0,
        )
        result = run_track_c_cascade(inputs)
        assert result.conviction == ConvictionLevel.EXCEPTIONAL

    def test_growth_durability_cap_at_1_5(self):
        """Growth durability TAM factor is capped at 1.5, not 2.0.

        With tam=5.0, deceleration=0: tam/3 = 1.667
        Old cap=2.0: gd = 1.667 (no cap hit)
        New cap=1.5: gd = 1.5 (capped)

        tam=4.5 gives tam/3=1.5 -> same result under new cap.
        So scores should be equal if cap=1.5 is enforced.
        """
        inputs_at_cap = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=0.0,
            tam_headroom=4.5,
        )
        inputs_above_cap = TrackCInputs(
            revenue_growth_rate=0.30,
            fcf_margin=0.15,
            gross_margin_current=0.65,
            gross_margin_3yr_ago=0.62,
            opex_growth_rate=0.15,
            revenue_growth_rate_for_leverage=0.30,
            incremental_roic=0.15,
            wacc=0.10,
            revenue_deceleration=0.0,
            tam_headroom=5.0,
        )
        result_at_cap = run_track_c_cascade(inputs_at_cap)
        result_above_cap = run_track_c_cascade(inputs_above_cap)
        # Both should produce the same score because GD is capped at 1.5
        assert result_at_cap.score == pytest.approx(result_above_cap.score)
