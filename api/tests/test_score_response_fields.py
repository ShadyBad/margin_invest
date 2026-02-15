"""Test that ScoreResponse includes name and scored_at fields."""

from margin_api.schemas.scores import FactorBreakdownResponse, ScoreResponse


def test_score_response_includes_name():
    resp = ScoreResponse(
        ticker="AAPL",
        name="Apple Inc.",
        composite_percentile=92.0,
        conviction_level="exceptional",
        signal="buy",
        quality=FactorBreakdownResponse(
            factor_name="quality", weight=0.35, sub_scores=[], average_percentile=88.0,
        ),
        value=FactorBreakdownResponse(
            factor_name="value", weight=0.30, sub_scores=[], average_percentile=72.0,
        ),
        momentum=FactorBreakdownResponse(
            factor_name="momentum", weight=0.35, sub_scores=[], average_percentile=95.0,
        ),
        filters_passed=[],
        data_coverage=0.95,
        scored_at="2026-02-12T08:00:00Z",
    )
    assert resp.name == "Apple Inc."
    assert resp.scored_at == "2026-02-12T08:00:00Z"


def test_score_response_name_defaults_to_empty():
    resp = ScoreResponse(
        ticker="AAPL",
        composite_percentile=92.0,
        conviction_level="exceptional",
        signal="buy",
        quality=FactorBreakdownResponse(
            factor_name="quality", weight=0.35, sub_scores=[], average_percentile=88.0,
        ),
        value=FactorBreakdownResponse(
            factor_name="value", weight=0.30, sub_scores=[], average_percentile=72.0,
        ),
        momentum=FactorBreakdownResponse(
            factor_name="momentum", weight=0.35, sub_scores=[], average_percentile=95.0,
        ),
        filters_passed=[],
        data_coverage=0.95,
    )
    assert resp.name == ""
    assert resp.scored_at is None
