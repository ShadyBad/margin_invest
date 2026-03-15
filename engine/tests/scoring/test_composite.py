"""Tests for composite scorer — combines quality, value, momentum into final score."""

import pytest
from margin_engine.models.scoring import (
    CompositeTier,
    FactorScore,
    FilterResult,
    GrowthStage,
    ScoringConfig,
    Signal,
)
from margin_engine.scoring.composite import compute_composite_score

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_factor_score(
    name: str = "test_factor",
    raw_value: float = 1.0,
    percentile_rank: float = 50.0,
) -> FactorScore:
    return FactorScore(name=name, raw_value=raw_value, percentile_rank=percentile_rank)


def _make_filter(name: str = "altman_z", passed: bool = True) -> FilterResult:
    return FilterResult(name=name, passed=passed, value=3.0, threshold=1.81)


# ---------------------------------------------------------------------------
# Basic composite computation
# ---------------------------------------------------------------------------


class TestBasicComposite:
    """Core weighted-average computation with default weights."""

    def test_known_percentiles_default_weights(self):
        """Quality=75, Value=60, Momentum=80 -> 75*0.35 + 60*0.30 + 80*0.35 = 72.25."""
        quality = [_make_factor_score("gp", percentile_rank=75.0)]
        value = [_make_factor_score("ev_fcf", percentile_rank=60.0)]
        momentum = [_make_factor_score("price_mom", percentile_rank=80.0)]
        filters = [_make_filter()]

        result = compute_composite_score(
            ticker="AAPL",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=filters,
        )

        assert result.composite_percentile == pytest.approx(72.25)
        assert result.ticker == "AAPL"

    def test_composite_raw_score_populated(self):
        """composite_raw_score should equal the weighted average before re-ranking."""
        quality = [_make_factor_score("gp", percentile_rank=75.0)]
        value = [_make_factor_score("ev_fcf", percentile_rank=60.0)]
        momentum = [_make_factor_score("price_mom", percentile_rank=80.0)]

        result = compute_composite_score(
            ticker="AAPL",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        assert result.composite_raw_score == pytest.approx(72.25)
        assert result.composite_percentile == result.composite_raw_score

    def test_multiple_sub_scores_per_factor(self):
        """Multiple sub-scores averaged within each factor before weighting."""
        quality = [
            _make_factor_score("gp", percentile_rank=90.0),
            _make_factor_score("roic", percentile_rank=80.0),
        ]  # avg = 85.0
        value = [
            _make_factor_score("ev_fcf", percentile_rank=70.0),
            _make_factor_score("dcf", percentile_rank=60.0),
        ]  # avg = 65.0
        momentum = [
            _make_factor_score("price_mom", percentile_rank=50.0),
        ]  # avg = 50.0

        result = compute_composite_score(
            ticker="MSFT",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        # 85*0.35 + 65*0.30 + 50*0.35 = 29.75 + 19.5 + 17.5 = 66.75
        assert result.composite_percentile == pytest.approx(66.75)

    def test_all_perfect_scores(self):
        """All 100th percentile -> composite = 100."""
        quality = [_make_factor_score(percentile_rank=100.0)]
        value = [_make_factor_score(percentile_rank=100.0)]
        momentum = [_make_factor_score(percentile_rank=100.0)]

        result = compute_composite_score(
            ticker="PERF",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        assert result.composite_percentile == pytest.approx(100.0)

    def test_all_zero_scores(self):
        """All 0th percentile -> composite = 0."""
        quality = [_make_factor_score(percentile_rank=0.0)]
        value = [_make_factor_score(percentile_rank=0.0)]
        momentum = [_make_factor_score(percentile_rank=0.0)]

        result = compute_composite_score(
            ticker="ZERO",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        assert result.composite_percentile == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Growth-stage-adjusted weights
# ---------------------------------------------------------------------------


class TestGrowthStageWeights:
    """Weights adjusted by growth stage via ScoringConfig.weights_for_stage."""

    def test_high_growth_weights(self):
        """High Growth: quality=0.40, value=0.25, momentum=0.35."""
        quality = [_make_factor_score(percentile_rank=75.0)]
        value = [_make_factor_score(percentile_rank=60.0)]
        momentum = [_make_factor_score(percentile_rank=80.0)]

        result = compute_composite_score(
            ticker="NVDA",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_stage=GrowthStage.HIGH_GROWTH,
        )

        # 75*0.40 + 60*0.25 + 80*0.35 = 30.0 + 15.0 + 28.0 = 73.0
        assert result.composite_percentile == pytest.approx(73.0)
        assert result.growth_stage == GrowthStage.HIGH_GROWTH

    def test_mature_weights(self):
        """Mature: quality=0.30, value=0.40, momentum=0.30."""
        quality = [_make_factor_score(percentile_rank=75.0)]
        value = [_make_factor_score(percentile_rank=60.0)]
        momentum = [_make_factor_score(percentile_rank=80.0)]

        result = compute_composite_score(
            ticker="KO",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_stage=GrowthStage.MATURE,
        )

        # 75*0.30 + 60*0.40 + 80*0.30 = 22.5 + 24.0 + 24.0 = 70.5
        assert result.composite_percentile == pytest.approx(70.5)

    def test_steady_growth_same_as_default(self):
        """Steady Growth: quality=0.35, value=0.30, momentum=0.35 (same as default)."""
        quality = [_make_factor_score(percentile_rank=75.0)]
        value = [_make_factor_score(percentile_rank=60.0)]
        momentum = [_make_factor_score(percentile_rank=80.0)]

        result_with_stage = compute_composite_score(
            ticker="MSFT",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_stage=GrowthStage.STEADY_GROWTH,
        )
        result_no_stage = compute_composite_score(
            ticker="MSFT",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        assert result_with_stage.composite_percentile == pytest.approx(
            result_no_stage.composite_percentile
        )


# ---------------------------------------------------------------------------
# Conviction level property
# ---------------------------------------------------------------------------


class TestCompositeTier:
    """CompositeScore.composite_tier thresholds."""

    def test_exceptional_at_99_95(self):
        """composite >= 99.95 -> exceptional."""
        quality = [_make_factor_score(percentile_rank=99.97)]
        value = [_make_factor_score(percentile_rank=99.97)]
        momentum = [_make_factor_score(percentile_rank=99.97)]

        result = compute_composite_score(
            ticker="TOP",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        assert result.composite_percentile == pytest.approx(99.97)
        assert result.composite_tier == CompositeTier.EXCEPTIONAL

    def test_high_conviction(self):
        """composite_raw_score >= 71 but < 76 -> high."""
        quality = [_make_factor_score(percentile_rank=73.0)]
        value = [_make_factor_score(percentile_rank=73.0)]
        momentum = [_make_factor_score(percentile_rank=73.0)]

        result = compute_composite_score(
            ticker="HI",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        assert result.composite_raw_score == pytest.approx(73.0)
        assert result.composite_tier == CompositeTier.HIGH

    def test_medium_conviction(self):
        """composite_raw_score >= 66 but < 71 -> medium."""
        quality = [_make_factor_score(percentile_rank=68.0)]
        value = [_make_factor_score(percentile_rank=68.0)]
        momentum = [_make_factor_score(percentile_rank=68.0)]

        result = compute_composite_score(
            ticker="MED",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        assert result.composite_raw_score == pytest.approx(68.0)
        assert result.composite_tier == CompositeTier.MEDIUM

    def test_none_below_66(self):
        """composite_raw_score < 66 -> none."""
        quality = [_make_factor_score(percentile_rank=50.0)]
        value = [_make_factor_score(percentile_rank=50.0)]
        momentum = [_make_factor_score(percentile_rank=50.0)]

        result = compute_composite_score(
            ticker="LOW",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        assert result.composite_percentile == pytest.approx(50.0)
        assert result.composite_tier == CompositeTier.NONE


# ---------------------------------------------------------------------------
# Signal property
# ---------------------------------------------------------------------------


class TestSignal:
    """CompositeScore.signal derived from composite_tier."""

    def test_buy_for_exceptional(self):
        quality = [_make_factor_score(percentile_rank=100.0)]
        value = [_make_factor_score(percentile_rank=100.0)]
        momentum = [_make_factor_score(percentile_rank=100.0)]

        result = compute_composite_score(
            ticker="BUY1",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )
        assert result.signal == Signal.BUY

    def test_buy_for_high(self):
        quality = [_make_factor_score(percentile_rank=99.4)]
        value = [_make_factor_score(percentile_rank=99.4)]
        momentum = [_make_factor_score(percentile_rank=99.4)]

        result = compute_composite_score(
            ticker="BUY2",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )
        assert result.signal == Signal.BUY

    def test_watch_for_medium(self):
        quality = [_make_factor_score(percentile_rank=68.0)]
        value = [_make_factor_score(percentile_rank=68.0)]
        momentum = [_make_factor_score(percentile_rank=68.0)]

        result = compute_composite_score(
            ticker="MED",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )
        assert result.signal == Signal.WATCH

    def test_no_action_below_medium(self):
        quality = [_make_factor_score(percentile_rank=40.0)]
        value = [_make_factor_score(percentile_rank=40.0)]
        momentum = [_make_factor_score(percentile_rank=40.0)]

        result = compute_composite_score(
            ticker="NOPE",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )
        assert result.signal == Signal.NO_ACTION


# ---------------------------------------------------------------------------
# Data coverage computation
# ---------------------------------------------------------------------------


class TestDataCoverage:
    """data_coverage = fraction of sub-scores with non-zero percentile_rank."""

    def test_full_coverage(self):
        """All sub-scores have percentile_rank > 0 -> coverage = 1.0."""
        quality = [_make_factor_score(percentile_rank=80.0)]
        value = [_make_factor_score(percentile_rank=60.0)]
        momentum = [_make_factor_score(percentile_rank=70.0)]

        result = compute_composite_score(
            ticker="FULL",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )
        assert result.data_coverage == pytest.approx(1.0)

    def test_partial_coverage(self):
        """Some sub-scores have percentile_rank == 0.0 -> partial coverage."""
        quality = [
            _make_factor_score("gp", percentile_rank=80.0),
            _make_factor_score("roic", percentile_rank=0.0),
        ]
        value = [_make_factor_score("ev_fcf", percentile_rank=60.0)]
        momentum = [_make_factor_score("price_mom", percentile_rank=0.0)]

        result = compute_composite_score(
            ticker="PART",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )
        # 2 with data out of 4 total
        assert result.data_coverage == pytest.approx(0.5)

    def test_zero_coverage(self):
        """All sub-scores have percentile_rank == 0.0 -> coverage = 0.0."""
        quality = [_make_factor_score(percentile_rank=0.0)]
        value = [_make_factor_score(percentile_rank=0.0)]
        momentum = [_make_factor_score(percentile_rank=0.0)]

        result = compute_composite_score(
            ticker="NONE",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )
        assert result.data_coverage == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Default config
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    """ScoringConfig defaults are used when config=None."""

    def test_none_config_uses_defaults(self):
        quality = [_make_factor_score(percentile_rank=75.0)]
        value = [_make_factor_score(percentile_rank=60.0)]
        momentum = [_make_factor_score(percentile_rank=80.0)]

        result = compute_composite_score(
            ticker="DEF",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            config=None,
        )

        # Default weights: 0.35 / 0.30 / 0.35
        assert result.composite_percentile == pytest.approx(72.25)

    def test_custom_config_overrides_defaults(self):
        """Custom config with different weights."""
        quality = [_make_factor_score(percentile_rank=75.0)]
        value = [_make_factor_score(percentile_rank=60.0)]
        momentum = [_make_factor_score(percentile_rank=80.0)]

        custom = ScoringConfig(
            quality_weight=0.50,
            value_weight=0.25,
            momentum_weight=0.25,
        )
        result = compute_composite_score(
            ticker="CUST",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            config=custom,
        )

        # 75*0.50 + 60*0.25 + 80*0.25 = 37.5 + 15.0 + 20.0 = 72.5
        assert result.composite_percentile == pytest.approx(72.5)


# ---------------------------------------------------------------------------
# Empty sub-score lists (edge case)
# ---------------------------------------------------------------------------


class TestEmptySubScores:
    """Empty sub-score lists should still produce valid CompositeScore."""

    def test_all_empty_lists(self):
        """All empty sub-score lists -> composite = 0, coverage = 1.0."""
        result = compute_composite_score(
            ticker="EMPTY",
            quality_scores=[],
            value_scores=[],
            momentum_scores=[],
            filters_passed=[],
        )

        assert result.composite_percentile == pytest.approx(0.0)
        # no scores -> data_coverage = 1.0 (vacuously true)
        assert result.data_coverage == pytest.approx(1.0)

    def test_one_factor_empty(self):
        """One empty factor still computes correctly for the others."""
        quality = [_make_factor_score(percentile_rank=80.0)]
        value = []  # empty
        momentum = [_make_factor_score(percentile_rank=60.0)]

        result = compute_composite_score(
            ticker="PARTIAL",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
        )

        # quality avg = 80, value avg = 0 (empty), momentum avg = 60
        # 80*0.35 + 0*0.30 + 60*0.35 = 28.0 + 0.0 + 21.0 = 49.0
        assert result.composite_percentile == pytest.approx(49.0)


# ---------------------------------------------------------------------------
# FactorBreakdown fields
# ---------------------------------------------------------------------------


class TestFactorBreakdownFields:
    """All FactorBreakdown fields populated correctly."""

    def test_breakdown_names_and_weights(self):
        quality = [
            _make_factor_score("gp", raw_value=0.73, percentile_rank=98.0),
            _make_factor_score("roic", raw_value=0.58, percentile_rank=99.0),
        ]
        value = [
            _make_factor_score("ev_fcf", raw_value=12.0, percentile_rank=70.0),
        ]
        momentum = [
            _make_factor_score("price_mom", raw_value=0.15, percentile_rank=85.0),
            _make_factor_score("sue", raw_value=2.1, percentile_rank=75.0),
        ]

        result = compute_composite_score(
            ticker="AAPL",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[_make_filter()],
        )

        # Quality breakdown
        assert result.quality.factor_name == "quality"
        assert result.quality.weight == pytest.approx(0.35)
        assert len(result.quality.sub_scores) == 2
        assert result.quality.average_percentile == pytest.approx(98.5)

        # Value breakdown
        assert result.value.factor_name == "value"
        assert result.value.weight == pytest.approx(0.30)
        assert len(result.value.sub_scores) == 1
        assert result.value.average_percentile == pytest.approx(70.0)

        # Momentum breakdown
        assert result.momentum.factor_name == "momentum"
        assert result.momentum.weight == pytest.approx(0.35)
        assert len(result.momentum.sub_scores) == 2
        assert result.momentum.average_percentile == pytest.approx(80.0)

    def test_breakdown_weights_adjusted_by_growth_stage(self):
        """FactorBreakdown.weight reflects growth-stage-adjusted weights."""
        quality = [_make_factor_score(percentile_rank=80.0)]
        value = [_make_factor_score(percentile_rank=70.0)]
        momentum = [_make_factor_score(percentile_rank=60.0)]

        result = compute_composite_score(
            ticker="GOOG",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_stage=GrowthStage.HIGH_GROWTH,
        )

        assert result.quality.weight == pytest.approx(0.40)
        assert result.value.weight == pytest.approx(0.25)
        assert result.momentum.weight == pytest.approx(0.35)

    def test_filters_passed_through(self):
        """filters_passed list is forwarded to CompositeScore."""
        filters = [
            _make_filter("altman_z", passed=True),
            _make_filter("beneish", passed=True),
        ]

        result = compute_composite_score(
            ticker="TST",
            quality_scores=[_make_factor_score(percentile_rank=50.0)],
            value_scores=[_make_factor_score(percentile_rank=50.0)],
            momentum_scores=[_make_factor_score(percentile_rank=50.0)],
            filters_passed=filters,
        )

        assert len(result.filters_passed) == 2
        assert result.filters_passed[0].name == "altman_z"
        assert result.filters_passed[1].name == "beneish"

    def test_sub_scores_preserve_details(self):
        """Sub-score name, raw_value, percentile_rank, detail preserved."""
        quality = [
            FactorScore(
                name="gross_profitability",
                raw_value=0.732,
                percentile_rank=98.0,
                detail="GP/TA = 0.732",
            ),
        ]

        result = compute_composite_score(
            ticker="DET",
            quality_scores=quality,
            value_scores=[_make_factor_score(percentile_rank=50.0)],
            momentum_scores=[_make_factor_score(percentile_rank=50.0)],
            filters_passed=[],
        )

        sub = result.quality.sub_scores[0]
        assert sub.name == "gross_profitability"
        assert sub.raw_value == pytest.approx(0.732)
        assert sub.percentile_rank == pytest.approx(98.0)
        assert sub.detail == "GP/TA = 0.732"


# ---------------------------------------------------------------------------
# Price targets integration
# ---------------------------------------------------------------------------


class TestPriceTargetsIntegration:
    """Price targets can be optionally passed into composite scorer."""

    def test_composite_score_with_price_targets(self):
        from margin_engine.scoring.quantitative.price_targets import PriceTargets

        targets = PriceTargets(
            margin_invest_value=195.20,
            buy_price=195.20,
            sell_price=234.24,
            actual_price=167.42,
            price_upside=0.166,
            valuation_methods={"dcf": 210.0, "ev_fcf": 185.0},
        )
        score = compute_composite_score(
            ticker="AAPL",
            quality_scores=[FactorScore(name="gp", raw_value=0.5, percentile_rank=80.0)],
            value_scores=[FactorScore(name="ev", raw_value=12.0, percentile_rank=75.0)],
            momentum_scores=[FactorScore(name="pm", raw_value=0.1, percentile_rank=60.0)],
            filters_passed=[],
            price_targets=targets,
        )
        assert score.margin_invest_value == 195.20
        assert score.buy_price == 195.20
        assert score.sell_price == 234.24
        assert score.actual_price == 167.42
        assert score.price_upside == 0.166
        assert score.valuation_methods == {"dcf": 210.0, "ev_fcf": 185.0}

    def test_composite_score_without_price_targets(self):
        """Existing behavior unchanged when no price_targets provided."""
        score = compute_composite_score(
            ticker="AAPL",
            quality_scores=[FactorScore(name="gp", raw_value=0.5, percentile_rank=80.0)],
            value_scores=[FactorScore(name="ev", raw_value=12.0, percentile_rank=75.0)],
            momentum_scores=[FactorScore(name="pm", raw_value=0.1, percentile_rank=60.0)],
            filters_passed=[],
        )
        assert score.margin_invest_value is None
        assert score.buy_price is None


# ---------------------------------------------------------------------------
# Task 1: ScoringConfig growth_weight field
# ---------------------------------------------------------------------------


class TestGrowthWeight:
    """ScoringConfig growth_weight field and 4-tuple weights_for_stage."""

    def test_default_growth_weight(self):
        config = ScoringConfig()
        assert config.growth_weight == 0.15

    def test_default_weights_changed(self):
        config = ScoringConfig()
        assert config.quality_weight == 0.25
        assert config.value_weight == 0.20
        assert config.momentum_weight == 0.25
        assert config.growth_weight == 0.15

    def test_weights_for_stage_returns_4_tuple(self):
        config = ScoringConfig()
        result = config.weights_for_stage(GrowthStage.HIGH_GROWTH)
        assert len(result) == 4

    def test_high_growth_stage_weights(self):
        config = ScoringConfig()
        q, v, m, g = config.weights_for_stage(GrowthStage.HIGH_GROWTH)
        assert q == pytest.approx(0.20)
        assert v == pytest.approx(0.10)
        assert m == pytest.approx(0.25)
        assert g == pytest.approx(0.30)
        assert q + v + m + g == pytest.approx(0.85)

    def test_mature_stage_weights(self):
        config = ScoringConfig()
        q, v, m, g = config.weights_for_stage(GrowthStage.MATURE)
        assert q == pytest.approx(0.25)
        assert v == pytest.approx(0.30)
        assert m == pytest.approx(0.15)
        assert g == pytest.approx(0.15)
        assert q + v + m + g == pytest.approx(0.85)

    def test_steady_growth_stage_weights(self):
        config = ScoringConfig()
        q, v, m, g = config.weights_for_stage(GrowthStage.STEADY_GROWTH)
        assert q == pytest.approx(0.25)
        assert v == pytest.approx(0.20)
        assert m == pytest.approx(0.25)
        assert g == pytest.approx(0.15)
