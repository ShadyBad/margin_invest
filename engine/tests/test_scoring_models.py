"""Tests for scoring result models."""

import pytest
from margin_engine.models.scoring import (
    CompositeScore,
    ConvictionLevel,
    FactorBreakdown,
    FactorScore,
    FilterResult,
    FilterVerdict,
    GrowthStage,
    ScoringConfig,
    Signal,
)


class TestFilterResult:
    def test_pass(self):
        result = FilterResult(
            name="beneish_m_score",
            passed=True,
            value=-2.94,
            threshold=-1.78,
            detail="M-Score well below threshold",
        )
        assert result.passed is True
        assert result.verdict == FilterVerdict.PASS

    def test_fail(self):
        result = FilterResult(
            name="beneish_m_score",
            passed=False,
            value=-1.50,
            threshold=-1.78,
            detail="M-Score above threshold — possible manipulation",
        )
        assert result.passed is False
        assert result.verdict == FilterVerdict.FAIL


class TestFactorScore:
    def test_create_factor_score(self):
        score = FactorScore(
            name="gross_profitability",
            raw_value=0.732,
            percentile_rank=98.0,
            detail="Revenue $394B, COGS $224B, Total Assets $353B",
        )
        assert score.percentile_rank == 98.0

    def test_percentile_bounds(self):
        with pytest.raises(ValueError):
            FactorScore(name="test", raw_value=0.5, percentile_rank=101.0)
        with pytest.raises(ValueError):
            FactorScore(name="test", raw_value=0.5, percentile_rank=-1.0)


class TestFactorBreakdown:
    def test_quality_factor(self):
        breakdown = FactorBreakdown(
            factor_name="quality",
            weight=0.35,
            sub_scores=[
                FactorScore(name="gross_profitability", raw_value=0.73, percentile_rank=98.0),
                FactorScore(name="roic_wacc_spread", raw_value=0.58, percentile_rank=99.0),
                FactorScore(name="accrual_ratio", raw_value=-0.02, percentile_rank=96.0),
                FactorScore(name="f_score", raw_value=8.0, percentile_rank=95.0),
            ],
        )
        assert breakdown.average_percentile == pytest.approx(97.0)


class TestCompositeScore:
    def test_conviction_level_exceptional(self):
        score = CompositeScore(
            ticker="NVDA",
            composite_percentile=99.5,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert score.conviction_level == ConvictionLevel.EXCEPTIONAL
        assert score.signal == Signal.BUY

    def test_conviction_level_high(self):
        score = CompositeScore(
            ticker="NVDA",
            composite_percentile=96.0,
            quality=FactorBreakdown(
                factor_name="quality", weight=0.35, sub_scores=[]
            ),
            value=FactorBreakdown(
                factor_name="value", weight=0.30, sub_scores=[]
            ),
            momentum=FactorBreakdown(
                factor_name="momentum", weight=0.35, sub_scores=[]
            ),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert score.conviction_level == ConvictionLevel.HIGH
        assert score.signal == Signal.BUY

    def test_conviction_level_high_boundary(self):
        score = CompositeScore(
            ticker="COST",
            composite_percentile=95.5,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert score.conviction_level == ConvictionLevel.HIGH
        assert score.signal == Signal.BUY

    def test_conviction_level_watchlist(self):
        score = CompositeScore(
            ticker="XYZ",
            composite_percentile=92.0,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert score.conviction_level == ConvictionLevel.WATCHLIST
        assert score.signal == Signal.WATCH

    def test_not_recommended(self):
        score = CompositeScore(
            ticker="BAD",
            composite_percentile=50.0,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert score.conviction_level == ConvictionLevel.NONE
        assert score.signal == Signal.NO_ACTION

    def test_turnaround_requires_top_3_percent(self):
        """Turnaround stocks need >= 97th percentile for HIGH conviction, not 95th."""
        score = CompositeScore(
            ticker="TURN",
            composite_percentile=96.0,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
            growth_stage=GrowthStage.TURNAROUND,
        )
        # 96th percentile is HIGH for normal stocks, but only WATCHLIST for turnarounds
        assert score.conviction_level == ConvictionLevel.WATCHLIST

    def test_turnaround_at_97_is_high(self):
        """Turnaround stock at 97th percentile qualifies as HIGH."""
        score = CompositeScore(
            ticker="TURN",
            composite_percentile=97.5,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert score.conviction_level == ConvictionLevel.HIGH

    def test_non_turnaround_at_96_is_high(self):
        """Non-turnaround stock at 96th percentile is still HIGH."""
        score = CompositeScore(
            ticker="NORM",
            composite_percentile=96.0,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
            growth_stage=GrowthStage.STEADY_GROWTH,
        )
        assert score.conviction_level == ConvictionLevel.HIGH


class TestGrowthStage:
    def test_all_stages_exist(self):
        stages = [
            GrowthStage.HIGH_GROWTH,
            GrowthStage.STEADY_GROWTH,
            GrowthStage.MATURE,
            GrowthStage.CYCLICAL,
            GrowthStage.TURNAROUND,
        ]
        assert len(stages) == 5


class TestScoringConfig:
    def test_default_weights(self):
        config = ScoringConfig()
        assert config.quality_weight == 0.35
        assert config.value_weight == 0.30
        assert config.momentum_weight == 0.35
        total = config.quality_weight + config.value_weight + config.momentum_weight
        assert total == pytest.approx(1.0)

    def test_growth_stage_weights(self):
        config = ScoringConfig()
        weights = config.weights_for_stage(GrowthStage.HIGH_GROWTH)
        assert weights == (0.40, 0.25, 0.35)

        weights = config.weights_for_stage(GrowthStage.MATURE)
        assert weights == (0.30, 0.40, 0.30)

    def test_all_stage_weights_sum_to_one(self):
        config = ScoringConfig()
        for stage in GrowthStage:
            q, v, m = config.weights_for_stage(stage)
            assert q + v + m == pytest.approx(1.0), f"Weights for {stage} don't sum to 1.0"
