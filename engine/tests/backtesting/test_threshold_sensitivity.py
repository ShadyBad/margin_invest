"""Tests for threshold sensitivity analysis -- parameter grid and sweep runner."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from margin_engine.backtesting.threshold_sensitivity import (
    ThresholdVariation,
    _set_nested_attr,
    build_parameter_grid,
    run_threshold_sensitivity,
)
from margin_engine.config.threshold_config import ThresholdConfig


class TestSetNestedAttr:
    def test_top_level_attr(self):
        cfg = ThresholdConfig()
        result = _set_nested_attr(cfg, "hysteresis_buffer", 0.20)
        assert result.hysteresis_buffer == 0.20
        # Original unchanged
        assert cfg.hysteresis_buffer == 0.10

    def test_nested_attr(self):
        cfg = ThresholdConfig()
        result = _set_nested_attr(cfg, "track_a.high_power", 0.12)
        assert result.track_a.high_power == 0.12
        # Other attrs unchanged
        assert result.track_a.exceptional_power == 0.15

    def test_invalid_top_level_key_raises(self):
        cfg = ThresholdConfig()
        with pytest.raises(KeyError, match="not_a_real_key"):
            _set_nested_attr(cfg, "not_a_real_key", 1.0)

    def test_invalid_nested_key_raises(self):
        cfg = ThresholdConfig()
        with pytest.raises(KeyError, match="nonexistent"):
            _set_nested_attr(cfg, "track_a.nonexistent", 1.0)

    def test_invalid_intermediate_key_raises(self):
        cfg = ThresholdConfig()
        with pytest.raises(KeyError, match="fake_track"):
            _set_nested_attr(cfg, "fake_track.high_power", 1.0)


class TestBuildParameterGrid:
    def test_single_param_variation(self):
        """Single param with 4 values -> 4 configs."""
        variations = [
            ThresholdVariation(param_path="track_a.high_power", values=[0.06, 0.08, 0.10, 0.12]),
        ]
        grid = build_parameter_grid(ThresholdConfig(), variations)
        assert len(grid) == 4
        assert grid[0].track_a.high_power == 0.06
        assert grid[3].track_a.high_power == 0.12
        # Other params unchanged
        assert grid[0].track_a.exceptional_power == 0.15

    def test_two_param_grid(self):
        """2 params x 2 values each -> 4 configs."""
        variations = [
            ThresholdVariation(param_path="track_a.high_power", values=[0.06, 0.10]),
            ThresholdVariation(param_path="track_b.high_asymmetry", values=[2.5, 3.5]),
        ]
        grid = build_parameter_grid(ThresholdConfig(), variations)
        assert len(grid) == 4

    def test_empty_variations_returns_default(self):
        grid = build_parameter_grid(ThresholdConfig(), [])
        assert len(grid) == 1

    def test_three_param_grid(self):
        """3 params x 2 values -> 8 configs."""
        variations = [
            ThresholdVariation(param_path="track_a.high_power", values=[0.06, 0.10]),
            ThresholdVariation(param_path="track_b.high_asymmetry", values=[2.5, 3.5]),
            ThresholdVariation(param_path="hysteresis_buffer", values=[0.05, 0.15]),
        ]
        grid = build_parameter_grid(ThresholdConfig(), variations)
        assert len(grid) == 8

    def test_preserves_unmodified_values(self):
        variations = [
            ThresholdVariation(param_path="track_a.exceptional_power", values=[0.20]),
        ]
        grid = build_parameter_grid(ThresholdConfig(), variations)
        assert grid[0].track_a.exceptional_power == 0.20
        assert grid[0].track_a.high_power == 0.08  # default unchanged
        assert grid[0].track_b.exceptional_asymmetry == 5.0  # default unchanged

    def test_top_level_param(self):
        """Can vary top-level params like hysteresis_buffer."""
        variations = [
            ThresholdVariation(param_path="hysteresis_buffer", values=[0.05, 0.15, 0.20]),
        ]
        grid = build_parameter_grid(ThresholdConfig(), variations)
        assert len(grid) == 3
        assert grid[0].hysteresis_buffer == 0.05
        assert grid[2].hysteresis_buffer == 0.20

    def test_grid_values_are_correct_combinations(self):
        """Verify all 4 combinations of a 2x2 grid have the right values."""
        variations = [
            ThresholdVariation(param_path="track_a.high_power", values=[0.06, 0.10]),
            ThresholdVariation(param_path="track_b.high_asymmetry", values=[2.5, 3.5]),
        ]
        grid = build_parameter_grid(ThresholdConfig(), variations)

        # Cartesian product order: (0.06, 2.5), (0.06, 3.5), (0.10, 2.5), (0.10, 3.5)
        assert grid[0].track_a.high_power == 0.06
        assert grid[0].track_b.high_asymmetry == 2.5
        assert grid[1].track_a.high_power == 0.06
        assert grid[1].track_b.high_asymmetry == 3.5
        assert grid[2].track_a.high_power == 0.10
        assert grid[2].track_b.high_asymmetry == 2.5
        assert grid[3].track_a.high_power == 0.10
        assert grid[3].track_b.high_asymmetry == 3.5

    def test_single_value_variation_passthrough(self):
        """A variation with a single value produces one config with that value."""
        base = ThresholdConfig()
        variations = [
            ThresholdVariation(param_path="hysteresis_buffer", values=[0.42]),
        ]
        grid = build_parameter_grid(base, variations)
        assert len(grid) == 1
        assert grid[0].hysteresis_buffer == 0.42


class TestRunThresholdSensitivity:
    def _make_mock_result(self, cagr=0.10, sharpe=1.0, max_dd=0.20, excess=0.03, turnover=0.15):
        result = MagicMock()
        result.metrics.cagr = cagr
        result.metrics.sharpe_ratio = sharpe
        result.metrics.max_drawdown = max_dd
        result.metrics.excess_cagr = excess
        result.metrics.avg_turnover = turnover
        return result

    def test_returns_sorted_by_sharpe(self):
        """Results sorted by Sharpe ratio descending."""
        # Use distinct configs so lookup by value is unambiguous
        configs = [
            ThresholdConfig(hysteresis_buffer=0.10),
            ThresholdConfig(hysteresis_buffer=0.20),
            ThresholdConfig(hysteresis_buffer=0.30),
        ]
        sharpe_map = {0.10: 0.5, 0.20: 1.2, 0.30: 0.8}

        def mock_backtest(cfg):
            return self._make_mock_result(sharpe=sharpe_map[cfg.hysteresis_buffer])

        results = run_threshold_sensitivity(configs, mock_backtest)
        assert results[0].sharpe == 1.2
        assert results[1].sharpe == 0.8
        assert results[2].sharpe == 0.5

    def test_empty_configs_returns_empty(self):
        results = run_threshold_sensitivity([], lambda c: None)
        assert results == []

    def test_populates_all_fields(self):
        """All SensitivityResult fields are populated from metrics."""
        configs = [ThresholdConfig()]

        def mock_backtest(cfg):
            return self._make_mock_result(
                cagr=0.12, sharpe=1.5, max_dd=0.18, excess=0.05, turnover=0.22
            )

        results = run_threshold_sensitivity(configs, mock_backtest)
        assert len(results) == 1
        r = results[0]
        assert r.cagr == 0.12
        assert r.sharpe == 1.5
        assert r.max_drawdown == 0.18
        assert r.excess_cagr == 0.05
        assert r.turnover_avg == 0.22

    def test_handles_multiple_configs(self):
        """All configs are evaluated and returned."""
        configs = [ThresholdConfig() for _ in range(5)]

        def mock_backtest(cfg):
            idx = configs.index(cfg)
            return self._make_mock_result(sharpe=float(idx))

        results = run_threshold_sensitivity(configs, mock_backtest)
        assert len(results) == 5
        # Should be sorted descending
        sharpes = [r.sharpe for r in results]
        assert sharpes == sorted(sharpes, reverse=True)

    def test_result_labels_are_unique(self):
        """Each result gets a unique label."""
        configs = [ThresholdConfig() for _ in range(3)]

        def mock_backtest(cfg):
            return self._make_mock_result()

        results = run_threshold_sensitivity(configs, mock_backtest)
        labels = [r.config_label for r in results]
        assert len(set(labels)) == len(labels)
