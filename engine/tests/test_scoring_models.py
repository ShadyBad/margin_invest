"""Tests for scoring result models."""

import pytest
from margin_engine.models.scoring import (
    CompositeScore,
    CompositeTier,
    ConsistencyFlag,
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


class TestFactorScoreStub:
    def test_stub_default_false(self):
        """FactorScore.stub defaults to False."""
        score = FactorScore(name="test", raw_value=1.0, percentile_rank=50.0)
        assert score.stub is False

    def test_stub_excluded_from_average(self):
        """Stub sub-scores are excluded from average_percentile."""
        breakdown = FactorBreakdown(
            factor_name="momentum",
            weight=0.35,
            sub_scores=[
                FactorScore(name="real_a", raw_value=1.0, percentile_rank=80.0),
                FactorScore(name="real_b", raw_value=1.0, percentile_rank=60.0),
                FactorScore(name="stub_a", raw_value=0.0, percentile_rank=0.0, stub=True),
                FactorScore(name="stub_b", raw_value=0.0, percentile_rank=0.0, stub=True),
            ],
        )
        # Average of real only: (80 + 60) / 2 = 70
        assert breakdown.average_percentile == pytest.approx(70.0)

    def test_all_stubs_returns_zero(self):
        """If all sub-scores are stubs, average_percentile is 0.0."""
        breakdown = FactorBreakdown(
            factor_name="momentum",
            weight=0.35,
            sub_scores=[
                FactorScore(name="stub_a", raw_value=0.0, percentile_rank=0.0, stub=True),
                FactorScore(name="stub_b", raw_value=0.0, percentile_rank=0.0, stub=True),
            ],
        )
        assert breakdown.average_percentile == 0.0

    def test_no_stubs_unchanged(self):
        """Without stubs, average_percentile works as before."""
        breakdown = FactorBreakdown(
            factor_name="quality",
            weight=0.35,
            sub_scores=[
                FactorScore(name="a", raw_value=1.0, percentile_rank=90.0),
                FactorScore(name="b", raw_value=1.0, percentile_rank=70.0),
                FactorScore(name="c", raw_value=1.0, percentile_rank=80.0),
            ],
        )
        assert breakdown.average_percentile == pytest.approx(80.0)


class TestCompositeScore:
    def _make_score(self, **kwargs):
        defaults = dict(
            ticker="TEST",
            composite_percentile=50.0,
            composite_raw_score=50.0,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
        )
        defaults.update(kwargs)
        return CompositeScore(**defaults)

    def test_composite_tier_exceptional(self):
        score = self._make_score(composite_raw_score=80.0)
        assert score.composite_tier == CompositeTier.EXCEPTIONAL
        assert score.signal == Signal.BUY

    def test_composite_tier_exceptional_boundary(self):
        score = self._make_score(composite_raw_score=76.0)
        assert score.composite_tier == CompositeTier.EXCEPTIONAL

    def test_composite_tier_high(self):
        score = self._make_score(composite_raw_score=73.0)
        assert score.composite_tier == CompositeTier.HIGH
        assert score.signal == Signal.BUY

    def test_composite_tier_high_boundary(self):
        score = self._make_score(composite_raw_score=71.0)
        assert score.composite_tier == CompositeTier.HIGH

    def test_composite_tier_medium(self):
        score = self._make_score(composite_raw_score=68.0)
        assert score.composite_tier == CompositeTier.MEDIUM
        assert score.signal == Signal.WATCH

    def test_composite_tier_medium_boundary(self):
        score = self._make_score(composite_raw_score=66.0)
        assert score.composite_tier == CompositeTier.MEDIUM

    def test_composite_tier_none(self):
        score = self._make_score(composite_raw_score=65.9)
        assert score.composite_tier == CompositeTier.NONE
        assert score.signal == Signal.NO_ACTION

    def test_composite_tier_none_low(self):
        score = self._make_score(composite_raw_score=30.0)
        assert score.composite_tier == CompositeTier.NONE

    def test_turnaround_uses_same_thresholds(self):
        """No turnaround exception — same thresholds for all growth stages."""
        score = self._make_score(
            composite_raw_score=71.0,
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert score.composite_tier == CompositeTier.HIGH

    def test_below_high_turnaround_is_medium(self):
        score = self._make_score(
            composite_raw_score=70.9,
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert score.composite_tier == CompositeTier.MEDIUM

    def test_override_none_uses_threshold(self):
        """conviction_override=None falls through to threshold logic."""
        score = self._make_score(composite_raw_score=76.0, conviction_override=None)
        assert score.composite_tier == CompositeTier.EXCEPTIONAL

    def test_override_set_takes_precedence(self):
        """Override overrides threshold: raw_score=50 would be NONE, but override=EXCEPTIONAL."""
        score = self._make_score(
            composite_raw_score=50.0, conviction_override=CompositeTier.EXCEPTIONAL
        )
        assert score.composite_tier == CompositeTier.EXCEPTIONAL

    def test_override_can_downgrade(self):
        """Override can downgrade: raw_score=80 would be EXCEPTIONAL, but override=MEDIUM."""
        score = self._make_score(
            composite_raw_score=80.0, conviction_override=CompositeTier.MEDIUM
        )
        assert score.composite_tier == CompositeTier.MEDIUM

    def test_signal_uses_overridden_tier(self):
        """Signal should use the overridden tier for price-aware logic."""
        score = self._make_score(
            composite_raw_score=50.0,
            conviction_override=CompositeTier.HIGH,
            actual_price=100.0,
            buy_price=110.0,
            sell_price=130.0,
        )
        # HIGH tier + actual_price <= buy_price → BUY
        assert score.composite_tier == CompositeTier.HIGH
        assert score.signal == Signal.BUY


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

    def test_default_thresholds(self):
        config = ScoringConfig()
        assert config.exceptional_threshold == 76.0
        assert config.high_threshold == 71.0
        assert config.medium_threshold == 66.0

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


class TestConsistencyFlag:
    def test_consistency_flag_creation(self):
        flag = ConsistencyFlag(
            field_name="revenue",
            current_value=1_000_000.0,
            historical_mean=500_000.0,
            historical_std=50_000.0,
            z_score=10.0,
            periods_used=5,
        )
        assert flag.field_name == "revenue"
        assert flag.z_score == 10.0
        assert flag.is_anomaly is True

    def test_consistency_flag_normal_value(self):
        flag = ConsistencyFlag(
            field_name="revenue",
            current_value=510_000.0,
            historical_mean=500_000.0,
            historical_std=50_000.0,
            z_score=0.2,
            periods_used=5,
        )
        assert flag.is_anomaly is False
