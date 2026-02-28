"""Tests for v2 fields in ScoreResponse schema."""

from margin_api.schemas.scores import (
    FactorBreakdownResponse,
    FactorScoreResponse,
    ScoreResponse,
)


def _minimal_breakdown(name: str = "quality") -> FactorBreakdownResponse:
    return FactorBreakdownResponse(
        factor_name=name,
        weight=0.35,
        sub_scores=[],
        average_percentile=75.0,
    )


class TestV2ScoreResponse:
    def test_v2_fields_default_to_none(self):
        resp = ScoreResponse(
            ticker="TEST",
            composite_percentile=95.0,
            composite_tier="high",
            signal="buy",
            quality=_minimal_breakdown("quality"),
            value=_minimal_breakdown("value"),
            momentum=_minimal_breakdown("momentum"),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert resp.opportunity_type is None
        assert resp.winning_track is None
        assert resp.asymmetry_ratio is None
        assert resp.max_position_pct is None
        assert resp.timing_signal is None
        assert resp.capital_allocation is None
        assert resp.catalyst is None

    def test_v2_fields_populated(self):
        cap_alloc = FactorBreakdownResponse(
            factor_name="capital_allocation",
            weight=0.20,
            sub_scores=[
                FactorScoreResponse(
                    name="buyback_effectiveness",
                    raw_value=0.85,
                    percentile_rank=72.0,
                )
            ],
            average_percentile=72.0,
        )
        resp = ScoreResponse(
            ticker="COST",
            composite_percentile=99.5,
            composite_tier="high",
            signal="buy",
            quality=_minimal_breakdown("quality"),
            value=_minimal_breakdown("value"),
            momentum=_minimal_breakdown("momentum"),
            filters_passed=[],
            data_coverage=1.0,
            opportunity_type="compounder",
            winning_track="compounder",
            asymmetry_ratio=4.2,
            max_position_pct=10.0,
            timing_signal="buy_now",
            capital_allocation=cap_alloc,
            catalyst=None,
        )
        assert resp.opportunity_type == "compounder"
        assert resp.winning_track == "compounder"
        assert resp.asymmetry_ratio == 4.2
        assert resp.max_position_pct == 10.0
        assert resp.timing_signal == "buy_now"
        assert resp.capital_allocation.factor_name == "capital_allocation"
