"""Tests for scoring result models."""

import pytest

from margin_engine.models.scoring import (
    CompositeScore,
    FactorBreakdown,
    FactorScore,
    OpportunityType,
    Signal,
)


def test_composite_score_price_fields():
    score = CompositeScore(
        ticker="AAPL",
        composite_percentile=96.0,
        quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
        value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
        momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
        filters_passed=[],
        data_coverage=1.0,
        intrinsic_value=195.20,
        buy_price=195.20,
        sell_price=234.24,
        actual_price=167.42,
        price_upside=0.166,
        valuation_methods={"dcf": 210.0, "ev_fcf": 185.0},
    )
    assert score.intrinsic_value == 195.20
    assert score.buy_price == 195.20
    assert score.sell_price == 234.24
    assert score.actual_price == 167.42
    assert score.price_upside == 0.166
    assert score.valuation_methods == {"dcf": 210.0, "ev_fcf": 185.0}


def test_composite_score_price_fields_default_none():
    score = CompositeScore(
        ticker="AAPL",
        composite_percentile=50.0,
        quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
        value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
        momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
        filters_passed=[],
        data_coverage=1.0,
    )
    assert score.intrinsic_value is None
    assert score.buy_price is None
    assert score.sell_price is None
    assert score.actual_price is None
    assert score.price_upside is None
    assert score.valuation_methods is None


# ---------------------------------------------------------------------------
# Price-aware signal tests
# ---------------------------------------------------------------------------


def _make_score(percentile, actual=None, buy=None, sell=None, growth_stage=None):
    return CompositeScore(
        ticker="TEST",
        composite_percentile=percentile,
        quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
        value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
        momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
        filters_passed=[],
        data_coverage=1.0,
        growth_stage=growth_stage,
        actual_price=actual,
        buy_price=buy,
        sell_price=sell,
    )


def test_signal_buy_when_below_buy_price():
    score = _make_score(99.4, actual=100.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.BUY


def test_signal_hold_when_between_buy_and_sell():
    score = _make_score(99.4, actual=135.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.HOLD


def test_signal_sell_when_above_sell_price():
    score = _make_score(99.4, actual=155.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.SELL


def test_signal_urgent_sell_when_far_above_sell():
    score = _make_score(99.4, actual=175.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.URGENT_SELL


def test_signal_watch_for_watchlist_conviction():
    score = _make_score(98.5, actual=100.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.WATCH


def test_signal_no_action_for_low_conviction():
    score = _make_score(50.0, actual=100.0, buy=120.0, sell=150.0)
    assert score.signal == Signal.NO_ACTION


def test_signal_fallback_buy_when_no_prices():
    score = _make_score(99.4)
    assert score.signal == Signal.BUY


# ---------------------------------------------------------------------------
# OpportunityType enum tests
# ---------------------------------------------------------------------------


class TestOpportunityType:
    def test_compounder_value(self):
        assert OpportunityType.COMPOUNDER == "compounder"

    def test_mispricing_value(self):
        assert OpportunityType.MISPRICING == "mispricing"

    def test_both_value(self):
        assert OpportunityType.BOTH == "both"

    def test_neither_value(self):
        assert OpportunityType.NEITHER == "neither"


# ---------------------------------------------------------------------------
# FactorBreakdown weighted percentile tests
# ---------------------------------------------------------------------------


class TestFactorBreakdownWeighted:
    def test_weighted_average_with_weights(self):
        scores = [
            FactorScore(name="a", raw_value=1.0, percentile_rank=90.0, weight=0.6),
            FactorScore(name="b", raw_value=2.0, percentile_rank=70.0, weight=0.4),
        ]
        bd = FactorBreakdown(factor_name="test", weight=1.0, sub_scores=scores)
        assert bd.average_percentile == pytest.approx(82.0)

    def test_weighted_average_falls_back_to_simple_when_no_weights(self):
        scores = [
            FactorScore(name="a", raw_value=1.0, percentile_rank=90.0),
            FactorScore(name="b", raw_value=2.0, percentile_rank=70.0),
        ]
        bd = FactorBreakdown(factor_name="test", weight=1.0, sub_scores=scores)
        assert bd.average_percentile == pytest.approx(80.0)

    def test_weighted_average_partial_weights_falls_back_to_simple(self):
        """When only some sub-scores have weights, fall back to simple average."""
        scores = [
            FactorScore(name="a", raw_value=1.0, percentile_rank=90.0, weight=0.6),
            FactorScore(name="b", raw_value=2.0, percentile_rank=70.0),
        ]
        bd = FactorBreakdown(factor_name="test", weight=1.0, sub_scores=scores)
        assert bd.average_percentile == pytest.approx(80.0)

    def test_weighted_average_empty_sub_scores(self):
        bd = FactorBreakdown(factor_name="test", weight=1.0, sub_scores=[])
        assert bd.average_percentile == 0.0


# ---------------------------------------------------------------------------
# CompositeScore v2 fields tests
# ---------------------------------------------------------------------------


def _make_composite(**kwargs):
    """Create a minimal CompositeScore with sensible defaults."""
    defaults = dict(
        ticker="TEST",
        composite_percentile=50.0,
        quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
        value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
        momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
        filters_passed=[],
        data_coverage=1.0,
    )
    defaults.update(kwargs)
    return CompositeScore(**defaults)


class TestCompositeScoreV2Fields:
    def test_opportunity_type_defaults_to_none(self):
        score = _make_composite()
        assert score.opportunity_type is None

    def test_winning_track_defaults_to_none(self):
        score = _make_composite()
        assert score.winning_track is None

    def test_asymmetry_ratio_defaults_to_none(self):
        score = _make_composite()
        assert score.asymmetry_ratio is None

    def test_max_position_pct_defaults_to_none(self):
        score = _make_composite()
        assert score.max_position_pct is None

    def test_timing_signal_defaults_to_none(self):
        score = _make_composite()
        assert score.timing_signal is None

    def test_capital_allocation_defaults_to_none(self):
        score = _make_composite()
        assert score.capital_allocation is None

    def test_catalyst_defaults_to_none(self):
        score = _make_composite()
        assert score.catalyst is None

    def test_opportunity_type_can_be_set(self):
        score = _make_composite(opportunity_type=OpportunityType.COMPOUNDER)
        assert score.opportunity_type == OpportunityType.COMPOUNDER

    def test_winning_track_can_be_set(self):
        score = _make_composite(winning_track="compounder")
        assert score.winning_track == "compounder"

    def test_asymmetry_ratio_can_be_set(self):
        score = _make_composite(asymmetry_ratio=3.5)
        assert score.asymmetry_ratio == 3.5

    def test_max_position_pct_can_be_set(self):
        score = _make_composite(max_position_pct=5.0)
        assert score.max_position_pct == 5.0

    def test_timing_signal_can_be_set(self):
        score = _make_composite(timing_signal="buy_now")
        assert score.timing_signal == "buy_now"

    def test_capital_allocation_pillar(self):
        cap_alloc = FactorBreakdown(
            factor_name="capital_allocation",
            weight=0.25,
            sub_scores=[
                FactorScore(name="roic_stability", raw_value=0.85, percentile_rank=75.0),
            ],
        )
        score = _make_composite(capital_allocation=cap_alloc)
        assert score.capital_allocation is not None
        assert score.capital_allocation.factor_name == "capital_allocation"

    def test_catalyst_pillar(self):
        catalyst = FactorBreakdown(
            factor_name="catalyst",
            weight=0.20,
            sub_scores=[
                FactorScore(name="contrarian_signal", raw_value=0.9, percentile_rank=88.0),
            ],
        )
        score = _make_composite(catalyst=catalyst)
        assert score.catalyst is not None
        assert score.catalyst.factor_name == "catalyst"
