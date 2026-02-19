"""Filter configuration — Pydantic models with YAML loading.

All filter thresholds are defined here with defaults matching the current
hardcoded values throughout the scoring/filters package. Values can be
overridden via a YAML file (typically engine/config/filters.yaml).

Usage:
    from margin_engine.config.filter_config import FilterConfig, load_filter_config

    # Defaults only (no YAML)
    config = FilterConfig()

    # Load from YAML with fallback to defaults
    config = load_filter_config(Path("engine/config/filters.yaml"))
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Liquidity sub-models ---


class DollarVolumeTiers(BaseModel):
    """Minimum average daily dollar volume by market-cap bucket."""

    mega: int = 50_000_000
    large: int = 20_000_000
    mid: int = 5_000_000
    small: int = 2_000_000


class MarketCapMinimum(BaseModel):
    """Minimum market cap thresholds (sector-adjusted)."""

    default: int = 300_000_000
    utilities: int = 1_000_000_000
    energy: int = 500_000_000


class PositionSizingConfig(BaseModel):
    """Position sizing and market impact settings for liquidity v2."""

    target_position: int = 500_000
    max_participation_rate: float = 0.05
    max_days_to_fill: int = 5
    max_impact_bps: float = 50.0


# Backward-compatible alias for code that references the old name
PositionImpact = PositionSizingConfig


class LiquidityConfig(BaseModel):
    """Liquidity filter configuration."""

    excluded_sectors: list[str] = Field(
        default_factory=lambda: ["Financials", "Real Estate"]
    )
    min_years_of_history: int = 5
    market_cap_minimum: MarketCapMinimum = Field(default_factory=MarketCapMinimum)
    dollar_volume: DollarVolumeTiers = Field(default_factory=DollarVolumeTiers)
    dollar_volume_window_days: int = 60
    position_sizing: PositionSizingConfig = Field(default_factory=PositionSizingConfig)
    divergence_max_ratio: float = 3.0

    @property
    def position_impact(self) -> PositionSizingConfig:
        """Backward-compatible alias for position_sizing."""
        return self.position_sizing


# --- Individual filter configs ---


class BeneishConfig(BaseModel):
    """Beneish M-Score filter configuration."""

    threshold: float = -1.78


class AltmanConfig(BaseModel):
    """Altman Z'' Score filter configuration."""

    threshold: float = 1.1
    equity_tl_cap: float = 10.0
    exempt_sectors: list[str] = Field(default_factory=lambda: ["Utilities"])


class FcfDistressConfig(BaseModel):
    """Free Cash Flow distress filter configuration."""

    positive_years_required: int = 3
    lookback_years: int = 5
    min_fcf_margin: float = -0.05
    allow_positive_trend_rescue: bool = True


class InterestCoverageConfig(BaseModel):
    """Interest Coverage Ratio filter configuration.

    Sector override keys should be the lowercased GICSSector value, e.g.
    ``"information technology"``, ``"utilities"``.
    """

    default: float = 1.5
    sector_overrides: dict[str, float] = Field(
        default_factory=lambda: {"information technology": 5.0, "utilities": 1.2}
    )
    median_lookback_years: int = 3
    median_minimum: float = 1.0


class CurrentRatioConfig(BaseModel):
    """Current Ratio filter configuration.

    Sector override keys should be the lowercased GICSSector value, e.g.
    ``"information technology"``, ``"utilities"``.
    """

    default: float = 0.8
    sector_overrides: dict[str, float] = Field(
        default_factory=lambda: {"information technology": 0.8, "utilities": 0.6}
    )
    quick_ratio_rescue: float = 0.5
    max_3yr_decline_pct: float = 30.0


class GrossMarginThresholds(BaseModel):
    """Gross margin thresholds (sector-adjusted) for the mediocrity gate."""

    default: float = 0.20
    energy: float = 0.15
    utilities: float = 0.10


class MediocGateConfig(BaseModel):
    """Anti-Mediocrity Gate filter configuration."""

    min_roic_5yr_median: float = 0.08
    gross_margin: GrossMarginThresholds = Field(default_factory=GrossMarginThresholds)
    fcf_positive_years: int = 4
    fcf_lookback_years: int = 5
    max_consecutive_revenue_decline: int = 3


# --- Top-level config ---


class FilterConfig(BaseModel):
    """Top-level filter configuration containing all filter sub-configs.

    Every field has a default matching the current hardcoded values, so
    constructing ``FilterConfig()`` with no arguments produces identical
    behavior to the existing code.
    """

    liquidity: LiquidityConfig = Field(default_factory=LiquidityConfig)
    beneish: BeneishConfig = Field(default_factory=BeneishConfig)
    altman: AltmanConfig = Field(default_factory=AltmanConfig)
    fcf_distress: FcfDistressConfig = Field(default_factory=FcfDistressConfig)
    interest_coverage: InterestCoverageConfig = Field(
        default_factory=InterestCoverageConfig
    )
    current_ratio: CurrentRatioConfig = Field(default_factory=CurrentRatioConfig)
    mediocrity_gate: MediocGateConfig = Field(default_factory=MediocGateConfig)


def load_filter_config(path: Path | None = None) -> FilterConfig:
    """Load filter configuration from a YAML file.

    If the path does not exist or is None, returns a FilterConfig with
    all defaults (matching current hardcoded behavior).

    Args:
        path: Path to a YAML file. If None or non-existent, defaults are used.

    Returns:
        A validated FilterConfig instance.
    """
    if path is None or not path.exists():
        if path is not None:
            logger.debug("Config file %s not found; using defaults", path)
        return FilterConfig()

    with open(path) as f:
        raw = yaml.safe_load(f)

    if raw is None:
        # Empty YAML file
        return FilterConfig()

    return FilterConfig.model_validate(raw)
