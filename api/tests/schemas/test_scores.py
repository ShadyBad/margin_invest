"""Tests for score-related API schemas."""

from margin_api.schemas.scores import ScoreResponse, PriceBarResponse, SignalTransitionResponse


def test_score_response_has_price_fields():
    data = {
        "ticker": "AAPL",
        "composite_percentile": 96.0,
        "conviction_level": "high",
        "signal": "buy",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 80.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 75.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 60.0},
        "filters_passed": [],
        "data_coverage": 1.0,
        "intrinsic_value": 195.20,
        "buy_price": 156.16,
        "sell_price": 195.20,
        "actual_price": 167.42,
        "price_upside": 0.166,
        "valuation_methods": {"dcf": 210.0},
    }
    resp = ScoreResponse(**data)
    assert resp.intrinsic_value == 195.20
    assert resp.buy_price == 156.16
    assert resp.actual_price == 167.42


def test_score_response_price_fields_default_none():
    data = {
        "ticker": "AAPL",
        "composite_percentile": 50.0,
        "conviction_level": "none",
        "signal": "no_action",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 50.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 50.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 50.0},
        "filters_passed": [],
        "data_coverage": 1.0,
    }
    resp = ScoreResponse(**data)
    assert resp.intrinsic_value is None
    assert resp.buy_price is None
    assert resp.price_history is None


def test_price_bar_response():
    bar = PriceBarResponse(
        date="2025-09-28", open=195.0, high=198.0, low=194.0,
        close=197.0, volume=50000000, adj_close=197.0,
    )
    assert bar.close == 197.0


def test_signal_transition_response():
    t = SignalTransitionResponse(
        previous_signal="watch",
        new_signal="buy",
        previous_conviction="watchlist",
        new_conviction="high",
        actual_price_at_transition=167.42,
        intrinsic_value_at_transition=195.20,
        composite_percentile=96.0,
        transitioned_at="2026-02-14T00:00:00+00:00",
    )
    assert t.new_signal == "buy"
