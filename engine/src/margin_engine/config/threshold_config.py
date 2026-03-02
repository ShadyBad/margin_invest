"""Conviction threshold configuration — YAML-loadable with Pydantic defaults.

All conviction thresholds for Track A (Compounder) and Track B (Contrarian)
are defined here with defaults matching the previous hardcoded values in
``scoring/v3_thresholds.py``. Values can be overridden via a YAML file
(typically ``engine/config/thresholds.yaml``).

Usage:
    from margin_engine.config.threshold_config import ThresholdConfig, load_threshold_config

    # Defaults only (no YAML)
    config = ThresholdConfig()

    # Load from YAML with fallback to defaults
    config = load_threshold_config(Path("engine/config/thresholds.yaml"))
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TrackAThresholds(BaseModel):
    """Track A (Compounder) conviction thresholds."""

    exceptional_power: float = 0.15
    exceptional_moat: int = 3
    exceptional_gap: float = 0.08
    high_power: float = 0.08
    high_moat: int = 2
    high_gap: float = 0.03
    medium_power: float = 0.04
    medium_moat: int = 2
    min_gates_full: int = 4
    min_gates_medium: int = 3


class TrackBThresholds(BaseModel):
    """Track B (Contrarian) conviction thresholds."""

    exceptional_asymmetry: float = 5.0
    exceptional_catalyst: float = 55.0
    exceptional_converging: int = 4
    high_asymmetry: float = 3.0
    high_catalyst: float = 40.0
    high_converging: int = 3
    medium_asymmetry: float = 1.5
    min_gates_full: int = 4
    min_gates_medium: int = 3


class ThresholdConfig(BaseModel):
    """Top-level conviction threshold configuration.

    Every field has a default matching the previous hardcoded values, so
    constructing ``ThresholdConfig()`` with no arguments produces identical
    behavior to the existing code.
    """

    track_a: TrackAThresholds = TrackAThresholds()
    track_b: TrackBThresholds = TrackBThresholds()
    hysteresis_buffer: float = 0.10


def load_threshold_config(path: Path | None = None) -> ThresholdConfig:
    """Load threshold configuration from a YAML file.

    If the path does not exist or is None, returns a ThresholdConfig with
    all defaults (matching previous hardcoded behavior).

    Args:
        path: Path to a YAML file. If None or non-existent, defaults are used.

    Returns:
        A validated ThresholdConfig instance.
    """
    if path is None or not path.exists():
        if path is not None:
            logger.debug("Config file %s not found; using defaults", path)
        return ThresholdConfig()

    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        # Empty YAML file
        return ThresholdConfig()

    return ThresholdConfig.model_validate(raw)
