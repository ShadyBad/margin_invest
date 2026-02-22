"""Tests for Track A (compounder) composite scorer."""

import pytest
from margin_engine.models.scoring import (
    FactorScore,
    FilterResult,
    GrowthStage,
)
from margin_engine.scoring.composite_compounder import compute_compounder_score

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fs(name: str, percentile: float, weight: float | None = None) -> FactorScore:
    return FactorScore(name=name, raw_value=1.0, percentile_rank=percentile, weight=weight)


def _filter(name: str = "altman_z", passed: bool = True) -> FilterResult:
    return FilterResult(name=name, passed=passed, value=3.0, threshold=1.81)


def _quality_scores() -> list[FactorScore]:
    """Track A quality sub-factors with spec weights."""
    return [
        _fs("roic_stability", 90.0, weight=0.30),
        _fs("incremental_roic", 80.0, weight=0.20),
        _fs("reinvestment_engine", 85.0, weight=0.20),
        _fs("gross_profitability", 75.0, weight=0.15),
        _fs("earnings_quality", 70.0, weight=0.15),
    ]


def _value_scores() -> list[FactorScore]:
    """Track A value sub-factors with spec weights."""
    return [
        _fs("dcf_mos", 80.0, weight=0.30),
        _fs("owner_earnings_yield", 75.0, weight=0.25),
        _fs("acquirers_multiple", 70.0, weight=0.20),
        _fs("runway_score", 65.0, weight=0.25),
    ]


def _cap_alloc_scores() -> list[FactorScore]:
    """Track A capital allocation sub-factors with spec weights."""
    return [
        _fs("organic_reinvestment", 85.0, weight=0.30),
        _fs("buyback_effectiveness", 70.0, weight=0.25),
        _fs("insider_ownership", 80.0, weight=0.25),
        _fs("debt_discipline", 75.0, weight=0.20),
    ]


# ---------------------------------------------------------------------------
# Basic composite computation
# ---------------------------------------------------------------------------


class TestBasicCompounder:
    """Core Track A composite calculation with default Steady Growth weights."""

    def test_weighted_composite_steady_growth(self):
        """Steady Growth: Quality(50%) + Value(30%) + CapAlloc(20%)."""
        quality = _quality_scores()
        value = _value_scores()
        cap_alloc = _cap_alloc_scores()

        result = compute_compounder_score(
            ticker="COST",
            quality_scores=quality,
            value_scores=value,
            capital_allocation_scores=cap_alloc,
            filters_passed=[_filter()],
            growth_stage=GrowthStage.STEADY_GROWTH,
        )

        # Quality weighted avg: 90*0.30 + 80*0.20 + 85*0.20 + 75*0.15 + 70*0.15
        # = 27.0 + 16.0 + 17.0 + 11.25 + 10.5 = 81.75
        # Value weighted avg: 80*0.30 + 75*0.25 + 70*0.20 + 65*0.25
        # = 24.0 + 18.75 + 14.0 + 16.25 = 73.0
        # CapAlloc weighted avg: 85*0.30 + 70*0.25 + 80*0.25 + 75*0.20
        # = 25.5 + 17.5 + 20.0 + 15.0 = 78.0
        # Composite: 81.75*0.50 + 73.0*0.30 + 78.0*0.20
        # = 40.875 + 21.9 + 15.6 = 78.375
        assert result.composite_percentile == pytest.approx(78.375)
        assert result.ticker == "COST"

    def test_winning_track_set_to_compounder(self):
        result = compute_compounder_score(
            ticker="COST",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
        )
        assert result.winning_track == "compounder"

    def test_capital_allocation_pillar_set(self):
        result = compute_compounder_score(
            ticker="COST",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
        )
        assert result.capital_allocation is not None
        assert result.capital_allocation.factor_name == "capital_allocation"
        assert result.capital_allocation.weight == pytest.approx(0.20)

    def test_momentum_empty_with_zero_weight(self):
        result = compute_compounder_score(
            ticker="COST",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
        )
        assert result.momentum.weight == pytest.approx(0.0)
        assert result.momentum.sub_scores == []

    def test_catalyst_not_set(self):
        result = compute_compounder_score(
            ticker="COST",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
        )
        assert result.catalyst is None


# ---------------------------------------------------------------------------
# Growth stage weight adjustments
# ---------------------------------------------------------------------------


class TestGrowthStageWeights:
    """Track A pillar weights vary by growth stage."""

    def test_high_growth_weights(self):
        """High Growth: 55% quality, 25% value, 20% cap alloc."""
        result = compute_compounder_score(
            ticker="NVDA",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
            growth_stage=GrowthStage.HIGH_GROWTH,
        )
        assert result.quality.weight == pytest.approx(0.55)
        assert result.value.weight == pytest.approx(0.25)
        assert result.capital_allocation.weight == pytest.approx(0.20)

    def test_mature_weights(self):
        """Mature: 40% quality, 35% value, 25% cap alloc."""
        result = compute_compounder_score(
            ticker="KO",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
            growth_stage=GrowthStage.MATURE,
        )
        assert result.quality.weight == pytest.approx(0.40)
        assert result.value.weight == pytest.approx(0.35)
        assert result.capital_allocation.weight == pytest.approx(0.25)

    def test_cyclical_weights(self):
        """Cyclical: 45% quality, 30% value, 25% cap alloc."""
        result = compute_compounder_score(
            ticker="CAT",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
            growth_stage=GrowthStage.CYCLICAL,
        )
        assert result.quality.weight == pytest.approx(0.45)
        assert result.value.weight == pytest.approx(0.30)
        assert result.capital_allocation.weight == pytest.approx(0.25)

    def test_turnaround_weights(self):
        """Turnaround: 40% quality, 35% value, 25% cap alloc."""
        result = compute_compounder_score(
            ticker="GE",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert result.quality.weight == pytest.approx(0.40)
        assert result.value.weight == pytest.approx(0.35)
        assert result.capital_allocation.weight == pytest.approx(0.25)

    def test_no_growth_stage_defaults_to_steady(self):
        """None growth stage uses Steady Growth weights (50/30/20)."""
        result = compute_compounder_score(
            ticker="COST",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
            growth_stage=None,
        )
        assert result.quality.weight == pytest.approx(0.50)
        assert result.value.weight == pytest.approx(0.30)
        assert result.capital_allocation.weight == pytest.approx(0.20)

    def test_high_growth_composite_value(self):
        """High Growth composite should reflect adjusted weights."""
        result = compute_compounder_score(
            ticker="NVDA",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
            growth_stage=GrowthStage.HIGH_GROWTH,
        )
        # Quality=81.75, Value=73.0, CapAlloc=78.0
        # 81.75*0.55 + 73.0*0.25 + 78.0*0.20 = 44.9625 + 18.25 + 15.6 = 78.8125
        assert result.composite_percentile == pytest.approx(78.8125)


# ---------------------------------------------------------------------------
# Data coverage
# ---------------------------------------------------------------------------


class TestDataCoverage:
    """data_coverage is passed through directly."""

    def test_full_coverage(self):
        result = compute_compounder_score(
            ticker="COST",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
            data_coverage=0.95,
        )
        assert result.data_coverage == pytest.approx(0.95)

    def test_default_coverage(self):
        result = compute_compounder_score(
            ticker="COST",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
        )
        assert result.data_coverage == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Filters and sub-scores passthrough
# ---------------------------------------------------------------------------


class TestPassthrough:
    """Filters and sub-scores are preserved in the result."""

    def test_filters_passed_through(self):
        filters = [_filter("altman_z"), _filter("beneish")]
        result = compute_compounder_score(
            ticker="COST",
            quality_scores=_quality_scores(),
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=filters,
        )
        assert len(result.filters_passed) == 2

    def test_quality_sub_scores_preserved(self):
        quality = _quality_scores()
        result = compute_compounder_score(
            ticker="COST",
            quality_scores=quality,
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
        )
        assert len(result.quality.sub_scores) == 5
        assert result.quality.sub_scores[0].name == "roic_stability"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for the compounder composite scorer."""

    def test_empty_quality_scores(self):
        result = compute_compounder_score(
            ticker="EDGE",
            quality_scores=[],
            value_scores=_value_scores(),
            capital_allocation_scores=_cap_alloc_scores(),
            filters_passed=[],
        )
        # Empty quality avg = 0.0, only value + cap_alloc contribute
        assert result.composite_percentile >= 0.0
        assert result.quality.average_percentile == pytest.approx(0.0)

    def test_all_perfect_scores(self):
        quality = [_fs("q", 100.0, weight=1.0)]
        value = [_fs("v", 100.0, weight=1.0)]
        cap_alloc = [_fs("ca", 100.0, weight=1.0)]
        result = compute_compounder_score(
            ticker="PERF",
            quality_scores=quality,
            value_scores=value,
            capital_allocation_scores=cap_alloc,
            filters_passed=[],
        )
        assert result.composite_percentile == pytest.approx(100.0)

    def test_all_zero_scores(self):
        quality = [_fs("q", 0.0, weight=1.0)]
        value = [_fs("v", 0.0, weight=1.0)]
        cap_alloc = [_fs("ca", 0.0, weight=1.0)]
        result = compute_compounder_score(
            ticker="ZERO",
            quality_scores=quality,
            value_scores=value,
            capital_allocation_scores=cap_alloc,
            filters_passed=[],
        )
        assert result.composite_percentile == pytest.approx(0.0)
