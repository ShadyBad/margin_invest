"""Tests for v4 style x stage weight matrix."""

import pytest
from margin_engine.models.scoring import GrowthStage, InvestmentStyle


class TestV4Weights:
    def test_growth_high_growth_weights_sum_to_1(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        q, v, m, g = weights_for_style_stage(InvestmentStyle.GROWTH, GrowthStage.HIGH_GROWTH)
        assert q + v + m + g == pytest.approx(1.0)
        assert g == 0.45
        assert v == 0.05

    def test_value_mature_weights_sum_to_1(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        q, v, m, g = weights_for_style_stage(InvestmentStyle.VALUE, GrowthStage.MATURE)
        assert q + v + m + g == pytest.approx(1.0)
        assert v == 0.40
        assert g == 0.15

    def test_blend_steady_growth_weights(self):
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        q, v, m, g = weights_for_style_stage(InvestmentStyle.BLEND, GrowthStage.STEADY_GROWTH)
        assert q + v + m + g == pytest.approx(1.0)
        assert m == 0.25

    def test_value_rows_momentum_020(self):
        """All VALUE rows should have momentum=0.20."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for stage in GrowthStage:
            q, v, m, g = weights_for_style_stage(InvestmentStyle.VALUE, stage)
            assert m == pytest.approx(0.20), f"VALUE/{stage} momentum should be 0.20, got {m}"

    def test_blend_rows_momentum_025(self):
        """All BLEND rows should have momentum=0.25."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for stage in GrowthStage:
            q, v, m, g = weights_for_style_stage(InvestmentStyle.BLEND, stage)
            assert m == pytest.approx(0.25), f"BLEND/{stage} momentum should be 0.25, got {m}"

    def test_growth_rows_momentum_030(self):
        """All GROWTH rows should have momentum=0.30."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for stage in GrowthStage:
            q, v, m, g = weights_for_style_stage(InvestmentStyle.GROWTH, stage)
            assert m == pytest.approx(0.30), f"GROWTH/{stage} momentum should be 0.30, got {m}"

    def test_all_rows_sum_to_one(self):
        """Every style/stage combination sums to 1.0."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                q, v, m, g = weights_for_style_stage(style, stage)
                assert q + v + m + g == pytest.approx(1.0), f"{style}/{stage} sums to {q+v+m+g}"

    def test_no_cell_exceeds_045(self):
        """No single weight exceeds 0.45."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                q, v, m, g = weights_for_style_stage(style, stage)
                for w, name in [(q, "quality"), (v, "value"), (m, "momentum"), (g, "growth")]:
                    assert w <= 0.45, f"{style}/{stage} {name}={w} exceeds 0.45"

    def test_quality_at_least_020(self):
        """Quality weight >= 0.20 for all rows."""
        from margin_engine.scoring.v4_weights import weights_for_style_stage

        for style in InvestmentStyle:
            for stage in GrowthStage:
                q, _, _, _ = weights_for_style_stage(style, stage)
                assert q >= 0.20, f"{style}/{stage} quality={q} below 0.20"
