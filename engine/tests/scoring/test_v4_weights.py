"""Tests for v4 style x stage weight matrix."""

import pytest
from margin_engine.models.scoring import GrowthStage, InvestmentStyle


class TestV4Weights:
    def test_growth_high_growth_weights_sum_to_1(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        q, v, m, g = weights_for_style_stage(InvestmentStyle.GROWTH, GrowthStage.HIGH_GROWTH)
        assert q + v + m + g == pytest.approx(1.0)
        assert g == 0.45
        assert v == 0.10

    def test_value_mature_weights_sum_to_1(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        q, v, m, g = weights_for_style_stage(InvestmentStyle.VALUE, GrowthStage.MATURE)
        assert q + v + m + g == pytest.approx(1.0)
        assert v == 0.35
        assert g == 0.15

    def test_blend_steady_growth_weights(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        q, v, m, g = weights_for_style_stage(InvestmentStyle.BLEND, GrowthStage.STEADY_GROWTH)
        assert q + v + m + g == pytest.approx(1.0)
        assert m == 0.25

    def test_all_combinations_sum_to_1(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                q, v, m, g = weights_for_style_stage(style, stage)
                assert q + v + m + g == pytest.approx(1.0), f"{style}/{stage}"

    def test_no_weight_exceeds_045(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                q, v, m, g = weights_for_style_stage(style, stage)
                for w, name in [(q, "quality"), (v, "value"), (m, "momentum"), (g, "growth")]:
                    assert w <= 0.45, f"{name}={w} for {style}/{stage}"

    def test_momentum_always_025(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                _, _, m, _ = weights_for_style_stage(style, stage)
                assert m == 0.25, f"{style}/{stage}"

    def test_quality_always_at_least_020(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                q, _, _, _ = weights_for_style_stage(style, stage)
                assert q >= 0.20, f"{style}/{stage}"
