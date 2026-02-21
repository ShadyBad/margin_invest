"""Tests for backtest API schemas."""

from margin_api.schemas.backtest import BacktestConfigRequest


def test_config_request_accepts_conviction_mos():
    config = BacktestConfigRequest(
        selection_mode="conviction_mos",
        min_conviction_score=79.0,
        min_margin_of_safety=0.30,
    )
    assert config.selection_mode == "conviction_mos"
    assert config.min_conviction_score == 79.0
    assert config.min_margin_of_safety == 0.30


def test_config_request_defaults_to_top_percentile():
    config = BacktestConfigRequest()
    assert config.selection_mode == "top_percentile"


def test_config_request_backward_compatible():
    """Existing requests without new fields still work."""
    config = BacktestConfigRequest(
        start_date="2020-01-01",
        top_percentile=0.05,
        benchmark_ticker="SPY",
    )
    assert config.selection_mode == "top_percentile"
    assert config.min_conviction_score == 79.0
    assert config.min_margin_of_safety == 0.20


def test_backtest_config_request_v2_fields():
    """New v2 fields have correct defaults."""
    req = BacktestConfigRequest()
    assert req.max_holdings == 5
    assert req.min_conviction_score_high == 72.0
    assert req.min_margin_of_safety == 0.20
