"""Threshold sensitivity analysis -- parameter sweep for conviction calibration.

Provides a parameter grid builder and sweep runner for empirically tuning
conviction thresholds in ThresholdConfig.  Given a base config and a list of
parameter variations, ``build_parameter_grid`` generates the Cartesian product
of all value combinations.  ``run_threshold_sensitivity`` then executes a
user-supplied backtest function for each config and returns the results sorted
by Sharpe ratio descending.

Usage:
    from margin_engine.backtesting.threshold_sensitivity import (
        ThresholdVariation, build_parameter_grid, run_threshold_sensitivity,
    )
    from margin_engine.config.threshold_config import ThresholdConfig

    variations = [
        ThresholdVariation(param_path="track_a.high_power", values=[0.06, 0.08, 0.10]),
        ThresholdVariation(param_path="track_b.high_asymmetry", values=[2.5, 3.0, 3.5]),
    ]
    grid = build_parameter_grid(ThresholdConfig(), variations)
    results = run_threshold_sensitivity(grid, my_backtest_fn)
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from margin_engine.config.threshold_config import ThresholdConfig

logger = logging.getLogger(__name__)


class ThresholdVariation(BaseModel):
    """A single parameter to vary in the sensitivity sweep.

    Attributes:
        param_path: Dot-separated path to the parameter on ThresholdConfig.
                    Top-level paths (e.g. ``"hysteresis_buffer"``) and nested
                    paths (e.g. ``"track_a.high_power"``) are both supported.
        values: The values to sweep through for this parameter.
    """

    param_path: str
    values: list[float | int]


class SensitivityResult(BaseModel):
    """Metrics for a single threshold configuration in the sweep.

    Attributes:
        config_label: Human-readable label describing the parameter combination.
        cagr: Compound annual growth rate.
        sharpe: Sharpe ratio.
        max_drawdown: Maximum drawdown (positive fraction).
        excess_cagr: CAGR above benchmark.
        num_positions_avg: Average number of positions held.
        turnover_avg: Average monthly turnover.
    """

    config_label: str
    cagr: float
    sharpe: float
    max_drawdown: float
    excess_cagr: float
    num_positions_avg: float
    turnover_avg: float


def _set_nested_attr(config: ThresholdConfig, path: str, value: Any) -> ThresholdConfig:
    """Set a nested attribute on a ThresholdConfig using model_dump/reconstruct.

    Decomposes the config to a dict, sets the value at the dot-separated path,
    and reconstructs a validated ThresholdConfig.

    Args:
        config: The base config to modify (not mutated).
        path: Dot-separated attribute path, e.g. ``"track_a.high_power"``
              or ``"hysteresis_buffer"``.
        value: The value to assign.

    Returns:
        A new ThresholdConfig with the specified attribute changed.

    Raises:
        KeyError: If the path does not exist in the config dict.
    """
    data = config.model_dump()
    parts = path.split(".")

    target = data
    for part in parts[:-1]:
        if part not in target:
            raise KeyError(f"Invalid config path segment: {part!r} in {path!r}")
        target = target[part]

    final_key = parts[-1]
    if final_key not in target:
        raise KeyError(f"Invalid config path: {path!r} -- key {final_key!r} not found")

    target[final_key] = value
    return ThresholdConfig.model_validate(data)


def build_parameter_grid(
    base_config: ThresholdConfig,
    variations: list[ThresholdVariation],
) -> list[ThresholdConfig]:
    """Build the Cartesian product of all threshold variations.

    Given a base config and a list of parameter variations, produces every
    combination of the specified values applied to the base config.

    Args:
        base_config: Starting ThresholdConfig whose unvaried fields are
                     preserved in all output configs.
        variations: Parameters to vary.  An empty list returns a single-element
                    list containing the base_config unchanged.

    Returns:
        List of ThresholdConfig instances, one per combination in the
        Cartesian product.  Length equals the product of
        ``len(v.values)`` for each variation.
    """
    if not variations:
        return [base_config]

    # Build the list of (path, value) iterables
    param_lists = [[(v.param_path, val) for val in v.values] for v in variations]

    configs: list[ThresholdConfig] = []
    for combo in itertools.product(*param_lists):
        cfg = base_config
        for path, value in combo:
            cfg = _set_nested_attr(cfg, path, value)
        configs.append(cfg)

    return configs


def _build_config_label(combo: tuple[tuple[str, Any], ...]) -> str:
    """Build a human-readable label from a parameter combination."""
    parts = [f"{path}={value}" for path, value in combo]
    return ", ".join(parts)


def run_threshold_sensitivity(
    configs: list[ThresholdConfig],
    run_backtest_fn: Callable[[ThresholdConfig], Any],
) -> list[SensitivityResult]:
    """Run a backtest for each config and collect metrics, sorted by Sharpe.

    The ``run_backtest_fn`` callable should accept a ThresholdConfig and return
    an object with a ``.metrics`` attribute containing at least:
    ``cagr``, ``sharpe_ratio``, ``max_drawdown``, ``excess_cagr``, and
    ``avg_turnover``.  This matches the ``ReplayResult.metrics`` interface.

    Args:
        configs: List of ThresholdConfig instances to evaluate.
        run_backtest_fn: Callable that runs a backtest for a given config.

    Returns:
        List of SensitivityResult sorted by Sharpe ratio descending.
        Empty list if configs is empty.
    """
    if not configs:
        return []

    results: list[SensitivityResult] = []

    for i, cfg in enumerate(configs):
        logger.info("Sensitivity sweep %d/%d", i + 1, len(configs))
        replay = run_backtest_fn(cfg)

        metrics = replay.metrics

        # Build a label from non-default config values
        label = f"config_{i}"

        result = SensitivityResult(
            config_label=label,
            cagr=metrics.cagr,
            sharpe=metrics.sharpe_ratio,
            max_drawdown=metrics.max_drawdown,
            excess_cagr=metrics.excess_cagr,
            num_positions_avg=0.0,  # TODO: derive from snapshots when available
            turnover_avg=metrics.avg_turnover,
        )
        results.append(result)

    # Sort by Sharpe descending
    results.sort(key=lambda r: r.sharpe, reverse=True)

    return results
