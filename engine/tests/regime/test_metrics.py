"""Tests for regime-segmented ablation metrics."""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pytest

from margin_engine.regime.metrics import (
    RegimePerformanceSlice,
    RegimeSegmentedMetrics,
    compute_regime_segmented_metrics,
    _compute_max_drawdown,
    _compute_sharpe,
)
from margin_engine.regime.models import (
    CreditState,
    RegimeConfidence,
    RegimeState,
    TrendState,
    ValuationState,
    VolatilityState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_regime(
    trend: TrendState = TrendState.BULL,
    volatility: VolatilityState = VolatilityState.NORMAL,
    valuation: ValuationState = ValuationState.NORMAL,
    credit: CreditState = CreditState.NORMAL,
    as_of_date: date | None = None,
) -> RegimeState:
    """Build a RegimeState with sensible defaults."""
    return RegimeState(
        as_of_date=as_of_date or date(2024, 1, 1),
        volatility=volatility,
        trend=trend,
        valuation=valuation,
        credit=credit,
        confidence=RegimeConfidence(
            volatility=0.8, trend=0.8, valuation=0.8, credit=0.8
        ),
    )


# ---------------------------------------------------------------------------
# Test: empty inputs -> empty result
# ---------------------------------------------------------------------------

class TestEmptyInputs:
    def test_empty_inputs_return_empty_result(self):
        result = compute_regime_segmented_metrics(
            regime_tags=[], monthly_returns=[], benchmark_returns=[]
        )
        assert isinstance(result, RegimeSegmentedMetrics)
        assert result.slices == {}


# ---------------------------------------------------------------------------
# Test: mismatched lengths -> ValueError
# ---------------------------------------------------------------------------

class TestMismatchedLengths:
    def test_mismatched_regime_and_returns_raises(self):
        regime = _make_regime()
        with pytest.raises(ValueError, match="same length"):
            compute_regime_segmented_metrics(
                regime_tags=[regime, regime],
                monthly_returns=[0.01],
                benchmark_returns=[0.005, 0.005],
            )

    def test_mismatched_returns_and_benchmark_raises(self):
        regime = _make_regime()
        with pytest.raises(ValueError, match="same length"):
            compute_regime_segmented_metrics(
                regime_tags=[regime],
                monthly_returns=[0.01],
                benchmark_returns=[0.005, 0.005],
            )


# ---------------------------------------------------------------------------
# Test: single regime -> one slice
# ---------------------------------------------------------------------------

class TestSingleRegime:
    def test_single_regime_produces_one_slice(self):
        regimes = [_make_regime(trend=TrendState.BULL) for _ in range(12)]
        returns = [0.02] * 12
        bench = [0.01] * 12

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        assert len(result.slices) == 1
        key = regimes[0].regime_key
        assert key in result.slices
        sl = result.slices[key]
        assert sl.n_months == 12
        assert sl.regime_key == key


# ---------------------------------------------------------------------------
# Test: two regimes -> two slices
# ---------------------------------------------------------------------------

class TestTwoRegimes:
    def test_two_regimes_produce_two_slices(self):
        bull = _make_regime(trend=TrendState.BULL)
        bear = _make_regime(trend=TrendState.BEAR)
        regimes = [bull] * 6 + [bear] * 6
        returns = [0.02] * 6 + [-0.03] * 6
        bench = [0.01] * 12

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        assert len(result.slices) == 2
        assert bull.regime_key in result.slices
        assert bear.regime_key in result.slices
        assert result.slices[bull.regime_key].n_months == 6
        assert result.slices[bear.regime_key].n_months == 6


# ---------------------------------------------------------------------------
# Test: slice has sharpe + drawdown + n_months
# ---------------------------------------------------------------------------

class TestSliceContents:
    def test_slice_has_sharpe_drawdown_n_months(self):
        regimes = [_make_regime(trend=TrendState.BULL) for _ in range(12)]
        returns = [0.02] * 12
        bench = [0.01] * 12

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        key = regimes[0].regime_key
        sl = result.slices[key]

        # Sharpe: (0.02 - rf) / std * sqrt(12), all returns equal so std=0 -> 0.0
        # Actually all returns identical means std=0, so sharpe should be 0
        assert isinstance(sl.sharpe_ratio, float)
        assert isinstance(sl.max_drawdown, float)
        assert sl.n_months == 12
        assert isinstance(sl.win_rate, float)
        assert isinstance(sl.mean_return, float)
        assert isinstance(sl.volatility, float)
        assert isinstance(sl.mean_excess_return, float)

    def test_sharpe_with_varying_returns(self):
        """When returns vary, Sharpe is computed properly."""
        regimes = [_make_regime() for _ in range(6)]
        returns = [0.03, 0.01, 0.04, 0.02, 0.05, 0.00]
        bench = [0.01] * 6

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        key = regimes[0].regime_key
        sl = result.slices[key]

        # Manual calculation
        rf = 0.04 / 12
        arr = np.array(returns)
        excess = arr - rf
        expected_sharpe = float(np.mean(excess) / np.std(excess, ddof=1) * np.sqrt(12))
        assert abs(sl.sharpe_ratio - expected_sharpe) < 1e-9

    def test_max_drawdown_computed(self):
        """Max drawdown captures the worst peak-to-trough."""
        regimes = [_make_regime() for _ in range(4)]
        # Cumulative: 1.10, 1.10*0.85=0.935, 0.935*1.05=0.982, 0.982*1.02=1.001
        returns = [0.10, -0.15, 0.05, 0.02]
        bench = [0.01] * 4

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        key = regimes[0].regime_key
        sl = result.slices[key]

        # Peak at 1.10, trough at 0.935 -> drawdown = (0.935 - 1.10) / 1.10 = -0.15
        assert sl.max_drawdown < 0
        assert abs(sl.max_drawdown - (-0.15)) < 1e-9


# ---------------------------------------------------------------------------
# Test: bull regime has higher Sharpe than bear
# ---------------------------------------------------------------------------

class TestBullBearSharpeComparison:
    def test_bull_sharpe_higher_than_bear(self):
        bull = _make_regime(trend=TrendState.BULL)
        bear = _make_regime(trend=TrendState.BEAR)

        # Bull months: positive returns with some variance
        bull_returns = [0.03, 0.04, 0.02, 0.05, 0.03, 0.04]
        # Bear months: negative returns with some variance
        bear_returns = [-0.03, -0.04, -0.02, -0.05, -0.03, -0.04]

        regimes = [bull] * 6 + [bear] * 6
        returns = bull_returns + bear_returns
        bench = [0.01] * 12

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        bull_sharpe = result.slices[bull.regime_key].sharpe_ratio
        bear_sharpe = result.slices[bear.regime_key].sharpe_ratio

        assert bull_sharpe > bear_sharpe


# ---------------------------------------------------------------------------
# Test: win rate computed correctly
# ---------------------------------------------------------------------------

class TestWinRate:
    def test_win_rate_all_positive_excess(self):
        regimes = [_make_regime() for _ in range(4)]
        returns = [0.05, 0.04, 0.03, 0.06]  # all > benchmark
        bench = [0.01, 0.01, 0.01, 0.01]

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        key = regimes[0].regime_key
        assert result.slices[key].win_rate == 1.0

    def test_win_rate_mixed(self):
        regimes = [_make_regime() for _ in range(4)]
        returns = [0.05, -0.01, 0.03, -0.02]
        bench = [0.01, 0.01, 0.01, 0.01]
        # excess: 0.04, -0.02, 0.02, -0.03 -> 2 wins, 2 losses

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        key = regimes[0].regime_key
        assert result.slices[key].win_rate == 0.5

    def test_win_rate_none_positive(self):
        regimes = [_make_regime() for _ in range(3)]
        returns = [-0.01, -0.02, -0.03]
        bench = [0.01, 0.01, 0.01]

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        key = regimes[0].regime_key
        assert result.slices[key].win_rate == 0.0

    def test_win_rate_exact_zero_excess_not_counted(self):
        """Excess return of exactly 0 is NOT a win (must be > 0)."""
        regimes = [_make_regime() for _ in range(2)]
        returns = [0.01, 0.03]
        bench = [0.01, 0.01]
        # excess: 0.0, 0.02 -> 1 win out of 2

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        key = regimes[0].regime_key
        assert result.slices[key].win_rate == 0.5


# ---------------------------------------------------------------------------
# Test: private helper functions
# ---------------------------------------------------------------------------

class TestComputeSharpe:
    def test_less_than_two_months_returns_zero(self):
        assert _compute_sharpe(np.array([0.05])) == 0.0

    def test_zero_std_returns_zero(self):
        # All returns identical -> std = 0
        assert _compute_sharpe(np.array([0.05, 0.05, 0.05])) == 0.0

    def test_known_value(self):
        returns = np.array([0.03, 0.01, 0.04, 0.02, 0.05, 0.00])
        rf = 0.04 / 12
        excess = returns - rf
        expected = float(np.mean(excess) / np.std(excess, ddof=1) * np.sqrt(12))
        assert abs(_compute_sharpe(returns) - expected) < 1e-9


class TestComputeMaxDrawdown:
    def test_empty_returns_zero(self):
        assert _compute_max_drawdown(np.array([])) == 0.0

    def test_monotonically_increasing(self):
        # No drawdown if always going up
        returns = np.array([0.05, 0.05, 0.05])
        assert _compute_max_drawdown(returns) == 0.0

    def test_known_drawdown(self):
        # 1.0 -> 1.10 -> 0.935 -> 0.982 -> 1.001
        returns = np.array([0.10, -0.15, 0.05, 0.02])
        dd = _compute_max_drawdown(returns)
        assert abs(dd - (-0.15)) < 1e-9


# ---------------------------------------------------------------------------
# Test: mean_excess_return
# ---------------------------------------------------------------------------

class TestMeanExcessReturn:
    def test_mean_excess_return_computed(self):
        regimes = [_make_regime() for _ in range(4)]
        returns = [0.05, 0.03, 0.04, 0.06]
        bench = [0.01, 0.02, 0.01, 0.03]
        # excess: 0.04, 0.01, 0.03, 0.03 -> mean = 0.0275

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench,
        )
        key = regimes[0].regime_key
        assert abs(result.slices[key].mean_excess_return - 0.0275) < 1e-9
