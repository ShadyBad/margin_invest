"""Tests for score-to-return alpha calibration."""

from __future__ import annotations

from margin_engine.models.scoring import (
    CompositeScore,
    FactorBreakdown,
    FactorScore,
    FilterResult,
)
from margin_engine.optimization.alpha_mapper import (
    calibrate_alpha,
    calibrate_alpha_from_backtest,
    v4_to_candidates,
)


def _make_composite(ticker: str, score: float) -> CompositeScore:
    """Create a minimal CompositeScore for testing."""
    dummy_factor = FactorBreakdown(
        factor_name="test",
        weight=1.0,
        sub_scores=[FactorScore(name="x", raw_value=0.5, percentile_rank=50.0)],
    )
    return CompositeScore(
        ticker=ticker,
        composite_percentile=score,
        composite_raw_score=score,
        quality=dummy_factor,
        value=dummy_factor,
        momentum=dummy_factor,
        filters_passed=[FilterResult(name="test", passed=True)],
        data_coverage=1.0,
    )


class TestCalibrateAlpha:
    """Tests for z-score rank calibration."""

    def test_z_scores_sum_near_zero(self):
        """Z-scored alphas should approximately sum to zero."""
        composites = [_make_composite(f"T{i}", 50.0 + i * 5) for i in range(10)]
        alphas = calibrate_alpha(composites, target_spread=0.10)
        total = sum(alphas.values())
        assert abs(total) < 1e-10

    def test_target_spread_scaling(self):
        """Wider target_spread should produce larger alpha range."""
        composites = [_make_composite(f"T{i}", 50.0 + i * 10) for i in range(5)]
        alphas_narrow = calibrate_alpha(composites, target_spread=0.05)
        alphas_wide = calibrate_alpha(composites, target_spread=0.20)

        range_narrow = max(alphas_narrow.values()) - min(alphas_narrow.values())
        range_wide = max(alphas_wide.values()) - min(alphas_wide.values())
        assert range_wide > range_narrow

    def test_higher_score_gets_higher_alpha(self):
        """Higher composite scores should map to higher alphas."""
        composites = [
            _make_composite("LOW", 40.0),
            _make_composite("MID", 60.0),
            _make_composite("HIGH", 80.0),
        ]
        alphas = calibrate_alpha(composites)
        assert alphas["HIGH"] > alphas["MID"] > alphas["LOW"]

    def test_empty_returns_empty(self):
        assert calibrate_alpha([]) == {}

    def test_single_returns_zero(self):
        alphas = calibrate_alpha([_make_composite("ONLY", 75.0)])
        assert alphas["ONLY"] == 0.0

    def test_equal_scores_all_zero(self):
        """All identical scores -> all zero alpha."""
        composites = [_make_composite(f"T{i}", 50.0) for i in range(5)]
        alphas = calibrate_alpha(composites)
        assert all(abs(v) < 1e-10 for v in alphas.values())


class TestCalibrateAlphaFromBacktest:
    """Tests for empirical bucket calibration."""

    def test_basic_buckets(self):
        """Higher score buckets should have higher returns."""
        scores = {f"T{i}": [float(i * 10)] for i in range(10)}
        returns = {f"T{i}": [float(i * 0.01)] for i in range(10)}

        result = calibrate_alpha_from_backtest(scores, returns, n_buckets=5)
        # Should have 5 buckets
        assert len(result) == 5
        # Higher buckets should generally have higher returns
        assert result[4] >= result[0]

    def test_empty_returns_empty(self):
        assert calibrate_alpha_from_backtest({}, {}) == {}

    def test_mismatched_tickers_uses_intersection(self):
        scores = {"A": [50.0], "B": [60.0]}
        returns = {"A": [0.05], "C": [0.10]}  # C not in scores
        result = calibrate_alpha_from_backtest(scores, returns, n_buckets=2)
        assert len(result) > 0


class TestV4ToCandidates:
    """Tests for V4 result to candidate conversion."""

    def test_basic_conversion(self):
        composites = [_make_composite("AAPL", 80.0), _make_composite("MSFT", 70.0)]
        alphas = {"AAPL": 0.025, "MSFT": -0.01}
        v4_results = [
            {"ticker": "AAPL", "opportunity_type": "compounder", "conviction": "exceptional"},
            {"ticker": "MSFT", "opportunity_type": "mispricing", "conviction": "high"},
        ]

        candidates = v4_to_candidates(v4_results, composites, alphas)
        assert len(candidates) == 2
        assert candidates[0].ticker == "AAPL"
        assert candidates[0].expected_alpha == 0.025
        assert candidates[0].track == "compounder"

    def test_ml_blending(self):
        composites = [_make_composite("AAPL", 80.0)]
        alphas = {"AAPL": 0.02}
        ml_alphas = {"AAPL": 0.04}
        v4_results = [{"ticker": "AAPL", "opportunity_type": "both", "conviction": "high"}]

        candidates = v4_to_candidates(
            v4_results, composites, alphas, ml_alphas=ml_alphas, ml_weight=0.30
        )
        # 0.70 * 0.02 + 0.30 * 0.04 = 0.014 + 0.012 = 0.026
        assert abs(candidates[0].expected_alpha - 0.026) < 1e-6

    def test_missing_ticker_skipped(self):
        composites = [_make_composite("AAPL", 80.0)]
        alphas = {"AAPL": 0.02}  # No MSFT
        v4_results = [
            {"ticker": "AAPL", "opportunity_type": "both", "conviction": "high"},
            {"ticker": "MSFT", "opportunity_type": "both", "conviction": "high"},
        ]
        candidates = v4_to_candidates(v4_results, composites, alphas)
        assert len(candidates) == 1
        assert candidates[0].ticker == "AAPL"
