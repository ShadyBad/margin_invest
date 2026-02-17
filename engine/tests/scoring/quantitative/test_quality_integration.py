"""Integration tests for quality factor scoring."""

import pytest
from margin_engine.scoring.quantitative import (
    gross_profitability,
    piotroski_f_score,
    roic_wacc_spread,
    sloan_accrual_ratio,
)

from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024


class TestQualityFactorIntegration:
    def test_all_quality_factors_compute(self):
        """All 4 quality sub-factors compute without error for Apple."""
        gp = gross_profitability(APPLE_PERIOD_2024)
        roic = roic_wacc_spread(APPLE_PERIOD_2024)
        accrual = sloan_accrual_ratio(APPLE_PERIOD_2024)
        fscore = piotroski_f_score(APPLE_PERIOD_2024)

        assert gp.name == "gross_profitability"
        assert roic.name == "roic_wacc_spread"
        assert accrual.name == "accrual_ratio"
        assert fscore.name == "piotroski_f_score"

    def test_apple_golden_values(self):
        """Verify all Apple golden values."""
        gp = gross_profitability(APPLE_PERIOD_2024)
        roic = roic_wacc_spread(APPLE_PERIOD_2024)
        accrual = sloan_accrual_ratio(APPLE_PERIOD_2024)
        fscore = piotroski_f_score(APPLE_PERIOD_2024)

        assert gp.raw_value == pytest.approx(0.4951, abs=0.001)
        assert roic.raw_value == pytest.approx(0.6353, abs=0.01)
        assert accrual.raw_value == pytest.approx(-0.0672, abs=0.001)
        assert fscore.raw_value == 6.0

    def test_all_percentiles_are_placeholders(self):
        """All percentile_ranks should be 0.0 (filled in Phase 6)."""
        gp = gross_profitability(APPLE_PERIOD_2024)
        roic = roic_wacc_spread(APPLE_PERIOD_2024)
        accrual = sloan_accrual_ratio(APPLE_PERIOD_2024)
        fscore = piotroski_f_score(APPLE_PERIOD_2024)

        for score in [gp, roic, accrual, fscore]:
            assert score.percentile_rank == 0.0, f"{score.name} percentile should be 0.0"

    def test_all_have_detail(self):
        """All quality factors should include detail strings."""
        gp = gross_profitability(APPLE_PERIOD_2024)
        roic = roic_wacc_spread(APPLE_PERIOD_2024)
        accrual = sloan_accrual_ratio(APPLE_PERIOD_2024)
        fscore = piotroski_f_score(APPLE_PERIOD_2024)

        for score in [gp, roic, accrual, fscore]:
            assert len(score.detail) > 0, f"{score.name} should have detail"

    def test_roic_with_wacc(self):
        """ROIC-WACC spread with a WACC value for Apple."""
        result = roic_wacc_spread(APPLE_PERIOD_2024, wacc=0.11)
        # ROIC ~63.53%, WACC 11% => spread ~52.53%
        assert result.raw_value == pytest.approx(0.5253, abs=0.01)
        assert "WACC" in result.detail
        assert "Spread" in result.detail

    def test_imports_from_package(self):
        """Verify all functions can be imported from the package."""
        from margin_engine.scoring.quantitative import (
            compute_f_score_signals,
            compute_roic,
        )
        from margin_engine.scoring.quantitative import (
            gross_profitability as gp,
        )
        from margin_engine.scoring.quantitative import (
            piotroski_f_score as fs,
        )
        from margin_engine.scoring.quantitative import (
            roic_wacc_spread as rws,
        )
        from margin_engine.scoring.quantitative import (
            sloan_accrual_ratio as sar,
        )
        # Just verify they're callable
        assert callable(gp)
        assert callable(rws)
        assert callable(compute_roic)
        assert callable(sar)
        assert callable(fs)
        assert callable(compute_f_score_signals)
