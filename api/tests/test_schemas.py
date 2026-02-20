"""Tests for API response schemas."""

from __future__ import annotations

from margin_api.schemas import (
    DashboardResponse,
    FactorBreakdownResponse,
    FactorScoreResponse,
    FilterResultResponse,
    PickSummary,
    ScoreListResponse,
    ScoreResponse,
    WatchlistItem,
)
from margin_engine.models.scoring import (
    CompositeScore,
    FactorBreakdown,
    FactorScore,
    FilterResult,
    GrowthStage,
)


def _make_factor_breakdown(
    name: str, weight: float, scores: list[tuple[str, float, float]]
) -> FactorBreakdown:
    """Helper to build a FactorBreakdown from (name, raw, percentile) tuples."""
    return FactorBreakdown(
        factor_name=name,
        weight=weight,
        sub_scores=[
            FactorScore(name=n, raw_value=r, percentile_rank=p) for n, r, p in scores
        ],
    )


def _make_composite_score(
    ticker: str = "AAPL",
    percentile: float = 96.0,
    raw_score: float = 75.0,
    growth_stage: GrowthStage | None = None,
) -> CompositeScore:
    """Helper to build a complete CompositeScore for testing."""
    return CompositeScore(
        ticker=ticker,
        composite_percentile=percentile,
        composite_raw_score=raw_score,
        quality=_make_factor_breakdown(
            "quality", 0.35, [("gross_margin", 0.45, 85.0), ("roe", 0.22, 90.0)]
        ),
        value=_make_factor_breakdown(
            "value", 0.30, [("pe_ratio", 18.5, 70.0), ("pb_ratio", 3.2, 65.0)]
        ),
        momentum=_make_factor_breakdown(
            "momentum", 0.35, [("rsi_14d", 62.0, 75.0), ("price_vs_sma200", 1.12, 80.0)]
        ),
        filters_passed=[
            FilterResult(name="min_market_cap", passed=True, value=2.5e12, threshold=1e9),
            FilterResult(
                name="min_volume", passed=False, value=500.0, threshold=1000.0, detail="Too low"
            ),
        ],
        data_coverage=0.95,
        growth_stage=growth_stage,
    )


class TestFilterResultResponse:
    def test_filter_result_response(self) -> None:
        """Create FilterResultResponse and verify serialization."""
        result = FilterResultResponse(
            name="min_market_cap",
            passed=True,
            value=2.5e12,
            threshold=1e9,
            detail="Market cap sufficient",
            verdict="pass",
        )
        data = result.model_dump()
        assert data["name"] == "min_market_cap"
        assert data["passed"] is True
        assert data["value"] == 2.5e12
        assert data["threshold"] == 1e9
        assert data["detail"] == "Market cap sufficient"
        assert data["verdict"] == "pass"

    def test_filter_result_response_defaults(self) -> None:
        """Verify optional fields default correctly."""
        result = FilterResultResponse(
            name="check",
            passed=False,
            verdict="fail",
        )
        data = result.model_dump()
        assert data["value"] is None
        assert data["threshold"] is None
        assert data["detail"] == ""


class TestFactorScoreResponse:
    def test_factor_score_response(self) -> None:
        """Verify FactorScoreResponse serialization."""
        score = FactorScoreResponse(
            name="gross_margin",
            raw_value=0.45,
            percentile_rank=85.0,
            detail="Above sector median",
        )
        data = score.model_dump()
        assert data["name"] == "gross_margin"
        assert data["raw_value"] == 0.45
        assert data["percentile_rank"] == 85.0
        assert data["detail"] == "Above sector median"


class TestFactorBreakdownResponse:
    def test_factor_breakdown_response(self) -> None:
        """Verify sub_scores and average_percentile serialize correctly."""
        breakdown = FactorBreakdownResponse(
            factor_name="quality",
            weight=0.35,
            sub_scores=[
                FactorScoreResponse(name="gross_margin", raw_value=0.45, percentile_rank=85.0),
                FactorScoreResponse(name="roe", raw_value=0.22, percentile_rank=90.0),
            ],
            average_percentile=87.5,
        )
        data = breakdown.model_dump()
        assert data["factor_name"] == "quality"
        assert data["weight"] == 0.35
        assert len(data["sub_scores"]) == 2
        assert data["sub_scores"][0]["name"] == "gross_margin"
        assert data["sub_scores"][1]["name"] == "roe"
        assert data["average_percentile"] == 87.5


class TestScoreResponse:
    def test_score_response_serialization(self) -> None:
        """Create a ScoreResponse manually and verify .model_dump() produces expected structure."""
        response = ScoreResponse(
            ticker="AAPL",
            composite_percentile=96.0,
            conviction_level="high",
            signal="buy",
            quality=FactorBreakdownResponse(
                factor_name="quality",
                weight=0.35,
                sub_scores=[
                    FactorScoreResponse(
                        name="gross_margin", raw_value=0.45, percentile_rank=85.0
                    ),
                ],
                average_percentile=85.0,
            ),
            value=FactorBreakdownResponse(
                factor_name="value",
                weight=0.30,
                sub_scores=[
                    FactorScoreResponse(name="pe_ratio", raw_value=18.5, percentile_rank=70.0),
                ],
                average_percentile=70.0,
            ),
            momentum=FactorBreakdownResponse(
                factor_name="momentum",
                weight=0.35,
                sub_scores=[
                    FactorScoreResponse(name="rsi_14d", raw_value=62.0, percentile_rank=75.0),
                ],
                average_percentile=75.0,
            ),
            filters_passed=[
                FilterResultResponse(
                    name="min_market_cap", passed=True, value=2.5e12, threshold=1e9, verdict="pass"
                ),
            ],
            data_coverage=0.95,
            growth_stage="steady_growth",
        )
        data = response.model_dump()
        assert data["ticker"] == "AAPL"
        assert data["composite_percentile"] == 96.0
        assert data["conviction_level"] == "high"
        assert data["signal"] == "buy"
        assert data["quality"]["factor_name"] == "quality"
        assert data["value"]["factor_name"] == "value"
        assert data["momentum"]["factor_name"] == "momentum"
        assert len(data["filters_passed"]) == 1
        assert data["data_coverage"] == 0.95
        assert data["growth_stage"] == "steady_growth"

    def test_score_response_from_engine(self) -> None:
        """Convert an engine CompositeScore via from_engine() and verify all fields."""
        engine_score = _make_composite_score(
            ticker="MSFT", percentile=99.4, growth_stage=GrowthStage.STEADY_GROWTH
        )
        response = ScoreResponse.from_engine(engine_score)

        assert response.ticker == "MSFT"
        assert response.composite_percentile == 99.4
        assert response.conviction_level == "high"
        assert response.signal == "buy"

        # Quality breakdown
        assert response.quality.factor_name == "quality"
        assert response.quality.weight == 0.35
        assert len(response.quality.sub_scores) == 2
        assert response.quality.sub_scores[0].name == "gross_margin"
        assert response.quality.sub_scores[0].raw_value == 0.45
        assert response.quality.sub_scores[0].percentile_rank == 85.0
        assert response.quality.average_percentile == 87.5

        # Value breakdown
        assert response.value.factor_name == "value"
        assert response.value.weight == 0.30
        assert len(response.value.sub_scores) == 2
        assert response.value.average_percentile == 67.5

        # Momentum breakdown
        assert response.momentum.factor_name == "momentum"
        assert response.momentum.weight == 0.35
        assert len(response.momentum.sub_scores) == 2
        assert response.momentum.average_percentile == 77.5

        # Filters
        assert len(response.filters_passed) == 2
        assert response.filters_passed[0].name == "min_market_cap"
        assert response.filters_passed[0].passed is True
        assert response.filters_passed[0].verdict == "pass"
        assert response.filters_passed[1].name == "min_volume"
        assert response.filters_passed[1].passed is False
        assert response.filters_passed[1].verdict == "fail"

        assert response.data_coverage == 0.95
        assert response.growth_stage == "steady_growth"

    def test_from_engine_with_growth_stage(self) -> None:
        """CompositeScore with a growth_stage set maps to string value."""
        engine_score = _make_composite_score(growth_stage=GrowthStage.HIGH_GROWTH)
        response = ScoreResponse.from_engine(engine_score)
        assert response.growth_stage == "high_growth"

    def test_from_engine_without_growth_stage(self) -> None:
        """CompositeScore with growth_stage=None maps to None."""
        engine_score = _make_composite_score(growth_stage=None)
        response = ScoreResponse.from_engine(engine_score)
        assert response.growth_stage is None

    def test_score_response_has_score_field(self) -> None:
        """ScoreResponse must include score and universe_percentile."""
        response = ScoreResponse(
            ticker="AAPL",
            composite_percentile=100.0,
            composite_raw_score=87.4,
            score=87.4,
            universe_percentile=100.0,
            conviction_level="exceptional",
            signal="buy",
            quality=FactorBreakdownResponse(
                factor_name="quality", weight=0.35, sub_scores=[], average_percentile=90.0,
            ),
            value=FactorBreakdownResponse(
                factor_name="value", weight=0.30, sub_scores=[], average_percentile=85.0,
            ),
            momentum=FactorBreakdownResponse(
                factor_name="momentum", weight=0.35, sub_scores=[], average_percentile=88.0,
            ),
            filters_passed=[],
            data_coverage=0.95,
        )
        data = response.model_dump()
        assert data["score"] == 87.4
        assert data["universe_percentile"] == 100.0

    def test_from_engine_propagates_price_target_invalid_reason(self) -> None:
        """price_target_invalid_reason from engine should surface in response."""
        engine_score = _make_composite_score(ticker="BAD", percentile=50.0)
        response = ScoreResponse.from_engine(engine_score)
        assert response.price_target_invalid_reason is None

    def test_from_engine_populates_score_and_universe_percentile(self) -> None:
        """from_engine() must populate score from composite_raw_score and
        universe_percentile from composite_percentile."""
        engine_score = _make_composite_score(ticker="TEST", percentile=99.0)
        engine_score = engine_score.model_copy(update={"composite_raw_score": 82.5})
        response = ScoreResponse.from_engine(engine_score)
        assert response.score == 82.5
        assert response.universe_percentile == 99.0


class TestScoreListResponse:
    def test_score_list_response(self) -> None:
        """Verify pagination fields and scores list."""
        response = ScoreListResponse(
            scores=[],
            total=0,
        )
        data = response.model_dump()
        assert data["scores"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_score_list_response_with_items(self) -> None:
        """Verify list with actual scores and custom pagination."""
        score = ScoreResponse(
            ticker="GOOG",
            composite_percentile=92.0,
            conviction_level="medium",
            signal="watch",
            quality=FactorBreakdownResponse(
                factor_name="quality",
                weight=0.35,
                sub_scores=[],
                average_percentile=0.0,
            ),
            value=FactorBreakdownResponse(
                factor_name="value",
                weight=0.30,
                sub_scores=[],
                average_percentile=0.0,
            ),
            momentum=FactorBreakdownResponse(
                factor_name="momentum",
                weight=0.35,
                sub_scores=[],
                average_percentile=0.0,
            ),
            filters_passed=[],
            data_coverage=0.88,
        )
        response = ScoreListResponse(
            scores=[score],
            total=1,
            page=2,
            page_size=25,
        )
        data = response.model_dump()
        assert len(data["scores"]) == 1
        assert data["scores"][0]["ticker"] == "GOOG"
        assert data["total"] == 1
        assert data["page"] == 2
        assert data["page_size"] == 25


class TestPickSummary:
    def test_pick_summary(self) -> None:
        """Verify PickSummary serialization."""
        pick = PickSummary(
            score_id=1,
            ticker="NVDA",
            name="NVIDIA Corporation",
            composite_percentile=99.5,
            conviction_level="exceptional",
            signal="buy",
            quality_percentile=97.0,
            value_percentile=85.0,
            momentum_percentile=98.0,
        )
        data = pick.model_dump()
        assert data["ticker"] == "NVDA"
        assert data["name"] == "NVIDIA Corporation"
        assert data["composite_percentile"] == 99.5
        assert data["conviction_level"] == "exceptional"
        assert data["signal"] == "buy"
        assert data["quality_percentile"] == 97.0
        assert data["value_percentile"] == 85.0
        assert data["momentum_percentile"] == 98.0

    def test_pick_summary_has_score_field(self) -> None:
        """PickSummary must include score and universe_percentile."""
        pick = PickSummary(
            score_id=1,
            ticker="NVDA",
            name="NVIDIA Corporation",
            composite_percentile=99.5,
            score=91.2,
            universe_percentile=99.5,
            conviction_level="exceptional",
            signal="buy",
            quality_percentile=97.0,
            value_percentile=85.0,
            momentum_percentile=98.0,
        )
        data = pick.model_dump()
        assert data["score"] == 91.2
        assert data["universe_percentile"] == 99.5


class TestWatchlistItem:
    def test_watchlist_item(self) -> None:
        """Verify WatchlistItem serialization."""
        item = WatchlistItem(
            ticker="AMZN",
            name="Amazon.com Inc.",
            composite_raw_score=73.0,
            conviction_level="medium",
        )
        data = item.model_dump()
        assert data["ticker"] == "AMZN"
        assert data["name"] == "Amazon.com Inc."
        assert data["composite_raw_score"] == 73.0
        assert data["conviction_level"] == "medium"

    def test_watchlist_item_enriched_fields(self) -> None:
        """Verify WatchlistItem with all enriched fields."""
        item = WatchlistItem(
            ticker="MSFT",
            name="Microsoft Corp",
            composite_raw_score=67.5,
            conviction_level="medium",
            sector="Information Technology",
            actual_price=420.50,
            price_upside=0.15,
            opportunity_type="compounder",
        )
        assert item.composite_raw_score == 67.5
        assert item.sector == "Information Technology"
        assert item.actual_price == 420.50
        assert item.price_upside == 0.15
        assert item.opportunity_type == "compounder"


class TestDashboardResponse:
    def test_dashboard_response(self) -> None:
        """Verify DashboardResponse with picks and watchlist."""
        response = DashboardResponse(
            picks=[
                PickSummary(
                    score_id=1,
                    ticker="NVDA",
                    name="NVIDIA Corporation",
                    composite_percentile=99.5,
                    conviction_level="exceptional",
                    signal="buy",
                    quality_percentile=97.0,
                    value_percentile=85.0,
                    momentum_percentile=98.0,
                ),
            ],
            watchlist=[
                WatchlistItem(
                    ticker="AMZN",
                    name="Amazon.com Inc.",
                    composite_raw_score=73.0,
                    conviction_level="medium",
                ),
            ],
            last_updated="2026-02-12T10:30:00Z",
            total_scored=500,
        )
        data = response.model_dump()
        assert len(data["picks"]) == 1
        assert data["picks"][0]["ticker"] == "NVDA"
        assert len(data["watchlist"]) == 1
        assert data["watchlist"][0]["ticker"] == "AMZN"
        assert data["last_updated"] == "2026-02-12T10:30:00Z"
        assert data["total_scored"] == 500

    def test_dashboard_response_empty(self) -> None:
        """Verify DashboardResponse with empty lists."""
        response = DashboardResponse(
            picks=[],
            watchlist=[],
            last_updated="2026-02-12T00:00:00Z",
            total_scored=0,
        )
        data = response.model_dump()
        assert data["picks"] == []
        assert data["watchlist"] == []
        assert data["total_scored"] == 0
