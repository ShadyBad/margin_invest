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
