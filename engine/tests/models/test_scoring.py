"""Tests for scoring result models."""

from margin_engine.models.scoring import CompositeScore, FactorBreakdown


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
        buy_price=156.16,
        sell_price=195.20,
        actual_price=167.42,
        price_upside=0.166,
        valuation_methods={"dcf": 210.0, "ev_fcf": 185.0},
    )
    assert score.intrinsic_value == 195.20
    assert score.buy_price == 156.16
    assert score.sell_price == 195.20
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
