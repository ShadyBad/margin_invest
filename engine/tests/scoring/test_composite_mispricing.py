"""Tests for Track B (mispricing) composite scorer."""

import pytest
from margin_engine.models.scoring import (
    FactorScore,
    FilterResult,
)
from margin_engine.scoring.composite_mispricing import compute_mispricing_score

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fs(name: str, percentile: float, weight: float | None = None) -> FactorScore:
    return FactorScore(name=name, raw_value=1.0, percentile_rank=percentile, weight=weight)


def _filter(name: str = "altman_z", passed: bool = True) -> FilterResult:
    return FilterResult(name=name, passed=passed, value=3.0, threshold=1.81)


def _value_scores() -> list[FactorScore]:
    """Track B value sub-factors with spec weights."""
    return [
        _fs("dcf_mos", 85.0, weight=0.30),
        _fs("owner_earnings_yield", 80.0, weight=0.25),
        _fs("acquirers_multiple", 75.0, weight=0.25),
        _fs("asymmetry_ratio", 90.0, weight=0.20),
    ]


def _quality_floor_scores() -> list[FactorScore]:
    """Track B quality floor sub-factors with spec weights."""
    return [
        _fs("roic_trajectory", 70.0, weight=0.40),
        _fs("gross_profitability", 65.0, weight=0.30),
        _fs("earnings_quality", 60.0, weight=0.30),
    ]


def _catalyst_scores() -> list[FactorScore]:
    """Track B catalyst sub-factors with spec weights."""
    return [
        _fs("insider_cluster", 80.0, weight=0.35),
        _fs("institutional_accumulation", 75.0, weight=0.35),
        _fs("contrarian_signal", 85.0, weight=0.30),
    ]


# ---------------------------------------------------------------------------
# Basic composite computation
# ---------------------------------------------------------------------------


class TestBasicMispricing:
    """Core Track B composite calculation with fixed weights."""

    def test_weighted_composite(self):
        """Value(45%) + Quality Floor(25%) + Catalyst(30%)."""
        value = _value_scores()
        quality_floor = _quality_floor_scores()
        catalyst = _catalyst_scores()

        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=value,
            quality_floor_scores=quality_floor,
            catalyst_scores=catalyst,
            filters_passed=[_filter()],
        )

        # Value weighted avg: 85*0.30 + 80*0.25 + 75*0.25 + 90*0.20
        # = 25.5 + 20.0 + 18.75 + 18.0 = 82.25
        # QualityFloor weighted avg: 70*0.40 + 65*0.30 + 60*0.30
        # = 28.0 + 19.5 + 18.0 = 65.5
        # Catalyst weighted avg: 80*0.35 + 75*0.35 + 85*0.30
        # = 28.0 + 26.25 + 25.5 = 79.75
        # Composite: 82.25*0.45 + 65.5*0.25 + 79.75*0.30
        # = 37.0125 + 16.375 + 23.925 = 77.3125
        assert result.composite_percentile == pytest.approx(77.3125)
        assert result.ticker == "DEEP"

    def test_winning_track_set_to_mispricing(self):
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
            filters_passed=[],
        )
        assert result.winning_track == "mispricing"

    def test_catalyst_pillar_set(self):
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
            filters_passed=[],
        )
        assert result.catalyst is not None
        assert result.catalyst.factor_name == "catalyst"
        assert result.catalyst.weight == pytest.approx(0.30)

    def test_quality_field_used_for_quality_floor(self):
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
            filters_passed=[],
        )
        assert result.quality.factor_name == "quality_floor"
        assert result.quality.weight == pytest.approx(0.25)

    def test_momentum_empty_with_zero_weight(self):
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
            filters_passed=[],
        )
        assert result.momentum.weight == pytest.approx(0.0)
        assert result.momentum.sub_scores == []

    def test_capital_allocation_not_set(self):
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
            filters_passed=[],
        )
        assert result.capital_allocation is None


# ---------------------------------------------------------------------------
# Fixed weights (no growth stage variation)
# ---------------------------------------------------------------------------


class TestFixedWeights:
    """Track B weights are FIXED — do not vary by growth stage."""

    def test_weights_same_regardless_of_growth_stage(self):
        """Weights should not change even if data_coverage varies."""
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
            filters_passed=[],
        )
        assert result.value.weight == pytest.approx(0.45)
        assert result.quality.weight == pytest.approx(0.25)
        assert result.catalyst.weight == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# Data coverage
# ---------------------------------------------------------------------------


class TestDataCoverage:
    """data_coverage is passed through directly."""

    def test_custom_coverage(self):
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
            filters_passed=[],
            data_coverage=0.80,
        )
        assert result.data_coverage == pytest.approx(0.80)

    def test_default_coverage(self):
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
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
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
            filters_passed=filters,
        )
        assert len(result.filters_passed) == 2

    def test_catalyst_sub_scores_preserved(self):
        result = compute_mispricing_score(
            ticker="DEEP",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=_catalyst_scores(),
            filters_passed=[],
        )
        assert len(result.catalyst.sub_scores) == 3
        assert result.catalyst.sub_scores[0].name == "insider_cluster"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for the mispricing composite scorer."""

    def test_all_perfect_scores(self):
        value = [_fs("v", 100.0, weight=1.0)]
        qf = [_fs("qf", 100.0, weight=1.0)]
        cat = [_fs("c", 100.0, weight=1.0)]
        result = compute_mispricing_score(
            ticker="PERF",
            value_scores=value,
            quality_floor_scores=qf,
            catalyst_scores=cat,
            filters_passed=[],
        )
        assert result.composite_percentile == pytest.approx(100.0)

    def test_all_zero_scores(self):
        value = [_fs("v", 0.0, weight=1.0)]
        qf = [_fs("qf", 0.0, weight=1.0)]
        cat = [_fs("c", 0.0, weight=1.0)]
        result = compute_mispricing_score(
            ticker="ZERO",
            value_scores=value,
            quality_floor_scores=qf,
            catalyst_scores=cat,
            filters_passed=[],
        )
        assert result.composite_percentile == pytest.approx(0.0)

    def test_empty_catalyst_scores(self):
        result = compute_mispricing_score(
            ticker="EDGE",
            value_scores=_value_scores(),
            quality_floor_scores=_quality_floor_scores(),
            catalyst_scores=[],
            filters_passed=[],
        )
        assert result.catalyst.average_percentile == pytest.approx(0.0)
        assert result.composite_percentile >= 0.0
