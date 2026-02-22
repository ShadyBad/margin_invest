"""Tests for feature matrix construction."""

import numpy as np
from margin_engine.factors.feature_matrix import build_feature_matrix
from margin_engine.factors.registry import default_registry
from margin_engine.models.scoring import (
    CompositeScore,
    FactorBreakdown,
    FactorScore,
    FilterResult,
)


def _make_composite(
    ticker: str,
    quality_scores: list[FactorScore] | None = None,
    value_scores: list[FactorScore] | None = None,
    momentum_scores: list[FactorScore] | None = None,
) -> CompositeScore:
    """Helper to create a minimal CompositeScore for testing."""
    return CompositeScore(
        ticker=ticker,
        composite_percentile=50.0,
        composite_raw_score=70.0,
        quality=FactorBreakdown(
            factor_name="quality",
            weight=0.35,
            sub_scores=quality_scores or [],
        ),
        value=FactorBreakdown(
            factor_name="value",
            weight=0.30,
            sub_scores=value_scores or [],
        ),
        momentum=FactorBreakdown(
            factor_name="momentum",
            weight=0.35,
            sub_scores=momentum_scores or [],
        ),
        filters_passed=[FilterResult(name="test", passed=True)],
        data_coverage=0.9,
    )


class TestBuildFeatureMatrix:
    def test_basic_shape(self) -> None:
        registry = default_registry()
        composites = [
            _make_composite(
                "AAPL",
                quality_scores=[
                    FactorScore(name="gross_profitability", raw_value=0.45, percentile_rank=80.0),
                    FactorScore(name="roic_wacc", raw_value=0.15, percentile_rank=70.0),
                ],
            ),
            _make_composite(
                "MSFT",
                quality_scores=[
                    FactorScore(name="gross_profitability", raw_value=0.60, percentile_rank=90.0),
                ],
            ),
        ]

        matrix, tickers, feature_names = build_feature_matrix(composites, registry)

        assert matrix.shape == (2, len(registry))
        assert tickers == ["AAPL", "MSFT"]
        assert feature_names == sorted(feature_names)

    def test_missing_factors_are_nan(self) -> None:
        registry = default_registry()
        composites = [
            _make_composite(
                "AAPL",
                quality_scores=[
                    FactorScore(name="gross_profitability", raw_value=0.45, percentile_rank=80.0),
                ],
            ),
        ]

        matrix, _, feature_names = build_feature_matrix(composites, registry)

        gp_idx = feature_names.index("gross_profitability")
        assert matrix[0, gp_idx] == 0.45

        # All other columns should be NaN
        for j in range(matrix.shape[1]):
            if j != gp_idx:
                assert np.isnan(matrix[0, j]), f"Expected NaN at column {j}"

    def test_raw_values_extracted(self) -> None:
        registry = default_registry()
        composites = [
            _make_composite(
                "AAPL",
                quality_scores=[
                    FactorScore(name="gross_profitability", raw_value=0.45, percentile_rank=80.0),
                ],
                value_scores=[
                    FactorScore(name="ev_fcf", raw_value=12.5, percentile_rank=65.0),
                ],
                momentum_scores=[
                    FactorScore(name="price_momentum", raw_value=0.08, percentile_rank=55.0),
                ],
            ),
        ]

        matrix, _, feature_names = build_feature_matrix(composites, registry)

        gp_idx = feature_names.index("gross_profitability")
        ev_idx = feature_names.index("ev_fcf")
        pm_idx = feature_names.index("price_momentum")

        assert matrix[0, gp_idx] == 0.45
        assert matrix[0, ev_idx] == 12.5
        assert matrix[0, pm_idx] == 0.08

    def test_empty_composites(self) -> None:
        registry = default_registry()
        matrix, tickers, feature_names = build_feature_matrix([], registry)

        assert matrix.shape == (0, len(registry))
        assert tickers == []
        assert len(feature_names) == len(registry)

    def test_multiple_assets(self) -> None:
        registry = default_registry()
        composites = [
            _make_composite(
                f"T{i}",
                quality_scores=[
                    FactorScore(
                        name="gross_profitability",
                        raw_value=0.1 * i,
                        percentile_rank=float(i * 10),
                    ),
                ],
            )
            for i in range(1, 6)
        ]

        matrix, tickers, feature_names = build_feature_matrix(composites, registry)

        assert matrix.shape[0] == 5
        assert tickers == ["T1", "T2", "T3", "T4", "T5"]

        gp_idx = feature_names.index("gross_profitability")
        for i in range(5):
            assert abs(matrix[i, gp_idx] - 0.1 * (i + 1)) < 1e-10
