"""Tests for ML training data quality — real JSONB unpacking."""

from __future__ import annotations

from margin_api.workers import _composite_from_score_detail


def _make_factor(name: str, weight: float, sub_scores: list[dict]) -> dict:
    """Build a factor dict matching the score_detail JSONB shape."""
    return {
        "factor_name": name,
        "weight": weight,
        "sub_scores": sub_scores,
    }


def _make_full_detail(**overrides) -> dict:
    """Return a well-formed score_detail dict with required pillars."""
    detail = {
        "quality": _make_factor(
            "quality",
            0.35,
            [
                {"name": "roe", "raw_value": 0.45, "percentile_rank": 90.0},
                {"name": "roic", "raw_value": 0.30, "percentile_rank": 80.0},
            ],
        ),
        "value": _make_factor(
            "value",
            0.30,
            [
                {"name": "pe_ratio", "raw_value": 15.0, "percentile_rank": 70.0},
                {"name": "pb_ratio", "raw_value": 2.5, "percentile_rank": 60.0},
            ],
        ),
        "momentum": _make_factor(
            "momentum",
            0.35,
            [
                {"name": "rsi_14d", "raw_value": 55.0, "percentile_rank": 65.0},
                {"name": "price_vs_52w_high", "raw_value": 0.95, "percentile_rank": 75.0},
            ],
        ),
        "filters_passed": [{"name": "market_cap", "passed": True}],
        "composite_percentile": 85.0,
        "composite_raw_score": 78.0,
        "data_coverage": 0.95,
    }
    detail.update(overrides)
    return detail


class TestCompositeFromScoreDetailRealPercentiles:
    """Verify real sub_scores are parsed from score_detail JSONB."""

    def test_composite_from_score_detail_has_real_percentiles(self):
        detail = _make_full_detail()
        composite = _composite_from_score_detail("AAPL", detail)

        assert composite is not None
        assert composite.ticker == "AAPL"

        # Quality factor
        assert composite.quality.factor_name == "quality"
        assert composite.quality.weight == 0.35
        assert len(composite.quality.sub_scores) == 2
        roe = composite.quality.sub_scores[0]
        assert roe.name == "roe"
        assert roe.raw_value == 0.45
        assert roe.percentile_rank == 90.0
        roic = composite.quality.sub_scores[1]
        assert roic.name == "roic"
        assert roic.raw_value == 0.30
        assert roic.percentile_rank == 80.0

        # Value factor
        assert composite.value.factor_name == "value"
        assert composite.value.weight == 0.30
        assert len(composite.value.sub_scores) == 2
        pe = composite.value.sub_scores[0]
        assert pe.name == "pe_ratio"
        assert pe.raw_value == 15.0
        assert pe.percentile_rank == 70.0

        # Momentum factor
        assert composite.momentum.factor_name == "momentum"
        assert composite.momentum.weight == 0.35
        assert len(composite.momentum.sub_scores) == 2

        # Top-level fields
        assert composite.composite_percentile == 85.0
        assert composite.composite_raw_score == 78.0
        assert composite.data_coverage == 0.95
        assert len(composite.filters_passed) == 1
        assert composite.filters_passed[0].name == "market_cap"
        assert composite.filters_passed[0].passed is True


class TestCompositeFromScoreDetailSkipsMalformed:
    """Verify None returned for bad / incomplete data."""

    def test_empty_dict_returns_none(self):
        assert _composite_from_score_detail("AAPL", {}) is None

    def test_missing_quality_returns_none(self):
        detail = _make_full_detail()
        del detail["quality"]
        assert _composite_from_score_detail("AAPL", detail) is None

    def test_missing_value_returns_none(self):
        detail = _make_full_detail()
        del detail["value"]
        assert _composite_from_score_detail("AAPL", detail) is None

    def test_missing_momentum_returns_none(self):
        detail = _make_full_detail()
        del detail["momentum"]
        assert _composite_from_score_detail("AAPL", detail) is None

    def test_quality_missing_sub_scores_returns_none(self):
        detail = _make_full_detail()
        del detail["quality"]["sub_scores"]
        assert _composite_from_score_detail("AAPL", detail) is None

    def test_quality_empty_sub_scores_returns_none(self):
        detail = _make_full_detail()
        detail["quality"]["sub_scores"] = []
        assert _composite_from_score_detail("AAPL", detail) is None

    def test_quality_not_a_dict_returns_none(self):
        detail = _make_full_detail()
        detail["quality"] = "bad"
        assert _composite_from_score_detail("AAPL", detail) is None

    def test_sub_score_missing_percentile_returns_none(self):
        detail = _make_full_detail()
        detail["quality"]["sub_scores"][0] = {"name": "roe", "raw_value": 0.45}
        assert _composite_from_score_detail("AAPL", detail) is None

    def test_none_detail_returns_none(self):
        # Passing an explicitly empty-ish dict
        assert _composite_from_score_detail("AAPL", {}) is None


class TestCompositeFromScoreDetailOptionalPillars:
    """Verify growth/capital_allocation/catalyst parsed when present."""

    def test_parses_growth_pillar(self):
        detail = _make_full_detail(
            growth=_make_factor(
                "growth",
                0.20,
                [
                    {"name": "revenue_growth", "raw_value": 0.25, "percentile_rank": 85.0},
                    {"name": "earnings_growth", "raw_value": 0.18, "percentile_rank": 72.0},
                ],
            )
        )
        composite = _composite_from_score_detail("AAPL", detail)
        assert composite is not None
        assert composite.growth is not None
        assert composite.growth.factor_name == "growth"
        assert composite.growth.weight == 0.20
        assert len(composite.growth.sub_scores) == 2
        assert composite.growth.sub_scores[0].name == "revenue_growth"
        assert composite.growth.sub_scores[0].percentile_rank == 85.0

    def test_parses_capital_allocation_pillar(self):
        detail = _make_full_detail(
            capital_allocation=_make_factor(
                "capital_allocation",
                0.15,
                [
                    {"name": "buyback_yield", "raw_value": 0.03, "percentile_rank": 70.0},
                ],
            )
        )
        composite = _composite_from_score_detail("AAPL", detail)
        assert composite is not None
        assert composite.capital_allocation is not None
        assert composite.capital_allocation.factor_name == "capital_allocation"
        assert composite.capital_allocation.sub_scores[0].percentile_rank == 70.0

    def test_parses_catalyst_pillar(self):
        detail = _make_full_detail(
            catalyst=_make_factor(
                "catalyst",
                0.10,
                [
                    {"name": "sue_percentile", "raw_value": 2.5, "percentile_rank": 88.0},
                ],
            )
        )
        composite = _composite_from_score_detail("AAPL", detail)
        assert composite is not None
        assert composite.catalyst is not None
        assert composite.catalyst.factor_name == "catalyst"
        assert composite.catalyst.sub_scores[0].percentile_rank == 88.0

    def test_all_optional_pillars_together(self):
        detail = _make_full_detail(
            growth=_make_factor("growth", 0.20, [
                {"name": "rev_growth", "raw_value": 0.25, "percentile_rank": 85.0},
            ]),
            capital_allocation=_make_factor("capital_allocation", 0.15, [
                {"name": "buyback_yield", "raw_value": 0.03, "percentile_rank": 70.0},
            ]),
            catalyst=_make_factor("catalyst", 0.10, [
                {"name": "sue_percentile", "raw_value": 2.5, "percentile_rank": 88.0},
            ]),
        )
        composite = _composite_from_score_detail("AAPL", detail)
        assert composite is not None
        assert composite.growth is not None
        assert composite.capital_allocation is not None
        assert composite.catalyst is not None

    def test_malformed_optional_pillar_ignored(self):
        """A malformed optional pillar should not cause failure — just set to None."""
        detail = _make_full_detail(growth="not_a_dict")
        composite = _composite_from_score_detail("AAPL", detail)
        assert composite is not None
        assert composite.growth is None

    def test_optional_pillar_empty_sub_scores_ignored(self):
        """Optional pillar with empty sub_scores should be set to None."""
        detail = _make_full_detail(
            growth=_make_factor("growth", 0.20, [])
        )
        composite = _composite_from_score_detail("AAPL", detail)
        assert composite is not None
        assert composite.growth is None
